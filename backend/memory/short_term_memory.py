# backend/memory/enhanced_short_term_memory.py
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional

class ShortTermMemory:
    """
    Enhanced short-term memory for active conversations with form handling
    """
    
    def __init__(self, db_connection, ttl_hours=2):  # Increased from 1 hour
        self.collection = db_connection.get_collection('short_term_memory')
        self.ttl_hours = ttl_hours
        self._create_ttl_index()
    
    def _create_ttl_index(self):
        """Create TTL index for automatic cleanup"""
        try:
            existing_indexes = list(self.collection.list_indexes())
            index_exists = any(idx.get('name') == 'expires_at_1' for idx in existing_indexes)
            
            if not index_exists:
                self.collection.create_index(
                    "expires_at", 
                    expireAfterSeconds=0,
                    background=True
                )
                print("✅ Short-term memory TTL index created")
        except Exception as e:
            print(f"TTL index creation warning: {e}")
    
    def store_context(self, user_id: str, session_id: str, context_data: Dict[str, Any]):
        """Enhanced context storage with categorization"""
        try:
            memory_data = {
                'user_id': user_id,
                'session_id': session_id,
                'context_type': context_data.get('context_type', 'conversation'),
                'data': context_data,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=self.ttl_hours),
                'interaction_count': 1,
                'last_accessed': datetime.now()
            }
            
            # Check if similar context exists and update instead
            existing = self.collection.find_one({
                'user_id': user_id,
                'session_id': session_id,
                'context_type': memory_data['context_type']
            })
            
            if existing:
                # Update existing context
                self.collection.update_one(
                    {'_id': existing['_id']},
                    {
                        '$set': {
                            'data': context_data,
                            'last_accessed': datetime.now(),
                            'expires_at': datetime.now() + timedelta(hours=self.ttl_hours)
                        },
                        '$inc': {'interaction_count': 1}
                    }
                )
            else:
                # Insert new context
                self.collection.insert_one(memory_data)
            
            return True
        except Exception as e:
            print(f"Error storing context: {str(e)}")
            return False
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get enhanced conversation history with context"""
        try:
            # Get recent conversations, sorted by recency
            conversations = list(
                self.collection.find({
                    'user_id': user_id,
                    'context_type': 'conversation'
                })
                .sort('last_accessed', -1)
                .limit(limit)
            )
            
            # Clean and format
            formatted_conversations = []
            for conv in conversations:
                formatted_conv = {
                    'session_id': conv.get('session_id'),
                    'data': conv.get('data', {}),
                    'created_at': conv.get('created_at'),
                    'interaction_count': conv.get('interaction_count', 1)
                }
                formatted_conversations.append(formatted_conv)
            
            return formatted_conversations
            
        except Exception as e:
            print(f"Error getting conversation history: {str(e)}")
            return []
    
    def store_form_data(self, user_id: str, session_id: str, form_type: str, form_data: Dict[str, Any]):
        """Store form data for multi-step processes"""
        try:
            form_memory = {
                'user_id': user_id,
                'session_id': session_id,
                'context_type': 'form_data',
                'form_type': form_type,
                'data': form_data,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=1),  # Forms expire in 1 hour
                'last_updated': datetime.now()
            }
            
            # Upsert form data
            self.collection.update_one(
                {
                    'user_id': user_id,
                    'session_id': session_id,
                    'context_type': 'form_data',
                    'form_type': form_type
                },
                {'$set': form_memory},
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"Error storing form data: {str(e)}")
            return False
    
    def get_form_data(self, user_id: str, session_id: str, form_type: str) -> Optional[Dict[str, Any]]:
        """Get stored form data"""
        try:
            form_data = self.collection.find_one({
                'user_id': user_id,
                'session_id': session_id,
                'context_type': 'form_data',
                'form_type': form_type
            })
            
            if form_data and form_data.get('expires_at', datetime.min) > datetime.now():
                return form_data.get('data', {})
            
            return None
        except Exception as e:
            print(f"Error getting form data: {str(e)}")
            return None
    
    def clear_form_data(self, user_id: str, session_id: str, form_type: str):
        """Clear form data after completion"""
        try:
            self.collection.delete_one({
                'user_id': user_id,
                'session_id': session_id,
                'context_type': 'form_data',
                'form_type': form_type
            })
            return True
        except Exception as e:
            print(f"Error clearing form data: {str(e)}")
            return False
    
    def get_user_context_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context summary"""
        try:
            # Get all contexts for user
            contexts = list(self.collection.find({'user_id': user_id}))
            
            summary = {
                'total_interactions': len(contexts),
                'active_sessions': len(set(ctx.get('session_id') for ctx in contexts)),
                'context_types': {},
                'recent_activity': [],
                'active_forms': []
            }
            
            # Analyze context types
            for ctx in contexts:
                ctx_type = ctx.get('context_type', 'unknown')
                summary['context_types'][ctx_type] = summary['context_types'].get(ctx_type, 0) + 1
                
                # Recent activity (last 24 hours)
                if ctx.get('last_accessed', datetime.min) > datetime.now() - timedelta(hours=24):
                    summary['recent_activity'].append({
                        'type': ctx_type,
                        'time': ctx.get('last_accessed'),
                        'session': ctx.get('session_id')
                    })
                
                # Active forms
                if ctx_type == 'form_data' and ctx.get('expires_at', datetime.min) > datetime.now():
                    summary['active_forms'].append({
                        'form_type': ctx.get('form_type'),
                        'session': ctx.get('session_id'),
                        'created': ctx.get('created_at')
                    })
            
            return summary
            
        except Exception as e:
            print(f"Error getting user context summary: {str(e)}")
            return {}
    
    def cleanup_expired_contexts(self):
        """Manual cleanup of expired contexts"""
        try:
            result = self.collection.delete_many({
                'expires_at': {'$lt': datetime.now()}
            })
            print(f"Cleaned up {result.deleted_count} expired short-term memories")
            return result.deleted_count
        except Exception as e:
            print(f"Error cleaning up expired contexts: {str(e)}")
            return 0


