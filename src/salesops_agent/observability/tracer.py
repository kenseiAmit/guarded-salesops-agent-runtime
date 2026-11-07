from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re
from datetime import datetime, timezone
from salesops_agent.schemas.models import TraceArtifact, TraceStep

SENSITIVE_PATTERNS = [
    # Credentials, secrets, tokens, API keys
    (r"\b(password|api_key|secret|token|bearer|auth)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?", "[REDACTED_CREDENTIAL]"),
    (r"\bsk-(?:ant-)?[0-9a-zA-Z_-]{16,}\b", "[REDACTED_API_KEY]"),
    (r"\bASIA[0-9A-Z]{16,}\b", "[REDACTED_AWS_KEY]"),

    # Executive compensation / Marcus Thorne
    (
        r"\b(marcus thorne|ceo|executive|chief\s+executive)\b.*\b(\$[0-9]+[kmbKMB]?|\bbonus\b|\bequity bonus\b|\bsalary\b|\bcompensation\b|\bseverance\b)",
        "[REDACTED_EXECUTIVE_SALARY]",
    ),
    (r"\b(\$[0-9]+[kmbKMB]?\s*(equity\s*)?bonus)\b", "[REDACTED_COMPENSATION]"),
    (r"\bexecutive\s+compensation\b", "[REDACTED_COMPENSATION]"),
    (r"\bretention\s+bonus\b", "[REDACTED_COMPENSATION]"),

    # Layoffs, downsizing & workforce reductions
    (
        r"\b(lay(ing)?\s+off(\s+\w+)?|laid\s+off|layoffs?|future\s+layoffs?|planned\s+layoffs?|workforce\s+reduction|reduction\s+in\s+force|\brif\b|downsizing|downsize|job\s+cuts?|cutting\s+jobs|staff\s+reductions?|severance\s+(package|plan|agreement)s?|headcount\s+reduction)\b",
        "[REDACTED_LAYOFF_INFO]",
    ),

    # Employee performance, PIPs & terminations
    (
        r"\b((poor|low|bad|negative|failing|unsatisfactory)\s+(employee\s+)?performance(\s+review|\s+rating)?|employee\s+performance\s+review|performance\s+improvement\s+plan|\bpip\s+list\b|\bpip\b|underperforming\s+employee|underperformance|employee\s+termination|terminat(ing|ion)\s+(of\s+)?(an\s+)?employee|firing\s+(an\s+)?employee|termination\s+list|disciplinary\s+action)\b",
        "[REDACTED_PERFORMANCE_INFO]",
    ),

    # Confidential M&A, mergers & competitor acquisitions
    (
        r"\b(merg(ing|er)\s+with(\s+a\s+competitor|\s+\w+)?|merger\s+(negotiations?|discussions?|talks?|agreement|deal)|confidential.*acquisition|acquir(ing|e|ition)\s+(of\s+)?(\w+\s+)?competitor|acquisition\s+of\s+acme|acquiring\s+acme|corporate\s+takeover|hostile\s+takeover|buyout\s+of|m&a\s+(discussions?|deal|targets?))\b",
        "[REDACTED_MA_INFO]",
    ),

    # Sensitive internal identifiers
    (r"\b(internal_hr_data|internal_financial_data)\b", "[REDACTED_INTERNAL_IDENTIFIER]"),
]

def redact_sensitive_data(obj: Any) -> Any:
    """Recursively redacts sensitive patterns from objects before trace serialization."""
    if isinstance(obj, str):
        text = obj
        for pattern, replacement in SENSITIVE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
    elif isinstance(obj, dict):
        redacted_dict = {}
        for k, v in obj.items():
            # If key contains sensitive markers, redact value
            if any(term in k.lower() for term in ["password", "secret", "token", "internal_hr", "financial_data"]):
                redacted_dict[k] = "[REDACTED_CONFIDENTIAL_FIELD]"
            else:
                redacted_dict[k] = redact_sensitive_data(v)
        return redacted_dict
    elif isinstance(obj, list):
        return [redact_sensitive_data(item) for item in obj]
    else:
        return obj

class LocalTracer:
    """Manages building and saving detailed local execution traces for each run."""

    def __init__(self, traces_dir: Optional[Path] = None):
        self.traces_dir = Path(traces_dir) if traces_dir else Path("traces")
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def save_trace(
        self,
        run_id: str,
        user_input: str,
        selected_tools: Optional[List[str]] = None,
        tool_arguments: Optional[List[Dict[str, Any]]] = None,
        tool_outputs: Optional[List[Any]] = None,
        guardrail_decisions: Optional[List[Dict[str, Any]]] = None,
        hitl_decision: Optional[str] = None,
        final_output: str = "",
        error_messages: Optional[List[str]] = None,
        steps: Optional[List[TraceStep]] = None,
    ) -> Path:
        """Serializes and saves a local trace artifact to traces/<run_id>.json.
        
        Applies comprehensive recursive redaction across the entire trace data structure,
        including all step inputs, step outputs, tool payloads, and error messages.
        """
        # Build initial TraceArtifact object
        trace = TraceArtifact(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input=user_input,
            selected_tools=selected_tools or [],
            tool_arguments=tool_arguments or [],
            tool_outputs=tool_outputs or [],
            guardrail_decisions=guardrail_decisions or [],
            hitl_decision=hitl_decision,
            final_output=final_output,
            error_messages=error_messages or [],
            steps=steps or [],
        )

        # Convert to dictionary and recursively redact all fields, steps, and messages
        trace_dict = trace.model_dump()
        redacted_trace_dict = redact_sensitive_data(trace_dict)

        trace_file = self.traces_dir / f"{run_id}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(redacted_trace_dict, f, indent=2)

        return trace_file
