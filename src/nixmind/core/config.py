"""
Configuration management for NixMind.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: str = "ollama"  # ollama, llama_cpp, vllm
    model_name: str = "llama3.2:latest"
    api_base: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 60


@dataclass
class SafetyConfig:
    """Configuration for safety and validation."""
    require_confirmation: bool = True
    enable_dry_run: bool = True
    risk_threshold: float = 0.7
    banned_commands: list = field(default_factory=lambda: [
        "rm -rf /", "dd if=", "mkfs", "fdisk", "parted"
    ])


@dataclass
class NixOSConfig:
    """Configuration for NixOS integration."""
    config_path: str = "/etc/nixos/configuration.nix"
    backup_generations: int = 5
    enable_snapshots: bool = True
    snapshot_tool: str = "auto"  # auto, btrfs, zfs, none


@dataclass
class Config:
    """Main configuration class."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration from file or environment."""
        self.config_file = config_file or self._get_default_config_path()
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        home = Path.home()
        config_dirs = [
            home / ".config" / "nixmind" / "config.json",
            Path("/etc/nixmind/config.json"),
            Path(__file__).parent.parent.parent.parent / "config" / "config.json"
        ]
        
        for path in config_dirs:
            if path.exists():
                return str(path)
        
        # Return the user config path for creation
        return str(config_dirs[0])
    
    def _load_config(self):
        """Load configuration from file or use defaults."""
        defaults = {
            "log_level": "INFO",
            "log_file": None,
            "llm": {},
            "safety": {},
            "nixos": {},
            "api": {
                "host": "127.0.0.1",
                "port": 8080,
                "enable_cors": False
            }
        }
        
        config_data = defaults.copy()
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    config_data.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        
        # Set attributes
        self.log_level = config_data.get("log_level", "INFO")
        self.log_file = config_data.get("log_file")
        
        # Initialize sub-configurations
        self.llm = LLMConfig(**config_data.get("llm", {}))
        self.safety = SafetyConfig(**config_data.get("safety", {}))
        self.nixos = NixOSConfig(**config_data.get("nixos", {}))
        self.api = config_data.get("api", {})
    
    def save_config(self):
        """Save current configuration to file."""
        config_data = {
            "log_level": self.log_level,
            "log_file": self.log_file,
            "llm": {
                "provider": self.llm.provider,
                "model_name": self.llm.model_name,
                "api_base": self.llm.api_base,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout
            },
            "safety": {
                "require_confirmation": self.safety.require_confirmation,
                "enable_dry_run": self.safety.enable_dry_run,
                "risk_threshold": self.safety.risk_threshold,
                "banned_commands": self.safety.banned_commands
            },
            "nixos": {
                "config_path": self.nixos.config_path,
                "backup_generations": self.nixos.backup_generations,
                "enable_snapshots": self.nixos.enable_snapshots,
                "snapshot_tool": self.nixos.snapshot_tool
            },
            "api": self.api
        }
        
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)