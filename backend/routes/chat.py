# backend/routes/chat.py
from flask import Blueprint, request, jsonify, current_app
from utils.auth import token_required
from datetime import datetime
import uuid
import json

chat_bp = Blueprint('chat', __name__)

def get_agents():
    """Get agent instances from app context"""
    try:
        return {
            'router': current_app.router_agent,
            'leave': current_app.leave_agent,
            'ats': current_app.ats_agent,
            'payroll': current_app.payroll_agent,
            'db': current_app.db_connection
        }
    except AttributeError as e:
        raise Exception(f"Agents not properly initialized: {str(e)}")

@chat_bp.route('/chat/message', methods=['POST'])
@token_required
def chat_message(current_user):
    """Enhanced chat endpoint with proper agent integration"""
    try:
        data = request.get_json()
        
        # Validate request data
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        if 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Enhanced user context
        user_context = {
            'user_id': current_user['user_id'],
            'username': current_user['username'],
            'role': current_user['role'],
            'session_id': session_id
        }
        
        # Get agent instances
        agents = get_agents()
        router_agent = agents['router']
        leave_agent = agents['leave']
        ats_agent = agents['ats']
        payroll_agent = agents['payroll']
        db_connection = agents['db']
        
        # Process message through router
        print(f"🔄 Processing message from {current_user['username']}: {user_message}")
        routing_result = router_agent.process_message(user_message, user_context, session_id)
        
        # Initialize default result
        result = {
            'success': False,
            'response': 'Sorry, I encountered an error processing your request.',
            'requires_action': False
        }
        
        if routing_result.get('requires_processing'):
            # Route to specific agent
            agent_name = routing_result['agent']
            print(f"📡 Routing to agent: {agent_name}")
            
            try:
                if agent_name == 'leave_agent':
                    result = leave_agent.process_request(routing_result)
                elif agent_name == 'ats_agent':
                    result = ats_agent.process_request(routing_result)
                elif agent_name == 'payroll_agent':
                    result = payroll_agent.process_request(routing_result)
                else:
                    result = {
                        'success': False, 
                        'error': f'Unknown agent: {agent_name}',
                        'response': 'Sorry, I cannot process this type of request at the moment.'
                    }
            except Exception as agent_error:
                print(f"❌ Agent {agent_name} error: {str(agent_error)}")
                result = {
                    'success': False,
                    'error': str(agent_error),
                    'response': f'Sorry, I encountered an error while processing your {agent_name.replace("_agent", "")} request.'
                }
        else:
            # Direct router response
            result = {
                'success': True,
                'response': routing_result.get('response', 'Hello! How can I help you today?'),
                'requires_action': False
            }
        
        # Store conversation in database
        try:
            conversations_collection = db_connection.get_collection('conversations')
            
            conversation_data = {
                'user_id': current_user['user_id'],
                'username': current_user['username'],
                'user_role': current_user['role'],
                'session_id': session_id,
                'message': user_message,
                'response': result.get('response', ''),
                'agent': routing_result.get('agent', 'router'),
                'intent': routing_result.get('intent', 'unknown'),
                'confidence': routing_result.get('confidence', 0.0),
                'success': result.get('success', False),
                'timestamp': datetime.now(),
                'processing_time': datetime.now()  # Could be calculated properly
            }
            
            conversations_collection.insert_one(conversation_data)
            print(f"💾 Conversation stored for user {current_user['username']}")
            
        except Exception as db_error:
            print(f"⚠️ Failed to store conversation: {str(db_error)}")
            # Don't fail the entire request if conversation storage fails
        
        # Prepare response
        response_data = {
            'response': result.get('response', 'Sorry, I encountered an error.'),
            'success': result.get('success', False),
            'requires_action': result.get('requires_action', False),
            'session_id': session_id,
            'agent': routing_result.get('agent', 'router'),
            'intent': routing_result.get('intent', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add action data if present
        if result.get('action_data'):
            response_data['action_data'] = result['action_data']
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Chat endpoint error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'success': False,
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/chat/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    """Get conversation history for user"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        session_id = request.args.get('session_id')
        
        # Validate pagination
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20
        
        skip = (page - 1) * limit
        
        agents = get_agents()
        db_connection = agents['db']
        conversations_collection = db_connection.get_collection('conversations')
        
        # Build query
        query = {'user_id': current_user['user_id']}
        if session_id:
            query['session_id'] = session_id
        
        # Get user's conversation history
        conversations = list(
            conversations_collection.find(query, {
                'message': 1,
                'response': 1,
                'agent': 1,
                'intent': 1,
                'success': 1,
                'timestamp': 1,
                'session_id': 1
            }).sort('timestamp', -1).skip(skip).limit(limit)
        )
        
        # Convert ObjectId to string and format timestamps
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
            if isinstance(conv.get('timestamp'), datetime):
                conv['timestamp'] = conv['timestamp'].isoformat()
        
        # Get total count for pagination
        total_count = conversations_collection.count_documents(query)
        total_pages = (total_count + limit - 1) // limit
        
        return jsonify({
            'conversations': conversations,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'success': True
        }), 200
        
    except Exception as e:
        print(f"❌ Chat history error: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@chat_bp.route('/chat/sessions', methods=['GET'])
@token_required
def get_chat_sessions(current_user):
    """Get user's chat sessions"""
    try:
        agents = get_agents()
        db_connection = agents['db']
        conversations_collection = db_connection.get_collection('conversations')
        
        # Aggregate sessions
        pipeline = [
            {'$match': {'user_id': current_user['user_id']}},
            {'$group': {
                '_id': '$session_id',
                'message_count': {'$sum': 1},
                'last_message': {'$max': '$timestamp'},
                'first_message': {'$min': '$timestamp'},
                'agents_used': {'$addToSet': '$agent'}
            }},
            {'$sort': {'last_message': -1}},
            {'$limit': 50}  # Limit to last 50 sessions
        ]
        
        sessions = list(conversations_collection.aggregate(pipeline))
        
        # Format sessions
        for session in sessions:
            session['session_id'] = session['_id']
            del session['_id']
            
            if isinstance(session.get('last_message'), datetime):
                session['last_message'] = session['last_message'].isoformat()
            if isinstance(session.get('first_message'), datetime):
                session['first_message'] = session['first_message'].isoformat()
        
        return jsonify({
            'sessions': sessions,
            'success': True
        }), 200
        
    except Exception as e:
        print(f"❌ Chat sessions error: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@chat_bp.route('/chat/clear', methods=['DELETE'])
@token_required
def clear_chat_history(current_user):
    """Clear user's conversation history"""
    try:
        session_id = request.args.get('session_id')
        
        agents = get_agents()
        db_connection = agents['db']
        conversations_collection = db_connection.get_collection('conversations')
        
        # Build delete query
        query = {'user_id': current_user['user_id']}
        if session_id:
            query['session_id'] = session_id
        
        result = conversations_collection.delete_many(query)
        
        message = f'Cleared {result.deleted_count} conversation records'
        if session_id:
            message += f' from session {session_id}'
        
        return jsonify({
            'message': message,
            'deleted_count': result.deleted_count,
            'success': True
        }), 200
        
    except Exception as e:
        print(f"❌ Clear chat error: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@chat_bp.route('/chat/feedback', methods=['POST'])
@token_required
def submit_feedback(current_user):
    """Submit feedback for a conversation"""
    try:
        data = request.get_json()
        
        if not data or 'conversation_id' not in data:
            return jsonify({'error': 'conversation_id is required'}), 400
        
        conversation_id = data['conversation_id']
        rating = data.get('rating')  # 1-5 scale
        feedback_text = data.get('feedback', '').strip()
        helpful = data.get('helpful')  # boolean
        
        agents = get_agents()
        db_connection = agents['db']
        
        # Store feedback
        feedback_collection = db_connection.get_collection('conversation_feedback')
        
        feedback_data = {
            'conversation_id': conversation_id,
            'user_id': current_user['user_id'],
            'rating': rating,
            'feedback_text': feedback_text,
            'helpful': helpful,
            'timestamp': datetime.now()
        }
        
        feedback_collection.insert_one(feedback_data)
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'success': True
        }), 200
        
    except Exception as e:
        print(f"❌ Feedback error: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@chat_bp.route('/chat/status', methods=['GET'])
@token_required
def chat_status(current_user):
    """Get chat system status"""
    try:
        agents = get_agents()
        
        # Test agent availability
        agent_status = {}
        for agent_name in ['router', 'leave', 'ats', 'payroll']:
            try:
                agent = agents[agent_name]
                # Simple test - check if agent has required methods
                if hasattr(agent, 'process_request') or hasattr(agent, 'process_message'):
                    agent_status[agent_name] = 'available'
                else:
                    agent_status[agent_name] = 'limited'
            except:
                agent_status[agent_name] = 'unavailable'
        
        # Test database connection
        try:
            agents['db'].command('ping')
            db_status = 'connected'
        except:
            db_status = 'disconnected'
        
        return jsonify({
            'status': 'operational',
            'agents': agent_status,
            'database': db_status,
            'user_role': current_user['role'],
            'features_available': {
                'leave_management': agent_status.get('leave') == 'available',
                'candidate_search': agent_status.get('ats') == 'available' and current_user['role'] == 'hr',
                'payroll_calculation': agent_status.get('payroll') == 'available',
                'general_chat': agent_status.get('router') == 'available'
            },
            'timestamp': datetime.now().isoformat(),
            'success': True
        }), 200
        
    except Exception as e:
        print(f"❌ Chat status error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'success': False
        }), 500