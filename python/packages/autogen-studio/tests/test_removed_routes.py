"""
Tests to verify that removed routes and modules are no longer accessible.
This ensures the cleanup was successful and prevents regressions.
"""
import pytest
from fastapi.testclient import TestClient
from autogenstudio.web.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_analytics_routes_removed(client):
    """Test that analytics routes are no longer accessible."""
    # These routes should return 404 since they were removed
    analytics_endpoints = [
        "/api/analytics/metrics",
        "/api/analytics/performance/test-id",
        "/api/analytics/usage",
        "/api/analytics/models/comparison",
        "/api/analytics/health/status",
    ]
    
    for endpoint in analytics_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 404, f"Endpoint {endpoint} should return 404 but got {response.status_code}"


def test_export_routes_removed(client):
    """Test that export/import routes are no longer accessible."""
    export_endpoints = [
        "/api/export/templates",
        "/api/export/templates/test-id",
    ]
    
    for endpoint in export_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 404, f"Endpoint {endpoint} should return 404 but got {response.status_code}"
    
    # Test POST endpoints
    response = client.post("/api/export/teams/test-id/export", json={})
    assert response.status_code == 404


def test_streaming_routes_removed(client):
    """Test that streaming routes are no longer accessible."""
    # Test POST endpoint
    response = client.post("/api/streaming/stream", json={})
    assert response.status_code == 404
    
    # Test GET endpoint
    response = client.get("/api/streaming/status/test-id")
    assert response.status_code == 404


def test_existing_routes_still_work(client):
    """Verify that existing routes are still accessible."""
    # These routes should still be available
    existing_endpoints = [
        ("/api/sessions", "GET"),
        ("/api/teams", "GET"),
        ("/api/runs", "GET"),
    ]
    
    for endpoint, method in existing_endpoints:
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json={})
        
        # Should not return 404
        assert response.status_code != 404, f"Endpoint {endpoint} returned 404"


def test_removed_modules_not_importable():
    """Test that removed route modules cannot be imported."""
    removed_modules = [
        "autogenstudio.web.routes.analytics",
        "autogenstudio.web.routes.export",
        "autogenstudio.web.routes.streaming",
    ]
    
    for module_name in removed_modules:
        with pytest.raises(ModuleNotFoundError):
            __import__(module_name)


def test_routes_init_empty():
    """Test that routes __init__.py doesn't export removed modules."""
    import autogenstudio.web.routes as routes_module
    
    removed_names = ["analytics", "export", "streaming"]
    
    for name in removed_names:
        assert not hasattr(routes_module, name), \
            f"Module {name} should not be accessible"


def test_app_startup_without_removed_routes():
    """Test that the app starts successfully without removed routes."""
    from autogenstudio.web.app import app
    
    assert app is not None
    assert hasattr(app, "routes")
    
    route_paths = [route.path for route in app.routes]
    
    for path in route_paths:
        assert "/api/analytics" not in path
        assert "/api/export" not in path
        assert "/api/streaming" not in path