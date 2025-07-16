# backend/agents/leave_agent.py
from agents.base_agent import BaseAgent
from models.leave import Leave
from models.user import User
from typing import Dict, Any, List
from datetime import datetime, timedelta
import re
import json

class LeaveAgent(BaseAgent):
    """
    Enhanced specialized agent for handling leave management requests
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        super().__init__(gemini_api_key, db_connection, memory_manager)
        self.leave_model = Leave(db_connection)
        self.user_model = User(db_connection)
        
        # Leave-specific prompt templates
        self.prompt_templates.update({
            'leave_understanding': """
            Analyze this leave-related message from {username} ({role}):
            Message: "{message}"
            Previous context: {context}
            
            Extract (respond in JSON only):
            {{
                "intent": "leave_request|leave_status|leave_approval|leave_history",
                "entities": {{
                    "leave_type": "annual|sick|casual|emergency|maternity|paternity",
                    "start_date": "YYYY-MM-DD or relative date",
                    "end_date": "YYYY-MM-DD or relative date",
                    "duration": "number of days",
                    "reason": "reason text",
                    "urgency": "low|medium|high",
                    "employee_name": "name if HR is asking about someone else"
                }},
                "confidence": 0.0-1.0,
                "missing_info": ["list of missing required fields"]
            }}
            
            Examples:
            "I need leave next week" → {{"intent": "leave_request", "entities": {{"start_date": "next week"}}, "confidence": 0.6}}
            "What's my leave balance?" → {{"intent": "leave_status", "entities": {{}}, "confidence": 0.9}}
            """,
            
            'leave_response': """
            Generate a helpful leave management response for: "{message}"
            
            User: {username} ({role})
            Intent: {intent}
            Available data: {tool_data}
            Form data: {form_data}
            
            Guidelines:
            - Be professional and helpful
            - Use specific data when available
            - For leave requests, guide through the process step by step
            - For HR users, provide management-level information
            - Support both English and Sinhala context
            - Keep response under 300 words
            """
        })
        
        # Available tools for leave management
        self.available_tools = [
            'check_leave_balance',
            'validate_leave_dates', 
            'create_leave_request',
            'get_leave_history',
            'check_team_availability',
            'notify_manager'
        ]
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced leave request processing with intelligent workflow"""
        try:
            # Extract request components
            intent = request_data.get('intent')
            message = request_data.get('message')
            entities = request_data.get('entities', {})
            user_context = request_data.get('user_context', {})
            
            # Enhanced understanding with leave-specific context
            understanding = self._enhanced_leave_understanding(message, user_context)
            
            # Merge with existing entities
            understanding['entities'].update(entities)
            
            # Route to appropriate handler
            if understanding['intent'] == 'leave_request':
                return self._handle_leave_request(message, understanding, user_context)
            elif understanding['intent'] == 'leave_status':
                return self._handle_leave_status(message, understanding, user_context)
            elif understanding['intent'] == 'leave_approval' and user_context.get('role') == 'hr':
                return self._handle_leave_approval(message, understanding, user_context)
            elif understanding['intent'] == 'leave_history':
                return self._handle_leave_history(message, understanding, user_context)
            else:
                return self.format_error_response("Unknown leave-related request")
                
        except Exception as e:
            return self.format_error_response(f"Error processing leave request: {str(e)}")
    
    def _enhanced_leave_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced understanding specifically for leave requests"""
        
        # Get leave-specific memory context
        memory_context = self._get_leave_memory_context(user_context.get('user_id'))
        
        # Build enhanced prompt
        prompt = self.prompt_templates['leave_understanding'].format(
            username=user_context.get('username', 'User'),
            role=user_context.get('role', 'user'),
            message=message,
            context=json.dumps(memory_context, default=str)[:300]
        )
        
        # Generate understanding
        response = self.generate_response(prompt)
        
        # Parse with fallback
        try:
            understanding = json.loads(response.strip())
        except:
            understanding = self._fallback_leave_understanding(message)
        
        return understanding
    
    def _fallback_leave_understanding(self, message: str) -> Dict[str, Any]:
        """Fallback understanding using pattern matching"""
        message_lower = message.lower()
        
        # Intent detection
        if any(word in message_lower for word in ['need leave', 'leave request', 'apply leave', 'ලීව්', 'නිවාඩු']):
            intent = 'leave_request'
        elif any(word in message_lower for word in ['leave balance', 'remaining leave', 'ශේෂය']):
            intent = 'leave_status'
        elif any(word in message_lower for word in ['leave history', 'past leave', 'ඉතිහාසය']):
            intent = 'leave_history'
        else:
            intent = 'general'
        
        # Basic entity extraction
        entities = {}
        
        # Extract leave type
        if any(word in message_lower for word in ['sick', 'ill', 'රෝග']):
            entities['leave_type'] = 'sick'
        elif any(word in message_lower for word in ['annual', 'vacation', 'වාර්ෂික']):
            entities['leave_type'] = 'annual'
        elif any(word in message_lower for word in ['casual', 'අනියම්']):
            entities['leave_type'] = 'casual'
        elif any(word in message_lower for word in ['emergency', 'urgent', 'හදිසි']):
            entities['leave_type'] = 'emergency'
        
        # Extract date mentions
        if any(word in message_lower for word in ['next week', 'ලබන සතියේ']):
            entities['start_date'] = 'next week'
        elif any(word in message_lower for word in ['tomorrow', 'හෙට']):
            entities['start_date'] = 'tomorrow'
        elif any(word in message_lower for word in ['today', 'අද']):
            entities['start_date'] = 'today'
        
        return {
            'intent': intent,
            'entities': entities,
            'confidence': 0.6,
            'missing_info': []
        }
    
    def _get_leave_memory_context(self, user_id: str) -> Dict[str, Any]:
        """Get leave-specific memory context"""
        if not user_id:
            return {}
        
        try:
            # Get recent leave interactions
            recent_context = self.memory_manager.short_term.get_conversation_history(user_id, limit=2)
            leave_interactions = [ctx for ctx in recent_context if 'leave' in str(ctx).lower()]
            
            # Get leave patterns
            leave_patterns = self.memory_manager.long_term.get_interaction_patterns(
                user_id, pattern_type='leave_request', days_back=30
            )
            
            return {
                'recent_leave_interactions': leave_interactions,
                'leave_patterns': leave_patterns[:1],  # Most recent pattern
                'user_leave_preferences': self._get_user_leave_preferences(user_id)
            }
        except:
            return {}
    
    def _get_user_leave_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's leave preferences from history"""
        try:
            # Get user's leave history to identify preferences
            history = self.leave_model.get_user_leave_history(user_id, limit=10)
            
            if not history:
                return {}
            
            # Analyze patterns
            leave_types = [leave.get('type', '') for leave in history]
            most_common_type = max(set(leave_types), key=leave_types.count) if leave_types else 'annual'
            
            return {
                'preferred_leave_type': most_common_type,
                'average_duration': sum(leave.get('duration', 1) for leave in history) / len(history),
                'total_leaves_taken': len(history)
            }
        except:
            return {}
    
    def _handle_leave_request(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave request creation with intelligent form handling"""
        user_id = user_context.get('user_id')
        session_id = user_context.get('session_id', 'default')
        entities = understanding.get('entities', {})
        missing_info = understanding.get('missing_info', [])
        
        # Check if there's an ongoing leave form
        existing_form = self.memory_manager.short_term.get_form_data(user_id, session_id, 'leave_request')
        
        if existing_form:
            return self._continue_leave_form(message, understanding, user_context, existing_form)
        
        # Check if we have enough information to proceed
        required_fields = ['leave_type', 'start_date', 'end_date']
        missing_fields = [field for field in required_fields if not entities.get(field)]
        
        if missing_fields:
            # Start collecting information
            form_data = {
                'collected_entities': entities,
                'missing_fields': missing_fields,
                'start_time': datetime.now().isoformat()
            }
            
            self.memory_manager.short_term.store_form_data(user_id, session_id, 'leave_request', form_data)
            
            response = self._generate_info_request(missing_fields, entities, user_context.get('username', 'User'))
            
            return self.format_success_response(
                response,
                requires_action=True,
                action_data={'form_type': 'leave_request', 'step': 'collecting_info'}
            )
        else:
            # We have enough information, proceed with creation
            return self._create_leave_request(entities, user_context)
    
    def _continue_leave_form(self, message: str, understanding: Dict[str, Any], 
                           user_context: Dict[str, Any], form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Continue with existing leave form"""
        user_id = user_context.get('user_id')
        session_id = user_context.get('session_id', 'default')
        
        # Merge new entities with collected data
        collected_entities = form_data.get('collected_entities', {})
        new_entities = understanding.get('entities', {})
        collected_entities.update(new_entities)
        
        # Extract additional info from current message
        additional_info = self._extract_leave_info_from_message(message)
        collected_entities.update(additional_info)
        
        # Check if form is now complete
        required_fields = ['leave_type', 'start_date', 'end_date']
        missing_fields = [field for field in required_fields if not collected_entities.get(field)]
        
        if not missing_fields:
            # Form is complete, create leave request
            self.memory_manager.short_term.clear_form_data(user_id, session_id, 'leave_request')
            return self._create_leave_request(collected_entities, user_context)
        else:
            # Still missing information, continue collecting
            form_data['collected_entities'] = collected_entities
            form_data['missing_fields'] = missing_fields
            self.memory_manager.short_term.store_form_data(user_id, session_id, 'leave_request', form_data)
            
            response = self._generate_info_request(missing_fields, collected_entities, user_context.get('username', 'User'))
            
            return self.format_success_response(
                response,
                requires_action=True,
                action_data={'form_type': 'leave_request', 'step': 'collecting_info'}
            )
    
    def _extract_leave_info_from_message(self, message: str) -> Dict[str, Any]:
        """Extract leave information from user message using patterns"""
        info = {}
        message_lower = message.lower()
        
        # Extract dates using patterns
        date_patterns = {
            r'(\d{1,2})/(\d{1,2})/(\d{4})': 'date_format',
            r'(\d{4})-(\d{1,2})-(\d{1,2})': 'iso_date',
            r'next week': 'next_week',
            r'tomorrow': 'tomorrow',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday': 'weekday'
        }
        
        for pattern, date_type in date_patterns.items():
            if re.search(pattern, message_lower):
                if 'start' in message_lower or 'from' in message_lower:
                    info['start_date'] = re.search(pattern, message_lower).group()
                elif 'end' in message_lower or 'to' in message_lower or 'until' in message_lower:
                    info['end_date'] = re.search(pattern, message_lower).group()
                else:
                    info['start_date'] = re.search(pattern, message_lower).group()
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*(day|days|week|weeks)', message_lower)
        if duration_match:
            number = int(duration_match.group(1))
            unit = duration_match.group(2)
            if 'week' in unit:
                number *= 7
            info['duration'] = number
        
        # Extract reason
        reason_patterns = [
            r'because\s+(.*)',
            r'for\s+(.*)',
            r'due to\s+(.*)',
            r'reason:\s*(.*)'
        ]
        
        for pattern in reason_patterns:
            match = re.search(pattern, message_lower)
            if match:
                info['reason'] = match.group(1).strip()
                break
        
        return info
    
    def _generate_info_request(self, missing_fields: List[str], 
                             collected_entities: Dict[str, Any], username: str) -> str:
        """Generate intelligent request for missing information"""
        
        if 'leave_type' in missing_fields:
            return f"""Hello {username}! I'd be happy to help you with your leave request. 📅
            
To get started, could you please tell me:
• **What type of leave** would you like to request?
  - Annual leave (vacation)
  - Sick leave
  - Casual leave  
  - Emergency leave

You can simply say something like "I need annual leave" or "sick leave request"."""
        
        elif 'start_date' in missing_fields:
            leave_type = collected_entities.get('leave_type', 'leave')
            return f"""Great! I understand you need {leave_type}. 📅

Could you please specify:
• **Start date**: When would you like your leave to begin?
  
Examples: "starting tomorrow", "from January 15th", "next Monday", "2024-01-15" """
        
        elif 'end_date' in missing_fields:
            start_date = collected_entities.get('start_date', '')
            return f"""Perfect! Your leave will start on {start_date}. 

Could you please tell me:
• **End date**: When would you like to return to work?
  
Examples: "until Friday", "end on January 19th", "for 3 days", "return on 2024-01-19" """
        
        else:
            missing_str = ', '.join(missing_fields)
            return f"I need a bit more information to process your leave request. Please provide: {missing_str}"
    
    def _create_leave_request(self, entities: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create the actual leave request with validation"""
        try:
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')
            
            # Use tools to validate and create leave request
            tool_results = self.execute_with_tools({
                'action': 'create_leave_request',
                'entities': entities,
                'user_context': user_context
            }, ['validate_leave_dates', 'check_leave_balance', 'create_leave_request'])
            
            if tool_results.get('execution_success'):
                # Generate success response
                leave_type = entities.get('leave_type', 'leave')
                start_date = entities.get('start_date', '')
                end_date = entities.get('end_date', '')
                
                response = f"""✅ **Leave Request Submitted Successfully!**

**Request Details:**
👤 Employee: {username}
📋 Type: {leave_type.title()} Leave  
📅 From: {start_date}
📅 To: {end_date}
📝 Reason: {entities.get('reason', 'Not specified')}

**Next Steps:**
🔄 Your request has been sent to your manager for approval
📧 You'll receive an email notification once it's reviewed
📱 You can check the status anytime by asking "What's my leave status?"

**Request ID:** {tool_results.get('request_id', 'Generated')}

Is there anything else I can help you with regarding your leave?"""

                requires_approval = self.check_human_approval_needed({'intent': 'leave_request'}, tool_results)
                
                return self.format_success_response(
                    response,
                    requires_action=requires_approval,
                    action_data={'request_id': tool_results.get('request_id'), 'type': 'leave_approval'}
                )
            else:
                error_msg = tool_results.get('error', 'Failed to create leave request')
                return self.format_error_response(f"❌ Unable to create leave request: {error_msg}")
                
        except Exception as e:
            return self.format_error_response(f"Error creating leave request: {str(e)}")
    
    def _handle_leave_status(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave status inquiries"""
        try:
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')
            
            # Execute tools to get leave status
            tool_results = self.execute_with_tools({
                'action': 'get_leave_status',
                'user_context': user_context
            }, ['check_leave_balance', 'get_leave_history'])
            
            # Generate response using template
            response = self._generate_leave_status_response(tool_results, username)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting leave status: {str(e)}")
    
    def _generate_leave_status_response(self, tool_results: Dict[str, Any], username: str) -> str:
        """Generate leave status response"""
        
        leave_balance = tool_results.get('leave_balance', {})
        recent_history = tool_results.get('recent_history', [])
        
        response = f"""📊 **Leave Status for {username}**

**Current Leave Balance:**
🏖️ Annual Leave: {leave_balance.get('annual', 21)} days
🏥 Sick Leave: {leave_balance.get('sick', 7)} days  
📝 Casual Leave: {leave_balance.get('casual', 7)} days

**Recent Leave History:**"""
        
        if recent_history:
            for leave in recent_history[:3]:
                status_emoji = "✅" if leave.get('status') == 'approved' else "⏳" if leave.get('status') == 'pending' else "❌"
                response += f"""
{status_emoji} {leave.get('start_date')} to {leave.get('end_date')} - {leave.get('type', '').title()} ({leave.get('status', 'unknown')})"""
        else:
            response += "\n📋 No recent leave history found"
        
        response += "\n\n💡 **Quick Actions:**\n• Request new leave: 'I need leave next week'\n• Check specific status: 'Status of my January leave'"
        
        return response
    
    def _handle_leave_approval(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave approval requests (HR only)"""
        if user_context.get('role') != 'hr':
            return self.format_error_response("❌ Leave approval functionality is only available for HR personnel.")
        
        try:
            # Execute tools to get pending approvals
            tool_results = self.execute_with_tools({
                'action': 'get_pending_approvals',
                'user_context': user_context
            }, ['get_pending_approvals', 'get_employee_details'])
            
            pending_requests = tool_results.get('pending_requests', [])
            
            if not pending_requests:
                return self.format_success_response("📋 No pending leave requests for approval at this time.")
            
            response = "📋 **Pending Leave Requests for Approval:**\n\n"
            
            for i, request in enumerate(pending_requests[:5], 1):
                response += f"""**{i}. {request.get('employee_name', 'Unknown')}**
📅 {request.get('start_date')} to {request.get('end_date')} ({request.get('duration', '?')} days)
📋 Type: {request.get('leave_type', '').title()}
📝 Reason: {request.get('reason', 'Not specified')}
🆔 Request ID: {request.get('request_id', 'N/A')}

"""
            
            response += "💡 To approve/reject: 'Approve request 12345' or 'Reject request 12345 - reason'"
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting leave approvals: {str(e)}")
    
    def _handle_leave_history(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave history requests"""
        try:
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')
            
            # Check if HR is asking about specific employee
            entities = understanding.get('entities', {})
            employee_name = entities.get('employee_name')
            
            if employee_name and user_context.get('role') != 'hr':
                return self.format_error_response("❌ You can only view your own leave history.")
            
            # Execute tools to get leave history
            tool_results = self.execute_with_tools({
                'action': 'get_leave_history',
                'employee_name': employee_name,
                'user_context': user_context
            }, ['get_leave_history'])
            
            history = tool_results.get('leave_history', [])
            target_user = employee_name if employee_name else username
            
            if not history:
                return self.format_success_response(f"📋 No leave history found for {target_user}.")
            
            response = f"📋 **Leave History for {target_user}**\n\n"
            
            for leave in history[:10]:  # Show last 10 leaves
                status_emoji = "✅" if leave.get('status') == 'approved' else "⏳" if leave.get('status') == 'pending' else "❌"
                response += f"""{status_emoji} **{leave.get('start_date')} to {leave.get('end_date')}**
   📋 {leave.get('type', '').title()} Leave ({leave.get('duration', '?')} days)
   📝 {leave.get('reason', 'No reason specified')}
   📊 Status: {leave.get('status', 'Unknown').title()}

"""
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting leave history: {str(e)}")
    
    def execute_with_tools(self, request_data: Dict[str, Any], tools: List[str]) -> Dict[str, Any]:
        """Execute request using leave-specific tools"""
        
        tool_responses = []
        execution_success = True
        result_data = {}
        
        try:
            action = request_data.get('action', '')
            user_context = request_data.get('user_context', {})
            user_id = user_context.get('user_id')
            
            # Execute tools based on action
            if action == 'create_leave_request':
                entities = request_data.get('entities', {})
                
                # Tool 1: Validate dates
                if 'validate_leave_dates' in tools:
                    date_validation = self._validate_leave_dates(entities, user_id)
                    tool_responses.append({'tool': 'validate_leave_dates', 'result': date_validation})
                    if not date_validation.get('valid', False):
                        execution_success = False
                        result_data['error'] = date_validation.get('error', 'Date validation failed')
                
                # Tool 2: Check leave balance
                if 'check_leave_balance' in tools and execution_success:
                    balance_check = self._check_leave_balance(user_id, entities.get('leave_type'))
                    tool_responses.append({'tool': 'check_leave_balance', 'result': balance_check})
                    if not balance_check.get('sufficient', False):
                        execution_success = False
                        result_data['error'] = f"Insufficient leave balance: {balance_check.get('message', '')}"
                
                # Tool 3: Create leave request
                if 'create_leave_request' in tools and execution_success:
                    creation_result = self._create_leave_db_entry(entities, user_context)
                    tool_responses.append({'tool': 'create_leave_request', 'result': creation_result})
                    result_data['request_id'] = creation_result.get('request_id')
                    
            elif action == 'get_leave_status':
                # Tool 1: Check leave balance
                if 'check_leave_balance' in tools:
                    balance = self._get_user_leave_balance(user_id)
                    result_data['leave_balance'] = balance
                    
                # Tool 2: Get recent history
                if 'get_leave_history' in tools:
                    history = self._get_user_leave_history(user_id, limit=5)
                    result_data['recent_history'] = history
                    
            elif action == 'get_pending_approvals':
                if 'get_pending_approvals' in tools:
                    pending = self._get_pending_leave_requests()
                    result_data['pending_requests'] = pending
                    
            elif action == 'get_leave_history':
                employee_name = request_data.get('employee_name')
                target_user_id = self._get_user_id_by_name(employee_name) if employee_name else user_id
                
                if 'get_leave_history' in tools:
                    history = self._get_user_leave_history(target_user_id, limit=20)
                    result_data['leave_history'] = history
            
        except Exception as e:
            execution_success = False
            result_data['error'] = str(e)
        
        return {
            'tool_responses': tool_responses,
            'execution_success': execution_success,
            'requires_human_approval': self._requires_human_approval(request_data),
            **result_data
        }
    
    # Tool implementation methods
    def _validate_leave_dates(self, entities: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Validate leave dates and check conflicts"""
        try:
            start_date = entities.get('start_date', '')
            end_date = entities.get('end_date', '')
            
            # Parse dates (simplified - would need more robust parsing)
            if start_date == 'tomorrow':
                start_dt = datetime.now() + timedelta(days=1)
            elif start_date == 'next week':
                start_dt = datetime.now() + timedelta(days=7)
            else:
                # Try to parse date string
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                except:
                    return {'valid': False, 'error': 'Invalid start date format'}
            
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                except:
                    # Calculate end date based on duration if available
                    duration = entities.get('duration', 1)
                    end_dt = start_dt + timedelta(days=duration-1)
            else:
                duration = entities.get('duration', 1)
                end_dt = start_dt + timedelta(days=duration-1)
            
            # Validate date logic
            if start_dt > end_dt:
                return {'valid': False, 'error': 'Start date cannot be after end date'}
            
            if start_dt < datetime.now().date():
                return {'valid': False, 'error': 'Cannot request leave for past dates'}
            
            # Check for conflicts (simplified)
            conflicts = self.leave_model.check_leave_conflicts(user_id, start_dt, end_dt)
            if conflicts:
                return {'valid': False, 'error': f'Conflicts with existing leave: {conflicts}'}
            
            duration = (end_dt - start_dt).days + 1
            
            return {
                'valid': True,
                'start_date': start_dt.strftime('%Y-%m-%d'),
                'end_date': end_dt.strftime('%Y-%m-%d'),
                'duration': duration
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Date validation error: {str(e)}'}
    
    def _check_leave_balance(self, user_id: str, leave_type: str) -> Dict[str, Any]:
        """Check if user has sufficient leave balance"""
        try:
            user_data = self.user_model.get_user_by_id(user_id)
            if not user_data:
                return {'sufficient': False, 'message': 'User not found'}
            
            # Get current balances (simplified - would be calculated from database)
            balances = {
                'annual': user_data.get('annual_leave_balance', 21),
                'sick': user_data.get('sick_leave_balance', 7),
                'casual': user_data.get('casual_leave_balance', 7),
                'emergency': 999  # Usually unlimited
            }
            
            current_balance = balances.get(leave_type, 0)
            
            return {
                'sufficient': current_balance > 0,
                'current_balance': current_balance,
                'message': f'Current {leave_type} leave balance: {current_balance} days'
            }
            
        except Exception as e:
            return {'sufficient': False, 'message': f'Error checking balance: {str(e)}'}
    
    def _create_leave_db_entry(self, entities: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create leave request entry in database"""
        try:
            leave_data = {
                'user_id': user_context.get('user_id'),
                'employee_name': user_context.get('username'),
                'leave_type': entities.get('leave_type'),
                'start_date': entities.get('start_date'),
                'end_date': entities.get('end_date'),
                'duration': entities.get('duration', 1),
                'reason': entities.get('reason', ''),
                'status': 'pending',
                'requested_date': datetime.now(),
                'requires_approval': True
            }
            
            request_id = self.leave_model.create_leave_request(leave_data)
            
            return {
                'success': True,
                'request_id': request_id,
                'message': 'Leave request created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create leave request: {str(e)}'
            }
    
    def _get_user_leave_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's current leave balance"""
        try:
            user_data = self.user_model.get_user_by_id(user_id)
            if not user_data:
                return {}
            
            return {
                'annual': user_data.get('annual_leave_balance', 21),
                'sick': user_data.get('sick_leave_balance', 7),
                'casual': user_data.get('casual_leave_balance', 7)
            }
        except:
            return {'annual': 21, 'sick': 7, 'casual': 7}  # Default values
    
    def _get_user_leave_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's leave history"""
        try:
            return self.leave_model.get_user_leave_history(user_id, limit=limit)
        except:
            return []
    
    def _get_pending_leave_requests(self) -> List[Dict[str, Any]]:
        """Get all pending leave requests for HR approval"""
        try:
            return self.leave_model.get_pending_requests()
        except:
            return []
    
    def _get_user_id_by_name(self, name: str) -> str:
        """Get user ID by name"""
        try:
            users = self.user_model.get_all_users()
            for user in users:
                if name.lower() in user.get('username', '').lower():
                    return user['user_id']
            return None
        except:
            return None
    
    def _requires_human_approval(self, request_data: Dict[str, Any]) -> bool:
        """Check if request requires human approval"""
        action = request_data.get('action', '')
        
        # Leave requests always need manager approval
        if action == 'create_leave_request':
            return True
        
        return False