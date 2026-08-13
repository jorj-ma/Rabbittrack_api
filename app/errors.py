"""
Registers JSON error handlers so every error response — validation failures,
auth failures, 404s, JWT errors, unhandled exceptions — matches the single
{"message": ...} shape documented in the README, instead of Flask's default
HTML error pages or Flask-JWT-Extended's own {"msg": ...} shape.
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException

from app import jwt


def register_error_handlers(app) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        # marshmallow ValidationError.messages (a dict) is passed straight through
        # as the description on 400s raised via `abort(400, description=...)`.
        message = e.description if e.description else e.name
        return jsonify(message=message), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        app.logger.exception(e)
        return jsonify(message="Internal server error."), 500

    @jwt.unauthorized_loader
    def missing_token(reason: str):
        return jsonify(message="Authentication required."), 401

    @jwt.invalid_token_loader
    def invalid_token(reason: str):
        return jsonify(message="Invalid or malformed token."), 422

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify(message="Session expired — please sign in again."), 401

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return jsonify(message="This session has been revoked."), 401
