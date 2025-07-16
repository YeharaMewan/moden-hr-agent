# backend/agents/langgraph_router.py
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str
    user_context: dict
    agent_response: dict

def create_agent_workflow():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("intent_classifier", classify_intent)
    workflow.add_node("leave_agent", process_leave_request)
    workflow.add_node("ats_agent", process_ats_request)
    workflow.add_node("payroll_agent", process_payroll_request)
    
    # Define conditional edges based on intent
    workflow.add_conditional_edges(
        "intent_classifier",
        route_to_agent,
        {
            "leave": "leave_agent",
            "ats": "ats_agent", 
            "payroll": "payroll_agent",
            "end": END
        }
    )
    
    workflow.set_entry_point("intent_classifier")
    return workflow.compile()