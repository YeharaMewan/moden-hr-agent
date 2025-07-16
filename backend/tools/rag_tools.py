# backend/tools/rag_tools.py
import os
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from pymongo import MongoClient
import google.generativeai as genai

class CompanyDocumentRAG:
    """
    RAG system for company documents
    Handles document ingestion, vectorization, and retrieval
    """
    
    def __init__(self, db_connection, gemini_api_key: str):
        self.db_connection = db_connection
        self.collection = db_connection.get_collection('company_documents')
        self.gemini_api_key = gemini_api_key
        
        # Initialize sentence transformer for embeddings
        try:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Could not load sentence transformer: {e}")
            self.encoder = None
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for efficient search"""
        try:
            self.collection.create_index([('document_type', 1)])
            self.collection.create_index([('department', 1)])
            self.collection.create_index([('tags', 1)])
            self.collection.create_index([('created_at', 1)])
        except Exception:
            pass  # Indexes might already exist
    
    def ingest_document(self, file_path: str, document_metadata: Dict[str, Any]) -> str:
        """
        Ingest a company document into the RAG system
        """
        try:
            # Read document content
            content = self._extract_text_content(file_path)
            
            # Generate chunks
            chunks = self._chunk_document(content)
            
            # Generate embeddings for each chunk
            chunk_embeddings = []
            if self.encoder:
                for chunk in chunks:
                    try:
                        embedding = self.encoder.encode(chunk)
                        chunk_embeddings.append(embedding.tolist())
                    except Exception as e:
                        print(f"Error generating embedding for chunk: {e}")
                        chunk_embeddings.append([])
            
            # Prepare document data
            document_data = {
                'file_path': file_path,
                'filename': os.path.basename(file_path),
                'content': content,
                'chunks': chunks,
                'chunk_embeddings': chunk_embeddings,
                'metadata': document_metadata,
                'document_type': document_metadata.get('type', 'general'),
                'department': document_metadata.get('department', 'general'),
                'tags': document_metadata.get('tags', []),
                'created_at': document_metadata.get('created_at'),
                'indexed_at': datetime.now()
            }
            
            # Store in MongoDB
            result = self.collection.insert_one(document_data)
            document_id = str(result.inserted_id)
            
            print(f"Document ingested successfully: {document_id}")
            return document_id
            
        except Exception as e:
            print(f"Error ingesting document: {str(e)}")
            raise e
    
    def _extract_text_content(self, file_path: str) -> str:
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
                    raise Exception("PyPDF2 not installed. Cannot process PDF files.")
            
            elif file_extension in ['.doc', '.docx']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except ImportError:
                    raise Exception("python-docx not installed. Cannot process Word files.")
            
            else:
                raise Exception(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            raise Exception(f"Error reading document: {str(e)}")
    
    def _chunk_document(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split document into overlapping chunks"""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to end at a sentence boundary
            if end < len(content):
                # Look for sentence endings within the last 100 characters
                sentence_end = content.rfind('.', end - 100, end)
                if sentence_end != -1:
                    end = sentence_end + 1
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
            if start >= len(content):
                break
        
        return chunks
    
    def search_documents(self, query: str, document_type: str = None, 
                        department: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search documents using vector similarity and metadata filtering
        """
        try:
            # Build MongoDB query
            mongo_query = {}
            
            if document_type:
                mongo_query['document_type'] = document_type
            
            if department:
                mongo_query['department'] = department
            
            # Get all documents matching metadata criteria
            documents = list(self.collection.find(mongo_query))
            
            if not documents:
                return []
            
            # If we have embeddings, use vector search
            if self.encoder:
                query_embedding = self.encoder.encode(query)
                scored_chunks = []
                
                for doc in documents:
                    chunk_embeddings = doc.get('chunk_embeddings', [])
                    chunks = doc.get('chunks', [])
                    
                    for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                        if embedding:  # Skip empty embeddings
                            # Calculate cosine similarity
                            similarity = np.dot(query_embedding, embedding) / (
                                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                            )
                            
                            scored_chunks.append({
                                'document_id': str(doc['_id']),
                                'filename': doc['filename'],
                                'chunk_index': i,
                                'chunk_content': chunk,
                                'similarity_score': float(similarity),
                                'document_type': doc.get('document_type'),
                                'department': doc.get('department'),
                                'metadata': doc.get('metadata', {})
                            })
                
                # Sort by similarity score and return top_k
                scored_chunks.sort(key=lambda x: x['similarity_score'], reverse=True)
                return scored_chunks[:top_k]
            
            else:
                # Fallback to text search
                return self._text_search_fallback(query, documents, top_k)
                
        except Exception as e:
            print(f"Error searching documents: {str(e)}")
            return []
    
    def _text_search_fallback(self, query: str, documents: List[Dict], top_k: int) -> List[Dict[str, Any]]:
        """Fallback text search when embeddings are not available"""
        query_terms = query.lower().split()
        scored_chunks = []
        
        for doc in documents:
            chunks = doc.get('chunks', [])
            
            for i, chunk in enumerate(chunks):
                chunk_lower = chunk.lower()
                
                # Simple term frequency scoring
                score = 0
                for term in query_terms:
                    score += chunk_lower.count(term)
                
                if score > 0:
                    scored_chunks.append({
                        'document_id': str(doc['_id']),
                        'filename': doc['filename'],
                        'chunk_index': i,
                        'chunk_content': chunk,
                        'similarity_score': score,
                        'document_type': doc.get('document_type'),
                        'department': doc.get('department'),
                        'metadata': doc.get('metadata', {})
                    })
        
        # Sort by score and return top_k
        scored_chunks.sort(key=lambda x: x['similarity_score'], reverse=True)
        return scored_chunks[:top_k]
    
    def generate_answer_with_context(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Generate answer using Gemini with retrieved context
        """
        try:
            if not context_chunks:
                return "I couldn't find relevant information in the company documents to answer your question."
            
            # Prepare context from chunks
            context_text = "\n\n".join([
                f"From {chunk['filename']} ({chunk['document_type']}):\n{chunk['chunk_content']}"
                for chunk in context_chunks
            ])
            
            prompt = f"""
            Based on the following company documents, please answer the user's question.
            
            User Question: {query}
            
            Relevant Company Information:
            {context_text}
            
            Instructions:
            1. Answer the question using only the information provided in the company documents
            2. If the documents don't contain enough information, say so clearly
            3. Cite which document(s) you're referencing
            4. Be concise but thorough
            5. If there are multiple relevant policies or procedures, mention them all
            
            Answer:
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Error generating answer: {str(e)}")
            return "I encountered an error while processing your question. Please try again."
    
    def query_company_documents(self, query: str, document_type: str = None, 
                               department: str = None) -> Dict[str, Any]:
        """
        Main RAG query function
        """
        try:
            # Search for relevant documents
            relevant_chunks = self.search_documents(query, document_type, department)
            
            if not relevant_chunks:
                return {
                    'answer': "I couldn't find any relevant information in the company documents.",
                    'sources': [],
                    'confidence': 0.0
                }
            
            # Generate answer with context
            answer = self.generate_answer_with_context(query, relevant_chunks)
            
            # Prepare sources information
            sources = []
            for chunk in relevant_chunks:
                sources.append({
                    'filename': chunk['filename'],
                    'document_type': chunk['document_type'],
                    'department': chunk['department'],
                    'similarity_score': chunk['similarity_score']
                })
            
            # Calculate confidence based on similarity scores
            avg_similarity = np.mean([chunk['similarity_score'] for chunk in relevant_chunks])
            confidence = min(avg_similarity * 100, 100.0)  # Convert to percentage, cap at 100%
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': confidence,
                'chunks_found': len(relevant_chunks)
            }
            
        except Exception as e:
            print(f"Error in RAG query: {str(e)}")
            return {
                'answer': "I encountered an error while searching the company documents.",
                'sources': [],
                'confidence': 0.0
            }
    
    def get_document_summary(self) -> Dict[str, Any]:
        """Get summary of ingested documents"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$document_type',
                        'count': {'$sum': 1},
                        'departments': {'$addToSet': '$department'}
                    }
                }
            ]
            
            stats = list(self.collection.aggregate(pipeline))
            
            total_docs = self.collection.count_documents({})
            
            return {
                'total_documents': total_docs,
                'by_type': {stat['_id']: stat['count'] for stat in stats},
                'departments': list(set([dept for stat in stats for dept in stat['departments']]))
            }
            
        except Exception as e:
            print(f"Error getting document summary: {str(e)}")
            return {'total_documents': 0, 'by_type': {}, 'departments': []}

# backend/utils/cv_processor.py
import os
import re
from typing import Dict, Any, List
import google.generativeai as genai
from datetime import datetime

class CVProcessor:
    """
    Utility class for processing CV files and extracting structured information
    """
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def extract_cv_info(self, cv_content: str) -> Dict[str, Any]:
        """Extract structured information from CV content"""
        try:
            prompt = f"""
            Extract structured information from this CV/Resume content:
            
            {cv_content[:4000]}  # Limit to avoid token limits
            
            Please extract the following information:
            1. Personal Information:
               - Full name
               - Email address
               - Phone number
               - Address (if available)
            
            2. Professional Information:
               - Current job title/position seeking
               - Years of total experience
               - Key skills (especially technical skills)
               - Programming languages
               - Frameworks and technologies
               - Certifications
            
            3. Education:
               - Highest degree
               - University/Institution
               - Field of study
            
            4. Work Experience:
               - Previous companies
               - Job titles
               - Key responsibilities
            
            5. Projects (if mentioned):
               - Project names
               - Technologies used
            
            Return the information in JSON format:
            {{
                "personal_info": {{
                    "name": "Full Name",
                    "email": "email@domain.com",
                    "phone": "phone number",
                    "address": "address if available"
                }},
                "professional_info": {{
                    "current_position": "current or seeking position",
                    "total_experience_years": "X years",
                    "technical_skills": ["skill1", "skill2", "skill3"],
                    "programming_languages": ["language1", "language2"],
                    "frameworks": ["framework1", "framework2"],
                    "certifications": ["cert1", "cert2"]
                }},
                "education": {{
                    "highest_degree": "degree name",
                    "institution": "university/college name",
                    "field_of_study": "field of study"
                }},
                "work_experience": [
                    {{
                        "company": "company name",
                        "position": "job title",
                        "duration": "duration if available",
                        "responsibilities": "key responsibilities"
                    }}
                ],
                "projects": [
                    {{
                        "name": "project name",
                        "technologies": ["tech1", "tech2"],
                        "description": "brief description"
                    }}
                ]
            }}
            
            Focus on extracting technical skills accurately. If information is not available, use null or empty arrays.
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
                return self._clean_extracted_info(extracted_info)
            
            return {}
            
        except Exception as e:
            print(f"Error extracting CV info: {str(e)}")
            return {}
    
    def _clean_extracted_info(self, raw_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate extracted CV information"""
        cleaned = {
            'name': '',
            'email': '',
            'phone': '',
            'position_applied': '',
            'experience': '',
            'skills': [],
            'education': '',
            'summary': ''
        }
        
        try:
            # Personal info
            personal = raw_info.get('personal_info', {})
            if personal.get('name'):
                cleaned['name'] = personal['name'].strip()
            if personal.get('email'):
                email = personal['email'].strip()
                if '@' in email:  # Basic email validation
                    cleaned['email'] = email
            if personal.get('phone'):
                cleaned['phone'] = personal['phone'].strip()
            
            # Professional info
            professional = raw_info.get('professional_info', {})
            if professional.get('current_position'):
                cleaned['position_applied'] = professional['current_position'].strip()
            if professional.get('total_experience_years'):
                cleaned['experience'] = professional['total_experience_years'].strip()
            
            # Skills aggregation
            skills = set()
            for skill_list in [
                professional.get('technical_skills', []),
                professional.get('programming_languages', []),
                professional.get('frameworks', [])
            ]:
                if isinstance(skill_list, list):
                    skills.update([skill.strip().lower() for skill in skill_list if skill.strip()])
            
            cleaned['skills'] = list(skills)
            
            # Education
            education = raw_info.get('education', {})
            if education.get('highest_degree') or education.get('institution'):
                edu_parts = []
                if education.get('highest_degree'):
                    edu_parts.append(education['highest_degree'])
                if education.get('field_of_study'):
                    edu_parts.append(f"in {education['field_of_study']}")
                if education.get('institution'):
                    edu_parts.append(f"from {education['institution']}")
                cleaned['education'] = ' '.join(edu_parts)
            
            # Generate summary
            summary_parts = []
            if cleaned['experience']:
                summary_parts.append(f"{cleaned['experience']} of experience")
            if cleaned['position_applied']:
                summary_parts.append(f"as {cleaned['position_applied']}")
            if cleaned['skills']:
                top_skills = cleaned['skills'][:5]
                summary_parts.append(f"with skills in {', '.join(top_skills)}")
            
            cleaned['summary'] = '. '.join(summary_parts) if summary_parts else 'Professional candidate'
            
        except Exception as e:
            print(f"Error cleaning extracted info: {str(e)}")
        
        return cleaned

# backend/utils/vector_store.py
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os

class VectorStore:
    """
    Vector store for similarity search using FAISS
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', index_path: str = None):
        self.model_name = model_name
        self.index_path = index_path or 'data/vector_index'
        
        # Initialize sentence transformer
        try:
            self.encoder = SentenceTransformer(model_name)
            self.dimension = self.encoder.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"Warning: Could not load sentence transformer: {e}")
            self.encoder = None
            self.dimension = 384  # Default dimension
        
        # Initialize FAISS index
        self.index = None
        self.document_store = []  # Store document metadata
        
        # Load existing index if available
        self.load_index()
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector store"""
        if not self.encoder:
            print("Warning: No encoder available, cannot add documents")
            return
        
        try:
            # Extract text content for embedding
            texts = []
            for doc in documents:
                text_content = doc.get('content', '')
                if isinstance(text_content, list):
                    # If content is chunked
                    texts.extend(text_content)
                    # Add metadata for each chunk
                    for i, chunk in enumerate(text_content):
                        chunk_metadata = doc.copy()
                        chunk_metadata['chunk_index'] = i
                        chunk_metadata['content'] = chunk
                        self.document_store.append(chunk_metadata)
                else:
                    texts.append(text_content)
                    self.document_store.append(doc)
            
            # Generate embeddings
            embeddings = self.encoder.encode(texts)
            embeddings = np.array(embeddings).astype('float32')
            
            # Initialize or update FAISS index
            if self.index is None:
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                # Normalize embeddings for cosine similarity
                faiss.normalize_L2(embeddings)
                self.index.add(embeddings)
            else:
                faiss.normalize_L2(embeddings)
                self.index.add(embeddings)
            
            print(f"Added {len(texts)} documents to vector store")
            
        except Exception as e:
            print(f"Error adding documents to vector store: {str(e)}")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar documents"""
        if not self.encoder or self.index is None:
            print("Warning: Vector store not properly initialized")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode([query])
            query_embedding = np.array(query_embedding).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search in FAISS index
            scores, indices = self.index.search(query_embedding, top_k)
            
            # Prepare results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.document_store):
                    doc = self.document_store[idx]
                    results.append((doc, float(score)))
            
            return results
            
        except Exception as e:
            print(f"Error searching vector store: {str(e)}")
            return []
    
    def save_index(self) -> None:
        """Save FAISS index and document store to disk"""
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            if self.index is not None:
                # Save FAISS index
                faiss.write_index(self.index, f"{self.index_path}.faiss")
                
                # Save document store
                with open(f"{self.index_path}.pkl", 'wb') as f:
                    pickle.dump(self.document_store, f)
                
                print(f"Vector index saved to {self.index_path}")
            
        except Exception as e:
            print(f"Error saving vector index: {str(e)}")
    
    def load_index(self) -> None:
        """Load FAISS index and document store from disk"""
        try:
            if os.path.exists(f"{self.index_path}.faiss") and os.path.exists(f"{self.index_path}.pkl"):
                # Load FAISS index
                self.index = faiss.read_index(f"{self.index_path}.faiss")
                
                # Load document store
                with open(f"{self.index_path}.pkl", 'rb') as f:
                    self.document_store = pickle.load(f)
                
                print(f"Vector index loaded from {self.index_path}")
            
        except Exception as e:
            print(f"Error loading vector index: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            'total_documents': len(self.document_store),
            'index_size': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'model_name': self.model_name
        }

# backend/tools/leave_tools.py
from datetime import datetime, timedelta
from typing import Dict, Any, List
import calendar

class LeaveTools:
    """
    Utility tools for leave management
    """
    
    @staticmethod
    def calculate_working_days(start_date: datetime, end_date: datetime, 
                              exclude_weekends: bool = True) -> int:
        """Calculate number of working days between two dates"""
        if start_date > end_date:
            return 0
        
        total_days = (end_date - start_date).days + 1
        
        if not exclude_weekends:
            return total_days
        
        # Count weekdays only
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    @staticmethod
    def check_leave_conflicts(user_id: str, start_date: datetime, end_date: datetime, 
                             leave_model, exclude_leave_id: str = None) -> List[Dict[str, Any]]:
        """Check for conflicting leave requests"""
        try:
            # Get user's existing leaves
            existing_leaves = leave_model.get_leaves_by_user(user_id)
            
            conflicts = []
            for leave in existing_leaves:
                # Skip the current leave being edited
                if exclude_leave_id and str(leave['_id']) == exclude_leave_id:
                    continue
                
                # Skip rejected leaves
                if leave['status'] == 'rejected':
                    continue
                
                # Check for date overlap
                if (start_date <= leave['end_date'] and end_date >= leave['start_date']):
                    conflicts.append({
                        'leave_id': str(leave['_id']),
                        'leave_type': leave['leave_type'],
                        'start_date': leave['start_date'],
                        'end_date': leave['end_date'],
                        'status': leave['status']
                    })
            
            return conflicts
            
        except Exception as e:
            print(f"Error checking leave conflicts: {str(e)}")
            return []
    
    @staticmethod
    def calculate_leave_balance(user_id: str, user_model, leave_model, 
                               year: int = None) -> Dict[str, Any]:
        """Calculate user's leave balance"""
        try:
            if not year:
                year = datetime.now().year
            
            # Get user details
            user = user_model.get_user_by_id(user_id)
            if not user:
                return {'error': 'User not found'}
            
            annual_allocation = user.get('annual_leave_balance', 21)
            
            # Get approved leaves for the year
            user_leaves = leave_model.get_leaves_by_user(user_id, status='approved')
            
            used_days = 0
            for leave in user_leaves:
                if leave['start_date'].year == year:
                    days = LeaveTools.calculate_working_days(leave['start_date'], leave['end_date'])
                    used_days += days
            
            remaining_balance = max(0, annual_allocation - used_days)
            
            return {
                'annual_allocation': annual_allocation,
                'used_days': used_days,
                'remaining_balance': remaining_balance,
                'year': year
            }
            
        except Exception as e:
            print(f"Error calculating leave balance: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def generate_leave_calendar(user_id: str, leave_model, year: int = None, 
                               month: int = None) -> Dict[str, Any]:
        """Generate leave calendar for user"""
        try:
            if not year:
                year = datetime.now().year
            
            if month:
                # Get leaves for specific month
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            else:
                # Get leaves for entire year
                start_date = datetime(year, 1, 1)
                end_date = datetime(year, 12, 31)
            
            leaves = leave_model.get_leaves_by_date_range(start_date, end_date)
            user_leaves = [leave for leave in leaves if leave['user_id'] == user_id]
            
            # Group by month
            calendar_data = {}
            for i in range(1, 13):
                if month and i != month:
                    continue
                calendar_data[i] = {
                    'month_name': calendar.month_name[i],
                    'leaves': []
                }
            
            for leave in user_leaves:
                leave_month = leave['start_date'].month
                if leave_month in calendar_data:
                    calendar_data[leave_month]['leaves'].append({
                        'leave_id': str(leave['_id']),
                        'leave_type': leave['leave_type'],
                        'start_date': leave['start_date'].strftime('%Y-%m-%d'),
                        'end_date': leave['end_date'].strftime('%Y-%m-%d'),
                        'status': leave['status'],
                        'days': LeaveTools.calculate_working_days(leave['start_date'], leave['end_date'])
                    })
            
            return {
                'year': year,
                'calendar': calendar_data
            }
            
        except Exception as e:
            print(f"Error generating leave calendar: {str(e)}")
            return {'error': str(e)}

# backend/tools/payroll_tools.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
import calendar

class PayrollTools:
    """
    Utility tools for payroll calculations
    """
    
    @staticmethod
    def calculate_working_days_in_month(year: int, month: int) -> int:
        """Calculate working days in a specific month"""
        try:
            # Get first and last day of month
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
            
            working_days = 0
            current_date = first_day
            
            while current_date <= last_day:
                # Monday = 0, Sunday = 6
                if current_date.weekday() < 5:  # Weekdays only
                    working_days += 1
                current_date += timedelta(days=1)
            
            return working_days
            
        except Exception as e:
            print(f"Error calculating working days: {str(e)}")
            return 22  # Default fallback
    
    @staticmethod
    def calculate_overtime_pay(basic_salary: float, overtime_hours: float, 
                              overtime_rate: float = 1.5) -> float:
        """Calculate overtime payment"""
        try:
            # Assuming 8 hours per day, 22 working days per month
            hourly_rate = basic_salary / (8 * 22)
            overtime_pay = hourly_rate * overtime_hours * overtime_rate
            return round(overtime_pay, 2)
            
        except Exception as e:
            print(f"Error calculating overtime pay: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_prorated_salary(basic_salary: float, worked_days: int, 
                                 total_working_days: int) -> float:
        """Calculate prorated salary based on days worked"""
        try:
            if total_working_days == 0:
                return 0.0
            
            daily_rate = basic_salary / total_working_days
            prorated_salary = daily_rate * worked_days
            return round(prorated_salary, 2)
            
        except Exception as e:
            print(f"Error calculating prorated salary: {str(e)}")
            return basic_salary
    
    @staticmethod
    def calculate_tax_deduction(gross_salary: float, tax_brackets: List[Dict[str, Any]] = None) -> float:
        """Calculate income tax based on tax brackets"""
        try:
            if not tax_brackets:
                # Default Sri Lankan tax brackets (simplified)
                tax_brackets = [
                    {'min': 0, 'max': 100000, 'rate': 0.0},
                    {'min': 100000, 'max': 150000, 'rate': 0.06},
                    {'min': 150000, 'max': 200000, 'rate': 0.12},
                    {'min': 200000, 'max': float('inf'), 'rate': 0.18}
                ]
            
            total_tax = 0.0
            remaining_salary = gross_salary
            
            for bracket in tax_brackets:
                if remaining_salary <= 0:
                    break
                
                bracket_min = bracket['min']
                bracket_max = bracket['max']
                tax_rate = bracket['rate']
                
                if gross_salary > bracket_min:
                    taxable_amount = min(remaining_salary, bracket_max - bracket_min)
                    bracket_tax = taxable_amount * tax_rate
                    total_tax += bracket_tax
                    remaining_salary -= taxable_amount
            
            return round(total_tax, 2)
            
        except Exception as e:
            print(f"Error calculating tax deduction: {str(e)}")
            return gross_salary * 0.1  # 10% fallback
    
    @staticmethod
    def generate_payroll_summary(payroll_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from payroll records"""
        try:
            if not payroll_records:
                return {
                    'total_records': 0,
                    'total_gross': 0.0,
                    'total_deductions': 0.0,
                    'total_net': 0.0,
                    'average_salary': 0.0
                }
            
            total_gross = sum(record.get('basic_salary', 0) + record.get('allowances', 0) 
                            for record in payroll_records)
            total_deductions = sum(record.get('deductions', 0) for record in payroll_records)
            total_net = sum(record.get('net_salary', 0) for record in payroll_records)
            
            return {
                'total_records': len(payroll_records),
                'total_gross': round(total_gross, 2),
                'total_deductions': round(total_deductions, 2),
                'total_net': round(total_net, 2),
                'average_salary': round(total_net / len(payroll_records), 2),
                'highest_salary': max(record.get('net_salary', 0) for record in payroll_records),
                'lowest_salary': min(record.get('net_salary', 0) for record in payroll_records)
            }
            
        except Exception as e:
            print(f"Error generating payroll summary: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def validate_payroll_data(payroll_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payroll data for consistency"""
        errors = []
        warnings = []
        
        try:
            basic_salary = payroll_data.get('basic_salary', 0)
            allowances = payroll_data.get('allowances', 0)
            deductions = payroll_data.get('deductions', 0)
            net_salary = payroll_data.get('net_salary', 0)
            
            # Basic validation
            if basic_salary <= 0:
                errors.append("Basic salary must be greater than 0")
            
            if allowances < 0:
                errors.append("Allowances cannot be negative")
            
            if deductions < 0:
                errors.append("Deductions cannot be negative")
            
            # Calculate expected net salary
            expected_gross = basic_salary + allowances
            expected_net = expected_gross - deductions
            
            # Check if net salary matches calculation
            if abs(net_salary - expected_net) > 0.01:  # Allow for rounding differences
                warnings.append(f"Net salary ({net_salary}) doesn't match calculation ({expected_net})")
            
            # Check for unreasonable values
            if deductions > expected_gross:
                errors.append("Total deductions cannot exceed gross salary")
            
            if basic_salary > 1000000:  # Arbitrary high threshold
                warnings.append("Basic salary seems unusually high")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }