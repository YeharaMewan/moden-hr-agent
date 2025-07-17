# backend/debug_auth.py
"""
Debug script to check database connection and user data
"""
from pymongo import MongoClient
from models.user import User
import os
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

def debug_database():
    """Debug database connection and user data"""
    try:
        print("🔍 Starting Database Debug...")
        print("=" * 50)
        
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        db_name = os.getenv('DATABASE_NAME', 'hr_ai_system')
        
        print(f"📡 MongoDB URI: {mongo_uri}")
        print(f"📋 Database Name: {db_name}")
        
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # Check users collection
        user_model = User(db)
        users_collection = db.get_collection('users')
        
        # Count total users
        total_users = users_collection.count_documents({})
        print(f"👥 Total users in database: {total_users}")
        
        if total_users == 0:
            print("❌ No users found in database!")
            print("💡 Run 'python init_db.py' to create sample users")
            return
        
        # List all users
        print("\n📋 Users in database:")
        users = list(users_collection.find({}, {'password': 0}))
        for user in users:
            print(f"   👤 {user['username']} ({user['role']}) - {user.get('full_name', 'No name')}")
        
        # Test login for admin user
        print("\n🔐 Testing login for admin user...")
        admin_user = user_model.verify_password('admin', 'admin123')
        
        if admin_user:
            print("✅ Admin login test successful!")
            print(f"   User ID: {admin_user['_id']}")
            print(f"   Role: {admin_user['role']}")
        else:
            print("❌ Admin login test failed!")
            
            # Check if admin user exists
            admin_raw = users_collection.find_one({'username': 'admin'})
            if admin_raw:
                print("   ℹ️ Admin user exists but password verification failed")
                print("   🔍 Checking password hash...")
                
                # Test password hash manually
                stored_password = admin_raw.get('password')
                if stored_password:
                    is_valid = bcrypt.checkpw('admin123'.encode('utf-8'), stored_password)
                    print(f"   🔐 Password hash validation: {'✅ PASS' if is_valid else '❌ FAIL'}")
                else:
                    print("   ❌ No password hash found")
            else:
                print("   ❌ Admin user does not exist")
        
        # Test with other sample users
        test_users = [
            ('hr.manager', 'hr123'),
            ('john.doe', 'user123')
        ]
        
        print("\n🧪 Testing other sample users...")
        for username, password in test_users:
            user = user_model.verify_password(username, password)
            status = "✅ PASS" if user else "❌ FAIL"
            print(f"   {username}: {status}")
        
        print("\n" + "=" * 50)
        print("🎯 Debug Summary:")
        
        if total_users == 0:
            print("❌ PROBLEM: No users in database")
            print("💡 SOLUTION: Run 'python init_db.py'")
        elif not admin_user:
            print("❌ PROBLEM: Admin user login failed")
            print("💡 SOLUTION: Recreate admin user or check password hashing")
        else:
            print("✅ Database looks good!")
            print("💡 If login still fails, check frontend API configuration")
        
    except Exception as e:
        print(f"💥 Debug failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check MongoDB is running")
        print("   2. Verify MONGODB_URI in .env file")
        print("   3. Check network connectivity")

if __name__ == '__main__':
    debug_database()