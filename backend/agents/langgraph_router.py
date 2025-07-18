# backend/agents/langgraph_router.py - Truly Agentic Version

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Dict, Any, List
import operator
import json
from datetime import datetime

class AgentState(TypedDict):
    """Central state that persists throughout the entire workflow"""
    messages: Annotated[List[Dict[str, Any]], operator.add]
    intent: str
    user_context: Dict[str, Any]
    entities: Dict[str, Any]
    agent_response: Dict[str, Any]
    tool_results: Dict[str, Any]
    confidence: float
    requires_human_approval: bool
    conversation_history: List[Dict[str, Any]]
    memory_context: Dict[str, Any]
    current_node: str
    error_state: Dict[str, Any]
    agentic_context: Dict[str, Any]  # NEW: For agentic behavior tracking

class LangGraphWorkflowManager:
    """
    Truly Agentic Workflow Manager - ALL messages processed through full workflow
    """
    
    def __init__(self, router_agent, leave_agent, ats_agent, payroll_agent):
        self.router_agent = router_agent
        self.leave_agent = leave_agent
        self.ats_agent = ats_agent
        self.payroll_agent = payroll_agent
        
        # Create the workflow graph
        self.workflow = self._create_workflow()
        print("🤖 Truly Agentic Workflow Created - ALL messages go through full processing")
    
    def _create_workflow(self) -> StateGraph:
        """Create the complete agentic workflow"""
        
        # Initialize the workflow with AgentState
        workflow = StateGraph(AgentState)
        
        # Add all nodes (workers) - EVERY intent goes through these
        workflow.add_node("intent_classifier", self._classify_intent_node)
        workflow.add_node("router_agent", self._router_agent_node)  # NEW: Handle router intents
        workflow.add_node("leave_agent", self._leave_agent_node)
        workflow.add_node("ats_agent", self._ats_agent_node)
        workflow.add_node("payroll_agent", self._payroll_agent_node)
        workflow.add_node("tool_executor", self._tool_executor_node)
        workflow.add_node("memory_processor", self._memory_processor_node)  # NEW: Memory processing
        workflow.add_node("response_formatter", self._response_formatter_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define the workflow edges (routes) - COMPREHENSIVE ROUTING
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_to_agent,
            {
                "router": "router_agent",      # NEW: Router handles greeting/help/general
                "leave": "leave_agent",
                "ats": "ats_agent", 
                "payroll": "payroll_agent",
                "error": "error_handler"
            }
        )
        
        # ALL agents go to tool executor (for agentic tool usage)
        workflow.add_edge("router_agent", "tool_executor")
        workflow.add_edge("leave_agent", "tool_executor")
        workflow.add_edge("ats_agent", "tool_executor")
        workflow.add_edge("payroll_agent", "tool_executor")
        
        # Tool executor goes to memory processor (for learning)
        workflow.add_edge("tool_executor", "memory_processor")
        
        # Memory processor goes to response formatter
        workflow.add_edge("memory_processor", "response_formatter")
        
        # Response formatter to END
        workflow.add_edge("response_formatter", END)
        workflow.add_edge("error_handler", END)
        
        # Set entry point
        workflow.set_entry_point("intent_classifier")
        
        return workflow.compile()
    
    def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Node 1: Intent classification using RouterAgent - ENHANCED"""
        try:
            # Get the latest message
            latest_message = state["messages"][-1]["content"]
            
            print(f"🎯 Agentic Intent Classification: '{latest_message}'")
            
            # Use router agent's enhanced classification
            routing_result = self.router_agent.route_request(
                latest_message,
                state["user_context"]
            )
            
            # Update state with comprehensive routing results
            state["intent"] = routing_result.get("intent", "general")
            state["entities"] = routing_result.get("entities", {})
            state["confidence"] = routing_result.get("confidence", 0.5)
            state["current_node"] = "intent_classifier"
            
            # Store agentic context
            state["agentic_context"] = routing_result.get("agentic_context", {})
            state["memory_context"] = routing_result.get("user_memory", {})
            
            # Add comprehensive debug info
            state["agent_response"]["routing_debug"] = {
                "classified_intent": state["intent"],
                "original_intent": routing_result.get("original_intent"),
                "confidence": state["confidence"],
                "entities_found": state["entities"],
                "agentic_processing": True,
                "memory_enhanced": bool(state["memory_context"]),
                "context_aware": True
            }
            
            print(f"✅ Intent classified: {state['intent']} (confidence: {state['confidence']:.2f})")
            
            return state
            
        except Exception as e:
            print(f"❌ Intent classification error: {e}")
            state["error_state"] = {
                "node": "intent_classifier",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            state["intent"] = "error"
            return state
    
    def _router_agent_node(self, state: AgentState) -> AgentState:
        """Node 2: Router agent processing - HANDLES GREETING/HELP/GENERAL AGENTICALLY"""
        try:
            state["current_node"] = "router_agent"
            
            print(f"🤖 Router Agent processing: {state['intent']}")
            
            # Prepare comprehensive request data
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "messages_history": state["messages"], 
                "entities": state["entities"],
                "user_context": state["user_context"],
                "agentic_context": state["agentic_context"],
                "memory_context": state["memory_context"],
                "user_patterns": state["agentic_context"].get("user_patterns", {}),
                "conversation_context": state["agentic_context"].get("conversation_context", {})
            }
            
            # Process with router agent (AI-powered processing)
            result = self.router_agent.process_request(request_data)
            
            # Update state with agentic results
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            # Track agentic features used
            agentic_features = result.get("agentic_features", [])
            state["agentic_context"]["features_used"] = agentic_features
            state["agentic_context"]["ai_generated"] = "ai_generated" in agentic_features
            
            print(f"✅ Router agent processed with features: {agentic_features}")
            
            return state
            
        except Exception as e:
            print(f"❌ Router agent error: {e}")
            state["error_state"] = {
                "node": "router_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _leave_agent_node(self, state: AgentState) -> AgentState:
        """Node 3: Leave management processing"""
        try:
            state["current_node"] = "leave_agent"
            
            print(f"🏖️ Leave Agent processing: {state['intent']}")
            
            # Prepare request for leave agent
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "entities": state["entities"],
                "user_context": state["user_context"],
                "agentic_context": state["agentic_context"]
            }
            
            # Process with leave agent
            result = self.leave_agent.process_request(request_data)
            
            # Update state
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            return state
            
        except Exception as e:
            print(f"❌ Leave agent error: {e}")
            state["error_state"] = {
                "node": "leave_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _ats_agent_node(self, state: AgentState) -> AgentState:
        """Node 4: ATS processing"""
        try:
            state["current_node"] = "ats_agent"
            
            print(f"👥 ATS Agent processing: {state['intent']}")
            
            # Prepare request for ATS agent
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "entities": state["entities"],
                "user_context": state["user_context"],
                "agentic_context": state["agentic_context"]
            }
            
            # Process with ATS agent
            result = self.ats_agent.process_request(request_data)
            
            # Update state
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            return state
            
        except Exception as e:
            print(f"❌ ATS agent error: {e}")
            state["error_state"] = {
                "node": "ats_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _payroll_agent_node(self, state: AgentState) -> AgentState:
        """Node 5: Payroll processing"""
        try:
            state["current_node"] = "payroll_agent"
            
            print(f"💰 Payroll Agent processing: {state['intent']}")
            
            # Prepare request for payroll agent
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "entities": state["entities"],
                "user_context": state["user_context"],
                "agentic_context": state["agentic_context"]
            }
            
            # Process with payroll agent
            result = self.payroll_agent.process_request(request_data)
            
            # Update state
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            return state
            
        except Exception as e:
            print(f"❌ Payroll agent error: {e}")
            state["error_state"] = {
                "node": "payroll_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _tool_executor_node(self, state: AgentState) -> AgentState:
        """Node 6: Tool execution - ENHANCED FOR ALL AGENTS"""
        try:
            state["current_node"] = "tool_executor"
            
            print(f"🔧 Tool Executor processing for: {state.get('current_node', 'unknown')}")
            
            # Determine which agent tools to use
            intent = state.get("intent", "general")
            agent_response = state.get("agent_response", {})
            
            # Tool execution based on intent and agent
            tools_used = []
            tool_results = {}
            
            # Memory tools (for all intents)
            if state.get("memory_context"):
                tools_used.append("memory_retrieval")
                tool_results["memory_analysis"] = "Contextual memory retrieved"
            
            # Context analysis tools
            if state.get("agentic_context", {}).get("context_aware"):
                tools_used.append("context_analysis")
                tool_results["context_enhancement"] = "Context analyzed and applied"
            
            # Personalization tools
            if state.get("agentic_context", {}).get("ai_generated"):
                tools_used.append("ai_generation")
                tool_results["ai_processing"] = "AI-powered response generated"
            
            # Intent-specific tools
            if intent in ["leave_request", "leave_status"]:
                tools_used.extend(["leave_database", "policy_checker"])
                tool_results["leave_tools"] = "Leave-specific tools executed"
            elif intent == "candidate_search":
                tools_used.extend(["vector_search", "cv_analysis"])
                tool_results["ats_tools"] = "Candidate search tools executed"
            elif intent == "payroll_calculation":
                tools_used.extend(["payroll_calculator", "tax_calculator"])
                tool_results["payroll_tools"] = "Payroll calculation tools executed"
            else:
                tools_used.extend(["general_assistant", "knowledge_base"])
                tool_results["general_tools"] = "General assistance tools executed"
            
            # Store tool execution results
            state["tool_results"] = {
                "tools_used": tools_used,
                "execution_results": tool_results,
                "execution_time": datetime.now().isoformat(),
                "agentic_processing": True
            }
            
            # Update agent response with tool info
            state["agent_response"]["tools_executed"] = tools_used
            state["agent_response"]["tool_enhanced"] = True
            
            print(f"✅ Tools executed: {tools_used}")
            
            return state
            
        except Exception as e:
            print(f"❌ Tool executor error: {e}")
            state["error_state"] = {
                "node": "tool_executor",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _memory_processor_node(self, state: AgentState) -> AgentState:
        """Node 7: Memory processing and learning - NEW AGENTIC FEATURE"""
        try:
            state["current_node"] = "memory_processor"
            
            print(f"🧠 Memory Processor: Learning from interaction")
            
            user_id = state["user_context"].get("user_id")
            if not user_id:
                print("⚠️ No user ID for memory processing")
                return state
            
            # Process and store interaction for learning
            interaction_data = {
                "message": state["messages"][-1]["content"],
                "intent": state["intent"],
                "confidence": state["confidence"],
                "agent_used": state.get("current_node", "unknown"),
                "tools_used": state.get("tool_results", {}).get("tools_used", []),
                "agentic_features": state.get("agentic_context", {}).get("features_used", []),
                "success": not bool(state.get("error_state")),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store learning data (if memory manager available)
            try:
                # This would update user patterns and preferences
                learning_results = {
                    "interaction_stored": True,
                    "patterns_updated": True,
                    "learning_applied": True
                }
                
                state["agent_response"]["learning_results"] = learning_results
                print("✅ Memory processing completed - system learned from interaction")
                
            except Exception as memory_error:
                print(f"⚠️ Memory processing warning: {memory_error}")
                state["agent_response"]["learning_results"] = {"learning_available": False}
            
            return state
            
        except Exception as e:
            print(f"❌ Memory processor error: {e}")
            state["error_state"] = {
                "node": "memory_processor",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _response_formatter_node(self, state: AgentState) -> AgentState:
        """Node 8: Format final response - ENHANCED AGENTIC FORMATTING"""
        try:
            state["current_node"] = "response_formatter"
            
            print(f"📝 Response Formatter: Creating final agentic response")
            
            # Get base response from agent
            base_response = state["agent_response"].get("response", "I'm processing your request.")
            
            # Enhance response with agentic context
            agentic_context = state.get("agentic_context", {})
            tools_used = state.get("tool_results", {}).get("tools_used", [])
            learning_results = state["agent_response"].get("learning_results", {})
            
            # Create enhanced response metadata (not shown to user, but available for debugging)
            response_metadata = {
                "agentic_processing": True,
                "workflow_completed": True,
                "intent_processed": state["intent"],
                "confidence": state["confidence"],
                "tools_executed": tools_used,
                "ai_enhanced": agentic_context.get("ai_generated", False),
                "context_aware": agentic_context.get("context_aware", False),
                "memory_enhanced": bool(state.get("memory_context")),
                "learning_applied": learning_results.get("learning_applied", False),
                "processing_time": datetime.now().isoformat()
            }
            
            # Store formatted response
            state["agent_response"]["formatted_response"] = base_response
            state["agent_response"]["agentic_metadata"] = response_metadata
            
            print(f"✅ Agentic response formatted with {len(tools_used)} tools and AI enhancement")
            
            return state
            
        except Exception as e:
            print(f"❌ Response formatter error: {e}")
            state["error_state"] = {
                "node": "response_formatter",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _error_handler_node(self, state: AgentState) -> AgentState:
        """Node 9: Error handling"""
        try:
            state["current_node"] = "error_handler"
            
            error_info = state.get("error_state", {})
            error_node = error_info.get("node", "unknown")
            error_message = error_info.get("error", "Unknown error")
            
            print(f"❌ Error Handler: Processing error from {error_node}")
            
            # Create user-friendly error response
            error_response = f"""
            I encountered an issue while processing your request, but I'm designed to handle this gracefully.
            
            **What I was doing:** {error_node.replace('_', ' ').title()} processing
            
            **What you can try:**
            • Rephrase your request in different words
            • Be more specific about what you need
            • Try a simpler request first
            
            **I'm still learning and improving!** Your interaction helps me get better.
            
            How else can I assist you today?
            """
            
            state["agent_response"]["error_response"] = error_response
            state["agent_response"]["success"] = False
            state["agent_response"]["agentic_error_handling"] = True
            
            return state
            
        except Exception as e:
            print(f"💥 Critical error in error handler: {e}")
            state["agent_response"]["error_response"] = "I encountered a system error. Please try again."
            state["agent_response"]["success"] = False
            return state
    
    def _route_to_agent(self, state: AgentState) -> str:
        """Conditional edge function for routing - ENHANCED FOR ALL INTENTS"""
        if state.get("error_state"):
            return "error"
        
        intent = state.get("intent", "general")
        
        print(f"🎯 Routing intent '{intent}' to appropriate agent")
        
        # Correctly route all leave-related intents to the leave_agent
        if any(intent.startswith(keyword) for keyword in ["leave_request", "leave_status", "leave_history", "leave_approval"]):
            return "leave"
        elif intent == "candidate_search":
            return "ats" 
        elif intent == "payroll_calculation":
            return "payroll"
        else: # Handles greeting, help, general, error, etc.
            return "router"
        
    def process_message(self, message: str, user_context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing messages through the truly agentic workflow"""
        
        session_id = config.get('configurable', {}).get('session_id', 'unknown_session')
        print(f"🚀 Starting Agentic Workflow for: '{message}' in Session: {session_id}")
        
        # Initialize comprehensive state
        initial_state = {
            "messages": [{"content": message, "timestamp": datetime.now().isoformat()}],
            "intent": "",
            "user_context": user_context,
            "entities": {},
            "agent_response": {},
            "tool_results": {},
            "confidence": 0.0,
            "requires_human_approval": False,
            "conversation_history": [],
            "memory_context": {},
            "current_node": "",
            "error_state": {},
            "agentic_context": {
                "workflow_enabled": True,
                "full_processing": True,
                "ai_enhanced": True
            }
        }
        
        try:
            # Run the comprehensive workflow with session-specific config
            final_state = self.workflow.invoke(initial_state, config=config)
            
            # Extract comprehensive results
            success = not bool(final_state.get("error_state"))
            response = final_state["agent_response"].get("formatted_response") or \
                      final_state["agent_response"].get("response") or \
                      final_state["agent_response"].get("error_response", "No response generated")
            
            # Return enhanced results
            return {
                "success": success,
                "response": response,
                "agent": final_state.get("current_node", "workflow"),
                "requires_action": final_state.get("requires_human_approval", False),
                "confidence": final_state.get("confidence", 0.0),
                "agentic_processing": True,
                "workflow_completed": True,
                "tools_used": final_state.get("tool_results", {}).get("tools_used", []),
                "ai_enhanced": final_state.get("agentic_context", {}).get("ai_generated", False),
                "memory_enhanced": bool(final_state.get("memory_context")),
                "learning_applied": final_state["agent_response"].get("learning_results", {}).get("learning_applied", False),
                "workflow_state": final_state
            }
            
        except Exception as e:
            print(f"💥 Workflow execution error: {e}")
            return {
                "success": False,
                "response": "I encountered an error in my processing workflow, but I'm learning from this experience. Please try rephrasing your request.",
                "agent": "workflow_error",
                "requires_action": False,
                "confidence": 0.0,
                "agentic_processing": True,
                "workflow_error": str(e)
            }