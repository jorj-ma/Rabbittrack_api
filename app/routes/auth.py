from datetime import datetime, timezone
from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required

from app import db
from ..models import User, Farm, FarmUser, FarmRole, FarmInvite, generate_farm_code
from ..schemas import signup_schema, login_schema, accept_invite_schema
from ..utils.validation import parse_body

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/signup")
def signup():
    """Creates a brand-new farm and its first user, who becomes that farm's admin."""
    data = parse_body(signup_schema)

    if User.query.filter_by(email=data["email"].lower()).first() is not None:
        return jsonify(message="An account with this email already exists."), 409

    code = generate_farm_code()
    while Farm.query.filter_by(code=code).first() is not None:  # extremely unlikely, but be sure
        code = generate_farm_code()

    farm = Farm(name=data["farm_name"], code=code)
    db.session.add(farm)
    db.session.flush()  # assigns farm.id

    user = User(name=data["name"], email=data["email"].lower())
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()

    db.session.add(FarmUser(farm_id=farm.id, user_id=user.id, role=FarmRole.ADMIN))
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(
        token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
        farm={"id": farm.id, "name": farm.name, "code": farm.code},
    ), 201


@auth_bp.post("/login")
def login():
    """email + password + farmCode. A person can belong to multiple farms with the same
    account, so farmCode picks which farm this session is scoped to."""
    data = parse_body(login_schema)

    user = User.query.filter_by(email=data["email"].lower()).first()
    if user is None or not user.check_password(data["password"]):
        return jsonify(message="Invalid email or password."), 401

    farm = Farm.query.filter_by(code=data["farm_code"].strip()).first()
    if farm is None:
        return jsonify(message="Invalid farm code."), 401

    membership = FarmUser.query.filter_by(farm_id=farm.id, user_id=user.id).first()
    if membership is None:
        return jsonify(message="This account isn't a member of that farm."), 403

    token = create_access_token(identity=str(user.id))
    return jsonify(
        token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
        farm={"id": farm.id, "name": farm.name, "code": farm.code},
        role=membership.role,
    )


@auth_bp.post("/accept-invite")
def accept_invite():
    """Completes signup for someone an admin invited: verifies the token, creates their
    User account (or reuses an existing one, if this email already has an account and is
    just joining a second farm), and adds the FarmUser membership at the invited role."""
    data = parse_body(accept_invite_schema)

    invite = (
        FarmInvite.query.filter_by(email=data["email"].lower())
        .order_by(FarmInvite.created_at.desc())
        .first()
    )
    if invite is None or not invite.is_redeemable or not invite.check_token(data["token"]):
        return jsonify(message="This invite link is invalid or has expired."), 400

    user = User.query.filter_by(email=data["email"].lower()).first()
    if user is None:
        user = User(name=data["name"], email=data["email"].lower())
        user.set_password(data["password"])
        db.session.add(user)
        db.session.flush()
    elif not user.check_password(data["password"]):
        return jsonify(message="An account already exists for this email — sign in instead."), 409

    existing_membership = FarmUser.query.filter_by(farm_id=invite.farm_id, user_id=user.id).first()
    if existing_membership is None:
        db.session.add(FarmUser(farm_id=invite.farm_id, user_id=user.id, role=invite.role))

    invite.accepted_at = datetime.now(timezone.utc)
    db.session.commit()

    farm = invite.farm
    token = create_access_token(identity=str(user.id))
    return jsonify(
        token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
        farm={"id": farm.id, "name": farm.name, "code": farm.code},
        role=invite.role,
    ), 201


@auth_bp.post("/logout")
@jwt_required()
def logout():
    return jsonify(message="Logged out."), 200
