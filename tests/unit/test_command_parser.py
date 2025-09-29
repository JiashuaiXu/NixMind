"""
Unit tests for command parser.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nixmind.agent.command_parser import CommandParser, ActionType, RiskLevel, Command
from nixmind.llm.base import LLMResponse


class TestCommandParser(unittest.TestCase):
    """Test command parser functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_llm = Mock()
        self.mock_llm.create_system_message = Mock(return_value=Mock())
        self.mock_llm.create_user_message = Mock(return_value=Mock())
        
        self.config = {
            "risk_threshold": 0.7,
            "banned_commands": ["rm -rf /", "dd if="]
        }
        
        self.parser = CommandParser(self.mock_llm, self.config)
    
    def test_basic_validation_safe_command(self):
        """Test basic validation for safe commands."""
        command = Command(
            type="nix_config",
            content="programs.git.enable = true;",
            description="Enable Git"
        )
        
        result = self.parser._basic_validation(command)
        
        self.assertTrue(result.safe)
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(len(result.risks), 0)
    
    def test_basic_validation_banned_command(self):
        """Test basic validation for banned commands."""
        command = Command(
            type="shell",
            content="rm -rf /tmp/test",
            description="Remove test directory"
        )
        
        result = self.parser._basic_validation(command)
        
        self.assertFalse(result.safe)
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)
        self.assertGreater(len(result.risks), 0)
    
    def test_basic_validation_dangerous_pattern(self):
        """Test basic validation for dangerous patterns."""
        command = Command(
            type="shell",
            content="chmod 777 /etc/passwd",
            description="Change file permissions"
        )
        
        result = self.parser._basic_validation(command)
        
        self.assertFalse(result.safe)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertGreater(len(result.risks), 0)
    
    async def test_parse_request_success(self):
        """Test successful request parsing."""
        mock_response = LLMResponse(
            content='{"action_type": "config_change", "explanation": "Install Git", "risk_level": "low", "commands": [{"type": "nix_config", "content": "programs.git.enable = true;", "description": "Enable Git"}], "rollback_info": "Set programs.git.enable = false;", "requires_rebuild": true, "additional_notes": "Git will be available system-wide"}',
            model="test-model"
        )
        
        self.mock_llm.generate = AsyncMock(return_value=mock_response)
        
        result = await self.parser.parse_request("Install Git")
        
        self.assertEqual(result.action_type, ActionType.CONFIG_CHANGE)
        self.assertEqual(result.explanation, "Install Git")
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(len(result.commands), 1)
        self.assertEqual(result.commands[0].type, "nix_config")
        self.assertTrue(result.requires_rebuild)
    
    async def test_parse_request_invalid_json(self):
        """Test request parsing with invalid JSON response."""
        mock_response = LLMResponse(
            content='Invalid JSON response',
            model="test-model"
        )
        
        self.mock_llm.generate = AsyncMock(return_value=mock_response)
        
        with self.assertRaises(ValueError):
            await self.parser.parse_request("Install Git")


if __name__ == '__main__':
    # Run async tests
    class AsyncTestRunner:
        def run_tests(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            suite = unittest.TestLoader().loadTestsFromTestCase(TestCommandParser)
            runner = unittest.TextTestRunner(verbosity=2)
            
            # Convert async test methods
            for test_case in suite:
                if hasattr(test_case, '_testMethodName'):
                    method = getattr(test_case, test_case._testMethodName)
                    if asyncio.iscoroutinefunction(method):
                        setattr(test_case, test_case._testMethodName, 
                               lambda self, method=method: loop.run_until_complete(method()))
            
            result = runner.run(suite)
            loop.close()
            return result
    
    runner = AsyncTestRunner()
    runner.run_tests()