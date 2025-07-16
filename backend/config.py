# backend/config.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'hr_ai_system')
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'hr-ai-secret-key-2024')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # JWT configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-2024')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    
    # Memory configuration
    SHORT_TERM_MEMORY_EXPIRY = 3600  # 1 hour
    LONG_TERM_MEMORY_EXPIRY = 2592000  # 30 days
    
    # Performance configuration
    CACHE_SIZE = 1000
    MAX_RESPONSE_LENGTH = 2000

# Global database connection
_db_connection = None

def get_database_connection():
    """
    Get database connection (singleton pattern)
    """
    global _db_connection
    
    if _db_connection is None:
        try:
            print("🔌 Connecting to MongoDB...")
            
            # Create MongoDB client
            client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,         # 10 second timeout
                socketTimeoutMS=20000           # 20 second timeout
            )
            
            # Test connection
            client.admin.command('ping')
            print("✅ MongoDB connection successful!")
            
            # Get database
            _db_connection = client[Config.DATABASE_NAME]
            
            # Create indexes for performance
            _create_database_indexes(_db_connection)
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("🔧 Please check:")
            print("   1. MongoDB is running")
            print("   2. MONGO_URI in .env file is correct")
            print("   3. Network connectivity")
            raise
    
    return _db_connection

def _create_database_indexes(db):
    """Create database indexes for performance"""
    try:
        print("📊 Creating database indexes...")
        
        # User collection indexes
        db.users.create_index([('username', 1)], unique=True)
        db.users.create_index([('email', 1)], unique=True)
        db.users.create_index([('role', 1)])
        
        # Leave collection indexes
        db.leaves.create_index([('user_id', 1)])
        db.leaves.create_index([('status', 1)])
        db.leaves.create_index([('start_date', 1)])
        db.leaves.create_index([('created_at', -1)])
        
        # Candidate collection indexes
        db.candidates.create_index([('name', 1)])
        db.candidates.create_index([('skills', 1)])
        db.candidates.create_index([('experience_years', 1)])
        db.candidates.create_index([('created_at', -1)])
        
        # Payroll collection indexes
        db.payroll.create_index([('user_id', 1)])
        db.payroll.create_index([('department', 1)])
        db.payroll.create_index([('pay_period', 1)])
        db.payroll.create_index([('created_at', -1)])
        
        # Memory collection indexes
        db.short_term_memory.create_index([('user_id', 1)])
        db.short_term_memory.create_index([('session_id', 1)])
        db.short_term_memory.create_index([('expires_at', 1)], expireAfterSeconds=0)
        
        db.long_term_memory.create_index([('user_id', 1)])
        db.long_term_memory.create_index([('memory_type', 1)])
        db.long_term_memory.create_index([('created_at', -1)])
        
        print("✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"⚠️ Index creation warning: {e}")

def get_config():
    """Get application configuration"""
    return Config

def validate_configuration():
    """Validate required configuration"""
    required_env_vars = ['GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        return False
    
    return True

# Initialize configuration validation
if not validate_configuration():
    print("💡 Create a .env file with required variables:")
    print("GEMINI_API_KEY=your_gemini_api_key_here")
    print("MONGO_URI=mongodb://localhost:27017/")
    print("DATABASE_NAME=hr_ai_system")