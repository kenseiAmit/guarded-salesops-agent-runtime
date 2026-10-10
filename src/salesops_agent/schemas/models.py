from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class RunLogEntry(BaseModel):
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_input: str
    task_id: Optional[str] = None
    final_status: str # "success" | "blocked" | "failed" | "rejected"
    tools_called: List[str] = Field(default_factory=list)
    latency: float # seconds
    estimated_cost: float # USD
    guardrail_interventions: List[Dict[str, Any]] = Field(default_factory=list)
    hitl_decision: Optional[str] = None # "approved" | "rejected" | None
    failure_reason: Optional[str] = None

class TraceStep(BaseModel):
    step_id: int
    name: str
    input: Any
    output: Any
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ok" # "ok" | "blocked" | "error"
    error: Optional[str] = None

class TraceArtifact(BaseModel):
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    input: str
    selected_tools: List[str] = Field(default_factory=list)
    tool_arguments: List[Dict[str, Any]] = Field(default_factory=list)
    tool_outputs: List[Any] = Field(default_factory=list)
    guardrail_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    hitl_decision: Optional[str] = None
    final_output: str = ""
    error_messages: List[str] = Field(default_factory=list)
    steps: List[TraceStep] = Field(default_factory=list)

class EmailDraft(BaseModel):
    to: str
    subject: str
    body: str
    account_id: Optional[str] = None
    requires_approval: bool = True
    approved: Optional[bool] = None

class Account(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    health_score: Optional[int] = None
    contract_end_date: Optional[str] = None
    status: Optional[str] = None

class Opportunity(BaseModel):
    id: str
    account_id: str
    name: str
    stage: str
    amount: float
    close_date: Optional[str] = None
    type: Optional[str] = None

class SupportTicket(BaseModel):
    id: str
    account_id: str
    subject: str
    severity: str
    status: str
    created_at: Optional[str] = None

class ProductUsage(BaseModel):
    account_id: str
    active_users: int
    monthly_queries: int
    storage_gb: float
    last_login: Optional[str] = None
