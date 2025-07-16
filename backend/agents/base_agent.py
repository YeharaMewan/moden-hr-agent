# backend/agents/base_agent.py (Enhanced for LangGraph)
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Tuple
import json
import time
from datetime import datetime
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    Enhanced Base Agent with tool execution capabilities for LangGraph workflow
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        self.gemini_api_key = gemini_api_key
        self.db_connection = db_connection
        self.memory_manager = memory_manager
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Performance optimization
        self.response_cache = {}
        self.performance_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'average_response_time': 0.0,
            'token_usage': 0
        }
        
        # Base prompt templates
        self.prompt_templates = {
            'understanding': """
            Analyze this user request for HR system:
            
            Message: "{message}"
            Context: {context}
            
            Extract (JSON only):
            {{
                "intent": "primary intention",
                "entities": {{"key": "value pairs of extracted info"}},
                "confidence": 0.0-1.0,
                "missing_info": ["required info not provided"],
                "urgency": "low|medium|high",
                "language": "english|sinhala|mixed"
            }}
            """,
            
            'tool_decision': """
            Based on this request, decide which tools to use:
            
            Request: {request_data}
            Available Tools: {available_tools}
            
            Respond with JSON:
            {{
                "tools_to_use": ["tool1", "tool2"],
                "execution_order": ["tool1", "tool2"],
                "requires_human_approval": true/false,
                "reasoning": "explanation of tool selection"
            }}
            """,
            
            'human_approval_check': """
            Analyze if this action requires human approval:
            
            Action: {action}
            Data: {data}
            User Role: {user_role}
            
            Consider factors:
            - Sensitive data access
            - Financial implications
            - Policy compliance
            - Security concerns
            
            Return JSON: {{"requires_approval": true/false, "reason": "explanation"}}
            """
        }
        
        # Available tools (to be defined by subclasses)
        self.available_tools = []
    
    def generate_response(self, prompt: str, use_cache: bool = True) -> str:
        """
        Enhanced response generation with caching and performance tracking
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache and prompt in self.response_cache:
                self.performance_stats['cache_hits'] += 1
                return self.response_cache[prompt]
            
            # Optimize prompt for token efficiency
            optimized_prompt = self._optimize_prompt(prompt)
            
            # Generate response
            response = self.model.generate_content(optimized_prompt)
            result = response.text
            
            # Update performance stats
            self.performance_stats['total_requests'] += 1
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            # Cache the response
            if use_cache:
                self.response_cache[prompt] = result
            
            return result
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def execute_with_tools(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        Execute request using available tools with intelligent tool selection
        """
        try:
            # Decide which tools to use
            tool_decision = self._decide_tools(request_data, available_tools)
            
            if not tool_decision.get('tools_to_use'):
                return {
                    'tool_responses': [],
                    'execution_success': True,
                    'requires_human_approval': False,
                    'reasoning': 'No tools required for this request'
                }
            
            # Execute tools in order
            tool_responses = []
            execution_success = True
            
            for tool_name in tool_decision['execution_order']:
                try:
                    tool_response = self._execute_tool(tool_name, request_data)
                    tool_responses.append({
                        'tool': tool_name,
                        'response': tool_response,
                        'success': True
                    })
                except Exception as e:
                    tool_responses.append({
                        'tool': tool_name,
                        'error': str(e),
                        'success': False
                    })
                    execution_success = False
            
            # Check if human approval is needed
            requires_approval = self._check_human_approval_needed(request_data, tool_responses)
            
            return {
                'tool_responses': tool_responses,
                'execution_success': execution_success,
                'requires_human_approval': requires_approval,
                'reasoning': tool_decision.get('reasoning', ''),
                'tools_used': tool_decision['tools_to_use']
            }
            
        except Exception as e:
            return {
                'tool_responses': [],
                'execution_success': False,
                'requires_human_approval': False,
                'error': str(e)
            }
    
    def _decide_tools(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        Intelligent tool selection based on request analysis
        """
        try:
            # Build tool decision prompt
            prompt = self.prompt_templates['tool_decision'].format(
                request_data=json.dumps(request_data, default=str)[:500],
                available_tools=json.dumps(available_tools)
            )
            
            # Generate decision
            response = self.generate_response(prompt)
            
            # Parse response
            try:
                decision = json.loads(response.strip())
                
                # Validate tools exist
                valid_tools = [tool for tool in decision.get('tools_to_use', []) 
                             if tool in available_tools]
                
                decision['tools_to_use'] = valid_tools
                decision['execution_order'] = [tool for tool in decision.get('execution_order', []) 
                                             if tool in valid_tools]
                
                return decision
                
            except json.JSONDecodeError:
                # Fallback to rule-based selection
                return self._rule_based_tool_selection(request_data, available_tools)
            
        except Exception as e:
            return {
                'tools_to_use': [],
                'execution_order': [],
                'requires_human_approval': False,
                'reasoning': f'Error in tool selection: {str(e)}'
            }
    
    def _rule_based_tool_selection(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        Fallback rule-based tool selection
        """
        intent = request_data.get('intent', '')
        selected_tools = []
        
        # Basic rule-based selection
        if intent == 'leave_request' and 'create_leave_request' in available_tools:
            selected_tools = ['validate_leave_dates', 'create_leave_request']
        elif intent == 'leave_status' and 'check_leave_balance' in available_tools:
            selected_tools = ['check_leave_balance', 'get_leave_history']
        elif intent == 'candidate_search' and 'search_candidates' in available_tools:
            selected_tools = ['search_candidates', 'rank_candidates']
        elif intent == 'payroll_calculation' and 'calculate_payroll' in available_tools:
            selected_tools = ['calculate_payroll']
        
        # Filter to only available tools
        valid_tools = [tool for tool in selected_tools if tool in available_tools]
        
        return {
            'tools_to_use': valid_tools,
            'execution_order': valid_tools,
            'requires_human_approval': False,
            'reasoning': 'Rule-based tool selection'
        }
    
    def _execute_tool(self, tool_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific tool (to be implemented by subclasses)
        """
        # This is a base implementation - subclasses should override with actual tool logic
        return {
            'tool_name': tool_name,
            'result': 'Tool executed successfully',
            'timestamp': datetime.now().isoformat()
        }
    
    def _check_human_approval_needed(self, request_data: Dict[str, Any], tool_responses: List[Dict[str, Any]]) -> bool:
        """
        Check if human approval is needed based on request and tool responses
        """
        try:
            # Build approval check prompt
            prompt = self.prompt_templates['human_approval_check'].format(
                action=request_data.get('intent', ''),
                data=json.dumps(tool_responses, default=str)[:300],
                user_role=request_data.get('user_context', {}).get('role', 'user')
            )
            
            # Generate decision
            response = self.generate_response(prompt)
            
            # Parse response
            try:
                approval_check = json.loads(response.strip())
                return approval_check.get('requires_approval', False)
                
            except json.JSONDecodeError:
                # Fallback to rule-based approval check
                return self._rule_based_approval_check(request_data, tool_responses)
            
        except Exception as e:
            # Default to requiring approval on error
            return True
    
    def _rule_based_approval_check(self, request_data: Dict[str, Any], tool_responses: List[Dict[str, Any]]) -> bool:
        """
        Rule-based fallback for approval checking
        """
        intent = request_data.get('intent', '')
        user_role = request_data.get('user_context', {}).get('role', 'user')
        
        # Rules for approval requirement
        if intent == 'leave_request':
            # Leave requests always need manager approval
            return True
        
        if intent == 'payroll_calculation' and user_role != 'hr':
            # Non-HR users accessing payroll might need approval
            return False
        
        if intent == 'candidate_search':
            # HR functions generally don't need additional approval
            return False
        
        # Default to no approval needed
        return False
    
    def check_human_approval_needed(self, request_data: Dict[str, Any], tool_results: Dict[str, Any]) -> bool:
        """
        Public method to check if human approval is needed
        """
        return self._check_human_approval_needed(request_data, tool_results.get('tool_responses', []))
    
    def _optimize_prompt(self, prompt: str) -> str:
        """
        Optimize prompt for token efficiency
        """
        # Remove extra whitespace
        optimized = ' '.join(prompt.split())
        
        # Truncate if too long (rough estimate: 1 token ≈ 0.75 words)
        max_words = 1200  # Approximately 1600 tokens
        words = optimized.split()
        
        if len(words) > max_words:
            optimized = ' '.join(words[:max_words]) + "..."
        
        return optimized
    
    def _update_response_time(self, response_time: float):
        """
        Update average response time
        """
        try:
            total = self.performance_stats['total_requests']
            current_avg = self.performance_stats['average_response_time']
            
            self.performance_stats['average_response_time'] = (
                (current_avg * (total - 1)) + response_time
            ) / total
            
        except Exception as e:
            print(f"Error updating response time: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get current performance statistics
        """
        cache_hit_rate = 0
        if self.performance_stats['total_requests'] > 0:
            cache_hit_rate = (self.performance_stats['cache_hits'] / self.performance_stats['total_requests']) * 100
        
        return {
            'total_requests': self.performance_stats['total_requests'],
            'cache_hits': self.performance_stats['cache_hits'],
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'average_response_time': f"{self.performance_stats['average_response_time']:.2f}s",
            'cache_size': len(self.response_cache)
        }
    
    def understand_request(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced request understanding with context awareness
        """
        try:
            # Get relevant context from memory
            memory_context = self._get_memory_context(user_context.get('user_id'), message)
            
            # Build understanding prompt
            prompt = self.prompt_templates['understanding'].format(
                message=message,
                context=json.dumps(user_context, default=str)[:200]
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
            
        except Exception as e:
            return {
                "intent": "error",
                "entities": {},
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _get_memory_context(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Get relevant memory context for processing
        """
        try:
            # Get recent context
            recent_context = self.memory_manager.short_term.get_recent_context(user_id, limit=5)
            
            # Get relevant patterns
            patterns = self.memory_manager.long_term.get_relevant_patterns(user_id, message)
            
            return {
                'recent_interactions': recent_context,
                'learned_patterns': patterns,
                'context_available': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'context_available': False
            }
    
    def _store_interaction_memory(self, user_id: str, message: str, understanding: Dict[str, Any]):
        """
        Store interaction in memory for learning
        """
        try:
            # Store in short-term memory
            interaction_data = {
                'message': message,
                'intent': understanding.get('intent'),
                'entities': understanding.get('entities', {}),
                'confidence': understanding.get('confidence', 0.0),
                'timestamp': datetime.now().isoformat(),
                'agent_type': self.__class__.__name__
            }
            
            self.memory_manager.short_term.store_context(
                user_id=user_id,
                context_data=interaction_data
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
    
    def format_success_response(self, response_text: str, requires_action: bool = False, 
                              action_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Format successful response
        """
        return {
            'success': True,
            'response': response_text,
            'requires_action': requires_action,
            'action_data': action_data or {},
            'agent': self.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }
    
    def format_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Format error response
        """
        return {
            'success': False,
            'error': error_message,
            'requires_action': False,
            'agent': self.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }
    
    @abstractmethod
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process request - must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def format_response(self, response_data: Dict[str, Any]) -> str:
        """
        Format response for user - must be implemented by subclasses
        """
        pass