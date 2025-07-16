# backend/agents/leave_agent.py (Enhanced for LangGraph)
from agents.base_agent import BaseAgent
from models.leave import Leave
from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime, timedelta
from dateutil.parser import parse

class LeaveAgent(BaseAgent):
    """
    Enhanced Leave Agent with intelligent leave management and tool integration
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        super().__init__(gemini_api_key, db_connection, memory_manager)
        self.leave_model = Leave(db_connection)
        
        # Leave-specific prompt templates
        self.prompt_templates.update({
            'leave_understanding': """
            Analyze this leave-related request from user:
            Message: "{message}"
            User Context: {user_context}
            
            Extract (respond in JSON only):
            {{
                "intent": "leave_request|leave_status|leave_history|leave_approval",
                "entities": {{
                    "leave_type": "annual|sick|casual|maternity|paternity|emergency",
                    "start_date": "YYYY-MM-DD",
                    "end_date": "YYYY-MM-DD",
                    "duration": "number of days",
                    "reason": "leave reason",
                    "urgency": "low|medium|high",
                    "employee_name": "if requesting for someone else"
                }},
                "confidence": 0.0-1.0,
                "requires_form": true/false,
                "missing_info": ["list of missing required information"],
                "language": "english|sinhala|mixed"
            }}
            
            Examples:
            "මට leave request එකක් දැමීමට අවශයි" → {{"intent": "leave_request", "requires_form": true}}
            "I need leave next week" → {{"intent": "leave_request", "entities": {{"urgency": "medium"}}}}
            "What's my leave balance?" → {{"intent": "leave_status"}}
            """,
            
            'leave_response': """
            Generate a helpful leave management response for: "{message}"
            
            User: {username} ({role})
            Intent: {intent}
            Tool Results: {tool_results}
            Form Data: {form_data}
            
            Guidelines:
            - Be professional and helpful
            - Use specific data when available
            - For leave requests, guide through the process step by step
            - For HR users, provide management-level information
            - Support both English and Sinhala context
            - Include relevant emojis for better UX
            - Keep response under 300 words
            """,
            
            'leave_form_guide': """
            Generate a leave request form guide for the user:
            
            Current entities: {entities}
            Missing information: {missing_info}
            
            Create a conversational form request that asks for missing information naturally.
            Format as a friendly HR assistant would.
            """
        })
        
        # Available tools for leave management
        self.available_tools = [
            'check_leave_balance',
            'validate_leave_dates',
            'create_leave_request',
            'get_leave_history',
            'check_team_availability',
            'get_pending_approvals',
            'approve_leave_request',
            'reject_leave_request',
            'notify_manager'
        ]
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced leave request processing with intelligent workflow
        """
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
            elif understanding['intent'] == 'leave_history':
                return self._handle_leave_history(message, understanding, user_context)
            elif understanding['intent'] == 'leave_approval' and user_context.get('role') == 'hr':
                return self._handle_leave_approval(message, understanding, user_context)
            else:
                return self._handle_general_leave_query(message, understanding, user_context)
                
        except Exception as e:
            return self.format_error_response(f"Error processing leave request: {str(e)}")
    
    def _enhanced_leave_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced leave understanding with context
        """
        try:
            # Use base understanding first
            base_understanding = self.understand_request(message, user_context)
            
            # Enhance with leave-specific logic
            enhanced_understanding = self._enhance_leave_entities(message, base_understanding)
            
            return enhanced_understanding
            
        except Exception as e:
            return {
                'intent': 'leave_request',
                'entities': {},
                'confidence': 0.5,
                'error': str(e)
            }
    
    def _enhance_leave_entities(self, message: str, understanding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance understanding with leave-specific entity extraction
        """
        message_lower = message.lower()
        entities = understanding.get('entities', {})
        
        # Extract leave type
        if not entities.get('leave_type'):
            if any(word in message_lower for word in ['sick', 'medical', 'hospital', 'doctor']):
                entities['leave_type'] = 'sick'
            elif any(word in message_lower for word in ['annual', 'vacation', 'holiday']):
                entities['leave_type'] = 'annual'
            elif any(word in message_lower for word in ['casual', 'personal']):
                entities['leave_type'] = 'casual'
            elif any(word in message_lower for word in ['maternity', 'pregnancy']):
                entities['leave_type'] = 'maternity'
            elif any(word in message_lower for word in ['paternity', 'father']):
                entities['leave_type'] = 'paternity'
            elif any(word in message_lower for word in ['emergency', 'urgent']):
                entities['leave_type'] = 'emergency'
        
        # Extract dates
        if not entities.get('start_date'):
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
                r'(\d{1,2}-\d{1,2}-\d{4})',  # MM-DD-YYYY
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, message)
                if matches:
                    try:
                        entities['start_date'] = parse(matches[0]).strftime('%Y-%m-%d')
                        if len(matches) > 1:
                            entities['end_date'] = parse(matches[1]).strftime('%Y-%m-%d')
                    except:
                        pass
        
        # Extract duration
        if not entities.get('duration'):
            duration_patterns = [
                r'(\d+)\s*days?',
                r'(\d+)\s*weeks?',
                r'for\s*(\d+)',
            ]
            
            for pattern in duration_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    if 'week' in pattern:
                        entities['duration'] = int(match.group(1)) * 7
                    else:
                        entities['duration'] = int(match.group(1))
                    break
        
        # Extract urgency
        if not entities.get('urgency'):
            if any(word in message_lower for word in ['urgent', 'emergency', 'immediately', 'asap']):
                entities['urgency'] = 'high'
            elif any(word in message_lower for word in ['soon', 'next week', 'tomorrow']):
                entities['urgency'] = 'medium'
            else:
                entities['urgency'] = 'low'
        
        understanding['entities'] = entities
        return understanding
    
    def _handle_leave_request(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle leave request with intelligent form processing
        """
        try:
            entities = understanding.get('entities', {})
            username = user_context.get('username', 'User')
            user_id = user_context.get('user_id')
            
            # Check if we have enough information
            required_fields = ['leave_type', 'start_date', 'end_date']
            missing_fields = [field for field in required_fields if not entities.get(field)]
            
            if missing_fields:
                # Generate form guide
                form_guide = self._generate_leave_form_guide(entities, missing_fields)
                return self.format_success_response(form_guide, requires_action=True, 
                                                  action_data={'type': 'form_completion', 'missing_fields': missing_fields})
            
            # Execute tools to process leave request
            tool_results = self.execute_with_tools({
                'action': 'create_leave_request',
                'entities': entities,
                'user_context': user_context
            }, ['validate_leave_dates', 'create_leave_request', 'check_leave_balance'])
            
            if tool_results.get('execution_success'):
                # Generate success response
                leave_type = entities.get('leave_type', 'leave').title()
                start_date = entities.get('start_date', 'TBD')
                end_date = entities.get('end_date', 'TBD')
                
                response = f"""
✅ **Leave Request Submitted Successfully!**

**Request Details:**
👤 Employee: {username}
📋 Type: {leave_type} Leave  
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
    
    def _handle_leave_history(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave history requests"""
        try:
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')
            
            # Execute tools to get leave history
            tool_results = self.execute_with_tools({
                'action': 'get_leave_history',
                'user_context': user_context
            }, ['get_leave_history'])
            
            # Generate response
            response = self._generate_leave_history_response(tool_results, username)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting leave history: {str(e)}")
    
    def _handle_leave_approval(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave approval requests (HR only)"""
        try:
            # Execute tools to get pending approvals
            tool_results = self.execute_with_tools({
                'action': 'get_pending_approvals',
                'user_context': user_context
            }, ['get_pending_approvals'])
            
            # Generate response
            response = self._generate_approval_response(tool_results)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting pending approvals: {str(e)}")
    
    def _handle_general_leave_query(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general leave queries"""
        try:
            username = user_context.get('username', 'User')
            
            response = f"""
👋 Hi {username}! I'm here to help with your leave management needs.

**What I can help you with:**
🏖️ **Leave Requests:** "I need leave next week" or "Request annual leave from Jan 15-19"
📊 **Leave Status:** "What's my leave balance?" or "Show my leave history"
📋 **Leave Information:** "How many sick days do I have?" or "When was my last leave?"

**Quick Commands:**
• "I need leave next week" - Start a new leave request
• "What's my leave balance?" - Check your current leave balance
• "Show my leave history" - View your past leave records

**Languages:** You can ask in English or Sinhala!

How can I assist you today?"""
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error handling general query: {str(e)}")
    
    def _generate_leave_form_guide(self, entities: Dict[str, Any], missing_fields: List[str]) -> str:
        """Generate conversational form guide for missing information"""
        
        username = entities.get('username', 'there')
        
        response = f"I'd be happy to help you with your leave request! I need a few more details:\n\n"
        
        if 'leave_type' in missing_fields:
            response += "📋 **Leave Type:** What type of leave do you need?\n"
            response += "   • Annual leave (vacation)\n"
            response += "   • Sick leave\n"
            response += "   • Casual leave\n"
            response += "   • Emergency leave\n\n"
        
        if 'start_date' in missing_fields:
            response += "📅 **Start Date:** When do you want your leave to begin?\n"
            response += "   Example: 'January 15, 2024' or '2024-01-15'\n\n"
        
        if 'end_date' in missing_fields:
            response += "📅 **End Date:** When will you return to work?\n"
            response += "   Example: 'January 19, 2024' or '2024-01-19'\n\n"
        
        response += "💡 **Tip:** You can provide all information at once like:\n"
        response += "\"I need annual leave from January 15 to January 19 for vacation\"\n\n"
        response += "Please provide the missing information, and I'll process your request!"
        
        return response
    
    def _generate_leave_status_response(self, tool_results: Dict[str, Any], username: str) -> str:
        """Generate leave status response"""
        
        leave_balance = tool_results.get('leave_balance', {})
        recent_history = tool_results.get('recent_history', [])
        
        response = f"""📊 **Leave Status for {username}**

**Current Leave Balance:**
🏖️ Annual Leave: {leave_balance.get('annual', 21)} days
🏥 Sick Leave: {leave_balance.get('sick', 7)} days  
📝 Casual Leave: {leave_balance.get('casual', 7)} days
🚨 Emergency Leave: {leave_balance.get('emergency', 3)} days

**Recent Leave Activity:**"""
        
        if recent_history:
            for leave_record in recent_history[:3]:
                status_emoji = "✅" if leave_record.get('status') == 'approved' else "⏳" if leave_record.get('status') == 'pending' else "❌"
                response += f"\n{status_emoji} {leave_record.get('leave_type', 'Leave').title()}: {leave_record.get('start_date')} - {leave_record.get('end_date')} ({leave_record.get('status', 'Unknown')})"
        else:
            response += "\nNo recent leave activity found."
        
        response += "\n\n💡 **Need help?** Ask me:\n"
        response += "• 'Show my leave history' - Full leave history\n"
        response += "• 'I need leave next week' - Request new leave\n"
        response += "• 'When can I take leave?' - Check availability"
        
        return response
    
    def _generate_leave_history_response(self, tool_results: Dict[str, Any], username: str) -> str:
        """Generate leave history response"""
        
        leave_history = tool_results.get('leave_history', [])
        
        response = f"""📋 **Leave History for {username}**

**Past 12 Months:**"""
        
        if leave_history:
            for leave_record in leave_history:
                status_emoji = "✅" if leave_record.get('status') == 'approved' else "⏳" if leave_record.get('status') == 'pending' else "❌"
                duration = leave_record.get('duration', 'N/A')
                response += f"\n{status_emoji} **{leave_record.get('leave_type', 'Leave').title()}** ({duration} days)"
                response += f"\n   📅 {leave_record.get('start_date')} to {leave_record.get('end_date')}"
                response += f"\n   📝 {leave_record.get('reason', 'No reason provided')}"
                response += f"\n   🔄 Status: {leave_record.get('status', 'Unknown').title()}\n"
        else:
            response += "\nNo leave history found for the past 12 months."
        
        response += "\n💡 **Quick Actions:**\n"
        response += "• 'What's my leave balance?' - Check current balance\n"
        response += "• 'I need leave next week' - Request new leave"
        
        return response
    
    def _generate_approval_response(self, tool_results: Dict[str, Any]) -> str:
        """Generate approval response for HR users"""
        
        pending_requests = tool_results.get('pending_requests', [])
        
        response = """🔍 **Pending Leave Requests**

**Awaiting Your Approval:**"""
        
        if pending_requests:
            for request in pending_requests:
                response += f"\n\n👤 **{request.get('employee_name', 'Unknown')}**"
                response += f"\n📋 Type: {request.get('leave_type', 'N/A').title()}"
                response += f"\n📅 Dates: {request.get('start_date')} to {request.get('end_date')}"
                response += f"\n📝 Reason: {request.get('reason', 'Not provided')}"
                response += f"\n🆔 Request ID: {request.get('request_id', 'N/A')}"
                response += f"\n⏰ Submitted: {request.get('submitted_date', 'N/A')}"
        else:
            response += "\n✅ No pending leave requests at this time."
        
        response += "\n\n💡 **Management Actions:**\n"
        response += "• 'Approve request [ID]' - Approve a leave request\n"
        response += "• 'Reject request [ID]' - Reject with reason\n"
        response += "• 'Team leave calendar' - View team schedule"
        
        return response
    
    def execute_with_tools(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """Execute leave-specific tools"""
        
        tool_responses = []
        execution_success = True
        result_data = {}
        
        try:
            action = request_data.get('action')
            entities = request_data.get('entities', {})
            user_context = request_data.get('user_context', {})
            user_id = user_context.get('user_id')
            
            if action == 'create_leave_request':
                # Tool 1: Validate dates
                if 'validate_leave_dates' in available_tools:
                    validation_result = self._validate_leave_dates(entities, user_id)
                    tool_responses.append({'tool': 'validate_leave_dates', 'result': validation_result})
                    
                    if not validation_result.get('valid', False):
                        execution_success = False
                        result_data['error'] = validation_result.get('error', 'Date validation failed')
                
                # Tool 2: Create leave request in database
                if execution_success and 'create_leave_request' in available_tools:
                    creation_result = self._create_leave_db_entry(entities, user_context)
                    tool_responses.append({'tool': 'create_leave_request', 'result': creation_result})
                    result_data['request_id'] = creation_result.get('request_id')
                    
            elif action == 'get_leave_status':
                # Tool 1: Check leave balance
                if 'check_leave_balance' in available_tools:
                    balance = self._get_user_leave_balance(user_id)
                    result_data['leave_balance'] = balance
                    
                # Tool 2: Get recent history
                if 'get_leave_history' in available_tools:
                    history = self._get_user_leave_history(user_id, limit=5)
                    result_data['recent_history'] = history
                    
            elif action == 'get_pending_approvals':
                if 'get_pending_approvals' in available_tools:
                    pending = self._get_pending_leave_requests()
                    result_data['pending_requests'] = pending
                    
            elif action == 'get_leave_history':
                employee_name = request_data.get('employee_name')
                target_user_id = self._get_user_id_by_name(employee_name) if employee_name else user_id
                
                if 'get_leave_history' in available_tools:
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
            start_date = entities.get('start_date')
            end_date = entities.get('end_date')
            
            if not start_date or not end_date:
                return {'valid': False, 'error': 'Start date and end date are required'}
            
            # Parse dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Validate date logic
            if start_dt > end_dt:
                return {'valid': False, 'error': 'Start date cannot be after end date'}
            
            if start_dt < datetime.now():
                return {'valid': False, 'error': 'Cannot request leave for past dates'}
            
            # Check for conflicts (simplified)
            # In real implementation, check against existing leave requests
            
            return {
                'valid': True,
                'duration': (end_dt - start_dt).days + 1,
                'start_date': start_date,
                'end_date': end_date
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Date validation error: {str(e)}'}
    
    def _create_leave_db_entry(self, entities: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create leave request in database"""
        try:
            leave_data = {
                'user_id': user_context.get('user_id'),
                'leave_type': entities.get('leave_type', 'annual'),
                'start_date': entities.get('start_date'),
                'end_date': entities.get('end_date'),
                'reason': entities.get('reason', ''),
                'status': 'pending',
                'created_at': datetime.now(),
                'duration': entities.get('duration', 1)
            }
            
            # Use leave model to create request
            result = self.leave_model.create_leave_request(leave_data)
            
            return {
                'success': True,
                'request_id': result.get('request_id'),
                'message': 'Leave request created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Database error: {str(e)}'
            }
    
    def _get_user_leave_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's leave balance"""
        try:
            # This would typically query the database
            # For now, return sample data
            return {
                'annual': 21,
                'sick': 7,
                'casual': 7,
                'emergency': 3,
                'used_this_year': {
                    'annual': 5,
                    'sick': 2,
                    'casual': 1,
                    'emergency': 0
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_user_leave_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's leave history"""
        try:
            # This would typically query the database
            # For now, return sample data
            return [
                {
                    'leave_type': 'annual',
                    'start_date': '2024-01-15',
                    'end_date': '2024-01-19',
                    'duration': 5,
                    'status': 'approved',
                    'reason': 'Family vacation'
                },
                {
                    'leave_type': 'sick',
                    'start_date': '2024-01-10',
                    'end_date': '2024-01-11',
                    'duration': 2,
                    'status': 'approved',
                    'reason': 'Flu'
                }
            ]
            
        except Exception as e:
            return []
    
    def _get_pending_leave_requests(self) -> List[Dict[str, Any]]:
        """Get pending leave requests for HR approval"""
        try:
            # This would typically query the database
            # For now, return sample data
            return [
                {
                    'request_id': 'REQ001',
                    'employee_name': 'John Doe',
                    'leave_type': 'annual',
                    'start_date': '2024-02-01',
                    'end_date': '2024-02-05',
                    'reason': 'Family vacation',
                    'submitted_date': '2024-01-20'
                }
            ]
            
        except Exception as e:
            return []
    
    def _get_user_id_by_name(self, name: str) -> str:
        """Get user ID by name"""
        try:
            # This would typically query the database
            # For now, return placeholder
            return f"user_{name.lower().replace(' ', '_')}"
            
        except Exception as e:
            return None
    
    def _requires_human_approval(self, request_data: Dict[str, Any]) -> bool:
        """Check if request requires human approval"""
        # Leave requests typically require manager approval
        return request_data.get('action') == 'create_leave_request'
    
    def format_response(self, response_data: Dict[str, Any]) -> str:
        """Format response for the user"""
        try:
            if response_data.get('error'):
                return f"❌ Error: {response_data['error']}"
            
            return response_data.get('response', 'Leave request processed successfully.')
            
        except Exception as e:
            return f"Error formatting response: {str(e)}"