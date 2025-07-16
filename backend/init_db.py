# backend/init_db.py - Complete version with CV file processing
from pymongo import MongoClient
from models.user import User
from models.candidate import Candidate
from models.leave import Leave
from models.payroll import Payroll
import os
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Import CV processor
from process_cv_files import CVFileProcessor

# Load environment variables
load_dotenv()

def init_database():
    """Initialize database with sample data including CV file processing"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        db_name = os.getenv('DB_NAME', 'hr_ai_system')
        
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        print(f"🔌 Connecting to database: {db_name}")
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Initialize models
        user_model = User(db)
        candidate_model = Candidate(db)
        leave_model = Leave(db)
        payroll_model = Payroll(db)
        
        # Ask user if they want to clear existing data
        clear_data = input("\n🗑️ Do you want to clear existing data? (y/N): ").lower().strip()
        
        if clear_data == 'y' or clear_data == 'yes':
            print("🗑️ Clearing existing data...")
            db.get_collection('users').delete_many({})
            db.get_collection('candidates').delete_many({})
            db.get_collection('leaves').delete_many({})
            db.get_collection('payroll').delete_many({})
            db.get_collection('conversations').delete_many({})
            print("✅ Existing data cleared")
        else:
            print("📝 Keeping existing data, will skip duplicates")
        
        # Create sample users
        print("\n👥 Creating sample users...")
        sample_users = create_sample_users(user_model)
        
        # Process CV files instead of creating sample candidates
        print("\n📄 Processing CV files from backend/data/cv_files...")
        cv_processor = CVFileProcessor()
        
        # Create sample CV files if directory is empty
        cv_processor.create_sample_cv_files()
        
        # Process all CV files and create candidates with vectors
        cv_processor.process_all_cv_files()
        
        # Create sample leave requests
        print("\n🏖️ Creating sample leave requests...")
        create_sample_leaves(leave_model, sample_users)
        
        # Create sample payroll records
        print("\n💰 Creating sample payroll records...")
        create_sample_payroll(payroll_model, sample_users)
        
        # Create database indexes
        print("\n📊 Creating database indexes...")
        create_indexes(db)
        
        print("\n✅ Database initialization completed successfully!")
        print_login_details()
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise e

def create_sample_users(user_model):
    """Create sample users with HR and regular user roles"""
    
    # HR Users
    hr_users = [
        {
            'username': 'admin',
            'email': 'admin@company.com',
            'password': 'admin123',
            'role': 'hr',
            'department': 'HR',
            'employee_id': 'HR001',
            'full_name': 'System Administrator',
            'phone': '+94771234567',
            'annual_leave_balance': 21,
            'position': 'HR Director',
            'salary': 300000,
            'join_date': datetime(2020, 1, 15)
        },
        {
            'username': 'hr.manager',
            'email': 'hr.manager@company.com',
            'password': 'hr123',
            'role': 'hr',
            'department': 'HR',
            'employee_id': 'HR002',
            'full_name': 'Priya Perera',
            'phone': '+94771234568',
            'annual_leave_balance': 21,
            'position': 'HR Manager',
            'salary': 180000,
            'join_date': datetime(2021, 3, 10)
        },
        {
            'username': 'hr.exec',
            'email': 'hr.executive@company.com',
            'password': 'hr123',
            'role': 'hr',
            'department': 'HR',
            'employee_id': 'HR003',
            'full_name': 'Sandun Silva',
            'phone': '+94771234569',
            'annual_leave_balance': 18,
            'position': 'HR Executive',
            'salary': 120000,
            'join_date': datetime(2022, 6, 1)
        }
    ]
    
    # Regular Users (Employees)
    regular_users = [
        {
            'username': 'john.doe',
            'email': 'john.doe@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'IT',
            'employee_id': 'IT001',
            'full_name': 'John Doe',
            'phone': '+94771234570',
            'annual_leave_balance': 21,
            'position': 'Senior Software Engineer',
            'salary': 150000,
            'join_date': datetime(2021, 8, 15)
        },
        {
            'username': 'jane.smith',
            'email': 'jane.smith@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'IT',
            'employee_id': 'IT002',
            'full_name': 'Jane Smith',
            'phone': '+94771234571',
            'annual_leave_balance': 19,
            'position': 'Frontend Developer',
            'salary': 120000,
            'join_date': datetime(2022, 1, 10)
        },
        {
            'username': 'mike.wilson',
            'email': 'mike.wilson@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'IT',
            'employee_id': 'IT003',
            'full_name': 'Mike Wilson',
            'phone': '+94771234572',
            'annual_leave_balance': 21,
            'position': 'DevOps Engineer',
            'salary': 140000,
            'join_date': datetime(2021, 11, 5)
        },
        {
            'username': 'sarah.brown',
            'email': 'sarah.brown@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'Finance',
            'employee_id': 'FIN001',
            'full_name': 'Sarah Brown',
            'phone': '+94771234573',
            'annual_leave_balance': 20,
            'position': 'Financial Analyst',
            'salary': 110000,
            'join_date': datetime(2022, 4, 20)
        },
        {
            'username': 'david.lee',
            'email': 'david.lee@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'Marketing',
            'employee_id': 'MKT001',
            'full_name': 'David Lee',
            'phone': '+94771234574',
            'annual_leave_balance': 18,
            'position': 'Marketing Manager',
            'salary': 130000,
            'join_date': datetime(2021, 9, 12)
        },
        {
            'username': 'lisa.garcia',
            'email': 'lisa.garcia@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'IT',
            'employee_id': 'IT004',
            'full_name': 'Lisa Garcia',
            'phone': '+94771234575',
            'annual_leave_balance': 21,
            'position': 'Backend Developer',
            'salary': 125000,
            'join_date': datetime(2022, 2, 28)
        },
        {
            'username': 'kevin.johnson',
            'email': 'kevin.johnson@company.com',
            'password': 'user123',
            'role': 'user',
            'department': 'Finance',
            'employee_id': 'FIN002',
            'full_name': 'Kevin Johnson',
            'phone': '+94771234576',
            'annual_leave_balance': 17,
            'position': 'Accountant',
            'salary': 85000,
            'join_date': datetime(2022, 7, 8)
        }
    ]
    
    all_users = hr_users + regular_users
    created_users = []
    
    for user_data in all_users:
        try:
            # Check if user already exists
            existing_user = user_model.get_user_by_username(user_data['username'])
            if existing_user:
                print(f"  ⚠️ User {user_data['username']} already exists, skipping...")
                created_users.append(existing_user)
                continue
            
            user_id = user_model.create_user(user_data)
            user_data['_id'] = user_id
            created_users.append(user_data)
            print(f"  ✅ Created user: {user_data['username']} ({user_data['role']})")
            
        except Exception as e:
            print(f"  ❌ Failed to create user {user_data['username']}: {e}")
    
    return created_users

def create_sample_leaves(leave_model, users):
    """Create sample leave requests"""
    
    leave_types = ['annual', 'sick', 'casual', 'emergency']
    statuses = ['pending', 'approved', 'rejected']
    
    # Get non-HR users for leave requests
    regular_users = [user for user in users if user.get('role') == 'user']
    
    for i in range(15):  # Create 15 sample leave requests
        user = random.choice(regular_users)
        
        # Random date within last 3 months and next 2 months
        base_date = datetime.now() - timedelta(days=90)
        random_days = random.randint(0, 150)
        start_date = base_date + timedelta(days=random_days)
        
        # Leave duration between 1-5 days
        duration = random.randint(1, 5)
        end_date = start_date + timedelta(days=duration - 1)
        
        leave_data = {
            'user_id': user['_id'],
            'leave_type': random.choice(leave_types),
            'start_date': start_date,
            'end_date': end_date,
            'reason': f'Sample leave request {i+1}',
            'status': random.choice(statuses)
        }
        
        # Add HR comments for rejected leaves
        if leave_data['status'] == 'rejected':
            leave_data['hr_comments'] = 'Insufficient leave balance or conflicting dates'
        
        try:
            leave_id = leave_model.create_leave_request(leave_data)
            print(f"  ✅ Created leave request: {leave_data['leave_type']} for {user['username']}")
        except Exception as e:
            print(f"  ❌ Failed to create leave request: {e}")

def create_sample_payroll(payroll_model, users):
    """Create sample payroll records"""
    
    months = ['January', 'February', 'March', 'April', 'May', 'June']
    current_year = datetime.now().year
    
    for user in users:
        for month in months[:3]:  # Create for first 3 months
            basic_salary = user.get('salary', 100000)
            
            # Calculate allowances
            transport_allowance = 15000
            meal_allowance = 10000
            other_allowances = 5000
            total_allowances = transport_allowance + meal_allowance + other_allowances
            
            # Calculate deductions
            gross_salary = basic_salary + total_allowances
            income_tax = gross_salary * 0.1
            epf_employee = basic_salary * 0.08
            insurance = 2000
            other_deductions = 1000
            total_deductions = income_tax + epf_employee + insurance + other_deductions
            
            # Net salary
            net_salary = gross_salary - total_deductions
            
            payroll_data = {
                'user_id': user['_id'],
                'basic_salary': basic_salary,
                'allowances': total_allowances,
                'deductions': total_deductions,
                'net_salary': net_salary,
                'month': month,
                'year': current_year,
                'department': user.get('department', 'Unknown')
            }
            
            try:
                payroll_id = payroll_model.create_payroll(payroll_data)
                print(f"  ✅ Created payroll: {month} {current_year} for {user['username']}")
            except Exception as e:
                print(f"  ❌ Failed to create payroll for {user['username']}: {e}")

def create_indexes(db):
    """Create database indexes for better performance"""
    
    try:
        # Users collection indexes
        db.get_collection('users').create_index([('username', 1)], unique=True)
        db.get_collection('users').create_index([('email', 1)], unique=True)
        db.get_collection('users').create_index([('employee_id', 1)], unique=True)
        db.get_collection('users').create_index([('role', 1)])
        db.get_collection('users').create_index([('department', 1)])
        
        # Candidates collection indexes
        db.get_collection('candidates').create_index([('email', 1)])
        db.get_collection('candidates').create_index([('skills', 1)])
        db.get_collection('candidates').create_index([('position_applied', 1)])
        db.get_collection('candidates').create_index([('status', 1)])
        db.get_collection('candidates').create_index([('applied_date', -1)])
        
        # Leaves collection indexes
        db.get_collection('leaves').create_index([('user_id', 1)])
        db.get_collection('leaves').create_index([('status', 1)])
        db.get_collection('leaves').create_index([('start_date', 1)])
        db.get_collection('leaves').create_index([('leave_type', 1)])
        db.get_collection('leaves').create_index([('applied_date', -1)])
        
        # Payroll collection indexes
        db.get_collection('payroll').create_index([('user_id', 1)])
        db.get_collection('payroll').create_index([('month', 1), ('year', 1)])
        db.get_collection('payroll').create_index([('department', 1)])
        db.get_collection('payroll').create_index([('calculated_date', -1)])
        
        # Conversations collection indexes
        db.get_collection('conversations').create_index([('user_id', 1)])
        db.get_collection('conversations').create_index([('session_id', 1)])
        db.get_collection('conversations').create_index([('timestamp', -1)])
        db.get_collection('conversations').create_index([('agent', 1)])
        
        # Memory collections indexes
        db.get_collection('short_term_memory').create_index([('user_id', 1)])
        db.get_collection('short_term_memory').create_index([('session_id', 1)])
        db.get_collection('short_term_memory').create_index([('expires_at', 1)], expireAfterSeconds=0)
        
        db.get_collection('long_term_memory').create_index([('user_id', 1)])
        db.get_collection('long_term_memory').create_index([('memory_type', 1)])
        db.get_collection('long_term_memory').create_index([('created_at', -1)])
        
        print("  ✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"  ⚠️ Some indexes may already exist: {e}")

def print_login_details():
    """Print login details for users"""
    print("\n📋 Login Details:")
    print("=" * 60)
    print("🏢 HR Users:")
    print("  👤 Username: admin | Password: admin123 (HR Director)")
    print("  👤 Username: hr.manager | Password: hr123 (HR Manager)")
    print("  👤 Username: hr.exec | Password: hr123 (HR Executive)")
    print("\n👥 Regular Users:")
    print("  👤 Username: john.doe | Password: user123 (Senior Software Engineer)")
    print("  👤 Username: jane.smith | Password: user123 (Frontend Developer)")
    print("  👤 Username: mike.wilson | Password: user123 (DevOps Engineer)")
    print("  👤 Username: sarah.brown | Password: user123 (Financial Analyst)")
    print("  👤 Username: david.lee | Password: user123 (Marketing Manager)")
    print("  👤 Username: lisa.garcia | Password: user123 (Backend Developer)")
    print("  👤 Username: kevin.johnson | Password: user123 (Accountant)")
    print("=" * 60)
    print("\n🔍 CV Files Information:")
    print("📁 CV files processed from: backend/data/cv_files/")
    print("🤖 Candidates created with vector embeddings for AI search")
    print("🔎 Use HR account to search: 'Find Java developers' or 'Show me Python candidates'")
    print("\n💡 Quick Test Commands:")
    print("  🏖️ Leave: 'I need leave next week'")
    print("  💰 Payroll: 'Calculate my payroll'")
    print("  👥 Candidates (HR only): 'Find React developers'")

if __name__ == '__main__':
    print("🚀 Starting HR AI Database Initialization...")
    print("=" * 60)
    
    try:
        init_database()
        print("\n🎉 Database setup completed successfully!")
        print("▶️ You can now start the application with: python app.py")
        
    except Exception as e:
        print(f"\n💥 Setup failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("  1. Check MongoDB connection")
        print("  2. Verify GEMINI_API_KEY in .env file")
        print("  3. Install required packages: pip install -r requirements.txt")
        exit(1)