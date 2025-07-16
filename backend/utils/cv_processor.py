# backend/utils/cv_processor.py
import os
import re
from typing import Dict, Any, List
import google.generativeai as genai
from datetime import datetime

class CVProcessor:
    """
    Essential CV processing utility for ATS agent
    """
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text content from various file formats"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            elif file_extension == '.pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                        return text
                except ImportError:
                    return "PDF processing requires PyPDF2. Please install: pip install PyPDF2"
            
            elif file_extension in ['.doc', '.docx']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except ImportError:
                    return "Word document processing requires python-docx. Please install: pip install python-docx"
            
            else:
                return f"Unsupported file format: {file_extension}"
                
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def extract_cv_info(self, cv_content: str) -> Dict[str, Any]:
        """Extract structured information from CV content using Gemini and fallback regex"""
        
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
            # First try with Gemini AI
            gemini_result = self._extract_with_gemini(cv_content)
            if gemini_result:
                extracted_info.update(gemini_result)
        except Exception as e:
            print(f"  ⚠️ Gemini extraction failed: {e}")
        
        # Fallback to regex extraction if Gemini didn't get everything
        if not extracted_info.get('email') or not extracted_info.get('skills'):
            regex_result = self._extract_with_regex(cv_content)
            
            # Merge results, preferring Gemini but filling gaps with regex
            for key, value in regex_result.items():
                if not extracted_info.get(key) and value:
                    extracted_info[key] = value
        
        return extracted_info
    
    def _extract_with_gemini(self, cv_content: str) -> Dict[str, Any]:
        """Extract information using Gemini AI"""
        try:
            prompt = f"""
            Extract structured information from this CV/Resume content:
            
            {cv_content[:3000]}  # Limit to avoid token limits
            
            Please extract the following information:
            1. Personal Information:
               - Full name
               - Email address
               - Phone number
            
            2. Professional Information:
               - Current job title/position seeking
               - Years of total experience
               - Key technical skills (especially programming languages, frameworks, tools)
               - Certifications
            
            3. Education:
               - Highest degree
               - University/Institution
            
            Return the information in JSON format:
            {{
                "name": "Full Name",
                "email": "email@domain.com",
                "phone": "phone number",
                "position_applied": "position seeking or current title",
                "skills": ["skill1", "skill2", "skill3"],
                "experience": "X years of experience in field",
                "education": "degree from institution",
                "summary": "brief professional summary"
            }}
            
            Focus on extracting technical skills accurately. If information is not available, use empty string or empty array.
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            import json
            json_start = response.text.find('{')
            json_end = response.text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response.text[json_start:json_end]
                extracted_info = json.loads(json_text)
                
                # Clean and validate the extracted information
                cleaned_info = {}
                
                if extracted_info.get('name'):
                    cleaned_info['name'] = extracted_info['name'].strip()
                
                if extracted_info.get('email'):
                    email = extracted_info['email'].strip()
                    if '@' in email:  # Basic email validation
                        cleaned_info['email'] = email
                
                if extracted_info.get('phone'):
                    cleaned_info['phone'] = extracted_info['phone'].strip()
                
                if extracted_info.get('position_applied'):
                    cleaned_info['position_applied'] = extracted_info['position_applied'].strip()
                
                if extracted_info.get('skills') and isinstance(extracted_info['skills'], list):
                    skills = [skill.strip().lower() for skill in extracted_info['skills'] if skill.strip()]
                    cleaned_info['skills'] = list(set(skills))  # Remove duplicates
                
                if extracted_info.get('experience'):
                    cleaned_info['experience'] = extracted_info['experience'].strip()
                
                if extracted_info.get('education'):
                    cleaned_info['education'] = extracted_info['education'].strip()
                
                if extracted_info.get('summary'):
                    cleaned_info['summary'] = extracted_info['summary'].strip()
                
                return cleaned_info
            
            return {}
            
        except Exception as e:
            print(f"  ⚠️ Gemini extraction error: {e}")
            return {}
    
    def _extract_with_regex(self, cv_content: str) -> Dict[str, Any]:
        """Fallback regex extraction"""
        
        extracted_info = {
            'name': '',
            'email': '',
            'phone': '',
            'position_applied': '',
            'skills': [],
            'experience': '',
            'summary': ''
        }
        
        try:
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
                'react', 'angular', 'vue', 'nodejs', 'express', 'django', 'flask', 'spring',
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'terraform',
                'html', 'css', 'bootstrap', 'sass', 'less', 'webpack',
                'machine learning', 'data science', 'artificial intelligence', 'tensorflow', 'pytorch',
                'figma', 'sketch', 'photoshop', 'illustrator', 'selenium', 'postman'
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
            
            # Determine position based on skills or content
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
            elif any(skill in found_skills for skill in ['figma', 'sketch', 'photoshop']):
                extracted_info['position_applied'] = 'UI/UX Designer'
            elif any(skill in found_skills for skill in ['selenium', 'postman']):
                extracted_info['position_applied'] = 'QA Engineer'
            else:
                # Try to extract from content
                if 'developer' in cv_lower:
                    extracted_info['position_applied'] = 'Software Developer'
                elif 'engineer' in cv_lower:
                    extracted_info['position_applied'] = 'Software Engineer'
                elif 'designer' in cv_lower:
                    extracted_info['position_applied'] = 'Designer'
                elif 'analyst' in cv_lower:
                    extracted_info['position_applied'] = 'Analyst'
                else:
                    extracted_info['position_applied'] = 'Professional'
            
            # Generate experience summary
            if found_skills:
                extracted_info['experience'] = f"Professional with experience in {', '.join(found_skills[:3])}"
            else:
                extracted_info['experience'] = "Experienced professional"
            
            # Generate summary
            if found_skills:
                extracted_info['summary'] = f"Candidate with skills in {', '.join(found_skills[:5])}"
            else:
                extracted_info['summary'] = "Professional candidate"
            
        except Exception as e:
            print(f"  ⚠️ Regex extraction error: {e}")
        
        return extracted_info
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract technical skills from CV text"""
        # Common technical skills to look for
        common_skills = [
            'java', 'python', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go',
            'react', 'angular', 'vue', 'nodejs', 'express', 'django', 'flask', 'spring',
            'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'jenkins'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in common_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found_skills.append(skill)
        
        return found_skills