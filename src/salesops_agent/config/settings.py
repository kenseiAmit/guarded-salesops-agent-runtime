from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import yaml
from pydantic import BaseModel, Field

CONFIG_FILE_PATH = Path(__file__).parent / "agent_config.yaml"

class ModelConfig(BaseModel):
    provider: str = "anthropic"
    name: str = "claude-sonnet-4-6"
    temperature: float = 0.1
    max_tokens: int = 1024
    timeout_seconds: float = 30.0

class CostConfig(BaseModel):
    input_token_cost_per_million: float = 3.00
    output_token_cost_per_million: float = 15.00

class PathsConfig(BaseModel):
    data_dir: Path = Path("data")
    logs_file: Path = Path("logs/runs.jsonl")
    traces_dir: Path = Path("traces")
    reports_dir: Path = Path("reports")
    evaluation_report_md: Path = Path("reports/evaluation_report.md")
    evaluation_report_json: Path = Path("reports/evaluation_report.json")
    monitoring_report_md: Path = Path("reports/monitoring_report.md")

class GuardrailsConfig(BaseModel):
    input_guardrails_enabled: bool = True
    tool_guardrails_enabled: bool = True
    output_guardrails_enabled: bool = True
    blocked_action_policy: str = "salesops_data_access_policy"
    restricted_terms: List[str] = Field(default_factory=list)

class HITLConfig(BaseModel):
    require_approval_for: List[str] = Field(default_factory=lambda: ["send_email"])
    default_action_on_missing_flag: str = "require_explicit"

class SandboxConfig(BaseModel):
    timeout_seconds: float = 5.0
    max_output_length: int = 5000
    blocked_builtins: List[str] = Field(default_factory=list)
    restricted_modules: List[str] = Field(default_factory=list)

class AgentSettings(BaseModel):
    version: str = "1.0.0"
    environment: str = "production"
    model: ModelConfig = Field(default_factory=ModelConfig)
    cost_estimation: CostConfig = Field(default_factory=CostConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    hitl: HITLConfig = Field(default_factory=HITLConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)

    # API credentials loaded from environment
    anthropic_api_key: Optional[str] = None
    anthropic_base_url: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_default_region: Optional[str] = None

def _load_env_file():
    """Simple parser for .env file to avoid heavy dotenv dependency if needed."""
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            if k not in os.environ:
                os.environ[k] = v

def get_settings() -> AgentSettings:
    """Load settings from YAML config file with environment variable overlays."""
    _load_env_file()
    
    raw_config: Dict[str, Any] = {}
    if CONFIG_FILE_PATH.exists():
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

    settings = AgentSettings(**raw_config)
    
    # Overlay environment variables
    settings.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    settings.anthropic_base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    settings.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    settings.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    settings.aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    settings.aws_default_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    
    if os.getenv("ANTHROPIC_MODEL"):
        settings.model.name = os.getenv("ANTHROPIC_MODEL")
    if os.getenv("SALESOPS_ENV"):
        settings.environment = os.getenv("SALESOPS_ENV")

    return settings
