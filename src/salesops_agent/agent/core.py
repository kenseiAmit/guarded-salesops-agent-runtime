import uuid
import time
import json
import re
from typing import Any, Dict, List, Optional
from salesops_agent.config.settings import get_settings, AgentSettings
from salesops_agent.prompts.loader import load_system_prompt
from salesops_agent.guardrails.input_guardrails import InputGuardrail
from salesops_agent.guardrails.tool_guardrails import ToolGuardrail
from salesops_agent.guardrails.output_guardrails import OutputGuardrail
from salesops_agent.hitl.gate import HITLGate
from salesops_agent.tools.crm_tools import (
    lookup_account,
    lookup_account_context,
    list_open_opportunities,
    summarize_pipeline,
)
from salesops_agent.tools.email_tool import draft_email, send_email
from salesops_agent.tools.restricted_tools import (
    lookup_internal_hr_data,
    lookup_internal_financial_data,
)
from salesops_agent.tools.sandbox_tool import CRMSandbox, execute_safe_data_analysis
from salesops_agent.observability.logger import StructuredLogger
from salesops_agent.observability.tracer import LocalTracer
from salesops_agent.state.persistence import StatePersistence
from salesops_agent.agent.llm_client import LLMClient
from salesops_agent.schemas.models import TraceStep

class SalesOpsAgent:
    """Production-grade SalesOps Agent orchestrator integrating multi-tier guardrails, HITL, and observability."""

    def __init__(self, settings: Optional[AgentSettings] = None):
        self.settings = settings or get_settings()
        prompt_ver = f"v{self.settings.version.split('.')[0]}" if not self.settings.version.startswith("v") else self.settings.version
        if prompt_ver not in ["v1"]:
            prompt_ver = "v1"
        self.system_prompt = load_system_prompt(prompt_ver)
        self.input_guardrail = InputGuardrail(self.settings.guardrails.blocked_action_policy)
        self.tool_guardrail = ToolGuardrail(self.settings.guardrails.blocked_action_policy)
        self.output_guardrail = OutputGuardrail(mode="block", policy=self.settings.guardrails.blocked_action_policy)
        self.hitl_gate = HITLGate(self.settings.hitl.require_approval_for)
        self.logger = StructuredLogger(self.settings.paths.logs_file)
        self.tracer = LocalTracer(self.settings.paths.traces_dir)
        self.persistence = StatePersistence()
        self.llm_client = LLMClient(
            api_key=self.settings.anthropic_api_key,
            base_url=self.settings.anthropic_base_url,
            model_name=self.settings.model.name,
            cost_per_m_in=self.settings.cost_estimation.input_token_cost_per_million,
            cost_per_m_out=self.settings.cost_estimation.output_token_cost_per_million,
            timeout_seconds=self.settings.model.timeout_seconds,
        )
        self.sandbox = CRMSandbox(timeout_seconds=self.settings.sandbox.timeout_seconds)

    def run(
        self,
        question: str,
        approval: Optional[str] = None,
        task_id: Optional[str] = None,
        user_id: str = "default_user",
        session_id: str = "default_session",
        thread_id: str = "default_thread",
        force_tool: Optional[str] = None,
        force_tool_args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Main entry point executing the agent workflow for a given question or tool invocation."""
        start_time = time.time()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        selected_tools: List[str] = []
        tool_args_list: List[Dict[str, Any]] = []
        tool_outputs: List[Any] = []
        guardrail_interventions: List[Dict[str, Any]] = []
        steps: List[TraceStep] = []
        errors: List[str] = []
        estimated_cost = 0.0
        final_answer = ""
        hitl_decision = None

        # ----------------------------------------------------
        # Step 1: Input Guardrail Check
        # ----------------------------------------------------
        input_result = self.input_guardrail.check(question)
        steps.append(TraceStep(
            step_id=1,
            name="input_guardrail",
            input={"question": question},
            output=input_result.to_dict(),
            status="blocked" if not input_result.passed else "ok",
        ))

        if not input_result.passed:
            intervention = {
                "guardrail": "input_guardrail",
                "action": "block",
                "reason": input_result.reason,
                "policy": input_result.policy,
            }
            guardrail_interventions.append(intervention)
            elapsed = time.time() - start_time
            final_status = "blocked"
            final_answer = f"Action blocked by policy [{input_result.policy}]: {input_result.reason}"

            # Log and Trace
            self.logger.log_run(
                run_id=run_id,
                user_input=question,
                task_id=task_id,
                final_status=final_status,
                tools_called=[],
                latency=elapsed,
                estimated_cost=0.0,
                guardrail_interventions=guardrail_interventions,
                hitl_decision=None,
                failure_reason=input_result.reason,
            )
            self.tracer.save_trace(
                run_id=run_id,
                user_input=question,
                selected_tools=[],
                tool_arguments=[],
                tool_outputs=[],
                guardrail_decisions=guardrail_interventions,
                hitl_decision=None,
                final_output=final_answer,
                error_messages=[f"Blocked by input guardrail: {input_result.reason}"],
                steps=steps,
            )
            self.persistence.record_run(run_id, user_id, session_id, thread_id, question, final_answer, final_status)
            
            return {
                "run_id": run_id,
                "status": "blocked",
                "reason": input_result.reason,
                "policy": input_result.policy,
                "answer": final_answer,
                "latency": round(elapsed, 4),
                "estimated_cost": 0.0,
                "guardrail_interventions": guardrail_interventions,
                "hitl_decision": None,
            }

        # ----------------------------------------------------
        # Step 2: Tool Planning & Action Dispatch
        # ----------------------------------------------------
        # Check if caller specified a specific tool to invoke (e.g. in test suites)
        tool_to_call = force_tool
        tool_args = force_tool_args or {}

        q_lower = question.lower()
        if not tool_to_call:
            if "lookup_internal_hr_data" in q_lower or "internal hr" in q_lower:
                tool_to_call = "lookup_internal_hr_data"
                tool_args = {"query": question}
            elif "lookup_internal_financial_data" in q_lower or "internal financial" in q_lower:
                tool_to_call = "lookup_internal_financial_data"
                tool_args = {"query": question}
            elif "send" in q_lower and "email" in q_lower:
                tool_to_call = "send_email"
                tool_args = {
                    "to": "contact@targetcompany.com",
                    "subject": "Follow-up",
                    "body": f"SalesOps follow-up regarding: {question}",
                }
            elif "draft" in q_lower and "email" in q_lower:
                tool_to_call = "draft_email"
                # Extract potential account name
                match = re.search(r"email to ([a-zA-Z0-9\.\s]+?)(?: about|$)", question, re.IGNORECASE)
                acc_name = match.group(1).strip() if match else "TechStart Inc."
                tool_args = {"account_name_or_id": acc_name, "purpose": question}
            elif "pipeline" in q_lower or "stage" in q_lower:
                tool_to_call = "summarize_pipeline"
                tool_args = {}
            elif "opportunity" in q_lower or "opportunities" in q_lower:
                tool_to_call = "list_open_opportunities"
                tool_args = {}
            elif "deal size" in q_lower or "average deal" in q_lower:
                tool_to_call = "safe_data_analysis"
                tool_args = {"query_type": "average_deal_size"}
            elif "severity" in q_lower or "support ticket" in q_lower:
                tool_to_call = "safe_data_analysis"
                tool_args = {"query_type": "tickets_by_severity"}
            elif "risk" in q_lower or "health" in q_lower or "account" in q_lower:
                tool_to_call = "lookup_account_context"
                # Attempt to extract account name
                acc = "TechStart Inc"
                for target in ["GlobalRetail Ltd", "TechStart Inc", "Acme Corp", "Apex Corp", "CloudScale"]:
                    if target.lower() in q_lower:
                        acc = target
                        break
                tool_args = {"account_name_or_id": acc}

        context_data = None
        if tool_to_call:
            selected_tools.append(tool_to_call)
            tool_args_list.append(tool_args)

            # Step 2a: Tool Guardrail Interception
            tool_guard_res = self.tool_guardrail.check(tool_to_call, tool_args, approval=approval)
            steps.append(TraceStep(
                step_id=2,
                name="tool_guardrail",
                input={"tool": tool_to_call, "args": tool_args, "approval": approval},
                output=tool_guard_res.to_dict(),
                status="blocked" if not tool_guard_res.passed else "ok",
            ))

            if not tool_guard_res.passed:
                intervention = {
                    "guardrail": "tool_guardrail",
                    "action": "block",
                    "reason": tool_guard_res.reason,
                    "policy": tool_guard_res.policy,
                    "tool": tool_to_call,
                }
                guardrail_interventions.append(intervention)
                final_status = "rejected" if approval == "reject" else "blocked"
                hitl_decision = "rejected" if approval == "reject" else ("missing_approval" if tool_to_call == "send_email" else None)
                failure_reason = tool_guard_res.reason
                final_answer = f"Action blocked by policy [{tool_guard_res.policy}]: {tool_guard_res.reason}"
                errors.append(final_answer)

                elapsed = time.time() - start_time
                self.logger.log_run(
                    run_id=run_id,
                    user_input=question,
                    task_id=task_id,
                    final_status=final_status,
                    tools_called=selected_tools,
                    latency=elapsed,
                    estimated_cost=0.0,
                    guardrail_interventions=guardrail_interventions,
                    hitl_decision=hitl_decision,
                    failure_reason=failure_reason,
                )
                self.tracer.save_trace(
                    run_id=run_id,
                    user_input=question,
                    selected_tools=selected_tools,
                    tool_arguments=tool_args_list,
                    tool_outputs=[{"status": "blocked", "reason": tool_guard_res.reason}],
                    guardrail_decisions=guardrail_interventions,
                    hitl_decision=hitl_decision,
                    final_output=final_answer,
                    error_messages=errors,
                    steps=steps,
                )
                self.persistence.record_run(run_id, user_id, session_id, thread_id, question, final_answer, final_status)
                
                return {
                    "run_id": run_id,
                    "status": final_status,
                    "reason": tool_guard_res.reason,
                    "policy": tool_guard_res.policy,
                    "answer": final_answer,
                    "latency": round(elapsed, 4),
                    "estimated_cost": 0.0,
                    "guardrail_interventions": guardrail_interventions,
                    "hitl_decision": hitl_decision,
                }

            # Step 2b: HITL Gate check for approved actions
            if self.hitl_gate.is_high_risk(tool_to_call):
                hitl_ok, hitl_meta = self.hitl_gate.evaluate_action(tool_to_call, tool_args, approval)
                hitl_decision = hitl_meta.get("decision")
                steps.append(TraceStep(
                    step_id=3,
                    name="hitl_gate",
                    input={"tool": tool_to_call, "approval": approval},
                    output=hitl_meta,
                    status="ok" if hitl_ok else "blocked",
                ))
                if not hitl_ok:
                    final_status = "rejected" if hitl_decision == "rejected" else "blocked"
                    final_answer = hitl_meta.get("message", "High risk action requires approval.")
                    elapsed = time.time() - start_time
                    self.logger.log_run(
                        run_id=run_id,
                        user_input=question,
                        task_id=task_id,
                        final_status=final_status,
                        tools_called=selected_tools,
                        latency=elapsed,
                        estimated_cost=0.0,
                        guardrail_interventions=guardrail_interventions,
                        hitl_decision=hitl_decision,
                        failure_reason=hitl_meta.get("reason"),
                    )
                    self.tracer.save_trace(
                        run_id=run_id,
                        user_input=question,
                        selected_tools=selected_tools,
                        tool_arguments=tool_args_list,
                        tool_outputs=[hitl_meta],
                        guardrail_decisions=guardrail_interventions,
                        hitl_decision=hitl_decision,
                        final_output=final_answer,
                        error_messages=[hitl_meta.get("message", "")],
                        steps=steps,
                    )
                    return {
                        "run_id": run_id,
                        "status": final_status,
                        "reason": hitl_meta.get("reason"),
                        "answer": final_answer,
                        "latency": round(elapsed, 4),
                        "estimated_cost": 0.0,
                    }

            # Step 2c: Execute the Tool Safely
            try:
                if tool_to_call == "lookup_account":
                    res = lookup_account(**tool_args)
                elif tool_to_call == "lookup_account_context":
                    res = lookup_account_context(**tool_args)
                elif tool_to_call == "list_open_opportunities":
                    res = list_open_opportunities(**tool_args)
                elif tool_to_call == "summarize_pipeline":
                    res = summarize_pipeline()
                elif tool_to_call == "draft_email":
                    res = draft_email(**tool_args)
                elif tool_to_call == "send_email":
                    res = send_email(approved=True, **tool_args)
                elif tool_to_call == "safe_data_analysis":
                    res = execute_safe_data_analysis(**tool_args)
                elif tool_to_call == "sandboxed_code":
                    res = self.sandbox.run_analysis(tool_args.get("code", ""))
                else:
                    res = {"error": f"Unknown tool: {tool_to_call}"}
                
                tool_outputs.append(res)
                context_data = res
                steps.append(TraceStep(
                    step_id=4,
                    name=f"tool_execution_{tool_to_call}",
                    input=tool_args,
                    output=res,
                    status="ok" if "error" not in res else "error",
                ))
            except Exception as e:
                err_msg = f"Tool execution failed: {e}"
                errors.append(err_msg)
                tool_outputs.append({"error": err_msg})

        # ----------------------------------------------------
        # Step 3: LLM Generation / Synthesis
        # ----------------------------------------------------
        if context_data:
            context_snippet = json.dumps(context_data, default=str, indent=2)[:3000]
            unified_content = f"Relevant CRM Context Data:\n{context_snippet}\n\nUser Question:\n{question}"
            messages = [{"role": "user", "content": unified_content}]
        else:
            messages = [{"role": "user", "content": question}]

        llm_response = self.llm_client.generate(
            messages=messages,
            system_prompt=self.system_prompt,
            max_tokens=self.settings.model.max_tokens,
            temperature=self.settings.model.temperature,
        )
        estimated_cost = llm_response.estimated_cost
        raw_output = llm_response.content
        steps.append(TraceStep(
            step_id=5,
            name="llm_generation",
            input={"messages": messages},
            output={"content": raw_output, "tokens": llm_response.input_tokens + llm_response.output_tokens},
            status="ok",
        ))

        # ----------------------------------------------------
        # Step 4: Output Guardrail Verification
        # ----------------------------------------------------
        out_passed, safe_output, out_blocked = self.output_guardrail.enforce(raw_output)
        steps.append(TraceStep(
            step_id=6,
            name="output_guardrail",
            input={"raw_output": raw_output},
            output={"safe_output": safe_output, "passed": out_passed},
            status="ok" if out_passed else "blocked",
        ))

        if not out_passed and out_blocked:
            intervention = {
                "guardrail": "output_guardrail",
                "action": "block",
                "reason": out_blocked.reason,
                "policy": out_blocked.policy,
            }
            guardrail_interventions.append(intervention)
            final_status = "blocked"
            final_answer = safe_output
            failure_reason = out_blocked.reason
            errors.append(f"Output blocked by policy: {out_blocked.reason}")
            # Defense-in-depth: scrub sensitive raw content from trace steps
            for step in steps:
                if step.name == "llm_generation" and isinstance(step.output, dict):
                    step.output["content"] = "[REDACTED_SENSITIVE_OUTPUT]"
                if step.name == "output_guardrail" and isinstance(step.input, dict):
                    step.input["raw_output"] = "[REDACTED_SENSITIVE_OUTPUT]"
        else:
            final_status = "success"
            final_answer = safe_output
            failure_reason = None

        elapsed = time.time() - start_time

        # ----------------------------------------------------
        # Step 5: Logging, Tracing & State Persistence
        # ----------------------------------------------------
        self.logger.log_run(
            run_id=run_id,
            user_input=question,
            task_id=task_id,
            final_status=final_status,
            tools_called=selected_tools,
            latency=elapsed,
            estimated_cost=estimated_cost,
            guardrail_interventions=guardrail_interventions,
            hitl_decision=hitl_decision,
            failure_reason=failure_reason,
        )

        self.tracer.save_trace(
            run_id=run_id,
            user_input=question,
            selected_tools=selected_tools,
            tool_arguments=tool_args_list,
            tool_outputs=tool_outputs,
            guardrail_decisions=guardrail_interventions,
            hitl_decision=hitl_decision,
            final_output=final_answer,
            error_messages=errors,
            steps=steps,
        )

        self.persistence.record_run(run_id, user_id, session_id, thread_id, question, final_answer, final_status)

        return {
            "run_id": run_id,
            "status": final_status,
            "answer": final_answer,
            "tools_called": selected_tools,
            "latency": round(elapsed, 4),
            "estimated_cost": estimated_cost,
            "guardrail_interventions": guardrail_interventions,
            "hitl_decision": hitl_decision,
        }
