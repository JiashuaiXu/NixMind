"""
CLI interface for NixMind.
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional
import logging

from ..core.config import Config
from ..llm.ollama_client import OllamaClient
from ..agent.command_parser import CommandParser, RiskLevel
from ..nixos.config_manager import ConfigManager


class NixMindCLI:
    """Command-line interface for NixMind."""
    
    def __init__(self):
        """Initialize CLI."""
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.llm = self._setup_llm()
        self.parser = CommandParser(self.llm, self.config.safety.__dict__)
        self.config_manager = ConfigManager(self.config.nixos.__dict__)
    
    def _setup_llm(self) -> OllamaClient:
        """Setup LLM client based on configuration."""
        if self.config.llm.provider == "ollama":
            return OllamaClient(self.config.llm.__dict__)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm.provider}")
    
    async def run_interactive(self):
        """Run interactive mode."""
        print("🧠 NixMind - AI Agent for NixOS")
        print("Type 'help' for commands, 'quit' to exit\n")
        
        # Check LLM availability
        if not await self.llm.is_available():
            print("❌ LLM service not available. Please check your configuration.")
            print(f"   Expected: {self.config.llm.api_base}")
            return
        
        print(f"✅ Connected to {self.config.llm.provider} ({self.config.llm.model_name})")
        
        # Get system context
        system_context = await self._get_system_context()
        
        while True:
            try:
                user_input = input("\n💬 nixmind> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                if user_input.lower() == 'status':
                    await self._show_status()
                    continue
                
                if user_input.lower() == 'generations':
                    await self._show_generations()
                    continue
                
                # Process request
                await self._process_request(user_input, system_context)
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.logger.error(f"CLI error: {e}")
    
    async def _process_request(self, user_input: str, system_context: Dict[str, Any]):
        """Process a user request."""
        try:
            print("🤔 Analyzing request...")
            
            # Parse the request
            parsed = await self.parser.parse_request(user_input, system_context)
            
            print(f"\n📋 Analysis:")
            print(f"   Action: {parsed.action_type.value}")
            print(f"   Risk Level: {parsed.risk_level.value}")
            print(f"   Explanation: {parsed.explanation}")
            
            if parsed.commands:
                print(f"\n📝 Generated Commands:")
                for i, cmd in enumerate(parsed.commands, 1):
                    print(f"   {i}. [{cmd.type}] {cmd.description}")
                    print(f"      Content: {cmd.content[:100]}{'...' if len(cmd.content) > 100 else ''}")
            
            if parsed.additional_notes:
                print(f"\n💡 Notes: {parsed.additional_notes}")
            
            # Validate commands if any
            if parsed.commands:
                print("\n🔍 Validating commands...")
                validations = await self.parser.validate_commands(
                    parsed.commands,
                    context=user_input
                )
                
                high_risk = any(v.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] for v in validations)
                
                if high_risk:
                    print("⚠️  High-risk operations detected!")
                    for i, validation in enumerate(validations):
                        if validation.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                            print(f"   Command {i+1}: {validation.risk_level.value} risk")
                            for risk in validation.risks:
                                print(f"     - {risk['description']}")
                
                # Ask for confirmation if required
                if self.config.safety.require_confirmation:
                    if not self._confirm_execution(parsed, validations):
                        print("❌ Execution cancelled by user")
                        return
                
                # Execute commands
                await self._execute_commands(parsed)
            
            else:
                print("ℹ️  No commands to execute")
        
        except Exception as e:
            print(f"❌ Error processing request: {e}")
            self.logger.error(f"Error processing request: {e}")
    
    def _confirm_execution(self, parsed, validations) -> bool:
        """Get user confirmation for command execution."""
        print(f"\n🚨 Confirmation Required")
        print(f"   Action: {parsed.explanation}")
        print(f"   Risk: {parsed.risk_level.value}")
        print(f"   Rebuild required: {'Yes' if parsed.requires_rebuild else 'No'}")
        
        if parsed.rollback_info:
            print(f"   Rollback: {parsed.rollback_info}")
        
        high_risk_validations = [v for v in validations if v.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
        if high_risk_validations:
            print("   ⚠️  High-risk operations detected!")
        
        while True:
            response = input("\n🤖 Proceed? (yes/no/dry-run): ").lower().strip()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            elif response in ['dry-run', 'dry', 'd']:
                # Perform dry run
                asyncio.create_task(self._dry_run_commands(parsed))
                return False
            else:
                print("Please answer 'yes', 'no', or 'dry-run'")
    
    async def _execute_commands(self, parsed):
        """Execute parsed commands."""
        print("\n🚀 Executing commands...")
        
        for i, command in enumerate(parsed.commands, 1):
            print(f"   Executing command {i}/{len(parsed.commands)}")
            
            try:
                if command.type == "nix_config":
                    # Apply configuration change
                    success = await self.config_manager.apply_config_patch(
                        command.content,
                        f"NixMind: {command.description}"
                    )
                    
                    if success:
                        print(f"   ✅ Configuration updated: {command.description}")
                        
                        # Rebuild if required
                        if parsed.requires_rebuild:
                            print("   🔄 Rebuilding system...")
                            rebuild_success, output = await self.config_manager.rebuild_system()
                            
                            if rebuild_success:
                                print("   ✅ System rebuilt successfully")
                            else:
                                print(f"   ❌ Rebuild failed: {output}")
                    else:
                        print(f"   ❌ Configuration update failed: {command.description}")
                
                elif command.type == "shell":
                    # Execute shell command (with caution)
                    print(f"   ⚠️  Shell command execution not implemented for safety")
                    print(f"   Command: {command.content}")
            
            except Exception as e:
                print(f"   ❌ Error executing command {i}: {e}")
                self.logger.error(f"Command execution error: {e}")
    
    async def _dry_run_commands(self, parsed):
        """Perform dry-run of commands."""
        print("\n🧪 Dry-run mode...")
        
        for i, command in enumerate(parsed.commands, 1):
            print(f"   Dry-run command {i}/{len(parsed.commands)}: {command.description}")
            
            if command.type == "nix_config":
                # Simulate configuration change
                print(f"   Would apply config: {command.content[:200]}...")
                
                if parsed.requires_rebuild:
                    success, output = await self.config_manager.dry_run_rebuild()
                    if success:
                        print("   ✅ Dry-run rebuild successful")
                    else:
                        print(f"   ❌ Dry-run rebuild failed: {output}")
            else:
                print(f"   Would execute: {command.content}")
    
    async def _get_system_context(self) -> Dict[str, Any]:
        """Get current system context."""
        context = {
            "nixos_version": "unknown",
            "current_generation": "unknown",
            "available_packages": "nixpkgs",
            "config_path": self.config.nixos.config_path
        }
        
        try:
            # Get current generation
            current_gen = await self.config_manager.get_current_generation()
            if current_gen:
                context["current_generation"] = str(current_gen.number)
        except Exception:
            pass
        
        return context
    
    async def _show_status(self):
        """Show system status."""
        print("\n📊 System Status:")
        
        # LLM status
        llm_available = await self.llm.is_available()
        print(f"   LLM Service: {'✅ Available' if llm_available else '❌ Unavailable'}")
        print(f"   Model: {self.config.llm.model_name}")
        
        # Current generation
        try:
            current_gen = await self.config_manager.get_current_generation()
            if current_gen:
                print(f"   Current Generation: {current_gen.number}")
            else:
                print("   Current Generation: Unknown")
        except Exception as e:
            print(f"   Current Generation: Error ({e})")
        
        # Configuration
        print(f"   Config Path: {self.config.nixos.config_path}")
        print(f"   Safety Mode: {'✅ Enabled' if self.config.safety.require_confirmation else '❌ Disabled'}")
    
    async def _show_generations(self):
        """Show available generations."""
        print("\n📚 Available Generations:")
        
        try:
            generations = await self.config_manager.list_generations()
            
            if not generations:
                print("   No generations found")
                return
            
            for gen in generations[:10]:  # Show last 10
                print(f"   {gen.number}: {gen.description} ({gen.timestamp.strftime('%Y-%m-%d %H:%M')})")
        
        except Exception as e:
            print(f"   Error listing generations: {e}")
    
    def _show_help(self):
        """Show help information."""
        print("\n📖 NixMind Commands:")
        print("   help        - Show this help")
        print("   status      - Show system status")
        print("   generations - List available generations")
        print("   quit        - Exit NixMind")
        print("\n💡 Natural Language Examples:")
        print("   'Install Blender with CUDA support'")
        print("   'Enable Docker and add my user to the docker group'")
        print("   'Update my firewall to allow SSH on port 2222'")
        print("   'Show me what packages are installed'")


async def main():
    """Main CLI entry point."""
    cli = NixMindCLI()
    await cli.run_interactive()