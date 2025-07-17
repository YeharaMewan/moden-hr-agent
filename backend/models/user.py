# backend/models/user.py
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
import bcrypt

class User:
    def __init__(self, db_connection):
        self.collection = db_connection.get_collection('users')
    
    def create_user(self, user_data):
        """Create a new user"""
        try:
            # Hash password
            password = user_data.get('password')
            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                user_data['password'] = hashed_password
            
            # Set default values
            user_data['created_at'] = datetime.now()
            user_data['updated_at'] = datetime.now()
            user_data['annual_leave_balance'] = user_data.get('annual_leave_balance', 21)  # Default 21 days
            
            result = self.collection.insert_one(user_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Error creating user: {str(e)}")
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            user = self.collection.find_one({'_id': ObjectId(user_id)})
            if user:
                user['_id'] = str(user['_id'])
                # Remove password from response
                user.pop('password', None)
            return user
        except Exception as e:
            raise Exception(f"Error getting user by ID: {str(e)}")
    
    def get_user_by_username(self, username):
        """Get user by username"""
        try:
            user = self.collection.find_one({'username': username})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            raise Exception(f"Error getting user by username: {str(e)}")
        
    def get_user_by_employee_id(self, employee_id):
        """Get user by employee ID"""
        try:
            # Employee IDs are case-sensitive, but we can search case-insensitively
            # if the format is consistent. Assuming case-sensitive for now.
            user = self.collection.find_one({'employee_id': employee_id})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            raise Exception(f"Error getting user by employee ID: {str(e)}")
    
    def verify_password(self, username, password):
        """Verify user password"""
        try:
            user = self.collection.find_one({'username': username})
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
                user['_id'] = str(user['_id'])
                user.pop('password', None)  # Remove password from response
                return user
            return None
        except Exception as e:
            raise Exception(f"Error verifying password: {str(e)}")
    
    def update_user(self, user_id, update_data):
        """Update user information"""
        try:
            update_data['updated_at'] = datetime.now()
            result = self.collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error updating user: {str(e)}")
    
    def get_all_users(self, role=None, department=None):
        """Get all users, optionally filtered by role and/or department (case-insensitive)."""
        try:
            query = {}
            if role:
                query['role'] = role
            if department:
                # Use regex for case-insensitive search
                query['department'] = {'$regex': f'^{department}$', '$options': 'i'}
            
            users = list(self.collection.find(query, {'password': 0}))
            for user in users:
                user['_id'] = str(user['_id'])
            return users
        except Exception as e:
            raise Exception(f"Error getting all users: {str(e)}")