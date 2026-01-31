# AstrBot iFlow 插件 - 项目上下文文档

本文档为 iFlow AI Agent 提供项目上下文信息，用于理解和维护 AstrBot iFlow 插件。

## 项目概述

**项目名称**: AstrBot iFlow 插件 (astrbot_plugin_iflow)

**项目类型**: Python 插件项目

**主要目的**: 为 AstrBot 提供与 iFlow CLI 的集成功能，通过 ACP 协议实现消息自动转发和处理结果回复。支持容器化部署场景。

**当前版本**: v1.0.0

**许可证**: GNU Affero General Public License v3.0 (AGPL-3.0)

**作者**: tongrenlu114514

**仓库地址**: https://github.com/tongrenlu114514/astrbot_plugin_iflow

## 技术栈

- **语言**: Python 3.x
- **框架**: AstrBot Plugin SDK (astrbot.api)
- **通信协议**: ACP (Agent Communication Protocol) v1
- **传输方式**: WebSocket
- **依赖工具**:
  - AstrBot >= v4.0.0
  - iFlow CLI (作为守护进程运行)
  - websockets >= 12.0
- **核心库**:
  - `asyncio` - 异步编程和超时控制
  - `websockets` - WebSocket 客户端
  - `json` - ACP 消息序列化
  - `astrbot.api.event` - 事件监听和消息处理
  - `astrbot.api.star` - 插件基类和注册机制

## 项目结构

```
astrbot_plugin_iflow/
├── main.py           # 主插件文件（核心实现）
├── metadata.yaml     # 插件元数据配置
├── requirements.txt  # Python 依赖
├── README.md         # 用户文档
├── AGENTS.md         # 本文档（AI Agent 上下文）
├── LICENSE           # AGPL-3.0 许可证
└── .gitignore        # Git 忽略配置
```

## 核心架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    AstrBot (容器)                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │              iFlow 插件                           │  │
│  │  ┌────────────┐      ┌──────────────────────┐   │  │
│  │  │ 消息监听器 │ ───→ │   ACP WebSocket 客户端│   │  │
│  │  └────────────┘      └──────────┬───────────┘   │  │
│  │                                   │               │  │
│  └───────────────────────────────────┼───────────────┘  │
│                                        │                  │
└────────────────────────────────────────┼──────────────────┘
                                         │
                                   WebSocket (ACP)
                                         │
┌────────────────────────────────────────┼──────────────────┐
│                 宿主机                  │                  │
│  ┌─────────────────────────────────────┼──────────────┐   │
│  │       iFlow ACP 服务 (8090端口)      │              │   │
│  │  ┌─────────────────────────────────┐│              │   │
│  │  │        ACP 协议处理器            ││              │   │
│  │  └─────────────────────────────────┘│              │   │
│  │                                     │               │   │
│  │  ┌─────────────────────────────────┐│              │   │
│  │  │        iFlow CLI (守护进程)      ││              │   │
│  │  └─────────────────────────────────┘│              │   │
│  └─────────────────────────────────────┼──────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 插件类: `IFlowPlugin`

继承自 `astrbot.api.star.Star`，是插件的核心类。

#### 主要属性

- `iflow_available: bool` - 标记 iFlow ACP 服务是否可用
- `iflow_enabled: bool` - 控制消息转发是否启用
- `timeout: int` - iFlow 处理超时时间（默认30秒）
- `acp_url: str` - ACP 服务地址（默认 `ws://host.docker.internal:8090/acp`）
- `acp_client: Optional[ACPClient]` - ACP WebSocket 客户端实例

#### 生命周期方法

1. **`__init__(self, context: Context)`**
   - 初始化插件实例
   - 设置默认属性值
   - 从环境变量读取 ACP 服务地址

2. **`async initialize(self)`**
   - 插件加载时自动调用
   - 创建 ACP 客户端并连接到 iFlow ACP 服务
   - 设置 `iflow_available` 状态

3. **`async terminate(self)`**
   - 插件卸载/停用时调用
   - 关闭 WebSocket 连接
   - 清理资源

#### 核心功能方法

1. **`@filter.event_message_type(filter.EventMessageType.ALL, priority=1)`**
   - 监听所有消息事件（群聊和私聊）
   - 优先级设为 1，确保先于其他插件执行
   - 处理流程：
     - 检查 iFlow 可用性和启用状态
     - 提取消息内容（跳过空消息）
     - 通过 ACP 协议发送消息到 iFlow
     - 流式接收响应并累积
     - 回复用户处理结果
     - 处理超时和异常情况

2. **`@filter.command("iflow")`**
   - 控制指令处理器
   - 支持操作：
     - 无参数：显示当前状态
     - `on`: 启用消息转发
     - `off`: 禁用消息转发
     - `status`: 显示详细状态

### ACP 客户端类: `ACPClient`

负责与 iFlow ACP 服务的 WebSocket 通信。

#### 主要方法

- `async connect() -> bool` - 连接到 iFlow ACP 服务
- `async send_message(content: str, timeout: int) -> str` - 发送消息并获取响应
- `async close()` - 关闭连接

#### ACP 消息类型

| 消息类型 | 方向 | 说明 |
|----------|------|------|
| `user_message` | 发送 | 用户消息 |
| `agent_message_chunk` | 接收 | AI 响应片段 |
| `task_finish` | 接收 | 任务完成 |
| `error` | 接收 | 错误消息 |

## 工作流程

### 消息处理流程

```
用户发送消息
    ↓
AstrBot 接收消息
    ↓
触发 on_message 监听器（priority=1）
    ↓
检查 iFlow ACP 可用性和启用状态
    ↓
提取消息内容
    ↓
通过 WebSocket 发送 ACP user_message
    ↓
等待并流式接收响应
    ├─ agent_message_chunk → 累积响应内容
    └─ task_finish → 结束接收
    ↓
回复用户处理结果
```

### 插件初始化流程

```
AstrBot 加载插件
    ↓
实例化 IFlowPlugin
    ↓
读取 ACP 服务地址配置
    ↓
创建 ACPClient 实例
    ↓
调用 initialize()
    ↓
连接到 iFlow ACP WebSocket 服务
    ↓
设置 iflow_available 状态
    ↓
记录连接结果
```

## 配置

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `IFLOW_ACP_URL` | `ws://121.37.183.44:8090/acp` | iFlow ACP 服务地址 |

### metadata.yaml

插件元数据配置文件，AstrBot 识别插件的关键文件：

```yaml
name: astrbot_plugin_iflow          # 插件唯一标识
display_name: iFlow 插件            # 显示名称
desc: AstrBot iFlow 插件...         # 功能描述
version: v1.0.0                      # 版本号
author: tongrenlu114514              # 作者
repo: https://github.com/...         # 仓库地址
```

### requirements.txt

Python 依赖管理文件：

```
websockets>=12.0
```

## 关键设计决策

### 1. ACP 协议通信

使用标准的 Agent Communication Protocol (ACP) 进行通信，而非直接调用命令行进程，这样可以：
- 支持容器化部署场景
- 实现流式响应
- 更好的错误处理和状态管理

### 2. 守护进程模式

iFlow CLI 在宿主机上以守护进程方式常驻运行，提供 ACP 服务：
- 避免每次启动的开销
- 容器无法直接访问宿主机进程的完美解决方案
- 支持多个客户端并发连接

### 3. WebSocket 连接

使用 WebSocket 而非 HTTP REST API：
- 支持双向通信
- 实时流式响应
- 更低的延迟

### 4. 优先级设置

消息监听器优先级设为 `priority=1`，确保在 LLM 处理之前拦截消息。

### 5. 超时保护

30秒超时机制防止 iFlow 长时间无响应导致阻塞。

### 6. 错误处理

- 捕获所有异常并记录日志
- 超时错误单独处理并回复用户
- iFlow 不可用时静默返回，不干扰正常功能

### 7. 开关控制

提供运行时控制指令，允许用户动态启用/禁用消息转发。

## 开发约定

### 代码风格

- 使用 Python 异步编程模式（async/await）
- 所有插件方法必须使用装饰器注册
- 日志使用 `astrbot.api.logger`
- 文档字符串使用中文
- 使用 ruff 格式化代码

### 文件命名

- 主文件必须命名为 `main.py`
- 插件类名使用 PascalCase（如 `IFlowPlugin`）
- 指令方法使用蛇形命名（如 `iflow_cmd`）

### Git 提交规范

使用语义化提交消息：

- `feat:` - 新功能
- `fix:` - 修复 bug
- `docs:` - 文档更新
- `refactor:` - 代码重构

## 测试建议

### 功能测试

1. **ACP 连接测试**
   - 测试 iFlow ACP 服务可用时的连接
   - 测试 iFlow ACP 服务不可用时的降级处理
   - 测试连接断开后的重连

2. **消息转发**
   - 测试普通文本消息转发
   - 测试空消息跳过
   - 测试超时场景
   - 测试异常场景
   - 测试流式响应累积

3. **控制指令**
   - 测试 `/iflow` 状态查询
   - 测试 `/iflow on` 启用功能
   - 测试 `/iflow off` 禁用功能
   - 测试 `/iflow status` 详细状态

### 边界测试

- iFlow 返回空响应
- iFlow 返回大量流式响应
- iFlow 返回错误消息
- 并发消息处理
- 网络中断场景

## 常见问题

### Q: 插件启动后显示 "iFlow ACP 服务连接失败"？

A: 确保 iFlow CLI 在宿主机上以守护进程运行并启动了 ACP 服务：

```bash
iflow --experimental-acp --port 8090
```

### Q: 容器内无法连接到宿主机的 iFlow？

A: 检查以下事项：
1. 使用 `host.docker.internal` 访问宿主机（Docker Desktop 默认支持）
2. 或使用 `--network host` 模式运行容器
3. 检查防火墙设置

### Q: 消息没有转发到 iFlow？

A: 检查以下事项：
1. 使用 `/iflow` 查看插件状态
2. 确认消息转发已启用（`/iflow on`）
3. 检查 AstrBot 日志中的错误信息
4. 确认 iFlow ACP 服务正在运行

### Q: 如何调整超时时间？

A: 修改 `main.py` 中的 `self.timeout = 30` 值（单位：秒）

### Q: 如何修改 ACP 服务地址？

A: 设置环境变量 `IFLOW_ACP_URL`：

```bash
export IFLOW_ACP_URL=ws://your-host:8090/acp
```

### Q: 支持哪些消息类型？

A: 支持所有文本消息（群聊和私聊），空消息和纯表情消息会被跳过。

## 扩展方向

### 可能的改进

1. **自动重连机制**
   - 实现连接断开后的自动重连
   - 指数退避重连策略

2. **配置文件支持**
   - 添加配置文件支持超时时间、默认状态等

3. **消息过滤**
   - 支持按群组/用户过滤
   - 支持关键词过滤

4. **日志记录**
   - 记录转发历史
   - 提供查询指令

5. **性能优化**
   - 消息队列处理
   - 批量转发支持
   - 连接池管理

## 相关资源

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [iFlow 官网](https://iflow.cn)
- [ACP 协议文档](https://agentcommunicationprotocol.dev/)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [websockets 库文档](https://websockets.readthedocs.io/)

## 维护说明

### 发布新版本流程

1. 更新 `metadata.yaml` 中的版本号
2. 更新 `main.py` 中的版本号
3. 更新 `requirements.txt`（如有依赖变更）
4. 更新 `README.md` 中的变更日志
5. 更新 `AGENTS.md` 文档版本
6. 测试所有功能
7. 提交 Git commit
8. 推送到远程仓库

### Bug 修复流程

1. 在 issue 中描述问题
2. 定位问题代码
3. 编写测试用例
4. 修复代码
5. 验证修复
6. 更新文档（如有必要）
7. 提交 commit

---

**文档版本**: 2.0.0

**文档生成时间**: 2026-01-31

**最后更新**: 2026-01-31

**插件版本**: v1.0.0

**协议版本**: ACP v1