# backend/config.py - Final Fixed Version
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database configuration - Fix environment variable names
    MONGO_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
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
_db_client = None

def get_database_connection():
    """
    Get database connection (singleton pattern) with better error handling
    """
    global _db_connection, _db_client
    
    if _db_connection is None:
        try:
            print("🔌 Connecting to MongoDB...")
            print(f"📡 URI: {Config.MONGO_URI[:50]}...")  # Show partial URI for debugging
            
            # Create MongoDB client with better timeout settings
            _db_client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=10000,  # 10 second timeout
                connectTimeoutMS=10000,          # 10 second timeout
                socketTimeoutMS=20000,           # 20 second timeout
                retryWrites=True,
                w='majority'
            )
            
            # Test connection
            print("🧪 Testing database connection...")
            _db_client.admin.command('ping')  # Use _db_client, not _db_connection
            print("✅ MongoDB connection successful!")
            
            # Get database
            _db_connection = _db_client[Config.DATABASE_NAME]
            print(f"📋 Using database: {Config.DATABASE_NAME}")
            
            # Create indexes for performance (with error handling)
            try:
                _create_database_indexes(_db_connection)
            except Exception as e:
                print(f"⚠️ Index creation warning: {e}")
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("🔧 Debug info:")
            print(f"   MONGODB_URI from env: {os.getenv('MONGODB_URI', 'Not set')}")
            print(f"   MONGO_URI (fallback): {os.getenv('MONGO_URI', 'Not set')}")
            print(f"   Database name: {Config.DATABASE_NAME}")
            print("\n💡 Troubleshooting:")
            print("   1. Check .env file exists and contains MONGODB_URI")
            print("   2. Verify MongoDB Atlas connection string")
            print("   3. Check network connectivity")
            print("   4. Verify database credentials")
            
            # Don't exit, return None to allow app to run with limited functionality
            return None
    
    return _db_connection

def _create_database_indexes(db):
    """Create database indexes for performance with error handling"""
    try:
        print("📊 Creating database indexes...")
        
        # User collection indexes
        try:
            db.users.create_index([('username', 1)], unique=True, background=True)
            db.users.create_index([('email', 1)], unique=True, background=True)
            db.users.create_index([('role', 1)], background=True)
            print("✅ User indexes created")
        except Exception as e:
            print(f"⚠️ User index warning: {e}")
        
        # Leave collection indexes
        try:
            db.leaves.create_index([('user_id', 1)], background=True)
            db.leaves.create_index([('status', 1)], background=True)
            db.leaves.create_index([('start_date', 1)], background=True)
            db.leaves.create_index([('created_at', -1)], background=True)
            print("✅ Leave indexes created")
        except Exception as e:
            print(f"⚠️ Leave index warning: {e}")
        
        # Candidate collection indexes
        try:
            db.candidates.create_index([('name', 1)], background=True)
            db.candidates.create_index([('skills', 1)], background=True)
            db.candidates.create_index([('experience_years', 1)], background=True)
            db.candidates.create_index([('created_at', -1)], background=True)
            print("✅ Candidate indexes created")
        except Exception as e:
            print(f"⚠️ Candidate index warning: {e}")
        
        # Payroll collection indexes
        try:
            db.payroll.create_index([('user_id', 1)], background=True)
            db.payroll.create_index([('department', 1)], background=True)
            db.payroll.create_index([('pay_period', 1)], background=True)
            db.payroll.create_index([('created_at', -1)], background=True)
            print("✅ Payroll indexes created")
        except Exception as e:
            print(f"⚠️ Payroll index warning: {e}")
        
        # Memory collection indexes
        try:
            db.short_term_memory.create_index([('user_id', 1)], background=True)
            db.short_term_memory.create_index([('session_id', 1)], background=True)
            db.short_term_memory.create_index([('expires_at', 1)], expireAfterSeconds=0, background=True)
            
            db.long_term_memory.create_index([('user_id', 1)], background=True)
            db.long_term_memory.create_index([('memory_type', 1)], background=True)
            db.long_term_memory.create_index([('created_at', -1)], background=True)
            print("✅ Memory indexes created")
        except Exception as e:
            print(f"⚠️ Memory index warning: {e}")
        
        print("✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"⚠️ General index creation warning: {e}")

def test_database_connection():
    """Test database connection and return status"""
    try:
        db = get_database_connection()
        if db is None:
            return False, "Database connection is None"
        
        # Test basic operations using the client
        if _db_client:
            _db_client.admin.command('ping')  # Use client instead of db.admin
        else:
            return False, "Database client is None"
        
        # Test collections access
        collections = db.list_collection_names()
        
        return True, f"Connection successful. Collections: {len(collections)}"
        
    except Exception as e:
        return False, str(e)

def get_config():
    """Get application configuration"""
    return Config

def validate_configuration():
    """Validate required configuration - simplified version"""
    issues = []
    
    # Check required environment variables
    if not Config.GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY is missing")
    
    if not Config.MONGO_URI or Config.MONGO_URI == 'mongodb://localhost:27017/':
        issues.append("MONGODB_URI is not properly configured")
    
    # Don't test database connection here to avoid recursion
    # Just check if MONGO_URI looks valid
    if Config.MONGO_URI and not (Config.MONGO_URI.startswith('mongodb://') or Config.MONGO_URI.startswith('mongodb+srv://')):
        issues.append("MONGO_URI format appears invalid")
    
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   • {issue}")
        return False, issues
    
    print("✅ Configuration validation passed")
    return True, []

# Manual test function
def manual_test():
    """Manual test for configuration"""
    print("🔧 Testing configuration manually...")
    
    # Test basic config
    valid, issues = validate_configuration()
    
    # Test database connection
    db_status, db_message = test_database_connection()
    print(f"📊 Database test: {'✅' if db_status else '❌'} {db_message}")
    
    return valid and db_status

# Initialize configuration validation on import
if __name__ == "__main__":
    manual_test()
else:
    # Silent validation when imported
    try:
        valid, issues = validate_configuration()
        if not valid:
            print("⚠️ Configuration warnings detected - some features may be limited")
    except Exception as e:
        print(f"⚠️ Configuration validation error: {e}")