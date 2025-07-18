# backend/agents/leave_agent.py (Enhanced for LangGraph)
from agents.base_agent import BaseAgent
from models.leave import Leave
from models.user import User  # Import User model
from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta, MO



class LeaveAgent(BaseAgent):
    """
    Enhanced Leave Agent with intelligent leave management and tool integration
    """
    @staticmethod
    def calculate_working_days(start_date: datetime, end_date: datetime) -> int:
        days = (end_date - start_date).days + 1
        working_days = 0
        for i in range(days):
            day = start_date + timedelta(days=i)
            if day.weekday() < 5:  # Monday to Friday
                working_days += 1
        return working_days

    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        super().__init__(gemini_api_key, db_connection, memory_manager)
        self.leave_model = Leave(db_connection)
        self.user_model = User(db_connection) # Initialize User model

        # ... (prompt_templates and available_tools remain the same)
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
        Streamlined leave request processing that trusts the incoming intent.
        """
        try:
            intent = request_data.get('intent')
            message = request_data.get('message')
            user_context = request_data.get('user_context', {})
            
            # Use a simplified understanding here as router does the heavy lifting
            understanding = self._enhanced_leave_understanding(message, user_context)
            print(f"🏖️ Leave Agent processing intent '{intent}'")


            if intent == 'leave_request':
                return self._handle_leave_request(message, understanding, user_context)
            elif intent == 'leave_status':
                return self._handle_leave_status(message, understanding, user_context)
            elif intent == 'leave_history':
                return self._handle_leave_history(message, understanding, user_context)
            elif intent.startswith('leave_approval') and user_context.get('role') == 'hr':
                return self._handle_leave_approval(message, understanding, user_context)
            else:
                # Fallback for any other leave-related queries
                return self._handle_general_leave_query(message, understanding, user_context)
                
        except Exception as e:
            return self.format_error_response(f"Error processing leave request: {str(e)}")
        
    def _handle_leave_status(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave status/balance requests."""
        try:
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')

            tool_results = self.execute_with_tools({
                'action': 'get_leave_status',
                'user_context': user_context
            }, ['check_leave_balance', 'get_leave_history'])

            if tool_results.get('execution_success'):
                response = self._generate_leave_status_response(tool_results, username)
                return self.format_success_response(response)
            else:
                error_msg = tool_results.get('error', 'Failed to retrieve leave status')
                return self.format_error_response(f"❌ Unable to retrieve leave status: {error_msg}")

        except Exception as e:
            return self.format_error_response(f"Error handling leave status request: {str(e)}")
    
    def _enhanced_leave_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced leave understanding with context
        """
        try:
            # Use base understanding first
            base_understanding = self.understand_request(message, user_context)
            
            # Enhance with leave-specific logic
            leave_specific_entities = self._enhance_leave_entities(message).get('entities', {})
            base_understanding.get('entities', {}).update(leave_specific_entities)
            enhanced_understanding = base_understanding
            
            return enhanced_understanding
            
        except Exception as e:
            return {
                'intent': 'leave_request',
                'entities': {},
                'confidence': 0.5,
                'error': str(e)
            }
    
    def _enhance_leave_entities(self, message: str) -> Dict[str, Any]:
        """
        Enhance understanding with leave-specific entity extraction, including relative dates.
        """
        message_lower = message.lower()
        entities = {}
        
        # --- 1. Extract Leave Type ---
        leave_types = {
            'sick': ['sick', 'medical', 'hospital', 'doctor'],
            'annual': ['annual', 'vacation', 'holiday'],
            'casual': ['casual', 'personal'],
        }
        for leave_type, keywords in leave_types.items():
            if any(word in message_lower for word in keywords):
                entities['leave_type'] = leave_type
                break

        # --- 2. Extract Duration ---
        duration_match = re.search(r'(\d+)\s*(day|week)s?', message_lower)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2)
            entities['duration'] = value * 7 if 'week' in unit else value

        # --- 3. Extract and Parse Dates (including relative dates) ---
        today = datetime.now()
        
        # Relative dates like "next Monday"
        if 'next monday' in message_lower:
            entities['start_date'] = (today + relativedelta(weekday=MO(+1))).strftime('%Y-%m-%d')
        elif 'tomorrow' in message_lower:
            entities['start_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'today' in message_lower:
            entities['start_date'] = today.strftime('%Y-%m-%d')
        
        # Explicit dates like "from January 15 to 19"
        try:
            # Attempt to parse specific dates if found
            date_matches = re.findall(r'(?:from|on|between)\s*([a-zA-Z]+\s*\d{1,2})', message_lower)
            if date_matches:
                 # This is a simplified logic, a real implementation would be more robust
                 start_date_str = date_matches[0]
                 entities['start_date'] = parse(start_date_str).strftime('%Y-%m-%d')
        except Exception:
            pass # Ignore parsing errors for now

        # --- 4. Calculate End Date if Start Date and Duration are present ---
        if 'start_date' in entities and 'duration' in entities and 'end_date' not in entities:
            start_date = datetime.strptime(entities['start_date'], '%Y-%m-%d')
            # Duration includes the start day, so we subtract 1
            end_date = start_date + timedelta(days=entities['duration'] - 1)
            entities['end_date'] = end_date.strftime('%Y-%m-%d')

        return {'entities': entities}
    
    def _handle_leave_request(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle leave request with intelligent form processing and short-term memory.
        """
        try:
            session_id = user_context.get('session_id')
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')

            # 1. Check for pending form data in short-term memory
            pending_form_data = self.memory_manager.short_term.get_form_data(user_id, session_id, 'leave_request')
            
            # 2. Extract new entities from the current message
            current_entities = self._enhance_leave_entities(message).get('entities', {})

            # 3. Merge old and new entities
            if pending_form_data:
                print("🧠 Found pending leave form data in memory. Merging now...")
                # Start with old entities and update with new ones
                merged_entities = {**pending_form_data.get('entities', {}), **current_entities}
            else:
                merged_entities = current_entities

            # 4. Check if all required information is now available
            required_fields = ['leave_type', 'start_date', 'end_date']
            missing_fields = [field for field in required_fields if not merged_entities.get(field)]
            
            if missing_fields:
                print(f"📝 Missing fields: {missing_fields}. Asking user for more info.")
                # Store the current (merged) state in memory
                self.memory_manager.short_term.store_form_data(
                    user_id, session_id, 'leave_request', 
                    {'entities': merged_entities, 'missing_fields': missing_fields}
                )
                
                form_guide = self._generate_leave_form_guide(merged_entities, missing_fields)
                return self.format_success_response(form_guide, requires_action=True, 
                                                  action_data={'type': 'form_completion', 'missing_fields': missing_fields})
            
            # 5. If all info is present, process the request
            print("✅ All required information is available. Processing leave request.")
            # Clear memory since the form is now complete
            self.memory_manager.short_term.clear_form_data(user_id, session_id, 'leave_request')
            
            tool_results = self.execute_with_tools({
                'action': 'create_leave_request',
                'entities': merged_entities, # Use the merged data
                'user_context': user_context
            }, ['validate_leave_dates', 'create_leave_request', 'check_leave_balance'])
            
            # ... (The rest of the success/error response logic remains the same)
            if tool_results.get('execution_success'):
                leave_type = merged_entities.get('leave_type', 'leave').title()
                start_date = merged_entities.get('start_date', 'TBD')
                end_date = merged_entities.get('end_date', 'TBD')
                
                response = f"""
✅ **Leave Request Submitted Successfully!**

**Request Details:**
👤 Employee: {username}
📋 Type: {leave_type} Leave  
📅 From: {start_date}
📅 To: {end_date}
📝 Reason: {merged_entities.get('reason', 'Not specified')}
"""
                return self.format_success_response(response)
            else:
                error_msg = tool_results.get('error', 'Failed to create leave request')
                return self.format_error_response(f"❌ Unable to create leave request: {error_msg}")
                
        except Exception as e:
            return self.format_error_response(f"Error creating leave request: {str(e)}")


    def _handle_leave_history(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle leave history requests by fetching all leave records."""
        try:
            user_id = user_context.get('user_id')
            username = user_context.get('username', 'User')
            
            # Execute tool to get the full leave history from the database
            tool_results = self.execute_with_tools({
                'action': 'get_leave_history',
                'user_context': user_context
            }, ['get_leave_history'])
            
            response = self._generate_leave_history_response(tool_results, username)
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting leave history: {str(e)}")
    
            
    def _handle_leave_approval(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles leave approval requests. 
        It can either list pending requests or approve/reject a specific one.
        """
        try:
            # --- START of the FIX ---
            # Step 1: Try to find a leave ID in the user's message
            message_lower = message.lower()
            # This regex looks for a 24-character hexadecimal string, which is the format of a MongoDB ID
            leave_id_match = re.search(r'\b([a-f0-9]{24})\b', message_lower)

            hr_user_id = user_context.get('user_id')

            # Step 2: If an ID is found, attempt to approve or reject it
            if leave_id_match:
                leave_id = leave_id_match.group(1)

                # Determine if the action is 'approve' or 'reject'
                action = 'approved' if 'approve' in message_lower else 'rejected'

                # Update the status in the database using the model
                success = self.leave_model.update_leave_status(leave_id, action, hr_user_id)

                if success:
                    response_message = f"✅ **Success!**\nLeave request with ID `{leave_id}` has been successfully **{action}**."
                else:
                    response_message = f"⚠️ **Could not update.**\nCould not find a leave request with ID `{leave_id}`. Please check the ID and try again."

                return self.format_success_response(response_message)

            # Step 3: If no ID is found, list all pending requests (the original behavior)
            else:
                pending_requests = self.leave_model.get_pending_leaves()
                response = self._generate_approval_response({'pending_requests': pending_requests})
                return self.format_success_response(response)
            # --- END of the FIX ---

        except Exception as e:
            # Return a detailed error message if something goes wrong
            return self.format_error_response(f"An error occurred while handling leave approval: {str(e)}")


    
    def _handle_general_leave_query(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general leave queries"""
        username = user_context.get('username', 'User')
        response = f"👋 Hi {username}! I'm here to help with your leave management. You can ask me to 'request a leave', check your 'leave balance', or view your 'leave history'."
        return self.format_success_response(response)
    
    def _generate_leave_form_guide(self, entities: Dict[str, Any], missing_fields: List[str]) -> str:
        """Generate conversational form guide for missing information"""
        response = f"I'd be happy to help you with your leave request! I just need a few more details:\n"
        
        if 'leave_type' in missing_fields:
            response += "\n📋 **What type of leave do you need?** (e.g., annual, sick)"
        if 'start_date' in missing_fields:
            response += "\n📅 **When do you want your leave to start?** (e.g., tomorrow, next Monday, 2024-10-25)"
        if 'end_date' in missing_fields:
            response += "\n📅 **And when will it end?** You can also tell me the duration (e.g., for 5 days)."
        
        response += "\n\n💡 You can provide all the information at once, like: \"I need sick leave from tomorrow for 3 days\"."
        return response
    
    def _generate_leave_status_response(self, tool_results: Dict[str, Any], username: str) -> str:
        """Generate leave status response with real balance and recent history."""
        leave_balance = tool_results.get('leave_balance', {})
        recent_history = tool_results.get('recent_history', [])
        
        annual = leave_balance.get('annual', {})
        sick = leave_balance.get('sick', {})
        casual = leave_balance.get('casual', {})

        response = f"""📊 **Leave Status for {username}**

**Current Leave Balance:**
🏖️ **Annual Leave:** {annual.get('remaining', 'N/A')} days remaining (out of {annual.get('total', 'N/A')})
🏥 **Sick Leave:** {sick.get('remaining', 'N/A')} days remaining (out of {sick.get('total', 'N/A')})
📝 **Casual Leave:** {casual.get('remaining', 'N/A')} days remaining (out of {casual.get('total', 'N/A')})

**Recent Leave Activity:**"""
        
        if recent_history:
            for leave_record in recent_history[:3]:
                status_emoji = "✅" if leave_record.get('status') == 'approved' else "⏳" if leave_record.get('status') == 'pending' else "❌"
                start_date_str = leave_record.get('start_date').strftime('%b %d, %Y')
                end_date_str = leave_record.get('end_date').strftime('%b %d, %Y')
                response += f"\n{status_emoji} **{leave_record.get('leave_type', 'Leave').title()}**: {start_date_str} - {end_date_str} ({leave_record.get('status', 'Unknown')})"
        else:
            response += "\nNo recent leave activity found."
        
        response += "\n\n💡 To see all your past requests, ask 'Show my leave history'."
        return response
    
    def _generate_leave_history_response(self, tool_results: Dict[str, Any], username: str) -> str:
        """Generate full leave history response from real data."""
        leave_history = tool_results.get('leave_history', [])
        
        response = f"""📋 **Full Leave History for {username}**"""
        
        if leave_history:
            for leave_record in leave_history:
                status_emoji = "✅" if leave_record.get('status') == 'approved' else "⏳" if leave_record.get('status') == 'pending' else "❌"
                start_date_str = leave_record.get('start_date').strftime('%Y-%m-%d')
                end_date_str = leave_record.get('end_date').strftime('%Y-%m-%d')
                
                response += f"\n\n{status_emoji} **{leave_record.get('leave_type', 'Leave').title()}**"
                response += f"\n   - **Dates:** {start_date_str} to {end_date_str}"
                response += f"\n   - **Status:** {leave_record.get('status', 'Unknown').title()}"
        else:
            response += "\n\nNo leave history found."
            
        return response
    
    def _generate_approval_response(self, tool_results: Dict[str, Any]) -> str:
        pending_requests = tool_results.get('pending_requests', [])
        if not pending_requests:
            return "✅ Great news! There are no pending leave requests awaiting your approval at this time."

        response = f"🔍 **Pending Leave Requests ({len(pending_requests)} Found)**\nHere are the requests awaiting your approval:"
        
        # In a real app, you'd fetch user details more efficiently
        for request in pending_requests:
            user = self.user_model.get_user_by_id(request.get('user_id'))
            employee_name = user.get('full_name') if user else 'Unknown Employee'
            response += f"""
\n-----------------------------------
👤 **{employee_name}**
  - **Type:** {request.get('leave_type', 'N/A').title()}
  - **Dates:** {request.get('start_date').strftime('%Y-%m-%d')} to {request.get('end_date').strftime('%Y-%m-%d')}
  - **Request ID:** `{str(request.get('_id'))}`"""
        
        response += "\n\n💡 To take action, you can say `approve leave [Request ID]` or `reject leave [Request ID] with reason [your reason]`."
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
            start_date_obj = datetime.strptime(entities.get('start_date'), '%Y-%m-%d')
            end_date_obj = datetime.strptime(entities.get('end_date'), '%Y-%m-%d')

            leave_data = {
                'user_id': user_context.get('user_id'),
                'leave_type': entities.get('leave_type', 'annual'),
                'start_date': start_date_obj,  # Save as datetime object
                'end_date': end_date_obj,      # Save as datetime object
                'reason': entities.get('reason', ''),
                'status': 'pending',
                'created_at': datetime.now(),
                'duration': entities.get('duration', 1)
            }
            
            # Use leave model to create request
            result = self.leave_model.create_leave_request(leave_data)
            
            return {
                'success': True,
                'request_id': result,
                'message': 'Leave request created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Database error: {str(e)}'
            }
    
    def _get_user_leave_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's leave balance from the database."""
        try:
            user = self.user_model.get_user_by_id(user_id)

            if not user:
                return {'error': 'User not found'}

            
            annual_balance = user.get('annual_leave_balance', 0)
            sick_balance = user.get('sick_leave_balance', 0)
            casual_balance = user.get('casual_leave_balance', 0)

            all_leaves = self.leave_model.get_leaves_by_user(user_id)

            deductible_leaves = [
                leave for leave in all_leaves if leave.get('status') in ['pending', 'approved']
            ]

            # CORRECTED LOGIC: Separate 'approved' leaves to calculate 'used' days
            approved_leaves = [leave for leave in all_leaves if leave.get('status') == 'approved']

            # Calculate total taken days for each leave type
            taken_annual = sum(self.calculate_working_days(l['start_date'], l['end_date']) 
                               for l in deductible_leaves if l.get('leave_type') == 'annual')
            taken_sick = sum(self.calculate_working_days(l['start_date'], l['end_date']) 
                             for l in deductible_leaves if l.get('leave_type') == 'sick')
            taken_casual = sum(self.calculate_working_days(l['start_date'], l['end_date']) 
                               for l in deductible_leaves if l.get('leave_type') == 'casual')

            # Calculate used days (approved only) for display purposes
            approved_leaves = [l for l in deductible_leaves if l.get('status') == 'approved']
            used_annual = sum(self.calculate_working_days(l['start_date'], l['end_date'])
                              for l in approved_leaves if l.get('leave_type') == 'annual')
            used_sick = sum(self.calculate_working_days(l['start_date'], l['end_date'])
                            for l in approved_leaves if l.get('leave_type') == 'sick')
            used_casual = sum(self.calculate_working_days(l['start_date'], l['end_date'])
                              for l in approved_leaves if l.get('leave_type') == 'casual')

            return {
                'annual': {'total': annual_balance, 'used': used_annual, 'remaining': annual_balance - taken_annual},
                'sick': {'total': sick_balance, 'used': used_sick, 'remaining': sick_balance - taken_sick},
                'casual': {'total': casual_balance, 'used': used_casual, 'remaining': casual_balance - taken_casual}
            }

        except Exception as e:
            print(f"Error calculating leave balance from DB: {e}")
            return {'error': str(e)}

    
    def _get_user_leave_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's leave history from the database."""
        try:
            history = self.leave_model.get_leaves_by_user(user_id)
            return history[:limit] # Return limited number of records
        except Exception as e:
            print(f"Error fetching leave history from DB: {e}")
            return []
    
    def _get_pending_leave_requests(self) -> List[Dict[str, Any]]:
        """Get pending leave requests for HR approval from the database."""
        try:
            # This now correctly fetches real data from the database
            pending_leaves = self.leave_model.get_pending_leaves()
            return pending_leaves

        except Exception as e:
            print(f"Error fetching pending leave requests from DB: {e}")
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