# backend/memory/enhanced_long_term_memory.py
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bson import ObjectId
import json

class LongTermMemory:
    """
    Enhanced long-term memory with semantic patterns and learning capabilities
    """
    
    def __init__(self, db_connection, ttl_days=90):  # Increased from 30 days
        self.collection = db_connection.get_collection('long_term_memory')
        self.ttl_days = ttl_days
        self._create_indexes()
    
    def _create_indexes(self):
        """Create enhanced indexes for better performance"""
        try:
            self.collection.create_index([('user_id', 1)])
            self.collection.create_index([('memory_type', 1)])
            self.collection.create_index([('created_at', -1)])
            self.collection.create_index([('user_id', 1), ('memory_type', 1)])
            self.collection.create_index([('interaction_type', 1)])
            print("✅ Long-term memory indexes created")
        except Exception:
            pass
    
    def store_user_preference(self, user_id: str, preference_type: str, preference_data: Dict[str, Any]):
        """Enhanced user preference storage"""
        try:
            memory_data = {
                'user_id': user_id,
                'memory_type': 'preference',
                'preference_type': preference_type,
                'data': preference_data,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'usage_count': 1,
                'confidence_score': preference_data.get('confidence', 0.8)
            }
            
            # Upsert preference with confidence scoring
            existing = self.collection.find_one({
                'user_id': user_id,
                'memory_type': 'preference',
                'preference_type': preference_type
            })
            
            if existing:
                # Update with weighted average of confidence
                old_confidence = existing.get('confidence_score', 0.5)
                old_count = existing.get('usage_count', 1)
                new_confidence = preference_data.get('confidence', 0.8)
                
                weighted_confidence = ((old_confidence * old_count) + new_confidence) / (old_count + 1)
                
                self.collection.update_one(
                    {'_id': existing['_id']},
                    {
                        '$set': {
                            'data': preference_data,
                            'updated_at': datetime.now(),
                            'confidence_score': weighted_confidence
                        },
                        '$inc': {'usage_count': 1}
                    }
                )
            else:
                self.collection.insert_one(memory_data)
            
            return True
        except Exception as e:
            print(f"Error storing user preference: {str(e)}")
            return False
    
    def get_user_preferences(self, user_id: str, preference_type: str = None) -> List[Dict[str, Any]]:
        """Get enhanced user preferences with confidence scoring"""
        try:
            query = {
                'user_id': user_id,
                'memory_type': 'preference'
            }
            
            if preference_type:
                query['preference_type'] = preference_type
            
            preferences = list(
                self.collection.find(query)
                .sort([('confidence_score', -1), ('updated_at', -1)])
            )
            
            # Convert ObjectId to string and add relevance scoring
            for pref in preferences:
                pref['_id'] = str(pref['_id'])
                
                # Calculate relevance based on recency and usage
                days_old = (datetime.now() - pref.get('updated_at', datetime.now())).days
                recency_score = max(0, 1 - (days_old / 30))  # Decay over 30 days
                usage_score = min(1, pref.get('usage_count', 1) / 10)  # Cap at 10 uses
                
                pref['relevance_score'] = (
                    pref.get('confidence_score', 0.5) * 0.5 +
                    recency_score * 0.3 +
                    usage_score * 0.2
                )
            
            return preferences
        except Exception as e:
            print(f"Error getting user preferences: {str(e)}")
            return []
    
    def store_interaction_pattern(self, user_id: str, pattern_type: str, pattern_data: Dict[str, Any]):
        """Enhanced interaction pattern storage with learning"""
        try:
            memory_data = {
                'user_id': user_id,
                'memory_type': 'pattern',
                'pattern_type': pattern_type,
                'data': pattern_data,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(days=self.ttl_days),
                'pattern_strength': pattern_data.get('confidence', 0.5),
                'occurrence_count': 1,
                'last_seen': datetime.now()
            }
            
            # Check for existing similar patterns
            existing = self.collection.find_one({
                'user_id': user_id,
                'memory_type': 'pattern',
                'pattern_type': pattern_type,
                'data.intent': pattern_data.get('intent')  # Match by intent
            })
            
            if existing:
                # Strengthen existing pattern
                old_strength = existing.get('pattern_strength', 0.5)
                old_count = existing.get('occurrence_count', 1)
                new_strength = pattern_data.get('confidence', 0.5)
                
                # Calculate reinforced pattern strength
                reinforced_strength = min(1.0, old_strength + (new_strength * 0.1))
                
                self.collection.update_one(
                    {'_id': existing['_id']},
                    {
                        '$set': {
                            'data': {**existing.get('data', {}), **pattern_data},
                            'pattern_strength': reinforced_strength,
                            'last_seen': datetime.now(),
                            'expires_at': datetime.now() + timedelta(days=self.ttl_days)
                        },
                        '$inc': {'occurrence_count': 1}
                    }
                )
            else:
                self.collection.insert_one(memory_data)
            
            return True
        except Exception as e:
            print(f"Error storing interaction pattern: {str(e)}")
            return False
    
    def get_interaction_patterns(self, user_id: str, pattern_type: str = None, 
                               days_back: int = 30) -> List[Dict[str, Any]]:
        """Get enhanced interaction patterns with strength scoring"""
        try:
            query = {
                'user_id': user_id,
                'memory_type': 'pattern',
                'created_at': {'$gte': datetime.now() - timedelta(days=days_back)}
            }
            
            if pattern_type:
                query['pattern_type'] = pattern_type
            
            patterns = list(
                self.collection.find(query)
                .sort([('pattern_strength', -1), ('occurrence_count', -1)])
            )
            
            # Enhance patterns with calculated scores
            for pattern in patterns:
                pattern['_id'] = str(pattern['_id'])
                
                # Calculate pattern reliability
                occurrence_count = pattern.get('occurrence_count', 1)
                pattern_strength = pattern.get('pattern_strength', 0.5)
                days_since_last = (datetime.now() - pattern.get('last_seen', datetime.now())).days
                
                # Reliability decreases over time but strengthens with usage
                time_decay = max(0.1, 1 - (days_since_last / 30))
                usage_boost = min(2.0, 1 + (occurrence_count / 10))
                
                pattern['reliability_score'] = pattern_strength * time_decay * usage_boost
            
            return patterns
        except Exception as e:
            print(f"Error getting interaction patterns: {str(e)}")
            return []
    
    def store_successful_interaction(self, user_id: str, interaction_type: str, details: Dict[str, Any]):
        """Enhanced successful interaction storage with learning insights"""
        try:
            memory_data = {
                'user_id': user_id,
                'memory_type': 'success',
                'interaction_type': interaction_type,
                'details': details,
                'created_at': datetime.now(),
                'success_score': details.get('confidence', 0.8),
                'context_hash': self._generate_context_hash(details),
                'learning_value': self._calculate_learning_value(details)
            }
            
            self.collection.insert_one(memory_data)
            
            # Also update related patterns
            self._update_success_patterns(user_id, interaction_type, details)
            
            return True
        except Exception as e:
            print(f"Error storing successful interaction: {str(e)}")
            return False
    
    def _generate_context_hash(self, details: Dict[str, Any]) -> str:
        """Generate hash for similar context detection"""
        try:
            # Create a simplified context signature
            context_elements = [
                details.get('intent', ''),
                str(sorted(details.get('entities', {}).keys())),
                details.get('message', '')[:50]  # First 50 chars
            ]
            
            context_string = '|'.join(context_elements)
            return str(hash(context_string))
        except:
            return 'unknown'
    
    def _calculate_learning_value(self, details: Dict[str, Any]) -> float:
        """Calculate how valuable this interaction is for learning"""
        learning_value = 0.5  # Base value
        
        # High confidence interactions are more valuable
        confidence = details.get('confidence', 0.5)
        learning_value += confidence * 0.3
        
        # Complex entities increase learning value
        entities = details.get('entities', {})
        if len(entities) > 2:
            learning_value += 0.2
        
        # Successful resolutions are valuable
        if details.get('success', False):
            learning_value += 0.3
        
        return min(1.0, learning_value)
    
    def _update_success_patterns(self, user_id: str, interaction_type: str, details: Dict[str, Any]):
        """Update success patterns based on successful interactions"""
        try:
            # Extract pattern data from successful interaction
            pattern_data = {
                'intent': details.get('intent'),
                'success_indicators': {
                    'entities_used': list(details.get('entities', {}).keys()),
                    'confidence_achieved': details.get('confidence', 0.5),
                    'response_type': details.get('response_type', 'standard')
                },
                'context_type': details.get('context_type', 'general'),
                'time_of_day': datetime.now().hour,
                'success': True
            }
            
            self.store_interaction_pattern(user_id, f"{interaction_type}_success", pattern_data)
            
        except Exception as e:
            print(f"Error updating success patterns: {str(e)}")
    
    def get_successful_interactions(self, user_id: str, interaction_type: str = None, 
                                   limit: int = 50) -> List[Dict[str, Any]]:
        """Get successful interactions with enhanced filtering"""
        try:
            query = {
                'user_id': user_id,
                'memory_type': 'success'
            }
            
            if interaction_type:
                query['interaction_type'] = interaction_type
            
            interactions = list(
                self.collection.find(query)
                .sort([('learning_value', -1), ('created_at', -1)])
                .limit(limit)
            )
            
            # Enhance with relevance scores
            for interaction in interactions:
                interaction['_id'] = str(interaction['_id'])
                
                # Calculate current relevance
                days_old = (datetime.now() - interaction.get('created_at', datetime.now())).days
                recency_score = max(0.1, 1 - (days_old / 60))  # Decay over 60 days
                learning_score = interaction.get('learning_value', 0.5)
                success_score = interaction.get('success_score', 0.5)
                
                interaction['current_relevance'] = (
                    recency_score * 0.3 +
                    learning_score * 0.4 +
                    success_score * 0.3
                )
            
            return interactions
        except Exception as e:
            print(f"Error getting successful interactions: {str(e)}")
            return []
    
    def store_context_summary(self, user_id: str, summary_data: Dict[str, Any]):
        """Enhanced context summary storage with semantic analysis"""
        try:
            memory_data = {
                'user_id': user_id,
                'memory_type': 'context_summary',
                'summary': summary_data,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(days=self.ttl_days),
                'summary_type': summary_data.get('type', 'conversation'),
                'key_topics': self._extract_key_topics(summary_data),
                'sentiment': summary_data.get('sentiment', 'neutral'),
                'complexity_score': self._calculate_complexity_score(summary_data)
            }
            
            self.collection.insert_one(memory_data)
            return True
        except Exception as e:
            print(f"Error storing context summary: {str(e)}")
            return False
    
    def _extract_key_topics(self, summary_data: Dict[str, Any]) -> List[str]:
        """Extract key topics from summary data"""
        try:
            key_topics = []
            
            # Extract from summary text
            summary_text = str(summary_data.get('summary', '')).lower()
            
            # Common HR topics
            hr_topics = ['leave', 'payroll', 'salary', 'candidate', 'recruitment', 
                        'interview', 'performance', 'benefits', 'training']
            
            for topic in hr_topics:
                if topic in summary_text:
                    key_topics.append(topic)
            
            # Extract from entities if available
            entities = summary_data.get('entities', {})
            for entity_type, entity_value in entities.items():
                if entity_type in ['skills', 'department', 'position']:
                    if isinstance(entity_value, list):
                        key_topics.extend(entity_value[:3])  # Top 3
                    else:
                        key_topics.append(str(entity_value))
            
            return list(set(key_topics))[:5]  # Max 5 topics
        except:
            return []
    
    def _calculate_complexity_score(self, summary_data: Dict[str, Any]) -> float:
        """Calculate complexity score of the interaction"""
        complexity = 0.0
        
        # Base complexity from summary length
        summary_length = len(str(summary_data.get('summary', '')))
        complexity += min(0.3, summary_length / 1000)
        
        # Entity complexity
        entities = summary_data.get('entities', {})
        complexity += min(0.3, len(entities) / 10)
        
        # Multi-step process complexity
        if summary_data.get('multi_step', False):
            complexity += 0.4
        
        # Tool usage complexity
        tools_used = summary_data.get('tools_used', [])
        complexity += min(0.2, len(tools_used) / 5)
        
        return min(1.0, complexity)
    
    def get_context_summaries(self, user_id: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get enhanced context summaries with topic analysis"""
        try:
            query = {
                'user_id': user_id,
                'memory_type': 'context_summary',
                'created_at': {'$gte': datetime.now() - timedelta(days=days_back)}
            }
            
            summaries = list(
                self.collection.find(query)
                .sort([('complexity_score', -1), ('created_at', -1)])
            )
            
            # Enhance summaries
            for summary in summaries:
                summary['_id'] = str(summary['_id'])
                
                # Calculate relevance decay
                days_old = (datetime.now() - summary.get('created_at', datetime.now())).days
                time_relevance = max(0.1, 1 - (days_old / 30))
                complexity = summary.get('complexity_score', 0.5)
                
                summary['current_relevance'] = time_relevance * complexity
            
            return summaries
        except Exception as e:
            print(f"Error getting context summaries: {str(e)}")
            return []
    
    def get_user_learning_profile(self, user_id: str) -> Dict[str, Any]:
        """Generate comprehensive user learning profile"""
        try:
            # Get all user memories
            all_memories = list(self.collection.find({'user_id': user_id}))
            
            if not all_memories:
                return {'profile_type': 'new_user'}
            
            profile = {
                'total_interactions': len(all_memories),
                'memory_types': {},
                'success_rate': 0,
                'preferred_topics': {},
                'interaction_complexity': 'medium',
                'learning_velocity': 'standard',
                'dominant_patterns': [],
                'expertise_areas': []
            }
            
            # Analyze memory distribution
            success_count = 0
            topic_frequency = {}
            complexity_scores = []
            
            for memory in all_memories:
                memory_type = memory.get('memory_type', 'unknown')
                profile['memory_types'][memory_type] = profile['memory_types'].get(memory_type, 0) + 1
                
                # Success rate calculation
                if memory_type == 'success':
                    success_count += 1
                
                # Topic analysis
                key_topics = memory.get('key_topics', [])
                for topic in key_topics:
                    topic_frequency[topic] = topic_frequency.get(topic, 0) + 1
                
                # Complexity analysis
                complexity = memory.get('complexity_score', 0.5)
                if complexity > 0:
                    complexity_scores.append(complexity)
            
            # Calculate metrics
            total_interactions = len(all_memories)
            profile['success_rate'] = success_count / total_interactions if total_interactions > 0 else 0
            
            # Top topics
            sorted_topics = sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)
            profile['preferred_topics'] = dict(sorted_topics[:5])
            
            # Average complexity
            if complexity_scores:
                avg_complexity = sum(complexity_scores) / len(complexity_scores)
                if avg_complexity > 0.7:
                    profile['interaction_complexity'] = 'high'
                elif avg_complexity < 0.3:
                    profile['interaction_complexity'] = 'low'
                else:
                    profile['interaction_complexity'] = 'medium'
            
            # Learning velocity based on interaction frequency
            recent_interactions = len([m for m in all_memories 
                                     if m.get('created_at', datetime.min) > datetime.now() - timedelta(days=7)])
            
            if recent_interactions > 20:
                profile['learning_velocity'] = 'fast'
            elif recent_interactions < 5:
                profile['learning_velocity'] = 'slow'
            else:
                profile['learning_velocity'] = 'standard'
            
            # Dominant patterns
            patterns = [m for m in all_memories if m.get('memory_type') == 'pattern']
            sorted_patterns = sorted(patterns, 
                                   key=lambda x: x.get('pattern_strength', 0) * x.get('occurrence_count', 1), 
                                   reverse=True)
            
            profile['dominant_patterns'] = [
                {
                    'pattern_type': p.get('pattern_type'),
                    'strength': p.get('pattern_strength', 0),
                    'occurrences': p.get('occurrence_count', 1)
                }
                for p in sorted_patterns[:3]
            ]
            
            # Expertise areas (topics with high success and frequency)
            expertise_threshold = 0.7
            for topic, frequency in sorted_topics:
                if frequency >= 3:  # Must appear at least 3 times
                    # Check success rate for this topic
                    topic_successes = [m for m in all_memories 
                                     if m.get('memory_type') == 'success' 
                                     and topic in m.get('key_topics', [])]
                    
                    if len(topic_successes) / frequency >= expertise_threshold:
                        profile['expertise_areas'].append({
                            'topic': topic,
                            'frequency': frequency,
                            'success_rate': len(topic_successes) / frequency
                        })
            
            return profile
            
        except Exception as e:
            print(f"Error generating user learning profile: {str(e)}")
            return {'profile_type': 'error', 'error': str(e)}
    
    def cleanup_expired_memories(self):
        """Enhanced cleanup with selective retention"""
        try:
            # Don't delete high-value memories even if expired
            high_value_query = {
                'expires_at': {'$lt': datetime.now()},
                '$or': [
                    {'learning_value': {'$lt': 0.8}},  # Keep high learning value
                    {'pattern_strength': {'$lt': 0.8}},  # Keep strong patterns
                    {'occurrence_count': {'$lt': 5}}  # Keep frequently occurring
                ]
            }
            
            result = self.collection.delete_many(high_value_query)
            
            # Extend expiry for high-value memories
            self.collection.update_many(
                {
                    'expires_at': {'$lt': datetime.now()},
                    '$or': [
                        {'learning_value': {'$gte': 0.8}},
                        {'pattern_strength': {'$gte': 0.8}},
                        {'occurrence_count': {'$gte': 5}}
                    ]
                },
                {
                    '$set': {
                        'expires_at': datetime.now() + timedelta(days=30)  # Extend by 30 days
                    }
                }
            )
            
            print(f"Cleaned up {result.deleted_count} expired long-term memories")
            return result.deleted_count
        except Exception as e:
            print(f"Error cleaning up expired memories: {str(e)}")
            return 0
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics"""
        try:
            total_memories = self.collection.count_documents({})
            
            # Memory type distribution
            pipeline = [
                {'$group': {
                    '_id': '$memory_type',
                    'count': {'$sum': 1},
                    'avg_learning_value': {'$avg': '$learning_value'},
                    'avg_pattern_strength': {'$avg': '$pattern_strength'}
                }}
            ]
            
            type_stats = list(self.collection.aggregate(pipeline))
            
            # Recent activity (last 7 days)
            recent_memories = self.collection.count_documents({
                'created_at': {'$gte': datetime.now() - timedelta(days=7)}
            })
            
            # Top users by memory count
            user_pipeline = [
                {'$group': {
                    '_id': '$user_id',
                    'memory_count': {'$sum': 1},
                    'last_activity': {'$max': '$created_at'}
                }},
                {'$sort': {'memory_count': -1}},
                {'$limit': 10}
            ]
            
            top_users = list(self.collection.aggregate(user_pipeline))
            
            return {
                'total_memories': total_memories,
                'recent_activity': recent_memories,
                'memory_type_distribution': type_stats,
                'top_users': top_users,
                'system_health': 'healthy' if total_memories > 0 else 'new_system'
            }
            
        except Exception as e:
            print(f"Error getting memory statistics: {str(e)}")
            return {'error': str(e)}