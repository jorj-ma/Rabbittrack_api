from datetime import datetime, timezone
from app import db


class HerdBatch(db.Model):
    """
    The thing that actually lives in the herd. A batch merges kits from every litter
    born in the same week (Monday-Sunday), possibly from several different does 
    """

    __tablename__ = "herd_batches"

    id                  = db.Column(db.Integer, primary_key=True)
    farm_id             = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    label               = db.Column(db.String(100))  # e.g. 'Batch — Week of Oct 9'
    week_start_date     = db.Column(db.Date, nullable=False)  # Monday of the birth week being merged
    week_end_date       = db.Column(db.Date, nullable=False)  # that Sunday

    male_count          = db.Column(db.Integer, nullable=False, default=0)
    female_count        = db.Column(db.Integer, nullable=False, default=0)
    avg_weight_kg       = db.Column(db.Numeric(5, 2))

    transferred_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at          = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    litters = db.relationship("Litter", back_populates="herd_batch")

    __table_args__ = (
        db.Index("idx_herd_batches_farm_week", "farm_id", "week_start_date"),
    )
