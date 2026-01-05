import sys
import os
import unittest
from unittest.mock import MagicMock

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins import plugin_manager
import local_ingestion

class TestPluginSystem(unittest.TestCase):
    def setUp(self):
        # Reset plugin manager
        plugin_manager.ingestion_sources = []
        plugin_manager._pro_enabled = False
        # Register default
        local_ingestion.register()

    def test_default_local_ingestion(self):
        """Test that local file ingestor is registered and handles local paths."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdirname:
            source = plugin_manager.get_ingestion_source_for_path(tmpdirname)
            self.assertIsNotNone(source)
            self.assertIsInstance(source, local_ingestion.LocalFileIngestor)
            self.assertEqual(source.name, "Local File System")
            self.assertTrue(source.can_handle(tmpdirname))
        
        # Should not handle S3 by default
        self.assertFalse(source.can_handle("s3://bucket/data"))

    def test_pro_plugin_loading(self):
        """Test that the plugin manager attempts to load prism_pro."""
        
        # Create a mock prism_pro module
        mock_pro = MagicMock()
        mock_pro.register_plugins = MagicMock()
        
        # Inject into sys.modules
        with unittest.mock.patch.dict(sys.modules, {'prism_pro': mock_pro}):
            plugin_manager.load_plugins()
            
            self.assertTrue(plugin_manager.is_pro)
            mock_pro.register_plugins.assert_called_once_with(plugin_manager)

    def test_missing_pro_plugin(self):
        """Test behavior when prism_pro is missing."""
        # Ensure prism_pro is NOT in sys.modules (it shouldn't be, but let's be safe)
        if 'prism_pro' in sys.modules:
            del sys.modules['prism_pro']
            
        plugin_manager.load_plugins()
        self.assertFalse(plugin_manager.is_pro)

if __name__ == '__main__':
    unittest.main()
