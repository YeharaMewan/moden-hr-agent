# backend/agents/payroll_agent.py (Enhanced for LangGraph)
from agents.base_agent import BaseAgent
from models.payroll import Payroll
from models.user import User
from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

class PayrollAgent(BaseAgent):
    """
    Enhanced Payroll Agent with intelligent payroll calculation and management
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        super().__init__(gemini_api_key, db_connection, memory_manager)
        self.payroll_model = Payroll(db_connection)
        self.user_model = User(db_connection)
        
        # Payroll-specific prompt templates
        self.prompt_templates.update({
            'payroll_understanding': """
            Analyze this payroll-related request:
            Message: "{message}"
            User Context: {user_context}
            
            Extract (respond in JSON only):
            {{
                "intent": "individual_payroll|department_payroll|payroll_history|payroll_summary",
                "entities": {{
                    "employee_name": "specific employee name",
                    "department": "department name",
                    "period": "pay period (monthly, yearly, etc.)",
                    "year": "specific year",
                    "month": "specific month",
                    "is_self_request": true/false
                }},
                "confidence": 0.0-1.0,
                "calculation_type": "current|historical|projection",
                "urgency": "low|medium|high",
                "language": "english|sinhala|mixed"
            }}
            
            Examples:
            "Calculate my payroll" → {{"intent": "individual_payroll", "entities": {{"is_self_request": true}}}}
            "Calculate payroll for John Doe" → {{"intent": "individual_payroll", "entities": {{"employee_name": "John Doe"}}}}
            "IT department payroll" → {{"intent": "department_payroll", "entities": {{"department": "IT"}}}}
            "මට මගේ වැටුප් calculate කරන්න" → {{"intent": "individual_payroll", "entities": {{"is_self_request": true}}, "language": "sinhala"}}
            """,
            
            'payroll_response': """
            Generate a professional payroll response:
            
            Query: "{message}"
            User: {username} ({role})
            Payroll Data: {payroll_data}
            Calculation Type: {calculation_type}
            
            Guidelines:
            - Act as a professional HR payroll assistant
            - Present data clearly with proper formatting
            - Include breakdown of salary components
            - Mention deductions and net pay
            - Add relevant insights or notes
            - Support both English and Sinhala
            - Use appropriate emojis for readability
            - Keep response under 400 words
            """
        })
        
        # Available tools for payroll operations
        self.available_tools = [
            'calculate_individual_payroll',
            'calculate_department_payroll',
            'get_payroll_history',
            'get_payroll_summary',
            'calculate_deductions',
            'calculate_benefits',
            'generate_payslip',
            'validate_payroll_data'
        ]
        
        # Payroll calculation constants
        self.TAX_RATES = {
            'income_tax': 0.15,
            'etf': 0.03,
            'epf_employee': 0.08,
            'epf_employer': 0.12
        }
        
        self.ALLOWANCES = {
            'transport': 15000,
            'meal': 10000,
            'medical': 5000
        }
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced payroll request processing with intelligent dispatching based on entities.
        """
        try:
            message = request_data.get('message')
            user_context = request_data.get('user_context', {})

            # Step 1: Enhanced understanding to get intent and all possible entities
            understanding = self._enhanced_payroll_understanding(message, user_context)
            
            # Step 2: Intelligent Routing based on extracted entities
            entities = understanding.get('entities', {})

            # --- CORRECTED ROUTING LOGIC ---
            # PRIORITY 1: Route to Individual Payroll if a specific employee was found (by name, ID, or self-request)
            if entities.get('employee_name') or entities.get('is_self_request'):
                print(f"✅ Routing to Individual Payroll for: {entities.get('employee_name', user_context.get('username'))}")
                return self._handle_individual_payroll(message, understanding, user_context)

            # PRIORITY 2: Route to Department Payroll if a department is mentioned and no specific employee was found
            if entities.get('department'):
                print(f"✅ Routing to Department Payroll for: {entities.get('department')}")
                return self._handle_department_payroll(message, understanding, user_context)
            
            # PRIORITY 3: Handle other intents like history or summary
            if understanding['intent'] == 'payroll_history':
                return self._handle_payroll_history(message, understanding, user_context)
            
            if understanding['intent'] == 'payroll_summary':
                 return self._handle_payroll_summary(message, understanding, user_context)

            # Fallback to general query if no specific entities are found for a calculation request
            print("✅ No specific entities found, routing to General Payroll Query.")
            return self._handle_general_payroll_query(message, understanding, user_context)
                
        except Exception as e:
            return self.format_error_response(f"Error processing payroll request: {str(e)}")
    
    def _enhanced_payroll_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced payroll understanding with context
        """
        try:
            # Use base understanding first
            base_understanding = self.understand_request(message, user_context)
            
            # Enhance with payroll-specific logic
            enhanced_understanding = self._enhance_payroll_entities(message, base_understanding, user_context)
            
            return enhanced_understanding
            
        except Exception as e:
            return {
                'intent': 'individual_payroll',
                'entities': {},
                'confidence': 0.5,
                'error': str(e)
            }
    
    def _enhance_payroll_entities(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance understanding with payroll-specific entity extraction,
        including robust detection of employee names, usernames, and employee IDs.
        """
        message_lower = message.lower()
        entities = understanding.get('entities', {})

        # --- 1. Check for self-request first ---
        if any(word in message_lower for word in ['my', 'මගේ', 'මගෙ']):
            entities['is_self_request'] = True
            entities['employee_name'] = user_context.get('username')
        
        # --- 2. Extract employee identifiers (Name, Username, or Employee ID) ---
        if not entities.get('employee_name'):
            # Pattern for Employee ID (e.g., MKT001, FIN002, IT001)
            emp_id_match = re.search(r'([A-Z]{2,3}\d{3})', message, re.IGNORECASE)
            # Pattern for username (e.g., david.lee)
            username_match = re.search(r'([a-z]+\.[a-z]+)', message_lower)
            # Pattern for full name (e.g., Kevin Johnson, Lisa Garcia, Sandun Silva)
            fullname_match = re.search(r'([A-Z][a-z]+\s[A-Z][a-z]+)', message, re.IGNORECASE)

            target_user = None
            if emp_id_match:
                employee_id = emp_id_match.group(1).upper()
                target_user = self.user_model.get_user_by_employee_id(employee_id)
                if target_user:
                    print(f"DEBUG: Found user by Employee ID: {employee_id}")
            elif fullname_match:
                full_name = fullname_match.group(1)
                # Convert "First Last" to "first.last" to find the user by username, which is a common pattern
                username_to_find = full_name.lower().replace(' ', '.')
                target_user = self.user_model.get_user_by_username(username_to_find)
                if not target_user:
                    # Fallback to searching by the full name field if username search fails
                    users_by_name = self.user_model.get_all_users() # A more specific lookup would be better
                    for u in users_by_name:
                        if u.get('full_name', '').lower() == full_name.lower():
                            target_user = u
                            break
                if target_user:
                    print(f"DEBUG: Found user by Full Name: {full_name}")
            elif username_match:
                username = username_match.group(1)
                target_user = self.user_model.get_user_by_username(username)
                if target_user:
                    print(f"DEBUG: Found user by Username: {username}")


            if target_user:
                entities['employee_name'] = target_user.get('username')
                entities['is_self_request'] = (target_user.get('username') == user_context.get('username'))
                # IMPORTANT: Set intent to individual payroll since we found a specific user
                understanding['intent'] = 'individual_payroll'


        # --- 3. Extract department (only if no specific user was found) ---
        if not entities.get('employee_name'):
            departments = ['it', 'hr', 'finance', 'marketing', 'sales', 'operations', 'engineering']
            for dept in departments:
                if re.search(r'\b' + dept + r'\b', message_lower):
                    entities['department'] = dept.upper()
                    understanding['intent'] = 'department_payroll'
                    break
        
        understanding['entities'] = entities
        return understanding
    
    def _handle_individual_payroll(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle individual payroll calculation
        """
        try:
            entities = understanding.get('entities', {})
            username = user_context.get('username', 'User')
            user_role = user_context.get('role', 'user')
            
            # Determine target employee
            target_employee = entities.get('employee_name', username)
            is_self_request = entities.get('is_self_request', True)
            
            # Permission check for non-self requests
            if not is_self_request and user_role != 'hr':
                return self.format_error_response("❌ Access Denied: You can only view your own payroll information.")
            
            # Execute tools to calculate payroll
            tool_results = self.execute_with_tools({
                'action': 'calculate_individual_payroll',
                'employee_name': target_employee, 'user_context': user_context,
                'entities': entities,
                'user_context': user_context
            }, ['calculate_individual_payroll', 'calculate_deductions', 'calculate_benefits'])
            
            if tool_results.get('execution_success'):
                response = self._generate_individual_payroll_response(
                    tool_results, target_employee, is_self_request
                )
                return self.format_success_response(response)
            else:
                error_msg = tool_results.get('error', 'Failed to calculate payroll')
                return self.format_error_response(f"❌ Unable to calculate payroll: {error_msg}")
                
        except Exception as e:
            return self.format_error_response(f"Error calculating individual payroll: {str(e)}")
    
    def _handle_department_payroll(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle department payroll calculation directly without an approval step.
        """
        try:
            user_role = user_context.get('role', 'user')
            
            # Permission check - only HR can access department payroll
            if user_role != 'hr':
                return self.format_error_response("❌ Access Denied: Department payroll access is restricted to HR users.")
            
            entities = understanding.get('entities', {})
            department = entities.get('department') # .get() is safer

            if not department:
                return self.format_error_response("❌ Please specify a department to calculate the payroll for.")

            # Execute tools to calculate department payroll and get summary
            tool_results = self.execute_with_tools({
                'action': 'calculate_department_payroll',
                'department': department,
                'entities': entities,
                'user_context': user_context
            }, ['calculate_department_payroll', 'get_payroll_summary'])
            
            if tool_results.get('execution_success'):
                # Generate the response with the calculated data
                response = self._generate_department_payroll_response(tool_results, department)
                # No human approval needed, so requires_action is False
                return self.format_success_response(response, requires_action=False)
            else:
                error_msg = tool_results.get('error', 'Failed to calculate department payroll')
                return self.format_error_response(f"❌ Unable to calculate department payroll: {error_msg}")
                
        except Exception as e:
            return self.format_error_response(f"Error calculating department payroll: {str(e)}")

    
    def _handle_payroll_history(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payroll history requests
        """
        try:
            entities = understanding.get('entities', {})
            username = user_context.get('username', 'User')
            
            # Execute tools to get payroll history
            tool_results = self.execute_with_tools({
                'action': 'get_payroll_history',
                'employee_name': username,
                'entities': entities,
                'user_context': user_context
            }, ['get_payroll_history'])
            
            if tool_results.get('execution_success'):
                response = self._generate_payroll_history_response(tool_results, username)
                return self.format_success_response(response)
            else:
                return self.format_error_response("❌ Unable to retrieve payroll history.")
                
        except Exception as e:
            return self.format_error_response(f"Error getting payroll history: {str(e)}")
    
    def _handle_payroll_summary(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payroll summary requests
        """
        try:
            entities = understanding.get('entities', {})
            
            # Execute tools to get payroll summary
            tool_results = self.execute_with_tools({
                'action': 'get_payroll_summary',
                'entities': entities,
                'user_context': user_context
            }, ['get_payroll_summary'])
            
            if tool_results.get('execution_success'):
                response = self._generate_payroll_summary_response(tool_results)
                return self.format_success_response(response)
            else:
                return self.format_error_response("❌ Unable to generate payroll summary.")
                
        except Exception as e:
            return self.format_error_response(f"Error generating payroll summary: {str(e)}")
    
    def _handle_general_payroll_query(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle general payroll queries
        """
        try:
            username = user_context.get('username', 'User')
            user_role = user_context.get('role', 'user')
            
            response = f"""
👋 Hi {username}! I'm here to help you with payroll information.

**💰 What I can help you with:**
"""
            
            if user_role == 'hr':
                response += """
🏢 **HR Payroll Management:**
• "Calculate payroll for John Doe" - Individual employee payroll
• "Calculate IT department payroll" - Department-wide payroll
• "Generate payroll summary for January" - Monthly summaries
• "Show payroll history for Sarah" - Employee payroll history

👤 **Individual Payroll:**
• "Calculate my payroll" - Your personal payroll
• "Show my payroll history" - Your payment history
• "What are my deductions?" - Breakdown of deductions
"""
            else:
                response += """
👤 **Your Payroll Information:**
• "Calculate my payroll" - Current payroll calculation
• "Show my payroll history" - Your payment history
• "What are my deductions?" - Breakdown of deductions
• "Show my benefits" - Your benefits information
"""
            
            response += """
**📊 Payroll Components:**
• Basic salary and allowances
• Deductions (tax, EPF, ETF)
• Benefits and bonuses
• Net pay calculation

**🗓️ Time Periods:**
• Monthly: "Calculate my monthly payroll"
• Yearly: "Show my annual payroll"
• Specific periods: "January 2024 payroll"

**Languages:** You can ask in English or Sinhala!
• "Calculate my payroll" or "මගේ වැටුප් calculate කරන්න"

How can I help you with your payroll today?"""
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error handling general query: {str(e)}")
    
    def _generate_individual_payroll_response(self, tool_results: Dict[str, Any], 
                                            employee_name: str, is_self_request: bool) -> str:
        """
        Generate individual payroll response
        """
        payroll_data = tool_results.get('payroll_data', {})
        
        if not payroll_data:
            return f"❌ Could not calculate payroll for {employee_name}. Please check if employee exists."
        
        # Extract payroll components
        basic_salary = payroll_data.get('basic_salary', 0)
        allowances = payroll_data.get('allowances', {})
        deductions = payroll_data.get('deductions', {})
        net_pay = payroll_data.get('net_pay', 0)
        
        # Calculate totals
        total_allowances = sum(allowances.values())
        total_deductions = sum(deductions.values())
        gross_pay = basic_salary + total_allowances
        
        pronoun = "Your" if is_self_request else f"{employee_name}'s"
        
        response = f"""
💰 **{pronoun} Payroll Calculation**

**📊 Salary Breakdown:**
• **Basic Salary:** Rs. {basic_salary:,.2f}
• **Allowances:** Rs. {total_allowances:,.2f}
  - Transport: Rs. {allowances.get('transport', 0):,.2f}
  - Meal: Rs. {allowances.get('meal', 0):,.2f}
  - Medical: Rs. {allowances.get('medical', 0):,.2f}
• **Gross Pay:** Rs. {gross_pay:,.2f}

**📉 Deductions:**
• **Total Deductions:** Rs. {total_deductions:,.2f}
  - Income Tax (15%): Rs. {deductions.get('income_tax', 0):,.2f}
  - EPF (8%): Rs. {deductions.get('epf_employee', 0):,.2f}
  - ETF (3%): Rs. {deductions.get('etf', 0):,.2f}

**💵 Net Pay:** Rs. {net_pay:,.2f}

**📅 Pay Period:** {payroll_data.get('period', 'Monthly')}
**🗓️ Calculation Date:** {payroll_data.get('calculation_date', datetime.now().strftime('%Y-%m-%d'))}

**📋 Additional Information:**
• **Employee ID:** {payroll_data.get('employee_id', 'N/A')}
• **Department:** {payroll_data.get('department', 'N/A')}
• **Position:** {payroll_data.get('position', 'N/A')}

**💡 Notes:**
• Employer EPF contribution: Rs. {deductions.get('epf_employer', 0):,.2f}
• Tax year: {payroll_data.get('tax_year', datetime.now().year)}
• Next pay date: {payroll_data.get('next_pay_date', 'End of month')}

**📄 Need More Details?**
• "Show my payroll history" - View past payments
• "Generate payslip" - Download detailed payslip
• "Explain deductions" - Understand deduction calculations"""
        
        return response
    
    def _generate_department_payroll_response(self, tool_results: Dict[str, Any], department: str) -> str:
        """
        Generate department payroll response
        """
        dept_data = tool_results.get('department_data', {})
        employees = dept_data.get('employees', [])
        
        if not employees:
            return f"❌ No employees found in {department} department or payroll data unavailable."
        
        total_gross = sum(emp.get('gross_pay', 0) for emp in employees)
        total_net = sum(emp.get('net_pay', 0) for emp in employees)
        total_deductions = total_gross - total_net
        
        response = f"""
🏢 **{department.upper()} Department Payroll**

**📊 Department Summary:**
• **Total Employees:** {len(employees)}
• **Total Gross Pay:** Rs. {total_gross:,.2f}
• **Total Deductions:** Rs. {total_deductions:,.2f}
• **Total Net Pay:** Rs. {total_net:,.2f}
• **Average Salary:** Rs. {total_net / len(employees):,.2f}

**👥 Employee Breakdown:**"""
        
        for i, emp in enumerate(employees[:10], 1):  # Show top 10
            response += f"""
{i}. **{emp.get('name', 'Employee')}**
   • Gross: Rs. {emp.get('gross_pay', 0):,.2f}
   • Net: Rs. {emp.get('net_pay', 0):,.2f}
   • Position: {emp.get('position', 'N/A')}"""
        
        if len(employees) > 10:
            response += f"\n... and {len(employees) - 10} more employees"
        
        response += f"""

**📈 Department Analytics:**
• **Highest Paid:** {dept_data.get('highest_paid', 'N/A')} - Rs. {dept_data.get('highest_salary', 0):,.2f}
• **Department Budget:** Rs. {dept_data.get('budget_utilization', 0):,.2f}
• **Budget Utilization:** {dept_data.get('budget_percentage', 0):.1f}%

**📅 Pay Period:** {dept_data.get('period', 'Monthly')}
**🗓️ Calculation Date:** {datetime.now().strftime('%Y-%m-%d')}

**📋 HR Actions:**
• "Generate department payslips" - Create all payslips
• "Export payroll data" - Download Excel report
• "Compare with last month" - Payroll comparison"""
        
        return response
    
    def _generate_payroll_history_response(self, tool_results: Dict[str, Any], username: str) -> str:
        """
        Generate payroll history response
        """
        history = tool_results.get('payroll_history', [])
        
        if not history:
            return f"❌ No payroll history found for {username}."
        
        response = f"""
📊 **Payroll History for {username}**

**📅 Recent Payments:**"""
        
        for i, record in enumerate(history[:6], 1):  # Show last 6 months
            response += f"""
{i}. **{record.get('period', 'Month')}**
   • Net Pay: Rs. {record.get('net_pay', 0):,.2f}
   • Gross Pay: Rs. {record.get('gross_pay', 0):,.2f}
   • Date: {record.get('pay_date', 'N/A')}"""
        
        # Calculate totals
        total_net = sum(rec.get('net_pay', 0) for rec in history)
        total_gross = sum(rec.get('gross_pay', 0) for rec in history)
        
        response += f"""

**📈 Summary Statistics:**
• **Total Net Earned:** Rs. {total_net:,.2f}
• **Total Gross:** Rs. {total_gross:,.2f}
• **Average Monthly:** Rs. {total_net / len(history):,.2f}
• **Records Available:** {len(history)} months

**📊 Yearly Breakdown:**
• **2024:** Rs. {sum(rec.get('net_pay', 0) for rec in history if rec.get('year') == 2024):,.2f}
• **2023:** Rs. {sum(rec.get('net_pay', 0) for rec in history if rec.get('year') == 2023):,.2f}

**📋 Actions:**
• "Show detailed payslip for [month]" - Get specific payslip
• "Calculate my tax for this year" - Tax calculation
• "Compare with previous year" - Year-over-year comparison"""
        
        return response
    
    def _generate_payroll_summary_response(self, tool_results: Dict[str, Any]) -> str:
        """
        Generate payroll summary response
        """
        summary = tool_results.get('payroll_summary', {})
        
        response = f"""
📊 **Payroll Summary Report**

**🏢 Company Overview:**
• **Total Employees:** {summary.get('total_employees', 0)}
• **Total Payroll:** Rs. {summary.get('total_payroll', 0):,.2f}
• **Average Salary:** Rs. {summary.get('average_salary', 0):,.2f}

**🏬 Department Breakdown:**"""
        
        departments = summary.get('departments', [])
        for dept in departments:
            response += f"""
• **{dept.get('name', 'Department')}:** {dept.get('employee_count', 0)} employees - Rs. {dept.get('total_payroll', 0):,.2f}"""
        
        response += f"""

**📈 Payroll Trends:**
• **This Month:** Rs. {summary.get('current_month', 0):,.2f}
• **Last Month:** Rs. {summary.get('last_month', 0):,.2f}
• **Change:** {summary.get('change_percentage', 0):+.1f}%

**💰 Salary Ranges:**
• **Senior Level:** Rs. {summary.get('senior_range', '100,000 - 200,000')}
• **Mid Level:** Rs. {summary.get('mid_range', '60,000 - 100,000')}
• **Junior Level:** Rs. {summary.get('junior_range', '30,000 - 60,000')}

**📅 Period:** {summary.get('period', 'Monthly')}
**🗓️ Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        return response
    
    def execute_with_tools(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        Execute payroll-specific tools
        """
        tool_responses = []
        execution_success = True
        result_data = {}
        
        try:
            action = request_data.get('action')
            entities = request_data.get('entities', {})
            user_context = request_data.get('user_context', {})
            
            if action == 'calculate_individual_payroll':
                employee_name = request_data.get('employee_name', user_context.get('username'))
                
                # Tool 1: Calculate individual payroll
                if 'calculate_individual_payroll' in available_tools:
                    payroll_data = self._calculate_individual_payroll_data(employee_name, entities,user_context)
                    tool_responses.append({'tool': 'calculate_individual_payroll', 'result': payroll_data})
                    result_data['payroll_data'] = payroll_data
                
                # Tool 2: Calculate deductions
                if 'calculate_deductions' in available_tools and result_data.get('payroll_data'):
                    deductions = self._calculate_deductions(result_data['payroll_data'])
                    result_data['payroll_data']['deductions'] = deductions
                
                # Tool 3: Calculate benefits
                if 'calculate_benefits' in available_tools and result_data.get('payroll_data'):
                    benefits = self._calculate_benefits(result_data['payroll_data'])
                    result_data['payroll_data']['benefits'] = benefits
                    
            elif action == 'calculate_department_payroll':
                department = request_data.get('department')
                
                if 'calculate_department_payroll' in available_tools:
                    dept_data = self._calculate_department_payroll_data(department, entities)
                    tool_responses.append({'tool': 'calculate_department_payroll', 'result': dept_data})
                    result_data['department_data'] = dept_data
                    
            elif action == 'get_payroll_history':
                employee_name = request_data.get('employee_name')
                
                if 'get_payroll_history' in available_tools:
                    history = self._get_payroll_history_data(employee_name, entities)
                    tool_responses.append({'tool': 'get_payroll_history', 'result': history})
                    result_data['payroll_history'] = history
                    
            elif action == 'get_payroll_summary':
                if 'get_payroll_summary' in available_tools:
                    summary = self._get_payroll_summary_data(entities)
                    tool_responses.append({'tool': 'get_payroll_summary', 'result': summary})
                    result_data['payroll_summary'] = summary
            
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
    def _calculate_individual_payroll_data(self, employee_name: str, entities: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate individual payroll data by fetching real data from the database.
        """
        try:
            # Find the user from the database
            target_user = self.user_model.get_user_by_username(employee_name)
            if not target_user:
                return {'error': f'Employee "{employee_name}" not found in the database.'}

            basic_salary = target_user.get('salary', 0.0)
            
            # Calculate allowances (can be made dynamic later)
            allowances = {
                'transport': self.ALLOWANCES['transport'],
                'meal': self.ALLOWANCES['meal'],
                'medical': self.ALLOWANCES['medical']
            }
            
            total_allowances = sum(allowances.values())
            gross_pay = basic_salary + total_allowances
            
            # Calculate deductions
            deductions = {
                'income_tax': gross_pay * self.TAX_RATES['income_tax'],
                'epf_employee': basic_salary * self.TAX_RATES['epf_employee'], # EPF is often on basic
                'etf': basic_salary * self.TAX_RATES['etf'], # ETF is often on basic
                'epf_employer': basic_salary * self.TAX_RATES['epf_employer']
            }
            
            total_deductions = deductions['income_tax'] + deductions['epf_employee']
            
            # Calculate net pay (Correction: ETF is not deducted from employee salary)
            net_pay = gross_pay - total_deductions
            
            return {
                'employee_name': employee_name,
                'basic_salary': float(basic_salary),
                'allowances': allowances,
                'gross_pay': float(gross_pay),
                'deductions': {k: float(v) for k, v in deductions.items()},
                'net_pay': float(net_pay),
                'period': 'Monthly',
                'calculation_date': datetime.now().strftime('%Y-%m-%d'),
                'employee_id': target_user.get('employee_id', 'N/A'),
                'department': target_user.get('department', 'N/A'),
                'position': target_user.get('position', 'N/A'),
                'tax_year': datetime.now().year,
                'next_pay_date': 'End of month'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_department_payroll_data(self, department: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate department payroll data by fetching real user data.
        """
        try:
            # Get all users in the specified department
            department_users = self.user_model.get_all_users(role=None, department=department)

            if not department_users:
                return {'error': f'No employees found in {department} department.'}

            employee_payroll_list = []
            total_gross_pay = 0
            total_net_pay = 0

            for user in department_users:
                # Reuse the individual calculation logic for each user
                # We pass a minimal user_context needed for the calculation
                individual_payroll = self._calculate_individual_payroll_data(user['username'], {}, {'user_id': user['_id']})
                
                if not individual_payroll.get('error'):
                    employee_data = {
                        'name': user.get('full_name', user['username']),
                        'gross_pay': individual_payroll['gross_pay'],
                        'net_pay': individual_payroll['net_pay'],
                        'position': user.get('position', 'N/A')
                    }
                    employee_payroll_list.append(employee_data)
                    total_gross_pay += individual_payroll['gross_pay']
                    total_net_pay += individual_payroll['net_pay']

            if not employee_payroll_list:
                 return {'error': f'Could not process payroll for any employee in {department} department.'}

            # Find highest paid employee based on net pay
            highest_paid_employee = max(employee_payroll_list, key=lambda x: x['net_pay'])

            return {
                'department': department,
                'employees': employee_payroll_list,
                'total_gross': total_gross_pay,
                'total_net': total_net_pay,
                'employee_count': len(employee_payroll_list),
                'average_salary': total_net_pay / len(employee_payroll_list),
                'highest_paid': highest_paid_employee['name'],
                'highest_salary': highest_paid_employee['net_pay'],
                'period': 'Monthly'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_deductions(self, payroll_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate payroll deductions
        """
        try:
            gross_pay = payroll_data.get('gross_pay', 0)
            
            deductions = {
                'income_tax': gross_pay * self.TAX_RATES['income_tax'],
                'epf_employee': gross_pay * self.TAX_RATES['epf_employee'],
                'etf': gross_pay * self.TAX_RATES['etf'],
                'epf_employer': gross_pay * self.TAX_RATES['epf_employer']
            }
            
            return deductions
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_benefits(self, payroll_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate employee benefits
        """
        try:
            return {
                'health_insurance': 5000,
                'life_insurance': 2000,
                'performance_bonus': 0,
                'overtime_pay': 0
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_payroll_history_data(self, employee_name: str, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get payroll history data
        """
        try:
            # Sample payroll history
            history = [
                {'period': 'January 2024', 'net_pay': 85000, 'gross_pay': 110000, 'pay_date': '2024-01-31', 'year': 2024},
                {'period': 'December 2023', 'net_pay': 82000, 'gross_pay': 107000, 'pay_date': '2023-12-31', 'year': 2023},
                {'period': 'November 2023', 'net_pay': 85000, 'gross_pay': 110000, 'pay_date': '2023-11-30', 'year': 2023},
                {'period': 'October 2023', 'net_pay': 83000, 'gross_pay': 108000, 'pay_date': '2023-10-31', 'year': 2023},
                {'period': 'September 2023', 'net_pay': 85000, 'gross_pay': 110000, 'pay_date': '2023-09-30', 'year': 2023},
                {'period': 'August 2023', 'net_pay': 84000, 'gross_pay': 109000, 'pay_date': '2023-08-31', 'year': 2023}
            ]
            
            return history
            
        except Exception as e:
            return []
    
    def _get_payroll_summary_data(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get payroll summary data
        """
        try:
            return {
                'total_employees': 50,
                'total_payroll': 4250000,
                'average_salary': 85000,
                'departments': [
                    {'name': 'IT', 'employee_count': 20, 'total_payroll': 1800000},
                    {'name': 'HR', 'employee_count': 8, 'total_payroll': 600000},
                    {'name': 'Finance', 'employee_count': 12, 'total_payroll': 950000},
                    {'name': 'Marketing', 'employee_count': 10, 'total_payroll': 900000}
                ],
                'current_month': 4250000,
                'last_month': 4100000,
                'change_percentage': 3.7,
                'senior_range': '100,000 - 200,000',
                'mid_range': '60,000 - 100,000',
                'junior_range': '30,000 - 60,000',
                'period': 'Monthly'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _requires_human_approval(self, request_data: Dict[str, Any]) -> bool:
        """
        Check if payroll request requires human approval
        """
        # Generally, payroll calculations don't require approval
        # But department-wide calculations might need HR approval
        return request_data.get('action') == 'calculate_department_payroll'
    
    def format_response(self, response_data: Dict[str, Any]) -> str:
        """
        Format response for the user
        """
        try:
            if response_data.get('error'):
                return f"❌ Error: {response_data['error']}"
            
            return response_data.get('response', 'Payroll calculation completed successfully.')
            
        except Exception as e:
            return f"Error formatting response: {str(e)}"