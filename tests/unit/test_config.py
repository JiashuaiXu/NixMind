"""
Unit tests for configuration management.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nixmind.core.config import Config, LLMConfig, SafetyConfig, NixOSConfig


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config(self.config_file)
        
        self.assertEqual(config.log_level, "INFO")
        self.assertIsInstance(config.llm, LLMConfig)
        self.assertIsInstance(config.safety, SafetyConfig)
        self.assertIsInstance(config.nixos, NixOSConfig)
        
        # Test default LLM config
        self.assertEqual(config.llm.provider, "ollama")
        self.assertEqual(config.llm.model_name, "llama3.2:latest")
        self.assertEqual(config.llm.temperature, 0.1)
    
    def test_load_custom_config(self):
        """Test loading custom configuration."""
        custom_config = {
            "log_level": "DEBUG",
            "llm": {
                "provider": "ollama",
                "model_name": "custom-model",
                "temperature": 0.5
            },
            "safety": {
                "require_confirmation": False,
                "risk_threshold": 0.5
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(custom_config, f)
        
        config = Config(self.config_file)
        
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.llm.model_name, "custom-model")
        self.assertEqual(config.llm.temperature, 0.5)
        self.assertEqual(config.safety.require_confirmation, False)
        self.assertEqual(config.safety.risk_threshold, 0.5)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = Config(self.config_file)
        config.log_level = "DEBUG"
        config.llm.model_name = "test-model"
        config.save_config()
        
        # Reload and verify
        new_config = Config(self.config_file)
        self.assertEqual(new_config.log_level, "DEBUG")
        self.assertEqual(new_config.llm.model_name, "test-model")


if __name__ == '__main__':
    unittest.main()