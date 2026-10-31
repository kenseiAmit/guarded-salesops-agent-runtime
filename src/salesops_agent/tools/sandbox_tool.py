import ast
import time
import copy
from typing import Any, Dict, List, Optional
from salesops_agent.tools.crm_tools import get_store

DISALLOWED_NODES = (
    ast.Import,
    ast.ImportFrom,
)

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

class SandboxSecurityError(Exception):
    """Raised when code violates sandbox constraints."""
    pass

class CRMSandbox:
    """Constrained, sandboxed execution environment for data analysis over CRM data."""
    
    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout_seconds = timeout_seconds

    def _get_crm_context(self) -> Dict[str, Any]:
        """Provide copies of approved CRM datasets. Strictly excludes HR and financial data."""
        store = get_store()
        return {
            "accounts": copy.deepcopy(store.accounts),
            "opportunities": copy.deepcopy(store.opportunities),
            "support_tickets": copy.deepcopy(store.support_tickets),
            "contacts": copy.deepcopy(store.contacts),
            "activities": copy.deepcopy(store.activities),
            "product_usage": copy.deepcopy(store.product_usage),
        }

    def validate_code(self, code_str: str) -> None:
        """Validate AST against forbidden AST nodes, builtins, and attribute lookups."""
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            raise SandboxSecurityError(f"Syntax error in sandbox code: {e}")

        for node in ast.walk(tree):
            if isinstance(node, DISALLOWED_NODES):
                raise SandboxSecurityError("Imports are strictly forbidden in sandboxed execution.")
            
            # Prevent calling eval, exec, compile, open, etc.
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in {"eval", "exec", "compile", "open", "__import__", "globals", "locals", "getattr", "setattr", "delattr", "system"}:
                        raise SandboxSecurityError(f"Use of '{node.func.id}' is prohibited in the sandbox.")
            
            # Prevent private/dunder attribute access to prevent sandbox escapes
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__") and node.attr.endswith("__"):
                    raise SandboxSecurityError(f"Access to dunder attribute '{node.attr}' is prohibited.")
                if node.attr in {"internal_hr_data", "internal_financial_data"}:
                    raise SandboxSecurityError(f"Access to restricted data source '{node.attr}' is blocked.")

            # Prevent forbidden variable names
            if isinstance(node, ast.Name):
                if node.id in {"internal_hr_data", "internal_financial_data", "os", "sys", "subprocess", "socket"}:
                    raise SandboxSecurityError(f"Referencing forbidden identifier '{node.id}' is prohibited.")

    def run_analysis(self, python_code: str) -> Dict[str, Any]:
        """Execute Python code in the sandbox.
        
        The code is expected to compute a result and assign it to variable `result`.
        """
        start_time = time.time()
        
        try:
            self.validate_code(python_code)
        except SandboxSecurityError as e:
            return {
                "status": "blocked",
                "reason": "sandbox_policy_violation",
                "error": str(e),
                "latency_seconds": time.time() - start_time,
            }

        safe_globals: Dict[str, Any] = {
            "__builtins__": SAFE_BUILTINS,
        }
        
        # Inject only approved CRM datasets into local scope
        local_scope = self._get_crm_context()
        local_scope["result"] = None

        try:
            # Execute with restricted globals and isolated locals
            exec(python_code, safe_globals, local_scope) # nosec
            
            # Check elapsed execution time
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                return {
                    "status": "blocked",
                    "reason": "sandbox_timeout_exceeded",
                    "error": f"Execution exceeded maximum timeout of {self.timeout_seconds}s.",
                    "latency_seconds": elapsed,
                }

            result = local_scope.get("result")
            return {
                "status": "success",
                "result": result,
                "latency_seconds": round(elapsed, 4),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Runtime execution failed: {type(e).__name__}: {str(e)}",
                "latency_seconds": round(time.time() - start_time, 4),
            }

# Pre-built standard safe analytical operations
def execute_safe_data_analysis(query_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Provides high-level analytical routines over approved CRM data."""
    store = get_store()
    params = params or {}
    
    if query_type == "pipeline_by_stage":
        stages: Dict[str, Dict[str, Any]] = {}
        for opp in store.opportunities:
            stage = opp.get("stage", "Unknown")
            amt = float(opp.get("amount_usd", 0) or 0)
            if stage not in stages:
                stages[stage] = {"count": 0, "total_value_usd": 0.0}
            stages[stage]["count"] += 1
            stages[stage]["total_value_usd"] += amt
        return {"status": "success", "data": stages}
        
    elif query_type == "average_deal_size":
        opps = [float(o.get("amount_usd", 0) or 0) for o in store.opportunities if o.get("amount_usd")]
        avg_val = sum(opps) / len(opps) if opps else 0.0
        return {"status": "success", "count": len(opps), "average_deal_size_usd": round(avg_val, 2)}
        
    elif query_type == "high_risk_renewals":
        risk_threshold = params.get("health_score_threshold", 60)
        low_health_accounts = {
            a["account_id"]: a for a in store.accounts 
            if (a.get("health_score") is not None and a.get("health_score") < risk_threshold)
        }
        at_risk_opps = [
            {
                "opportunity_id": o["opportunity_id"],
                "account_name": low_health_accounts[o["account_id"]]["name"],
                "health_score": low_health_accounts[o["account_id"]]["health_score"],
                "amount_usd": o.get("amount_usd"),
                "stage": o.get("stage"),
                "close_date": o.get("close_date"),
            }
            for o in store.opportunities
            if o.get("account_id") in low_health_accounts and "renewal" in o.get("name", "").lower()
        ]
        return {"status": "success", "count": len(at_risk_opps), "high_risk_renewals": at_risk_opps}

    elif query_type == "tickets_by_severity":
        counts: Dict[str, int] = {}
        for t in store.support_tickets:
            sev = t.get("severity", "Unknown")
            counts[sev] = counts.get(sev, 0) + 1
        return {"status": "success", "tickets_by_severity": counts}

    else:
        return {"status": "error", "error": f"Unsupported query type: {query_type}"}
