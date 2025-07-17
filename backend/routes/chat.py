# backend/routes/chat.py - Fixed Version
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
    Enhanced chat endpoint using LangGraph workflow - FIXED VERSION
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
        
        # Debug: Print current_user to see structure
        print(f"🔍 Debug current_user: {current_user}")
        
        # Fixed: Handle both '_id' and 'user_id' cases
        user_id = None
        if '_id' in current_user:
            user_id = str(current_user['_id'])
        elif 'user_id' in current_user:
            user_id = str(current_user['user_id'])
        else:
            print(f"❌ No user ID found in current_user: {current_user}")
            return jsonify({
                'success': False,
                'error': 'User identification error'
            }), 400
        
        # Prepare user context with fixed user_id
        user_context = {
            'user_id': user_id,
            'username': current_user.get('username', 'User'),
            'full_name': current_user.get('full_name', current_user.get('username', 'User')),
            'role': current_user.get('role', 'user'),
            'department': current_user.get('department', 'General'),
            'email': current_user.get('email', ''),
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ Processing message for user: {user_id} ({user_context['username']})")
        print(f"📝 Message: {message}")
        
        # Check if workflow manager is available
        if not current_app.workflow_manager:
            print("⚠️ Workflow manager not available, using fallback response")
            return jsonify({
                'success': True,
                'response': "I'm currently initializing. Please try again in a moment.",
                'agent': 'system',
                'confidence': 0.5,
                'requires_action': False,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }), 200
        
       # Prepare config for LangGraph to manage state per session
        config = {"configurable": {"session_id": session_id}}
        
        # Process message through LangGraph workflow with session config
        print("🔄 Processing through workflow...")
        workflow_result = current_app.workflow_manager.process_message(
            message=message,
            user_context=user_context,
            config=config  # Pass the config object here
        )
        
        print(f"🎯 Workflow result: {workflow_result}")
        
       # Extract workflow state and response from the correct key
        workflow_state = workflow_result.get('workflow_state', {}) # <-- 'state' වෙනුවට 'workflow_state' භාවිතා කරන්න
        if not workflow_state: # Fallback for direct responses
            return jsonify(workflow_result), 200

        agent_response = workflow_state.get('agent_response', {})

        # Determine response details
        response_text = agent_response.get('response', 'I apologize, but I encountered an issue processing your request.')
        agent_used = workflow_state.get('current_agent', 'router')
        confidence = workflow_state.get('confidence', 0.0)
        requires_action = workflow_state.get('requires_action', False)
        
        # Prepare final response
        response_data = {
            'success': True,
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
            'user_id': 'unknown',
            'message': data.get('message', 'N/A')[:100] if 'data' in locals() else 'N/A'
        }
        
        # Try to get user_id for logging
        try:
            if current_user:
                if '_id' in current_user:
                    error_details['user_id'] = str(current_user['_id'])
                elif 'user_id' in current_user:
                    error_details['user_id'] = str(current_user['user_id'])
        except:
            pass
        
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
    Get conversation context for the user - FIXED VERSION
    """
    try:
        # Fixed: Handle both '_id' and 'user_id' cases
        user_id = None
        if '_id' in current_user:
            user_id = str(current_user['_id'])
        elif 'user_id' in current_user:
            user_id = str(current_user['user_id'])
        else:
            return jsonify({
                'success': False,
                'error': 'User identification error'
            }), 400
        
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent conversation context
        recent_context = []
        user_patterns = {}
        
        if current_app.memory_manager:
            try:
                recent_context = current_app.memory_manager.short_term.get_recent_context(
                    user_id=user_id,
                    limit=limit
                )
                user_patterns = current_app.memory_manager.long_term.get_user_patterns(user_id)
            except AttributeError:
                print("⚠️ Memory manager methods not fully available")
        
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
    Get chat history for the user - FIXED VERSION
    """
    try:
        # Fixed: Handle both '_id' and 'user_id' cases
        user_id = None
        if '_id' in current_user:
            user_id = str(current_user['_id'])
        elif 'user_id' in current_user:
            user_id = str(current_user['user_id'])
        else:
            return jsonify({
                'success': False,
                'error': 'User identification error'
            }), 400
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get chat history from memory
        history = []
        
        if current_app.memory_manager:
            try:
                history = current_app.memory_manager.short_term.get_user_history(
                    user_id=user_id,
                    limit=limit,
                    offset=offset
                )
            except AttributeError:
                print("⚠️ Memory manager history method not available")
        
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
    Clear chat history for the user - FIXED VERSION
    """
    try:
        # Fixed: Handle both '_id' and 'user_id' cases
        user_id = None
        if '_id' in current_user:
            user_id = str(current_user['_id'])
        elif 'user_id' in current_user:
            user_id = str(current_user['user_id'])
        else:
            return jsonify({
                'success': False,
                'error': 'User identification error'
            }), 400
        
        # Clear short-term memory for the user
        if current_app.memory_manager:
            try:
                current_app.memory_manager.short_term.clear_user_context(user_id)
            except AttributeError:
                print("⚠️ Memory manager clear method not available")
        
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

# Health check for chat service
@chat_bp.route('/health', methods=['GET'])
def chat_health():
    """Chat service health check"""
    try:
        components = {
            'workflow_manager': bool(current_app.workflow_manager),
            'memory_manager': bool(current_app.memory_manager),
            'agents': bool(current_app.router_agent)
        }
        
        status = 'healthy' if all(components.values()) else 'degraded'
        
        return jsonify({
            'status': status,
            'components': components,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500