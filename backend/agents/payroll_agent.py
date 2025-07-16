# backend/agents/payroll_agent.py
from agents.base_agent import BaseAgent
from models.payroll import Payroll
from models.user import User
from typing import Dict, Any, List
from datetime import datetime, timedelta
import calendar
import re
import json

class PayrollAgent(BaseAgent):
    """
    Enhanced specialized agent for payroll calculation and management
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        super().__init__(gemini_api_key, db_connection, memory_manager)
        self.payroll_model = Payroll(db_connection)
        self.user_model = User(db_connection)
        
        # Enhanced payroll calculation rules (configurable in real system)
        self.payroll_rules = {
            'tax_rate': 0.10,  # 10% income tax
            'epf_employee': 0.08,  # 8% EPF employee contribution
            'epf_employer': 0.12,  # 12% EPF employer contribution
            'etf_employer': 0.03,  # 3% ETF employer contribution
            'overtime_rate': 1.5,  # 1.5x for overtime
            'working_days_per_month': 22,
            'working_hours_per_day': 8,
            'allowances': {
                'house_rent': 15000,
                'transport': 8000,
                'mobile': 3000,
                'meal': 5000
            }
        }
        
        # Enhanced salary matrix (in real system, this would be in database)
        self.salary_matrix = {
            'IT': {
                'junior_developer': 80000,
                'developer': 120000,
                'senior_developer': 180000,
                'tech_lead': 250000,
                'manager': 300000,
                'director': 500000
            },
            'HR': {
                'hr_executive': 70000,
                'hr_manager': 150000,
                'director': 350000
            },
            'Finance': {
                'accountant': 75000,
                'senior_accountant': 120000,
                'finance_manager': 200000,
                'cfo': 600000
            },
            'Marketing': {
                'marketing_executive': 65000,
                'marketing_manager': 140000,
                'brand_manager': 180000,
                'marketing_director': 350000
            },
            'Sales': {
                'sales_executive': 60000,
                'sales_manager': 130000,
                'regional_manager': 200000,
                'sales_director': 350000
            }
        }
        
        # Payroll-specific prompt templates
        self.prompt_templates.update({
            'payroll_understanding': """
            Analyze this payroll request from {username} ({role}):
            Message: "{message}"
            Context: {context}
            
            Extract (respond in JSON only):
            {{
                "intent": "individual_payroll|department_payroll|payroll_breakdown|my_payroll|payroll_comparison",
                "entities": {{
                    "employee_name": "specific employee name",
                    "department": "IT|HR|Finance|Marketing|Sales",
                    "calculation_type": "gross|net|breakdown|summary",
                    "time_period": "current|month|year|specific_date",
                    "comparison_type": "department|individual|historical"
                }},
                "confidence": 0.0-1.0,
                "permission_level": "self_only|department|company_wide"
            }}
            
            Permission rules:
            - Regular users: can only view their own payroll
            - HR users: can view all employee payrolls and department summaries
            """,
            
            'payroll_response': """
            Generate a professional payroll response for: "{message}"
            
            User: {username} ({role})
            Payroll Data: {payroll_data}
            Calculations: {calculations}
            Permissions: {permissions}
            
            Guidelines:
            - Be professional and accurate with financial information
            - Show clear breakdown of calculations
            - Include relevant allowances and deductions
            - Respect privacy - only show authorized information
            - Use proper formatting for currency (Rs. X,XXX.XX)
            - Provide actionable insights where appropriate
            """
        })
        
        # Available tools for payroll operations
        self.available_tools = [
            'calculate_individual_payroll',
            'calculate_department_payroll',
            'get_payroll_breakdown',
            'validate_payroll_permissions',
            'get_payroll_history',
            'generate_payroll_report'
        ]
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced payroll request processing with permission validation"""
        try:
            # Extract request components
            intent = request_data.get('intent', 'individual_payroll')
            message = request_data.get('message', '')
            entities = request_data.get('entities', {})
            user_context = request_data.get('user_context', {})
            
            # Enhanced understanding with payroll-specific context
            understanding = self._enhanced_payroll_understanding(message, user_context)
            
            # Merge entities
            understanding['entities'].update(entities)
            
            # Validate permissions before processing
            permission_check = self._validate_payroll_permissions(understanding, user_context)
            if not permission_check['allowed']:
                return self.format_error_response(permission_check['error_message'])
            
            # Route to appropriate handler
            if understanding['intent'] == 'my_payroll' or understanding['intent'] == 'individual_payroll':
                return self._handle_individual_payroll(message, understanding, user_context)
            elif understanding['intent'] == 'department_payroll':
                return self._handle_department_payroll(message, understanding, user_context)
            elif understanding['intent'] == 'payroll_breakdown':
                return self._handle_payroll_breakdown(message, understanding, user_context)
            elif understanding['intent'] == 'payroll_comparison':
                return self._handle_payroll_comparison(message, understanding, user_context)
            else:
                return self._handle_individual_payroll(message, understanding, user_context)
                
        except Exception as e:
            return self.format_error_response(f"Error processing payroll request: {str(e)}")
    
    def _enhanced_payroll_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced understanding specifically for payroll requests"""
        
        # Get payroll-specific memory context
        memory_context = self._get_payroll_memory_context(user_context.get('user_id'))
        
        # Build enhanced prompt
        prompt = self.prompt_templates['payroll_understanding'].format(
            username=user_context.get('username', 'User'),
            role=user_context.get('role', 'user'),
            message=message,
            context=json.dumps(memory_context, default=str)[:200]
        )
        
        # Generate understanding
        response = self.generate_response(prompt)
        
        # Parse with fallback
        try:
            understanding = json.loads(response.strip())
        except:
            understanding = self._fallback_payroll_understanding(message, user_context)
        
        return understanding
    
    def _fallback_payroll_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback payroll understanding using pattern matching"""
        message_lower = message.lower()
        user_role = user_context.get('role', 'user')
        
        # Intent detection
        if any(word in message_lower for word in ['my payroll', 'මගේ වැටුප්', 'my salary']):
            intent = 'my_payroll'
        elif any(word in message_lower for word in ['department payroll', 'team payroll']):
            intent = 'department_payroll'
        elif any(word in message_lower for word in ['breakdown', 'detailed', 'විස්තර']):
            intent = 'payroll_breakdown'
        elif any(word in message_lower for word in ['compare', 'comparison']):
            intent = 'payroll_comparison'
        else:
            intent = 'individual_payroll'
        
        # Extract entities
        entities = {}
        
        # Extract employee name
        if ' for ' in message_lower:
            parts = message_lower.split(' for ')
            if len(parts) > 1:
                name_part = parts[1].split()[0]
                entities['employee_name'] = name_part
        
        # Extract department
        departments = ['it', 'hr', 'finance', 'marketing', 'sales', 'engineering']
        for dept in departments:
            if dept in message_lower:
                entities['department'] = dept.upper()
                break
        
        # Check for self-reference
        if any(word in message_lower for word in ['my', 'මගේ', 'own']):
            entities['self_payroll'] = True
        
        # Determine permission level
        if entities.get('department') and user_role != 'hr':
            permission_level = 'unauthorized'
        elif entities.get('employee_name') and user_role != 'hr':
            permission_level = 'self_only'
        elif user_role == 'hr':
            permission_level = 'company_wide'
        else:
            permission_level = 'self_only'
        
        return {
            'intent': intent,
            'entities': entities,
            'confidence': 0.7,
            'permission_level': permission_level
        }
    
    def _get_payroll_memory_context(self, user_id: str) -> Dict[str, Any]:
        """Get payroll-specific memory context"""
        if not user_id:
            return {}
        
        try:
            # Get recent payroll interactions
            recent_context = self.memory_manager.short_term.get_conversation_history(user_id, limit=2)
            payroll_interactions = [ctx for ctx in recent_context if 'payroll' in str(ctx).lower() or 'salary' in str(ctx).lower()]
            
            # Get payroll patterns
            payroll_patterns = self.memory_manager.long_term.get_interaction_patterns(
                user_id, pattern_type='payroll_calculation', days_back=30
            )
            
            return {
                'recent_payroll_interactions': payroll_interactions,
                'payroll_patterns': payroll_patterns[:1],
                'user_payroll_preferences': self._get_user_payroll_preferences(user_id)
            }
        except:
            return {}
    
    def _get_user_payroll_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's payroll viewing preferences"""
        try:
            # Get user's payroll history to identify preferences
            successful_interactions = self.memory_manager.long_term.get_successful_interactions(
                user_id, interaction_type='payroll_calculation', limit=5
            )
            
            if not successful_interactions:
                return {}
            
            # Analyze preferred calculation types
            calc_types = []
            for interaction in successful_interactions:
                entities = interaction.get('details', {}).get('entities', {})
                calc_type = entities.get('calculation_type', 'summary')
                calc_types.append(calc_type)
            
            preferred_calc_type = max(set(calc_types), key=calc_types.count) if calc_types else 'summary'
            
            return {
                'preferred_calculation_type': preferred_calc_type,
                'interaction_frequency': len(successful_interactions),
                'last_interaction': successful_interactions[0].get('created_at') if successful_interactions else None
            }
        except:
            return {}
    
    def _validate_payroll_permissions(self, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, bool]:
        """Validate user permissions for payroll operations"""
        
        user_role = user_context.get('role', 'user')
        user_id = user_context.get('user_id', '')
        entities = understanding.get('entities', {})
        
        # HR users have full access
        if user_role == 'hr':
            return {'allowed': True, 'access_level': 'full'}
        
        # Check if user is trying to access others' payroll
        employee_name = entities.get('employee_name')
        department = entities.get('department')
        
        if department:
            return {
                'allowed': False,
                'error_message': '❌ Access Denied: Only HR personnel can view department payroll information.\n\nYou can view your own payroll by asking: "Calculate my payroll"'
            }
        
        if employee_name:
            # Check if it's their own name
            username = user_context.get('username', '').lower()
            if employee_name.lower() not in username and username not in employee_name.lower():
                return {
                    'allowed': False,
                    'error_message': '❌ Access Denied: You can only view your own payroll information.\n\nTry asking: "Show me my payroll" or "Calculate my salary"'
                }
        
        return {'allowed': True, 'access_level': 'self_only'}
    
    def _handle_individual_payroll(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle individual payroll calculation requests"""
        try:
            entities = understanding.get('entities', {})
            user_role = user_context.get('role', 'user')
            
            # Determine target employee
            if entities.get('self_payroll') or not entities.get('employee_name'):
                target_user_id = user_context.get('user_id')
                target_username = user_context.get('username')
            else:
                # HR requesting someone else's payroll
                employee_name = entities.get('employee_name')
                target_user_id = self._get_user_id_by_name(employee_name)
                target_username = employee_name
                
                if not target_user_id:
                    return self.format_error_response(f'❌ Employee "{employee_name}" not found in the system.')
            
            # Execute payroll calculation tools
            tool_results = self.execute_with_tools({
                'action': 'calculate_individual_payroll',
                'target_user_id': target_user_id,
                'calculation_type': entities.get('calculation_type', 'summary'),
                'user_context': user_context
            }, ['calculate_individual_payroll', 'get_payroll_breakdown'])
            
            if not tool_results.get('execution_success'):
                return self.format_error_response(f"❌ Payroll calculation failed: {tool_results.get('error', 'Unknown error')}")
            
            payroll_data = tool_results.get('payroll_data', {})
            calculation_details = tool_results.get('calculation_details', {})
            
            # Generate professional response
            response = self._generate_individual_payroll_response(
                payroll_data, calculation_details, target_username, user_role
            )
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error calculating individual payroll: {str(e)}")
    
    def _handle_department_payroll(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle department payroll calculation (HR only)"""
        try:
            entities = understanding.get('entities', {})
            department = entities.get('department', '').upper()
            
            if not department:
                return self.format_error_response(
                    '❌ Please specify which department\'s payroll you want to calculate.\n\nExample: "Calculate IT department payroll"'
                )
            
            # Execute department payroll calculation
            tool_results = self.execute_with_tools({
                'action': 'calculate_department_payroll',
                'department': department,
                'user_context': user_context
            }, ['calculate_department_payroll', 'generate_payroll_report'])
            
            if not tool_results.get('execution_success'):
                return self.format_error_response(f"❌ Department payroll calculation failed: {tool_results.get('error', 'Unknown error')}")
            
            department_data = tool_results.get('department_data', {})
            summary_stats = tool_results.get('summary_stats', {})
            
            response = self._generate_department_payroll_response(department, department_data, summary_stats)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error calculating department payroll: {str(e)}")
    
    def _handle_payroll_breakdown(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detailed payroll breakdown requests"""
        try:
            entities = understanding.get('entities', {})
            
            # Determine target (self or specified employee)
            target_user_id = user_context.get('user_id')
            target_username = user_context.get('username')
            
            employee_name = entities.get('employee_name')
            if employee_name and user_context.get('role') == 'hr':
                target_user_id = self._get_user_id_by_name(employee_name)
                target_username = employee_name
            
            # Execute detailed breakdown calculation
            tool_results = self.execute_with_tools({
                'action': 'get_detailed_payroll_breakdown',
                'target_user_id': target_user_id,
                'user_context': user_context
            }, ['get_payroll_breakdown', 'calculate_individual_payroll'])
            
            if not tool_results.get('execution_success'):
                return self.format_error_response(f"❌ Payroll breakdown failed: {tool_results.get('error', 'Unknown error')}")
            
            breakdown_data = tool_results.get('breakdown_data', {})
            
            response = self._generate_payroll_breakdown_response(breakdown_data, target_username)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error generating payroll breakdown: {str(e)}")
    
    def _handle_payroll_comparison(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payroll comparison requests (HR only)"""
        try:
            if user_context.get('role') != 'hr':
                return self.format_error_response('❌ Payroll comparison functionality is only available for HR personnel.')
            
            entities = understanding.get('entities', {})
            comparison_type = entities.get('comparison_type', 'department')
            
            # Execute comparison analysis
            tool_results = self.execute_with_tools({
                'action': 'generate_payroll_comparison',
                'comparison_type': comparison_type,
                'user_context': user_context
            }, ['generate_payroll_report', 'calculate_department_payroll'])
            
            comparison_data = tool_results.get('comparison_data', {})
            
            response = self._generate_payroll_comparison_response(comparison_data, comparison_type)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error generating payroll comparison: {str(e)}")
    
    def _generate_individual_payroll_response(self, payroll_data: Dict[str, Any], 
                                            calculation_details: Dict[str, Any], 
                                            username: str, user_role: str) -> str:
        """Generate individual payroll response"""
        
        response = f"💰 **Payroll Calculation for {username}**\n\n"
        
        # Basic salary information
        basic_salary = payroll_data.get('basic_salary', 0)
        allowances = payroll_data.get('allowances', {})
        deductions = payroll_data.get('deductions', {})
        gross_salary = payroll_data.get('gross_salary', 0)
        net_salary = payroll_data.get('net_salary', 0)
        
        response += "**📊 Salary Breakdown:**\n"
        response += f"💵 **Basic Salary**: Rs. {basic_salary:,.2f}\n\n"
        
        # Allowances section
        if allowances:
            response += "**➕ Allowances:**\n"
            total_allowances = 0
            for allowance, amount in allowances.items():
                response += f"   • {allowance.replace('_', ' ').title()}: Rs. {amount:,.2f}\n"
                total_allowances += amount
            response += f"   **Total Allowances**: Rs. {total_allowances:,.2f}\n\n"
        
        response += f"**💰 Gross Salary**: Rs. {gross_salary:,.2f}\n\n"
        
        # Deductions section
        if deductions:
            response += "**➖ Deductions:**\n"
            total_deductions = 0
            for deduction, amount in deductions.items():
                percentage = ""
                if deduction == 'income_tax':
                    percentage = " (10%)"
                elif deduction == 'epf':
                    epf_rate = (amount / basic_salary) * 100 if basic_salary > 0 else 0
                    response += f"   🏦 EPF Employee: Rs. {amount:,.2f} ({epf_rate:.1f}%)\n"
                    response += f"      (8% of basic salary for retirement)\n"
                    
                elif deduction == 'professional_tax':
                    response += f"   📋 Professional Tax: Rs. {amount:,.2f}\n"
                    response += f"      (State professional tax)\n"
                    
                total_deductions += amount
            
            response += f"   **📊 Total Deductions**: Rs. {total_deductions:,.2f}\n\n"
        
        # Net salary calculation
        net_salary = breakdown_data.get('net_salary', 0)
        response += f"**🎯 Net Salary Calculation:**\n"
        response += f"💰 Gross Salary: Rs. {gross_salary:,.2f}\n"
        response += f"➖ Total Deductions: Rs. {total_deductions:,.2f}\n"
        response += f"💵 **Net Take-Home**: Rs. {net_salary:,.2f}\n\n"
        
        # Employer contributions (informational)
        employer_epf = basic_salary * 0.12 if basic_salary > 0 else 0
        employer_etf = basic_salary * 0.03 if basic_salary > 0 else 0
        
        response += "**🏢 Employer Contributions (For Your Information):**\n"
        response += f"🏦 EPF Employer (12%): Rs. {employer_epf:,.2f}\n"
        response += f"🎓 ETF Employer (3%): Rs. {employer_etf:,.2f}\n"
        response += f"🏥 Insurance Premiums: Rs. {breakdown_data.get('insurance_cost', 5000):,.2f}\n"
        response += f"💊 Medical Benefits: Rs. {breakdown_data.get('medical_benefits', 3000):,.2f}\n\n"
        
        # Annual projections
        annual_gross = gross_salary * 12
        annual_net = net_salary * 12
        
        response += "**📅 Annual Projections:**\n"
        response += f"💰 Annual Gross: Rs. {annual_gross:,.2f}\n"
        response += f"💵 Annual Net: Rs. {annual_net:,.2f}\n"
        response += f"🎁 Performance Bonus: Variable (up to 2 months salary)\n"
        response += f"🏖️ Leave Encashment: Available for unused leave\n\n"
        
        # Tax savings opportunities
        response += "**💡 Tax Saving Opportunities:**\n"
        response += "📚 Education Allowance: Up to Rs. 100,000/year\n"
        response += "🏥 Medical Reimbursement: Up to Rs. 50,000/year\n"
        response += "🚗 Transport Allowance: Up to Rs. 19,200/year\n"
        response += "📱 Communication Allowance: Up to Rs. 36,000/year\n"
        response += "🏠 HRA: Actual rent paid or 50% of salary\n\n"
        
        # Comparison with industry standards
        response += "**📊 Industry Comparison:**\n"
        position = breakdown_data.get('position', '').lower()
        department = breakdown_data.get('department', '').lower()
        
        if 'developer' in position:
            response += "💻 Software Developer avg in Sri Lanka: Rs. 80,000 - 200,000\n"
        elif 'manager' in position:
            response += "👔 Manager avg in Sri Lanka: Rs. 150,000 - 350,000\n"
        else:
            response += f"📈 {position.title()} market range varies by experience\n"
        
        response += "🎯 Your package is competitive within industry standards\n"
        response += "📈 Next review scheduled: Annual performance cycle\n\n"
        
        # Action items
        response += "**🚀 Next Steps:**\n"
        response += "📋 Download payslip: Contact HR for official document\n"
        response += "🏦 EPF statement: Check with EPF department quarterly\n"
        response += "📊 Tax planning: Consult with tax advisor for optimization\n"
        response += "💰 Investment planning: Consider retirement and insurance needs\n"
        
        return response
    
    def _generate_payroll_comparison_response(self, comparison_data: Dict[str, Any], comparison_type: str) -> str:
        """Generate payroll comparison response"""
        
        response = f"📊 **Payroll Comparison Analysis** ({comparison_type})\n\n"
        
        if comparison_type == 'department':
            departments = comparison_data.get('departments', {})
            
            response += "**🏢 Department-wise Comparison:**\n\n"
            
            # Sort departments by average salary
            sorted_depts = sorted(departments.items(), key=lambda x: x[1].get('average_salary', 0), reverse=True)
            
            for i, (dept, data) in enumerate(sorted_depts, 1):
                avg_salary = data.get('average_salary', 0)
                employee_count = data.get('employee_count', 0)
                total_cost = data.get('total_cost', 0)
                
                response += f"**{i}. {dept} Department**\n"
                response += f"   👥 Employees: {employee_count}\n"
                response += f"   💰 Average Salary: Rs. {avg_salary:,.2f}\n"
                response += f"   💸 Total Cost: Rs. {total_cost:,.2f}\n"
                response += f"   📊 Cost per Employee: Rs. {total_cost/employee_count if employee_count > 0 else 0:,.2f}\n\n"
            
            # Summary statistics
            total_employees = sum(d.get('employee_count', 0) for d in departments.values())
            total_payroll = sum(d.get('total_cost', 0) for d in departments.values())
            company_average = total_payroll / total_employees if total_employees > 0 else 0
            
            response += "**📈 Company Summary:**\n"
            response += f"👥 Total Employees: {total_employees}\n"
            response += f"💰 Company Average Salary: Rs. {company_average:,.2f}\n"
            response += f"💸 Total Monthly Payroll: Rs. {total_payroll:,.2f}\n"
            response += f"📅 Annual Payroll Budget: Rs. {total_payroll * 12:,.2f}\n\n"
            
            # Insights
            highest_dept = sorted_depts[0][0] if sorted_depts else 'N/A'
            lowest_dept = sorted_depts[-1][0] if sorted_depts else 'N/A'
            
            response += "**💡 Key Insights:**\n"
            response += f"📈 Highest paying department: {highest_dept}\n"
            response += f"📉 Most cost-effective department: {lowest_dept}\n"
            
            # Calculate salary distribution
            high_earners = sum(1 for d in departments.values() if d.get('average_salary', 0) > company_average * 1.2)
            response += f"💰 Departments above company average (+20%): {high_earners}\n"
            
        return response
    
    def execute_with_tools(self, request_data: Dict[str, Any], tools: List[str]) -> Dict[str, Any]:
        """Execute payroll request using specialized tools"""
        
        tool_responses = []
        execution_success = True
        result_data = {}
        
        try:
            action = request_data.get('action', '')
            user_context = request_data.get('user_context', {})
            
            if action == 'calculate_individual_payroll':
                target_user_id = request_data.get('target_user_id')
                calc_type = request_data.get('calculation_type', 'summary')
                
                payroll_data = self._calculate_individual_payroll_data(target_user_id)
                
                if payroll_data:
                    result_data['payroll_data'] = payroll_data
                    
                    if 'get_payroll_breakdown' in tools:
                        breakdown = self._get_detailed_breakdown(payroll_data, target_user_id)
                        result_data['calculation_details'] = breakdown
                else:
                    execution_success = False
                    result_data['error'] = 'Unable to calculate payroll - employee data not found'
                    
            elif action == 'calculate_department_payroll':
                department = request_data.get('department')
                
                dept_data = self._calculate_department_payroll_data(department)
                
                if dept_data:
                    result_data['department_data'] = dept_data
                    
                    if 'generate_payroll_report' in tools:
                        summary_stats = self._generate_department_summary_stats(dept_data)
                        result_data['summary_stats'] = summary_stats
                else:
                    execution_success = False
                    result_data['error'] = f'No employees found in {department} department'
                    
            elif action == 'get_detailed_payroll_breakdown':
                target_user_id = request_data.get('target_user_id')
                
                payroll_data = self._calculate_individual_payroll_data(target_user_id)
                
                if payroll_data:
                    detailed_breakdown = self._get_detailed_breakdown(payroll_data, target_user_id)
                    result_data['breakdown_data'] = detailed_breakdown
                else:
                    execution_success = False
                    result_data['error'] = 'Unable to generate breakdown - employee data not found'
                    
            elif action == 'generate_payroll_comparison':
                comparison_type = request_data.get('comparison_type', 'department')
                
                comparison_data = self._generate_comparison_data(comparison_type)
                result_data['comparison_data'] = comparison_data
            
        except Exception as e:
            execution_success = False
            result_data['error'] = str(e)
        
        return {
            'tool_responses': tool_responses,
            'execution_success': execution_success,
            'requires_human_approval': False,  # Payroll calculations usually don't need approval
            **result_data
        }
    
    # Tool implementation methods
    def _calculate_individual_payroll_data(self, user_id: str) -> Dict[str, Any]:
        """Calculate individual employee payroll data"""
        try:
            # Get user data
            user_data = self.user_model.get_user_by_id(user_id)
            if not user_data:
                return None
            
            # Get salary information
            department = user_data.get('department', 'IT').upper()
            position = user_data.get('position', 'developer').lower()
            
            # Calculate basic salary based on department and position
            dept_salaries = self.salary_matrix.get(department, self.salary_matrix['IT'])
            basic_salary = dept_salaries.get(position, dept_salaries.get('developer', 120000))
            
            # Apply any custom salary if available
            if user_data.get('custom_salary'):
                basic_salary = user_data['custom_salary']
            
            # Calculate allowances
            allowances = {
                'house_rent': self.payroll_rules['allowances']['house_rent'],
                'transport': self.payroll_rules['allowances']['transport'],
                'mobile': self.payroll_rules['allowances']['mobile'],
                'meal': self.payroll_rules['allowances']['meal']
            }
            
            total_allowances = sum(allowances.values())
            gross_salary = basic_salary + total_allowances
            
            # Calculate deductions
            income_tax = gross_salary * self.payroll_rules['tax_rate']
            epf_employee = basic_salary * self.payroll_rules['epf_employee']
            professional_tax = 200  # Fixed professional tax
            
            deductions = {
                'income_tax': income_tax,
                'epf': epf_employee,
                'professional_tax': professional_tax
            }
            
            total_deductions = sum(deductions.values())
            net_salary = gross_salary - total_deductions
            
            return {
                'basic_salary': basic_salary,
                'allowances': allowances,
                'gross_salary': gross_salary,
                'deductions': deductions,
                'net_salary': net_salary,
                'department': department,
                'position': position,
                'employee_name': user_data.get('username', 'Unknown')
            }
            
        except Exception as e:
            print(f"Error calculating individual payroll: {str(e)}")
            return None
    
    def _calculate_department_payroll_data(self, department: str) -> Dict[str, Any]:
        """Calculate department payroll data"""
        try:
            # Get all users in department
            all_users = self.user_model.get_all_users()
            department_users = [user for user in all_users if user.get('department', '').upper() == department]
            
            if not department_users:
                return None
            
            employees_data = []
            total_gross = 0
            total_net = 0
            
            for user in department_users:
                payroll = self._calculate_individual_payroll_data(user['user_id'])
                if payroll:
                    employee_data = {
                        'name': user.get('username', 'Unknown'),
                        'position': payroll['position'],
                        'basic_salary': payroll['basic_salary'],
                        'gross_salary': payroll['gross_salary'],
                        'net_salary': payroll['net_salary']
                    }
                    employees_data.append(employee_data)
                    total_gross += payroll['gross_salary']
                    total_net += payroll['net_salary']
            
            return {
                'employees': employees_data,
                'total_gross': total_gross,
                'total_net': total_net,
                'employee_count': len(employees_data)
            }
            
        except Exception as e:
            print(f"Error calculating department payroll: {str(e)}")
            return None
    
    def _get_detailed_breakdown(self, payroll_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Get detailed payroll breakdown"""
        
        # Add additional details to payroll data
        breakdown = payroll_data.copy()
        
        # Add working days calculation
        today = datetime.now()
        _, days_in_month = calendar.monthrange(today.year, today.month)
        working_days = self.payroll_rules['working_days_per_month']
        
        breakdown['working_days'] = working_days
        breakdown['days_in_month'] = days_in_month
        
        # Add employer costs (informational)
        basic_salary = payroll_data.get('basic_salary', 0)
        breakdown['employer_epf'] = basic_salary * self.payroll_rules['epf_employer']
        breakdown['employer_etf'] = basic_salary * self.payroll_rules['etf_employer']
        breakdown['insurance_cost'] = 5000  # Estimated monthly insurance cost
        breakdown['medical_benefits'] = 3000  # Estimated monthly medical benefits
        
        # Add tax year information
        breakdown['tax_year'] = today.year
        breakdown['calculation_date'] = today.strftime('%Y-%m-%d')
        
        return breakdown
    
    def _generate_department_summary_stats(self, dept_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate department summary statistics"""
        
        employees = dept_data.get('employees', [])
        if not employees:
            return {}
        
        # Calculate statistics
        salaries = [emp['net_salary'] for emp in employees]
        total_employees = len(employees)
        
        summary = {
            'total_gross': dept_data.get('total_gross', 0),
            'total_net': dept_data.get('total_net', 0),
            'average_salary': sum(salaries) / total_employees if total_employees > 0 else 0,
            'highest_salary': max(salaries) if salaries else 0,
            'lowest_salary': min(salaries) if salaries else 0,
            'median_salary': sorted(salaries)[total_employees//2] if salaries else 0,
            'salary_range': max(salaries) - min(salaries) if salaries else 0
        }
        
        # Calculate employer costs
        basic_salaries = [emp['basic_salary'] for emp in employees]
        total_basic = sum(basic_salaries)
        
        summary['epf_employer'] = total_basic * self.payroll_rules['epf_employer']
        summary['etf_employer'] = total_basic * self.payroll_rules['etf_employer']
        summary['benefits_cost'] = total_employees * 8000  # Estimated benefits per employee
        summary['total_employer_cost'] = (summary['total_net'] + summary['epf_employer'] + 
                                        summary['etf_employer'] + summary['benefits_cost'])
        
        # Position distribution
        positions = {}
        for emp in employees:
            position = emp['position']
            positions[position] = positions.get(position, 0) + 1
        
        summary['position_distribution'] = positions
        
        return summary
    
    def _generate_comparison_data(self, comparison_type: str) -> Dict[str, Any]:
        """Generate comparison data between departments or other criteria"""
        
        if comparison_type == 'department':
            departments = {}
            all_users = self.user_model.get_all_users()
            
            # Group users by department
            dept_users = {}
            for user in all_users:
                dept = user.get('department', 'Unknown').upper()
                if dept not in dept_users:
                    dept_users[dept] = []
                dept_users[dept].append(user)
            
            # Calculate department statistics
            for dept, users in dept_users.items():
                dept_payroll = self._calculate_department_payroll_data(dept)
                if dept_payroll:
                    dept_summary = self._generate_department_summary_stats(dept_payroll)
                    
                    departments[dept] = {
                        'employee_count': len(users),
                        'average_salary': dept_summary.get('average_salary', 0),
                        'total_cost': dept_summary.get('total_employer_cost', 0),
                        'salary_range': dept_summary.get('salary_range', 0)
                    }
            
            return {'departments': departments}
        
        return {}
    
    def _get_user_id_by_name(self, name: str) -> str:
        """Get user ID by name"""
        try:
            all_users = self.user_model.get_all_users()
            for user in all_users:
                if name.lower() in user.get('username', '').lower():
                    return user['user_id']
            return None
        except:
            return None':
                    percentage = " (8%)"
                
                response += f"   • {deduction.replace('_', ' ').title()}{percentage}: Rs. {amount:,.2f}\n"
                total_deductions += amount
            response += f"   **Total Deductions**: Rs. {total_deductions:,.2f}\n\n"
        
        response += f"🎯 **Net Salary**: Rs. {net_salary:,.2f}\n\n"
        
        # Additional information
        department = payroll_data.get('department', 'N/A')
        position = payroll_data.get('position', 'N/A')
        
        response += "**📋 Employment Details:**\n"
        response += f"🏢 Department: {department}\n"
        response += f"💼 Position: {position}\n"
        response += f"📅 Calculation Date: {datetime.now().strftime('%B %Y')}\n\n"
        
        # Benefits information
        response += "**🎁 Additional Benefits:**\n"
        response += "🏥 Medical Insurance: Covered\n"
        response += "🛡️ Life Insurance: Covered\n"
        response += "🎁 Annual Bonus: Performance Based\n"
        response += "🏖️ Paid Leave: 21 Annual + 7 Sick + 7 Casual\n\n"
        
        # Action suggestions based on user role
        if user_role == 'hr':
            response += "**🔧 HR Actions:**\n"
            response += "• Generate payslip document\n"
            response += "• Compare with department average\n"
            response += "• View salary history\n"
            response += "• Update salary components\n"
        else:
            response += "**💡 Available Actions:**\n"
            response += "• Request detailed breakdown: \"Show me detailed payroll breakdown\"\n"
            response += "• View salary history: \"Show my salary history\"\n"
            response += "• Ask about benefits: \"What benefits do I have?\"\n"
        
        return response
    
    def _generate_department_payroll_response(self, department: str, department_data: Dict[str, Any], 
                                            summary_stats: Dict[str, Any]) -> str:
        """Generate department payroll response"""
        
        response = f"🏢 **{department} Department Payroll Summary**\n\n"
        
        employees = department_data.get('employees', [])
        total_employees = len(employees)
        
        response += f"**📊 Department Overview:**\n"
        response += f"👥 Total Employees: {total_employees}\n"
        response += f"💰 Total Gross Payroll: Rs. {summary_stats.get('total_gross', 0):,.2f}\n"
        response += f"💵 Total Net Payroll: Rs. {summary_stats.get('total_net', 0):,.2f}\n"
        response += f"📈 Average Salary: Rs. {summary_stats.get('average_salary', 0):,.2f}\n\n"
        
        # Employee breakdown
        response += "**👥 Employee Breakdown:**\n\n"
        
        for i, employee in enumerate(employees[:10], 1):  # Show top 10
            response += f"**{i}. {employee.get('name', 'Unknown')}**\n"
            response += f"   💼 {employee.get('position', 'N/A')}\n"
            response += f"   💰 Gross: Rs. {employee.get('gross_salary', 0):,.2f}\n"
            response += f"   💵 Net: Rs. {employee.get('net_salary', 0):,.2f}\n\n"
        
        if total_employees > 10:
            response += f"➕ **{total_employees - 10} more employees in department**\n\n"
        
        # Department statistics
        response += "**📈 Department Statistics:**\n"
        response += f"💰 Highest Salary: Rs. {summary_stats.get('highest_salary', 0):,.2f}\n"
        response += f"💵 Lowest Salary: Rs. {summary_stats.get('lowest_salary', 0):,.2f}\n"
        response += f"📊 Salary Range: Rs. {summary_stats.get('salary_range', 0):,.2f}\n"
        response += f"🎯 Median Salary: Rs. {summary_stats.get('median_salary', 0):,.2f}\n\n"
        
        # Position distribution
        position_stats = summary_stats.get('position_distribution', {})
        if position_stats:
            response += "**💼 Position Distribution:**\n"
            for position, count in position_stats.items():
                response += f"• {position.title()}: {count} employees\n"
            response += "\n"
        
        # Cost analysis
        total_cost = summary_stats.get('total_employer_cost', 0)
        response += "**💸 Total Department Cost (Including Benefits):**\n"
        response += f"💰 Employee Salaries: Rs. {summary_stats.get('total_net', 0):,.2f}\n"
        response += f"🏥 EPF Employer (12%): Rs. {summary_stats.get('epf_employer', 0):,.2f}\n"
        response += f"🛡️ ETF Employer (3%): Rs. {summary_stats.get('etf_employer', 0):,.2f}\n"
        response += f"💊 Benefits & Insurance: Rs. {summary_stats.get('benefits_cost', 0):,.2f}\n"
        response += f"🎯 **Total Department Cost**: Rs. {total_cost:,.2f}\n\n"
        
        # Insights and recommendations
        response += "**💡 Insights & Recommendations:**\n"
        avg_salary = summary_stats.get('average_salary', 0)
        if avg_salary > 150000:
            response += "• Department has competitive salary levels\n"
        elif avg_salary < 80000:
            response += "• Consider salary review for retention\n"
        
        if total_employees < 5:
            response += "• Small team - consider expansion if workload is high\n"
        elif total_employees > 20:
            response += "• Large team - consider team structure optimization\n"
        
        response += "• Regular salary benchmarking recommended\n"
        response += "• Monitor for internal equity across positions\n"
        
        return response
    
    def _generate_payroll_breakdown_response(self, breakdown_data: Dict[str, Any], username: str) -> str:
        """Generate detailed payroll breakdown response"""
        
        response = f"📋 **Detailed Payroll Breakdown for {username}**\n\n"
        
        # Basic salary calculation
        basic_salary = breakdown_data.get('basic_salary', 0)
        working_days = breakdown_data.get('working_days', 22)
        daily_rate = basic_salary / working_days if working_days > 0 else 0
        hourly_rate = daily_rate / 8 if daily_rate > 0 else 0
        
        response += "**💰 Basic Salary Calculation:**\n"
        response += f"📅 Working Days: {working_days} days/month\n"
        response += f"💵 Daily Rate: Rs. {daily_rate:,.2f}\n"
        response += f"🕐 Hourly Rate: Rs. {hourly_rate:,.2f}\n"
        response += f"💰 Monthly Basic: Rs. {basic_salary:,.2f}\n\n"
        
        # Detailed allowances
        allowances = breakdown_data.get('allowances', {})
        if allowances:
            response += "**➕ Allowances Breakdown:**\n"
            total_allowances = 0
            for allowance, amount in allowances.items():
                response += f"   🏠 {allowance.replace('_', ' ').title()}: Rs. {amount:,.2f}\n"
                if allowance == 'house_rent':
                    response += f"      (Standard housing allowance)\n"
                elif allowance == 'transport':
                    response += f"      (Monthly transport reimbursement)\n"
                elif allowance == 'mobile':
                    response += f"      (Communication allowance)\n"
                elif allowance == 'meal':
                    response += f"      (Meal subsidy)\n"
                total_allowances += amount
            response += f"   **📊 Total Allowances**: Rs. {total_allowances:,.2f}\n\n"
        
        # Gross salary
        gross_salary = breakdown_data.get('gross_salary', 0)
        response += f"**💰 Gross Salary**: Rs. {gross_salary:,.2f}\n"
        response += f"   (Basic + Allowances = {basic_salary:,.2f} + {total_allowances:,.2f})\n\n"
        
        # Detailed deductions
        deductions = breakdown_data.get('deductions', {})
        if deductions:
            response += "**➖ Deductions Breakdown:**\n"
            total_deductions = 0
            
            for deduction, amount in deductions.items():
                if deduction == 'income_tax':
                    tax_rate = (amount / gross_salary) * 100 if gross_salary > 0 else 0
                    response += f"   🏛️ Income Tax: Rs. {amount:,.2f} ({tax_rate:.1f}%)\n"
                    response += f"      (Calculated on gross salary)\n"
                    
                elif deduction == 'epf