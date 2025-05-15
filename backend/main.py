from flask import Flask
from flask_cors import CORS

from config import Config
from app.extensions import db, migrate # Import from extensions
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app) # Initialize db from extensions
    migrate.init_app(app, db) # Initialize migrate from extensions

    upload_folder = app.config["UPLOAD_FOLDER"]
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Import and register blueprints AFTER db and migrate are initialized and app context is available for them
    with app.app_context():
        from app.routes.uploads import bp as uploads_bp
        app.register_blueprint(uploads_bp, url_prefix="/api/v1/uploads")

        from app.routes.analysis_routes import bp as analysis_bp
        app.register_blueprint(analysis_bp, url_prefix="/api/v1/analysis")

        from app.routes.jd_routes import bp as jd_routes_bp  # Import the new JD routes blueprint
        app.register_blueprint(jd_routes_bp, url_prefix="/api/v1/jd") # Register it
        
        # Import models here to ensure they are registered with SQLAlchemy AFTER db is initialized
        # and within app_context if they rely on app.config or db directly at import time (though ideally they shouldn\'t)
        from app import models 

    @app.route("/health")
    def health_check():
        return "OK", 200

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all() # Create tables if they don\'t exist
    app.run(host="0.0.0.0", port=5000, debug=True)

