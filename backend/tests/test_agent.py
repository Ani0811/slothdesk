"""Agent tests for smolagents ToolCallingAgent integration and error handling."""

import json
from unittest.mock import MagicMock
import pytest

from app.schemas import FileItem
from app.agent import (
    classify_files_with_smolagents,
    _parse_and_validate_agent_output,
    check_lm_studio_status,
)


def test_agent_local_inference_unavailable_fallback():
    """When LM Studio is unreachable, agent immediately falls back to deterministic rules with transparent mode."""
    files = [
        FileItem(
            filename="dataset.csv",
            relative_path="dataset.csv",
            size_bytes=1024,
            extension=".csv",
            mtime=1700000000.0,
            sha256="abc",
        ),
        FileItem(
            filename="song.mp3",
            relative_path="song.mp3",
            size_bytes=2048,
            extension=".mp3",
            mtime=1700000000.0,
            sha256="def",
        ),
    ]

    result = classify_files_with_smolagents(files, mock_model=None)
    assert result.model_mode == "deterministic_fallback"
    assert "none" in result.model_name or "offline" in result.model_name
    assert result.classifications["dataset.csv"][0] == "Documents"
    assert result.classifications["song.mp3"][0] == "Audio"
    assert "deterministic" in result.classifications["dataset.csv"][1].lower()


def test_agent_mocked_successful_tool_calling():
    """Test ToolCallingAgent when model produces valid JSON classifications."""
    files = [
        FileItem(
            filename="presentation.pptx",
            relative_path="presentation.pptx",
            size_bytes=5000,
            extension=".pptx",
            mtime=1700000000.0,
            sha256="123",
        )
    ]

    # Create mock model that returns valid JSON structure
    mock_model = MagicMock()
    # When agent runs, the mock model returns a simulated answer
    mock_response = MagicMock()
    mock_response.content = json.dumps([
        {
            "filename": "presentation.pptx",
            "category": "Documents",
            "reason": "AI identified PowerPoint presentation as a document.",
        }
    ])
    mock_model.return_value = mock_response

    # Force check_lm_studio_status to report connected for this test
    from app import agent
    orig_check = agent.check_lm_studio_status
    agent.check_lm_studio_status = lambda: (True, "qwen2.5-7b-instruct", ["qwen2.5-7b-instruct"])

    try:
        # Pass mock_model
        # ToolCallingAgent calls model() or model.generate()
        # Since smolagents wraps the model, we test parsing & validation
        inventory = {"presentation.pptx": {"filename": "presentation.pptx", "size_bytes": 5000, "extension": ".pptx"}}
        parsed = _parse_and_validate_agent_output(mock_response.content, inventory)
        assert "presentation.pptx" in parsed
        assert parsed["presentation.pptx"][0] == "Documents"
        assert "PowerPoint" in parsed["presentation.pptx"][1]
    finally:
        agent.check_lm_studio_status = orig_check


def test_agent_rejects_out_of_inventory_paths():
    """Agent validation strictly drops any files invented by the model not in inventory."""
    inventory = {
        "valid.pdf": {"filename": "valid.pdf", "size_bytes": 100, "extension": ".pdf"}
    }
    raw_output = json.dumps([
        {"filename": "valid.pdf", "category": "Documents", "reason": "Real file"},
        {"filename": "hallucinated.exe", "category": "Other", "reason": "Invented file"},
        {"filename": "../../traversal.txt", "category": "Documents", "reason": "Attack attempt"},
    ])

    parsed = _parse_and_validate_agent_output(raw_output, inventory)
    assert "valid.pdf" in parsed
    assert "hallucinated.exe" not in parsed
    assert "../../traversal.txt" not in parsed


def test_agent_rejects_invalid_categories():
    """Agent validation rejects any category outside the ALLOWED_CATEGORIES allowlist."""
    inventory = {
        "pic.jpg": {"filename": "pic.jpg", "size_bytes": 100, "extension": ".jpg"}
    }
    raw_output = json.dumps([
        {"filename": "pic.jpg", "category": "NonExistentCategory", "reason": "Bad category"},
    ])

    parsed = _parse_and_validate_agent_output(raw_output, inventory)
    assert "pic.jpg" not in parsed


def test_agent_handles_corrupt_model_json():
    """Agent parser gracefully recovers from non-JSON or partial responses."""
    inventory = {"file.txt": {"filename": "file.txt", "size_bytes": 10, "extension": ".txt"}}

    assert _parse_and_validate_agent_output("Here is some text: [invalid json", inventory) == {}
    assert _parse_and_validate_agent_output("", inventory) == {}
    assert _parse_and_validate_agent_output("None", inventory) == {}
    assert _parse_and_validate_agent_output("{\"not\": \"a list\"}", inventory) == {}
