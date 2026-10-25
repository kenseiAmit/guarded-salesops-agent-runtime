from typing import Any, Dict, Optional, Tuple
from salesops_agent.schemas.guardrails import BlockedActionResponse, GuardrailResult, GuardrailType
from salesops_agent.tools.registry import is_restricted_tool, is_hitl_tool

class ToolGuardrail:
    """Application-level middleware intercepting tool calls before execution."""

    def __init__(self, policy: str = "salesops_data_access_policy"):
        self.policy = policy

    def check(self, tool_name: str, tool_args: Dict[str, Any], approval: Optional[str] = None) -> GuardrailResult:
        """Inspects tool name, arguments, and approval status before tool execution."""
        
        # 1. Block restricted internal tools (HR, financial strategy)
        if is_restricted_tool(tool_name) or tool_name in {"lookup_internal_hr_data", "lookup_internal_financial_data"}:
            return GuardrailResult(
                passed=False,
                guardrail_type=GuardrailType.TOOL,
                action="block",
                reason="restricted_internal_data",
                policy=self.policy,
                metadata={"tool_name": tool_name, "tool_args": tool_args},
            )

        # 2. Block unapproved email sending
        if tool_name == "send_email":
            if approval != "approve":
                return GuardrailResult(
                    passed=False,
                    guardrail_type=GuardrailType.TOOL,
                    action="block",
                    reason="unapproved_email_sending",
                    policy="salesops_hitl_approval_policy",
                    metadata={
                        "tool_name": tool_name,
                        "approval_provided": approval,
                        "status": "rejected" if approval == "reject" else "missing_approval",
                    },
                )

        # 3. Check for restricted field access in arguments
        arg_str = str(tool_args).lower()
        if "ceo bonus" in arg_str or "confidential_m_and_a" in arg_str or "internal_hr" in arg_str:
            return GuardrailResult(
                passed=False,
                guardrail_type=GuardrailType.TOOL,
                action="block",
                reason="restricted_internal_data",
                policy=self.policy,
                metadata={"tool_name": tool_name, "argument_leak": True},
            )

        return GuardrailResult(
            passed=True,
            guardrail_type=GuardrailType.TOOL,
            action="allow",
            policy=self.policy,
        )

    def enforce(
        self, tool_name: str, tool_args: Dict[str, Any], approval: Optional[str] = None
    ) -> Tuple[bool, Optional[BlockedActionResponse]]:
        result = self.check(tool_name, tool_args, approval=approval)
        if not result.passed:
            return False, BlockedActionResponse(
                status="blocked",
                reason=result.reason or "restricted_tool_call",
                policy=result.policy or self.policy,
                details=result.metadata,
            )
        return True, None
