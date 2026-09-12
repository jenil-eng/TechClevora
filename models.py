from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    profile_pic = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = db.relationship('Resume', backref='user', lazy=True, cascade="all, delete-orphan")
    interviews = db.relationship('InterviewSession', backref='user', lazy=True, cascade="all, delete-orphan")
    reports = db.relationship('PerformanceReport', backref='user', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    bulk_jobs = db.relationship('BulkJob', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'profile_pic': self.profile_pic,
            'created_at': self.created_at.isoformat()
        }

class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bulk_job_id = db.Column(db.Integer, db.ForeignKey('bulk_jobs.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=True)
    file_hash = db.Column(db.String(64), nullable=True, index=True)
    analysis_version = db.Column(db.String(30), default='v2')
    job_role = db.Column(db.String(100), nullable=True)
    target_job_description = db.Column(db.Text, nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)
    
    # Parsed candidate details
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    linkedin = db.Column(db.String(255), nullable=True)
    github = db.Column(db.String(255), nullable=True)
    portfolio = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(150), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    
    # Structured resume metadata stored as JSON
    skills_json = db.Column(db.Text, nullable=True)        # Categorized or list of skills
    education_json = db.Column(db.Text, nullable=True)     # Education history
    experience_json = db.Column(db.Text, nullable=True)    # Work experience
    projects_json = db.Column(db.Text, nullable=True)      # Project portfolio
    certifications_json = db.Column(db.Text, nullable=True)# Certifications
    achievements_json = db.Column(db.Text, nullable=True)  # Achievements & awards
    
    # Deterministic and AI scores
    ats_score = db.Column(db.Integer, default=0)
    resume_score = db.Column(db.Integer, default=0)
    score_breakdown_json = db.Column(db.Text, nullable=True)
    
    # Semantic analysis results
    analysis_json = db.Column(db.Text, nullable=True)      # Strengths, weaknesses, suggestions, etc.
    
    processing_status = db.Column(db.String(30), default='completed') # pending, processing, completed, failed
    processing_error = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        def _safe_json(val, default):
            if not val:
                return default
            try:
                return json.loads(val)
            except Exception:
                return default

        return {
            'id': self.id,
            'user_id': self.user_id,
            'bulk_job_id': self.bulk_job_id,
            'filename': self.filename,
            'file_hash': self.file_hash,
            'analysis_version': self.analysis_version,
            'job_role': self.job_role,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'linkedin': self.linkedin,
            'github': self.github,
            'portfolio': self.portfolio,
            'title': self.title,
            'summary': self.summary,
            'skills': _safe_json(self.skills_json, []),
            'education': _safe_json(self.education_json, []),
            'experience': _safe_json(self.experience_json, []),
            'projects': _safe_json(self.projects_json, []),
            'certifications': _safe_json(self.certifications_json, []),
            'achievements': _safe_json(self.achievements_json, []),
            'ats_score': self.ats_score,
            'resume_score': self.resume_score,
            'score_breakdown': _safe_json(self.score_breakdown_json, {}),
            'analysis': _safe_json(self.analysis_json, {}),
            'processing_status': self.processing_status,
            'processing_error': self.processing_error,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class InterviewSession(db.Model):
    __tablename__ = 'interview_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    experience_level = db.Column(db.String(50), nullable=False)  # Entry, Mid, Senior
    difficulty = db.Column(db.String(20), nullable=False)  # Easy, Medium, Hard
    question_types = db.Column(db.String(100), nullable=True)  # Technical, HR, Behavioral, etc.
    
    current_question_index = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('InterviewQuestion', backref='session', lazy=True, cascade="all, delete-orphan")
    report = db.relationship('PerformanceReport', backref='session', uselist=False, lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_role': self.job_role,
            'experience_level': self.experience_level,
            'difficulty': self.difficulty,
            'question_types': self.question_types.split(',') if self.question_types else [],
            'current_question_index': self.current_question_index,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    expected_answer = db.Column(db.Text, nullable=True)
    hints = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=True)
    concept = db.Column(db.String(100), nullable=True)
    time_limit = db.Column(db.Integer, default=60)  # seconds
    
    user_answer = db.Column(db.Text, nullable=True)
    feedback_text = db.Column(db.Text, nullable=True)
    
    # Category scoring per question
    technical_score = db.Column(db.Integer, default=0)
    grammar_score = db.Column(db.Integer, default=0)
    fluency_score = db.Column(db.Integer, default=0)
    overall_score = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'question_text': self.question_text,
            'expected_answer': self.expected_answer,
            'hints': self.hints,
            'difficulty': self.difficulty,
            'concept': self.concept,
            'time_limit': self.time_limit,
            'user_answer': self.user_answer,
            'feedback_text': self.feedback_text,
            'scores': {
                'technical': self.technical_score,
                'grammar': self.grammar_score,
                'fluency': self.fluency_score,
                'overall': self.overall_score
            },
            'created_at': self.created_at.isoformat()
        }

class PerformanceReport(db.Model):
    __tablename__ = 'performance_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    
    overall_score = db.Column(db.Integer, default=0)
    communication_score = db.Column(db.Integer, default=0)
    technical_score = db.Column(db.Integer, default=0)
    confidence_score = db.Column(db.Integer, default=0)
    grammar_score = db.Column(db.Integer, default=0)
    vocabulary_score = db.Column(db.Integer, default=0)
    fluency_score = db.Column(db.Integer, default=0)
    speaking_speed = db.Column(db.Integer, default=0)  # words per minute
    
    strengths_json = db.Column(db.Text, nullable=True)  # List of strengths
    weaknesses_json = db.Column(db.Text, nullable=True)  # List of weaknesses
    roadmap_json = db.Column(db.Text, nullable=True)  # Timelines, courses, books
    suggestions = db.Column(db.Text, nullable=True)  # General advice
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'overall_score': self.overall_score,
            'scores': {
                'communication': self.communication_score,
                'technical': self.technical_score,
                'confidence': self.confidence_score,
                'grammar': self.grammar_score,
                'vocabulary': self.vocabulary_score,
                'fluency': self.fluency_score,
                'speaking_speed': self.speaking_speed
            },
            'strengths': json.loads(self.strengths_json) if self.strengths_json else [],
            'weaknesses': json.loads(self.weaknesses_json) if self.weaknesses_json else [],
            'roadmap': json.loads(self.roadmap_json) if self.roadmap_json else {},
            'suggestions': self.suggestions,
            'created_at': self.created_at.isoformat()
        }

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    logo = db.Column(db.String(255), nullable=True)
    questions_json = db.Column(db.Text, nullable=True)  # Categorized questions list
    tips_json = db.Column(db.Text, nullable=True)  # Tips list
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'logo': self.logo,
            'questions': json.loads(self.questions_json) if self.questions_json else {},
            'tips': json.loads(self.tips_json) if self.tips_json else []
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'message': self.message,
            'created_at': self.created_at.isoformat()
        }

class BulkJob(db.Model):
    __tablename__ = 'bulk_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    total_files = db.Column(db.Integer, default=0)
    processed_files = db.Column(db.Integer, default=0)
    failed_files = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    resumes = db.relationship('Resume', backref='bulk_job', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'failed_files': self.failed_files,
            'created_at': self.created_at.isoformat()
        }


def migrate_database(app):
    """
    Safely synchronizes the SQLite schema with current SQLAlchemy models.
    Executes ALTER TABLE ADD COLUMN for any missing columns without data loss.
    """
    with app.app_context():
        # First ensure all tables exist
        db.create_all()
        
        # Get engine and inspector
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        # Define expected schema columns for tables that have evolved
        expected_columns = {
            'resumes': {
                'bulk_job_id': 'INTEGER REFERENCES bulk_jobs(id)',
                'file_hash': 'VARCHAR(64)',
                'analysis_version': 'VARCHAR(30) DEFAULT "v2"',
                'job_role': 'VARCHAR(100)',
                'target_job_description': 'TEXT',
                'location': 'VARCHAR(120)',
                'linkedin': 'VARCHAR(255)',
                'github': 'VARCHAR(255)',
                'portfolio': 'VARCHAR(255)',
                'title': 'VARCHAR(150)',
                'summary': 'TEXT',
                'projects_json': 'TEXT',
                'certifications_json': 'TEXT',
                'achievements_json': 'TEXT',
                'score_breakdown_json': 'TEXT',
                'processing_status': 'VARCHAR(30) DEFAULT "completed"',
                'processing_error': 'TEXT'
            }
        }
        
        with db.engine.connect() as conn:
            for table_name, columns in expected_columns.items():
                if table_name in inspector.get_table_names():
                    existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
                    for col_name, col_type in columns.items():
                        if col_name not in existing_cols:
                            try:
                                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                                conn.commit()
                            except Exception as e:
                                print(f"Note: Column {col_name} on {table_name} migration check: {e}")

        # Automatically seed standard demo & admin users into SQLite database
        try:
            demo_user = User.query.filter_by(email='user@techclevora.com').first()
            if not demo_user:
                demo_user = User(username='TechClevoraUser', email='user@techclevora.com', role='user')
                demo_user.set_password('password123')
                db.session.add(demo_user)

            admin_user = User.query.filter_by(email='admin@techclevora.com').first()
            if not admin_user:
                admin_user = User(username='AdminUser', email='admin@techclevora.com', role='admin')
                admin_user.set_password('admin123')
                db.session.add(admin_user)

            db.session.commit()
        except Exception as seed_err:
            print(f"Seed users note: {seed_err}")
            db.session.rollback()

