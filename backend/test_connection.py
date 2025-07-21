# backend/test_connection.py
"""
Test network connection between frontend and backend
"""
import requests
import json
from datetime import datetime

def test_backend_connection():
    """Test backend API endpoints"""
    
    print("🔗 Testing Backend API Connection...")
    print("=" * 50)
    
    base_url = "https://moden-hr-agent.onrender.com/api"
    
    # Test 1: Health check
    try:
        print("🏥 Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Health check successful!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - Backend not running on port 5000")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Login endpoint (OPTIONS request)
    try:
        print("\n🔐 Testing login OPTIONS request...")
        response = requests.options(f"{base_url}/auth/login", timeout=5)
        
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers: {dict(response.headers)}")
        
    except Exception as e:
        print(f"❌ OPTIONS request error: {e}")
    
    # Test 3: Actual login test
    try:
        print("\n👤 Testing actual login...")
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = requests.post(
            f"{base_url}/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            data = response.json()
            print(f"   Token received: {'Yes' if 'token' in data else 'No'}")
            print(f"   User data: {data.get('user', {}).get('username', 'N/A')}")
            
            return True
        else:
            print(f"❌ Login failed!")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login test error: {e}")
        return False

def test_frontend_config():
    """Test frontend environment configuration"""
    
    print("\n🖥️ Frontend Configuration Check...")
    print("=" * 50)
    
    # Check if frontend .env.local exists
    import os
    
    frontend_env_path = "../frontend/.env.local"
    
    if os.path.exists(frontend_env_path):
        print("✅ Frontend .env.local file exists")
        
        with open(frontend_env_path, 'r') as f:
            content = f.read()
            print(f"📋 Contents:\n{content}")
            
        if "https://moden-hr-agent.onrender.com/api" in content:
            print("✅ API URL configuration looks correct")
        else:
            print("❌ API URL might be incorrect")
            
    else:
        print("❌ Frontend .env.local file missing!")
        print("💡 Create the file with:")
        print("   NEXT_PUBLIC_API_URL=https://moden-hr-agent.onrender.com/api")

if __name__ == '__main__':
    print("🧪 Starting Connection Tests...")
    print("=" * 60)
    
    # Test backend
    backend_ok = test_backend_connection()
    
    # Test frontend config
    test_frontend_config()
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    
    if backend_ok:
        print("✅ Backend is working correctly")
        print("💡 If frontend still can't connect:")
        print("   1. Check frontend .env.local file")
        print("   2. Restart frontend server (npm run dev)")
        print("   3. Clear browser cache/cookies")
        print("   4. Check browser console for errors")
    else:
        print("❌ Backend connection issues found")
        print("💡 Fix backend issues first, then test frontend")
    
    print(f"\n⏰ Test completed at: {datetime.now()}")