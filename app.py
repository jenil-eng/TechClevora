import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from models import db, User, Resume, InterviewSession, InterviewQuestion, PerformanceReport, Company, Notification, Feedback

def create_app(config=None):
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Enable CORS for external testing or SPA development
    CORS(app)
    
    # Configure SQLite Database
    db_path = os.path.join(os.path.dirname(__file__), 'techclevora.db')
    if not os.path.exists(db_path):
        legacy_db = os.path.join(os.path.dirname(__file__), 'meetai.db')
        if os.path.exists(legacy_db):
            db_path = legacy_db
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path.replace(os.sep, '/')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    if config:
        app.config.update(config)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'timeout': 15
        }
    }
    
    # Maximum file upload size: 16 Megabytes
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Initialize DB
    db.init_app(app)
    
    # Register Blueprints
    from routes.auth import auth_bp
    from routes.api import api_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Main SPA endpoint
    @app.route('/')
    @app.route('/dashboard')
    @app.route('/login')
    @app.route('/register')
    @app.route('/features')
    @app.route('/pricing')
    @app.route('/contact')
    @app.route('/resume-analyzer')
    @app.route('/interview-prep')
    @app.route('/career-roadmap')
    @app.route('/resume-builder')
    @app.route('/admin-panel')
    def index():
        return render_template('index.html')
        
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        # Fallback to SPA router
        return render_template('index.html')

    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        from datetime import datetime
        try:
            with open('error.log', 'a') as f:
                f.write(f"--- ERROR AT {datetime.utcnow()} ---\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception as log_err:
            print(f"Failed to write to error.log: {log_err}")
        return jsonify({'message': f'Internal Server Error: {str(e)}'}), 500


    # Automatically create tables & safely migrate schema
    from models import migrate_database
    migrate_database(app)
        
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
