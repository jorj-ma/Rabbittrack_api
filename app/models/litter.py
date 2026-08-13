from datetime import datetime, timezone
from app import db


class LitterStatus:
    MATING_RECORDED = "mating_recorded"
    EXPECTING = "expecting"
    NESTING = "nesting"
    BORN = "born"
    NURSING = "nursing"
    WEANING = "weaning"
    READY_FOR_HERD = "ready_for_herd"
    TRANSFERRED_TO_HERD = "transferred_to_herd"
    CHOICES = [
        MATING_RECORDED, EXPECTING, NESTING, BORN,
        NURSING, WEANING, READY_FOR_HERD, TRANSFERRED_TO_HERD,
    ]


class MilestoneType:
    BIRTH = "birth"
    EYES_OPEN = "eyes_open"
    EATING_SOLIDS = "eating_solids"
    READY_FOR_HERD = "ready_for_herd"
    CHOICES = [BIRTH, EYES_OPEN, EATING_SOLIDS, READY_FOR_HERD]

    DAY_OFFSETS = {BIRTH: 0, EYES_OPEN: 10, EATING_SOLIDS: 21, READY_FOR_HERD: 30}


class Litter(db.Model):
    __tablename__ = "litters"
    __table_args__ = (
        db.UniqueConstraint("farm_id", "litter_number", name="uq_litter_farm_number"),
        db.Index("idx_litters_farm_dam", "farm_id", "dam_id"),
        db.Index("idx_litters_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    litter_number = db.Column(db.String(20))  # 'Litter #42'
    dam_id = db.Column(db.Integer, db.ForeignKey("rabbits.id"), nullable=False)
    sire_id = db.Column(db.Integer, db.ForeignKey("rabbits.id"))

    mating_date = db.Column(db.Date)
    expected_nesting_date = db.Column(db.Date)  # auto: mating_date + 26 days
    nest_box_added_at = db.Column(db.Date)  # actual: when the nest box was introduced
    expected_birth_date = db.Column(db.Date)  # auto: mating_date + 28 days (early bound)
    expected_birth_date_latest = db.Column(db.Date)  # auto: mating_date + 35 days (late bound)
    actual_birth_date = db.Column(db.Date)

    total_kits = db.Column(db.Integer, nullable=False, default=0)  # entered directly at birth
    male_kits = db.Column(db.Integer, nullable=False, default=0)
    female_kits = db.Column(db.Integer, nullable=False, default=0)
    kits_survived = db.Column(db.Integer)  # optional; not auto-derived from batch transfer — see herd_batches


    herd_batch_id = db.Column(db.Integer, db.ForeignKey("herd_batches.id"))

    status = db.Column(
        db.Enum(*LitterStatus.CHOICES, name="litter_status"),
        nullable=False,
        default=LitterStatus.MATING_RECORDED,
    )
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    dam = db.relationship("Rabbit", foreign_keys=[dam_id])
    sire = db.relationship("Rabbit", foreign_keys=[sire_id])
    section = db.relationship("Section", back_populates="litters")
    herd_batch = db.relationship("HerdBatch", back_populates="litters")


    promoted_individuals = db.relationship(
        "Rabbit", back_populates="litter", foreign_keys="Rabbit.litter_id"
    )
    milestones = db.relationship(
        "LitterMilestone", back_populates="litter", cascade="all, delete-orphan",
        order_by="LitterMilestone.expected_date",
    )
    activity_logs = db.relationship(
        "ActivityLog", back_populates="litter", cascade="all, delete-orphan"
    )


class LitterMilestone(db.Model):
    __tablename__ = "litter_milestones"
    __table_args__ = (
        db.UniqueConstraint("litter_id", "milestone", name="uq_milestone_per_litter"),
    )

    id = db.Column(db.Integer, primary_key=True)
    litter_id = db.Column(
        db.Integer, db.ForeignKey("litters.id", ondelete="CASCADE"), nullable=False
    )
    milestone = db.Column(db.Enum(*MilestoneType.CHOICES, name="milestone_type"), nullable=False)
    expected_date = db.Column(db.Date)
    actual_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, nullable=False, default=False)

    litter = db.relationship("Litter", back_populates="milestones")
