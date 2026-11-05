from pathlib import Path
from typing import Any, Dict, List, Optional
import json
from datetime import datetime, timezone
from salesops_agent.schemas.models import RunLogEntry

class StructuredLogger:
    """Manages appending structured JSONL records to the run log."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path) if log_path else Path("logs/runs.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_run(
        self,
        run_id: str,
        user_input: str,
        final_status: str,
        latency: float,
        estimated_cost: float,
        tools_called: Optional[List[str]] = None,
        task_id: Optional[str] = None,
        guardrail_interventions: Optional[List[Dict[str, Any]]] = None,
        hitl_decision: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> RunLogEntry:
        """Constructs and persists a structured log entry."""
        entry = RunLogEntry(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_input=user_input,
            task_id=task_id,
            final_status=final_status,
            tools_called=tools_called or [],
            latency=round(latency, 4),
            estimated_cost=round(estimated_cost, 6),
            guardrail_interventions=guardrail_interventions or [],
            hitl_decision=hitl_decision,
            failure_reason=failure_reason,
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

        return entry

    def read_all_logs(self) -> List[RunLogEntry]:
        """Reads all logged runs from disk."""
        if not self.log_path.exists():
            return []
        
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(RunLogEntry(**data))
                except Exception:
                    continue
        return entries
