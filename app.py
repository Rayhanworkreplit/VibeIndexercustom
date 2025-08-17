import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///indexer.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    import routes
    # Routes are imported in routes.py
    
    # Register backlink indexer blueprint
    from backlink_routes import backlink_bp
    app.register_blueprint(backlink_bp)
    
    # Create all tables
    db.create_all()
    
    # Initialize default settings if not exists
    from models import Settings
    import json
    
    if not Settings.query.first():
        default_settings = Settings()
        default_settings.site_url = "https://example.com"
        default_settings.gsc_property_url = "https://example.com"
        default_settings.max_crawl_rate = 50
        default_settings.sitemap_max_urls = 50000
        default_settings.crawl_delay = 2.0
        default_settings.auto_submit_sitemaps = True
        default_settings.alert_on_deindex = True
        # Set default advanced settings
        default_advanced = {
            'indexing_strategy': 'balanced',
            'enable_backlink_indexing': True,
            'retry_failed_urls': 'auto',
            'detailed_logging': False
        }
        default_settings.advanced_settings = json.dumps(default_advanced)
        db.session.add(default_settings)
        db.session.commit()
        print("Created default settings with advanced options")
