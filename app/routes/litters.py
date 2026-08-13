from datetime import timedelta
from flask import Blueprint, jsonify

from app import db
from ..models import (
    Litter, LitterMilestone, MilestoneType, LitterStatus,
    Rabbit, RabbitRole, RabbitStatus, ActivityType,
)
from ..schemas import (
    litter_schema, litter_edit_schema, nest_box_schema, record_birth_schema,
    promote_to_breeding_schema, rabbit_schema,
)
from ..utils.auth import farm_scoped
from ..utils.validation import parse_body
from ..utils.activity import log_activity

litters_bp = Blueprint("litters", __name__)


@litters_bp.patch("/<int:litter_id>")
@farm_scoped
def edit_litter(farm_id: int, litter_id: int):
    litter = Litter.query.filter_by(id=litter_id, farm_id=farm_id).first_or_404()
    data = parse_body(litter_edit_schema)
    for key, value in data.items():
        setattr(litter, key, value)
    db.session.commit()
    return jsonify(litter_schema.dump(litter))


@litters_bp.post("/<int:litter_id>/nest-box")
@farm_scoped
def add_nest_box(farm_id: int, litter_id: int):
    litter = Litter.query.filter_by(id=litter_id, farm_id=farm_id).first_or_404()
    data = parse_body(nest_box_schema)

    litter.nest_box_added_at = data["date"]
    litter.status = LitterStatus.NESTING

    log_activity(
        rabbit_id=litter.dam_id,
        litter_id=litter.id,
        activity_type=ActivityType.NEST_BOX_ADDED,
        title="Nest Box Added",
        description="Nest box introduced to the doe ahead of expected kindling.",
        occurred_at=data["date"],
    )

    db.session.commit()
    return jsonify(litter_schema.dump(litter))


@litters_bp.post("/<int:litter_id>/birth")
@farm_scoped
def record_birth(farm_id: int, litter_id: int):
    """
    Records the birth date and the group counts directly — kits are tracked as a
    group only, so no individual `rabbits` rows are created here.
    """
    litter = Litter.query.filter_by(id=litter_id, farm_id=farm_id).first_or_404()
    data = parse_body(record_birth_schema)

    litter.actual_birth_date = data["actual_birth_date"]
    litter.total_kits = data["total_kits"]
    litter.male_kits = data["male_kits"]
    litter.female_kits = data["female_kits"]
    litter.status = LitterStatus.NURSING

    for milestone, offset in MilestoneType.DAY_OFFSETS.items():
        expected = litter.actual_birth_date + timedelta(days=offset)
        db.session.add(
            LitterMilestone(
                litter_id=litter.id,
                milestone=milestone,
                expected_date=expected,
                actual_date=litter.actual_birth_date if milestone == MilestoneType.BIRTH else None,
                completed=(milestone == MilestoneType.BIRTH),
            )
        )

    log_activity(
        rabbit_id=litter.dam_id,
        litter_id=litter.id,
        activity_type=ActivityType.BIRTH,
        title="Litter Born",
        description=f"{data['total_kits']} kits born ({data['male_kits']} male, {data['female_kits']} female).",
        occurred_at=litter.actual_birth_date,
    )

    db.session.commit()
    return jsonify(litter_schema.dump(litter)), 201


@litters_bp.post("/<int:litter_id>/promote")
@farm_scoped
def promote_to_breeding(farm_id: int, litter_id: int):
    litter = Litter.query.filter_by(id=litter_id, farm_id=farm_id).first_or_404()
    if litter.herd_batch_id is not None:
        return jsonify(
            message="This litter's kits have already joined a herd batch — "
            "promote from the batch instead."
        ), 400

    data = parse_body(promote_to_breeding_schema)
    sex = data["sex"]
    count_field = "male_kits" if sex == "M" else "female_kits"

    remaining = getattr(litter, count_field) or 0
    if remaining <= 0:
        return jsonify(message=f"No remaining {'male' if sex == 'M' else 'female'} kits in this litter."), 400
    setattr(litter, count_field, remaining - 1)

    new_rabbit = Rabbit(
        farm_id=farm_id,
        name=data["name"],
        role=RabbitRole.DOE if sex == "F" else RabbitRole.BUCK,
        status=RabbitStatus.ACTIVE,
        sex=sex,
        breed_id=data.get("breed_id"),
        section_id=data.get("section_id"),
        dam_id=litter.dam_id,
        sire_id=litter.sire_id,
        litter_id=litter.id,
        hatch_date=litter.actual_birth_date,
    )
    db.session.add(new_rabbit)

    log_activity(
        litter_id=litter.id,
        activity_type=ActivityType.STATUS_CHANGE,
        title="Promoted to breeding stock",
        description=f"{data['name']} pulled from this litter and added to the active {new_rabbit.role} roster.",
    )

    db.session.commit()
    return jsonify(rabbit_schema.dump(new_rabbit)), 201
