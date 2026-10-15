from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re
import difflib

class CRMStore:
    """Manages loading, caching, and searching CRM records."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self._accounts: Optional[List[Dict[str, Any]]] = None
        self._contacts: Optional[List[Dict[str, Any]]] = None
        self._opportunities: Optional[List[Dict[str, Any]]] = None
        self._activities: Optional[List[Dict[str, Any]]] = None
        self._support_tickets: Optional[List[Dict[str, Any]]] = None
        self._product_usage: Optional[List[Dict[str, Any]]] = None
        self._internal_hr_data: Optional[List[Dict[str, Any]]] = None
        self._internal_financial_data: Optional[List[Dict[str, Any]]] = None

    def _load_json(self, filename: str) -> List[Dict[str, Any]]:
        file_path = self.data_dir / filename
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def accounts(self) -> List[Dict[str, Any]]:
        if self._accounts is None:
            self._accounts = self._load_json("accounts.json")
        return self._accounts

    @property
    def contacts(self) -> List[Dict[str, Any]]:
        if self._contacts is None:
            self._contacts = self._load_json("contacts.json")
        return self._contacts

    @property
    def opportunities(self) -> List[Dict[str, Any]]:
        if self._opportunities is None:
            self._opportunities = self._load_json("opportunities.json")
        return self._opportunities

    @property
    def activities(self) -> List[Dict[str, Any]]:
        if self._activities is None:
            self._activities = self._load_json("activities.json")
        return self._activities

    @property
    def support_tickets(self) -> List[Dict[str, Any]]:
        if self._support_tickets is None:
            self._support_tickets = self._load_json("support_tickets.json")
        return self._support_tickets

    @property
    def product_usage(self) -> List[Dict[str, Any]]:
        if self._product_usage is None:
            self._product_usage = self._load_json("product_usage.json")
        return self._product_usage

    @property
    def internal_hr_data(self) -> List[Dict[str, Any]]:
        if self._internal_hr_data is None:
            self._internal_hr_data = self._load_json("internal_hr_data.json")
        return self._internal_hr_data

    @property
    def internal_financial_data(self) -> List[Dict[str, Any]]:
        if self._internal_financial_data is None:
            self._internal_financial_data = self._load_json("internal_financial_data.json")
        return self._internal_financial_data

    @staticmethod
    def normalize_lookup_text(value: str) -> str:
        """Normalize names and IDs for forgiving lookups."""
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(
            r"\b(incorporated|inc|corp|corporation|ltd|limited|llc|co|company)\b",
            "",
            value,
        )
        return re.sub(r"\s+", " ", value).strip()

    def find_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        norm_id = account_id.strip().lower()
        return next((a for a in self.accounts if a.get("account_id", "").lower() == norm_id), None)

    def find_account_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        query = self.normalize_lookup_text(name)
        if not query:
            return None

        # Exact match
        for acc in self.accounts:
            if query == self.normalize_lookup_text(acc.get("name", "")):
                return acc

        # Substring match
        for acc in self.accounts:
            acc_name = self.normalize_lookup_text(acc.get("name", ""))
            if query in acc_name or acc_name in query:
                return acc

        # Fuzzy fallback
        name_map = {self.normalize_lookup_text(a["name"]): a for a in self.accounts if "name" in a}
        matches = difflib.get_close_matches(query, name_map.keys(), n=1, cutoff=0.75)
        if matches:
            return name_map[matches[0]]

        return None

    def resolve_account(self, account_name_or_id: str) -> Optional[Dict[str, Any]]:
        return self.find_account_by_id(account_name_or_id) or self.find_account_by_name(account_name_or_id)

    def get_contacts_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        return [c for c in self.contacts if c.get("account_id") == account_id]

    def get_opportunities_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        return [o for o in self.opportunities if o.get("account_id") == account_id]

    def get_activities_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        return [a for a in self.activities if a.get("account_id") == account_id]

    def get_tickets_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        return [t for t in self.support_tickets if t.get("account_id") == account_id]

    def get_usage_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        return [u for u in self.product_usage if u.get("account_id") == account_id]
