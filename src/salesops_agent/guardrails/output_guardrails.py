import re
from typing import Optional, Tuple
from salesops_agent.schemas.guardrails import BlockedActionResponse, GuardrailResult, GuardrailType

# Sensitive patterns that must never leak to users in generated responses
SENSITIVE_OUTPUT_PATTERNS = [
    # Executive compensation / Marcus Thorne equity bonus
    (
        r"\b(marcus thorne|ceo|executive|chief\s+executive)\b.*\b(\$[0-9]+[kmbKMB]?|\bbonus\b|\bequity bonus\b|\bsalary\b|\bcompensation\b|\bseverance\b)",
        "executive_compensation",
    ),
    (r"\b(\$[0-9]+[kmbKMB]?\s*(equity\s*)?bonus)\b", "executive_compensation"),
    (r"\bexecutive\s+compensation\b", "executive_compensation"),
    (r"\bretention\s+bonus\b", "executive_compensation"),

    # Layoffs, downsizing & workforce reductions
    (
        r"\b(lay(ing)?\s+off(\s+\w+)?|laid\s+off|layoffs?|future\s+layoffs?|planned\s+layoffs?|workforce\s+reduction|reduction\s+in\s+force|\brif\b|downsizing|downsize|downsizing\s+schedule|job\s+cuts?|cutting\s+jobs|staff\s+reductions?|severance\s+(package|plan|agreement)s?|headcount\s+reduction)\b",
        "layoff_plans",
    ),

    # Employee performance, PIPs & terminations
    (
        r"\b((poor|low|bad|negative|failing|unsatisfactory)\s+(employee\s+)?performance(\s+review|\s+rating)?|employee\s+performance\s+review|performance\s+improvement\s+plan|\bpip\s+list\b|\bpip\b|underperforming\s+employee|underperformance|employee\s+termination|terminat(ing|ion)\s+(of\s+)?(an\s+)?employee|firing\s+(an\s+)?employee|termination\s+list|disciplinary\s+action)\b",
        "employee_performance_or_termination",
    ),

    # Confidential M&A, mergers & competitor acquisitions
    (
        r"\b(merg(ing|er)\s+with(\s+a\s+competitor|\s+\w+)?|merger\s+(negotiations?|discussions?|talks?|agreement|deal)|confidential.*acquisition|acquir(ing|e|ition)\s+(of\s+)?(\w+\s+)?competitor|acquisition\s+of\s+acme|acquiring\s+acme|corporate\s+takeover|hostile\s+takeover|buyout\s+of|m&a\s+(discussions?|deal|targets?))\b",
        "confidential_m_and_a",
    ),

    # Internal strategy & financial targets
    (
        r"\b(confidential strategy|internal financial target|undisclosed revenue goal|internal financial data)\b",
        "internal_strategy",
    ),
]

class OutputGuardrail:
    """Application-level inspector checking agent output before returning to user."""

    def __init__(self, mode: str = "block", policy: str = "salesops_data_access_policy"):
        """mode: 'block' blocks the output entirely; 'redact' redacts the sensitive substrings."""
        self.mode = mode
        self.policy = policy

    def check(self, response_text: str) -> GuardrailResult:
        """Inspects response text and detects sensitive data leakage."""
        lower_text = response_text.lower()
        
        for pattern, category in SENSITIVE_OUTPUT_PATTERNS:
            if re.search(pattern, lower_text):
                if self.mode == "redact":
                    # Redact matched text
                    redacted_text = re.sub(
                        pattern, "[REDACTED: SENSITIVE_CONFIDENTIAL_INFO]", response_text, flags=re.IGNORECASE
                    )
                    return GuardrailResult(
                        passed=False,
                        guardrail_type=GuardrailType.OUTPUT,
                        action="redact",
                        reason=f"sensitive_output_{category}",
                        policy=self.policy,
                        sanitized_text=redacted_text,
                        metadata={"category": category},
                    )
                else:
                    return GuardrailResult(
                        passed=False,
                        guardrail_type=GuardrailType.OUTPUT,
                        action="block",
