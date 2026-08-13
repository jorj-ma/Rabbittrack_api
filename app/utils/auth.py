from functools import wraps
from flask import g, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from ..models import FarmUser


def farm_scoped(fn):
    @wraps(fn)
    def wrapper(*args, farm_id: int, **kwargs):
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())

        membership = FarmUser.query.filter_by(farm_id=farm_id, user_id=user_id).first()
        if membership is None:
            abort(403, description="You don't have access to this farm.")

        g.farm_id = farm_id
        g.user_id = user_id
        g.farm_role = membership.role
        return fn(*args, farm_id=farm_id, **kwargs)

    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if g.farm_role != "admin":
            abort(403, description="This action requires an admin account.")
        return fn(*args, **kwargs)

    return wrapper
