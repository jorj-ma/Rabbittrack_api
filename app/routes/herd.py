from collections import defaultdict
from flask import Blueprint, jsonify

from app import db
from ..models import Litter, LitterStatus, HerdBatch, ActivityType, Rabbit, RabbitRole, RabbitStatus
from ..schemas import herd_batch_schema, transfer_batch_schema, edit_herd_batch_schema, promote_to_breeding_schema, rabbit_schema
from ..utils.auth import farm_scoped
from ..utils.validation import parse_body
from ..utils.activity import log_activity
from ..utils.dates import age_label, age_months, iso_week_bounds

herd_bp = Blueprint("herd", __name__)

@herd_bp.get("")
@farm_scoped
def get_herd_overview(farm_id: int):
    batches = HerdBatch.query.filter_by(farm_id=farm_id).order_by(HerdBatch.week_start_date.desc()).all()
    total_herd_size = sum(b.male_count + b.female_count for b in batches)
    active_groups = len(batches)

    ready_litters = Litter.query.filter(
        Litter.farm_id == farm_id, Litter.status == LitterStatus.READY_FOR_HERD
    ).all()
    due_for_herd = sum(l.total_kits for l in ready_litters)

    weeks: dict[tuple, list[Litter]] = defaultdict(list)
    for l in ready_litters:
        if l.actual_birth_date:
            weeks[iso_week_bounds(l.actual_birth_date)].append(l)

    kits_ready_for_transfer = []
    for (week_start, week_end), litters_in_week in sorted(weeks.items(), reverse=True):
        kits_ready_for_transfer.append(
            {
                "weekStart": week_start.isoformat(),
                "weekEnd": week_end.isoformat(),
                "label": f"Week of {week_start.strftime('%b %-d')}",
                "ageLabel": age_label(week_start),
                "totalKits": sum(l.total_kits for l in litters_in_week),
                "maleKits": sum(l.male_kits for l in litters_in_week),
                "femaleKits": sum(l.female_kits for l in litters_in_week),
                "litters": [
                    {"litterId": l.id, "damName": l.dam.name if l.dam else None, "totalKits": l.total_kits}
                    for l in litters_in_week
                ],
            }
        )

    groups_by_month: dict[int, list[HerdBatch]] = defaultdict(list)
    for b in batches:
        groups_by_month[age_months(b.week_start_date)].append(b)

    age_groups = []
    for months in sorted(groups_by_month.keys()):
        batches_in_group = groups_by_month[months]
        weight_range = "—"
        for b in batches_in_group:
            if b.litters and b.litters[0].dam and b.litters[0].dam.breed:
                breed = b.litters[0].dam.breed
                if breed.expected_weight_min_kg and breed.expected_weight_max_kg:
                    weight_range = f"{breed.expected_weight_min_kg} - {breed.expected_weight_max_kg} kg"
                    break

        age_groups.append(
            {
                "ageLabel": f"{months} Month{'s' if months != 1 else ''} Old",
                "expectedWeightRange": weight_range,
                "batches": [herd_batch_schema.dump(b) for b in batches_in_group],
            }
        )

    return jsonify(
        totalHerdSize=total_herd_size,
        activeGroups=active_groups,
        dueForHerd=due_for_herd,
        kitsReadyForTransfer=kits_ready_for_transfer,
        ageGroups=age_groups,
    )


@herd_bp.get("/batches/<int:batch_id>")
@farm_scoped
def get_batch_detail(farm_id: int, batch_id: int):
    batch = HerdBatch.query.filter_by(id=batch_id, farm_id=farm_id).first_or_404()
    return jsonify(herd_batch_schema.dump(batch))


@herd_bp.post("/batches/transfer")
@farm_scoped
def transfer_week_to_herd(farm_id: int):
    """
    The transfer-to-herd popup. Takes every litter being merged (born the same
    week, validated below), plus the combined male/female count and optional
    avg weight actually moving to herd right now.
    """
    data = parse_body(transfer_batch_schema)

    litters = Litter.query.filter(
        Litter.id.in_(data["litter_ids"]), Litter.farm_id == farm_id
    ).all()
    if len(litters) != len(data["litter_ids"]):
        return jsonify(message="One or more litters were not found on this farm."), 404
    if any(l.herd_batch_id is not None for l in litters):
        return jsonify(message="One or more of these litters have already been transferred."), 400
    if any(l.actual_birth_date is None for l in litters):
        return jsonify(message="Every litter being transferred needs a recorded birth date."), 400

    weeks = {iso_week_bounds(l.actual_birth_date) for l in litters}
    if len(weeks) > 1:
        return jsonify(message="All litters in one transfer must be born in the same week."), 400
    week_start, week_end = weeks.pop()

    batch = HerdBatch(
        farm_id=farm_id,
        label=f"Batch — Week of {week_start.strftime('%b %-d')}",
        week_start_date=week_start,
        week_end_date=week_end,
        male_count=data["male_count"],
        female_count=data["female_count"],
        avg_weight_kg=data.get("avg_weight_kg"),
    )
    db.session.add(batch)
    db.session.flush()

    for litter in litters:
        litter.herd_batch_id = batch.id
        litter.status = LitterStatus.TRANSFERRED_TO_HERD
        log_activity(
            litter_id=litter.id,
            activity_type=ActivityType.TRANSFER,
            title="Transferred to Herd",
            description=(
                f"Merged into {batch.label} alongside "
                f"{len(litters) - 1} other litter(s)." if len(litters) > 1
                else f"Moved into {batch.label}."
            ),
        )

    db.session.commit()
    return jsonify(herd_batch_schema.dump(batch)), 201


@herd_bp.patch("/batches/<int:batch_id>")
@farm_scoped
def edit_batch(farm_id: int, batch_id: int):
    """Corrects the counts/weight entered at transfer time — nothing there is locked in."""
    batch = HerdBatch.query.filter_by(id=batch_id, farm_id=farm_id).first_or_404()
    data = parse_body(edit_herd_batch_schema)

    if "male_count" in data:
        batch.male_count = data["male_count"]
    if "female_count" in data:
        batch.female_count = data["female_count"]
    if "avg_weight_kg" in data:
        batch.avg_weight_kg = data["avg_weight_kg"]

    db.session.commit()
    return jsonify(herd_batch_schema.dump(batch))


@herd_bp.post("/batches/<int:batch_id>/promote")
@farm_scoped
def promote_from_batch(farm_id: int, batch_id: int):
    """
    Pulls one individual out of a merged batch to keep for breeding. Since a batch
    can mix kits from several does, pedigree (dam/sire) is unknown for a
    batch-promoted individual — that's the honest trade-off of merging; it's
    called out on the new rabbit's activity log.
    """
    batch = HerdBatch.query.filter_by(id=batch_id, farm_id=farm_id).first_or_404()
    data = parse_body(promote_to_breeding_schema)
    sex = data["sex"]
    count_field = "male_count" if sex == "M" else "female_count"

    remaining = getattr(batch, count_field) or 0
    if remaining <= 0:
        return jsonify(message=f"No remaining {'male' if sex == 'M' else 'female'} kits in this batch."), 400
    setattr(batch, count_field, remaining - 1)

    new_rabbit = Rabbit(
        farm_id=farm_id,
        name=data["name"],
        role=RabbitRole.DOE if sex == "F" else RabbitRole.BUCK,
        status=RabbitStatus.ACTIVE,
        sex=sex,
        breed_id=data.get("breed_id"),
        section_id=data.get("section_id"),
        hatch_date=batch.week_start_date,  
    )
    db.session.add(new_rabbit)
    db.session.flush()

    log_activity(
        rabbit_id=new_rabbit.id,
        activity_type=ActivityType.STATUS_CHANGE,
        title="Promoted to breeding stock",
        description=(
            f"{data['name']} pulled from {batch.label}. Pedigree unknown — this batch "
            "merged kits from multiple does."
        ),
    )

    db.session.commit()
    return jsonify(rabbit_schema.dump(new_rabbit)), 201
