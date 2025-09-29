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
  > “帮我安装 Blender 并启用 CUDA 支持”  

- 自动修改 `configuration.nix`，并安全回滚：  
  > “开启 podman 并配置 GPU 支持”  

- Web/CLI 界面审核 AI 生成的命令，一键确认或拒绝。  

## 📦 计划中的模块
- **模型接口**：Ollama / vLLM / llama.cpp  
- **命令代理层**：命令解析、风险检测、dry-run  
- **回退机制**：NixOS generations、btrfs/zfs 快照、git 版本控制  
- **用户界面**：CLI / Web Dashboard  

## 📖 路线图
- [ ] 初始化项目结构  
- [ ] 接入本地大模型（Ollama 优先）  
- [ ] 实现命令代理层（含 dry-run 校验）  
- [ ] 集成 NixOS 回退机制  
- [ ] 提供 Web 界面（Vue/React 前端）  

## 📜 许可证
MIT License
