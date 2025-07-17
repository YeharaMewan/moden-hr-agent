# backend/app.py - Final Fixed Version
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import traceback
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app FIRST
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'hr-ai-secret-key-2024')

# Enable CORS
CORS(app, 
     origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True
)

# Initialize global variables
db_connection = None
memory_manager = None
router_agent = None
leave_agent = None
ats_agent = None
payroll_agent = None
workflow_manager = None

# Simple health check endpoint FIRST
@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'service': 'HR AI Backend'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Database connection with proper error handling
def initialize_database():
    """Initialize database connection"""
    global db_connection
    
    try:
        print("🔌 Initializing database connection...")
        from config import get_database_connection
        db_connection = get_database_connection()
        
        if db_connection is not None:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        db_connection = None
        return False

# Memory systems initialization
def initialize_memory():
    """Initialize memory systems"""
    global memory_manager
    
    try:
        if db_connection is None:
            print("⚠️ Skipping memory initialization - no database connection")
            return False
            
        print("🧠 Initializing memory systems...")
        from memory.short_term_memory import ShortTermMemory
        from memory.long_term_memory import LongTermMemory
        
        short_term_memory = ShortTermMemory(db_connection)
        long_term_memory = LongTermMemory(db_connection)
        
        # Create memory manager
        class MemoryManager:
            def __init__(self, short_term, long_term):
                self.short_term = short_term
                self.long_term = long_term
            
            def get_system_statistics(self):
                try:
                    return {
                        'short_term_memory': {
                            'total_contexts': getattr(self.short_term, 'get_total_contexts', lambda: 0)(),
                            'active_sessions': getattr(self.short_term, 'get_active_sessions', lambda: 0)()
                        },
                        'long_term_memory': {
                            'total_memories': getattr(self.long_term, 'get_total_memories', lambda: 0)(),
                            'learned_patterns': getattr(self.long_term, 'get_pattern_count', lambda: 0)()
                        }
                    }
                except Exception as e:
                    return {'error': f'Memory stats unavailable: {str(e)}'}
        
        memory_manager = MemoryManager(short_term_memory, long_term_memory)
        print("✅ Memory systems initialized!")
        return True
        
    except Exception as e:
        print(f"⚠️ Memory system warning: {e}")
        memory_manager = None
        return False

# Agents initialization
def initialize_agents():
    """Initialize AI agents"""
    global router_agent, leave_agent, ats_agent, payroll_agent
    
    try:
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not gemini_api_key:
            print("⚠️ Warning: GEMINI_API_KEY not found - AI features will be limited")
            return False
            
        if db_connection is None:
            print("⚠️ Warning: No database connection - AI features will be limited")
            return False
            
        print("🤖 Initializing agents...")
        
        from agents.router_agent import RouterAgent
        from agents.leave_agent import LeaveAgent
        from agents.ats_agent import ATSAgent
        from agents.payroll_agent import PayrollAgent
        
        router_agent = RouterAgent(gemini_api_key, db_connection, memory_manager)
        leave_agent = LeaveAgent(gemini_api_key, db_connection, memory_manager)
        ats_agent = ATSAgent(gemini_api_key, db_connection, memory_manager)
        payroll_agent = PayrollAgent(gemini_api_key, db_connection, memory_manager)
        
        print("✅ Agents initialized!")
        return True
        
    except Exception as e:
        print(f"⚠️ Agents initialization warning: {e}")
        router_agent = None
        leave_agent = None
        ats_agent = None
        payroll_agent = None
        return False

# Workflow manager initialization
def initialize_workflow():
    """Initialize workflow manager"""
    global workflow_manager
    
    try:
        if not all([router_agent, leave_agent, ats_agent, payroll_agent]):
            print("⚠️ Warning: Not all agents available - workflow features will be limited")
            return False
            
        print("🔄 Initializing LangGraph workflow...")
        from agents.langgraph_router import LangGraphWorkflowManager
        
        workflow_manager = LangGraphWorkflowManager(
            router_agent=router_agent,
            leave_agent=leave_agent,
            ats_agent=ats_agent,
            payroll_agent=payroll_agent
        )
        print("✅ Workflow manager initialized!")
        return True
        
    except Exception as e:
        print(f"⚠️ Workflow manager warning: {e}")
        workflow_manager = None
        return False

# Routes registration
def register_routes():
    """Register application routes"""
    try:
        from routes.auth import auth_bp
        from routes.chat import chat_bp
        
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(chat_bp, url_prefix='/api/chat')
        
        print("✅ Routes registered!")
        return True
        
    except Exception as e:
        print(f"⚠️ Routes registration warning: {e}")
        return False

# Enhanced health check
@app.route('/api/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with component status"""
    try:
        components = {
            'database': 'healthy' if db_connection else 'unavailable',
            'memory_manager': 'healthy' if memory_manager else 'unavailable',
            'agents': 'healthy' if router_agent else 'unavailable',
            'workflow_manager': 'healthy' if workflow_manager else 'unavailable'
        }
        
        overall_status = 'healthy' if all(status == 'healthy' for status in components.values()) else 'degraded'
        
        return jsonify({
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'components': components,
            'message': 'System operational with available components'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# System statistics endpoint
@app.route('/api/system/stats', methods=['GET'])
def system_stats():
    """Get system statistics"""
    try:
        stats = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'version': '2.0.0',
                'workflow_engine': 'LangGraph' if workflow_manager else 'Unavailable',
                'ai_model': 'Gemini Pro' if router_agent else 'Unavailable'
            },
            'memory_stats': memory_manager.get_system_statistics() if memory_manager else {'status': 'unavailable'},
            'component_status': {
                'database': bool(db_connection),
                'memory': bool(memory_manager),
                'agents': bool(router_agent),
                'workflow': bool(workflow_manager)
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist.',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred.',
        'timestamp': datetime.now().isoformat()
    }), 500

# System initialization
def initialize_system():
    """Initialize all system components"""
    print("🚀 Initializing Enhanced HR AI System...")
    print("=" * 60)
    
    # Initialize components step by step
    components_status = {
        'database': initialize_database(),
        'memory': initialize_memory(),
        'agents': initialize_agents(),
        'workflow': initialize_workflow(),
        'routes': register_routes()
    }
    
    # Make components available to routes
    app.db_connection = db_connection
    app.memory_manager = memory_manager
    app.router_agent = router_agent
    app.leave_agent = leave_agent
    app.ats_agent = ats_agent
    app.payroll_agent = payroll_agent
    app.workflow_manager = workflow_manager
    
    print("=" * 60)
    print("✨ Component Status:")
    for component, status in components_status.items():
        print(f"  • {component.title()}: {'✅' if status else '❌'}")
    
    print("=" * 60)
    print("🔗 Available API Endpoints:")
    print("  • /api/health - Simple health check")
    print("  • /api/health/detailed - Detailed component status")
    print("  • /api/system/stats - System statistics")
    print("  • /api/auth/login - User authentication")
    if workflow_manager:
        print("  • /api/chat/message - AI chat interface")
    print("=" * 60)
    
    # Check if core functionality is available
    core_available = components_status['database'] and components_status['routes']
    
    if core_available:
        print("🎉 Core system initialized successfully!")
        if not all(components_status.values()):
            print("⚠️ Some AI features may be limited due to component issues")
    else:
        print("❌ Core system initialization failed!")
        print("💡 Check database connection and routes configuration")
    
    return core_available

if __name__ == '__main__':
    # Initialize system
    system_ready = initialize_system()
    
    if system_ready:
        print("\n🌟 Starting Flask application...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("\n💥 System initialization failed - cannot start application")
        print("🔧 Please check the error messages above and fix the issues")
        exit(1)