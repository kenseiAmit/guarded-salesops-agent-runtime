from pathlib import Path
from typing import Any, Dict, Optional
import json
from salesops_agent.tools.crm_tools import lookup_account_context

EMAIL_OUTBOX_PATH = Path("data/email_outbox.json")

def draft_email(account_name_or_id: str, purpose: str) -> Dict[str, Any]:
    """Draft a follow-up email for an account's primary contact."""
    context = lookup_account_context(account_name_or_id)
    if "error" in context:
        return context

    account = context["account"]
    account_contacts = context.get("contacts", [])
    primary_contact = next(
        (c for c in account_contacts if c.get("is_primary")),
        account_contacts[0] if account_contacts else None,
    )

    if not primary_contact:
        return {"error": f"No contact found for account {account.get('name', account_name_or_id)}"}

    return {
        "to": primary_contact.get("email", ""),
        "subject": f"Following up on {account.get('name', '')}",
        "body": f"Hi {primary_contact.get('first_name', 'there')},\n\nI wanted to follow up regarding {purpose}.\n\nBest,\nNexaCRM SalesOps Agent\n",
        "status": "drafted",
        "requires_approval": True,
    }

def send_email(to: str, subject: str, body: str, approved: bool = False) -> Dict[str, Any]:
    """Simulate sending an email by appending it to email_outbox.json.
    
    CRITICAL: Requires explicit human approval. If approved is False, this call fails.
    """
    if not approved:
        return {
            "status": "blocked",
            "reason": "unapproved_email_sending",
            "policy": "salesops_hitl_approval_policy",
            "error": "Action rejected: sending email requires explicit human approval.",
        }

    outbox = []
    if EMAIL_OUTBOX_PATH.exists():
        try:
            with open(EMAIL_OUTBOX_PATH, "r", encoding="utf-8") as f:
                outbox = json.load(f)
        except Exception:
            outbox = []

    message = {
        "to": to,
        "subject": subject,
        "body": body,
        "status": "sent",
    }
    outbox.append(message)

    EMAIL_OUTBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EMAIL_OUTBOX_PATH, "w", encoding="utf-8") as f:
        json.dump(outbox, f, indent=2)

    return {"status": "sent", "message": message}
