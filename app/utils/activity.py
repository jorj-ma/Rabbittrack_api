from flask import g
from app import db
from ..models import ActivityLog, WeightLog


def log_activity(*, rabbit_id=None, litter_id=None, activity_type, title, description=None, occurred_at=None) -> ActivityLog:
    entry = ActivityLog(
        farm_id=g.farm_id,
        rabbit_id=rabbit_id,
        litter_id=litter_id,
        activity_type=activity_type,
        title=title,
        description=description,
        occurred_at=occurred_at,
        recorded_by=g.user_id,
    )
    db.session.add(entry)
    return entry


def log_weight(*, rabbit_id, weight_kg, recorded_at=None, notes=None) -> WeightLog:
    entry = WeightLog(
        farm_id=g.farm_id,
        rabbit_id=rabbit_id,
        weight_kg=weight_kg,
        recorded_at=recorded_at,
        notes=notes,
        recorded_by=g.user_id,
    )
    db.session.add(entry)
    return entry
