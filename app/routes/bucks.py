from flask import Blueprint, jsonify

from app import db
from ..models import Rabbit, RabbitRole, RabbitStatus
from ..schemas import rabbit_schema, rabbits_schema, rabbit_create_schema, rabbit_update_schema
from ..utils.auth import farm_scoped
from ..utils.validation import parse_body

bucks_bp = Blueprint("bucks", __name__)


@bucks_bp.get("")
@farm_scoped
def list_bucks(farm_id: int):
    bucks = (
        Rabbit.query.filter(Rabbit.farm_id == farm_id, Rabbit.role == RabbitRole.BUCK)
        .order_by(Rabbit.name)
        .all()
    )
    return jsonify(rabbits_schema.dump(bucks))


@bucks_bp.get("/<int:rabbit_id>")
@farm_scoped
def get_buck(farm_id: int, rabbit_id: int):
    buck = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id, role=RabbitRole.BUCK).first_or_404()
    return jsonify(rabbit_schema.dump(buck))


@bucks_bp.post("")
@farm_scoped
def create_buck(farm_id: int):
    data = parse_body(rabbit_create_schema)
    buck = Rabbit(farm_id=farm_id, role=RabbitRole.BUCK, status=RabbitStatus.ACTIVE, **data)
    db.session.add(buck)
    db.session.commit()
    return jsonify(rabbit_schema.dump(buck)), 201


@bucks_bp.patch("/<int:rabbit_id>")
@farm_scoped
def update_buck(farm_id: int, rabbit_id: int):
    buck = Rabbit.query.filter_by(id=rabbit_id, farm_id=farm_id, role=RabbitRole.BUCK).first_or_404()
    data = parse_body(rabbit_update_schema)
    for key, value in data.items():
        setattr(buck, key, value)
    db.session.commit()
    return jsonify(rabbit_schema.dump(buck))
