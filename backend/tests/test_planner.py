"""Unit tests for SlothDesk planner and classification rules."""

from pathlib import Path
import pytest
from app.tools.scanner import classify_by_extension, scan_downloads_folder, validate_path_safety
from app.tools.planner import generate_plan, get_plan, is_plan_expired
from app.schemas import FileItem
from app.agent import _parse_and_validate_agent_output, classify_files_with_smolagents


def test_extension_classification():
    """Verify correct categorization across file extensions."""
    assert classify_by_extension("document.pdf") == "Documents"
    assert classify_by_extension("budget.xlsx") == "Documents"
    assert classify_by_extension("photo.jpg") == "Images"
    assert classify_by_extension("icon.svg") == "Images"
    assert classify_by_extension("movie.mp4") == "Videos"
    assert classify_by_extension("song.mp3") == "Audio"
    assert classify_by_extension("archive.tar.gz") == "Archives"
    assert classify_by_extension("backup.zip") == "Archives"
    assert classify_by_extension("script.py") == "Code"
    assert classify_by_extension("component.tsx") == "Code"


def test_unknown_extension_handling():
    """Verify unrecognized or missing extensions are routed to 'Other'."""
    assert classify_by_extension("unknown_binary.bin") == "Other"
    assert classify_by_extension("weird_file.customxyz") == "Other"
    assert classify_by_extension("no_extension_file") == "Other"


def test_path_traversal_rejection(tmp_path: Path):
    """Verify relative paths with '..' or escaping root are rejected."""
    is_valid, err, _ = validate_path_safety("../outside.txt", tmp_path)
    assert not is_valid
    assert "prohibited" in err or "traversal" in err

    is_valid, err, _ = validate_path_safety("sub/../../escaped.txt", tmp_path)
    assert not is_valid


def test_absolute_path_rejection(tmp_path: Path):
    """Verify absolute paths are rejected."""
    is_valid, err, _ = validate_path_safety("/etc/passwd", tmp_path)
    assert not is_valid
    assert "Absolute paths are rejected" in err

    is_valid, err, _ = validate_path_safety("C:/Windows/System32/cmd.exe", tmp_path)
    assert not is_valid


def test_existing_subfolder_not_treated_as_movable_file(tmp_path: Path):
    """Existing subdirectories inside root must be preserved and not moved."""
    docs_dir = tmp_path / "Documents"
    docs_dir.mkdir()
    (docs_dir / "nested_doc.pdf").write_text("nested")

    (tmp_path / "top_level.pdf").write_text("top level")

    scanned = scan_downloads_folder(tmp_path)
    filenames = [f.filename for f in scanned]

    assert "top_level.pdf" in filenames
    # Documents directory itself and its nested files must not be in the direct scanned list
    assert "Documents" not in filenames
    assert "nested_doc.pdf" not in filenames


def test_duplicate_destination_collision_resolution(tmp_path: Path):
    """Verify collisions with existing files in destination directory are resolved deterministically."""
    # Create an existing destination file
    docs_dir = tmp_path / "Documents"
    docs_dir.mkdir()
    (docs_dir / "report.pdf").write_text("existing version")

    # Create root file with identical destination name
    (tmp_path / "report.pdf").write_text("new incoming version")

    plan = generate_plan(tmp_path)
    assert len(plan.operations) == 1
    op = plan.operations[0]

    assert op.has_collision is True
    # Destination must be resolved to prevent overwrite (e.g. Documents/report_1.pdf)
    assert op.dest_rel_path == "Documents/report_1.pdf"
    assert op.collision_warning is not None
    assert "Collision detected" in op.collision_warning


def test_invalid_model_output_safe_fallback(tmp_path: Path):
    """Verify that corrupt or hallucinated model outputs are safely caught and validated."""
    inventory = {
        "file1.pdf": {"filename": "file1.pdf", "size_bytes": 100, "extension": ".pdf"}
    }

    # Model hallucinates non-existent file
    hallucinated = '[{"filename": "ghost.pdf", "category": "Documents"}]'
    parsed = _parse_and_validate_agent_output(hallucinated, inventory)
    assert "ghost.pdf" not in parsed

    # Model returns invalid category
    invalid_cat = '[{"filename": "file1.pdf", "category": "SuperSecretCategory"}]'
    parsed = _parse_and_validate_agent_output(invalid_cat, inventory)
    assert "file1.pdf" not in parsed

    # Model returns malformed non-JSON text
    garbage = "I am an AI and I think this should go somewhere else!"
    parsed = _parse_and_validate_agent_output(garbage, inventory)
    assert parsed == {}
