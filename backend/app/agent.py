"""AI Agent harness integrating smolagents with LM Studio local inference."""

import json
import re
from typing import Dict, List, Tuple, Any, Optional
import httpx
from smolagents import tool, ToolCallingAgent, OpenAIServerModel

from app.config import settings
from app.schemas import FileItem, ALLOWED_CATEGORIES
from app.tools.scanner import classify_by_extension


def check_lm_studio_status() -> Tuple[bool, str, List[str]]:
    """
    Check if LM Studio is running and inspect available models.
    Returns:
        (is_connected, active_or_configured_model, available_models_list)
    """
    endpoint = f"{settings.LM_STUDIO_BASE_URL.rstrip('/')}/models"
    try:
        with httpx.Client(timeout=0.3) as client:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                active_model = settings.LM_STUDIO_MODEL
                if models and active_model not in models:
                    # If configured model isn't in models, default to the first available model
                    active_model = models[0]
                return True, active_model, models
    except Exception:
        pass
    return False, settings.LM_STUDIO_MODEL, []


class AgentClassificationResult:
    def __init__(
        self,
        classifications: Dict[str, Tuple[str, str]],  # filename -> (category, reason)
        model_mode: str,
        model_name: str,
    ):
        self.classifications = classifications
        self.model_mode = model_mode
        self.model_name = model_name


def classify_files_with_smolagents(
    files: List[FileItem],
    mock_model: Optional[Any] = None,
) -> AgentClassificationResult:
    """
    Classifies pre-scanned files using smolagents ToolCallingAgent and LM Studio.
    If LM Studio is unreachable or agent execution fails, falls back safely to
    the deterministic classifier while accurately reporting the mode.
    """
    if not files:
        return AgentClassificationResult(
            classifications={},
            model_mode="deterministic_fallback",
            model_name="none",
        )

    connected, active_model, available_models = check_lm_studio_status()

    # If LM Studio is not reachable and no mock model is provided, use deterministic fallback
    if not connected and mock_model is None:
        deterministic_results = {}
        for item in files:
            cat = classify_by_extension(item.filename)
            deterministic_results[item.filename] = (
                cat,
                f"Classified as {cat} based on extension '{item.extension}' (Deterministic fallback: LM Studio unavailable).",
            )
        return AgentClassificationResult(
            classifications=deterministic_results,
            model_mode="deterministic_fallback",
            model_name="none (offline rule-based)",
        )

    # Build metadata lookup for agent tools
    inventory_metadata: Dict[str, Dict[str, Any]] = {
        f.filename: {
            "filename": f.filename,
            "size_bytes": f.size_bytes,
            "extension": f.extension,
        }
        for f in files
    }

    # Narrowly scoped typed tools for smolagents
    @tool
    def get_file_metadata(filename: str) -> str:
        """Retrieve pre-scanned metadata for a file in the downloads inventory.

        Args:
            filename: The exact name of the file to query.
        """
        meta = inventory_metadata.get(filename)
        if not meta:
            return json.dumps({"error": f"File '{filename}' not found in inventory"})
        return json.dumps(meta)

    @tool
    def get_allowed_categories() -> str:
        """Retrieve the exact list of allowed category names."""
        return json.dumps(ALLOWED_CATEGORIES)

    @tool
    def validate_category(category: str) -> str:
        """Check if a category name is valid.

        Args:
            category: The category name to validate.
        """
        if category in ALLOWED_CATEGORIES:
            return f"Valid category: '{category}'"
        return f"Invalid category: '{category}'. Allowed: {ALLOWED_CATEGORIES}"

    tools = [get_file_metadata, get_allowed_categories, validate_category]

    try:
        model = (
            mock_model
            if mock_model is not None
            else OpenAIServerModel(
                model_id=active_model,
                api_base=settings.LM_STUDIO_BASE_URL,
                api_key="lm-studio",
            )
        )

        agent = ToolCallingAgent(
            tools=tools,
            model=model,
            max_steps=5,
        )

        files_list_summary = [
            {"filename": f.filename, "size_bytes": f.size_bytes, "ext": f.extension}
            for f in files
        ]

        prompt = (
            f"You are the SlothDesk File Classification Agent.\n"
            f"You must categorize these {len(files)} files into one of the allowed categories: {ALLOWED_CATEGORIES}.\n"
            f"Files to classify:\n{json.dumps(files_list_summary, indent=2)}\n\n"
            f"Instructions:\n"
            f"1. You may inspect file metadata using get_file_metadata if helpful.\n"
            f"2. Every category MUST be strictly one of: {ALLOWED_CATEGORIES}.\n"
            f"3. Return ONLY a valid JSON array of objects with keys 'filename', 'category', and 'reason'.\n"
            f"Example format: [ {{\"filename\": \"report.pdf\", \"category\": \"Documents\", \"reason\": \"PDF document\"}} ]\n"
            f"Do not include markdown fences or extraneous text outside the JSON array."
        )

        output = agent.run(prompt)
        parsed_results = _parse_and_validate_agent_output(output, inventory_metadata)

        # Merge with fallback for any missing or omitted files
        final_classifications: Dict[str, Tuple[str, str]] = {}
        for item in files:
            if item.filename in parsed_results:
                final_classifications[item.filename] = parsed_results[item.filename]
            else:
                cat = classify_by_extension(item.filename)
                final_classifications[item.filename] = (
                    cat,
                    f"Classified as {cat} based on extension '{item.extension}' (Fallback).",
                )

        return AgentClassificationResult(
            classifications=final_classifications,
            model_mode="local_ai_smolagents",
            model_name=active_model,
        )

    except Exception as exc:
        # Safe fallback if inference times out, errors, or fails to parse
        fallback_results = {}
        for item in files:
            cat = classify_by_extension(item.filename)
            fallback_results[item.filename] = (
                cat,
                f"Classified as {cat} based on extension '{item.extension}' (Deterministic fallback: {str(exc)[:60]}).",
            )
        return AgentClassificationResult(
            classifications=fallback_results,
            model_mode="deterministic_fallback",
            model_name=f"fallback ({str(exc)[:40]})",
        )


def _parse_and_validate_agent_output(
    output: Any,
    inventory: Dict[str, Dict[str, Any]],
) -> Dict[str, Tuple[str, str]]:
    """Parse and rigorously validate raw agent output against inventory constraints."""
    text = str(output).strip()

    # Extract JSON if wrapped in markdown code blocks
    match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
    except Exception:
        return {}

    if not isinstance(data, list):
        return {}

    validated: Dict[str, Tuple[str, str]] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        fname = entry.get("filename")
        cat = entry.get("category")
        reason = entry.get("reason", "AI categorized based on filename and type.")

        if not fname or fname not in inventory:
            # Reject invented or out-of-inventory paths
            continue

        if cat not in ALLOWED_CATEGORIES:
            # Reject invalid categories
            continue

        validated[fname] = (cat, str(reason))

    return validated
