"""
Tests for the routes/__init__.py module.
Verifies that the module can be imported and doesn't export removed functionality.
"""

import pytest


class TestRoutesInitModule:
    """Test suite for routes/__init__.py module."""
    
    def test_routes_init_can_be_imported(self):
        """Test that routes/__init__.py can be imported without errors."""
        try:
            from autogenstudio.web import routes
            assert routes is not None
        except ImportError as e:
            pytest.fail(f"Failed to import routes module: {e}")
    
    def test_routes_init_is_effectively_empty(self):
        """Test that routes/__init__.py doesn't export removed modules."""
        from autogenstudio.web import routes
        
        # If __all__ exists, it should not contain removed modules
        if hasattr(routes, '__all__'):
            assert 'analytics' not in routes.__all__, \
                "analytics should not be in __all__"
            assert 'export' not in routes.__all__, \
                "export should not be in __all__"
            assert 'streaming' not in routes.__all__, \
                "streaming should not be in __all__"
        
        # Removed modules should not be directly accessible
        assert not hasattr(routes, 'analytics'), \
            "analytics should not be accessible from routes module"
        assert not hasattr(routes, 'export'), \
            "export should not be accessible from routes module"
        assert not hasattr(routes, 'streaming'), \
            "streaming should not be accessible from routes module"
    
    def test_individual_route_modules_still_importable(self):
        """Test that individual route modules can still be imported directly."""
        try:
            from autogenstudio.web.routes import gallery
            from autogenstudio.web.routes import mcp
            from autogenstudio.web.routes import runs
            from autogenstudio.web.routes import sessions
            from autogenstudio.web.routes import settingsroute
            from autogenstudio.web.routes import teams
            from autogenstudio.web.routes import validation
            from autogenstudio.web.routes import ws
            
            # All of these should import successfully
            assert gallery is not None
            assert mcp is not None
            assert runs is not None
            assert sessions is not None
            assert settingsroute is not None
            assert teams is not None
            assert validation is not None
            assert ws is not None
            
        except ImportError as e:
            pytest.fail(f"Failed to import individual route modules: {e}")
    
    def test_removed_route_modules_not_imported_via_init(self):
        """Test that removed modules are not imported through __init__.py."""
        from autogenstudio.web import routes
        
        # Get all attributes from the routes module
        route_attrs = dir(routes)
        
        # Removed module names should not be in the attributes
        # (excluding magic methods and built-ins)
        public_attrs = [attr for attr in route_attrs if not attr.startswith('_')]
        
        assert 'analytics' not in public_attrs, \
            "analytics should not be exported from routes"
        assert 'export' not in public_attrs, \
            "export should not be exported from routes"
        assert 'streaming' not in public_attrs, \
            "streaming should not be exported from routes"
    
    def test_routes_init_file_is_empty_or_minimal(self):
        """Test that routes/__init__.py file is empty or contains minimal code."""
        import os
        from pathlib import Path
        from autogenstudio.web import routes
        
        # Get the file path of the routes module
        routes_file = Path(routes.__file__)
        
        # Read the file content
        content = routes_file.read_text()
        
        # The file should be empty or only contain comments/whitespace
        # Remove comments and whitespace to check
        lines = [line.strip() for line in content.split('\n')]
        non_empty_lines = [
            line for line in lines 
            if line and not line.startswith('#')
        ]
        
        # Should be empty or have very few lines (just imports if any)
        assert len(non_empty_lines) == 0, \
            "routes/__init__.py should be empty (contains only comments/whitespace)"
    
    def test_no_circular_imports(self):
        """Test that importing routes doesn't cause circular import issues."""
        try:
            # Import routes first
            from autogenstudio.web import routes
            
            # Then import app (which imports from routes)
            with pytest.warns(None) as warning_list:
                from autogenstudio.web import app
            
            # Should not generate import warnings
            import_warnings = [w for w in warning_list if 'import' in str(w.message).lower()]
            assert len(import_warnings) == 0, \
                "No import-related warnings should be generated"
                
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")


class TestRemovedRoutesNotAccessible:
    """Test that removed route modules are truly inaccessible."""
    
    def test_analytics_module_not_in_routes_package(self):
        """Test that analytics module is not accessible via routes package."""
        from autogenstudio.web import routes
        
        with pytest.raises(AttributeError):
            _ = routes.analytics
    
    def test_export_module_not_in_routes_package(self):
        """Test that export module is not accessible via routes package."""
        from autogenstudio.web import routes
        
        with pytest.raises(AttributeError):
            _ = routes.export
    
    def test_streaming_module_not_in_routes_package(self):
        """Test that streaming module is not accessible via routes package."""
        from autogenstudio.web import routes
        
        with pytest.raises(AttributeError):
            _ = routes.streaming
    
    def test_wildcard_import_doesnt_include_removed_modules(self):
        """Test that from routes import * doesn't include removed modules."""
        # This test verifies that __all__ is properly configured or absent
        import sys
        
        # Create a clean namespace for the wildcard import test
        test_namespace = {}
        
        try:
            exec("from autogenstudio.web.routes import *", test_namespace)
        except ImportError:
            # If wildcard import fails, that's acceptable (no __all__ defined)
            pass
        
        # Removed modules should not be in the namespace
        assert 'analytics' not in test_namespace, \
            "analytics should not be imported with wildcard"
        assert 'export' not in test_namespace, \
            "export should not be imported with wildcard"
        assert 'streaming' not in test_namespace, \
            "streaming should not be imported with wildcard"