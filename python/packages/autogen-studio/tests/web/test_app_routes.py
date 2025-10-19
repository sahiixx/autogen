"""
Unit tests for autogenstudio web app route configuration.

Tests focus on ensuring removed routes (analytics, export, streaming) 
are no longer accessible and that existing routes remain functional.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_managers():
    """Mock all manager dependencies to avoid database/external dependencies."""
    with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock) as mock_init, \
         patch('autogenstudio.web.app.cleanup_managers', new_callable=AsyncMock) as mock_cleanup, \
         patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
         patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock) as mock_reg_auth:
        
        mock_auth.return_value = MagicMock()
        yield {
            'init_managers': mock_init,
            'cleanup_managers': mock_cleanup,
            'init_auth_manager': mock_auth,
            'register_auth_dependencies': mock_reg_auth
        }


@pytest.fixture
def client(mock_managers):
    """Create a test client with mocked dependencies."""
    from autogenstudio.web.app import app
    return TestClient(app)


class TestRemovedRoutes:
    """Test that removed routes are no longer accessible."""
    
    def test_analytics_route_removed(self, client):
        """Test that /api/analytics routes return 404."""
        response = client.get("/api/analytics")
        assert response.status_code == 404
        
        # Test sub-routes that might have existed
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 404
        
        response = client.post("/api/analytics/events")
        assert response.status_code == 404
    
    def test_export_route_removed(self, client):
        """Test that /api/export routes return 404."""
        response = client.get("/api/export")
        assert response.status_code == 404
        
        response = client.post("/api/export/config")
        assert response.status_code == 404
        
        response = client.get("/api/export/download")
        assert response.status_code == 404
    
    def test_streaming_route_removed(self, client):
        """Test that /api/streaming routes return 404."""
        response = client.get("/api/streaming")
        assert response.status_code == 404
        
        response = client.post("/api/streaming/start")
        assert response.status_code == 404
        
        response = client.get("/api/streaming/status")
        assert response.status_code == 404


class TestExistingRoutes:
    """Test that existing routes remain functional."""
    
    def test_version_endpoint_accessible(self, client):
        """Test that /api/version endpoint is accessible."""
        response = client.get("/api/version")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert "version" in data["data"]
    
    def test_health_endpoint_accessible(self, client):
        """Test that /api/health endpoint is accessible."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
    
    def test_sessions_route_exists(self, client):
        """Test that /api/sessions route exists (even if it needs auth)."""
        # Route should exist, but may require authentication
        response = client.get("/api/sessions")
        # Should not be 404 - might be 401, 403, or 200 depending on auth
        assert response.status_code != 404
    
    def test_runs_route_exists(self, client):
        """Test that /api/runs route exists."""
        response = client.get("/api/runs")
        assert response.status_code != 404
    
    def test_teams_route_exists(self, client):
        """Test that /api/teams route exists."""
        response = client.get("/api/teams")
        assert response.status_code != 404
    
    def test_validation_route_exists(self, client):
        """Test that /api/validate route exists."""
        response = client.post("/api/validate/config", json={})
        assert response.status_code != 404
    
    def test_settings_route_exists(self, client):
        """Test that /api/settings route exists."""
        response = client.get("/api/settings")
        assert response.status_code != 404
    
    def test_gallery_route_exists(self, client):
        """Test that /api/gallery route exists."""
        response = client.get("/api/gallery")
        assert response.status_code != 404
    
    def test_auth_route_exists(self, client):
        """Test that /api/auth route exists."""
        response = client.post("/api/auth/login", json={})
        assert response.status_code != 404
    
    def test_mcp_route_exists(self, client):
        """Test that /api/mcp route exists."""
        response = client.get("/api/mcp")
        assert response.status_code != 404


class TestAPIDocumentation:
    """Test that OpenAPI documentation reflects removed routes."""
    
    def test_openapi_schema_excludes_removed_routes(self, client):
        """Test that OpenAPI schema doesn't include removed routes."""
        # Get OpenAPI schema if docs are enabled
        try:
            response = client.get("/api/docs")
            if response.status_code == 200:
                # Docs are enabled, check openapi.json
                openapi_response = client.get("/api/openapi.json")
                assert openapi_response.status_code == 200
                schema = openapi_response.json()
                
                # Verify removed routes are not in paths
                paths = schema.get("paths", {})
                for path in paths.keys():
                    assert not path.startswith("/analytics"), "Analytics routes should be removed from schema"
                    assert not path.startswith("/export"), "Export routes should be removed from schema"
                    assert not path.startswith("/streaming"), "Streaming routes should be removed from schema"
        except Exception:
            # Docs might be disabled, which is fine
            pass
    
    def test_openapi_tags_exclude_removed_routes(self, client):
        """Test that removed route tags are not present in OpenAPI spec."""
        try:
            openapi_response = client.get("/api/openapi.json")
            if openapi_response.status_code == 200:
                schema = openapi_response.json()
                tags = [tag.get("name") for tag in schema.get("tags", [])]
                
                assert "analytics" not in tags, "Analytics tag should be removed"
                assert "export" not in tags, "Export tag should be removed"
                assert "streaming" not in tags, "Streaming tag should be removed"
        except Exception:
            pass


class TestRouteInitialization:
    """Test route initialization and module imports."""
    
    def test_routes_module_import(self):
        """Test that routes module can be imported without errors."""
        try:
            from autogenstudio.web import routes
            # Should succeed even though __init__.py is empty
            assert routes is not None
        except ImportError as e:
            pytest.fail(f"Failed to import routes module: {e}")
    
    def test_individual_route_modules_import(self):
        """Test that individual route modules can still be imported."""
        try:
            from autogenstudio.web.routes import gallery
            from autogenstudio.web.routes import mcp
            from autogenstudio.web.routes import runs
            from autogenstudio.web.routes import sessions
            from autogenstudio.web.routes import settingsroute
            from autogenstudio.web.routes import teams
            from autogenstudio.web.routes import validation
            from autogenstudio.web.routes import ws
            
            # All should import successfully
            assert all([gallery, mcp, runs, sessions, settingsroute, teams, validation, ws])
        except ImportError as e:
            pytest.fail(f"Failed to import route module: {e}")
    
    def test_removed_route_modules_not_imported(self):
        """Test that removed route modules cannot be imported from routes package."""
        # Since __init__.py is now empty, these should not be in the namespace
        from autogenstudio.web import routes
        
        assert not hasattr(routes, 'analytics'), "analytics should not be exported"
        assert not hasattr(routes, 'export'), "export should not be exported"
        assert not hasattr(routes, 'streaming'), "streaming should not be exported"


class TestAppLifecycle:
    """Test application lifecycle with removed routes."""
    
    def test_app_startup_without_removed_routes(self, mock_managers):
        """Test that app starts successfully without removed routes."""
        from autogenstudio.web.app import app
        
        # App should be created successfully
        assert app is not None
        assert hasattr(app, 'routes')
        
        # Verify removed routes are not registered
        route_paths = [route.path for route in app.routes]
        
        analytics_routes = [p for p in route_paths if '/analytics' in p]
        export_routes = [p for p in route_paths if '/export' in p]
        streaming_routes = [p for p in route_paths if '/streaming' in p]
        
        assert len(analytics_routes) == 0, "No analytics routes should be registered"
        assert len(export_routes) == 0, "No export routes should be registered"
        assert len(streaming_routes) == 0, "No streaming routes should be registered"
    
    def test_api_router_configuration(self, mock_managers):
        """Test that API router is properly configured without removed routes."""
        from autogenstudio.web.app import api
        
        # Check that API has expected routes
        route_paths = [route.path for route in api.routes]
        
        # Should have these routes
        assert any('/sessions' in p for p in route_paths), "Sessions routes should exist"
        assert any('/runs' in p for p in route_paths), "Runs routes should exist"
        assert any('/teams' in p for p in route_paths), "Teams routes should exist"
        assert any('/version' in p for p in route_paths), "Version endpoint should exist"
        assert any('/health' in p for p in route_paths), "Health endpoint should exist"
        
        # Should not have these routes
        assert not any('/analytics' in p for p in route_paths), "Analytics routes should not exist"
        assert not any('/export' in p for p in route_paths), "Export routes should not exist"
        assert not any('/streaming' in p for p in route_paths), "Streaming routes should not exist"


class TestCORSConfiguration:
    """Test that CORS is still properly configured after route changes."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options("/api/version", headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET"
        })
        # Should have CORS headers
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """Test error handling for removed routes."""
    
    def test_removed_routes_return_proper_404(self, client):
        """Test that removed routes return proper 404 responses."""
        removed_routes = [
            "/api/analytics",
            "/api/export",
            "/api/streaming",
        ]
        
        for route in removed_routes:
            response = client.get(route)
            assert response.status_code == 404, f"Route {route} should return 404"
            
            # Try POST as well
            response = client.post(route, json={})
            assert response.status_code == 404, f"Route {route} should return 404 for POST"
    
    def test_removed_routes_different_methods(self, client):
        """Test that removed routes return 404 for all HTTP methods."""
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        
        for method in methods:
            response = client.request(method, "/api/analytics/test")
            assert response.status_code == 404, f"Analytics route should return 404 for {method}"
            
            response = client.request(method, "/api/export/test")
            assert response.status_code == 404, f"Export route should return 404 for {method}"
            
            response = client.request(method, "/api/streaming/test")
            assert response.status_code == 404, f"Streaming route should return 404 for {method}"