from typing import Any, Dict
from salesops_agent.tools.crm_tools import get_store

def lookup_internal_hr_data(query: str) -> Dict[str, Any]:
    """Look up internal HR data. Restricted internal tool - must be blocked by tool guardrails."""
    store = get_store()
    return {
        "query": query,
        "data": store.internal_hr_data,
    }

def lookup_internal_financial_data(query: str) -> Dict[str, Any]:
    """Look up internal financial strategy data. Restricted internal tool - must be blocked by tool guardrails."""
    store = get_store()
    return {
        "query": query,
        "data": store.internal_financial_data,
    }
