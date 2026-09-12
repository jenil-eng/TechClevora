from flask import Blueprint, request, jsonify
from models import db, User, Resume, InterviewSession, PerformanceReport, Feedback
from routes.auth import token_required
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'message': 'Administrative privileges required.'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

@admin_bp.route('/dashboard', methods=['GET'])
@token_required
@admin_required
def admin_dashboard(current_user):
    # Total statistics
    total_users = User.query.count()
    total_resumes = Resume.query.count()
    total_sessions = InterviewSession.query.count()
    total_feedbacks = Feedback.query.count()
    
    # Average scores
    reports = PerformanceReport.query.all()
    avg_score = 0
    if reports:
        avg_score = int(sum(r.overall_score for r in reports) / len(reports))
        
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # System logs simulation
    logs = [
        {"timestamp": "2026-07-27 12:30:10", "level": "INFO", "message": "Database successfully initialized."},
        {"timestamp": "2026-07-27 12:35:44", "level": "INFO", "message": "User signup triggered: Meet Vekariya."},
        {"timestamp": "2026-07-27 12:45:00", "level": "WARNING", "message": "Gemini API key missing, falling back to mock provider."},
        {"timestamp": "2026-07-27 13:12:15", "level": "INFO", "message": "Mock interview session completed successfully."}
    ]
    
    return jsonify({
        'stats': {
            'total_users': total_users,
            'total_resumes': total_resumes,
            'total_sessions': total_sessions,
            'total_feedbacks': total_feedbacks,
            'average_performance_score': avg_score
        },
        'recent_users': [u.to_dict() for u in recent_users],
        'system_logs': logs
    }), 200

@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def list_users(current_user):
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200

@admin_bp.route('/users/<int:target_user_id>', methods=['DELETE', 'POST'])
@token_required
@admin_required
def manage_user(current_user, target_user_id):
    user = db.session.get(User, int(target_user_id))
    if not user:
        return jsonify({'message': 'User not found.'}), 404
        
    if request.method == 'DELETE':
        if user.id == current_user.id:
            return jsonify({'message': 'You cannot delete your own administrative account.'}), 400
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'message': f'User {user.username} deleted.'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Error deleting user: {str(e)}'}), 500
            
    # POST - Toggle Role
    if request.method == 'POST':
        new_role = 'admin' if user.role == 'user' else 'user'
        user.role = new_role
        try:
            db.session.commit()
            return jsonify({'message': f'User {user.username} role updated to {new_role}.', 'user': user.to_dict()}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Error toggling role: {str(e)}'}), 500

@admin_bp.route('/resumes', methods=['GET'])
@token_required
@admin_required
def list_resumes(current_user):
    resumes = Resume.query.order_by(Resume.created_at.desc()).all()
    return jsonify({'resumes': [r.to_dict() for r in resumes]}), 200

@admin_bp.route('/sessions', methods=['GET'])
@token_required
@admin_required
def list_sessions(current_user):
    sessions = InterviewSession.query.order_by(InterviewSession.created_at.desc()).all()
    output = []
    for s in sessions:
        user = db.session.get(User, int(s.user_id))
        s_dict = s.to_dict()
        s_dict['username'] = user.username if user else 'Deleted User'
        output.append(s_dict)
    return jsonify({'sessions': output}), 200
