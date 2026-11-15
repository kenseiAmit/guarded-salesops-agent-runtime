# SalesOps Agent Operational Monitoring Report

**Generated:** 2026-11-15 17:42:18 UTC  
**Environment:** Production  
**Reporting Scope:** Aggregated runs from `logs/runs.jsonl`

---

## 1. Executive Summary & KPIs

| Metric | Value |
|:---|:---|
| **Total Processed Runs** | **237** |
| **Successful Runs** | 118 (49.79%) |
| **Failed Runs** | 0 (0.0%) |
| **Blocked Runs (Guardrails)** | 89 |
| **Rejected Runs (HITL)** | 30 |
| **Average Latency** | **0.0103s** |
| **Estimated Total Cost** | **$0.133820** |
| **Estimated Avg Cost / Run** | **$0.000565** |

---

## 2. Runtime Guardrails & Human-in-the-Loop Interventions

- **Total Guardrail Interventions:** `119`
- **HITL Approvals Granted:** `30`
- **HITL Rejections Enforced:** `30`

All unauthorized access attempts to internal HR/financial strategy data or unsafe output leaks were intercepted at the application layer with zero unauthorized transmissions.

---

## 3. Tool Usage Statistics

| Tool Name | Invocations |
|:---|:---|
| `send_email` | 61 |
| `lookup_account_context` | 30 |
| `summarize_pipeline` | 30 |
| `list_open_opportunities` | 28 |
| `lookup_internal_hr_data` | 27 |

---

## 4. Failure and Interception Diagnostics

| Failure / Interception Reason | Count |
|:---|:---|
| `unapproved_email_sending` | 31 |
| `restricted_input_executive_compensation` | 30 |
| `restricted_input_layoffs_and_terminations` | 28 |
| `restricted_internal_data` | 27 |
| `sensitive_output_executive_compensation` | 2 |
| `restricted_input_restricted_hr_data` | 1 |

---

## 5. Trace Inspection & Runbook

To inspect the detailed trajectory and payload of any specific run:
1. Identify the `run_id` from `logs/runs.jsonl`.
2. Inspect `traces/<run_id>.json` for step-by-step telemetry with sensitive credentials and compensation redacted.
