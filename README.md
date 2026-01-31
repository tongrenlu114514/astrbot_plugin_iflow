# AstrBot iFlow 插件

AstrBot iFlow 插件 - 通过 ACP 协议自动转发消息到 iFlow CLI 并回复处理结果

AstrBot plugin that automatically forwards messages to iFlow CLI via ACP protocol and replies with the results.

## 功能特性

- 📥 **自动消息转发**: 监听所有消息，自动转发到 iFlow CLI 处理
- ⚡ **实时回复**: 将 iFlow CLI 的处理结果实时回复给用户
- 🔌 **ACP 协议**: 使用标准的 Agent Communication Protocol 进行通信
- 🐳 **容器支持**: 支持在容器环境中连接宿主机的 iFlow 服务
- 🔧 **可用性检测**: 插件启动时自动检测 iFlow ACP 服务是否可用
- 🎛️ **开关控制**: 支持通过指令启用/禁用消息转发功能
- ⏱️ **超时保护**: 30秒超时机制，防止长时间等待
- 🛡️ **错误处理**: 完善的异常捕获和日志记录

## 安装

### 前置要求

1. **安装 iFlow CLI**

   访问 [iFlow CLI 官网](https://iflow.cn) 下载并安装适合您系统的版本。

2. **启动 iFlow ACP 服务**

   在宿主机上以守护进程方式启动 iFlow ACP 服务：

   ```bash
   iflow --experimental-acp --port 8090
   ```

   **建议**：将 iFlow 配置为系统服务，使其在系统启动时自动运行。

3. **容器网络配置**

   如果 AstrBot 运行在 Docker 容器中，确保容器可以访问宿主机的 8090 端口：
   - 使用宿主机 IP 地址（如 `121.37.183.44`）直接访问
   - 确保防火墙允许 8090 端口的入站连接
   - 或使用 `--network host` 模式运行容器

### 安装插件

1. 将插件目录放置到 AstrBot 的 `data/plugins` 目录下
2. 在 AstrBot WebUI 中启用插件

## 使用方法

### 自动转发

插件启用后，所有非空消息都会自动转发到 iFlow CLI 处理，处理结果会自动回复。

### 控制指令

- `/iflow` - 查看当前状态
- `/iflow on` - 启用消息转发
- `/iflow off` - 禁用消息转发
- `/iflow status` - 查看详细状态

## 配置

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `IFLOW_ACP_URL` | `ws://121.37.183.44:8090/acp` | iFlow ACP 服务地址 |

### 插件配置

插件会在启动时自动连接到 iFlow ACP 服务。如果连接失败，插件会记录警告日志但仍会加载。

## 依赖

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) >= v4.0.0
- [iFlow CLI](https://iflow.cn) - 需要在宿主机上以守护进程运行
- [websockets](https://pypi.org/project/websockets/) >= 12.0 - Python WebSocket 库

## 开发

### 插件结构

```
astrbot_plugin_iflow/
├── main.py           # 主插件文件
├── metadata.yaml     # 插件元数据
├── requirements.txt  # Python 依赖
├── README.md         # 说明文档
├── AGENTS.md         # AI Agent 上下文文档
└── LICENSE           # 许可证
```

### 主要功能

- `ACPClient` - ACP WebSocket 客户端类
- `initialize()` - 连接到 iFlow ACP 服务
- `on_message()` - 监听所有消息并通过 ACP 转发
- `iflow_cmd()` - 控制指令处理
- `terminate()` - 关闭连接并清理资源

## 架构说明

插件通过 WebSocket 连接到宿主机的 iFlow ACP 服务，使用标准的 Agent Communication Protocol (ACP) 进行通信：

```
AstrBot (容器)
    ↓
iFlow 插件
    ↓ WebSocket (ACP)
iFlow ACP 服务 (宿主机:8090)
    ↓
iFlow CLI
```

## 许可证

GNU Affero General Public License v3.0

## 支持

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [iFlow 官网](https://iflow.cn)
- [ACP 协议文档](https://agentcommunicationprotocol.dev/)

## 作者

tongrenlu114514
