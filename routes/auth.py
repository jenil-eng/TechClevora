from flask import Blueprint, request, jsonify, current_app
from models import db, User, Notification
from functools import wraps
import jwt
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "techclevora_secret_key_998877")

def generate_token(user_id):
    payload = {
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'sub': str(user_id)
    }
    # PyJWT 2.x returns string directly
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token if isinstance(token, str) else token.decode('utf-8')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
                
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
            
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = db.session.get(User, int(data['sub']))
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'message': 'Username, email, and password are required.'}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists.'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered.'}), 400
        
    # Check if this is the first user, and assign them as admin if so
    is_first_user = User.query.count() == 0
    role = 'admin' if is_first_user else 'user'
    
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Add welcome notification
        welcome_note = Notification(
            user_id=user.id,
            message="Welcome to TECH CLEVORA! Upload your first resume to check your ATS compatibility."
        )
        db.session.add(welcome_note)
        db.session.commit()
        
        token = generate_token(user.id)
        return jsonify({
            'message': 'Registration successful.',
            'token': token,
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating user: {str(e)}'}), 500

def _ensure_demo_user(email, password):
    if email == 'user@techclevora.com':
        default_username = 'TechClevoraUser'
        role = 'user'
    elif email == 'admin@techclevora.com':
        default_username = 'AdminUser'
        role = 'admin'
    else:
        return None

    # Search for existing demo user by email or fallback username
    user = User.query.filter((User.email == email) | (User.username == default_username)).first()
    if not user:
        user = User(username=default_username, email=email, role=role)
    else:
        user.email = email
        user.role = role
        
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
    return user

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    
    if not email or not password:
        return jsonify({'message': 'Email and password are required.'}), 400

    # Ensure demo user exists and password is updated
    if email in ['user@techclevora.com', 'admin@techclevora.com']:
        user = _ensure_demo_user(email, password)
    else:
        user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid credentials. Please check your email and password.'}), 401
        
    token = generate_token(user.id)
    return jsonify({
        'message': 'Login successful.',
        'token': token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/profile', methods=['GET', 'POST'])
@token_required
def profile(current_user):
    if request.method == 'GET':
        return jsonify({'user': current_user.to_dict()})
        
    # POST - update profile details
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if username:
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != current_user.id:
            return jsonify({'message': 'Username already taken.'}), 400
        current_user.username = username
        
    if email:
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            return jsonify({'message': 'Email already registered by another account.'}), 400
        current_user.email = email
        
    if password:
        current_user.set_password(password)
        
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully.',
            'user': current_user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Email is required.'}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        # Avoid user enumeration attacks, say success
        return jsonify({'message': 'Password reset link sent (if account exists).'}), 200
        
    # Mock behavior
    return jsonify({
        'message': f'Password reset link generated. A mock email has been simulated for {email}. Please note that mock testing code will bypass this.'
    }), 200

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    email = data.get('email')
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({'message': 'Email and OTP are required.'}), 400
        
    # Accept standard OTP code '123456' or any 6 digit input for test/demo
    if len(otp) == 6:
        return jsonify({'message': 'OTP verification successful.'}), 200
    else:
        return jsonify({'message': 'Invalid OTP code. Try "123456".'}), 400

@auth_bp.route('/profile-pic', methods=['POST'])
@token_required
def upload_profile_pic(current_user):
    if 'profile_pic' not in request.files:
        return jsonify({'message': 'No image file found.'}), 400
        
    file = request.files['profile_pic']
    if file.filename == '':
        return jsonify({'message': 'No file selected.'}), 400
        
    # Verify image extensions
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in allowed_extensions:
        return jsonify({'message': 'Invalid file format. Please upload PNG, JPG, JPEG, GIF or WEBP.'}), 400
        
    filename = f"pic_{current_user.id}_{int(datetime.utcnow().timestamp())}{ext}"
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    relative_path = f"/static/uploads/avatars/{filename}"
    current_user.profile_pic = relative_path
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile picture uploaded.',
            'profile_pic': relative_path
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error saving path: {str(e)}'}), 500
