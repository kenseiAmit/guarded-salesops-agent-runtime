from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class GuardrailStatus(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    REDACTED = "redacted"
    PENDING_APPROVAL = "pending_approval"

class GuardrailType(str, Enum):
    INPUT = "input"
    TOOL = "tool"
    OUTPUT = "output"

class BlockedActionResponse(BaseModel):
    status: str = "blocked"
    reason: str
    policy: str = "salesops_data_access_policy"
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "policy": self.policy,
        }

class GuardrailResult(BaseModel):
    passed: bool
    guardrail_type: GuardrailType
    action: str = "allow" # "allow", "block", "redact"
    reason: Optional[str] = None
    policy: Optional[str] = "salesops_data_access_policy"
    sanitized_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "guardrail_type": self.guardrail_type.value if hasattr(self.guardrail_type, "value") else str(self.guardrail_type),
            "action": self.action,
            "reason": self.reason,
            "policy": self.policy,
            "sanitized_text": self.sanitized_text,
            "metadata": self.metadata,
        }
