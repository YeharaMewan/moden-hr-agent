# backend/models/leave.py
from datetime import datetime
from bson import ObjectId

class Leave:
    def __init__(self, db_connection):
        self.collection = db_connection.get_collection('leaves')
    
    def create_leave_request(self, leave_data):
        """Create a new leave request"""
        try:
            leave_data['applied_date'] = datetime.now()
            leave_data['status'] = 'pending'
            leave_data['created_at'] = datetime.now()
            leave_data['updated_at'] = datetime.now()
            
            result = self.collection.insert_one(leave_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Error creating leave request: {str(e)}")
    
    def get_leave_by_id(self, leave_id):
        """Get leave request by ID"""
        try:
            leave = self.collection.find_one({'_id': ObjectId(leave_id)})
            if leave:
                leave['_id'] = str(leave['_id'])
                leave['user_id'] = str(leave['user_id'])
                if 'approved_by' in leave and leave['approved_by']:
                    leave['approved_by'] = str(leave['approved_by'])
            return leave
        except Exception as e:
            raise Exception(f"Error getting leave by ID: {str(e)}")
    
    def get_leaves_by_user(self, user_id, status=None):
        """Get all leaves for a specific user"""
        try:
            query = {'user_id': ObjectId(user_id)}
            if status:
                query['status'] = status
            
            leaves = list(self.collection.find(query).sort('applied_date', -1))
            for leave in leaves:
                leave['_id'] = str(leave['_id'])
                leave['user_id'] = str(leave['user_id'])
                if 'approved_by' in leave and leave['approved_by']:
                    leave['approved_by'] = str(leave['approved_by'])
            return leaves
        except Exception as e:
            raise Exception(f"Error getting leaves by user: {str(e)}")
    
    def get_pending_leaves(self):
        """Get all pending leave requests"""
        try:
            leaves = list(self.collection.find({'status': 'pending'}).sort('applied_date', 1))
            for leave in leaves:
                leave['_id'] = str(leave['_id'])
                leave['user_id'] = str(leave['user_id'])
            return leaves
        except Exception as e:
            raise Exception(f"Error getting pending leaves: {str(e)}")
    
    def update_leave_status(self, leave_id, status, hr_id, hr_comments=None):
        """Update leave request status"""
        try:
            update_data = {
                'status': status,
                'approved_by': ObjectId(hr_id),
                'updated_at': datetime.now()
            }
            
            if status == 'approved':
                update_data['approved_date'] = datetime.now()
            
            if hr_comments:
                update_data['hr_comments'] = hr_comments
            
            result = self.collection.update_one(
                {'_id': ObjectId(leave_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error updating leave status: {str(e)}")
    
    def get_leaves_by_date_range(self, start_date, end_date):
        """Get leaves within a date range"""
        try:
            query = {
                '$or': [
                    {'start_date': {'$gte': start_date, '$lte': end_date}},
                    {'end_date': {'$gte': start_date, '$lte': end_date}},
                    {'start_date': {'$lte': start_date}, 'end_date': {'$gte': end_date}}
                ]
            }
            
            leaves = list(self.collection.find(query))
            for leave in leaves:
                leave['_id'] = str(leave['_id'])
                leave['user_id'] = str(leave['user_id'])
                if 'approved_by' in leave and leave['approved_by']:
                    leave['approved_by'] = str(leave['approved_by'])
            return leaves
        except Exception as e:
            raise Exception(f"Error getting leaves by date range: {str(e)}")