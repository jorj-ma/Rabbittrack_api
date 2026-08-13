from datetime import datetime, timezone
from app import db


class RabbitRole:
    DOE = "doe"
    BUCK = "buck"
    KIT = "kit"
    CHOICES = [DOE, BUCK, KIT]


class RabbitStatus:
    ACTIVE = "active"
    PREGNANT = "pregnant"
    NURSING = "nursing"
    RESTING = "resting"
    AVAILABLE = "available"
    GROWING = "growing"
    READY_FOR_HERD = "ready_for_herd"
    FOR_SALE = "for_sale"
    SOLD = "sold"
    TRANSFERRED = "transferred"
    DECEASED = "deceased"
    CHOICES = [
        ACTIVE, PREGNANT, NURSING, RESTING, AVAILABLE, GROWING,
        READY_FOR_HERD, FOR_SALE, SOLD, TRANSFERRED, DECEASED,
    ]


class Rabbit(db.Model):
    __tablename__ = "rabbits"

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(*RabbitRole.CHOICES, name="rabbit_role"), nullable=False)
    status = db.Column(
        db.Enum(*RabbitStatus.CHOICES, name="rabbit_status"),
        nullable=False,
        default=RabbitStatus.ACTIVE,
    )
    breed_id = db.Column(db.Integer, db.ForeignKey("breeds.id"))
    sex = db.Column(db.String(1))  # 'M' or 'F'

    # Pedigree — self-referencing, nullable for founder stock with no recorded parents
    dam_id = db.Column(db.Integer, db.ForeignKey("rabbits.id"))
    sire_id = db.Column(db.Integer, db.ForeignKey("rabbits.id"))
    litter_id = db.Column(db.Integer, db.ForeignKey("litters.id"))

    hatch_date = db.Column(db.Date)  # this animal's own birth date
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"))

    current_weight_kg = db.Column(db.Numeric(5, 2))  # cache of latest weight_logs entry
    color_tag = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    breed = db.relationship("Breed", back_populates="rabbits")
    section = db.relationship("Section", back_populates="rabbits")

    # Only meaningful for does/bucks that were specifically pulled out of a litter to be kept
    # for breeding — general kit siblings are never given rows.
    dam = db.relationship("Rabbit", remote_side=[id], foreign_keys=[dam_id], backref="promoted_kits_as_dam")
    sire = db.relationship("Rabbit", remote_side=[id], foreign_keys=[sire_id], backref="promoted_kits_as_sire")

    litter = db.relationship(
        "Litter", back_populates="promoted_individuals", foreign_keys=[litter_id]
    )

    weight_logs = db.relationship(
        "WeightLog", back_populates="rabbit", cascade="all, delete-orphan",
        order_by="WeightLog.recorded_at.desc()",
    )
    activity_logs = db.relationship(
        "ActivityLog", back_populates="rabbit", cascade="all, delete-orphan",
        order_by="ActivityLog.occurred_at.desc()",
    )

    __table_args__ = (
        db.Index("idx_rabbits_farm_role_status", "farm_id", "role", "status"),
        db.Index("idx_rabbits_dam", "dam_id"),
        db.Index("idx_rabbits_litter", "litter_id"),
    )
