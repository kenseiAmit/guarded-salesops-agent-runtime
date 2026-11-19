# Architecture Decision Records (ADRs)

## ADR-001: Deterministic Middleware Guardrails vs. Prompt-Only Safety
- **Context:** System-prompt instructions (`"Never disclose HR salaries or M&A plans"`) are vulnerable to jailbreaks, indirect prompt injections, and model drift.
- **Decision:** Implement three independent Python enforcement layers (`InputGuardrail`, `ToolGuardrail`, `OutputGuardrail`) around the orchestrator so unauthorized tool calls (`lookup_internal_hr_data`, `lookup_internal_financial_data`) and sensitive output leaks are intercepted deterministically in application code.
- **Consequence:** Policy enforcement remains 100% deterministic (`0` tokens spent on blocked inputs) and testable offline via `pytest`.

## ADR-002: AST Validation Before Dynamic CRM Analytics Execution
- **Context:** Revenue operations users frequently ask ad-hoc aggregation questions across opportunities and tickets that benefit from Python expressions.
- **Decision:** Parse candidate code into a Python Abstract Syntax Tree (`ast.parse`) inside `CRMSandbox` prior to evaluation, rejecting `Import`/`ImportFrom`, dunder attribute access, and dangerous builtins (`eval`, `exec`, `open`, `__import__`), while injecting deep copies of approved CRM datasets only.
- **Consequence:** Analytical aggregations execute in milliseconds with zero risk of filesystem read/write or restricted HR dataset exposure.

## ADR-003: Pre-Serialization Recursive Trace Redaction
- **Context:** Even when `OutputGuardrail` blocks a response from reaching the caller, naive observability pipelines accidentally persist the raw model output inside trace JSON files on disk.
- **Decision:** `LocalTracer.save_trace()` recursively scrubs all strings, dictionaries, lists, tool outputs, and error payloads against `SENSITIVE_PATTERNS` *before* JSON serialization (`verified by test_trace_redaction_recursively_covers_all_fields`).
- **Consequence:** Diagnostic traces remain safe to inspect without secondary PII/compensation leakage.

## ADR-004: Explicit Human-in-the-Loop (HITL) Gate for External Side Effects
- **Context:** Autonomous customer emails create legal and commercial risk if hallucinated commitments are sent externally.
- **Decision:** Separate `draft_email` (read-only composition) from `send_email` (side-effecting action gated by `HITLGate`), requiring explicit `--approval approve` authorization.
