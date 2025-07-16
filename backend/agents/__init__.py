# backend/agents/__init__.py
from .base_agent import BaseAgent
from .leave_agent import LeaveAgent
from .ats_agent import ATSAgent
from .payroll_agent import PayrollAgent

# Import router_agent separately to avoid circular imports
try:
    from .router_agent import RouterAgent
    __all__ = ['BaseAgent', 'RouterAgent', 'LeaveAgent', 'ATSAgent', 'PayrollAgent']
except ImportError as e:
    print(f"Warning: Could not import RouterAgent: {e}")
    __all__ = ['BaseAgent', 'LeaveAgent', 'ATSAgent', 'PayrollAgent']