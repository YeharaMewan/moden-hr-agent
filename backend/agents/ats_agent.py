# backend/agents/ats_agent.py
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
                    "contract_type": "full-time|part-time|contract"
                }},
                "confidence": 0.0-1.0,
                "search_type": "skill_based|position_based|name_based|experience_based",
                "urgency": "low|medium|high"
            }}
            
            Examples:
            "Find Java developers" → {{"intent": "candidate_search", "entities": {{"skills": ["java"]}}, "search_type": "skill_based"}}
            "Show me senior React developers" → {{"intent": "candidate_search", "entities": {{"skills": ["react"], "experience_level": "senior"}}}}
            """,
            
            'candidate_response': """
            Generate a professional HR response for candidate search:
            
            Query: "{message}"
            Search Results: {search_results}
            Match Quality: {match_quality}
            Total Candidates: {total_count}
            
            Guidelines:
            - Present results in a professional, scannable format
            - Highlight key qualifications and match scores
            - Include actionable next steps
            - Use emojis sparingly but appropriately
            - Keep response under 400 words
            - Focus on business value and hiring insights
            """
        })
        
        # Available tools for ATS operations
        self.available_tools = [
            'search_candidates_semantic',
            'analyze_candidate_fit',
            'get_candidate_details',
            'rank_candidates_by_criteria',
            'generate_candidate_summary',
            'check_candidate_availability'
        ]
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced ATS request processing with intelligent search"""
        try:
            # Permission check - only HR can access ATS
            user_context = request_data.get('user_context', {})
            if user_context.get('role') != 'hr':
                return self.format_error_response(
                    "❌ Access Denied: ATS functionality is restricted to HR personnel only."
                )
            
            # Extract request components
            intent = request_data.get('intent', 'candidate_search')
            message = request_data.get('message', '')
            entities = request_data.get('entities', {})
            
            # Enhanced understanding for ATS requests
            understanding = self._enhanced_ats_understanding(message, user_context)
            
            # Merge entities
            understanding['entities'].update(entities)
            
            # Route to appropriate handler
            if understanding['intent'] == 'candidate_search':
                return self._handle_candidate_search(message, understanding, user_context)
            elif understanding['intent'] == 'candidate_details':
                return self._handle_candidate_details(message, understanding, user_context)
            elif understanding['intent'] == 'candidate_ranking':
                return self._handle_candidate_ranking(message, understanding, user_context)
            elif understanding['intent'] == 'candidate_analysis':
                return self._handle_candidate_analysis(message, understanding, user_context)
            else:
                return self._handle_candidate_search(message, understanding, user_context)
                
        except Exception as e:
            return self.format_error_response(f"Error processing ATS request: {str(e)}")
    
    def _enhanced_ats_understanding(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced understanding specifically for ATS requests"""
        
        # Get ATS-specific memory context
        memory_context = self._get_ats_memory_context(user_context.get('user_id'))
        
        # Build enhanced prompt
        prompt = self.prompt_templates['candidate_understanding'].format(
            message=message,
            hr_context=json.dumps(memory_context, default=str)[:200]
        )
        
        # Generate understanding
        response = self.generate_response(prompt)
        
        # Parse with fallback
        try:
            understanding = json.loads(response.strip())
        except:
            understanding = self._fallback_ats_understanding(message)
        
        return understanding
    
    def _fallback_ats_understanding(self, message: str) -> Dict[str, Any]:
        """Fallback ATS understanding using pattern matching"""
        message_lower = message.lower()
        
        # Intent detection
        if any(word in message_lower for word in ['details of', 'show me candidate', 'candidate profile']):
            intent = 'candidate_details'
        elif any(word in message_lower for word in ['rank', 'best', 'top', 'compare']):
            intent = 'candidate_ranking'
        elif any(word in message_lower for word in ['analyze', 'analysis', 'evaluate']):
            intent = 'candidate_analysis'
        else:
            intent = 'candidate_search'
        
        # Extract entities
        entities = {}
        
        # Extract skills
        common_skills = [
            'java', 'python', 'javascript', 'react', 'angular', 'nodejs', 'spring', 'django',
            'php', 'c++', 'c#', '.net', 'mysql', 'mongodb', 'postgresql', 'aws', 'azure',
            'docker', 'kubernetes', 'git', 'html', 'css', 'bootstrap', 'vue', 'laravel'
        ]
        
        found_skills = [skill for skill in common_skills if skill in message_lower]
        if found_skills:
            entities['skills'] = found_skills
        
        # Extract positions
        positions = ['developer', 'engineer', 'manager', 'analyst', 'designer', 'architect', 'lead', 'coordinator']
        for position in positions:
            if position in message_lower:
                entities['position'] = position
                break
        
        # Extract experience level
        if any(word in message_lower for word in ['senior', 'sr', 'experienced', 'lead']):
            entities['experience_level'] = 'senior'
        elif any(word in message_lower for word in ['junior', 'jr', 'entry', 'fresher', 'beginner']):
            entities['experience_level'] = 'junior'
        elif any(word in message_lower for word in ['mid', 'intermediate', 'middle']):
            entities['experience_level'] = 'mid'
        
        # Extract departments
        departments = ['it', 'hr', 'finance', 'marketing', 'sales', 'engineering', 'operations']
        for dept in departments:
            if dept in message_lower:
                entities['department'] = dept
                break
        
        # Determine search type
        if entities.get('skills'):
            search_type = 'skill_based'
        elif entities.get('position'):
            search_type = 'position_based'
        elif entities.get('experience_level'):
            search_type = 'experience_based'
        else:
            search_type = 'general'
        
        return {
            'intent': intent,
            'entities': entities,
            'confidence': 0.7,
            'search_type': search_type,
            'urgency': 'medium'
        }
    
    def _get_ats_memory_context(self, user_id: str) -> Dict[str, Any]:
        """Get ATS-specific memory context"""
        if not user_id:
            return {}
        
        try:
            # Get recent ATS searches
            recent_context = self.memory_manager.short_term.get_conversation_history(user_id, limit=3)
            ats_interactions = [ctx for ctx in recent_context if 'candidate' in str(ctx).lower() or 'search' in str(ctx).lower()]
            
            # Get search patterns
            search_patterns = self.memory_manager.long_term.get_interaction_patterns(
                user_id, pattern_type='candidate_search', days_back=30
            )
            
            return {
                'recent_ats_searches': ats_interactions,
                'search_patterns': search_patterns[:2],
                'hr_preferences': self._get_hr_search_preferences(user_id)
            }
        except:
            return {}
    
    def _get_hr_search_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get HR user's search preferences from history"""
        try:
            # Analyze past search patterns
            successful_searches = self.memory_manager.long_term.get_successful_interactions(
                user_id, interaction_type='candidate_search', limit=10
            )
            
            if not successful_searches:
                return {}
            
            # Extract common search criteria
            common_skills = []
            common_positions = []
            
            for search in successful_searches:
                details = search.get('details', {})
                entities = details.get('entities', {})
                
                if entities.get('skills'):
                    common_skills.extend(entities['skills'])
                if entities.get('position'):
                    common_positions.append(entities['position'])
            
            # Get most frequent
            most_searched_skills = list(set(common_skills))[:5]
            most_searched_position = max(set(common_positions), key=common_positions.count) if common_positions else None
            
            return {
                'preferred_skills': most_searched_skills,
                'preferred_position': most_searched_position,
                'search_frequency': len(successful_searches)
            }
        except:
            return {}
    
    def _handle_candidate_search(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle candidate search with intelligent matching"""
        try:
            entities = understanding.get('entities', {})
            search_type = understanding.get('search_type', 'general')
            
            # Execute semantic search using tools
            tool_results = self.execute_with_tools({
                'action': 'semantic_candidate_search',
                'entities': entities,
                'search_type': search_type,
                'user_context': user_context
            }, ['search_candidates_semantic', 'rank_candidates_by_criteria'])
            
            if not tool_results.get('execution_success'):
                return self.format_error_response(f"Search failed: {tool_results.get('error', 'Unknown error')}")
            
            candidates = tool_results.get('candidates', [])
            total_count = tool_results.get('total_count', 0)
            
            if not candidates:
                return self._handle_no_candidates_found(entities, search_type)
            
            # Generate professional response
            response = self._generate_candidate_search_response(
                candidates, entities, total_count, search_type
            )
            
            return self.format_success_response(
                response,
                requires_action=False,
                action_data={
                    'search_results': candidates[:3],  # Top 3 for follow-up
                    'total_count': total_count,
                    'search_type': search_type
                }
            )
            
        except Exception as e:
            return self.format_error_response(f"Error in candidate search: {str(e)}")
    
    def _handle_no_candidates_found(self, entities: Dict[str, Any], search_type: str) -> Dict[str, Any]:
        """Handle case when no candidates are found"""
        
        skills = entities.get('skills', [])
        position = entities.get('position', '')
        experience_level = entities.get('experience_level', '')
        
        response = "🔍 **No Candidates Found**\n\n"
        response += f"I couldn't find any candidates matching your criteria:\n"
        
        if skills:
            response += f"• **Skills**: {', '.join(skills)}\n"
        if position:
            response += f"• **Position**: {position}\n"
        if experience_level:
            response += f"• **Experience**: {experience_level}\n"
        
        response += "\n**Suggestions:**\n"
        response += "🔧 Try broadening your search criteria\n"
        response += "📚 Search for related skills (e.g., 'Python' instead of 'Django')\n"
        response += "🎯 Remove experience level filters\n"
        response += "📁 Check if new CVs need to be processed\n"
        
        response += "\n**Alternative searches:**\n"
        if skills:
            alternative_skills = self._get_alternative_skills(skills[0])
            response += f"• \"Find {alternative_skills} developers\"\n"
        
        response += "• \"Show me all software developers\"\n"
        response += "• \"Find candidates with any programming experience\"\n"
        
        return self.format_success_response(response)
    
    def _get_alternative_skills(self, skill: str) -> str:
        """Get alternative skills for suggestions"""
        skill_alternatives = {
            'java': 'Spring or Kotlin',
            'python': 'Django or Flask',
            'javascript': 'React or Node.js',
            'react': 'Vue or Angular',
            'angular': 'React or Vue',
            'php': 'Laravel or Symfony',
            'c#': '.NET or ASP.NET',
            'mysql': 'PostgreSQL or MongoDB'
        }
        
        return skill_alternatives.get(skill.lower(), f'related {skill}')
    
    def _generate_candidate_search_response(self, candidates: List[Dict], entities: Dict[str, Any], 
                                          total_count: int, search_type: str) -> str:
        """Generate professional candidate search response"""
        
        skills = entities.get('skills', [])
        position = entities.get('position', '')
        
        # Header
        response = f"🔍 **Candidate Search Results**\n\n"
        
        if skills:
            response += f"**Searching for:** {', '.join(skills).title()}"
            if position:
                response += f" {position.title()}"
            response += f" • **Found:** {total_count} candidates\n\n"
        
        # Display top candidates
        response += "**Top Matches:**\n\n"
        
        for i, candidate in enumerate(candidates[:5], 1):
            match_score = candidate.get('match_score', 0.5)
            match_percentage = f"{match_score * 100:.0f}%"
            
            response += f"**{i}. {candidate.get('name', 'Unknown Candidate')}** ({match_percentage} match)\n"
            response += f"   📧 {candidate.get('email', 'N/A')}\n"
            response += f"   💼 {candidate.get('position_applied', 'N/A')}\n"
            
            # Show relevant skills
            candidate_skills = candidate.get('skills', [])
            relevant_skills = []
            
            if skills:
                # Show matching skills first
                for skill in skills:
                    matching = [s for s in candidate_skills if skill.lower() in s.lower()]
                    relevant_skills.extend(matching)
                
                # Add other skills up to 5 total
                other_skills = [s for s in candidate_skills if s not in relevant_skills]
                relevant_skills.extend(other_skills[:5-len(relevant_skills)])
            else:
                relevant_skills = candidate_skills[:5]
            
            if relevant_skills:
                response += f"   🛠️ **Skills**: {', '.join(relevant_skills[:5])}\n"
            
            # Show experience or education if available
            experience = candidate.get('experience', '')
            if experience and len(experience) < 100:
                response += f"   📈 **Experience**: {experience[:80]}{'...' if len(experience) > 80 else ''}\n"
            
            response += f"   📅 **Applied**: {candidate.get('created_at', 'Recently')}\n"
            response += "\n"
        
        # Show summary if more candidates available
        if total_count > 5:
            response += f"➕ **{total_count - 5} more candidates available**\n\n"
        
        # Action suggestions
        response += "**Next Steps:**\n"
        response += "📋 Get details: \"Show me details for [candidate name]\"\n"
        response += "📊 Compare candidates: \"Rank these candidates by experience\"\n"
        response += "🎯 Refine search: \"Find senior React developers with 5+ years\"\n"
        response += "📞 Schedule interviews: \"Contact top 3 candidates\"\n"
        
        # Add insights if available
        if total_count > 0:
            response += f"\n💡 **Insights:**\n"
            response += f"• Average match score: {self._calculate_average_match_score(candidates):.0f}%\n"
            
            # Skill distribution
            all_skills = []
            for candidate in candidates:
                all_skills.extend(candidate.get('skills', []))
            
            if all_skills:
                top_skills = self._get_top_skills(all_skills, 3)
                response += f"• Most common skills: {', '.join(top_skills)}\n"
        
        return response
    
    def _calculate_average_match_score(self, candidates: List[Dict]) -> float:
        """Calculate average match score"""
        if not candidates:
            return 0
        
        scores = [c.get('match_score', 0.5) for c in candidates]
        return (sum(scores) / len(scores)) * 100
    
    def _get_top_skills(self, all_skills: List[str], top_n: int = 3) -> List[str]:
        """Get most common skills from candidates"""
        skill_counts = {}
        for skill in all_skills:
            skill_lower = skill.lower()
            skill_counts[skill_lower] = skill_counts.get(skill_lower, 0) + 1
        
        # Sort by frequency and return top N
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        return [skill for skill, count in sorted_skills[:top_n]]
    
    def _handle_candidate_details(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detailed candidate information requests"""
        try:
            entities = understanding.get('entities', {})
            candidate_name = entities.get('specific_name', '')
            
            # Extract candidate name from message if not in entities
            if not candidate_name:
                candidate_name = self._extract_candidate_name_from_message(message)
            
            if not candidate_name:
                return self.format_error_response(
                    "❌ Please specify which candidate you'd like details for.\nExample: \"Show me details for John Doe\""
                )
            
            # Execute tools to get candidate details
            tool_results = self.execute_with_tools({
                'action': 'get_candidate_details',
                'candidate_name': candidate_name,
                'user_context': user_context
            }, ['get_candidate_details', 'analyze_candidate_fit'])
            
            if not tool_results.get('execution_success'):
                return self.format_error_response(f"Could not find candidate: {candidate_name}")
            
            candidate = tool_results.get('candidate_details', {})
            fit_analysis = tool_results.get('fit_analysis', {})
            
            response = self._generate_candidate_details_response(candidate, fit_analysis)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error getting candidate details: {str(e)}")
    
    def _extract_candidate_name_from_message(self, message: str) -> str:
        """Extract candidate name from message"""
        # Look for patterns like "details for John Doe", "show me John Smith"
        patterns = [
            r'details?\s+for\s+([A-Za-z\s]+)',
            r'show\s+me\s+([A-Za-z\s]+)',
            r'about\s+([A-Za-z\s]+)',
            r'candidate\s+([A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Remove common words
                exclude_words = ['candidate', 'details', 'information', 'profile', 'the', 'of']
                name_parts = [word for word in name.split() if word.lower() not in exclude_words]
                if len(name_parts) >= 2:  # At least first and last name
                    return ' '.join(name_parts)
        
        return ''
    
    def _generate_candidate_details_response(self, candidate: Dict[str, Any], fit_analysis: Dict[str, Any]) -> str:
        """Generate detailed candidate profile response"""
        
        name = candidate.get('name', 'Unknown Candidate')
        
        response = f"👤 **Candidate Profile: {name}**\n\n"
        
        # Basic Information
        response += "**📋 Basic Information:**\n"
        response += f"• **Email**: {candidate.get('email', 'N/A')}\n"
        response += f"• **Phone**: {candidate.get('phone', 'N/A')}\n"
        response += f"• **Position Applied**: {candidate.get('position_applied', 'N/A')}\n"
        response += f"• **Application Date**: {candidate.get('created_at', 'Unknown')}\n"
        response += f"• **Status**: {candidate.get('status', 'Active')}\n\n"
        
        # Skills Section
        skills = candidate.get('skills', [])
        if skills:
            response += "**🛠️ Technical Skills:**\n"
            # Group skills by category if possible
            primary_skills = skills[:8]  # Show top 8 skills
            response += f"• {', '.join(primary_skills)}\n"
            
            if len(skills) > 8:
                response += f"• *+{len(skills) - 8} more skills*\n"
            response += "\n"
        
        # Experience Section
        experience = candidate.get('experience', '')
        if experience:
            response += "**💼 Experience:**\n"
            response += f"{experience[:300]}{'...' if len(experience) > 300 else ''}\n\n"
        
        # Education Section
        education = candidate.get('education', '')
        if education:
            response += "**🎓 Education:**\n"
            response += f"{education[:200]}{'...' if len(education) > 200 else ''}\n\n"
        
        # Candidate Summary
        summary = candidate.get('summary', '')
        if summary:
            response += "**📝 Professional Summary:**\n"
            response += f"{summary[:250]}{'...' if len(summary) > 250 else ''}\n\n"
        
        # Fit Analysis
        if fit_analysis:
            response += "**🎯 Fit Analysis:**\n"
            response += f"• **Overall Score**: {fit_analysis.get('overall_score', 'N/A')}/10\n"
            response += f"• **Technical Match**: {fit_analysis.get('technical_match', 'N/A')}\n"
            response += f"• **Experience Level**: {fit_analysis.get('experience_assessment', 'N/A')}\n"
            
            strengths = fit_analysis.get('strengths', [])
            if strengths:
                response += f"• **Key Strengths**: {', '.join(strengths[:3])}\n"
            
            concerns = fit_analysis.get('concerns', [])
            if concerns:
                response += f"• **Areas of Concern**: {', '.join(concerns[:2])}\n"
            
            response += "\n"
        
        # Action Items
        response += "**🚀 Recommended Actions:**\n"
        response += "📞 Schedule screening call\n"
        response += "📝 Technical assessment\n"
        response += "👥 Team interview\n"
        response += "📋 Reference check\n"
        response += "📊 Compare with other candidates\n"
        
        return response
    
    def _handle_candidate_ranking(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle candidate ranking and comparison requests"""
        try:
            entities = understanding.get('entities', {})
            
            # Execute tools for ranking
            tool_results = self.execute_with_tools({
                'action': 'rank_candidates',
                'ranking_criteria': entities,
                'message': message,
                'user_context': user_context
            }, ['rank_candidates_by_criteria', 'analyze_candidate_fit'])
            
            if not tool_results.get('execution_success'):
                return self.format_error_response(f"Ranking failed: {tool_results.get('error', 'Unknown error')}")
            
            ranked_candidates = tool_results.get('ranked_candidates', [])
            ranking_criteria = tool_results.get('ranking_criteria', 'overall fit')
            
            if not ranked_candidates:
                return self.format_success_response("📋 No candidates available for ranking at this time.")
            
            response = self._generate_ranking_response(ranked_candidates, ranking_criteria)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error ranking candidates: {str(e)}")
    
    def _generate_ranking_response(self, ranked_candidates: List[Dict], criteria: str) -> str:
        """Generate candidate ranking response"""
        
        response = f"📊 **Candidate Ranking** (by {criteria})\n\n"
        
        for i, candidate in enumerate(ranked_candidates[:10], 1):
            score = candidate.get('rank_score', 0)
            
            # Medal emojis for top 3
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            response += f"{medal}**{i}. {candidate.get('name', 'Unknown')}** (Score: {score:.1f}/10)\n"
            response += f"   💼 {candidate.get('position_applied', 'N/A')}\n"
            
            # Show relevant skills
            skills = candidate.get('skills', [])[:4]
            if skills:
                response += f"   🛠️ {', '.join(skills)}\n"
            
            # Show ranking justification
            justification = candidate.get('ranking_justification', '')
            if justification:
                response += f"   📝 {justification[:100]}{'...' if len(justification) > 100 else ''}\n"
            
            response += "\n"
        
        # Summary insights
        if len(ranked_candidates) > 10:
            response += f"➕ **{len(ranked_candidates) - 10} more candidates in full ranking**\n\n"
        
        response += "**📈 Ranking Insights:**\n"
        response += f"• Top candidate score: {ranked_candidates[0].get('rank_score', 0):.1f}/10\n"
        response += f"• Average score: {sum(c.get('rank_score', 0) for c in ranked_candidates) / len(ranked_candidates):.1f}/10\n"
        response += f"• Score range: {min(c.get('rank_score', 0) for c in ranked_candidates):.1f} - {max(c.get('rank_score', 0) for c in ranked_candidates):.1f}\n"
        
        return response
    
    def _handle_candidate_analysis(self, message: str, understanding: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle candidate analysis requests"""
        try:
            # Execute analysis tools
            tool_results = self.execute_with_tools({
                'action': 'analyze_candidate_pool',
                'analysis_type': understanding.get('entities', {}),
                'user_context': user_context
            }, ['analyze_candidate_fit', 'generate_candidate_summary'])
            
            analysis = tool_results.get('analysis', {})
            
            response = self._generate_analysis_response(analysis)
            
            return self.format_success_response(response)
            
        except Exception as e:
            return self.format_error_response(f"Error in candidate analysis: {str(e)}")
    
    def _generate_analysis_response(self, analysis: Dict[str, Any]) -> str:
        """Generate candidate analysis response"""
        
        response = "📊 **Candidate Pool Analysis**\n\n"
        
        total_candidates = analysis.get('total_candidates', 0)
        response += f"**📈 Overview:**\n"
        response += f"• Total Candidates: {total_candidates}\n"
        response += f"• Active Applications: {analysis.get('active_applications', 0)}\n"
        response += f"• Average Match Score: {analysis.get('average_match_score', 0):.1f}/10\n\n"
        
        # Skill distribution
        skill_distribution = analysis.get('skill_distribution', {})
        if skill_distribution:
            response += "**🛠️ Top Skills in Pool:**\n"
            for skill, count in list(skill_distribution.items())[:5]:
                percentage = (count / total_candidates) * 100 if total_candidates > 0 else 0
                response += f"• {skill.title()}: {count} candidates ({percentage:.0f}%)\n"
            response += "\n"
        
        # Experience distribution
        exp_distribution = analysis.get('experience_distribution', {})
        if exp_distribution:
            response += "**💼 Experience Levels:**\n"
            for level, count in exp_distribution.items():
                response += f"• {level.title()}: {count} candidates\n"
            response += "\n"
        
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            response += "**💡 Recommendations:**\n"
            for rec in recommendations[:3]:
                response += f"• {rec}\n"
        
        return response
    
    def execute_with_tools(self, request_data: Dict[str, Any], tools: List[str]) -> Dict[str, Any]:
        """Execute ATS request using specialized tools"""
        
        tool_responses = []
        execution_success = True
        result_data = {}
        
        try:
            action = request_data.get('action', '')
            user_context = request_data.get('user_context', {})
            
            if action == 'semantic_candidate_search':
                entities = request_data.get('entities', {})
                search_type = request_data.get('search_type', 'general')
                
                # Perform semantic search
                candidates = self._semantic_candidate_search(entities, search_type)
                
                # Rank candidates if requested
                if 'rank_candidates_by_criteria' in tools:
                    ranked_candidates = self._rank_candidates(candidates, entities)
                    result_data['candidates'] = ranked_candidates
                else:
                    result_data['candidates'] = candidates
                
                result_data['total_count'] = len(candidates)
                
            elif action == 'get_candidate_details':
                candidate_name = request_data.get('candidate_name', '')
                candidate = self._get_candidate_by_name(candidate_name)
                
                if candidate:
                    result_data['candidate_details'] = candidate
                    
                    # Add fit analysis if requested
                    if 'analyze_candidate_fit' in tools:
                        fit_analysis = self._analyze_candidate_fit(candidate)
                        result_data['fit_analysis'] = fit_analysis
                else:
                    execution_success = False
                    result_data['error'] = f'Candidate "{candidate_name}" not found'
                    
            elif action == 'rank_candidates':
                criteria = request_data.get('ranking_criteria', {})
                message = request_data.get('message', '')
                
                # Get candidates to rank
                all_candidates = self._get_all_candidates()
                ranked_candidates = self._rank_candidates_by_criteria(all_candidates, criteria, message)
                
                result_data['ranked_candidates'] = ranked_candidates
                result_data['ranking_criteria'] = self._extract_ranking_criteria(message)
                
            elif action == 'analyze_candidate_pool':
                analysis = self._analyze_candidate_pool()
                result_data['analysis'] = analysis
            
        except Exception as e:
            execution_success = False
            result_data['error'] = str(e)
        
        return {
            'tool_responses': tool_responses,
            'execution_success': execution_success,
            'requires_human_approval': False,  # ATS operations usually don't need approval
            **result_data
        }
    
    # Tool implementation methods
    def _semantic_candidate_search(self, entities: Dict[str, Any], search_type: str) -> List[Dict[str, Any]]:
        """Perform semantic candidate search"""
        try:
            skills = entities.get('skills', [])
            position = entities.get('position', '')
            experience_level = entities.get('experience_level', '')
            
            # Build search query
            search_query = ' '.join(skills)
            if position:
                search_query += f' {position}'
            if experience_level:
                search_query += f' {experience_level}'
            
            # Use RAG system for semantic search
            search_results = self.rag_system.query_candidates(search_query)
            candidates = search_results.get('candidates', [])
            
            # Filter and enhance results
            filtered_candidates = []
            for candidate in candidates:
                # Calculate match score
                match_score = self._calculate_match_score(candidate, entities)
                candidate['match_score'] = match_score
                
                # Apply filters
                if self._candidate_matches_criteria(candidate, entities):
                    filtered_candidates.append(candidate)
            
            # Sort by match score
            filtered_candidates.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            return filtered_candidates[:20]  # Return top 20
            
        except Exception as e:
            print(f"Error in semantic search: {str(e)}")
            return []
    
    def _calculate_match_score(self, candidate: Dict[str, Any], search_entities: Dict[str, Any]) -> float:
        """Calculate match score between candidate and search criteria"""
        
        total_score = 0
        criteria_count = 0
        
        # Skill matching (40% weight)
        search_skills = search_entities.get('skills', [])
        if search_skills:
            candidate_skills = [s.lower() for s in candidate.get('skills', [])]
            matched_skills = sum(1 for skill in search_skills if skill.lower() in candidate_skills)
            skill_score = matched_skills / len(search_skills)
            total_score += skill_score * 0.4
            criteria_count += 1
        
        # Position matching (30% weight)
        search_position = search_entities.get('position', '').lower()
        if search_position:
            candidate_position = candidate.get('position_applied', '').lower()
            position_score = 1 if search_position in candidate_position else 0.3
            total_score += position_score * 0.3
            criteria_count += 1
        
        # Experience level matching (20% weight)
        search_exp = search_entities.get('experience_level', '').lower()
        if search_exp:
            # Simplified experience matching
            candidate_exp = candidate.get('experience', '').lower()
            if search_exp in candidate_exp:
                exp_score = 1.0
            elif search_exp == 'senior' and any(word in candidate_exp for word in ['lead', 'manager', 'architect']):
                exp_score = 0.8
            elif search_exp == 'junior' and any(word in candidate_exp for word in ['entry', 'fresh', 'intern']):
                exp_score = 0.8
            else:
                exp_score = 0.5
            
            total_score += exp_score * 0.2
            criteria_count += 1
        
        # Department matching (10% weight)
        search_dept = search_entities.get('department', '').lower()
        if search_dept:
            candidate_position = candidate.get('position_applied', '').lower()
            dept_score = 1 if search_dept in candidate_position else 0.5
            total_score += dept_score * 0.1
            criteria_count += 1
        
        # Normalize score
        final_score = total_score / criteria_count if criteria_count > 0 else 0.5
        
        # Add base quality score (CV completeness, etc.)
        base_quality = self._assess_candidate_quality(candidate)
        final_score = (final_score * 0.8) + (base_quality * 0.2)
        
        return min(final_score, 1.0)
    
    def _assess_candidate_quality(self, candidate: Dict[str, Any]) -> float:
        """Assess overall candidate profile quality"""
        quality_score = 0
        
        # Check profile completeness
        if candidate.get('email'):
            quality_score += 0.2
        if candidate.get('phone'):
            quality_score += 0.1
        if candidate.get('skills') and len(candidate['skills']) >= 3:
            quality_score += 0.3
        if candidate.get('experience') and len(candidate['experience']) > 50:
            quality_score += 0.2
        if candidate.get('education'):
            quality_score += 0.1
        if candidate.get('summary'):
            quality_score += 0.1
        
        return quality_score
    
    def _candidate_matches_criteria(self, candidate: Dict[str, Any], entities: Dict[str, Any]) -> bool:
        """Check if candidate meets minimum criteria"""
        
        # Must have at least one required skill if skills are specified
        required_skills = entities.get('skills', [])
        if required_skills:
            candidate_skills = [s.lower() for s in candidate.get('skills', [])]
            has_required_skill = any(skill.lower() in candidate_skills for skill in required_skills)
            if not has_required_skill:
                return False
        
        return True
    
    def _get_candidate_by_name(self, name: str) -> Dict[str, Any]:
        """Get candidate by name"""
        try:
            candidates = self.candidate_model.get_all_candidates()
            
            for candidate in candidates:
                candidate_name = candidate.get('name', '').lower()
                if name.lower() in candidate_name or candidate_name in name.lower():
                    return candidate
            
            return None
        except:
            return None
    
    def _analyze_candidate_fit(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how well candidate fits typical requirements"""
        
        analysis = {
            'overall_score': 7.5,  # Default score
            'technical_match': 'Good',
            'experience_assessment': 'Suitable',
            'strengths': [],
            'concerns': []
        }
        
        # Analyze skills
        skills = candidate.get('skills', [])
        if len(skills) >= 5:
            analysis['strengths'].append('Diverse technical skillset')
        elif len(skills) < 3:
            analysis['concerns'].append('Limited technical skills listed')
        
        # Analyze experience
        experience = candidate.get('experience', '')
        if len(experience) > 200:
            analysis['strengths'].append('Detailed work experience')
        elif len(experience) < 50:
            analysis['concerns'].append('Limited experience details')
        
        # Analyze education
        if candidate.get('education'):
            analysis['strengths'].append('Educational background provided')
        
        # Calculate overall score based on analysis
        strengths_score = len(analysis['strengths']) * 1.5
        concerns_penalty = len(analysis['concerns']) * 1.0
        analysis['overall_score'] = max(5.0, min(10.0, 7.5 + strengths_score - concerns_penalty))
        
        return analysis
    
    def _get_all_candidates(self) -> List[Dict[str, Any]]:
        """Get all candidates for ranking"""
        try:
            return self.candidate_model.get_all_candidates()
        except:
            return []
    
    def _rank_candidates(self, candidates: List[Dict], entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank candidates based on search criteria"""
        
        for candidate in candidates:
            if 'match_score' not in candidate:
                candidate['match_score'] = self._calculate_match_score(candidate, entities)
        
        # Sort by match score
        candidates.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return candidates
    
    def _rank_candidates_by_criteria(self, candidates: List[Dict], criteria: Dict[str, Any], message: str) -> List[Dict[str, Any]]:
        """Rank candidates by specific criteria mentioned in message"""
        
        # Extract ranking criteria from message
        message_lower = message.lower()
        
        if 'experience' in message_lower:
            # Rank by experience
            for candidate in candidates:
                exp_length = len(candidate.get('experience', ''))
                candidate['rank_score'] = min(10, exp_length / 50)  # Rough scoring
                candidate['ranking_justification'] = f"Experience detail score: {exp_length} characters"
        
        elif 'skill' in message_lower:
            # Rank by number of skills
            for candidate in candidates:
                skill_count = len(candidate.get('skills', []))
                candidate['rank_score'] = min(10, skill_count / 2)
                candidate['ranking_justification'] = f"Technical skills: {skill_count} listed"
        
        else:
            # Default overall ranking
            for candidate in candidates:
                quality_score = self._assess_candidate_quality(candidate)
                candidate['rank_score'] = quality_score * 10
                candidate['ranking_justification'] = f"Overall profile completeness"
        
        # Sort by rank score
        candidates.sort(key=lambda x: x.get('rank_score', 0), reverse=True)
        
        return candidates
    
    def _extract_ranking_criteria(self, message: str) -> str:
        """Extract what criteria to rank by from message"""
        message_lower = message.lower()
        
        if 'experience' in message_lower:
            return 'experience level'
        elif 'skill' in message_lower:
            return 'technical skills'
        elif 'education' in message_lower:
            return 'educational background'
        else:
            return 'overall fit'
    
    def _analyze_candidate_pool(self) -> Dict[str, Any]:
        """Analyze the entire candidate pool"""
        try:
            candidates = self.candidate_model.get_all_candidates()
            
            if not candidates:
                return {'total_candidates': 0}
            
            # Basic statistics
            total_candidates = len(candidates)
            active_applications = len([c for c in candidates if c.get('status') == 'active'])
            
            # Skill distribution
            all_skills = []
            for candidate in candidates:
                all_skills.extend(candidate.get('skills', []))
            
            skill_counts = {}
            for skill in all_skills:
                skill_lower = skill.lower()
                skill_counts[skill_lower] = skill_counts.get(skill_lower, 0) + 1
            
            # Get top skills
            top_skills = dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
            # Experience level distribution
            exp_distribution = {'junior': 0, 'mid': 0, 'senior': 0, 'lead': 0}
            
            for candidate in candidates:
                exp_text = candidate.get('experience', '').lower()
                if any(word in exp_text for word in ['senior', 'lead', 'architect']):
                    exp_distribution['senior'] += 1
                elif any(word in exp_text for word in ['junior', 'entry', 'intern']):
                    exp_distribution['junior'] += 1
                elif any(word in exp_text for word in ['manager', 'lead']):
                    exp_distribution['lead'] += 1
                else:
                    exp_distribution['mid'] += 1
            
            # Calculate average match score
            total_quality = sum(self._assess_candidate_quality(c) for c in candidates)
            avg_match_score = (total_quality / total_candidates) * 10 if total_candidates > 0 else 0
            
            # Generate recommendations
            recommendations = []
            if total_candidates < 50:
                recommendations.append("Consider expanding recruitment channels")
            
            if top_skills:
                most_common_skill = max(top_skills.keys(), key=top_skills.get)
                recommendations.append(f"Strong pool in {most_common_skill} - consider specialized roles")
            
            if exp_distribution['senior'] < exp_distribution['junior']:
                recommendations.append("Focus on senior-level recruitment for mentorship roles")
            
            return {
                'total_candidates': total_candidates,
                'active_applications': active_applications,
                'average_match_score': avg_match_score,
                'skill_distribution': top_skills,
                'experience_distribution': exp_distribution,
                'recommendations': recommendations
            }
            
        except Exception as e:
            print(f"Error in candidate pool analysis: {str(e)}")
            return {'total_candidates': 0, 'error': str(e)}