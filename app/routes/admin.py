import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, g

from app import db
from ..models import Section, Breed, FarmUser, FarmInvite, ActivityLog, WeightLog
from ..schemas import (
    section_schema, sections_schema, breed_schema, breeds_schema,
    create_invite_schema, update_farm_user_schema,
)
from ..utils.auth import farm_scoped, require_admin
from ..utils.validation import parse_body
from ..utils.email import send_farm_invite_email, EmailError

admin_bp = Blueprint("admin", __name__)

INVITE_EXPIRY_DAYS = 7


# ── Sections ──────────────────────────────────────────
@admin_bp.get("/sections")
@farm_scoped
def list_sections(farm_id: int):
    sections = Section.query.filter_by(farm_id=farm_id).order_by(Section.code).all()
    return jsonify(sections_schema.dump(sections))


@admin_bp.post("/sections")
@farm_scoped
@require_admin
def create_section(farm_id: int):
    data = parse_body(section_schema)
    section = Section(farm_id=farm_id, **data)
    db.session.add(section)
    db.session.commit()
    return jsonify(section_schema.dump(section)), 201


@admin_bp.patch("/sections/<int:section_id>")
@farm_scoped
@require_admin
def update_section(farm_id: int, section_id: int):
    section = Section.query.filter_by(id=section_id, farm_id=farm_id).first_or_404()
    data = parse_body(section_schema)
    for key, value in data.items():
        setattr(section, key, value)
    db.session.commit()
    return jsonify(section_schema.dump(section))


# ── Breeds ────────────────────────────────────────────
@admin_bp.get("/breeds")
@farm_scoped
def list_breeds(farm_id: int):
    # Global breeds (farm_id IS NULL) plus this farm's own custom breeds.
    breeds = (
        Breed.query.filter((Breed.farm_id == farm_id) | (Breed.farm_id.is_(None)))
        .order_by(Breed.name)
        .all()
    )
    return jsonify(breeds_schema.dump(breeds))


@admin_bp.post("/breeds")
@farm_scoped
@require_admin
def create_breed(farm_id: int):
    data = parse_body(breed_schema)
    breed = Breed(farm_id=farm_id, **data)
    db.session.add(breed)
    db.session.commit()
    return jsonify(breed_schema.dump(breed)), 201


@admin_bp.patch("/breeds/<int:breed_id>")
@farm_scoped
@require_admin
def update_breed(farm_id: int, breed_id: int):
    # Only this farm's own breeds can be edited — global (farm_id IS NULL) breeds are read-only here.
    breed = Breed.query.filter_by(id=breed_id, farm_id=farm_id).first_or_404()
    data = parse_body(breed_schema)
    for key, value in data.items():
        setattr(breed, key, value)
    db.session.commit()
    return jsonify(breed_schema.dump(breed))


# ── Farm users — the admin profile page's user list ──
@admin_bp.get("/users")
@farm_scoped
@require_admin
def list_farm_users(farm_id: int):
    """Powers the admin profile page: every user on this farm, their role, and a
    lightweight activity summary (count + most recent action) so an admin can see
    who's actually been using the app."""
    memberships = FarmUser.query.filter_by(farm_id=farm_id).all()

    result = []
    for m in memberships:
        activity_count = ActivityLog.query.filter_by(farm_id=farm_id, recorded_by=m.user_id).count()
        weight_count = WeightLog.query.filter_by(farm_id=farm_id, recorded_by=m.user_id).count()
        last_activity = (
            ActivityLog.query.filter_by(farm_id=farm_id, recorded_by=m.user_id)
            .order_by(ActivityLog.created_at.desc())
            .first()
        )
        result.append(
            {
                "userId": m.user_id,
                "name": m.user.name,
                "email": m.user.email,
                "role": m.role,
                "joinedAt": m.joined_at.isoformat() if m.joined_at else None,
                "activityCount": activity_count + weight_count,
                "lastActiveAt": last_activity.created_at.isoformat() if last_activity else None,
            }
        )
    return jsonify(result)


@admin_bp.patch("/users/<int:user_id>")
@farm_scoped
@require_admin
def update_farm_user(farm_id: int, user_id: int):
    """Edit a user's name and/or their role on this farm."""
    membership = FarmUser.query.filter_by(farm_id=farm_id, user_id=user_id).first_or_404()
    data = parse_body(update_farm_user_schema)

    if "name" in data:
        membership.user.name = data["name"]
    if "role" in data:
        if user_id == g.user_id and data["role"] != "admin":
            return jsonify(message="You can't demote yourself."), 400
        membership.role = data["role"]

    db.session.commit()
    return jsonify(
        userId=membership.user_id, name=membership.user.name,
        email=membership.user.email, role=membership.role,
    )


@admin_bp.delete("/users/<int:user_id>")
@farm_scoped
@require_admin
def remove_farm_user(farm_id: int, user_id: int):
    """Removes this user from the farm (their account itself isn't deleted — they may
    belong to other farms)."""
    if user_id == g.user_id:
        return jsonify(message="You can't remove yourself from the farm."), 400
    membership = FarmUser.query.filter_by(farm_id=farm_id, user_id=user_id).first_or_404()
    db.session.delete(membership)
    db.session.commit()
    return "", 204


# ── Invites ───────────────────────────────────────────
@admin_bp.get("/invites")
@farm_scoped
@require_admin
def list_invites(farm_id: int):
    """Pending (not accepted, not cancelled, not expired) invites — shown alongside
    active users on the admin profile page."""
    now = datetime.now(timezone.utc)
    invites = (
        FarmInvite.query.filter(
            FarmInvite.farm_id == farm_id,
            FarmInvite.accepted_at.is_(None),
            FarmInvite.cancelled_at.is_(None),
        )
        .order_by(FarmInvite.created_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "expiresAt": inv.expires_at.isoformat(),
                "expired": inv.expires_at <= now,
                "createdAt": inv.created_at.isoformat(),
            }
            for inv in invites
        ]
    )


@admin_bp.post("/invites")
@farm_scoped
@require_admin
def create_invite(farm_id: int):
    data = parse_body(create_invite_schema)
    farm = FarmUser.query.filter_by(farm_id=farm_id, user_id=g.user_id).first().farm

    raw_token = secrets.token_urlsafe(32)
    invite = FarmInvite(
        farm_id=farm_id,
        email=data["email"].lower(),
        role=data["role"],
        invited_by=g.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    invite.set_token(raw_token)
    db.session.add(invite)
    db.session.commit()  # commit before emailing so a delivery failure doesn't lose the invite

    try:
        send_farm_invite_email(
            to=invite.email, farm_name=farm.name, farm_code=farm.code,
            invite_token=raw_token, role=invite.role,
        )
    except EmailError as e:
        return jsonify(message=f"Invite created but the email failed to send: {e}"), 502

    return jsonify(id=invite.id, email=invite.email, role=invite.role), 201


@admin_bp.post("/invites/<int:invite_id>/cancel")
@farm_scoped
@require_admin
def cancel_invite(farm_id: int, invite_id: int):
    invite = FarmInvite.query.filter_by(id=invite_id, farm_id=farm_id).first_or_404()
    invite.cancelled_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(message="Invite cancelled.")


@admin_bp.post("/invites/<int:invite_id>/resend")
@farm_scoped
@require_admin
def resend_invite(farm_id: int, invite_id: int):
    invite = FarmInvite.query.filter_by(id=invite_id, farm_id=farm_id).first_or_404()
    if not invite.is_redeemable:
        return jsonify(message="This invite was cancelled or already accepted — create a new one instead."), 400

    farm = FarmUser.query.filter_by(farm_id=farm_id, user_id=g.user_id).first().farm
    raw_token = secrets.token_urlsafe(32)
    invite.set_token(raw_token)
    invite.expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)
    db.session.commit()

    try:
        send_farm_invite_email(
            to=invite.email, farm_name=farm.name, farm_code=farm.code,
            invite_token=raw_token, role=invite.role,
        )
    except EmailError as e:
        return jsonify(message=f"Invite refreshed but the email failed to send: {e}"), 502

    return jsonify(message="Invite resent.")
