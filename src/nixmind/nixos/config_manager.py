"""
NixOS configuration management for NixMind.
"""

import os
import shutil
import subprocess
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Generation:
    """Represents a NixOS generation."""
    number: int
    timestamp: datetime
    description: str
    path: str


@dataclass
class ConfigBackup:
    """Represents a configuration backup."""
    timestamp: datetime
    config_path: str
    backup_path: str
    generation: Optional[int] = None


class ConfigManager:
    """Manages NixOS configuration files and system generations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize configuration manager."""
        self.config_path = config.get("config_path", "/etc/nixos/configuration.nix")
        self.backup_generations = config.get("backup_generations", 5)
        self.enable_snapshots = config.get("enable_snapshots", True)
        self.snapshot_tool = config.get("snapshot_tool", "auto")
        
        self.logger = logging.getLogger(__name__)
        
        # Setup backup directory
        self.backup_dir = Path.home() / ".nixmind" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_current_generation(self) -> Optional[Generation]:
        """Get information about the current NixOS generation."""
        try:
            result = await self._run_command([
                "nixos-rebuild", "--list-generations"
            ])
            
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if "current" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        number = int(parts[0])
                        # Parse generation info
                        gen_result = await self._run_command([
                            "nix-env", "--list-generations", "-p", "/nix/var/nix/profiles/system"
                        ])
                        
                        # Extract generation details
                        return Generation(
                            number=number,
                            timestamp=datetime.now(),  # Simplified for now
                            description="Current generation",
                            path=f"/nix/var/nix/profiles/system-{number}-link"
                        )
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting current generation: {e}")
            return None
    
    async def list_generations(self, limit: int = 10) -> List[Generation]:
        """List available NixOS generations."""
        try:
            result = await self._run_command([
                "nix-env", "--list-generations", "-p", "/nix/var/nix/profiles/system"
            ])
            
            generations = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines[-limit:]:  # Get last N generations
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        number = int(parts[0])
                        timestamp_str = " ".join(parts[1:3]) if len(parts) >= 3 else ""
                        
                        # Parse timestamp (simplified)
                        timestamp = datetime.now()  # Placeholder
                        
                        generations.append(Generation(
                            number=number,
                            timestamp=timestamp,
                            description=f"Generation {number}",
                            path=f"/nix/var/nix/profiles/system-{number}-link"
                        ))
                    except ValueError:
                        continue
            
            return sorted(generations, key=lambda g: g.number, reverse=True)
        
        except Exception as e:
            self.logger.error(f"Error listing generations: {e}")
            return []
    
    async def backup_config(self, description: str = "") -> ConfigBackup:
        """Create a backup of the current configuration."""
        timestamp = datetime.now()
        backup_name = f"config-{timestamp.strftime('%Y%m%d-%H%M%S')}.nix"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Copy configuration file
            shutil.copy2(self.config_path, backup_path)
            
            # Get current generation
            current_gen = await self.get_current_generation()
            generation_num = current_gen.number if current_gen else None
            
            backup = ConfigBackup(
                timestamp=timestamp,
                config_path=self.config_path,
                backup_path=str(backup_path),
                generation=generation_num
            )
            
            self.logger.info(f"Configuration backed up to {backup_path}")
            
            # Cleanup old backups
            await self._cleanup_old_backups()
            
            return backup
        
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            raise
    
    async def restore_config(self, backup_path: str) -> bool:
        """Restore configuration from backup."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Create backup of current config before restore
            await self.backup_config("Before restore")
            
            # Restore configuration
            shutil.copy2(backup_path, self.config_path)
            
            self.logger.info(f"Configuration restored from {backup_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error restoring configuration: {e}")
            return False
    
    async def apply_config_patch(self, patch_content: str, description: str = "") -> bool:
        """Apply a configuration patch."""
        try:
            # Create backup first
            await self.backup_config(f"Before applying: {description}")
            
            # Read current configuration
            with open(self.config_path, 'r') as f:
                current_config = f.read()
            
            # Apply patch (this is simplified - in practice you'd want more sophisticated merging)
            new_config = self._merge_config(current_config, patch_content)
            
            # Validate syntax
            if await self._validate_nix_syntax(new_config):
                # Write new configuration
                with open(self.config_path, 'w') as f:
                    f.write(new_config)
                
                self.logger.info(f"Configuration patch applied: {description}")
                return True
            else:
                self.logger.error("Configuration syntax validation failed")
                return False
        
        except Exception as e:
            self.logger.error(f"Error applying configuration patch: {e}")
            return False
    
    async def dry_run_rebuild(self) -> Tuple[bool, str]:
        """Perform a dry-run of nixos-rebuild."""
        try:
            result = await self._run_command([
                "nixos-rebuild", "dry-run", "--fast"
            ])
            
            return True, result.stdout
        
        except subprocess.CalledProcessError as e:
            return False, e.stderr or str(e)
        except Exception as e:
            return False, str(e)
    
    async def rebuild_system(self, switch: bool = True) -> Tuple[bool, str]:
        """Rebuild the NixOS system."""
        try:
            command = ["nixos-rebuild"]
            command.append("switch" if switch else "boot")
            
            result = await self._run_command(command, timeout=300)  # 5 minutes
            
            return True, result.stdout
        
        except subprocess.CalledProcessError as e:
            return False, e.stderr or str(e)
        except Exception as e:
            return False, str(e)
    
    async def rollback_generation(self, generation_number: Optional[int] = None) -> bool:
        """Rollback to a specific generation or the previous one."""
        try:
            if generation_number is None:
                # Rollback to previous generation
                command = ["nixos-rebuild", "switch", "--rollback"]
            else:
                # Switch to specific generation
                gen_path = f"/nix/var/nix/profiles/system-{generation_number}-link"
                if not os.path.exists(gen_path):
                    raise FileNotFoundError(f"Generation {generation_number} not found")
                
                command = [gen_path + "/bin/switch-to-configuration", "switch"]
            
            await self._run_command(command, timeout=120)
            
            self.logger.info(f"Rolled back to generation {generation_number or 'previous'}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error rolling back generation: {e}")
            return False
    
    def _merge_config(self, current_config: str, patch_content: str) -> str:
        """Merge patch content with current configuration."""
        # This is a simplified implementation
        # In practice, you'd want proper Nix AST parsing and merging
        
        # For now, just append the patch content before the closing brace
        lines = current_config.strip().split('\n')
        
        # Find the last closing brace
        insert_index = -1
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '}':
                insert_index = i
                break
        
        if insert_index == -1:
            # If no closing brace found, just append
            return current_config + '\n\n' + patch_content
        
        # Insert patch before closing brace
        lines.insert(insert_index, '')
        lines.insert(insert_index + 1, '  # NixMind generated configuration')
        lines.insert(insert_index + 2, patch_content)
        
        return '\n'.join(lines)
    
    async def _validate_nix_syntax(self, config_content: str) -> bool:
        """Validate Nix configuration syntax."""
        try:
            # Write to temporary file
            temp_path = self.backup_dir / "temp_config.nix"
            with open(temp_path, 'w') as f:
                f.write(config_content)
            
            # Validate syntax
            await self._run_command([
                "nix-instantiate", "--parse", str(temp_path)
            ])
            
            # Clean up
            temp_path.unlink()
            return True
        
        except Exception:
            return False
    
    async def _cleanup_old_backups(self):
        """Clean up old backup files."""
        try:
            backups = list(self.backup_dir.glob("config-*.nix"))
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Keep only the most recent backups
            for old_backup in backups[self.backup_generations:]:
                old_backup.unlink()
                self.logger.debug(f"Removed old backup: {old_backup}")
        
        except Exception as e:
            self.logger.warning(f"Error cleaning up old backups: {e}")
    
    async def _run_command(
        self,
        command: List[str],
        timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """Run a system command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    command,
                    output=stdout,
                    stderr=stderr
                )
            
            return subprocess.CompletedProcess(
                command,
                process.returncode,
                stdout.decode(),
                stderr.decode()
            )
        
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise subprocess.TimeoutExpired(command, timeout)