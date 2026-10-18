from typing import Any, Callable, Dict, List, Optional
from salesops_agent.tools.crm_tools import (
    lookup_account,
    lookup_account_context,
    list_open_opportunities,
    summarize_pipeline,
)
from salesops_agent.tools.restricted_tools import (
    lookup_internal_hr_data,
    lookup_internal_financial_data,
)
from salesops_agent.tools.email_tool import draft_email, send_email

SAFE_SALESOPS_TOOLS: Dict[str, Callable[..., Any]] = {
    "lookup_account": lookup_account,
    "lookup_account_context": lookup_account_context,
    "list_open_opportunities": list_open_opportunities,
    "summarize_pipeline": summarize_pipeline,
    "draft_email": draft_email,
}

RESTRICTED_TOOLS: Dict[str, Callable[..., Any]] = {
    "lookup_internal_hr_data": lookup_internal_hr_data,
    "lookup_internal_financial_data": lookup_internal_financial_data,
}

HITL_TOOLS: Dict[str, Callable[..., Any]] = {
    "send_email": send_email,
}

ALL_TOOLS: Dict[str, Callable[..., Any]] = {
    **SAFE_SALESOPS_TOOLS,
    **RESTRICTED_TOOLS,
    **HITL_TOOLS,
}

def get_tool(tool_name: str) -> Optional[Callable[..., Any]]:
    return ALL_TOOLS.get(tool_name)

def list_safe_tool_names() -> List[str]:
    return list(SAFE_SALESOPS_TOOLS.keys())

def is_restricted_tool(tool_name: str) -> bool:
    return tool_name in RESTRICTED_TOOLS

def is_hitl_tool(tool_name: str) -> bool:
    return tool_name in HITL_TOOLS
