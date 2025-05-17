# This file makes 'app' a Python package.
from flask import Flask
from app.extensions import db, migrate
from config_postgres import config
from flask_cors import CORS

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize CORS:
    CORS(app, resources={
        r"/uploads/*": {"origins": "*"},
        r"/jd/*": {"origins": "*"},
        r"/analysis/*": {"origins": "*"}
    }, supports_credentials=True)
    
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
