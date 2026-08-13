from marshmallow import fields, validate, EXCLUDE
from app import ma
from ..models import LitterStatus, MilestoneType


class LitterMilestoneSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    milestone = fields.Str(validate=validate.OneOf(MilestoneType.CHOICES))
    expectedDate = fields.Date(attribute="expected_date", allow_none=True)
    actualDate = fields.Date(attribute="actual_date", allow_none=True)
    completed = fields.Bool()


class LitterSchema(ma.Schema):

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    litterNumber = fields.Str(attribute="litter_number", allow_none=True)
    damId = fields.Int(attribute="dam_id", dump_only=True)
    damName = fields.Method("get_dam_name", dump_only=True)
    sireId = fields.Int(attribute="sire_id", allow_none=True)
    matingDate = fields.Date(attribute="mating_date", allow_none=True)
    expectedNestingDate = fields.Date(attribute="expected_nesting_date", dump_only=True)
    nestBoxAddedAt = fields.Date(attribute="nest_box_added_at", allow_none=True)
    expectedBirthDate = fields.Date(attribute="expected_birth_date", dump_only=True)
    expectedBirthDateLatest = fields.Date(attribute="expected_birth_date_latest", dump_only=True)
    actualBirthDate = fields.Date(attribute="actual_birth_date", allow_none=True)
    totalKits = fields.Int(attribute="total_kits", dump_only=True)
    maleKits = fields.Int(attribute="male_kits", dump_only=True)
    femaleKits = fields.Int(attribute="female_kits", dump_only=True)
    kitsSurvived = fields.Int(attribute="kits_survived", allow_none=True)
    status = fields.Str(validate=validate.OneOf(LitterStatus.CHOICES))
    sectionCode = fields.Method("get_section_code", dump_only=True)
    herdBatchId = fields.Int(attribute="herd_batch_id", dump_only=True, allow_none=True)
    milestones = fields.List(fields.Nested(LitterMilestoneSchema), dump_only=True)

    def get_dam_name(self, obj):
        return obj.dam.name if obj.dam else None

    def get_section_code(self, obj):
        return obj.section.code if obj.section else None


class LitterEditSchema(ma.Schema):
    """General-purpose edit for anything on a litter that isn't covered by a more specific
    action (mating/nest-box/birth/transfer each have their own endpoint and side effects)."""

    class Meta:
        unknown = EXCLUDE

    litterNumber = fields.Str(attribute="litter_number", allow_none=True)
    sectionId = fields.Int(attribute="section_id", allow_none=True)
    kitsSurvived = fields.Int(attribute="kits_survived", allow_none=True, validate=validate.Range(min=0))


class RecordMatingSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    sireId = fields.Int(attribute="sire_id", required=True)
    matingDate = fields.Date(attribute="mating_date", required=True)


class EditMatingSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    matingDate = fields.Date(attribute="mating_date", required=True)
    sireId = fields.Int(attribute="sire_id", allow_none=True)


class NestBoxSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    date = fields.Date(required=True)


class RecordBirthSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    actualBirthDate = fields.Date(attribute="actual_birth_date", required=True)
    totalKits = fields.Int(attribute="total_kits", required=True, validate=validate.Range(min=0))
    maleKits = fields.Int(attribute="male_kits", required=True, validate=validate.Range(min=0))
    femaleKits = fields.Int(attribute="female_kits", required=True, validate=validate.Range(min=0))


class PromoteToBreedingSchema(ma.Schema):
    """Pulls one individual out of a litter/herd batch to be tracked as breeding stock —
    creates a brand-new `rabbits` row and decrements the group's count by one."""

    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    sex = fields.Str(required=True, validate=validate.OneOf(["M", "F"]))
    breedId = fields.Int(attribute="breed_id", allow_none=True)
    sectionId = fields.Int(attribute="section_id", allow_none=True)


litter_schema = LitterSchema()
litters_schema = LitterSchema(many=True)
litter_edit_schema = LitterEditSchema()
record_mating_schema = RecordMatingSchema()
edit_mating_schema = EditMatingSchema()
nest_box_schema = NestBoxSchema()
record_birth_schema = RecordBirthSchema()
promote_to_breeding_schema = PromoteToBreedingSchema()
