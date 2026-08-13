from flask import Blueprint, jsonify

from app import db
from ..models import Rabbit, RabbitStatus, ActivityType
from ..schemas import rabbit_schema, weight_log_schema, activity_log_schema, add_weight_schema, add_activity_schema
from ..utils.auth import farm_scoped
from ..utils.validation import parse_body
from ..utils.activity import log_activity, log_weight

rabbits_bp = Blueprint("rabbits", __name__)


@rabbits_bp.post("/<int:rabbit_id>/weight")
@farm_scoped
def add_weight(farm_id: int, rabbit_id: int):
    rabbit = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id).first_or_404()
    data = parse_body(add_weight_schema)

    entry = log_weight(rabbit_id=rabbit.id, weight_kg=data["weight_kg"])
    rabbit.current_weight_kg = data["weight_kg"]  # keep the denormalized cache in sync

    db.session.commit()
    return jsonify(weight_log_schema.dump(entry)), 201


@rabbits_bp.post("/<int:rabbit_id>/activity")
@farm_scoped
def add_activity(farm_id: int, rabbit_id: int):
    rabbit = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id).first_or_404()
    data = parse_body(add_activity_schema)

    entry = log_activity(
        rabbit_id=rabbit.id,
        activity_type=ActivityType.HEALTH_NOTE,
        title=data["title"],
        description=data.get("description"),
    )

    db.session.commit()
    return jsonify(activity_log_schema.dump(entry)), 201


@rabbits_bp.post("/<int:rabbit_id>/sell")
@farm_scoped
def sell_rabbit(farm_id: int, rabbit_id: int):
    rabbit = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id).first_or_404()
    rabbit.status = RabbitStatus.SOLD

    log_activity(rabbit_id=rabbit.id, activity_type=ActivityType.SALE, title="Sold")

    db.session.commit()
    return jsonify(rabbit_schema.dump(rabbit))


@rabbits_bp.post("/<int:rabbit_id>/mark-deceased")
@farm_scoped
def mark_deceased(farm_id: int, rabbit_id: int):
    rabbit = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id).first_or_404()
    rabbit.status = RabbitStatus.DECEASED

    log_activity(rabbit_id=rabbit.id, activity_type=ActivityType.STATUS_CHANGE, title="Marked deceased")

    db.session.commit()
    return jsonify(rabbit_schema.dump(rabbit))
