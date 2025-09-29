#!/usr/bin/env python3

"""
NixMind Demo Script

This script demonstrates the core functionality of NixMind without requiring
a full Ollama installation. It shows how the system would work with mocked responses.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nixmind.core.config import Config
from nixmind.core.logger import setup_logging
from nixmind.llm.base import LLMResponse
from nixmind.agent.command_parser import CommandParser


class MockLLM:
    """Mock LLM for demonstration purposes."""
    
    def __init__(self):
        self.model_name = "mock-llama3.2"
    
    async def is_available(self):
        return True
    
    async def generate(self, messages, **kwargs):
        # Simulate different responses based on user input
        user_content = messages[-1].content.lower()
        
        if "install blender" in user_content:
            response_content = """{
                "action_type": "config_change",
                "explanation": "安装 Blender 3D 建模软件并启用 CUDA 支持以提升渲染性能",
                "risk_level": "low",
                "commands": [
                    {
                        "type": "nix_config",
                        "content": "  # Blender with CUDA support\\n  programs.blender = {\\n    enable = true;\\n    cudaSupport = true;\\n  };\\n  \\n  # NVIDIA driver support\\n  services.xserver.videoDrivers = [ \\"nvidia\\" ];",
                        "description": "Add Blender with CUDA support to NixOS configuration"
                    }
                ],
                "rollback_info": "Set programs.blender.enable = false; 并重新构建系统",
                "requires_rebuild": true,
                "additional_notes": "需要 NVIDIA 显卡才能使用 CUDA 支持。首次构建可能需要下载较大的软件包。"
            }"""
        
        elif "docker" in user_content or "podman" in user_content:
            response_content = """{
                "action_type": "config_change", 
                "explanation": "启用 Podman 容器运行时并配置用户权限",
                "risk_level": "medium",
                "commands": [
                    {
                        "type": "nix_config",
                        "content": "  # Enable Podman\\n  virtualisation.podman = {\\n    enable = true;\\n    dockerCompat = true;\\n    defaultNetwork.settings.dns_enabled = true;\\n  };\\n  \\n  # Add user to podman group\\n  users.users.your-username.extraGroups = [ \\"podman\\" ];",
                        "description": "Enable Podman with Docker compatibility"
                    }
                ],
                "rollback_info": "Set virtualisation.podman.enable = false; 并从用户组中移除 podman",
                "requires_rebuild": true,
                "additional_notes": "重启后需要重新登录以使组权限生效。可以使用 'podman' 命令或 'docker' 别名。"
            }"""
        
        elif "firewall" in user_content and "ssh" in user_content:
            response_content = """{
                "action_type": "config_change",
                "explanation": "配置防火墙允许自定义 SSH 端口 2222",
                "risk_level": "medium", 
                "commands": [
                    {
                        "type": "nix_config",
                        "content": "  # Configure SSH on custom port\\n  services.openssh = {\\n    enable = true;\\n    ports = [ 2222 ];\\n    settings = {\\n      PasswordAuthentication = false;\\n      KbdInteractiveAuthentication = false;\\n    };\\n  };\\n  \\n  # Open firewall port\\n  networking.firewall.allowedTCPPorts = [ 2222 ];",
                        "description": "Configure SSH on port 2222 and update firewall"
                    }
                ],
                "rollback_info": "恢复默认 SSH 端口 22 并更新防火墙规则",
                "requires_rebuild": true,
                "additional_notes": "确保在应用前测试 SSH 密钥认证，避免被锁定在系统外。"
            }"""
        
        else:
            response_content = """{
                "action_type": "info_request",
                "explanation": "这看起来是一个信息查询请求",
                "risk_level": "low",
                "commands": [],
                "rollback_info": "无需回滚",
                "requires_rebuild": false,
                "additional_notes": "如需配置更改，请提供更具体的请求。"
            }"""
        
        return LLMResponse(
            content=response_content,
            model=self.model_name
        )
    
    def create_system_message(self, content):
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        return MockMessage("system", content)
    
    def create_user_message(self, content):
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        return MockMessage("user", content)


async def demo_request_parsing():
    """Demonstrate request parsing with different scenarios."""
    print("🧠 NixMind Demo - Request Parsing")
    print("=" * 50)
    
    # Setup
    config = Config()
    setup_logging("INFO")
    
    mock_llm = MockLLM()
    parser = CommandParser(mock_llm, config.safety.__dict__)
    
    # Test cases
    test_requests = [
        "帮我安装 Blender 并启用 CUDA 支持",
        "开启 podman 并配置 GPU 支持", 
        "更新防火墙设置，允许 SSH 在端口 2222",
        "显示当前安装的软件包"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n📝 测试请求 {i}: {request}")
        print("-" * 40)
        
        try:
            parsed = await parser.parse_request(request)
            
            print(f"✅ 操作类型: {parsed.action_type.value}")
            print(f"🎯 风险等级: {parsed.risk_level.value}")
            print(f"📋 说明: {parsed.explanation}")
            
            if parsed.commands:
                print(f"📜 生成命令数: {len(parsed.commands)}")
                for j, cmd in enumerate(parsed.commands, 1):
                    print(f"   {j}. [{cmd.type}] {cmd.description}")
                
                print(f"🔄 需要重建: {'是' if parsed.requires_rebuild else '否'}")
                
                # Validate commands
                print("🔍 安全验证:")
                validations = await parser.validate_commands(parsed.commands, request)
                for j, validation in enumerate(validations, 1):
                    status = "✅ 安全" if validation.safe else "⚠️ 有风险"
                    print(f"   命令 {j}: {status} ({validation.risk_level.value})")
                    
                    if validation.risks:
                        for risk in validation.risks[:2]:  # Show first 2 risks
                            print(f"     - {risk['description']}")
            else:
                print("ℹ️  无需执行命令")
            
            if parsed.additional_notes:
                print(f"💡 注意事项: {parsed.additional_notes}")
        
        except Exception as e:
            print(f"❌ 解析失败: {e}")


async def demo_configuration_management():
    """Demonstrate configuration management concepts."""
    print("\n\n🔧 NixMind Demo - Configuration Management")
    print("=" * 50)
    
    print("📁 配置文件管理:")
    print("   - 当前配置: /etc/nixos/configuration.nix")
    print("   - 备份位置: ~/.nixmind/backups/")
    print("   - 备份保留: 5 个最新版本")
    
    print("\n🔄 系统世代管理:")
    print("   - 当前世代: 42 (示例)")
    print("   - 可回滚世代: 38, 39, 40, 41, 42")
    print("   - 回滚命令: nixos-rebuild switch --rollback")
    
    print("\n🛡️ 安全机制:")
    print("   ✅ 执行前确认")
    print("   ✅ Dry-run 模式")
    print("   ✅ 自动备份")
    print("   ✅ 风险评估")
    print("   ✅ 命令验证")


async def main():
    """Main demo function."""
    print("🎭 NixMind 功能演示")
    print("这是一个模拟演示，展示 NixMind 的核心功能")
    print("实际使用需要安装 Ollama 并运行在 NixOS 系统上\n")
    
    await demo_request_parsing()
    await demo_configuration_management()
    
    print("\n\n🎉 演示完成!")
    print("\n要在实际 NixOS 系统上使用 NixMind:")
    print("1. 安装 Ollama: curl -fsSL https://ollama.com/install.sh | sh")
    print("2. 拉取模型: ollama pull llama3.2:latest")
    print("3. 运行 NixMind: python main.py")


if __name__ == "__main__":
    asyncio.run(main())