# backend/config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-super-secret-key-here-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Database Configuration - Fixed to use MONGODB_URI from .env
    MONGO_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'hr_ai_system')
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # File Upload Settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'data/cv_files')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
    
    # Memory Settings
    SHORT_TERM_TTL_HOURS = int(os.getenv('SHORT_TERM_TTL_HOURS', '1'))
    LONG_TERM_TTL_DAYS = int(os.getenv('LONG_TERM_TTL_DAYS', '30'))
    
    # Security Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or SECRET_KEY
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    BCRYPT_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', '12'))
    
    # Application Settings
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Vector Database Settings
    VECTOR_DB_URI = os.getenv('VECTOR_DB_URI') or MONGO_URI
    VECTOR_COLLECTION = os.getenv('VECTOR_COLLECTION', 'vector_embeddings')
    
    # Agent Settings
    AGENT_TIMEOUT = int(os.getenv('AGENT_TIMEOUT', '30'))  # seconds
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    # Logging Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/hr_ai.log')
    
    @staticmethod
    def validate_config():
        """Validate required configuration"""
        required_vars = ['GEMINI_API_KEY']
        missing = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Validate database URI
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not mongo_uri or mongo_uri == 'mongodb://localhost:27017/':
            print("⚠️ Warning: Using default MongoDB URI. Consider setting MONGODB_URI in .env")
        
        return True
    
    @classmethod
    def get_database_config(cls):
        """Get database configuration"""
        return {
            'uri': cls.MONGO_URI,
            'db_name': cls.DB_NAME,
            'vector_collection': cls.VECTOR_COLLECTION
        }
    
    @classmethod
    def get_agent_config(cls):
        """Get agent configuration"""
        return {
            'gemini_api_key': cls.GEMINI_API_KEY,
            'timeout': cls.AGENT_TIMEOUT,
            'max_retries': cls.MAX_RETRIES,
            'short_term_ttl': cls.SHORT_TERM_TTL_HOURS,
            'long_term_ttl': cls.LONG_TERM_TTL_DAYS
        }

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False
    FLASK_ENV = 'development'
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    FLASK_ENV = 'production'
    
    # Stricter settings for production
    LOG_LEVEL = 'WARNING'
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB in production
    
    @staticmethod
    def validate_config():
        """Additional validation for production"""
        Config.validate_config()
        
        # Check for strong secret keys in production
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key or secret_key == 'your-super-secret-key-here-change-in-production':
            raise ValueError("Strong SECRET_KEY required in production")
        
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret or jwt_secret == secret_key:
            raise ValueError("Separate JWT_SECRET_KEY required in production")

class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = True
    TESTING = True
    FLASK_ENV = 'testing'
    
    # Use test database
    DB_NAME = 'hr_ai_system_test'
    
    # Faster settings for testing
    BCRYPT_ROUNDS = 4
    JWT_EXPIRATION_HOURS = 1
    SHORT_TERM_TTL_HOURS = 1
    LONG_TERM_TTL_DAYS = 1

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration by name"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])