import re
from typing import Optional, Tuple
from salesops_agent.schemas.guardrails import BlockedActionResponse, GuardrailResult, GuardrailType

# Pattern definitions for restricted domains
RESTRICTED_INPUT_PATTERNS = [
    # Executive compensation
    (r"\b(ceo|executive|c-suite|cfo|cro)\b.*\b(bonus|compensation|salary|equity|pay|package)\b", "executive_compensation"),
    (r"\b(bonus|compensation|salary|equity)\b.*\b(ceo|executive|marcus thorne)\b", "executive_compensation"),
    
    # Layoffs & terminations
    (r"\b(layoff|layoffs|downsizing|firing|fired|terminated|termination|severance)\b", "layoffs_and_terminations"),
    (r"\b(performance improvement plan|pip)\b", "employee_performance_or_pip"),
    
    # M&A and confidential strategy
    (r"\b(acquiring|acquisition|merger|m&a|takeover)\b.*\b(acme|corp|competitor)\b", "confidential_m_and_a"),
    (r"\b(acme corp)\b.*\b(acquiring|acquisition|buyout)\b", "confidential_m_and_a"),
    (r"\b(confidential strategy|internal financial data|internal financial strategy)\b", "confidential_financial_strategy"),
    
    # Internal HR data
    (r"\b(internal hr|hr data|employee records|personnel file)\b", "restricted_hr_data"),
    
    # Prompt injection & jailbreaks
    (r"\b(ignore|disregard|bypass|override)\b.*\b(previous|prior|all|system)\b.*\b(instructions|rules|prompts|directives)\b", "prompt_injection"),
    (r"\b(reveal|show|print|leak|output)\b.*\b(hidden|system|confidential|secret)\b.*\b(prompt|instructions|rules)\b", "prompt_injection"),
]

class InputGuardrail:
    """Application-level interceptor inspecting user input prior to agent invocation."""

    def __init__(self, policy: str = "salesops_data_access_policy"):
        self.policy = policy

    def check(self, prompt: str) -> GuardrailResult:
        """Inspects user prompt for restricted topics or prompt injection."""
        text = prompt.strip()
        lower_text = text.lower()

        for pattern, category in RESTRICTED_INPUT_PATTERNS:
            if re.search(pattern, lower_text):
                reason = f"restricted_input_{category}"
                return GuardrailResult(
                    passed=False,
                    guardrail_type=GuardrailType.INPUT,
                    action="block",
                    reason=reason,
                    policy=self.policy,
                    metadata={"matched_category": category, "prompt": prompt},
                )

        return GuardrailResult(
            passed=True,
            guardrail_type=GuardrailType.INPUT,
            action="allow",
            policy=self.policy,
        )

    def enforce(self, prompt: str) -> Tuple[bool, Optional[BlockedActionResponse]]:
        """Convenience method returning (allowed, blocked_response)."""
        result = self.check(prompt)
        if not result.passed:
            return False, BlockedActionResponse(
                status="blocked",
                reason=result.reason or "restricted_input_prompt",
                policy=self.policy,
                details={"input": prompt},
            )
        return True, None
