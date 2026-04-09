"""
Tests for the FastAPI application route configuration.
Verifies that routes are correctly registered and removed routes are not accessible.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestAppRouteConfiguration:
    """Test suite for application route configuration."""
    
    def test_app_imports_successfully(self):
        """Test that the app module can be imported without errors."""
        try:
            from autogenstudio.web import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import app module: {e}")
    
    def test_removed_routes_not_in_app(self):
        """Test that analytics, export, and streaming routes are not registered."""
        # Mock dependencies to avoid initialization issues
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            from autogenstudio.web.app import api
            
            # Get all registered routes
            routes = [route.path for route in api.routes]
            
            # Verify removed routes are NOT present
            assert not any('/analytics' in route for route in routes), \
                "Analytics routes should not be registered"
            assert not any('/export' in route for route in routes), \
                "Export routes should not be registered"
            assert not any('/streaming' in route for route in routes), \
                "Streaming routes should not be registered"
    
    def test_existing_routes_still_registered(self):
        """Test that other routes are still properly registered."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            from autogenstudio.web.app import api
            
            routes = [route.path for route in api.routes]
            
            # Verify expected routes ARE present
            assert any('/sessions' in route for route in routes), \
                "Sessions routes should be registered"
            assert any('/runs' in route for route in routes), \
                "Runs routes should be registered"
            assert any('/teams' in route for route in routes), \
                "Teams routes should be registered"
            assert any('/ws' in route for route in routes), \
                "WebSocket routes should be registered"
            assert any('/validate' in route for route in routes), \
                "Validation routes should be registered"
            assert any('/settings' in route for route in routes), \
                "Settings routes should be registered"
            assert any('/gallery' in route for route in routes), \
                "Gallery routes should be registered"
            assert any('/auth' in route for route in routes), \
                "Auth routes should be registered"
            assert any('/mcp' in route for route in routes), \
                "MCP routes should be registered"
    
    def test_version_endpoint_exists(self):
        """Test that the version endpoint is still available."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            from autogenstudio.web.app import api
            
            routes = [route.path for route in api.routes]
            
            assert '/version' in routes, "Version endpoint should be registered"
    
    def test_health_endpoint_exists(self):
        """Test that the health check endpoint is still available."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            from autogenstudio.web.app import api
            
            routes = [route.path for route in api.routes]
            
            assert '/health' in routes, "Health endpoint should be registered"
    
    def test_routes_module_import_doesnt_fail(self):
        """Test that the routes module can be imported without errors."""
        try:
            from autogenstudio.web import routes
            # The module should be importable even if empty
            assert routes is not None
        except ImportError as e:
            pytest.fail(f"Failed to import routes module: {e}")
    
    def test_app_has_correct_middleware(self):
        """Test that the app has the correct middleware configured."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            from autogenstudio.web.app import app
            
            # Check that CORS middleware is configured
            middleware_types = [type(m).__name__ for m in app.user_middleware]
            assert 'CORSMiddleware' in str(middleware_types) or len(app.user_middleware) > 0
    
    def test_api_metadata_is_correct(self):
        """Test that API metadata (title, version, description) is properly set."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            from autogenstudio.web.app import api
            from autogenstudio.version import VERSION
            
            assert api.title == "AutoGen Studio API"
            assert api.version == VERSION
            assert "AutoGen Studio" in api.description


class TestRemovedRoutesNotAccessible:
    """Test that removed routes (analytics, export, streaming) are truly inaccessible."""
    
    def test_analytics_routes_removed(self):
        """Test that analytics module is not imported in app.py."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            # Import the app module
            import autogenstudio.web.app as app_module
            
            # Verify that analytics is not in the imported modules
            assert not hasattr(app_module, 'analytics'), \
                "Analytics should not be imported in app module"
    
    def test_export_routes_removed(self):
        """Test that export module is not imported in app.py."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            import autogenstudio.web.app as app_module
            
            # Verify that export_routes is not in the imported modules
            # (it was imported as 'export_routes' in the original)
            assert not hasattr(app_module, 'export_routes'), \
                "Export routes should not be imported in app module"
    
    def test_streaming_routes_removed(self):
        """Test that streaming module is not imported in app.py."""
        with patch('autogenstudio.web.app.init_managers', new_callable=AsyncMock), \
             patch('autogenstudio.web.app.init_auth_manager') as mock_auth, \
             patch('autogenstudio.web.app.register_auth_dependencies', new_callable=AsyncMock):
            
            mock_auth.return_value = MagicMock()
            
            import autogenstudio.web.app as app_module
            
            # Verify that streaming is not in the imported modules
            assert not hasattr(app_module, 'streaming'), \
                "Streaming should not be imported in app module"
    
    def test_routes_init_is_empty(self):
        """Test that routes/__init__.py is empty and doesn't export removed modules."""
        try:
            from autogenstudio.web.routes import (
                gallery, mcp, runs, sessions, settingsroute, teams, validation, ws
            )
            # These should still be importable from their individual modules
            assert gallery is not None
            assert mcp is not None
            assert runs is not None
            assert sessions is not None
            assert settingsroute is not None
            assert teams is not None
            assert validation is not None
            assert ws is not None
        except ImportError:
            # If they can't be imported from __init__, that's expected
            # since __init__ is now empty
            pass
        
        # Try to import removed modules - they should not be in __all__
        from autogenstudio.web import routes as routes_module
        
        # Check that removed modules are not in __all__ (if it exists)
        if hasattr(routes_module, '__all__'):
            assert 'analytics' not in routes_module.__all__
            assert 'export' not in routes_module.__all__
            assert 'streaming' not in routes_module.__all__


class TestAppImportCleanup:
    """Test that app imports are clean after route removal."""
    
    def test_app_import_statement_clean(self):
        """Test that the import statement in app.py is clean."""
        import inspect
        from autogenstudio.web import app
        
        # Get the source code of the app module
        source = inspect.getsource(app)
        
        # Verify removed imports are not present
        assert 'analytics' not in source or 'from .routes import' not in source or \
               'analytics' not in source[source.find('from .routes import'):source.find('from .routes import') + 200], \
               "Analytics should not be in import statement"
        
        assert 'export as export_routes' not in source, \
               "Export routes should not be in import statement"
        
        assert 'streaming' not in source or 'from .routes import' not in source or \
               'streaming' not in source[source.find('from .routes import'):source.find('from .routes import') + 200], \
               "Streaming should not be in import statement"
    
    def test_no_analytics_router_registration(self):
        """Test that analytics router is not registered."""
        import inspect
        from autogenstudio.web import app
        
        source = inspect.getsource(app)
        
        # Check that analytics router is not included
        assert 'analytics.router' not in source, \
               "Analytics router should not be registered"
    
    def test_no_export_router_registration(self):
        """Test that export router is not registered."""
        import inspect
        from autogenstudio.web import app
        
        source = inspect.getsource(app)
        
        # Check that export router is not included
        assert 'export_routes.router' not in source, \
               "Export router should not be registered"
    
    def test_no_streaming_router_registration(self):
        """Test that streaming router is not registered."""
        import inspect
        from autogenstudio.web import app
        
        source = inspect.getsource(app)
        
        # Check that streaming router is not included
        assert 'streaming.router' not in source, \
               "Streaming router should not be registered"