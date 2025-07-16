# backend/agents/langgraph_router.py
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

class LangGraphWorkflowManager:
    """
    Main workflow manager that orchestrates the entire agentic system
    """
    
    def __init__(self, router_agent, leave_agent, ats_agent, payroll_agent):
        self.router_agent = router_agent
        self.leave_agent = leave_agent
        self.ats_agent = ats_agent
        self.payroll_agent = payroll_agent
        
        # Create the workflow graph
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the complete LangGraph workflow"""
        
        # Initialize the workflow with AgentState
        workflow = StateGraph(AgentState)
        
        # Add all nodes (workers)
        workflow.add_node("intent_classifier", self._classify_intent_node)
        workflow.add_node("leave_agent", self._leave_agent_node)
        workflow.add_node("ats_agent", self._ats_agent_node)
        workflow.add_node("payroll_agent", self._payroll_agent_node)
        workflow.add_node("tool_executor", self._tool_executor_node)
        workflow.add_node("human_approval", self._human_approval_node)
        workflow.add_node("response_formatter", self._response_formatter_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define the workflow edges (routes)
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_to_agent,
            {
                "leave": "leave_agent",
                "ats": "ats_agent",
                "payroll": "payroll_agent",
                "error": "error_handler"
            }
        )
        
        # Agent to tool executor
        workflow.add_edge("leave_agent", "tool_executor")
        workflow.add_edge("ats_agent", "tool_executor")
        workflow.add_edge("payroll_agent", "tool_executor")
        
        # Tool executor to human approval check
        workflow.add_conditional_edges(
            "tool_executor",
            self._check_human_approval,
            {
                "approve": "human_approval",
                "format": "response_formatter",
                "error": "error_handler"
            }
        )
        
        # Human approval to response formatter
        workflow.add_edge("human_approval", "response_formatter")
        
        # Response formatter to END
        workflow.add_edge("response_formatter", END)
        workflow.add_edge("error_handler", END)
        
        # Set entry point
        workflow.set_entry_point("intent_classifier")
        
        return workflow.compile()
    
    def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Node 1: Intent classification using RouterAgent"""
        try:
            # Get the latest message
            latest_message = state["messages"][-1]["content"]
            
            # Use router agent to classify intent
            routing_result = self.router_agent.route_request(
                latest_message,
                state["user_context"]
            )
            
            # Update state with routing results
            state["intent"] = routing_result.get("intent", "general")
            state["entities"] = routing_result.get("entities", {})
            state["confidence"] = routing_result.get("confidence", 0.5)
            state["current_node"] = "intent_classifier"
            
            # Add debug info
            state["agent_response"]["routing_debug"] = {
                "classified_intent": state["intent"],
                "confidence": state["confidence"],
                "entities_found": state["entities"]
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "intent_classifier",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            state["intent"] = "error"
            return state
    
    def _leave_agent_node(self, state: AgentState) -> AgentState:
        """Node 2: Leave management processing"""
        try:
            state["current_node"] = "leave_agent"
            
            # Prepare request for leave agent
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "entities": state["entities"],
                "user_context": state["user_context"]
            }
            
            # Process with leave agent
            result = self.leave_agent.process_request(request_data)
            
            # Update state
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "leave_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _ats_agent_node(self, state: AgentState) -> AgentState:
        """Node 3: ATS processing"""
        try:
            state["current_node"] = "ats_agent"
            
            # Prepare request for ATS agent
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "entities": state["entities"],
                "user_context": state["user_context"]
            }
            
            # Process with ATS agent
            result = self.ats_agent.process_request(request_data)
            
            # Update state
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "ats_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _payroll_agent_node(self, state: AgentState) -> AgentState:
        """Node 4: Payroll processing"""
        try:
            state["current_node"] = "payroll_agent"
            
            # Prepare request for payroll agent
            request_data = {
                "intent": state["intent"],
                "message": state["messages"][-1]["content"],
                "entities": state["entities"],
                "user_context": state["user_context"]
            }
            
            # Process with payroll agent
            result = self.payroll_agent.process_request(request_data)
            
            # Update state
            state["agent_response"].update(result)
            state["requires_human_approval"] = result.get("requires_human_approval", False)
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "payroll_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _tool_executor_node(self, state: AgentState) -> AgentState:
        """Node 5: Tool execution for agents"""
        try:
            state["current_node"] = "tool_executor"
            
            # Determine which agent's tools to execute
            current_agent = None
            if state["intent"] in ["leave_request", "leave_status"]:
                current_agent = self.leave_agent
            elif state["intent"] == "candidate_search":
                current_agent = self.ats_agent
            elif state["intent"] == "payroll_calculation":
                current_agent = self.payroll_agent
            
            if current_agent:
                # Execute tools based on agent's requirements
                tool_results = current_agent.execute_with_tools(
                    state["agent_response"],
                    current_agent.available_tools
                )
                
                state["tool_results"] = tool_results
                state["agent_response"]["tool_execution"] = tool_results
                
                # Update human approval requirement
                if tool_results.get("requires_human_approval", False):
                    state["requires_human_approval"] = True
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "tool_executor",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _human_approval_node(self, state: AgentState) -> AgentState:
        """Node 6: Human-in-the-loop approval"""
        try:
            state["current_node"] = "human_approval"
            
            # Create approval request
            approval_request = {
                "type": "human_approval_required",
                "context": state["user_context"],
                "action": state["intent"],
                "data": state["agent_response"],
                "timestamp": datetime.now().isoformat()
            }
            
            # Add approval context to response
            state["agent_response"]["approval_required"] = approval_request
            state["agent_response"]["approval_status"] = "pending"
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "human_approval",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _response_formatter_node(self, state: AgentState) -> AgentState:
        """Node 7: Format final response"""
        try:
            state["current_node"] = "response_formatter"
            
            # Format final response based on agent type
            if state["intent"] in ["leave_request", "leave_status"]:
                response = self.leave_agent.format_response(state["agent_response"])
            elif state["intent"] == "candidate_search":
                response = self.ats_agent.format_response(state["agent_response"])
            elif state["intent"] == "payroll_calculation":
                response = self.payroll_agent.format_response(state["agent_response"])
            else:
                response = self.router_agent.format_response(state["agent_response"])
            
            # Update final response
            state["agent_response"]["formatted_response"] = response
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "response_formatter",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _error_handler_node(self, state: AgentState) -> AgentState:
        """Node 8: Error handling"""
        try:
            error_info = state.get("error_state", {})
            
            # Format error response
            error_response = f"""
            ❌ **System Error Occurred**
            
            **Error Details:**
            • Node: {error_info.get('node', 'Unknown')}
            • Error: {error_info.get('error', 'Unknown error')}
            • Time: {error_info.get('timestamp', 'Unknown')}
            
            **What you can do:**
            • Try rephrasing your request
            • Check if you have the required permissions
            • Contact system administrator if the issue persists
            
            **Quick Help:**
            • For leave requests: "I need leave next week"
            • For payroll: "Calculate my payroll"
            • For candidates (HR only): "Find Java developers"
            """
            
            state["agent_response"]["error_response"] = error_response
            state["agent_response"]["success"] = False
            
            return state
            
        except Exception as e:
            # Fallback error handling
            state["agent_response"]["error_response"] = "❌ A system error occurred. Please try again."
            state["agent_response"]["success"] = False
            return state
    
    def _route_to_agent(self, state: AgentState) -> str:
        """Conditional edge function for routing"""
        if state.get("error_state"):
            return "error"
        
        intent = state.get("intent", "general")
        
        if intent in ["leave_request", "leave_status"]:
            return "leave"
        elif intent == "candidate_search":
            return "ats"
        elif intent == "payroll_calculation":
            return "payroll"
        else:
            return "error"
    
    def _check_human_approval(self, state: AgentState) -> str:
        """Check if human approval is required"""
        if state.get("error_state"):
            return "error"
        
        if state.get("requires_human_approval", False):
            return "approve"
        else:
            return "format"
    
    def process_message(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing messages through the workflow"""
        
        # Initialize state
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
            "error_state": {}
        }
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Return formatted response
        return {
            "success": not bool(final_state.get("error_state")),
            "response": final_state["agent_response"].get("formatted_response", 
                                                       final_state["agent_response"].get("error_response", "No response generated")),
            "agent": final_state.get("current_node", "workflow"),
            "requires_action": final_state.get("requires_human_approval", False),
            "confidence": final_state.get("confidence", 0.0),
            "workflow_state": final_state
        }