from flask import request, abort
from marshmallow import ValidationError


def parse_body(schema) -> dict:
    try:
        return schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        abort(400, description=err.messages)
