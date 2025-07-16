# backend/agents/router_agent.py
import re
from typing import Dict, Any, Optional, Tuple
import google.generativeai as genai
from datetime import datetime
import json
import hashlib
from datetime import timedelta

class RouterAgent:
    """
    Enhanced central orchestrator that routes user messages to appropriate agents
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        self.gemini_api_key = gemini_api_key
        self.db_connection = db_connection
        self.memory_manager = memory_manager
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Enhanced intent patterns (Sinhala and English)
        self.intent_patterns = {
            'leave_request': [
                'leave.*request', 'need.*leave', 'apply.*leave', 'vacation', 'time.*off',
                'නිවාඩු.*ඉල්ලීම', 'ලීව්.*ඕන', 'නිවාඩු.*අයදුම්පත', 'නිවාඩු.*අවශ්‍ය',
                'ලීව්.*එක', 'නිවාඩු.*ගන්න', 'leave.*එකක්'
            ],
            'leave_status': [
                'leave.*status', 'leave.*balance', 'remaining.*leave', 'leave.*history',
                'නිවාඩු.*තත්වය', 'නිවාඩු.*ශේෂය', 'ඉතිරි.*නිවාඩු', 'නිවාඩු.*ඉතිහාසය',
                'leave.*balance', 'ශේෂ.*නිවාඩු'
            ],
            'candidate_search': [
                'find.*developer', 'java.*developer', 'candidates.*with', 'cv.*search',
                'developers.*who', 'candidates.*who.*know', 'apply.*කර.*ඇති',
                'සොයන්න.*developer', 'අපේක්ෂකයින්.*සමග', 'cv.*සෙවීම',
                'give.*me.*developers', 'show.*me.*candidates'
            ],
            'payroll_calculation': [
                'calculate.*payroll', 'salary.*calculation', 'payroll.*for', 'my.*payroll',
                'ගණනය.*වැටුප්', 'වැටුප්.*ගණනය', 'මගේ.*වැටුප්', 'payroll.*calculate',
                'ආදායම.*calculate', 'calculate.*ආදායම'
            ],
            'greeting': [
                'hello', 'hi', 'hey', 'good.*morning', 'good.*afternoon', 'how.*are.*you',
                'ආයුබෝවන්', 'හලෝ', 'සුභ.*උදෑසන', 'හම්බුන්ගමුව', 'කොහොමද'
            ],
            'help': [
                'help', 'what.*can.*do', 'how.*work', 'commands', 'support',
                'උදව්', 'මොනවද.*කරන්න', 'කොහොමද.*වැඩ.*කරන්නේ', 'help.*me'
            ]
        }
        
        # Caching for optimization
        self.intent_cache = {}
        self.routing_cache = {}
        
        # Performance tracking
        self.routing_requests = 0
        self.successful_routes = 0
        self.cache_hits = 0
    
    def process_message(self, message: str, user_context: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Enhanced message processing with intelligent routing and caching"""
        
        self.routing_requests += 1
        
        # Generate cache key for routing
        cache_key = self._generate_routing_cache_key(message, user_context)
        
        # Check routing cache
        if cache_key in self.routing_cache:
            cached_result = self.routing_cache[cache_key]
            # Check if cache is still valid (5 minutes)
            if datetime.now() - cached_result['timestamp'] < timedelta(minutes=5):
                self.cache_hits += 1
                return cached_result['result']
        
        try:
            # Enhanced intent classification
            intent, confidence, entities = self._enhanced_classify_intent(message, user_context)
            
            # Route to appropriate agent or handle directly
            routing_result = self.route_to_agent(intent, message, user_context, entities, confidence)
            
            # Cache successful routing
            if routing_result.get('success', False):
                self.successful_routes += 1
                self.routing_cache[cache_key] = {
                    'result': routing_result,
                    'timestamp': datetime.now()
                }
            
            # Store interaction in memory
            self._store_routing_memory(user_context.get('user_id'), message, intent, routing_result)
            
            return routing_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Routing error: {str(e)}',
                'requires_action': False,
                'agent': 'router'
            }
    
    def _enhanced_classify_intent(self, message: str, user_context: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """Enhanced intent classification with context awareness"""
        
        # Generate cache key
        cache_key = hashlib.md5(f"{message[:50]}{user_context.get('user_id', '')}".encode()).hexdigest()
        
        # Check intent cache
        if cache_key in self.intent_cache:
            cached = self.intent_cache[cache_key]
            if datetime.now() - cached['timestamp'] < timedelta(minutes=10):
                return cached['intent'], cached['confidence'], cached['entities']
        
        # Pattern-based classification (fast fallback)
        pattern_intent, pattern_confidence = self._pattern_based_classification(message)
        
        # Enhanced AI-based classification for complex cases
        if pattern_confidence < 0.8:
            ai_intent, ai_confidence, entities = self._ai_based_classification(message, user_context)
        else:
            ai_intent = pattern_intent
            ai_confidence = pattern_confidence
            entities = self._extract_entities(message, pattern_intent)
        
        # Combine results for final decision
        final_intent = ai_intent if ai_confidence > pattern_confidence else pattern_intent
        final_confidence = max(ai_confidence, pattern_confidence)
        
        # Cache the result
        self.intent_cache[cache_key] = {
            'intent': final_intent,
            'confidence': final_confidence,
            'entities': entities,
            'timestamp': datetime.now()
        }
        
        return final_intent, final_confidence, entities
    
    def _pattern_based_classification(self, message: str) -> Tuple[str, float]:
        """Fast pattern-based intent classification"""
        message_lower = message.lower()
        
        # Score each intent based on pattern matches
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 1
            
            if score > 0:
                # Normalize score
                intent_scores[intent] = min(score / len(patterns), 1.0)
        
        if not intent_scores:
            return 'general', 0.3
        
        # Get highest scoring intent
        best_intent = max(intent_scores.keys(), key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        # Boost confidence for clear matches
        if confidence >= 0.5:
            confidence = min(confidence + 0.3, 1.0)
        
        return best_intent, confidence
    
    def _ai_based_classification(self, message: str, user_context: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """AI-based intent classification for complex cases"""
        
        user_role = user_context.get('role', 'user')
        username = user_context.get('username', 'user')
        
        # Get relevant memory context
        memory_context = self._get_routing_memory_context(user_context.get('user_id'))
        
        # Build enhanced classification prompt
        prompt = f"""
        Analyze this message from {username} ({user_role}) and classify the intent:
        
        Message: "{message}"
        Context: {json.dumps(memory_context, default=str)[:200]}
        
        Respond in JSON format only:
        {{
            "intent": "leave_request|leave_status|candidate_search|payroll_calculation|greeting|help|general",
            "confidence": 0.0-1.0,
            "entities": {{
                "key": "value"
            }},
            "reasoning": "brief explanation"
        }}
        
        Intent definitions:
        - leave_request: User wants to request time off
        - leave_status: User wants to check leave balance/history
        - candidate_search: HR wants to find candidates (HR only)
        - payroll_calculation: Calculate salary/payroll
        - greeting: General greetings
        - help: User needs assistance
        - general: Everything else
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip())
            
            return (
                result.get('intent', 'general'),
                result.get('confidence', 0.5),
                result.get('entities', {})
            )
        except:
            return 'general', 0.3, {}
    
    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Enhanced entity extraction based on intent"""
        entities = {}
        message_lower = message.lower()
        
        if intent in ['leave_request', 'leave_status']:
            # Extract dates
            date_patterns = [
                'next week', 'tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                'ලබන සතියේ', 'හෙට', 'සදුදා', 'අඟහරුවාදා', 'බදාදා', 'බ්‍රහස්පතින්දා', 'සිකුරාදා'
            ]
            
            for pattern in date_patterns:
                if pattern in message_lower:
                    entities['date_mention'] = pattern
                    break
            
            # Extract leave type
            leave_types = {
                'sick': ['sick', 'ill', 'medical', 'රෝග', 'අසනීප'],
                'annual': ['annual', 'vacation', 'holiday', 'වාර්ෂික', 'නිවාඩු'],
                'casual': ['casual', 'personal', 'අනියම්'],
                'emergency': ['emergency', 'urgent', 'හදිසි', 'හදිසි']
            }
            
            for leave_type, keywords in leave_types.items():
                if any(keyword in message_lower for keyword in keywords):
                    entities['leave_type'] = leave_type
                    break
            
            # Extract duration
            duration_match = re.search(r'(\d+)\s*(day|days|week|weeks|දින|සතියක්)', message_lower)
            if duration_match:
                number = int(duration_match.group(1))
                unit = duration_match.group(2)
                if 'week' in unit or 'සතියක්' in unit:
                    number *= 7
                entities['duration'] = number
        
        elif intent == 'candidate_search':
            # Extract skills
            skills = ['java', 'python', 'javascript', 'react', 'angular', 'nodejs', 'spring', 'django', 
                     'php', 'c++', 'c#', '.net', 'mysql', 'mongodb', 'aws', 'docker']
            found_skills = []
            for skill in skills:
                if skill in message_lower:
                    found_skills.append(skill)
            if found_skills:
                entities['skills'] = found_skills
            
            # Extract position
            positions = ['developer', 'engineer', 'manager', 'analyst', 'designer', 'architect', 'lead']
            for position in positions:
                if position in message_lower:
                    entities['position'] = position
                    break
            
            # Extract experience level
            if any(word in message_lower for word in ['senior', 'experienced', 'lead']):
                entities['experience_level'] = 'senior'
            elif any(word in message_lower for word in ['junior', 'entry', 'fresher']):
                entities['experience_level'] = 'junior'
            elif any(word in message_lower for word in ['mid', 'intermediate']):
                entities['experience_level'] = 'mid'
        
        elif intent == 'payroll_calculation':
            # Extract employee names
            if ' for ' in message_lower:
                parts = message_lower.split(' for ')
                if len(parts) > 1:
                    name_part = parts[1].split()[0]
                    entities['employee_name'] = name_part
            
            # Extract department
            departments = ['it', 'hr', 'finance', 'marketing', 'sales', 'engineering', 'operations']
            for dept in departments:
                if dept in message_lower:
                    entities['department'] = dept
                    break
            
            # Check if asking for own payroll
            if any(word in message_lower for word in ['my', 'මගේ', 'own']):
                entities['self_payroll'] = True
        
        return entities
    
    def route_to_agent(self, intent: str, message: str, user_context: Dict[str, Any], 
                      entities: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Enhanced routing with permission checks and context awareness"""
        
        user_role = user_context.get('role', 'user')
        user_id = user_context.get('user_id', '')
        
        # Permission checks
        if intent == 'candidate_search' and user_role != 'hr':
            return {
                'success': False,
                'agent': 'router',
                'response': '❌ Access Denied: Candidate search functionality is only available for HR personnel.\n\nAs a regular user, you can:\n• Request leave\n• Check your leave status\n• View your payroll information',
                'requires_action': False,
                'confidence': 1.0
            }
        
        # Route based on intent with enhanced context
        if intent in ['leave_request', 'leave_status']:
            return {
                'success': True,
                'agent': 'leave_agent',
                'intent': intent,
                'message': message,
                'entities': entities,
                'user_context': user_context,
                'confidence': confidence,
                'requires_processing': True
            }
        
        elif intent == 'candidate_search':
            return {
                'success': True,
                'agent': 'ats_agent',
                'intent': intent,
                'message': message,
                'entities': entities,
                'user_context': user_context,
                'confidence': confidence,
                'requires_processing': True
            }
        
        elif intent == 'payroll_calculation':
            # Additional permission check for payroll
            employee_name = entities.get('employee_name')
            department = entities.get('department')
            
            if (employee_name or department) and user_role != 'hr':
                return {
                    'success': False,
                    'agent': 'router',
                    'response': '❌ Access Denied: You can only view your own payroll information.\n\nTry asking: "Calculate my payroll" or "Show me my salary details"',
                    'requires_action': False
                }
            
            return {
                'success': True,
                'agent': 'payroll_agent',
                'intent': intent,
                'message': message,
                'entities': entities,
                'user_context': user_context,
                'confidence': confidence,
                'requires_processing': True
            }
        
        elif intent in ['greeting', 'help']:
            return self._handle_general_conversation(intent, message, user_context, confidence)
        
        else:
            return self._handle_general_conversation('general', message, user_context, confidence)
    
    def _handle_general_conversation(self, intent: str, message: str, user_context: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Enhanced general conversation handling"""
        user_name = user_context.get('username', 'there')
        user_role = user_context.get('role', 'user')
        
        if intent == 'greeting':
            # Personalized greeting based on time and user role
            current_hour = datetime.now().hour
            if current_hour < 12:
                time_greeting = "Good morning"
            elif current_hour < 17:
                time_greeting = "Good afternoon"
            else:
                time_greeting = "Good evening"
            
            response = f"{time_greeting} {user_name}! 👋 I'm your HR AI assistant. How can I help you today?"
            
            if user_role == 'hr':
                response += "\n\n**As an HR user, you can:**\n• 🔍 Search and manage candidates\n• ✅ Review and approve leave requests\n• 💰 Calculate payroll for employees and departments\n• 📊 View team analytics"
            else:
                response += "\n\n**You can:**\n• 🏖️ Request leave\n• 📋 Check your leave status and balance\n• 💰 View your payroll information\n• 📞 Get help with HR processes"
            
            response += "\n\n💡 Try saying something like:\n• \"I need leave next week\"\n• \"What's my leave balance?\"\n• \"Calculate my payroll\""
            
            return {
                'success': True,
                'agent': 'router',
                'response': response,
                'requires_action': False,
                'confidence': confidence
            }
        
        elif intent == 'help':
            help_text = f"I'm your HR AI assistant, {user_name}! 🤖\n\n"
            
            if user_role == 'hr':
                help_text += """**HR Management Commands:**
🔍 **Candidate Search:**
• "Find Java developers"
• "Show me React candidates"
• "Give me developers with 5+ years experience"

💰 **Payroll Management:**
• "Calculate payroll for John Doe"
• "Show me IT department payroll"
• "Calculate my payroll"

✅ **Leave Management:**
• "Show pending leave requests"
• "Approve leave request 12345"
• "Check team leave status"

📊 **Analytics:**
• "Show team productivity"
• "Department statistics"
"""
            else:
                help_text += """**Available Commands:**
🏖️ **Leave Management:**
• "I need leave next week"
• "Request annual leave from Jan 15 to Jan 19"
• "What's my leave balance?"
• "Show my leave history"

💰 **Payroll Information:**
• "Calculate my payroll"
• "Show my salary details"
• "What's my monthly income?"

❓ **General Help:**
• "Help" - Show this message
• "Hello" - General greeting
"""
            
            help_text += "\n🌐 **Language Support:** You can communicate in English or Sinhala!"
            help_text += "\n\n❓ **Need specific help?** Just ask me naturally, like you would ask a colleague!"
            
            return {
                'success': True,
                'agent': 'router',
                'response': help_text,
                'requires_action': False,
                'confidence': confidence
            }
        
        else:
            # Handle general queries with context awareness
            memory_context = self._get_routing_memory_context(user_context.get('user_id'))
            
            # Try to understand what the user might be looking for
            suggestions = self._generate_smart_suggestions(message, user_context, memory_context)
            
            response = f"I'm not quite sure what you're looking for, {user_name}. 🤔\n\n"
            
            if suggestions:
                response += f"**Did you mean:**\n{suggestions}\n\n"
            
            response += "**I can help you with:**\n"
            response += "🏖️ Leave requests and status\n"
            response += "💰 Payroll calculations\n"
            
            if user_role == 'hr':
                response += "🔍 Candidate search and management\n"
                response += "✅ Leave approvals\n"
            
            response += "\n💡 Try asking: \"What can you do?\" for more detailed help!"
            
            return {
                'success': True,
                'agent': 'router',
                'response': response,
                'requires_action': False,
                'confidence': confidence
            }
    
    def _generate_smart_suggestions(self, message: str, user_context: Dict[str, Any], memory_context: Dict[str, Any]) -> str:
        """Generate smart suggestions based on message content and context"""
        suggestions = []
        message_lower = message.lower()
        
        # Check for partial matches
        if any(word in message_lower for word in ['leave', 'vacation', 'නිවාඩු']):
            suggestions.append("• Request leave: \"I need leave next week\"")
            suggestions.append("• Check balance: \"What's my leave balance?\"")
        
        if any(word in message_lower for word in ['salary', 'pay', 'money', 'වැටුප්']):
            suggestions.append("• View payroll: \"Calculate my payroll\"")
            if user_context.get('role') == 'hr':
                suggestions.append("• Department payroll: \"Calculate IT department payroll\"")
        
        if any(word in message_lower for word in ['candidate', 'developer', 'hire']) and user_context.get('role') == 'hr':
            suggestions.append("• Find candidates: \"Find Java developers\"")
            suggestions.append("• Search CVs: \"Show me React candidates\"")
        
        # Check recent interaction patterns
        if memory_context.get('recent_interactions'):
            for interaction in memory_context['recent_interactions']:
                if 'leave' in str(interaction).lower():
                    suggestions.append("• Continue leave process: \"Check my leave status\"")
                    break
        
        return '\n'.join(suggestions[:3])  # Limit to 3 suggestions
    
    def _get_routing_memory_context(self, user_id: str) -> Dict[str, Any]:
        """Get routing-specific memory context"""
        if not user_id:
            return {}
        
        try:
            # Get recent interactions
            recent_interactions = self.memory_manager.short_term.get_conversation_history(user_id, limit=3)
            
            # Get routing patterns
            routing_patterns = self.memory_manager.long_term.get_interaction_patterns(
                user_id, pattern_type='routing', days_back=7
            )
            
            return {
                'recent_interactions': recent_interactions,
                'routing_patterns': routing_patterns[:2],  # Limit for efficiency
                'user_preferences': self._get_user_routing_preferences(user_id)
            }
        except:
            return {}
    
    def _get_user_routing_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's routing preferences from interaction history"""
        try:
            # Analyze user's most common intents
            successful_interactions = self.memory_manager.long_term.get_successful_interactions(user_id, limit=20)
            
            if not successful_interactions:
                return {}
            
            intent_counts = {}
            for interaction in successful_interactions:
                intent = interaction.get('interaction_type', 'general')
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            most_common_intent = max(intent_counts.keys(), key=intent_counts.get) if intent_counts else 'general'
            
            return {
                'preferred_intent': most_common_intent,
                'intent_distribution': intent_counts,
                'total_interactions': len(successful_interactions)
            }
        except:
            return {}
    
    def _store_routing_memory(self, user_id: str, message: str, intent: str, routing_result: Dict[str, Any]):
        """Store routing interaction in memory"""
        if not user_id:
            return
        
        try:
            interaction_data = {
                'message': message,
                'intent': intent,
                'routing_result': {
                    'success': routing_result.get('success'),
                    'agent': routing_result.get('agent'),
                    'confidence': routing_result.get('confidence')
                },
                'timestamp': datetime.now(),
                'router_version': 'enhanced'
            }
            
            # Store in short-term memory
            self.memory_manager.short_term.store_context(
                user_id,
                f"routing_session_{datetime.now().strftime('%Y%m%d')}",
                interaction_data
            )
            
            # Store successful routing patterns in long-term memory
            if routing_result.get('success'):
                self.memory_manager.long_term.store_interaction_pattern(
                    user_id=user_id,
                    pattern_type='routing',
                    pattern_data={
                        'intent': intent,
                        'success': True,
                        'confidence': routing_result.get('confidence', 0.5),
                        'agent_routed': routing_result.get('agent'),
                        'time_of_day': datetime.now().hour
                    }
                )
        except Exception as e:
            print(f"Error storing routing memory: {str(e)}")
    
    def _generate_routing_cache_key(self, message: str, user_context: Dict[str, Any]) -> str:
        """Generate cache key for routing optimization"""
        key_components = [
            message[:30],  # First 30 chars of message
            user_context.get('role', 'user'),
            user_context.get('user_id', '')[:10]  # First 10 chars of user ID
        ]
        
        key_string = '|'.join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance statistics"""
        success_rate = (self.successful_routes / self.routing_requests) if self.routing_requests > 0 else 0
        cache_hit_rate = (self.cache_hits / self.routing_requests) if self.routing_requests > 0 else 0
        
        return {
            'total_routing_requests': self.routing_requests,
            'successful_routes': self.successful_routes,
            'success_rate': f"{success_rate:.2%}",
            'cache_hits': self.cache_hits,
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'cached_intents': len(self.intent_cache),
            'cached_routes': len(self.routing_cache),
            'agent_type': 'RouterAgent'
        }
    
    def clear_caches(self):
        """Clear all caches"""
        self.intent_cache.clear()
        self.routing_cache.clear()
        print("Router agent caches cleared")
    
    def optimize_performance(self):
        """Optimize router performance"""
        # Clean expired cache entries
        current_time = datetime.now()
        
        # Clean intent cache (10 minute expiry)
        expired_intent_keys = [
            key for key, value in self.intent_cache.items()
            if current_time - value['timestamp'] > timedelta(minutes=10)
        ]
        for key in expired_intent_keys:
            del self.intent_cache[key]
        
        # Clean routing cache (5 minute expiry)
        expired_routing_keys = [
            key for key, value in self.routing_cache.items()
            if current_time - value['timestamp'] > timedelta(minutes=5)
        ]
        for key in expired_routing_keys:
            del self.routing_cache[key]
        
        print(f"Router optimization: Removed {len(expired_intent_keys)} intent cache entries and {len(expired_routing_keys)} routing cache entries")

