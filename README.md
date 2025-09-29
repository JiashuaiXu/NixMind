# NixMind

**NixMind** 是一个运行在 **NixOS** 上的本地智能代理系统。  
它通过 **本地大模型**（如 Ollama、llama.cpp、vLLM）来解析自然语言请求，生成对应的 **NixOS 配置修改或 Shell 命令**，并在执行前进行 **安全校验与回退保护**。

## ✨ 特性

- 🧠 **本地大模型接管**  
  使用大模型解析自然语言输入，生成系统操作命令或配置补丁。  

- 🛡 **安全执行**  
  命令不会直接运行，进入代理层进行 `dry-run` 或人工确认。  

- ⏪ **随时回退**  
  基于 **NixOS generations** 和 **btrfs/zfs snapshots**，确保系统可快速恢复。  

- 🌐 **可扩展 API**  
  提供 REST/gRPC 接口，未来可接入 Web UI 或 CLI。  

## 🚀 使用场景

- 自然语言管理 NixOS：  
  > "帮我安装 Blender 并启用 CUDA 支持"  

- 自动修改 `configuration.nix`，并安全回滚：  
  > "开启 podman 并配置 GPU 支持"  

- Web/CLI 界面审核 AI 生成的命令，一键确认或拒绝。  

## 📦 安装与使用

### 前置要求

1. **NixOS** 系统
2. **Ollama** 服务 (推荐) 或其他支持的 LLM 后端
3. **Python 3.8+**

### 快速安装

```bash
# 克隆仓库
git clone https://github.com/JiashuaiXu/NixMind.git
cd NixMind

# 安装依赖
pip install -r requirements.txt

# 或使用 setup.py
pip install -e .
```

### 配置 Ollama

```bash
# 安装并启动 Ollama
curl -fsSL https://ollama.com/install.sh | sh
systemctl start ollama

# 拉取推荐模型
ollama pull llama3.2:latest
```

### 运行 NixMind

```bash
# 直接运行
python main.py

# 或通过安装的命令
nixmind
```

## 🔧 配置

配置文件位置（按优先级）：
1. `~/.config/nixmind/config.json`
2. `/etc/nixmind/config.json` 
3. `./config/config.json`

### 示例配置

```json
{
  "llm": {
    "provider": "ollama",
    "model_name": "llama3.2:latest",
    "api_base": "http://localhost:11434",
    "temperature": 0.1
  },
  "safety": {
    "require_confirmation": true,
    "enable_dry_run": true,
    "risk_threshold": 0.7
  },
  "nixos": {
    "config_path": "/etc/nixos/configuration.nix",
    "backup_generations": 5
  }
}
```

## 💬 使用示例

启动 NixMind 后，您可以用自然语言发送请求：

```
💬 nixmind> 帮我安装 Blender 并启用 CUDA 支持

🤔 Analyzing request...

📋 Analysis:
   Action: config_change
   Risk Level: low
   Explanation: 将安装 Blender 3D 建模软件并启用 NVIDIA CUDA 支持

📝 Generated Commands:
   1. [nix_config] Add Blender with CUDA support
      Content: programs.blender = { enable = true; cudaSupport = true; };...

🚨 Confirmation Required
   Action: 将安装 Blender 3D 建模软件并启用 NVIDIA CUDA 支持
   Risk: low
   Rebuild required: Yes

🤖 Proceed? (yes/no/dry-run): yes

🚀 Executing commands...
   ✅ Configuration updated: Add Blender with CUDA support
   🔄 Rebuilding system...
   ✅ System rebuilt successfully
```

## 📖 CLI 命令

- `help` - 显示帮助信息
- `status` - 显示系统状态  
- `generations` - 列出可用的系统代数
- `quit` - 退出程序

## 🏗 架构组件

### 核心模块

- **`nixmind.core`** - 配置管理和日志系统
- **`nixmind.llm`** - LLM 接口抽象和 Ollama 客户端
- **`nixmind.agent`** - 命令解析器和安全验证
- **`nixmind.nixos`** - NixOS 配置管理和回退机制
- **`nixmind.cli`** - 命令行界面

### 安全机制

1. **命令验证** - 基于规则和 LLM 的双重安全检查
2. **确认流程** - 高风险操作需要用户确认
3. **Dry-run 模式** - 预览配置更改而不实际应用
4. **自动备份** - 每次更改前自动备份当前配置
5. **代数回退** - 利用 NixOS generations 快速回退

## 📦 计划中的模块

- **模型接口**：Ollama ✅ / vLLM ⏳ / llama.cpp ⏳  
- **命令代理层**：命令解析 ✅、风险检测 ✅、dry-run ✅  
- **回退机制**：NixOS generations ✅、btrfs/zfs 快照 ⏳、git 版本控制 ⏳  
- **用户界面**：CLI ✅ / Web Dashboard ⏳  

## 📖 路线图

- [x] 初始化项目结构  
- [x] 接入本地大模型（Ollama 优先）  
- [x] 实现命令代理层（含 dry-run 校验）  
- [x] 集成 NixOS 回退机制  
- [ ] 提供 Web 界面（Vue/React 前端）  
- [ ] 添加 btrfs/zfs 快照支持
- [ ] 实现 REST API 接口
- [ ] 添加更多 LLM 后端支持

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 许可证

MIT License
