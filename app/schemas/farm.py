from marshmallow import fields, validate, EXCLUDE
from app import ma
from ..models import FarmRole


class CreateInviteSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    email = fields.Email(required=True)
    role = fields.Str(required=True, validate=validate.OneOf(FarmRole.CHOICES))


class UpdateFarmUserSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(validate=validate.Length(min=1, max=150))
    role = fields.Str(validate=validate.OneOf(FarmRole.CHOICES))


create_invite_schema = CreateInviteSchema()
update_farm_user_schema = UpdateFarmUserSchema()
