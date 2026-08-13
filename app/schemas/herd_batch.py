from marshmallow import fields, validate, EXCLUDE
from app import ma


class HerdBatchSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    label = fields.Str(allow_none=True)
    weekStartDate = fields.Date(attribute="week_start_date", dump_only=True)
    weekEndDate = fields.Date(attribute="week_end_date", dump_only=True)
    maleCount = fields.Int(attribute="male_count", dump_only=True)
    femaleCount = fields.Int(attribute="female_count", dump_only=True)
    avgWeightKg = fields.Decimal(attribute="avg_weight_kg", allow_none=True, as_string=True)
    transferredAt = fields.DateTime(attribute="transferred_at", dump_only=True)
    # Which does/litters contributed — traceability only, not used for the batch's own counts.
    contributingLitters = fields.Method("get_contributing_litters", dump_only=True)

    def get_contributing_litters(self, obj):
        return [
            {"litterId": l.id, "litterNumber": l.litter_number, "damName": l.dam.name if l.dam else None}
            for l in obj.litters
        ]


class TransferBatchSchema(ma.Schema):
    """The transfer-to-herd popup. `litterIds` is every litter born in the same ISO week
    being merged together — possibly from different does. Counts entered here are the
    combined total actually moving to herd (may be lower than the litters' combined birth
    counts if any kits were lost) and are the batch's only record of "how many are here" —
    no per-mother breakdown is kept once merged."""

    class Meta:
        unknown = EXCLUDE

    litterIds = fields.List(fields.Int(), attribute="litter_ids", required=True, validate=validate.Length(min=1))
    maleCount = fields.Int(attribute="male_count", required=True, validate=validate.Range(min=0))
    femaleCount = fields.Int(attribute="female_count", required=True, validate=validate.Range(min=0))
    avgWeightKg = fields.Decimal(attribute="avg_weight_kg", allow_none=True, validate=validate.Range(min=0))


class EditHerdBatchSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    maleCount = fields.Int(attribute="male_count", allow_none=True, validate=validate.Range(min=0))
    femaleCount = fields.Int(attribute="female_count", allow_none=True, validate=validate.Range(min=0))
    avgWeightKg = fields.Decimal(attribute="avg_weight_kg", allow_none=True, validate=validate.Range(min=0))


herd_batch_schema = HerdBatchSchema()
herd_batches_schema = HerdBatchSchema(many=True)
transfer_batch_schema = TransferBatchSchema()
edit_herd_batch_schema = EditHerdBatchSchema()
