# backend/utils/auth.py
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
import bcrypt

class AuthManager:
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def hr_required(f):
        """Decorator to require HR role"""
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.get('role') != 'hr':
                return jsonify({'error': 'HR access required'}), 403
            return f(current_user, *args, **kwargs)
        
        return decorated

    def generate_token(self, user_data):
        """Generate JWT token for user"""
        try:
            payload = {
                'user_id': user_data['_id'],
                'username': user_data['username'],
                'role': user_data['role'],
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow()
            }
            token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            return token
        except Exception as e:
            raise Exception(f"Error generating token: {str(e)}")
    
    def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token")
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def token_required(f):
    """Decorator to require authentication token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            auth_manager = AuthManager(current_app.config['SECRET_KEY'])
            payload = auth_manager.verify_token(token)
            current_user = payload
            
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def hr_required(f):
    """Decorator to require HR role"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.get('role') != 'hr':
            return jsonify({'error': 'HR access required'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated