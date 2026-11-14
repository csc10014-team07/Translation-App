"""Unit and health probe tests for Ticket 01."""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings
from app.core.vram_monitor import get_vram_info, vram_tracker
from app.main import app
from app.models.manager import ModelManager, get_model_manager
from starlette.testclient import TestClient


def test_health_endpoint():
    """Verify GET /health returns 200, valid device, and valid VRAM info."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "ok"
    assert "device" in data
    assert data["device"] in ("cuda", "cpu")
    assert "vram" in data
    assert "vram_allocated_mb" in data
    assert "vram_total_mb" in data
    assert isinstance(data["vram_allocated_mb"], (int, float))
    assert isinstance(data["vram_total_mb"], (int, float))
    vram = data["vram"]
    for key in ("used_mb", "free_mb", "total_mb", "allocated_mb"):
        assert key in vram, f"Missing {key} in vram payload"
        assert isinstance(vram[key], (int, float))
        assert vram[key] >= 0.0
    print("✅ /health test passed:", data)


def test_docs_endpoint():
    """Verify Swagger UI docs load at /docs."""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
    print("✅ /docs test passed.")


def test_device_abstraction():
    """Verify effective_device returns a valid device string without crashing."""
    dev = settings.effective_device()
    assert dev in ("cuda", "cpu")
    print(f"✅ Device abstraction test passed. Effective device: {dev}")


def test_cors_middleware():
    """Verify CORS middleware is active and allows cross-origin requests."""
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    # With allow_credentials=True, Starlette echoes the requested Origin
    assert response.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")
    print("✅ CORS middleware test passed.")


def test_vram_monitor():
    """Verify get_vram_info returns dictionary with valid numeric metrics."""
    info = get_vram_info()
    assert isinstance(info, dict)
    for field in ("used_mb", "free_mb", "total_mb", "allocated_mb"):
        assert field in info
        assert isinstance(info[field], float)
        assert info[field] >= 0.0

    # Also test snapshot tracking
    vram_tracker.snapshot_vram(label="test_probe")
    metrics = vram_tracker.get_metrics()
    assert "current_vram" in metrics
    assert "vram_snapshots" in metrics
    assert len(metrics["vram_snapshots"]) > 0
    print("✅ VRAM monitor and tracker test passed:", info)


def test_model_manager_singleton():
    """Verify ModelManager initializes and provides singleton adapters."""
    manager1 = get_model_manager()
    manager2 = get_model_manager()
    assert manager1 is manager2, "ModelManager must be a singleton"
    assert isinstance(manager1, ModelManager)
    assert manager1.device in ("cuda", "cpu")
    print("✅ ModelManager singleton test passed.")


if __name__ == "__main__":
    test_health_endpoint()
    test_docs_endpoint()
    test_device_abstraction()
    test_cors_middleware()
    test_vram_monitor()
    test_model_manager_singleton()
    print("\n🎉 ALL TICKET 01 TESTS PASSED!")
