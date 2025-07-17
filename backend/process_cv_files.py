# backend/process_cv_files.py
import os
import glob
from datetime import datetime
from pymongo import MongoClient
from models.candidate import Candidate
from utils.cv_processor import CVProcessor
from dotenv import load_dotenv
import json
import re

# Try to import sentence transformers for vectorization
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ Warning: sentence-transformers not available. Install with: pip install sentence-transformers")

# Load environment variables
load_dotenv()

class CVFileProcessor:
    """Process CV files from backend/data/cv_files and store in MongoDB with vectors"""
    
    def __init__(self):
        # MongoDB connection
        mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        db_name = os.getenv('DB_NAME', 'hr_ai_system')
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        
        # Initialize models
        self.candidate_model = Candidate(self.db)
        
        # Initialize CV processor
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            self.cv_processor = CVProcessor(gemini_api_key)
        else:
            self.cv_processor = None
            print("⚠️ Warning: GEMINI_API_KEY not found. CV processing will be limited.")
        
        # Initialize sentence transformer for vectorization
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Sentence transformer model loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load sentence transformer: {e}")
                self.encoder = None
        else:
            self.encoder = None
        
        # CV files directory
        self.cv_files_dir = os.path.join('data', 'cv_files')
        
    def process_all_cv_files(self):
        """Process all CV files in the cv_files directory"""
        
        # Check if directory exists
        if not os.path.exists(self.cv_files_dir):
            print(f"❌ Directory {self.cv_files_dir} does not exist!")
            print(f"📁 Please create the directory and add CV text files")
            return
        
        # Find all text files
        cv_files = glob.glob(os.path.join(self.cv_files_dir, "*.txt"))
        
        if not cv_files:
            print(f"📄 No .txt files found in {self.cv_files_dir}")
            print("💡 Please add CV files as .txt format in the cv_files directory")
            return
        
        print(f"📋 Found {len(cv_files)} CV files to process")
        print("🔄 Starting processing...")
        
        processed_count = 0
        failed_count = 0
        
        for cv_file in cv_files:
            try:
                print(f"\n📄 Processing: {os.path.basename(cv_file)}")
                success = self.process_single_cv_file(cv_file)
                
                if success:
                    processed_count += 1
                    print(f"  ✅ Successfully processed")
                else:
                    failed_count += 1
                    print(f"  ❌ Failed to process")
                    
            except Exception as e:
                failed_count += 1
                print(f"  ❌ Error processing {cv_file}: {str(e)}")
        
        print(f"\n📊 Processing Summary:")
        print(f"  ✅ Successfully processed: {processed_count}")
        print(f"  ❌ Failed: {failed_count}")
        print(f"  📁 Total files: {len(cv_files)}")
        
    def process_single_cv_file(self, file_path):
        """Process a single CV file"""
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as file:
                cv_content = file.read().strip()
            
            if not cv_content:
                print(f"  ⚠️ File is empty: {file_path}")
                return False
            
            # Extract filename without extension for candidate name
            filename = os.path.basename(file_path)
            candidate_name = os.path.splitext(filename)[0].replace('_', ' ').title()
            
            # Process CV content to extract structured information
            extracted_info = self.extract_cv_information(cv_content)
            
            # Use extracted name if available, otherwise use filename
            if extracted_info.get('name'):
                candidate_name = extracted_info['name']
            
            # Generate vector embedding
            vector_embedding = None
            if self.encoder:
                try:
                    embedding = self.encoder.encode(cv_content)
                    vector_embedding = embedding.tolist()
                    print(f"  🔢 Generated vector embedding (dimension: {len(vector_embedding)})")
                except Exception as e:
                    print(f"  ⚠️ Failed to generate embedding: {e}")
            
            # Prepare candidate data
            candidate_data = {
                'name': candidate_name,
                'email': extracted_info.get('email', f"{candidate_name.lower().replace(' ', '.')}@email.com"),
                'phone': extracted_info.get('phone', '+94771234567'),
                'position_applied': extracted_info.get('position_applied', 'Software Developer'),
                'skills': extracted_info.get('skills', []),
                'experience': extracted_info.get('experience', 'Experience details not specified'),
                'education': extracted_info.get('education', 'Education details not specified'),
                'cv_content': cv_content,
                'cv_file_path': file_path,
                'summary': extracted_info.get('summary', 'Professional candidate'),
                'status': 'applied',
                'vector_embedding': vector_embedding,
                'processed_date': datetime.now()
            }
            
            # Check if candidate already exists
            existing_candidates = self.candidate_model.get_all_candidates()
            existing_names = [c.get('name', '').lower() for c in existing_candidates]
            
            if candidate_name.lower() in existing_names:
                print(f"  ⚠️ Candidate {candidate_name} already exists, skipping...")
                return True
            
            # Save to database
            candidate_id = self.candidate_model.create_candidate(candidate_data)
            
            print(f"  📝 Candidate: {candidate_name}")
            print(f"  📧 Email: {candidate_data['email']}")
            print(f"  💼 Position: {candidate_data['position_applied']}")
            print(f"  🛠️ Skills: {', '.join(candidate_data['skills'][:5])}{'...' if len(candidate_data['skills']) > 5 else ''}")
            print(f"  🆔 Database ID: {candidate_id}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return False
    
    def extract_cv_information(self, cv_content):
        """Extract structured information from CV content"""
        
        extracted_info = {
            'name': '',
            'email': '',
            'phone': '',
            'position_applied': '',
            'skills': [],
            'experience': '',
            'education': '',
            'summary': ''
        }
        
        try:
            # Use CV processor if available
            if self.cv_processor:
                processed_info = self.cv_processor.extract_cv_info(cv_content)
                if processed_info:
                    extracted_info.update(processed_info)
                    return extracted_info
            
            # Fallback: Extract information using regex patterns
            cv_lower = cv_content.lower()
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, cv_content)
            if email_match:
                extracted_info['email'] = email_match.group()
            
            # Extract phone number
            phone_patterns = [
                r'\+94\d{9}',
                r'94\d{9}',
                r'0\d{9}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
            ]
            for pattern in phone_patterns:
                phone_match = re.search(pattern, cv_content)
                if phone_match:
                    extracted_info['phone'] = phone_match.group()
                    break
            
            # Extract skills using common programming terms
            common_skills = [
                'java', 'python', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'react', 'angular', 'vue', 'nodejs', 'node.js', 'express', 'django', 'flask', 'spring',
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'terraform', 'ansible',
                'html', 'css', 'bootstrap', 'sass', 'less', 'webpack',
                'machine learning', 'data science', 'artificial intelligence', 'tensorflow', 'pytorch',
                'devops', 'flutter', 'dart', 'kotlin', 'swift', 'xcode', 'android', 
                'ui/ux', 'ui', 'ux', 'figma', 'sketch', 'adobe xd', 
                'selenium', 'cypress', 'postman', 'qa' 
            ]
            
            found_skills = []
            for skill in common_skills:
                if re.search(r'\b' + re.escape(skill) + r'\b', cv_lower):
                    found_skills.append(skill)
            
            extracted_info['skills'] = found_skills
            
            # Extract name (usually in the first few lines)
            lines = cv_content.split('\n')
            for line in lines[:5]:
                line = line.strip()
                if line and len(line.split()) <= 4 and len(line) > 5:
                    # Likely a name if it's short and contains letters
                    if re.match(r'^[A-Za-z\s\.]+$', line):
                        extracted_info['name'] = line.title()
                        break
            
            # Determine position based on skills
            if any(skill in found_skills for skill in ['java', 'spring']):
                extracted_info['position_applied'] = 'Java Developer'
            elif any(skill in found_skills for skill in ['python', 'django', 'flask']):
                extracted_info['position_applied'] = 'Python Developer'
            elif any(skill in found_skills for skill in ['react', 'angular', 'vue']):
                extracted_info['position_applied'] = 'Frontend Developer'
            elif any(skill in found_skills for skill in ['docker', 'kubernetes', 'aws']):
                extracted_info['position_applied'] = 'DevOps Engineer'
            elif any(skill in found_skills for skill in ['machine learning', 'data science']):
                extracted_info['position_applied'] = 'Data Scientist'
            else:
                extracted_info['position_applied'] = 'Software Developer'
            
            # Generate experience summary
            extracted_info['experience'] = f"Professional with experience in {', '.join(found_skills[:3])}" if found_skills else "Experienced professional"
            
            # Generate summary
            extracted_info['summary'] = f"Candidate with skills in {', '.join(found_skills[:5])}" if found_skills else "Professional candidate"
            
        except Exception as e:
            print(f"  ⚠️ Error extracting CV info: {e}")
        
        return extracted_info
    
    def create_sample_cv_files(self):
        """Create sample CV files if directory is empty"""
        
        # Create directory if it doesn't exist
        os.makedirs(self.cv_files_dir, exist_ok=True)
        
        sample_cvs = [
            {
                'filename': 'john_developer.txt',
                'content': '''John Smith
Email: john.smith@email.com
Phone: +94771234567

Senior Java Developer

Experience:
5+ years of experience in Java development with expertise in Spring Boot, microservices architecture.
Worked on large-scale enterprise applications and REST API development.

Skills:
- Java, Spring Boot, Spring Security
- MySQL, PostgreSQL, MongoDB
- Docker, Kubernetes, AWS
- Git, Jenkins, Maven
- Microservices, REST APIs

Education:
BSc Computer Science, University of Colombo (2018)

Projects:
- E-commerce platform using Spring Boot and React
- Microservices architecture for banking system
- Real-time chat application with WebSocket'''
            },
            {
                'filename': 'sarah_frontend.txt',
                'content': '''Sarah Johnson
sarah.johnson@email.com
+94772345678

Frontend Developer

Professional Summary:
Creative and detail-oriented Frontend Developer with 3+ years of experience in building responsive web applications using modern JavaScript frameworks.

Technical Skills:
- JavaScript, TypeScript, ES6+
- React.js, Redux, Context API
- HTML5, CSS3, SASS, Bootstrap
- Node.js, Express.js
- Git, Webpack, Babel
- Responsive Design, UI/UX

Work Experience:
Frontend Developer at Tech Solutions (2021-2024)
- Developed and maintained React-based web applications
- Collaborated with UX/UI designers to implement pixel-perfect designs
- Optimized application performance and loading times

Education:
BSc Information Technology, SLIIT (2020)'''
            },
            {
                'filename': 'mike_devops.txt',
                'content': '''Michael Wilson
Email: mike.wilson@email.com
Contact: +94773456789

DevOps Engineer

Summary:
Experienced DevOps Engineer with 4+ years in cloud infrastructure management, containerization, and CI/CD pipeline automation.

Core Competencies:
- AWS, Azure, Google Cloud Platform
- Docker, Kubernetes, Helm
- Terraform, Ansible, CloudFormation
- Jenkins, GitLab CI, GitHub Actions
- Linux, Bash scripting, Python
- Monitoring: Prometheus, Grafana, ELK Stack

Professional Experience:
DevOps Engineer at CloudTech Inc. (2020-2024)
- Managed AWS infrastructure for multiple client projects
- Implemented CI/CD pipelines reducing deployment time by 60%
- Containerized legacy applications using Docker and Kubernetes
- Automated infrastructure provisioning using Terraform

Certifications:
- AWS Certified Solutions Architect
- Certified Kubernetes Administrator (CKA)

Education:
BSc Computer Engineering, University of Moratuwa (2019)'''
            },
            {
                'filename': 'priya_datascientist.txt',
                'content': '''Dr. Priya Perera
priya.perera@email.com
+94774567890

Data Scientist & Machine Learning Engineer

Profile:
PhD in Data Science with 6+ years of experience in machine learning, statistical analysis, and big data processing.

Technical Expertise:
- Python, R, SQL, Scala
- Machine Learning: Scikit-learn, TensorFlow, PyTorch
- Data Processing: Pandas, NumPy, Spark
- Visualization: Matplotlib, Seaborn, Plotly, Tableau
- Cloud Platforms: AWS SageMaker, Google AI Platform
- Databases: PostgreSQL, MongoDB, Cassandra

Research & Development:
- Published 15+ research papers in machine learning conferences
- Developed predictive models for financial risk assessment
- Built recommendation systems for e-commerce platforms
- Expertise in NLP, computer vision, and time series analysis

Education:
PhD Data Science, University of Colombo (2022)
MSc Statistics, University of Peradeniya (2018)'''
            },
            {
                'filename': 'david_mobile.txt',
                'content': '''David Fernando
david.fernando@email.com
Mobile: +94775678901

Mobile Application Developer

Overview:
Passionate mobile developer with 3+ years of experience in creating cross-platform and native mobile applications.

Technical Skills:
- Flutter, Dart
- React Native, JavaScript
- Android (Java, Kotlin)
- iOS (Swift, Objective-C)
- Firebase, Firestore
- REST APIs, GraphQL
- Git, Android Studio, Xcode

Portfolio Projects:
- E-learning mobile app with 10K+ downloads
- Food delivery app with real-time tracking
- Social media app with chat functionality
- Fitness tracking app with wearable integration

Experience:
Mobile Developer at InnoApps (2021-2024)
- Developed 8+ mobile applications for various clients
- Maintained 4.5+ star rating on app stores
- Collaborated with backend teams for API integration

Education:
BSc Software Engineering, NSBM (2020)'''
            },
            {
                'filename': 'lisa_qa.txt',
                'content': '''Lisa Garcia
lisa.garcia@email.com
Phone: +94776789012

Quality Assurance Engineer

Professional Summary:
Detail-oriented QA Engineer with 4+ years of experience in manual and automated testing across web and mobile applications.

Testing Expertise:
- Selenium WebDriver, TestNG, JUnit
- Postman, REST Assured for API testing
- Cucumber, BDD, Gherkin
- JIRA, TestRail, Bugzilla
- Java, Python for test automation
- Performance Testing: JMeter, LoadRunner
- Mobile Testing: Appium

Experience:
Senior QA Engineer at QualityFirst Solutions (2020-2024)
- Designed and executed comprehensive test plans
- Automated 70% of regression test cases
- Reduced bug leakage to production by 85%
- Mentored junior QA team members

Testing Methodologies:
- Agile/Scrum testing practices
- Risk-based testing approach
- Continuous integration testing
- Cross-browser and cross-platform testing

Education:
BSc Information Systems, University of Sri Jayewardenepura (2019)'''
            },
            {
                'filename': 'kevin_fullstack.txt',
                'content': '''Kevin Rajapakse
kevin.raj@email.com
+94777890123

Full Stack Developer

Technical Profile:
Versatile Full Stack Developer with 4+ years of experience in end-to-end web application development.

Frontend Technologies:
- React.js, Vue.js, Angular
- JavaScript, TypeScript, HTML5, CSS3
- Bootstrap, Tailwind CSS, Material-UI
- Redux, Vuex, RxJS

Backend Technologies:
- Node.js, Express.js, Nest.js
- Python, Django, FastAPI
- PHP, Laravel
- RESTful APIs, GraphQL

Database & DevOps:
- MySQL, PostgreSQL, MongoDB
- Redis, Elasticsearch
- Docker, AWS, Heroku
- Git, CI/CD pipelines

Recent Projects:
- E-commerce platform with payment integration
- Real-time collaboration tool
- Hospital management system
- Property management web application

Education:
BSc Computer Science, University of Kelaniya (2019)'''
            },
            {
                'filename': 'nina_uiux.txt',
                'content': '''Nina Wickramasinghe
nina.wickrama@email.com
Contact: +94778901234

UI/UX Designer

Creative Profile:
Innovative UI/UX Designer with 3+ years of experience creating user-centered digital experiences for web and mobile platforms.

Design Skills:
- Figma, Sketch, Adobe XD
- Adobe Photoshop, Illustrator
- Principle, InVision, Marvel
- Wireframing, Prototyping
- User Research, Usability Testing
- Design Systems, Style Guides

Design Methodology:
- Human-centered design approach
- Design thinking process
- Agile design practices
- Accessibility standards (WCAG)
- Responsive design principles

Portfolio Highlights:
- Redesigned e-commerce platform increasing conversion by 35%
- Created design system for fintech startup
- Mobile app UI for healthcare platform
- Dashboard design for analytics platform

Experience:
UI/UX Designer at CreativeMinds Agency (2021-2024)
- Led design for 15+ client projects
- Conducted user research and usability testing
- Collaborated closely with development teams

Education:
Diploma in Graphic Design, AOD (2020)
UX Design Certification, Google (2021)'''
            }
        ]
        
        created_files = []
        for cv_data in sample_cvs:
            file_path = os.path.join(self.cv_files_dir, cv_data['filename'])
            
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(cv_data['content'])
                created_files.append(cv_data['filename'])
        
        if created_files:
            print(f"📄 Created {len(created_files)} sample CV files:")
            for filename in created_files:
                print(f"  - {filename}")
        else:
            print("📄 All sample CV files already exist")
        
        return len(created_files)

def main():
    """Main function to process CV files"""
    
    print("🚀 CV Files Vectorization and MongoDB Storage")
    print("=" * 60)
    
    processor = CVFileProcessor()
    
    # Check if CV files directory exists and has files
    if not os.path.exists(processor.cv_files_dir):
        print(f"📁 Creating directory: {processor.cv_files_dir}")
        os.makedirs(processor.cv_files_dir, exist_ok=True)
    
    # Check for existing CV files
    existing_files = glob.glob(os.path.join(processor.cv_files_dir, "*.txt"))
    
    if not existing_files:
        print("📄 No CV files found. Creating sample CV files...")
        created_count = processor.create_sample_cv_files()
        
        if created_count > 0:
            print(f"✅ Created {created_count} sample CV files")
            print("🔄 Now processing these files...")
        else:
            print("⚠️ No new files created")
            return
    else:
        print(f"📋 Found {len(existing_files)} existing CV files")
    
    # Process all CV files
    processor.process_all_cv_files()
    
    print("\n🎉 CV processing completed!")
    print("💡 You can now use the ATS agent to search for candidates")

if __name__ == '__main__':
    main()