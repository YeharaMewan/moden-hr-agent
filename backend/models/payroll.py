# backend/models/payroll.py
from datetime import datetime
from bson import ObjectId

class Payroll:
    def __init__(self, db_connection):
        self.collection = db_connection.get_collection('payroll')
    
    def create_payroll(self, payroll_data):
        """Create a new payroll record"""
        try:
            payroll_data['calculated_date'] = datetime.now()
            payroll_data['created_at'] = datetime.now()
            payroll_data['updated_at'] = datetime.now()
            
            result = self.collection.insert_one(payroll_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Error creating payroll: {str(e)}")
    
    def get_payroll_by_user(self, user_id, month=None, year=None):
        """Get payroll for a specific user"""
        try:
            query = {'user_id': ObjectId(user_id)}
            if month:
                query['month'] = month
            if year:
                query['year'] = year
            
            payrolls = list(self.collection.find(query).sort('calculated_date', -1))
            for payroll in payrolls:
                payroll['_id'] = str(payroll['_id'])
                payroll['user_id'] = str(payroll['user_id'])
            return payrolls
        except Exception as e:
            raise Exception(f"Error getting payroll by user: {str(e)}")
    
    def get_payroll_by_department(self, department, month=None, year=None):
        """Get payroll for a specific department"""
        try:
            query = {'department': department}
            if month:
                query['month'] = month
            if year:
                query['year'] = year
            
            payrolls = list(self.collection.find(query).sort('calculated_date', -1))
            for payroll in payrolls:
                payroll['_id'] = str(payroll['_id'])
                payroll['user_id'] = str(payroll['user_id'])
            return payrolls
        except Exception as e:
            raise Exception(f"Error getting payroll by department: {str(e)}")
    
    def calculate_department_total(self, department, month=None, year=None):
        """Calculate total payroll for department"""
        try:
            match_query = {'department': department}
            if month:
                match_query['month'] = month
            if year:
                match_query['year'] = year
            
            pipeline = [
                {'$match': match_query},
                {'$group': {
                    '_id': None,
                    'total_basic_salary': {'$sum': '$basic_salary'},
                    'total_allowances': {'$sum': '$allowances'},
                    'total_deductions': {'$sum': '$deductions'},
                    'total_net_salary': {'$sum': '$net_salary'},
                    'employee_count': {'$sum': 1}
                }}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            return result[0] if result else None
        except Exception as e:
            raise Exception(f"Error calculating department total: {str(e)}")
    
    def update_payroll(self, payroll_id, update_data):
        """Update payroll record"""
        try:
            update_data['updated_at'] = datetime.now()
            result = self.collection.update_one(
                {'_id': ObjectId(payroll_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error updating payroll: {str(e)}")