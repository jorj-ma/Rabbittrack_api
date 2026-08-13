from marshmallow import fields, validate, EXCLUDE
from app import ma


class SignupSchema(ma.Schema):
    """Creates a brand-new farm plus its first user, who becomes that farm's admin."""

    class Meta:
        unknown = EXCLUDE

    farmName = fields.Str(attribute="farm_name", required=True, validate=validate.Length(min=1, max=150))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))


class LoginSchema(ma.Schema):
    """Every user signs in with email + password + farmCode now."""

    class Meta:
        unknown = EXCLUDE

    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))
    farmCode = fields.Str(attribute="farm_code", required=True)


class AcceptInviteSchema(ma.Schema):
    """Completes signup for someone an admin invited — sets their own password."""

    class Meta:
        unknown = EXCLUDE

    token = fields.Str(required=True)
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    password = fields.Str(required=True, validate=validate.Length(min=8))


signup_schema = SignupSchema()
login_schema = LoginSchema()
accept_invite_schema = AcceptInviteSchema()
