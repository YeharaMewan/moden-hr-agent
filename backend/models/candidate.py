# backend/models/candidate.py
from datetime import datetime
from bson import ObjectId

class Candidate:
    def __init__(self, db_connection):
        self.collection = db_connection.get_collection('candidates')
    
    def create_candidate(self, candidate_data):
        """Create a new candidate record"""
        try:
            candidate_data['applied_date'] = datetime.now()
            candidate_data['created_at'] = datetime.now()
            candidate_data['updated_at'] = datetime.now()
            candidate_data['status'] = 'applied'
            
            result = self.collection.insert_one(candidate_data)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Error creating candidate: {str(e)}")
    
    def get_candidate_by_id(self, candidate_id):
        """Get candidate by ID"""
        try:
            candidate = self.collection.find_one({'_id': ObjectId(candidate_id)})
            if candidate:
                candidate['_id'] = str(candidate['_id'])
            return candidate
        except Exception as e:
            raise Exception(f"Error getting candidate by ID: {str(e)}")
    
    def search_candidates_by_skills(self, skills):
        """Search candidates by skills"""
        try:
            query = {'skills': {'$all': skills}}
            candidates = list(self.collection.find(query))
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            return candidates
        except Exception as e:
            raise Exception(f"Error searching candidates by skills: {str(e)}")
    
    def search_candidates_by_position(self, position):
        """Search candidates by position"""
        try:
            query = {'position_applied': {'$regex': position, '$options': 'i'}}
            candidates = list(self.collection.find(query))
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            return candidates
        except Exception as e:
            raise Exception(f"Error searching candidates by position: {str(e)}")
    
    def get_all_candidates(self):
        """Get all candidates"""
        try:
            candidates = list(self.collection.find().sort('applied_date', -1))
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            return candidates
        except Exception as e:
            raise Exception(f"Error getting all candidates: {str(e)}")
    

    def search_candidates_by_name(self, name: str):
        """Search for candidates by name using a case-insensitive regex search."""
        try:
            # This query looks for the 'name' field containing the given name string, ignoring case
            query = {'name': {'$regex': name, '$options': 'i'}}
            candidates = list(self.collection.find(query))
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            return candidates
        except Exception as e:
            raise Exception(f"Error searching candidates by name: {str(e)}")


    def search_candidates(self, criteria: dict):
        """
        Search candidates by multiple criteria like skills and position.
        """
        try:
            query = {}
            
            # Build the query for skills using $all for AND logic
            if criteria.get('skills'):
                query['skills'] = {'$all': [skill.lower() for skill in criteria['skills']]}
            
            # Build the query for position using $regex for flexible matching
            if criteria.get('position'):
                query['position_applied'] = {'$regex': criteria['position'], '$options': 'i'}
            
            # If there's no criteria, return an empty list
            if not query:
                return []

            candidates = list(self.collection.find(query))
            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])
            return candidates
        except Exception as e:
            raise Exception(f"Error searching candidates with combined criteria: {str(e)}")

    def update_candidate_status(self, candidate_id, status):
        """Update candidate status"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now()
            }
            
            result = self.collection.update_one(
                {'_id': ObjectId(candidate_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error updating candidate status: {str(e)}")