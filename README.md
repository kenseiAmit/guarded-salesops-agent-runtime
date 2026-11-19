# Guarded SalesOps Agent Runtime

[![CI Pipeline](https://github.com/kenseiAmit/guarded-salesops-agent-runtime/actions/workflows/ci.yml/badge.svg)](https://github.com/kenseiAmit/guarded-salesops-agent-runtime/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Package Manager: uv](https://img.shields.io/badge/package%20manager-uv-purple.svg)](https://docs.astral.sh/uv/)
[![Evaluation Pass Rate](https://img.shields.io/badge/eval%20suite-14%2F14%20(100%25)-brightgreen.svg)](reports/evaluation_report.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, observable, and multi-tier guarded AI agent runtime for B2B Sales Operations (**NexaCRM**). Rather than relying solely on system prompts for safety, this runtime enforces security policies deterministically in application code—combining **input/tool/output guardrails**, **AST-constrained CRM code sandboxing**, **human-in-the-loop (HITL) approval gates**, **multi-tenant SQLite state isolation**, **recursive PII/secret trace redaction**, and **automated regression evaluation**.

---

## Why Application-Layer Guardrails?

Unconstrained LLM prototypes in enterprise CRM environments suffer from critical failure modes:
1. **Unrestricted Tool & Data Exposure:** Direct tool bindings risk exposing internal HR payroll, executive compensation, PIPs, or confidential M&A strategy alongside standard CRM accounts.
2. **Prompt Injection & Paraphrase Leaks:** System-prompt instructions alone cannot guarantee refusal against adversarial overrides or subtle output leaks.
3. **Ungated High-Risk Side Effects:** Autonomous external customer emails require explicit human authorization before dispatch.
4. **Unsafe Analytical Code Execution:** Dynamic Python aggregations over CRM tables must be syntactically constrained without `import`, filesystem, or builtin escape paths.
5. **Auditability & Redaction:** Every run requires structured telemetry (`runs.jsonl`) and step-level traces with recursive secret/PII scrubbing prior to disk serialization.

---

## System Architecture

```mermaid
flowchart TD
    User([User Request / CLI]) --> InputGuard[1. Application-Level Input Guardrail]

    InputGuard -- Blocked Prompt --> BlockedLog[Structured Run Logger]
    InputGuard -- Passed --> Planner[2. SalesOps Orchestrator]

    Planner --> ToolRouter{Tool Selection}

    ToolRouter -- Restricted Tool HR/Financial --> ToolGuard[3. Tool Interception Guardrail]
    ToolGuard -- Blocked Action --> BlockedLog

    ToolRouter -- High-Risk Action: send_email --> HITLGate{4. HITL Approval Gate}
    HITLGate -- Missing Approval / Reject --> BlockedLog
    HITLGate -- Approved --> EmailTool[Execute Email Dispatch]

    ToolRouter -- Safe Analytical Code --> Sandbox[5. AST-Constrained CRM Sandbox]
    ToolRouter -- Safe CRM Query --> SafeTools[6. Safe CRM Tools Store]

    EmailTool --> LLMSynth[7. LLM Synthesis Anthropic Claude / Deterministic Fallback]
    Sandbox --> LLMSynth
    SafeTools --> LLMSynth

    LLMSynth --> OutputGuard[8. Output Guardrail / Redaction]
    OutputGuard -- Leak Detected --> RedactBlock[Block / Scrub Trace Payload]
    OutputGuard -- Safe Response --> FinalOut([Structured Response])
    RedactBlock --> FinalOut

    FinalOut --> Observability[9. Observability: JSONL Run Log + Redacted Traces]
    Observability --> StateDB[(10. SQLite State Store: Session Isolation)]
```

### Repository Layout

```text
.
├── pyproject.toml              # Package metadata & CLI entry points
├── uv.lock                     # Deterministic dependency lockfile
├── Dockerfile                  # Non-root containerized runtime image
├── .env.example                # Environment variable configuration template
├── .github/workflows/ci.yml    # Automated pytest, evaluation, and monitoring CI
├── data/                       # Normalized CRM datasets (accounts, opportunities, tickets, restricted fixtures)
├── logs/runs.jsonl             # Append-only structured telemetry log
├── reports/
│   ├── evaluation_report.md    # 14-scenario automated security & functional benchmark report
│   ├── evaluation_report.json  # Machine-readable evaluation telemetry
│   └── monitoring_report.md    # Aggregated operational KPI & guardrail dashboard
├── src/salesops_agent/
│   ├── cli.py                  # CLI commands (ask, evaluate, generate-monitoring-report)
│   ├── agent/
│   │   ├── core.py             # Guarded SalesOps orchestrator
│   │   └── llm_client.py       # Anthropic Messages API client + offline deterministic fallback
│   ├── config/
│   │   ├── agent_config.yaml   # Versioned runtime policy & cost configuration
│   │   └── settings.py         # Typed Pydantic configuration loader
│   ├── evaluation/evaluator.py # 14-scenario automated regression & security harness
│   ├── guardrails/
│   │   ├── input_guardrails.py # Pre-inference prompt injection & restricted topic filter
│   │   ├── tool_guardrails.py  # Pre-execution tool interception middleware
│   │   └── output_guardrails.py# Post-inference leak detection & redaction
│   ├── hitl/gate.py            # Human-in-the-loop approval enforcement
│   ├── observability/
│   │   ├── logger.py           # Structured JSONL run logger
│   │   ├── tracer.py           # Step-level trace serializer with recursive redaction
│   │   └── metrics.py          # Operational KPI & guardrail report generator
│   ├── prompts/                # Versioned system prompt loader (v1.0.0)
│   ├── schemas/                # Pydantic schemas for CRM records, guardrails, and traces
│   ├── state/persistence.py    # SQLite session store isolated by (user_id, session_id, thread_id)
│   └── tools/
│       ├── crm_store.py        # Normalized CRM store & fuzzy entity resolution
│       ├── crm_tools.py        # Approved read-only CRM tools
│       ├── email_tool.py       # Draft & HITL-gated email dispatch tools
│       ├── restricted_tools.py # Restricted HR/financial tools (intercepted by ToolGuardrail)
│       └── sandbox_tool.py     # AST-validated Python analytics sandbox
└── tests/
    └── test_evaluation.py      # End-to-end pytest unit, security, redaction & benchmark suite
```

---

## Defense-in-Depth Controls

### 1. Multi-Tier Application Guardrails
- **Input Guardrail ([`input_guardrails.py`](src/salesops_agent/guardrails/input_guardrails.py)):** Blocks queries probing executive compensation, layoff plans, employee PIPs/terminations, confidential M&A, and prompt-injection overrides prior to model invocation.
- **Tool Guardrail ([`tool_guardrails.py`](src/salesops_agent/guardrails/tool_guardrails.py)):** Middleware intercepting restricted tool calls (`lookup_internal_hr_data`, `lookup_internal_financial_data`), sensitive argument payloads, and unapproved outbound side effects.
- **Output Guardrail ([`output_guardrails.py`](src/salesops_agent/guardrails/output_guardrails.py)):** Post-generation verifier supporting both `block` and `redact` enforcement across compensation, RIF/layoffs, HR performance reviews, and M&A disclosures.

### 2. AST-Constrained CRM Code Sandbox ([`sandbox_tool.py`](src/salesops_agent/tools/sandbox_tool.py))
- Parses candidate Python snippets via `ast` prior to execution, rejecting `Import`, `ImportFrom`, dangerous builtins (`eval`, `exec`, `open`, `compile`, `__import__`), dunder traversal (`__subclasses__`, `__dict__`), and restricted identifiers.
- Executes strictly against deep-copied approved CRM collections (`accounts`, `opportunities`, `contacts`, `support_tickets`, `product_usage`) with wall-clock timeout enforcement.

### 3. Human-in-the-Loop Gate ([`gate.py`](src/salesops_agent/hitl/gate.py))
- Outbound customer emails cannot execute autonomously:
  - `--approval approve`: Dispatches drafted email to `data/email_outbox.json` (`final_status="success"`, `hitl_decision="approved"`).
  - `--approval reject`: Halts transmission (`final_status="rejected"`, `failure_reason="action_rejected_by_human"`).
  - Omitted flag: Blocks execution with `hitl_decision="missing_approval"`.

### 4. Observability & Recursive Trace Redaction ([`tracer.py`](src/salesops_agent/observability/tracer.py))
- Appends structured telemetry (`run_id`, `latency`, `estimated_cost`, `tools_called`, `guardrail_interventions`, `hitl_decision`) to `logs/runs.jsonl`.
- Recursively scrubs credentials, API keys, executive salaries, layoff notes, PIP details, and M&A strings across all trace steps before writing `traces/<run_id>.json`.

---

## Quick Start

### Installation
```bash
git clone https://github.com/kenseiAmit/guarded-salesops-agent-runtime.git
cd guarded-salesops-agent-runtime

# Install editable package with uv (or pip install -e .)
uv pip install -e .
```

### Configuration (Optional)
The runtime includes a deterministic offline fallback mode so all tests, guardrails, and evaluations run out of the box with zero API cost. To connect live Anthropic Claude inference:
```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY=sk-ant-...
```

### 5-Second Interactive Walkthrough (`make demo`)
Run all defense-in-depth layers end-to-end in a single command (zero API keys required):
```bash
make demo
# or: uv run python examples/demo_walkthrough.py
