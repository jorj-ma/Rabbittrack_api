from datetime import datetime, timezone, date
from app import db


class WeightLog(db.Model):
    __tablename__ = "weight_logs"
    __table_args__ = (db.Index("idx_weight_logs_rabbit_date", "rabbit_id", "recorded_at"),)

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    rabbit_id = db.Column(
        db.Integer, db.ForeignKey("rabbits.id", ondelete="CASCADE"), nullable=False
    )
    weight_kg = db.Column(db.Numeric(5, 2), nullable=False)
    recorded_at = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    rabbit = db.relationship("Rabbit", back_populates="weight_logs")
    recorded_by_user = db.relationship("User", foreign_keys=[recorded_by])


class ActivityType:
    WEIGHT_CHECK = "weight_check"
    ROUTINE_CHECKUP = "routine_checkup"
    MATING_EVENT = "mating_event"
    NEST_BOX_ADDED = "nest_box_added"
    BIRTH = "birth"
    TRANSFER = "transfer"
    HEALTH_NOTE = "health_note"
    STATUS_CHANGE = "status_change"
    SALE = "sale"
    CHOICES = [
        WEIGHT_CHECK, ROUTINE_CHECKUP, MATING_EVENT, NEST_BOX_ADDED,
        BIRTH, TRANSFER, HEALTH_NOTE, STATUS_CHANGE, SALE,
    ]


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    __table_args__ = (
        db.Index("idx_activity_rabbit", "rabbit_id", "occurred_at"),
        db.CheckConstraint(
            "rabbit_id IS NOT NULL OR litter_id IS NOT NULL", name="ck_activity_has_subject"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    rabbit_id = db.Column(db.Integer, db.ForeignKey("rabbits.id", ondelete="CASCADE"))
    litter_id = db.Column(db.Integer, db.ForeignKey("litters.id", ondelete="CASCADE"))

    activity_type = db.Column(db.Enum(*ActivityType.CHOICES, name="activity_type"), nullable=False)
    title = db.Column(db.String(150), nullable=False)  # 'Mating Event'
    description = db.Column(db.Text)
    occurred_at = db.Column(db.Date, nullable=False, default=date.today)

    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    rabbit = db.relationship("Rabbit", back_populates="activity_logs")
    litter = db.relationship("Litter", back_populates="activity_logs")
    recorded_by_user = db.relationship("User", foreign_keys=[recorded_by])
