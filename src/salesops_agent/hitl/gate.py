from typing import Any, Dict, Optional, Tuple

class HITLGate:
    """Human-in-the-Loop gate controller for high-risk actions."""

    def __init__(self, high_risk_actions: Optional[list] = None):
        self.high_risk_actions = high_risk_actions or ["send_email"]

    def is_high_risk(self, action_name: str) -> bool:
        """Determines if an action requires explicit human approval."""
        return action_name in self.high_risk_actions

    def evaluate_action(
        self,
        action_name: str,
        action_payload: Dict[str, Any],
        approval_signal: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluates an action against the approval gate.
        
        Returns:
            (is_allowed, gate_result_dict)
        """
        if not self.is_high_risk(action_name):
            return True, {
                "action": action_name,
                "requires_approval": False,
                "status": "allowed",
                "decision": None,
            }

        # High-risk action: evaluate approval signal
        signal = (approval_signal or "").strip().lower()

        if signal == "approve":
            return True, {
                "action": action_name,
                "requires_approval": True,
                "status": "allowed",
                "decision": "approved",
                "message": f"Action '{action_name}' was approved by human operator.",
            }
        elif signal == "reject":
            return False, {
                "action": action_name,
                "requires_approval": True,
                "status": "rejected",
                "decision": "rejected",
                "reason": "action_rejected_by_human",
                "message": f"Action '{action_name}' was explicitly rejected by human operator.",
            }
        else:
            return False, {
                "action": action_name,
                "requires_approval": True,
                "status": "pending_approval",
                "decision": "missing_approval",
                "reason": "human_approval_required",
                "message": f"Action '{action_name}' is high-risk and requires explicit human approval (--approval approve / --approval reject).",
            }
