# backend/routes/auth.py
from flask import Blueprint, request, jsonify
from models.user import User
from utils.auth import AuthManager, token_required
import re

auth_bp = Blueprint('auth', __name__)

def get_db_connection():
    from app import db_connection
    return db_connection

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'role', 'department', 'employee_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate role
        if data['role'] not in ['user', 'hr']:
            return jsonify({'error': 'Role must be either "user" or "hr"'}), 400
        
        # Validate password strength
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        db_connection = get_db_connection()
        user_model = User(db_connection)
        
        # Check if user already exists
        existing_user = user_model.get_user_by_username(data['username'])
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create user
        user_id = user_model.create_user(data)
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password are required'}), 400
        
        db_connection = get_db_connection()
        user_model = User(db_connection)
        
        # Verify user credentials
        user = user_model.verify_password(data['username'], data['password'])
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Generate token
        auth_manager = AuthManager('your-secret-key')  # In production, use config
        token = auth_manager.generate_token(user)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['_id'],
                'username': user['username'],
                'role': user['role'],
                'department': user['department'],
                'employee_id': user['employee_id']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get user profile"""
    try:
        db_connection = get_db_connection()
        user_model = User(db_connection)
        
        user = user_model.get_user_by_id(current_user['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        
        # Remove sensitive fields that shouldn't be updated here
        data.pop('password', None)
        data.pop('role', None)
        data.pop('username', None)
        
        db_connection = get_db_connection()
        user_model = User(db_connection)
        
        success = user_model.update_user(current_user['user_id'], data)
        if not success:
            return jsonify({'error': 'Failed to update profile'}), 500
        
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change user password"""
    try:
        data = request.get_json()
        
        if 'current_password' not in data or 'new_password' not in data:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        if len(data['new_password']) < 6:
            return jsonify({'error': 'New password must be at least 6 characters long'}), 400
        
        db_connection = get_db_connection()
        user_model = User(db_connection)
        
        # Verify current password
        user = user_model.verify_password(current_user['username'], data['current_password'])
        if not user:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        auth_manager = AuthManager('your-secret-key')
        hashed_password = auth_manager.hash_password(data['new_password'])
        
        success = user_model.update_user(current_user['user_id'], {'password': hashed_password})
        if not success:
            return jsonify({'error': 'Failed to update password'}), 500
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500