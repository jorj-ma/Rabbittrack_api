import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class FarmRole:
    ADMIN = "admin"
    USER = "user"
    CHOICES = [ADMIN, USER]


def generate_farm_code() -> str:
    return secrets.token_hex(4)


class Farm(db.Model):
    __tablename__ = "farms"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    code            = db.Column(db.String(20), nullable=False, unique=True)  # used at login, alongside email+password
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    memberships = db.relationship("FarmUser", back_populates="farm", cascade="all, delete-orphan")
    invites     = db.relationship("FarmInvite", back_populates="farm", cascade="all, delete-orphan")


class User(db.Model):
    __tablename__ = "users"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    email           = db.Column(db.String(255), nullable=False, unique=True)
    password_hash   = db.Column(db.Text, nullable=False)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    memberships = db.relationship("FarmUser", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class FarmUser(db.Model):

    __tablename__ = "farm_users"

    farm_id     = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role        = db.Column(db.Enum(*FarmRole.CHOICES, name="farm_role"), nullable=False, default=FarmRole.USER)
    joined_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    farm = db.relationship("Farm", back_populates="memberships")
    user = db.relationship("User", back_populates="memberships")


class FarmInvite(db.Model):

    __tablename__ = "farm_invites"

    id              = db.Column(db.Integer, primary_key=True)
    farm_id         = db.Column(db.Integer, db.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    email           = db.Column(db.String(255), nullable=False)
    role            = db.Column(db.Enum(*FarmRole.CHOICES, name="farm_role"), nullable=False, default=FarmRole.USER)
    token_hash      = db.Column(db.Text, nullable=False)
    invited_by      = db.Column(db.Integer, db.ForeignKey("users.id"))
    expires_at      = db.Column(db.DateTime, nullable=False)
    accepted_at     = db.Column(db.DateTime)
    cancelled_at    = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    farm = db.relationship("Farm", back_populates="invites")
    inviter = db.relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
              db.Index(
            "uq_farm_invites_pending", "farm_id", "email",
            unique=True,
            postgresql_where=db.text("accepted_at IS NULL AND cancelled_at IS NULL"),
        ),
    )

    def set_token(self, raw_token: str) -> None:
        self.token_hash = generate_password_hash(raw_token)

    def check_token(self, raw_token: str) -> bool:
        return check_password_hash(self.token_hash, raw_token)

    @property
    def is_redeemable(self) -> bool:
        return (
            self.accepted_at is None
            and self.cancelled_at is None
            and self.expires_at > datetime.now(timezone.utc)
        )
