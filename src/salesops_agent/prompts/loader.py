from pathlib import Path
from typing import Dict, Optional

PROMPTS_DIR = Path(__file__).parent

AVAILABLE_PROMPTS = {
    "v1": PROMPTS_DIR / "system_prompt_v1.txt",
}

DEFAULT_VERSION = "v1"

def load_system_prompt(version: str = DEFAULT_VERSION) -> str:
    """Load a versioned system prompt from disk."""
    if version not in AVAILABLE_PROMPTS:
        raise ValueError(
            f"Prompt version '{version}' not found. Available versions: {list(AVAILABLE_PROMPTS.keys())}"
        )
    prompt_path = AVAILABLE_PROMPTS[version]
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()

def get_prompt_metadata(version: str = DEFAULT_VERSION) -> Dict[str, str]:
    """Retrieve metadata about a prompt version."""
    return {
        "version": version,
        "filename": AVAILABLE_PROMPTS.get(version, Path("")).name,
        "path": str(AVAILABLE_PROMPTS.get(version, Path(""))),
    }
