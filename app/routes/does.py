from flask import Blueprint, jsonify, request

from app import db
from ..models import Rabbit, RabbitRole, RabbitStatus, Litter, LitterStatus, MilestoneType, ActivityType
from ..schemas import (
    rabbit_schema, rabbit_create_schema, rabbit_update_schema,
    litter_schema, record_mating_schema, edit_mating_schema,
    activity_logs_schema, weight_logs_schema,
)
from ..utils.auth import farm_scoped
from ..utils.validation import parse_body
from ..utils.activity import log_activity
from ..utils.dates import predict_gestation_dates

does_bp = Blueprint("does", __name__)


@does_bp.get("")
@farm_scoped
def list_does(farm_id: int):
    status = request.args.get("status")
    query = Rabbit.query.filter(Rabbit.farm_id == farm_id, Rabbit.role == RabbitRole.DOE)
    if status:
        query = query.filter(Rabbit.status == status)
    does = query.order_by(Rabbit.name).all()

    payload = []
    for doe in does:
        base = rabbit_schema.dump(doe)
        latest_litter = (
            Litter.query.filter(Litter.dam_id == doe.id)
            .order_by(Litter.mating_date.desc().nullslast(), Litter.id.desc())
            .first()
        )
        base["currentLitterId"] = latest_litter.id if latest_litter else None
        base["matingDate"] = latest_litter.mating_date.isoformat() if latest_litter and latest_litter.mating_date else None
        base["expectedNestingDate"] = (
            latest_litter.expected_nesting_date.isoformat()
            if latest_litter and latest_litter.expected_nesting_date else None
        )
        base["expectedBirthDate"] = (
            latest_litter.expected_birth_date.isoformat()
            if latest_litter and latest_litter.expected_birth_date else None
        )
        base["expectedBirthDateLatest"] = (
            latest_litter.expected_birth_date_latest.isoformat()
            if latest_litter and latest_litter.expected_birth_date_latest else None
        )
        base["currentKits"] = (
            latest_litter.total_kits
            if latest_litter and latest_litter.status in (LitterStatus.NURSING, LitterStatus.WEANING)
            else 0
        )
        payload.append(base)

    return jsonify(payload)


@does_bp.get("/<int:rabbit_id>")
@farm_scoped
def get_doe_details(farm_id: int, rabbit_id: int):
    """Composite payload for the Doe Details screen: rabbit + active litter + milestones
    + recent activity + weight history, in one response."""
    doe = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id, role=RabbitRole.DOE).first_or_404()

    active_litter = (
        Litter.query.filter(Litter.dam_id == doe.id)
        .order_by(Litter.mating_date.desc().nullslast(), Litter.id.desc())
        .first()
    )

    litter_payload = None
    if active_litter:
        litter_payload = litter_schema.dump(active_litter)
        litter_payload["milestones"] = [
            {
                "milestone": m.milestone,
                "expectedDate": m.expected_date.isoformat() if m.expected_date else None,
                "actualDate": m.actual_date.isoformat() if m.actual_date else None,
                "completed": m.completed,
            }
            for m in sorted(active_litter.milestones, key=lambda m: MilestoneType.DAY_OFFSETS[m.milestone])
        ]

    recent_activity = doe.activity_logs[:5]
    weight_history = doe.weight_logs[:5]

    return jsonify(
        doe=rabbit_schema.dump(doe),
        activeLitter=litter_payload,
        recentActivity=activity_logs_schema.dump(recent_activity),
        weightHistory=weight_logs_schema.dump(weight_history),
    )


@does_bp.post("")
@farm_scoped
def create_doe(farm_id: int):
    data = parse_body(rabbit_create_schema)
    doe = Rabbit(farm_id=farm_id, role=RabbitRole.DOE, status=RabbitStatus.ACTIVE, **data)
    db.session.add(doe)
    db.session.commit()
    return jsonify(rabbit_schema.dump(doe)), 201


@does_bp.patch("/<int:rabbit_id>")
@farm_scoped
def update_doe(farm_id: int, rabbit_id: int):
    doe = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id, role=RabbitRole.DOE).first_or_404()
    data = parse_body(rabbit_update_schema)
    for key, value in data.items():
        setattr(doe, key, value)
    db.session.commit()
    return jsonify(rabbit_schema.dump(doe))


@does_bp.post("/<int:rabbit_id>/mating")
@farm_scoped
def record_mating(farm_id: int, rabbit_id: int):
    """Creates the litters row for a new breeding cycle and predicts nesting/birth dates."""
    doe = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id, role=RabbitRole.DOE).first_or_404()
    data = parse_body(record_mating_schema)

    mating_date = data["mating_date"]
    litter = Litter(
        farm_id=farm_id,
        dam_id=doe.id,
        sire_id=data["sire_id"],
        mating_date=mating_date,
        status=LitterStatus.EXPECTING,
        **predict_gestation_dates(mating_date),
    )
    db.session.add(litter)
    doe.status = RabbitStatus.PREGNANT

    log_activity(
        rabbit_id=doe.id,
        activity_type=ActivityType.MATING_EVENT,
        title="Mating Event",
        description=f"Mated with buck #{data['sire_id']}.",
        occurred_at=mating_date,
    )

    db.session.commit()
    return jsonify(litter_schema.dump(litter)), 201


@does_bp.patch("/<int:rabbit_id>/mating")
@farm_scoped
def edit_mating(farm_id: int, rabbit_id: int):
    doe = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id, role=RabbitRole.DOE).first_or_404()
    litter = (
        Litter.query.filter(Litter.dam_id == doe.id)
        .order_by(Litter.mating_date.desc().nullslast(), Litter.id.desc())
        .first()
    )
    if litter is None:
        return jsonify(message="This doe has no recorded litter to edit."), 404

    data = parse_body(edit_mating_schema)
    litter.mating_date = data["mating_date"]
    if data.get("sire_id"):
        litter.sire_id = data["sire_id"]

    for field, value in predict_gestation_dates(data["mating_date"]).items():
        setattr(litter, field, value)

    db.session.commit()
    return jsonify(litter_schema.dump(litter))
