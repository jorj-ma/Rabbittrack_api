from datetime import date
from flask import Blueprint, jsonify

from ..models import Rabbit, RabbitRole, Litter, LitterStatus, HerdBatch
from ..utils.auth import farm_scoped
from ..utils.dates import age_label

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("")
@farm_scoped
def get_dashboard(farm_id: int):
    """
    One route, one payload for the whole Dashboard screen.

    Kits are tracked as a group only (no individual `rabbits` rows), so the
    totals here are a mix of individual-row counts (does, bucks)"""
    does = Rabbit.query.filter(Rabbit.farm_id == farm_id, Rabbit.role == RabbitRole.DOE).count()
    bucks = Rabbit.query.filter(Rabbit.farm_id == farm_id, Rabbit.role == RabbitRole.BUCK).count()

    growing_litters = Litter.query.filter(
        Litter.farm_id == farm_id,
        Litter.status.in_([LitterStatus.NURSING, LitterStatus.WEANING, LitterStatus.READY_FOR_HERD]),
    ).all()
    kits = sum(l.total_kits for l in growing_litters)

    batches = HerdBatch.query.filter_by(farm_id=farm_id).all()
    herd = sum(b.male_count + b.female_count for b in batches)

    total_rabbits = does + bucks + kits + herd

    active_litters = sorted(growing_litters, key=lambda l: l.actual_birth_date or date.min, reverse=True)[:10]
    active_kit_groups = [
        {
            "litterId": litter.id,
            "label": litter.litter_number or f"Litter #{litter.id}",
            "damName": litter.dam.name if litter.dam else None,
            "totalKits": litter.total_kits,
            "bornAt": litter.actual_birth_date.isoformat() if litter.actual_birth_date else None,
            "ageLabel": age_label(litter.actual_birth_date) if litter.actual_birth_date else "—",
        }
        for litter in active_litters
    ]

    return jsonify(
        totals={"rabbits": total_rabbits, "does": does, "bucks": bucks, "herd": herd, "kits": kits},
        activeKitGroups=active_kit_groups,
    )
