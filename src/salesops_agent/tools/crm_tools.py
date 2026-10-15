from typing import Any, Dict, List, Optional
from salesops_agent.tools.crm_store import CRMStore

_store = CRMStore()

def get_store() -> CRMStore:
    global _store
    return _store

def set_store(store: CRMStore) -> None:
    global _store
    _store = store

def lookup_account(account_name_or_id: str) -> Dict[str, Any]:
    """Look up a B2B account by account ID or account name."""
    store = get_store()
    account = store.resolve_account(account_name_or_id)
    if not account:
        return {"error": f"No account found for {account_name_or_id}"}
    return account

def lookup_account_context(account_name_or_id: str) -> Dict[str, Any]:
    """Return comprehensive account context including contacts, opportunities, activities, tickets, and product usage."""
    store = get_store()
    account = store.resolve_account(account_name_or_id)
    if not account:
        return {"error": f"No account found for {account_name_or_id}"}

    account_id = account["account_id"]
    return {
        "account": account,
        "contacts": store.get_contacts_for_account(account_id),
        "opportunities": store.get_opportunities_for_account(account_id),
        "activities": store.get_activities_for_account(account_id),
        "support_tickets": store.get_tickets_for_account(account_id),
        "product_usage": store.get_usage_for_account(account_id),
    }

def list_open_opportunities(stage: Optional[str] = None) -> List[Dict[str, Any]]:
    """List open opportunities, optionally filtered by stage."""
    store = get_store()
    closed_stages = {"closed won", "closed lost"}
    results = [
        o for o in store.opportunities
        if o.get("stage", "").lower() not in closed_stages
    ]
    if stage:
        results = [
            o for o in results
            if o.get("stage", "").lower() == stage.lower()
        ]
    return results

def summarize_pipeline() -> Dict[str, Any]:
    """Summarize opportunity count and total value by stage across the pipeline."""
    store = get_store()
    summary: Dict[str, Dict[str, Any]] = {}
    for opp in store.opportunities:
        stage = opp.get("stage", "Unknown")
        amount = opp.get("amount_usd", 0) or 0
        if stage not in summary:
            summary[stage] = {"count": 0, "amount_usd": 0.0}
        summary[stage]["count"] += 1
        summary[stage]["amount_usd"] += float(amount)
    return summary
