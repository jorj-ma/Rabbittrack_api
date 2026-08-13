from marshmallow import fields, validate, EXCLUDE
from app import ma
from ..models import ActivityType


class ActivityLogSchema(ma.Schema):
    """Matches the frontend's `ActivityLogEntry` type."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    activityType = fields.Str(attribute="activity_type", validate=validate.OneOf(ActivityType.CHOICES))
    title = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    description = fields.Str(allow_none=True)
    occurredAt = fields.Date(attribute="occurred_at", dump_only=True)
    recordedByName = fields.Method("get_recorded_by_name", dump_only=True)

    def get_recorded_by_name(self, obj):
        return obj.recorded_by_user.name if obj.recorded_by_user else None


class WeightLogSchema(ma.Schema):
    """Matches the frontend's `WeightLogEntry` type."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    weightKg = fields.Decimal(attribute="weight_kg", required=True, as_string=True)
    recordedAt = fields.Date(attribute="recorded_at", dump_only=True)
    recordedByName = fields.Method("get_recorded_by_name", dump_only=True)

    def get_recorded_by_name(self, obj):
        return obj.recorded_by_user.name if obj.recorded_by_user else None


class AddWeightSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    weightKg = fields.Decimal(attribute="weight_kg", required=True, validate=validate.Range(min=0))


class AddActivitySchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    description = fields.Str(allow_none=True)


activity_log_schema = ActivityLogSchema()
activity_logs_schema = ActivityLogSchema(many=True)
weight_log_schema = WeightLogSchema()
weight_logs_schema = WeightLogSchema(many=True)
add_weight_schema = AddWeightSchema()
add_activity_schema = AddActivitySchema()
