from marshmallow import fields, EXCLUDE
from app import ma


class BreedSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    expectedWeightMinKg = fields.Decimal(attribute="expected_weight_min_kg", allow_none=True, as_string=True)
    expectedWeightMaxKg = fields.Decimal(attribute="expected_weight_max_kg", allow_none=True, as_string=True)
    notes = fields.Str(allow_none=True)


class SectionSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    code = fields.Str(required=True)
    capacity = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)


breed_schema = BreedSchema()
breeds_schema = BreedSchema(many=True)
section_schema = SectionSchema()
sections_schema = SectionSchema(many=True)
