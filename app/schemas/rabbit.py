from marshmallow import fields, validate, EXCLUDE
from app import ma
from ..models import RabbitRole, RabbitStatus


class RabbitSchema(ma.Schema):
    """Matches the frontend's `Rabbit` type in src/types/rabbit.ts exactly (camelCase)."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    farmId = fields.Int(attribute="farm_id", dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    role = fields.Str(validate=validate.OneOf(RabbitRole.CHOICES))
    status = fields.Str(validate=validate.OneOf(RabbitStatus.CHOICES))
    breedName = fields.Method("get_breed_name", dump_only=True)
    sex = fields.Str(validate=validate.OneOf(["M", "F"]))
    damId = fields.Int(attribute="dam_id", allow_none=True)
    sireId = fields.Int(attribute="sire_id", allow_none=True)
    litterId = fields.Int(attribute="litter_id", allow_none=True)
    hatchDate = fields.Date(attribute="hatch_date", allow_none=True)
    sectionCode = fields.Method("get_section_code", dump_only=True)
    currentWeightKg = fields.Decimal(attribute="current_weight_kg", allow_none=True, as_string=True)
    colorTag = fields.Str(attribute="color_tag", allow_none=True)

    def get_breed_name(self, obj):
        return obj.breed.name if obj.breed else None

    def get_section_code(self, obj):
        return obj.section.code if obj.section else None


class RabbitCreateSchema(ma.Schema):
    """Input validation for POST /does, POST /bucks."""

    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    sex = fields.Str(required=True, validate=validate.OneOf(["M", "F"]))
    breedId = fields.Int(attribute="breed_id", allow_none=True)
    sectionId = fields.Int(attribute="section_id", allow_none=True)
    hatchDate = fields.Date(attribute="hatch_date", allow_none=True)
    damId = fields.Int(attribute="dam_id", allow_none=True)
    sireId = fields.Int(attribute="sire_id", allow_none=True)
    colorTag = fields.Str(attribute="color_tag", allow_none=True)


class RabbitUpdateSchema(RabbitCreateSchema):

    name = fields.Str(validate=validate.Length(min=1, max=100))
    sex = fields.Str(validate=validate.OneOf(["M", "F"]))
    status = fields.Str(validate=validate.OneOf(RabbitStatus.CHOICES))
    currentWeightKg = fields.Decimal(attribute="current_weight_kg", allow_none=True, as_string=True)


rabbit_schema = RabbitSchema()
rabbits_schema = RabbitSchema(many=True)
rabbit_create_schema = RabbitCreateSchema()
rabbit_update_schema = RabbitUpdateSchema()
