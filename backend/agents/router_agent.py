# backend/agents/router_agent.py - Truly Agentic Version

import re
from typing import Dict, Any, Optional, Tuple
import google.generativeai as genai
from datetime import datetime, timedelta
import json
import hashlib

class RouterAgent:
    """
    Truly Agentic Router - ALL messages go through full workflow
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
                # Be specific: Look for words indicating an application or request
                r'apply for leave', r'request.*leave', r'need.*leave', r'want.*leave',
                r'නිවාඩු.*ඉල්ලන්න', r'ලීව්.*දාන්න', r'නිවාඩුවක්.*ඕන'
            ],
            'leave_status': [
                # Look for words indicating a query about status or balance
                r'leave.*status', r'balance', r'remaining.*leave', r'leave.*history', r'sick days',
                r'තත්වය', r'ශේෂය', r'ඉතිරි', r'ඉතිහාසය'
            ],
            'leave_approval': [ 
                r'approve', r'reject', r'pending.*leave', r'for approval',
                r'අනුමත', r'ප්‍රතික්ෂේප', r'pending'
            ],
            'candidate_search': [
                r'find.*candidate', r'search.*candidate', r'find.*developer', r'cv', r'resume', r'applicant',
                r'සොයන්න', r'අපේක්ෂක', r'සීවී'
            ],
            'payroll_calculation': [
                r'payroll', r'salary', r'calculate.*pay', r'calculate.*salary', r'my salary',
                r'වැටුප්', r'පඩි', r'ගනනය', r'ගණනය'
            ],
            'greeting': [
                r'hello', r'hi', r'hey', r'good morning', r'good afternoon', r'how are you',
                r'ආයුබෝවන්', r'හලෝ', r'සුභ', r'කොහොමද'
            ],
            'help': [
                r'help', r'support', r'assist', r'what.*can.*do', r'how.*work',
                r'උදව්', r'සහය', r'කරන්න පුලුවන්'
            ],
            'general': [
                r'thanks', r'thank you', r'ok', r'okay', r'bye', r'goodbye',
                r'ස්තූතියි', r'හරි', 'ගිහින් එන්නම්'
            ]
        }
        
        # Performance tracking
        self.routing_requests = 0
        self.successful_routes = 0
        self.cache_hits = 0
        
        # Intent and routing caches
        self.intent_cache = {}
        self.routing_cache = {}
        
        # Available tools for truly agentic behavior
        self.available_tools = [
            'memory_retrieval',
            'user_context_analysis', 
            'conversation_history',
            'personalization_engine',
            'response_enhancement'
        ]
    
    def route_request(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main routing method - TRULY AGENTIC VERSION
        All messages go through full analysis and workflow
        """
        try:
            print(f"🤖 Agentic Router: Processing '{message}' for {user_context.get('username', 'User')}")
            
            # STEP 1: Enhanced intent classification with context
            intent, confidence, entities = self._enhanced_classify_intent(message, user_context)
            
            # STEP 2: Retrieve user memory and conversation history
            user_memory = self._retrieve_user_memory(user_context.get('user_id'))
            conversation_context = self._get_conversation_context(user_context.get('user_id'))
            
            # STEP 3: Analyze user patterns and preferences
            user_patterns = self._analyze_user_patterns(user_context, user_memory)
            
            # STEP 4: Enhance intent with contextual information
            enhanced_intent = self._enhance_intent_with_context(
                intent, message, user_context, user_patterns, conversation_context
            )
            
            print(f"🧠 Intent: {intent} → Enhanced: {enhanced_intent['intent']} (confidence: {confidence:.2f})")
            
            # STEP 5: Determine routing strategy (ALL intents go through workflow)
            routing_result = {
                "intent": enhanced_intent['intent'],
                "original_intent": intent,
                "confidence": confidence,
                "entities": entities,
                "enhanced_entities": enhanced_intent.get('enhanced_entities', {}),
                "agent": self._get_agent_for_intent(enhanced_intent['intent']),
                "success": True,
                "user_memory": user_memory,
                "conversation_context": conversation_context,
                "user_patterns": user_patterns,
                "requires_workflow": True,  # ALWAYS True for agentic behavior
                "agentic_context": {
                    "personalization": enhanced_intent.get('personalization', {}),
                    "context_aware": True,
                    "memory_enhanced": bool(user_memory),
                    "pattern_aware": bool(user_patterns)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # STEP 6: Store routing decision with full context
            self._store_enhanced_routing_memory(user_context.get('user_id'), message, routing_result)
            
            return routing_result
            
        except Exception as e:
            print(f"❌ Agentic Router error: {e}")
            return {
                "intent": "error",
                "confidence": 0.0,
                "entities": {},
                "agent": "router",
                "success": False,
                "error": str(e),
                "requires_workflow": True,  # Even errors go through workflow
                "timestamp": datetime.now().isoformat()
            }
    
    def _enhance_intent_with_context(self, intent: str, message: str, user_context: Dict[str, Any], 
                                   user_patterns: Dict[str, Any], conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance intent classification with contextual AI analysis
        This makes the system truly intelligent and agentic
        """
        try:
            # Create context-aware prompt for Gemini
            context_prompt = f"""
            Analyze this user message with full context awareness:
            
            **Message:** {message}
            **Initial Intent:** {intent}
            **User Role:** {user_context.get('role', 'user')}
            **User Department:** {user_context.get('department', 'unknown')}
            **User Patterns:** {json.dumps(user_patterns, indent=2)}
            **Recent Context:** {json.dumps(conversation_context, indent=2)}
            
            As an agentic HR AI system, provide enhanced analysis:
            1. Confirm or refine the intent classification
            2. Extract additional contextual entities
            3. Identify personalization opportunities
            4. Suggest proactive assistance
            5. Detect emotional tone and urgency
            
            Return JSON format:
            {{
                "intent": "confirmed_or_refined_intent",
                "confidence_adjustment": 0.1,
                "enhanced_entities": {{}},
                "personalization": {{
                    "user_preference": "detected_preference",
                    "communication_style": "formal/casual",
                    "proactive_suggestions": []
                }},
                "emotional_context": {{
                    "tone": "professional/urgent/casual",
                    "urgency_level": "low/medium/high"
                }},
                "agentic_insights": []
            }}
            """
            
            response = self.model.generate_content(context_prompt)
            enhanced_data = json.loads(response.text)
            
            # Apply confidence adjustment
            adjusted_confidence = min(1.0, max(0.0, 
                enhanced_data.get('confidence_adjustment', 0.0)
            ))
            
            return {
                "intent": enhanced_data.get('intent', intent),
                "enhanced_entities": enhanced_data.get('enhanced_entities', {}),
                "personalization": enhanced_data.get('personalization', {}),
                "emotional_context": enhanced_data.get('emotional_context', {}),
                "agentic_insights": enhanced_data.get('agentic_insights', []),
                "confidence_adjustment": adjusted_confidence
            }
            
        except Exception as e:
            print(f"⚠️ Context enhancement warning: {e}")
            return {
                "intent": intent,
                "enhanced_entities": {},
                "personalization": {},
                "emotional_context": {},
                "agentic_insights": [],
                "confidence_adjustment": 0.0
            }
    
    def _retrieve_user_memory(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user's memory for contextual understanding"""
        try:
            if not self.memory_manager or not user_id:
                return {}
            
            # Get recent interactions
            recent_memory = self.memory_manager.short_term.get_conversation_history(user_id, limit=5)
            
            # Get learned patterns  
            long_term_patterns = self.memory_manager.long_term.get_interaction_patterns(user_id)
            
            return {
                "recent_interactions": recent_memory,
                "learned_patterns": long_term_patterns,
                "memory_available": True
            }
            
        except Exception as e:
            print(f"⚠️ Memory retrieval warning: {e}")
            return {"memory_available": False}
    
    def _get_conversation_context(self, user_id: str) -> Dict[str, Any]:
        """Get current conversation context"""
        try:
            # This would typically retrieve from session or database
            return {
                "session_active": True,
                "message_count": 1,
                "last_interaction": datetime.now().isoformat()
            }
        except:
            return {}
    
    def _analyze_user_patterns(self, user_context: Dict[str, Any], user_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user patterns for personalization"""
        try:
            patterns = {
                "communication_style": "professional",
                "preferred_language": "english",
                "common_requests": [],
                "time_patterns": {},
                "department_context": user_context.get('department', 'unknown')
            }
            
            # Analyze from memory if available
            if user_memory.get('learned_patterns'):
                patterns.update(user_memory['learned_patterns'])
            
            return patterns
            
        except:
            return {}
    
    def _store_enhanced_routing_memory(self, user_context: Dict[str, Any], message: str, routing_result: Dict[str, Any]):
        """Store enhanced routing decision with full context"""
        try:
            user_id = user_context.get('user_id')
            session_id = user_context.get('session_id')

            if not all([self.memory_manager, user_id, session_id]):
                return
            
            memory_entry = {
                "message": message,
                "routing_decision": routing_result,
                "timestamp": datetime.now().isoformat(),
                "agentic_processing": True,
                "context_enhanced": True
            }
            
            # Store in short-term memory
            self.memory_manager.short_term.store_context(user_id,session_id, memory_entry)
            
            # Update long-term patterns
            self.memory_manager.long_term.update_user_patterns(user_id, {
                "interaction_count": 1,
                "last_intent": routing_result['intent'],
                "preferred_processing": "agentic"
            })
            
        except Exception as e:
            print(f"⚠️ Memory storage warning: {e}")
    
    def _enhanced_classify_intent(self, message: str, user_context: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """Enhanced intent classification with AI and patterns"""
        try:
            message_lower = message.lower()
            
            # Check pattern matching first
            pattern_intent, pattern_confidence = self._pattern_match_intent(message_lower)
            
            # Use AI for enhanced classification
            ai_intent, ai_confidence, entities = self._ai_classify_intent(message, user_context)
            
            # Combine results intelligently
            if pattern_confidence > 0.8:
                final_intent = pattern_intent
                final_confidence = pattern_confidence
            elif ai_confidence > 0.7:
                final_intent = ai_intent  
                final_confidence = ai_confidence
            else:
                final_intent = pattern_intent if pattern_confidence > ai_confidence else ai_intent
                final_confidence = max(pattern_confidence, ai_confidence)
            
            print(f"🎯 Intent Classification: Pattern={pattern_intent}({pattern_confidence:.2f}), AI={ai_intent}({ai_confidence:.2f}) → Final={final_intent}({final_confidence:.2f})")
            
            return final_intent, final_confidence, entities
            
        except Exception as e:
            print(f"❌ Intent classification error: {e}")
            return "general", 0.5, {}
    
    def _pattern_match_intent(self, message: str) -> Tuple[str, float]:
        """Pattern-based intent matching"""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    return intent, 0.9
        return "general", 0.3
    
    def _ai_classify_intent(self, message: str, user_context: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """AI-powered intent classification"""
        try:
            # A simpler, more robust prompt
            prompt = f"""
            Analyze the user's message and classify its primary intent.
            Message: "{message}"
            Available intents are: leave_request, leave_status, candidate_search, payroll_calculation, greeting, help, general.
            Respond with a single word for the intent. For example: payroll_calculation
            """
            
            response = self.model.generate_content(prompt)

            # Clean the response text to get a single intent word
            result_intent = response.text.strip().lower().replace(".", "")

            # Basic validation to ensure the result is one of the available intents
            available_intents = self.intent_patterns.keys()
            if result_intent in available_intents:
                # Since AI classification is now simpler, we can assign a moderate confidence
                return result_intent, 0.75, {}
            else:
                # If the AI returns something unexpected, fallback gracefully
                return "general", 0.4, {}
            
        except Exception as e:
            print(f"⚠️ AI classification warning: {e}")
            return "general", 0.5, {}
    
    def _get_agent_for_intent(self, intent: str) -> str:
        """Get the appropriate agent name for an intent"""
        agent_mapping = {
            'leave_request': 'leave_agent',
            'leave_status': 'leave_agent',
            'candidate_search': 'ats_agent',
            'payroll_calculation': 'payroll_agent',
            'greeting': 'router_agent',  # Still goes through workflow
            'help': 'router_agent',      # Still goes through workflow  
            'general': 'router_agent',   # Still goes through workflow
            'error': 'router_agent'
        }
        
        return agent_mapping.get(intent, 'router_agent')
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process requests that come through the workflow
        This handles greeting, help, and general queries in an agentic way
        """
        try:
            intent = request_data.get('intent')
            message = request_data.get('message')
            user_context = request_data.get('user_context', {})
            
            print(f"🤖 RouterAgent processing workflow request: {intent}")
            
            # Generate contextual, personalized responses using AI
            if intent == 'greeting':
                return self._generate_agentic_greeting(message, user_context, request_data)
            elif intent == 'help':
                return self._generate_agentic_help(message, user_context, request_data)
            elif intent == 'general':
                return self._generate_agentic_general_response(message, user_context, request_data)
            else:
                return self._generate_fallback_response(message, user_context, request_data)
                
        except Exception as e:
            return {
                "success": False,
                "response": f"I encountered an error processing your request: {str(e)}",
                "requires_human_approval": False,
                "confidence": 0.0
            }
    
    def _generate_agentic_greeting(self, message: str, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates an intelligent, context-aware greeting. It uses AI for the first greeting
        in a session and cycles through a predefined list for any subsequent greetings to
        ensure variety and natural conversation flow.
        """
        try:
            username = user_context.get('full_name') or user_context.get('username', 'there')
            messages_in_current_session = request_data.get('messages_history', [])

            # --- CORRECTED & SIMPLIFIED LOGIC ---
            # Check for greetings in the history, EXCLUDING the current message.
            previous_messages = messages_in_current_session[:-1]
            is_first_greeting = not any(
                re.search(p, msg.get('content', '').lower())
                for p in self.intent_patterns['greeting']
                for msg in previous_messages
            )

            ai_response = ""

            if is_first_greeting:
                # For the first greeting in a session, use AI for a personalized welcome.
                greeting_prompt = f"""
                As a friendly and professional HR AI assistant, generate a warm, welcoming response for {username}.
                Briefly state your purpose and offer 2-3 examples of what you can help with (e.g., leave, payroll, candidates).
                """
                response = self.model.generate_content(greeting_prompt)
                ai_response = response.text.strip()
            else:
                # For any subsequent greetings in the same session, cycle through a list of varied responses.
                greeting_count = sum(1 for msg in previous_messages if any(re.search(p, msg.get('content','').lower()) for p in self.intent_patterns['greeting']))

                varied_responses = [
                    f"Hello again, {username}! How can I be of assistance?",
                    "Yes, I'm here and ready to help. What's next?",
                    f"Hi again, {username}! What can I do for you now?",
                    "I'm still here and ready to assist.",
                ]
                
                # The modulo operator ensures a different response each time.
                ai_response = varied_responses[greeting_count % len(varied_responses)]
            
            return {
                "success": True,
                "response": ai_response,
                "requires_human_approval": False,
                "confidence": 0.99,
                "agentic_features": ["context_aware", "session_aware", "varied_response"],
            }

        except Exception as e:
            print(f"⚠️ AI greeting generation warning: {e}")
            username = user_context.get('username', 'there')
            return { "success": True, "response": f"Hello {username}! How can I help you today?", "requires_human_approval": False, "confidence": 0.7 }

    
    def _generate_agentic_help(self, message: str, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate intelligent, role-specific help using AI"""
        try:
            role = user_context.get('role', 'user')
            department = user_context.get('department', 'team')
            
            help_prompt = f"""
            Generate comprehensive, role-specific help for an HR AI assistant:
            
            User Role: {role}
            Department: {department}
            Request: "{message}"
            
            Create help content that:
            1. Lists capabilities specific to their role
            2. Provides concrete examples they can try
            3. Includes both English and Sinhala examples
            4. Shows advanced AI features available
            5. Is well-formatted and easy to scan
            6. Demonstrates agentic intelligence
            
            Make it helpful and encouraging.
            """
            
            response = self.model.generate_content(help_prompt)
            ai_response = response.text.strip()
            
            return {
                "success": True,
                "response": ai_response,
                "requires_human_approval": False,
                "confidence": 0.95,
                "agentic_features": ["ai_generated", "role_specific", "comprehensive"],
                "tools_used": ["role_analysis", "capability_mapping"]
            }
            
        except Exception as e:
            print(f"⚠️ AI help generation warning: {e}")
            return {
                "success": True,
                "response": "I'm here to help with HR tasks! Ask me about leave requests, payroll calculations, or finding candidates.",
                "requires_human_approval": False,
                "confidence": 0.7
            }
    
    def _generate_agentic_general_response(self, message: str, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate intelligent general responses using AI"""
        try:
            general_prompt = f"""
            Generate a helpful response as an agentic HR AI assistant:
            
            User message: "{message}"
            User role: {user_context.get('role', 'user')}
            
            Analyze the message and provide:
            1. Acknowledgment of their message
            2. Relevant HR assistance offered
            3. Specific suggestions based on their likely needs
            4. Examples in English and Sinhala
            5. Encouraging next steps
            
            Be helpful, intelligent, and show AI capabilities.
            """
            
            response = self.model.generate_content(general_prompt)
            ai_response = response.text.strip()
            
            return {
                "success": True,
                "response": ai_response,
                "requires_human_approval": False,
                "confidence": 0.85,
                "agentic_features": ["ai_generated", "contextual", "helpful"],
                "tools_used": ["intent_analysis", "response_generation"]
            }
            
        except Exception as e:
            print(f"⚠️ AI general response warning: {e}")
            return {
                "success": True,
                "response": "I understand you're looking for assistance. I can help with leave requests, payroll calculations, and candidate searches. What specific task would you like help with?",
                "requires_human_approval": False,
                "confidence": 0.7
            }
    
    def _generate_fallback_response(self, message: str, user_context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback response"""
        return {
            "success": True,
            "response": "I'm processing your request through my agentic workflow. Let me help you with that.",
            "requires_human_approval": False,
            "confidence": 0.6,
            "agentic_features": ["workflow_processed"]
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "total_requests": self.routing_requests,
            "successful_routes": self.successful_routes,
            "success_rate": f"{(self.successful_routes/max(1, self.routing_requests)*100):.1f}%",
            "cache_hit_rate": f"{(self.cache_hits/max(1, self.routing_requests)*100):.1f}%",
            "agentic_mode": True
        }
    
    def optimize_performance(self):
        """Optimize performance"""
        # Clear old cache entries
        current_time = datetime.now()
        self.intent_cache.clear()
        self.routing_cache.clear()
        print("✅ RouterAgent cache cleared and optimized")