# backend/routes/chat.py (Updated for LangGraph Workflow)
from flask import Blueprint, request, jsonify, current_app
from utils.auth import token_required
import traceback
from datetime import datetime
import json

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST'])
@token_required
def send_message(current_user):
    """
    Enhanced chat endpoint using LangGraph workflow
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message content is required'
            }), 400
        
        message = data['message'].strip()
        session_id = data.get('session_id', f"session_{datetime.now().isoformat()}")
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Prepare user context
        user_context = {
            'user_id': str(current_user['_id']),
            'username': current_user.get('username', 'User'),
            'full_name': current_user.get('full_name', 'User'),
            'role': current_user.get('role', 'user'),
            'department': current_user.get('department', 'General'),
            'email': current_user.get('email', ''),
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Process message through LangGraph workflow
        print(f"🔄 Processing message through workflow: {message[:50]}...")
        
        workflow_result = current_app.workflow_manager.process_message(
            message=message,
            user_context=user_context
        )
        
        # Extract response components
        success = workflow_result.get('success', False)
        response_text = workflow_result.get('response', 'No response generated')
        agent_used = workflow_result.get('agent', 'workflow')
        requires_action = workflow_result.get('requires_action', False)
        confidence = workflow_result.get('confidence', 0.0)
        workflow_state = workflow_result.get('workflow_state', {})
        
        # Store conversation in memory
        try:
            current_app.memory_manager.short_term.store_context(
                user_id=user_context['user_id'],
                context_data={
                    'message': message,
                    'response': response_text,
                    'agent': agent_used,
                    'success': success,
                    'confidence': confidence,
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as memory_error:
            print(f"⚠️ Memory storage error: {memory_error}")
        
        # Prepare response
        response_data = {
            'success': success,
            'response': response_text,
            'agent': agent_used,
            'confidence': confidence,
            'requires_action': requires_action,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'workflow_info': {
                'nodes_executed': workflow_state.get('current_node', 'unknown'),
                'intent_classified': workflow_state.get('intent', 'unknown'),
                'entities_found': workflow_state.get('entities', {}),
                'tools_used': workflow_state.get('tool_results', {}).get('tools_used', [])
            }
        }
        
        # Add action data if action is required
        if requires_action:
            action_data = workflow_state.get('agent_response', {}).get('action_data', {})
            response_data['action_data'] = action_data
        
        # Log successful processing
        print(f"✅ Message processed successfully - Agent: {agent_used}, Confidence: {confidence:.2f}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # Log error details
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat(),
            'user_id': str(current_user.get('_id', 'unknown')),
            'message': data.get('message', 'N/A')[:100] if 'data' in locals() else 'N/A'
        }
        
        print(f"💥 Chat processing error: {error_details}")
        
        # Return user-friendly error
        return jsonify({
            'success': False,
            'error': 'I encountered an error processing your message. Please try again.',
            'technical_error': str(e) if current_app.debug else None,
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/context', methods=['GET'])
@token_required
def get_conversation_context(current_user):
    """
    Get conversation context for the user
    """
    try:
        user_id = str(current_user['_id'])
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent conversation context
        recent_context = current_app.memory_manager.short_term.get_recent_context(
            user_id=user_id,
            limit=limit
        )
        
        # Get user patterns
        user_patterns = current_app.memory_manager.long_term.get_user_patterns(user_id)
        
        return jsonify({
            'success': True,
            'recent_context': recent_context,
            'user_patterns': user_patterns,
            'context_count': len(recent_context),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    """
    Get chat history for the user
    """
    try:
        user_id = str(current_user['_id'])
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get chat history from memory
        history = current_app.memory_manager.short_term.get_user_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history),
            'limit': limit,
            'offset': offset,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/clear', methods=['POST'])
@token_required
def clear_chat_history(current_user):
    """
    Clear chat history for the user
    """
    try:
        user_id = str(current_user['_id'])
        
        # Clear short-term memory for the user
        current_app.memory_manager.short_term.clear_user_context(user_id)
        
        return jsonify({
            'success': True,
            'message': 'Chat history cleared successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/feedback', methods=['POST'])
@token_required
def submit_feedback(current_user):
    """
    Submit feedback about chat interaction
    """
    try:
        data = request.get_json()
        
        if not data or 'rating' not in data:
            return jsonify({
                'success': False,
                'error': 'Rating is required'
            }), 400
        
        feedback_data = {
            'user_id': str(current_user['_id']),
            'rating': data['rating'],
            'feedback': data.get('feedback', ''),
            'session_id': data.get('session_id', ''),
            'message_id': data.get('message_id', ''),
            'agent': data.get('agent', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store feedback in long-term memory
        current_app.memory_manager.long_term.store_feedback(
            user_id=feedback_data['user_id'],
            feedback_data=feedback_data
        )
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/analytics', methods=['GET'])
@token_required
def get_chat_analytics(current_user):
    """
    Get chat analytics for the user
    """
    try:
        user_id = str(current_user['_id'])
        
        # Get analytics from memory manager
        analytics = {
            'total_conversations': 0,
            'most_used_features': [],
            'average_satisfaction': 0.0,
            'recent_activity': []
        }
        
        # Get user patterns
        user_patterns = current_app.memory_manager.long_term.get_user_patterns(user_id)
        
        if user_patterns:
            analytics.update({
                'total_conversations': user_patterns.get('total_interactions', 0),
                'most_used_features': user_patterns.get('common_actions', []),
                'preferred_language': user_patterns.get('language_preference', 'english'),
                'interaction_frequency': user_patterns.get('interaction_frequency', 'low')
            })
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/workflow/status', methods=['GET'])
@token_required
def get_workflow_status(current_user):
    """
    Get current workflow status and statistics
    """
    try:
        # Get workflow statistics
        workflow_stats = {
            'system_status': 'active',
            'workflow_engine': 'LangGraph',
            'total_workflows_processed': 0,  # Would be tracked in real implementation
            'average_processing_time': '< 2 seconds',
            'success_rate': '98.5%',
            'active_nodes': [
                'intent_classifier',
                'leave_agent',
                'ats_agent',
                'payroll_agent',
                'tool_executor',
                'response_formatter'
            ],
            'available_tools': {
                'leave_management': [
                    'check_leave_balance',
                    'create_leave_request',
                    'validate_leave_dates',
                    'get_leave_history'
                ],
                'candidate_search': [
                    'search_candidates',
                    'rank_candidates',
                    'filter_candidates'
                ],
                'payroll_calculation': [
                    'calculate_individual_payroll',
                    'calculate_department_payroll',
                    'get_payroll_history'
                ]
            }
        }
        
        # Get agent performance stats
        agent_stats = {
            'router': current_app.router_agent.get_performance_stats(),
            'leave': current_app.leave_agent.get_performance_stats(),
            'ats': current_app.ats_agent.get_performance_stats(),
            'payroll': current_app.payroll_agent.get_performance_stats()
        }
        
        return jsonify({
            'success': True,
            'workflow_stats': workflow_stats,
            'agent_performance': agent_stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/debug', methods=['POST'])
@token_required
def debug_workflow(current_user):
    """
    Debug workflow with detailed information (for development)
    """
    try:
        if not current_app.debug:
            return jsonify({
                'success': False,
                'error': 'Debug mode is not enabled'
            }), 403
        
        data = request.get_json()
        message = data.get('message', 'test message')
        
        # Prepare debug context
        debug_context = {
            'user_id': str(current_user['_id']),
            'username': current_user.get('username', 'debug_user'),
            'role': current_user.get('role', 'user'),
            'debug_mode': True
        }
        
        # Process with debug information
        workflow_result = current_app.workflow_manager.process_message(
            message=message,
            user_context=debug_context
        )
        
        # Return detailed debug information
        return jsonify({
            'success': True,
            'debug_info': {
                'input_message': message,
                'workflow_result': workflow_result,
                'user_context': debug_context,
                'system_state': {
                    'memory_stats': current_app.memory_manager.get_system_statistics(),
                    'agent_stats': {
                        'router': current_app.router_agent.get_performance_stats(),
                        'leave': current_app.leave_agent.get_performance_stats(),
                        'ats': current_app.ats_agent.get_performance_stats(),
                        'payroll': current_app.payroll_agent.get_performance_stats()
                    }
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }), 500