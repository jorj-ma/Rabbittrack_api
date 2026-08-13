from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_cors import CORS


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()
cors = CORS()


def create_app(config_class = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

    with app.app_context():
        from . import models 

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.does import does_bp
    from .routes.bucks import bucks_bp
    from .routes.herd import herd_bp
    from .routes.litters import litters_bp
    from .routes.rabbits import rabbits_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(
        dashboard_bp, url_prefix="/farms/<int:farm_id>/dashboard"
    )
    app.register_blueprint(does_bp, url_prefix="/farms/<int:farm_id>/does")
    app.register_blueprint(bucks_bp, url_prefix="/farms/<int:farm_id>/bucks")
    app.register_blueprint(herd_bp, url_prefix="/farms/<int:farm_id>/herd")
    app.register_blueprint(litters_bp, url_prefix="/farms/<int:farm_id>/litters")
    app.register_blueprint(rabbits_bp, url_prefix="/farms/<int:farm_id>/rabbits")
    app.register_blueprint(admin_bp, url_prefix="/farms/<int:farm_id>")

    from .errors import register_error_handlers
    register_error_handlers(app)

    @app.get("/health")
    def health():
        return {"status": "ok",
                "message": "RabbitTrack backend is running.",
                "version": "1.0.0"}, 200

    return app
