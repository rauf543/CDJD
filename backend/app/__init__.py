# This file makes 'app' a Python package.
from flask import Flask
from app.extensions import db, migrate
from config_postgres import config

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.uploads import uploads_bp
    from app.routes.jd_routes import jd_bp
    from app.routes.analysis_routes import analysis_bp
    
    app.register_blueprint(uploads_bp, url_prefix='/uploads')
    app.register_blueprint(jd_bp, url_prefix='/jd')
    app.register_blueprint(analysis_bp, url_prefix='/analysis')
    
    return app
