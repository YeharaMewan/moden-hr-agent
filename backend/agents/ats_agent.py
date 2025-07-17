# backend/agents/ats_agent.py (Enhanced for LangGraph)
from agents.base_agent import BaseAgent
from models.candidate import Candidate
from tools.rag_tools import CompanyDocumentRAG
from typing import Dict, Any, List, Tuple
import json
import re
from datetime import datetime

class ATSAgent(BaseAgent):
    """
    Enhanced ATS (Applicant Tracking System) Agent with intelligent candidate search
    """
    
    def __init__(self, gemini_api_key: str, db_connection, memory_manager):
        super().__init__(gemini_api_key, db_connection, memory_manager)
        self.candidate_model = Candidate(db_connection)
        self.rag_system = CompanyDocumentRAG(db_connection, gemini_api_key)
        
        # ATS-specific prompt templates
        self.prompt_templates.update({
            'candidate_understanding': """
            Analyze this candidate search request from HR user:
            Message: "{message}"
            HR Context: {hr_context}
            
            Extract (respond in JSON only):
            {{
                "intent": "candidate_search|candidate_details|candidate_ranking|candidate_analysis",
                "entities": {{
                    "skills": ["list of technical skills"],
                    "position": "job position",
                    "experience_level": "junior|mid|senior|lead",
                    "department": "IT|HR|Finance|Marketing",
                    "education": "degree requirements",
                    "specific_name": "candidate name if searching for specific person",
                    "location": "work location",
                    "contract_type": "full-time|part-time|contract",
                    "years_experience": "number of years",
                    "certifications": ["list of certifications"]
                }},
                "confidence": 0.0-1.0,
                "search_type": "skill_based|position_based|name_based|experience_based",
                "urgency": "low|medium|high",
                "language": "english|sinhala|mixed"
            }}
            
            Examples:
            "Find Java developers" → {{"intent": "candidate_search", "entities": {{"skills": ["java"]}}, "search_type": "skill_based"}}
            "Show me senior React developers" → {{"intent": "candidate_search", "entities": {{"skills": ["react"], "experience_level": "senior"}}}}
            "මට java දන්නා candidates ලා ලබාදෙන්න" → {{"intent": "candidate_search", "entities": {{"skills": ["java"]}}, "language": "sinhala"}}
            """,
            
            'candidate_response': """
            Generate a professional HR response for candidate search:
            
            Query: "{message}"
            Search Results: {search_results}
            Match Quality: {match_quality}
            Total Candidates: {total_count}
            
            Guidelines:
            - Act like an intelligent HR assistant
            - Summarize top candidates with key highlights
            - Mention specific skills and experience
            - Provide actionable insights
            - Support both English and Sinhala
            - Use emojis for better UX
            - Keep under 400 words
            
            Format as conversational HR response, not just data listing.
            """
        })
        
        # Available tools for ATS operations
        self.available_tools = [
            'search_candidates',
            'filter_candidates',
            'rank_candidates',
            'get_candidate_details',
            'analyze_candidate_fit',
            'generate_candidate_summary',
            'check_candidate_availability',
            'extract_cv_skills'
        ]
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Streamlined ATS request processing using combined entity extraction.
        """
        try:
            intent = request_data.get('intent')
            message = request_data.get('message')
            user_context = request_data.get('user_context', {})

            entities = self._enhance_candidate_entities(message)
            understanding = {'intent': intent, 'entities': entities}

            print(f"👥 ATS Agent processing intent '{intent}' with entities: {entities}")

            # New "list all" check
            if entities.get('list_all'):
                print("📋 Listing all candidates. Routing to get_all_candidates handler.")
                return self._handle_get_all_candidates(message, understanding, user_context)

            # If a specific name is found, route to details handler
            if 'candidate_name' in entities:
                print(f"👤 Name entity found: '{entities['candidate_name']}'. Routing to details handler.")
                return self._handle_candidate_details(message, understanding, user_context)
            
            # If any search criteria (skills or position) are found, route to the main search handler
            elif 'position' in entities or 'skills' in entities:
                print(f"🔍 Search entities found: {entities}. Routing to combined search handler.")
                return self._handle_combined_candidate_search(message, understanding, user_context)
            
            # Fallback for general queries
            else:
                print("🤔 No specific entities found. Routing to general query handler.")
                return self._handle_general_ats_query(message, understanding, user_context)
                
        except Exception as e:
            return self.format_error_response(f"Error processing ATS request: {str(e)}")
    
    def _handle_combined_candidate_search(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles candidate search using combined criteria (skills, position, etc.).
        """
        try:
            entities = understanding.get('entities', {})
            username = user_context.get('username', 'HR User')

            # Use the new combined search function in the candidate model
            candidates_found = self.candidate_model.search_candidates(entities)
            
            # This part remains the same: scoring and response generation
            for candidate in candidates_found:
                candidate['match_score'] = self._calculate_match_score(candidate, entities)
            
            candidates_found.sort(key=lambda x: x.get('match_score', 0), reverse=True)

            tool_results = {'candidates': candidates_found}
            
            response = self._generate_candidate_search_response(
                message, tool_results, entities, username
            )
            
            return self.format_success_response(response)
                
        except Exception as e:
            return self.format_error_response(f"Error during combined candidate search: {str(e)}")

    def _enhanced_candidate_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced candidate search understanding with context
        """
        try:
            # Use base understanding first
            base_understanding = self.understand_request(message, user_context)
            
            # Enhance with ATS-specific logic
            enhanced_understanding = self._enhance_candidate_entities(message, base_understanding)
            
            return enhanced_understanding
            
        except Exception as e:
            return {
                'intent': 'candidate_search',
                'entities': {},
                'confidence': 0.5,
                'error': str(e)
            }
    
    def _enhance_candidate_entities(self, message: str) -> Dict[str, Any]:
        """
        Extracts job positions, technical skills, and experience levels using regex patterns.
        It processes the entire message to find all relevant entities.
        """
        message_lower = message.lower()
        entities = {}

        # 1. Define keywords for all entities to search for
        job_positions = [
            'qa engineer', 'software engineer', 'business analyst', 'project manager',
            'frontend developer', 'backend developer', 'full stack developer', 'devops engineer',
            'data scientist', 'data analyst', 'ui/ux designer', 'hr coordinator',
            'digital marketing specialist', 'mobile application developer', 'developer', 'engineer'
        ]
        technical_skills = [
            'java', 'python', 'javascript', 'react', 'angular', 'nodejs', 'node.js', 'php', 'c#', 'c++',
            'spring', 'django', 'flask', 'express', 'laravel', 'mysql', 'postgresql', 'mongodb',
            'docker', 'kubernetes', 'aws', 'azure', 'git', 'jenkins', 'terraform', 'ansible',
            'flutter', 'dart', 'kotlin', 'swift', 'xcode', 'android',
            'ui/ux', 'ui', 'ux', 'figma', 'sketch', 'adobe xd',
            'selenium', 'cypress', 'postman', 'qa'
        ]
        experience_levels = ['junior', 'mid-level', 'mid level', 'senior', 'lead']

        # 2. Extract Job Positions from the message
        found_positions = [p for p in job_positions if re.search(r'\b' + re.escape(p) + r's?\b', message_lower)]
        if found_positions:
            entities['position'] = max(found_positions, key=len)

        # 3. Extract Technical Skills
        found_skills = []
        if 'ui/ux' in message_lower or 'ui ux' in message_lower:
            found_skills.append('ui/ux')
        for skill in technical_skills:
            if entities.get('position') and skill in entities['position']:
                continue
            if re.search(r'\b' + re.escape(skill) + r'\b', message_lower, re.IGNORECASE):
                found_skills.append(skill.replace('node.js', 'nodejs'))
        if found_skills:
            entities['skills'] = list(set(found_skills))

        # 4. Extract Experience Level
        for level in experience_levels:
            if re.search(r'\b' + re.escape(level) + r'\b', message_lower):
                entities['experience_level'] = level.replace('mid level', 'mid-level')
                break

        
        # 5. Check for "list all" intent or extract a name if NO other search entities were found
        if not entities:
            if re.search(r'\b(all|list|show me all|every)\b.*\b(candidate|applicant)s?\b', message_lower):
                entities['list_all'] = True
            else:
                name_patterns = [
                r'details of ([A-Z][a-z]+\s[A-Z][a-z]+)',      # "details of John Smith"
                r'cv for ([A-Z][a-z]+\s[A-Z][a-z]+)',         # "cv for Anura Fernando"
                r'give me ([A-Z][a-z]+\s[A-Z][a-z]+) candidate', # "give me Anura Fernando candidate"
                r'give me the ([A-Z][a-z]+\s[A-Z][a-z]+) cv details',
                r'give me the ([A-Z][a-z]+\s[A-Z][a-z]+) cv information',
                r'([A-Z][a-z]+\s[A-Z][a-z]+) ගෙ cv',         # "David Fernando ගෙ cv"
                r'([A-Z][a-z]+\s[A-Z][a-z]+)'                 # "Anura Fernando" (as a fallback)
            ]
                for pattern in name_patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        # Avoid matching generic phrases like "give me"
                        candidate_name = match.group(1).strip()
                        if candidate_name.lower() not in ["give me", "show me", "find me"]:
                            entities['candidate_name'] = candidate_name
                            break

        return entities
    
    def _handle_candidate_search_by_position(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle candidate search by their job position.
        """
        try:
            entities = understanding.get('entities', {})
            position = entities.get('position')
            username = user_context.get('username', 'HR User')

            if not position:
                return self.format_error_response("Please specify a position to search for.")

            # Use the candidate model to search by position
            candidates_found = self.candidate_model.search_candidates_by_position(position)
            
            # Create a dummy tool_results to pass to the response generator
            tool_results = {'candidates': candidates_found}
            
            response = self._generate_candidate_search_response(
                message, tool_results, entities, username
            )
            
            return self.format_success_response(response)
                
        except Exception as e:
            return self.format_error_response(f"Error searching for position '{position}': {str(e)}")

    def _handle_candidate_search(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle candidate search with intelligent matching
        """
        try:
            entities = understanding.get('entities', {})
            username = user_context.get('username', 'HR User')
            
            # Execute tools to search candidates
            tool_results = self.execute_with_tools({
                'action': 'search_candidates',
                'entities': entities,
                'user_context': user_context
            }, ['search_candidates', 'rank_candidates', 'analyze_candidate_fit'])
            
            if tool_results.get('execution_success'):
                # Generate intelligent response
                response = self._generate_candidate_search_response(
                    message, tool_results, entities, username
                )
                
                return self.format_success_response(response)
            else:
                error_msg = tool_results.get('error', 'Failed to search candidates')
                return self.format_error_response(f"❌ Unable to search candidates: {error_msg}")
                
        except Exception as e:
            return self.format_error_response(f"Error searching candidates: {str(e)}")
    

    def _handle_get_all_candidates(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles a request to list all candidates in the system.
        """
        try:
            username = user_context.get('username', 'HR User')
            all_candidates = self.candidate_model.get_all_candidates()

            if not all_candidates:
                return self.format_success_response("No candidates found in the system yet. You can start by processing some CV files.")

            response = f"📋 **Found {len(all_candidates)} candidates in the system.**\n\nHere are the most recently added ones:"
            
            for i, candidate in enumerate(all_candidates[:10], 1): # Show top 10
                name = candidate.get('name', f'Candidate {i}')
                position = candidate.get('position_applied', 'Not specified')
                skills_text = ', '.join(candidate.get('skills', [])[:3]) if candidate.get('skills') else 'No skills listed'
                response += f"""
\n**{i}. {name}**
   - **Position:** {position}
   - **Top Skills:** {skills_text}...
   - **Contact:** {candidate.get('email', 'N/A')}"""

            if len(all_candidates) > 10:
                response += f"\n\n... and {len(all_candidates) - 10} more."
            
            response += "\n\nYou can ask for details about a specific candidate by name, like 'Show me details for John Smith'."
            
            return self.format_success_response(response)
        except Exception as e:
            return self.format_error_response(f"Error retrieving all candidates: {str(e)}")


    def _handle_candidate_details(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles requests for specific candidate details by name.
        """
        try:
            entities = understanding.get('entities', {})
            candidate_name = entities.get('candidate_name')
            
            if not candidate_name:
                return self.format_error_response("Please specify the candidate's name to get details.")
            
            # Use the candidate model to search by name
            candidates_found = self.candidate_model.search_candidates_by_name(candidate_name)
            
            if candidates_found:
                # Assuming the first result is the most relevant one
                # Create a dummy tool_results dictionary to pass to the response generator
                tool_results = {'candidate_details': candidates_found[0]}
                response = self._generate_candidate_details_response(tool_results, candidate_name)
                return self.format_success_response(response)
            else:
                return self.format_error_response(f"❌ Could not find details for a candidate named '{candidate_name}'. Please check the spelling or ensure the CV has been processed.")
                
        except Exception as e:
            return self.format_error_response(f"Error getting candidate details: {str(e)}")

    
    def _handle_candidate_ranking(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle candidate ranking and comparison requests
        """
        try:
            entities = understanding.get('entities', {})
            
            # Execute tools to rank candidates
            tool_results = self.execute_with_tools({
                'action': 'rank_candidates',
                'entities': entities,
                'user_context': user_context
            }, ['search_candidates', 'rank_candidates', 'analyze_candidate_fit'])
            
            if tool_results.get('execution_success'):
                response = self._generate_ranking_response(tool_results, entities)
                return self.format_success_response(response)
            else:
                return self.format_error_response("❌ Could not rank candidates at this time.")
                
        except Exception as e:
            return self.format_error_response(f"Error ranking candidates: {str(e)}")
    
    def _handle_general_ats_query(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle general ATS queries
        """
        try:
            username = user_context.get('username', 'HR User')
            
            response = f"""
👋 Hi {username}! I'm here to help you find the perfect candidates.

**What I can help you with:**
🔍 **Candidate Search:** "Find Java developers" or "Show me senior React candidates"
📊 **Candidate Analysis:** "Rank Python developers by experience"
👤 **Candidate Details:** "Tell me about John Doe's background"
📋 **Skill Matching:** "Find candidates with AWS and Docker experience"

**Search Examples:**
• "Find Java developers with 5+ years experience"
• "Show me frontend developers"
• "මට python දන්නා candidates ලා ලබාදෙන්න"
• "Find senior developers for mobile app project"

**Advanced Search:**
• Specify skills: "React, Node.js, MongoDB"
• Experience level: "Senior", "Mid-level", "Junior"
• Years of experience: "5+ years", "2-4 years"
• Position type: "Full-stack developer", "DevOps engineer"

How can I help you find the right talent today?"""
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error handling general query: {str(e)}")
    
    def _generate_candidate_search_response(self, message: str, tool_results: Dict[str, Any], 
                                          entities: Dict[str, Any], username: str) -> str:
        """
        Generate intelligent candidate search response. Handles searches by position, skills, or both.
        """
        candidates = tool_results.get('candidates', [])
        
        # Build a descriptive criteria string from all entities
        criteria_parts = []
        if entities.get('experience_level'):
            criteria_parts.append(entities['experience_level'].title())
        if entities.get('position'):
            criteria_parts.append(entities['position'].title())
        if entities.get('skills'):
            criteria_parts.append(f"with skills in {', '.join(entities['skills'])}")
        
        criteria = ' '.join(criteria_parts) or 'your criteria'

        if not candidates:
            return f"""
🔍 **Search Results for "{criteria}"**

❌ **No candidates found** matching your criteria.

**Suggestions:**
• Try broader search terms.
• Ensure CVs for matching candidates have been processed.
• Search for related skills or different job titles.
"""
        
        total_candidates = len(candidates)
        top_candidates = candidates[:3]
        
        # ******** නිවැරදි කිරීම මෙතනයි / THE FIX IS HERE ********
        # Define searched_skills from entities, defaulting to an empty list if not present.
        searched_skills = entities.get('skills', [])
        # **********************************************************

        response = f"""
🎯 **Found {total_candidates} candidate(s) matching "{criteria}"**

**🏆 Top Matches:**"""
        
        for i, candidate in enumerate(top_candidates, 1):
            name = candidate.get('name', f'Candidate {i}')
            
            # This logic now works safely because searched_skills is always defined.
            candidate_skills = candidate.get('skills', [])
            highlight_skills = [skill for skill in candidate_skills if skill in searched_skills]
            other_skills = [skill for skill in candidate_skills if skill not in searched_skills]
            display_skills = highlight_skills + other_skills
            skills_text = ', '.join(display_skills[:5]) if display_skills else 'No skills listed'

            experience = candidate.get('experience', 'N/A')
            match_score = candidate.get('match_score', 0)
            
            response += f"""

**{i}. {name}** ⭐ {match_score:.1f}/10
🛠️ **Skills:** {skills_text}
⏱️ **Experience:** {experience}
📧 **Contact:** {candidate.get('email', 'N/A')}
💡 **Highlights:** Strong match in {len(highlight_skills)} key skills"""
        
        if total_candidates > 3:
            response += f"\n\n📋 **+{total_candidates - 3} more candidates available**"
        
        response += f"""

**🎯 Search Summary:**
• **Total Matches:** {total_candidates}
• **Criteria:** {criteria}
• **Match Quality:** {'Excellent' if any(c.get('match_score', 0) > 8 for c in candidates) else 'Good'}

**💡 Next Steps:**
• "Tell me more about {top_candidates[0]['name']}" - Get detailed profile
• "Compare top 2 candidates"
"""
        
        return response
    
    def _generate_candidate_details_response(self, tool_results: Dict[str, Any], candidate_name: str) -> str:
        """
        Generate detailed candidate profile response
        """
        candidate = tool_results.get('candidate_details', {})
        
        if not candidate:
            return f"❌ Could not find detailed information for {candidate_name}."
        
        name = candidate.get('name', candidate_name)
        skills = candidate.get('skills', [])
        experience = candidate.get('experience_years', 'N/A')
        education = candidate.get('education', 'Not specified')
        
        response = f"""
👤 **Detailed Profile: {name}**

**🛠️ Technical Skills:**
{self._format_skills_section(skills)}

**💼 Professional Experience:**
• **Total Experience:** {experience} years
• **Current Role:** {candidate.get('current_role', 'Not specified')}
• **Previous Companies:** {', '.join(candidate.get('previous_companies', ['Not specified']))}

**🎓 Education:**
• **Degree:** {education}
• **Institution:** {candidate.get('institution', 'Not specified')}
• **Graduation Year:** {candidate.get('graduation_year', 'Not specified')}

**📞 Contact Information:**
• **Email:** {candidate.get('email', 'Available on request')}
• **Phone:** {candidate.get('phone', 'Available on request')}
• **Location:** {candidate.get('location', 'Not specified')}

**🎯 Assessment:**
• **Overall Fit:** {candidate.get('overall_fit', 'Good')}
• **Strengths:** {candidate.get('strengths', 'Strong technical background')}
• **Experience Level:** {candidate.get('seniority_level', 'Mid-level')}

**📋 Additional Notes:**
{candidate.get('summary', 'Professional candidate with relevant experience.')}

**💡 HR Actions:**
• Schedule phone screening
• Request portfolio/code samples
• Check references
• Arrange technical interview

Would you like me to help with next steps for this candidate?"""
        
        return response
    
    def _generate_ranking_response(self, tool_results: Dict[str, Any], entities: Dict[str, Any]) -> str:
        """
        Generate candidate ranking response
        """
        ranked_candidates = tool_results.get('ranked_candidates', [])
        criteria = entities.get('skills', []) + [entities.get('position', '')]
        criteria = [item for item in criteria if item]
        
        response = f"""
📊 **Candidate Ranking for "{' '.join(criteria)}"**

**🏆 Top Candidates (Ranked by fit):**"""
        
        for i, candidate in enumerate(ranked_candidates[:5], 1):
            name = candidate.get('name', f'Candidate {i}')
            score = candidate.get('ranking_score', 0)
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            response += f"""

{rank_emoji} **{name}** - Score: {score:.1f}/10
• **Key Strengths:** {candidate.get('key_strengths', 'Strong technical skills')}
• **Experience:** {candidate.get('experience_years', 'N/A')} years
• **Best Fit For:** {candidate.get('best_fit_role', 'Development role')}"""
        
        response += f"""

**📈 Ranking Criteria:**
• Technical skill match
• Experience level alignment
• Educational background
• Previous project relevance
• Overall profile completeness

**🎯 Recommendations:**
• **Top Pick:** Focus on candidate #1 for immediate interview
• **Backup Options:** Candidates #2-3 are strong alternatives
• **Consider:** Review candidates #4-5 if top choices decline

**📋 Next Actions:**
• "Interview top 3 candidates"
• "Compare [name1] vs [name2]"
• "Schedule screening calls"

Would you like me to help arrange interviews with the top candidates?"""
        
        return response
    
    def _format_skills_section(self, skills: List[str]) -> str:
        """
        Format skills section with categories
        """
        if not skills:
            return "• No specific skills listed"
        
        # Categorize skills (simplified)
        programming_langs = [s for s in skills if s.lower() in ['java', 'python', 'javascript', 'c++', 'c#', 'php']]
        frameworks = [s for s in skills if s.lower() in ['react', 'angular', 'spring', 'django', 'express']]
        databases = [s for s in skills if s.lower() in ['mysql', 'postgresql', 'mongodb', 'oracle']]
        cloud_tools = [s for s in skills if s.lower() in ['aws', 'azure', 'docker', 'kubernetes']]
        other_skills = [s for s in skills if s.lower() not in [*programming_langs, *frameworks, *databases, *cloud_tools]]
        
        formatted = ""
        if programming_langs:
            formatted += f"• **Programming:** {', '.join(programming_langs)}\n"
        if frameworks:
            formatted += f"• **Frameworks:** {', '.join(frameworks)}\n"
        if databases:
            formatted += f"• **Databases:** {', '.join(databases)}\n"
        if cloud_tools:
            formatted += f"• **Cloud/DevOps:** {', '.join(cloud_tools)}\n"
        if other_skills:
            formatted += f"• **Other:** {', '.join(other_skills)}\n"
        
        return formatted.strip()
    
    def execute_with_tools(self, request_data: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        Execute ATS-specific tools
        """
        tool_responses = []
        execution_success = True
        result_data = {}
        
        try:
            action = request_data.get('action')
            entities = request_data.get('entities', {})
            user_context = request_data.get('user_context', {})
            
            if action == 'search_candidates':
                # Tool 1: Search candidates
                if 'search_candidates' in available_tools:
                    search_results = self._search_candidates_db(entities)
                    tool_responses.append({'tool': 'search_candidates', 'result': search_results})
                    result_data['candidates'] = search_results.get('candidates', [])
                
                # Tool 2: Rank candidates
                if 'rank_candidates' in available_tools and result_data.get('candidates'):
                    ranked_candidates = self._rank_candidates(result_data['candidates'], entities)
                    tool_responses.append({'tool': 'rank_candidates', 'result': ranked_candidates})
                    result_data['candidates'] = ranked_candidates.get('ranked_candidates', [])
                
                # Tool 3: Analyze fit
                if 'analyze_candidate_fit' in available_tools and result_data.get('candidates'):
                    for candidate in result_data['candidates'][:3]:  # Analyze top 3
                        fit_analysis = self._analyze_candidate_fit(candidate, entities)
                        candidate.update(fit_analysis)
            
            elif action == 'get_candidate_details':
                candidate_name = request_data.get('candidate_name')
                if 'get_candidate_details' in available_tools:
                    details = self._get_candidate_details(candidate_name)
                    tool_responses.append({'tool': 'get_candidate_details', 'result': details})
                    result_data['candidate_details'] = details
            
            elif action == 'rank_candidates':
                # First search, then rank
                if 'search_candidates' in available_tools:
                    search_results = self._search_candidates_db(entities)
                    candidates = search_results.get('candidates', [])
                    
                    if 'rank_candidates' in available_tools:
                        ranked_results = self._rank_candidates(candidates, entities)
                        result_data['ranked_candidates'] = ranked_results.get('ranked_candidates', [])
            
        except Exception as e:
            execution_success = False
            result_data['error'] = str(e)
        
        return {
            'tool_responses': tool_responses,
            'execution_success': execution_success,
            'requires_human_approval': False,  # ATS operations generally don't need approval
            **result_data
        }
    
    # Tool implementation methods
    def _search_candidates_db(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Searches candidates by SKILLS. Returns an empty list if no skills are provided.
        """
        try:
            skills_to_search = entities.get('skills')
            candidates = []

            if skills_to_search:
                print(f"🔍 Searching database for candidates with skills: {skills_to_search}")
                candidates = self.candidate_model.search_candidates_by_skills(skills_to_search)
            else:
                # IMPORTANT: If no skills are in the query, return no results.
                # This prevents showing all candidates for queries like "Find candidates".
                print("⚠️ No skills provided to search. Returning 0 candidates.")
                return {'success': True, 'candidates': [], 'total_count': 0}

            for candidate in candidates:
                candidate['match_score'] = self._calculate_match_score(candidate, entities)
            
            candidates.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            return {
                'success': True,
                'candidates': candidates,
                'total_count': len(candidates)
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Search error: {str(e)}', 'candidates': []}
    
    def _rank_candidates(self, candidates: List[Dict[str, Any]], entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rank candidates based on criteria
        """
        try:
            for candidate in candidates:
                # Calculate comprehensive ranking score
                ranking_score = self._calculate_ranking_score(candidate, entities)
                candidate['ranking_score'] = ranking_score
                
                # Add ranking insights
                candidate['key_strengths'] = self._identify_key_strengths(candidate, entities)
                candidate['best_fit_role'] = self._suggest_best_fit_role(candidate)
            
            # Sort by ranking score
            ranked_candidates = sorted(candidates, key=lambda x: x.get('ranking_score', 0), reverse=True)
            
            return {
                'success': True,
                'ranked_candidates': ranked_candidates
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ranked_candidates': candidates
            }
    
    def _analyze_candidate_fit(self, candidate: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how well a candidate fits the requirements
        """
        try:
            candidate_skills = set(candidate.get('skills', []))
            required_skills = set(entities.get('skills', []))
            
            # Calculate fit metrics
            skill_match = len(candidate_skills.intersection(required_skills)) / max(len(required_skills), 1)
            
            # Experience fit
            exp_fit = 1.0
            if entities.get('years_experience'):
                candidate_exp = candidate.get('experience_years', 0)
                required_exp = entities.get('years_experience')
                exp_fit = min(candidate_exp / required_exp, 1.0) if required_exp > 0 else 1.0
            
            # Overall fit score
            overall_fit = (skill_match * 0.6) + (exp_fit * 0.4)
            
            return {
                'skill_match_percentage': skill_match * 100,
                'experience_fit': exp_fit * 100,
                'overall_fit_score': overall_fit * 100,
                'highlights': f"Strong match in {len(candidate_skills.intersection(required_skills))} key skills"
            }
            
        except Exception as e:
            return {
                'overall_fit_score': 50,
                'error': str(e)
            }
    
    def _get_candidate_details(self, candidate_name: str) -> Dict[str, Any]:
        """
        Get detailed candidate information
        """
        try:
            # Search for candidate by name
            candidate = self.candidate_model.get_candidate_by_name(candidate_name)
            
            if candidate:
                # Enhance with additional details
                candidate['summary'] = self._generate_candidate_summary(candidate)
                candidate['strengths'] = self._identify_candidate_strengths(candidate)
                return candidate
            else:
                return {}
                
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_match_score(self, candidate: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """
        Calculate match score between candidate and requirements
        """
        try:
            score = 0.0
            
            # Skill matching (40% weight)
            candidate_skills = set(skill.lower() for skill in candidate.get('skills', []))
            required_skills = set(skill.lower() for skill in entities.get('skills', []))
            
            if required_skills:
                skill_match = len(candidate_skills.intersection(required_skills)) / len(required_skills)
                score += skill_match * 4.0
            else:
                score += 2.0  # Default if no specific skills required
            
            # Experience matching (30% weight)
            if entities.get('years_experience'):
                candidate_exp = candidate.get('experience_years', 0)
                required_exp = entities.get('years_experience')
                if candidate_exp >= required_exp:
                    score += 3.0
                elif candidate_exp >= required_exp * 0.8:
                    score += 2.0
                else:
                    score += 1.0
            else:
                score += 2.0
            
            # Education matching (20% weight)
            if candidate.get('education'):
                score += 2.0
            else:
                score += 1.0
            
            # Profile completeness (10% weight)
            completeness = len([f for f in ['name', 'email', 'skills', 'experience_years'] 
                              if candidate.get(f)]) / 4
            score += completeness * 1.0
            
            return min(score, 10.0)  # Cap at 10
            
        except Exception as e:
            return 5.0  # Default score
    
    def _calculate_ranking_score(self, candidate: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """
        Calculate comprehensive ranking score
        """
        # Use match score as base, can be enhanced with additional criteria
        return self._calculate_match_score(candidate, entities)
    
    def _identify_key_strengths(self, candidate: Dict[str, Any], entities: Dict[str, Any]) -> str:
        """
        Identify key strengths of a candidate
        """
        strengths = []
        
        skills = candidate.get('skills', [])
        required_skills = entities.get('skills', [])
        
        # Skill-based strengths
        matching_skills = [s for s in skills if s.lower() in [rs.lower() for rs in required_skills]]
        if matching_skills:
            strengths.append(f"Expert in {', '.join(matching_skills[:3])}")
        
        # Experience-based strengths
        exp_years = candidate.get('experience_years', 0)
        if exp_years >= 5:
            strengths.append("Senior-level experience")
        elif exp_years >= 2:
            strengths.append("Solid mid-level experience")
        
        # Education strengths
        if candidate.get('education'):
            strengths.append("Strong educational background")
        
        return ', '.join(strengths) if strengths else "Well-rounded technical profile"
    
    def _suggest_best_fit_role(self, candidate: Dict[str, Any]) -> str:
        """
        Suggest best fit role for candidate
        """
        skills = [s.lower() for s in candidate.get('skills', [])]
        
        if any(skill in skills for skill in ['react', 'angular', 'vue', 'html', 'css']):
            return "Frontend Developer"
        elif any(skill in skills for skill in ['node', 'django', 'spring', 'express']):
            return "Backend Developer"
        elif any(skill in skills for skill in ['aws', 'docker', 'kubernetes', 'jenkins']):
            return "DevOps Engineer"
        elif any(skill in skills for skill in ['java', 'python', 'javascript']):
            return "Full-stack Developer"
        else:
            return "Software Developer"
    
    def _generate_candidate_summary(self, candidate: Dict[str, Any]) -> str:
        """
        Generate candidate summary
        """
        name = candidate.get('name', 'Candidate')
        experience = candidate.get('experience_years', 0)
        skills = candidate.get('skills', [])
        
        return f"{name} is a {'senior' if experience >= 5 else 'mid-level' if experience >= 2 else 'junior'} professional with {experience} years of experience in {', '.join(skills[:3])}."
    
    def _identify_candidate_strengths(self, candidate: Dict[str, Any]) -> str:
        """
        Identify candidate strengths
        """
        skills = candidate.get('skills', [])
        experience = candidate.get('experience_years', 0)
        
        strengths = []
        if experience >= 5:
            strengths.append("Extensive experience")
        if len(skills) >= 5:
            strengths.append("Diverse technical skillset")
        if candidate.get('education'):
            strengths.append("Strong educational foundation")
        
        return ', '.join(strengths) if strengths else "Technical competency"
    
    def format_response(self, response_data: Dict[str, Any]) -> str:
        """
        Format response for the user
        """
        try:
            if response_data.get('error'):
                return f"❌ Error: {response_data['error']}"
            
            return response_data.get('response', 'Candidate search completed successfully.')
            
        except Exception as e:
            return f"Error formatting response: {str(e)}"