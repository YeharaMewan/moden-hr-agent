# backend/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from datetime import datetime
import json
import hashlib

class BaseAgent(ABC):
    """
    Enhanced base class for all specialized agents with intelligent capabilities
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        self.gemini_api_key = gemini_api_key
        self.db_connection = db_connection
        self.memory_manager = memory_manager
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Enhanced features
        self.response_cache = {}
        self.context_cache = {}
        self.prompt_templates = self._initialize_prompt_templates()
        
        # Performance tracking
        self.request_count = 0
        self.cache_hits = 0
        
    def _initialize_prompt_templates(self) -> Dict[str, str]:
        """Initialize optimized prompt templates"""
        return {
            'understanding': """
            Analyze this user message and extract key information:
            Message: "{message}"
            Context: {context}
            
            Extract (respond in JSON only):
            {{
                "intent": "primary_intent",
                "entities": {{"key": "value"}},
                "confidence": 0.0-1.0,
                "missing_info": ["list of missing fields"],
                "urgency": "low|medium|high"
            }}
            """,
            
            'response_generation': """
            Generate a helpful response for: "{message}"
            
            Available information: {tool_data}
            User context: {user_context}
            Previous interactions: {memory_context}
            
            Guidelines:
            - Be conversational and helpful
            - Use specific data when available
            - Keep response under 200 words
            - Be culturally appropriate (English/Sinhala mixed context)
            """
        }
    
    @abstractmethod
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent-specific request - to be implemented by subclasses"""
        pass
    
    def generate_response(self, prompt: str, use_cache: bool = True) -> str:
        """Enhanced response generation with caching and optimization"""
        self.request_count += 1
        
        # Generate cache key
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check cache first
        if use_cache and cache_key in self.response_cache:
            cached_response = self.response_cache[cache_key]
            if datetime.now() - cached_response['timestamp'] < cached_response['ttl']:
                self.cache_hits += 1
                return cached_response['response']
        
        # Generate new response
        try:
            # Optimize prompt for token efficiency
            optimized_prompt = self._optimize_prompt(prompt)
            
            response = self.model.generate_content(optimized_prompt)
            response_text = response.text
            
            # Cache the response
            if use_cache:
                self.response_cache[cache_key] = {
                    'response': response_text,
                    'timestamp': datetime.now(),
                    'ttl': timedelta(minutes=30)  # 30 minute cache
                }
            
            return response_text
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again."
    
    def _optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt for token efficiency"""
        # Remove extra whitespace
        optimized = ' '.join(prompt.split())
        
        # Truncate if too long (rough estimate: 1 token ≈ 0.75 words)
        max_words = 1200  # Approximately 1600 tokens
        words = optimized.split()
        
        if len(words) > max_words:
            optimized = ' '.join(words[:max_words]) + "..."
        
        return optimized
    
    def understand_request(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced request understanding with context awareness"""
        
        # Get relevant context from memory
        memory_context = self._get_memory_context(user_context.get('user_id'), message)
        
        # Build understanding prompt
        prompt = self.prompt_templates['understanding'].format(
            message=message,
            context=json.dumps(user_context, default=str)[:200]  # Limit context size
        )
        
        # Generate understanding
        response = self.generate_response(prompt)
        
        # Parse response
        try:
            understanding = json.loads(response.strip())
        except:
            # Fallback parsing
            understanding = {
                "intent": "general",
                "entities": {},
                "confidence": 0.5,
                "missing_info": [],
                "urgency": "medium"
            }
        
        # Store interaction in memory
        self._store_interaction_memory(user_context.get('user_id'), message, understanding)
        
        return understanding
    
    def _get_memory_context(self, user_id: str, current_message: str) -> Dict[str, Any]:
        """Get relevant context from memory systems"""
        if not user_id:
            return {}
        
        try:
            # Get recent conversation
            recent_context = self.memory_manager.short_term.get_conversation_history(user_id, limit=3)
            
            # Get user patterns
            patterns = self.memory_manager.long_term.get_interaction_patterns(user_id, days_back=7)
            
            # Get preferences
            preferences = self.memory_manager.long_term.get_user_preferences(user_id)
            
            return {
                'recent_context': recent_context[:2],  # Limit for token efficiency
                'patterns': patterns[:1] if patterns else [],
                'preferences': preferences[:1] if preferences else []
            }
        except Exception as e:
            print(f"Error getting memory context: {str(e)}")
            return {}
    
    def _store_interaction_memory(self, user_id: str, message: str, understanding: Dict[str, Any]):
        """Store interaction in memory for learning"""
        if not user_id:
            return
        
        try:
            interaction_data = {
                'message': message,
                'understanding': understanding,
                'timestamp': datetime.now(),
                'agent_type': self.__class__.__name__
            }
            
            # Store in short-term memory
            self.memory_manager.short_term.store_context(
                user_id, 
                f"session_{datetime.now().strftime('%Y%m%d')}", 
                interaction_data
            )
            
            # If high confidence, store pattern in long-term memory
            if understanding.get('confidence', 0) > 0.7:
                self.memory_manager.long_term.store_interaction_pattern(
                    user_id=user_id,
                    pattern_type=understanding.get('intent', 'general'),
                    pattern_data={
                        'successful_understanding': True,
                        'confidence': understanding.get('confidence'),
                        'entities': understanding.get('entities', {}),
                        'time_of_day': datetime.now().hour
                    }
                )
        except Exception as e:
            print(f"Error storing interaction memory: {str(e)}")
    
    def execute_with_tools(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """Execute request using available tools (to be enhanced by subclasses)"""
        # Base implementation - subclasses should override
        return {
            'tool_responses': [],
            'execution_success': True,
            'requires_human_approval': False
        }
    
    def format_error_response(self, error_message: str) -> Dict[str, Any]:
        """Format error response"""
        return {
            'success': False,
            'error': error_message,
            'requires_action': False,
            'agent': self.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }
    
    def format_success_response(self, response_text: str, requires_action: bool = False, 
                              action_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format success response"""
        result = {
            'success': True,
            'response': response_text,
            'requires_action': requires_action,
            'agent': self.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }
        
        if action_data:
            result['action_data'] = action_data
        
        return result
    
    def check_human_approval_needed(self, request_data: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if human approval is needed for this action"""
        # Base logic - subclasses can override
        high_impact_intents = ['leave_request', 'payroll_calculation', 'candidate_decision']
        intent = request_data.get('intent', '')
        confidence = request_data.get('confidence', 1.0)
        
        return intent in high_impact_intents and confidence < 0.8
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics"""
        cache_hit_rate = (self.cache_hits / self.request_count) if self.request_count > 0 else 0
        
        return {
            'total_requests': self.request_count,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'cached_responses': len(self.response_cache),
            'agent_type': self.__class__.__name__
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self.response_cache.clear()
        self.context_cache.clear()
        print(f"Cache cleared for {self.__class__.__name__}")

from datetime import timedelta