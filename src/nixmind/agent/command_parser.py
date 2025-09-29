"""
Command parser and validator for NixMind.
"""

import json
import re
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..llm.base import BaseLLM, Message
from ..llm.prompts import NIXOS_SYSTEM_PROMPT, get_nixos_prompt, get_validation_prompt


class ActionType(Enum):
    CONFIG_CHANGE = "config_change"
    SHELL_COMMAND = "shell_command"
    INFO_REQUEST = "info_request"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Command:
    """Represents a parsed command."""
    type: str  # "nix_config" or "shell"
    content: str
    description: str


@dataclass
class ParsedRequest:
    """Represents a parsed user request."""
    action_type: ActionType
    explanation: str
    risk_level: RiskLevel
    commands: List[Command]
    rollback_info: str
    requires_rebuild: bool
    additional_notes: str


@dataclass
class ValidationResult:
    """Result of command validation."""
    safe: bool
    risk_level: RiskLevel
    risks: List[Dict[str, Any]]
    recommendations: List[str]
    alternative_approach: Optional[str] = None


class CommandParser:
    """Parses natural language requests into NixOS commands."""
    
    def __init__(self, llm: BaseLLM, config: Dict[str, Any]):
        """Initialize command parser."""
        self.llm = llm
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Risk assessment configuration
        self.risk_threshold = config.get("risk_threshold", 0.7)
        self.banned_commands = config.get("banned_commands", [])
    
    async def parse_request(
        self,
        user_input: str,
        system_context: Optional[Dict[str, Any]] = None
    ) -> ParsedRequest:
        """Parse a natural language request into structured commands."""
        try:
            # Prepare messages for LLM
            system_msg = self.llm.create_system_message(NIXOS_SYSTEM_PROMPT)
            user_msg = self.llm.create_user_message(
                get_nixos_prompt(user_input, system_context)
            )
            
            # Get response from LLM
            response = await self.llm.generate([system_msg, user_msg])
            
            # Parse JSON response
            parsed_data = self._parse_llm_response(response.content)
            
            # Convert to structured object
            return self._create_parsed_request(parsed_data)
        
        except Exception as e:
            self.logger.error(f"Error parsing request: {e}")
            raise ValueError(f"Failed to parse request: {e}")
    
    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response JSON."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_content.strip()
            
            return json.loads(json_str)
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response from LLM: {response_content}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def _create_parsed_request(self, data: Dict[str, Any]) -> ParsedRequest:
        """Create ParsedRequest from parsed data."""
        try:
            commands = [
                Command(
                    type=cmd.get("type", "shell"),
                    content=cmd.get("content", ""),
                    description=cmd.get("description", "")
                )
                for cmd in data.get("commands", [])
            ]
            
            return ParsedRequest(
                action_type=ActionType(data.get("action_type", "info_request")),
                explanation=data.get("explanation", ""),
                risk_level=RiskLevel(data.get("risk_level", "medium")),
                commands=commands,
                rollback_info=data.get("rollback_info", ""),
                requires_rebuild=data.get("requires_rebuild", False),
                additional_notes=data.get("additional_notes", "")
            )
        
        except (KeyError, ValueError) as e:
            self.logger.error(f"Invalid response structure: {e}")
            raise ValueError(f"Invalid response structure: {e}")
    
    async def validate_commands(
        self,
        commands: List[Command],
        context: str = ""
    ) -> List[ValidationResult]:
        """Validate commands for security and safety."""
        results = []
        
        for command in commands:
            # Basic validation checks
            basic_result = self._basic_validation(command)
            if not basic_result.safe:
                results.append(basic_result)
                continue
            
            # Advanced LLM-based validation
            try:
                llm_result = await self._llm_validation(command, context)
                results.append(llm_result)
            except Exception as e:
                self.logger.warning(f"LLM validation failed: {e}, using basic validation")
                results.append(basic_result)
        
        return results
    
    def _basic_validation(self, command: Command) -> ValidationResult:
        """Perform basic command validation."""
        risks = []
        safe = True
        risk_level = RiskLevel.LOW
        
        # Check for banned commands
        for banned in self.banned_commands:
            if banned.lower() in command.content.lower():
                risks.append({
                    "type": "security",
                    "description": f"Command contains banned pattern: {banned}",
                    "severity": "critical"
                })
                safe = False
                risk_level = RiskLevel.CRITICAL
        
        # Check for potentially dangerous patterns
        dangerous_patterns = [
            (r'rm\s+-rf\s+/', "recursive deletion from root"),
            (r'dd\s+if=', "disk imaging operation"),
            (r'mkfs\s+', "filesystem creation"),
            (r'fdisk|parted', "disk partitioning"),
            (r'chmod\s+777', "overly permissive permissions"),
            (r'curl.*\|\s*sh', "piping remote script to shell"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, command.content, re.IGNORECASE):
                risks.append({
                    "type": "system_damage",
                    "description": f"Potentially dangerous: {description}",
                    "severity": "high"
                })
                if safe:
                    risk_level = RiskLevel.HIGH
                    safe = False
        
        return ValidationResult(
            safe=safe,
            risk_level=risk_level,
            risks=risks,
            recommendations=["Review command carefully before execution"] if risks else []
        )
    
    async def _llm_validation(
        self,
        command: Command,
        context: str
    ) -> ValidationResult:
        """Perform LLM-based command validation."""
        try:
            system_msg = self.llm.create_system_message(
                "You are a security expert. Analyze commands for risks."
            )
            user_msg = self.llm.create_user_message(
                get_validation_prompt(command.content, context)
            )
            
            response = await self.llm.generate([system_msg, user_msg])
            validation_data = json.loads(response.content)
            
            return ValidationResult(
                safe=validation_data.get("safe", False),
                risk_level=RiskLevel(validation_data.get("risk_level", "medium")),
                risks=validation_data.get("risks", []),
                recommendations=validation_data.get("recommendations", []),
                alternative_approach=validation_data.get("alternative_approach")
            )
        
        except Exception as e:
            self.logger.error(f"LLM validation error: {e}")
            # Fallback to conservative approach
            return ValidationResult(
                safe=False,
                risk_level=RiskLevel.MEDIUM,
                risks=[{"type": "unknown", "description": "Could not validate", "severity": "medium"}],
                recommendations=["Manual review required"]
            )