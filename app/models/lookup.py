from app import db


class Breed(db.Model):
    __tablename__ = "breeds"
    __table_args__ = (db.UniqueConstraint("farm_id", "name", name="uq_breed_farm_name"),)

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(
        db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=True
    )  # NULL = global/shared breed available to every farm
    name = db.Column(db.String(100), nullable=False)
    expected_weight_min_kg = db.Column(db.Numeric(5, 2))
    expected_weight_max_kg = db.Column(db.Numeric(5, 2))
    notes = db.Column(db.Text)

    rabbits = db.relationship("Rabbit", back_populates="breed")


class Section(db.Model):
    __tablename__ = "sections"
    __table_args__ = (db.UniqueConstraint("farm_id", "code", name="uq_section_farm_code"),)

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    code = db.Column(db.String(20), nullable=False)  # 'A-1', 'B-2'
    capacity = db.Column(db.Integer)
    notes = db.Column(db.Text)

    rabbits = db.relationship("Rabbit", back_populates="section")
    litters = db.relationship("Litter", back_populates="section")
