"""API endpoint integration tests using FastAPI TestClient."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client_with_mock_root(tmp_path: Path, monkeypatch):
    """Fixture pointing settings.root_path and settings.data_path to tmp_path."""
    test_root = tmp_path / "downloads"
    test_root.mkdir()
    test_data = tmp_path / "data"
    test_data.mkdir()

    monkeypatch.setattr(settings, "SLOTHDESK_ROOT", str(test_root))
    monkeypatch.setattr(settings, "SLOTHDESK_DATA_DIR", str(test_data))

    client = TestClient(app)
    return client, test_root


def test_api_health_endpoint(client_with_mock_root):
    """Test GET /api/health reports valid structure and mode."""
    client, _ = client_with_mock_root
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["backend"] == "running"
    assert "slothdesk_root" in data
    assert "lm_studio_connected" in data
    assert "ai_classification_available" in data
    assert "deterministic_fallback_active" in data


def test_api_files_inventory(client_with_mock_root):
    """Test GET /api/files lists items in managed folder."""
    client, root = client_with_mock_root
    (root / "sample.pdf").write_text("sample pdf data")
    (root / "photo.png").write_text("sample png data")

    res = client.get("/api/files")
    assert res.status_code == 200
    data = res.json()
    assert data["total_files"] == 2
    filenames = [f["filename"] for f in data["files"]]
    assert "sample.pdf" in filenames
    assert "photo.png" in filenames


def test_api_plan_and_execution_lifecycle(client_with_mock_root):
    """Test full cycle: scan -> propose plan -> explicit approval execution -> undo."""
    client, root = client_with_mock_root
    test_file = root / "presentation.pptx"
    test_file.write_text("slides content")

    # Step 1: Request plan proposal
    plan_res = client.post("/api/plan")
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    plan_id = plan_data["plan_id"]
    assert plan_data["operations_count"] == 1
    assert plan_data["operations"][0]["category"] == "Documents"
    assert plan_data["operations"][0]["dest_rel_path"] == "Documents/presentation.pptx"

    # Verify no files changed during planning!
    assert test_file.exists()
    assert not (root / "Documents" / "presentation.pptx").exists()

    # Step 2: Retrieve plan by ID
    get_res = client.get(f"/api/plan/{plan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["plan_id"] == plan_id

    # Step 3: Explicit approval execution
    exec_res = client.post(f"/api/execute/{plan_id}")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    manifest_id = exec_data["manifest_id"]
    assert exec_data["status"] == "completed"
    assert exec_data["total_moved"] == 1

    # Verify filesystem changed after explicit execution
    assert not test_file.exists()
    assert (root / "Documents" / "presentation.pptx").exists()

    # Plan cannot be executed a second time (consumed)
    dup_res = client.post(f"/api/execute/{plan_id}")
    assert dup_res.status_code == 404

    # Step 4: Verify undo history lists the manifest
    history_res = client.get("/api/undo")
    assert history_res.status_code == 200
    manifest_ids = [m["manifest_id"] for m in history_res.json()]
    assert manifest_id in manifest_ids

    # Step 5: Execute undo
    undo_res = client.post(f"/api/undo/{manifest_id}")
    assert undo_res.status_code == 200
    undo_data = undo_res.json()
    assert undo_data["status"] == "undone"
    assert undo_data["restored_count"] == 1

    # Verify restored state
    assert test_file.exists()
    assert not (root / "Documents" / "presentation.pptx").exists()


def test_api_nonexistent_plan_and_manifest(client_with_mock_root):
    """Test 404 handling on missing resources."""
    client, _ = client_with_mock_root
    res = client.get("/api/plan/plan_fake123")
    assert res.status_code == 404

    res = client.post("/api/execute/plan_fake123")
    assert res.status_code == 404

    res = client.post("/api/undo/manifest_fake123")
    assert res.status_code == 404
