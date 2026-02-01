# AstrBot iFlow 插件 - 项目上下文文档

本文档为 iFlow AI Agent 提供项目上下文信息，用于理解和维护 AstrBot iFlow 插件。

## 项目概述

**项目名称**: AstrBot iFlow 插件 (astrbot_plugin_iflow)

**项目类型**: Python 插件项目

**主要目的**: 为 AstrBot 提供与 iFlow CLI 的集成功能，通过 iFlow CLI SDK 实现 ACP 协议消息自动转发和处理结果回复。支持容器化部署场景。

**当前版本**: v2.0.0

**许可证**: GNU Affero General Public License v3.0 (AGPL-3.0)

**作者**: tongrenlu114514

**仓库地址**: https://github.com/tongrenlu114514/astrbot_plugin_iflow

## 技术栈

- **语言**: Python 3.x
- **框架**: AstrBot Plugin SDK (astrbot.api)
- **通信协议**: ACP (Agent Communication Protocol) v1
- **传输方式**: WebSocket
- **SDK**: iflow-cli-sdk >= 0.1.11
- **依赖工具**:
  - AstrBot >= v4.0.0
  - iFlow CLI (作为守护进程运行)
- **核心库**:
  - `asyncio` - 异步编程和超时控制
  - `iflow_sdk` - iFlow CLI SDK（提供 IFlowClient、IFlowOptions、AssistantMessage、TaskFinishMessage 等）
  - `astrbot.api.event` - 事件监听和消息处理
  - `astrbot.api.star` - 插件基类和注册机制
  - `astrbot.core.utils.astrbot_path` - 获取 AstrBot 数据目录

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
│  │  │ 消息监听器 │ ───→ │  iFlow CLI SDK 客户端│   │  │
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

- `iflow_enabled: bool` - 控制消息转发是否启用
- `timeout: int` - iFlow 处理超时时间（默认30秒）
- `acp_url: str` - ACP 服务地址（默认 `ws://host.docker.internal:8090/acp`）
- `client: Optional[IFlowClient]` - iFlow SDK 客户端实例

#### 生命周期方法

1. **`__init__(self, context: Context)`**
   - 初始化插件实例
   - 设置默认属性值
   - 从环境变量读取 ACP 服务地址

2. **`async initialize(self)`**
   - 插件加载时自动调用
   - 获取插件数据目录作为工作目录
   - 配置并创建 iFlow SDK 客户端实例
   - 设置工作目录和文件访问选项

3. **`async terminate(self)`**
   - 插件卸载/停用时调用
   - 关闭 SDK 客户端连接
   - 清理资源

#### 核心功能方法

1. **`@filter.event_message_type(filter.EventMessageType.ALL, priority=1)`**
   - 监听所有消息事件（群聊和私聊）
   - 优先级设为 1，确保先于其他插件执行
   - 处理流程：
     - 检查 iFlow 客户端可用性和启用状态
     - 提取消息内容（跳过空消息）
     - 使用上下文管理器 `async with self.client:` 管理 SDK 生命周期
     - 通过 SDK 发送消息到 iFlow
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

### SDK 客户端: `IFlowClient`

使用 `iflow_cli_sdk` 提供的 SDK 客户端，负责与 iFlow ACP 服务的通信。

#### SDK 配置选项 (`IFlowOptions`)

- `url` - ACP 服务地址
- `auto_start_process` - 是否自动启动 iFlow 进程（设为 false，假设 iFlow 已独立运行）
- `timeout` - 超时时间
- `cwd` - 工作目录（设置为插件数据目录）
- `file_access` - 文件访问权限（设为 false，避免路径检查问题）

#### SDK 消息类型

| 消息类型 | 类型 | 说明 |
|----------|------|------|
| `AssistantMessage` | 接收 | AI 助手响应片段 |
| `TaskFinishMessage` | 接收 | 任务完成信号 |

## 工作流程

### 消息处理流程

```
用户发送消息
    ↓
AstrBot 接收消息
    ↓
触发 on_message 监听器（priority=1）
    ↓
检查 iFlow SDK 客户端可用性和启用状态
    ↓
提取消息内容
    ↓
使用 async with 上下文管理器管理 SDK 客户端
    ↓
通过 SDK 发送消息
    ↓
等待并流式接收响应
    ├─ AssistantMessage → 累积响应内容
    └─ TaskFinishMessage → 结束接收
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
调用 initialize()
    ↓
获取插件数据目录作为工作目录
    ↓
配置 IFlowOptions（url, timeout, cwd, file_access 等）
    ↓
创建 IFlowClient 实例
    ↓
记录初始化结果
```

## 配置

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `IFLOW_ACP_URL` | `ws://host.docker.internal:8090/acp` | iFlow ACP 服务地址 |

### metadata.yaml

插件元数据配置文件，AstrBot 识别插件的关键文件：

```yaml
name: astrbot_plugin_iflow          # 插件唯一标识
display_name: iFlow 插件            # 显示名称
desc: AstrBot iFlow 插件 - 自动转发消息到 iFlow CLI (心流 CLI) 并回复处理结果
version: v2.0.0                      # 版本号
author: tongrenlu114514              # 作者
repo: https://github.com/tongrenlu114514/astrbot_plugin_iflow
```

### requirements.txt

Python 依赖管理文件：

```
iflow-cli-sdk >= 0.1.11
```

## 关键设计决策

### 1. 使用 iFlow CLI SDK

采用官方提供的 `iflow-cli-sdk` SDK 而非直接实现 WebSocket 通信：
- 减少维护成本和复杂度
- 自动处理 ACP 协议细节
- 获得官方支持和更新
- 更好的类型安全和代码可读性

### 2. ACP 协议通信

使用标准的 Agent Communication Protocol (ACP) 进行通信，而非直接调用命令行进程，这样可以：
- 支持容器化部署场景
- 实现流式响应
- 更好的错误处理和状态管理

### 3. 守护进程模式

iFlow CLI 在宿主机上以守护进程方式常驻运行，提供 ACP 服务：
- 避免每次启动的开销
- 容器无法直接访问宿主机进程的完美解决方案
- 支持多个客户端并发连接

### 4. 上下文管理器

使用 `async with self.client:` 上下文管理器管理 SDK 生命周期：
- 自动管理连接的打开和关闭
- 确保资源正确释放
- 简化异常处理

### 5. 优先级设置

消息监听器优先级设为 `priority=1`，确保在 LLM 处理之前拦截消息。

### 6. 超时保护

30秒超时机制防止 iFlow 长时间无响应导致阻塞。

### 7. 错误处理

- 捕获所有异常并记录日志
- 超时错误单独处理并回复用户
- iFlow 不可用时静默返回，不干扰正常功能

### 8. 工作目录隔离

使用 AstrBot 的插件数据目录作为 SDK 的工作目录：
- 避免文件路径冲突
- 提供更好的文件隔离
- 便于插件数据管理

### 9. 文件访问控制

设置 `file_access=False` 禁用文件访问：
- 避免路径检查问题
- 提高安全性
- 简化配置需求

### 10. 开关控制

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

### Q: 插件启动后显示 "初始化 iFlow SDK 客户端失败"？

A: 确保 iFlow CLI 在宿主机上以守护进程运行并启动了 ACP 服务：

```bash
iflow --experimental-acp --port 8090
```

### Q: 容器内无法连接到宿主机的 iFlow？

A: 检查以下事项：
1. 使用 `host.docker.internal` 访问宿主机（Docker Desktop 默认支持）
2. 或使用 `--network host` 模式运行容器
3. 检查防火墙设置
4. 确保容器启动时添加了 `--add-host=host.docker.internal:host-gateway` 参数

### Q: 消息没有转发到 iFlow？

A: 检查以下事项：
1. 使用 `/iflow` 查看插件状态
2. 确认消息转发已启用（`/iflow on`）
3. 检查 AstrBot 日志中的错误信息
4. 确认 iFlow ACP 服务正在运行
5. 确认 `iflow-cli-sdk` 已正确安装

### Q: 如何调整超时时间？

A: 修改 `main.py` 中的 `self.timeout = 30` 值（单位：秒）

### Q: 如何修改 ACP 服务地址？

A: 设置环境变量 `IFLOW_ACP_URL`：

```bash
export IFLOW_ACP_URL=ws://your-host:8090/acp
```

### Q: 支持哪些消息类型？

A: 支持所有文本消息（群聊和私聊），空消息和纯表情消息会被跳过。

### Q: 插件数据存储在哪里？

A: 插件使用 AstrBot 的插件数据目录作为工作目录，通常位于 `{astrbot_data_path}/plugin_data/astrbot_plugin_iflow`。

### Q: 为什么禁用了文件访问？

A: 设置 `file_access=False` 可以避免路径检查问题，简化配置需求，并提高安全性。如果需要文件访问功能，可以修改 `main.py` 中的配置。

### Q: 如何安装 iflow-cli-sdk？

A: 插件会自动安装 requirements.txt 中定义的依赖。如果需要手动安装：

```bash
pip install iflow-cli-sdk>=0.1.11
```

## 扩展方向

### 可能的改进

1. **自动重连机制**
   - 实现连接断开后的自动重连
   - 指数退避重连策略

2. **配置文件支持**
   - 添加配置文件支持超时时间、默认状态等
   - 支持通过配置文件自定义 SDK 选项

3. **消息过滤**
   - 支持按群组/用户过滤
   - 支持关键词过滤

4. **日志记录**
   - 记录转发历史
   - 提供查询指令

5. **性能优化**
   - 消息队列处理
   - 批量转发支持
   - 客户端连接池管理

6. **SDK 功能扩展**
   - 利用 SDK 提供的更多功能（如文件访问、工具调用等）
   - 支持多轮对话上下文管理
   - 支持更复杂的消息类型（图片、文件等）

7. **健康检查**
   - 定期检查 iFlow ACP 服务状态
   - 提供健康状态报告

## 相关资源

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [iFlow 官网](https://iflow.cn)
- [ACP 协议文档](https://agentcommunicationprotocol.dev/)
- [iFlow CLI SDK](https://pypi.org/project/iflow-cli-sdk/)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)

## 维护说明

### 发布新版本流程

1. 更新 `metadata.yaml` 中的版本号
2. 更新 `main.py` 中 `@register` 装饰器的版本号
3. 更新 `requirements.txt`（如有依赖变更）
4. 更新 `README.md` 中的变更日志
5. 更新 `AGENTS.md` 文档版本
6. 测试所有功能（包括与 iFlow CLI SDK 的集成）
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

**文档版本**: 2.1.0

**文档生成时间**: 2026-01-31

**最后更新**: 2026-02-01

**插件版本**: v2.0.0

**SDK 版本**: iflow-cli-sdk >= 0.1.11

**协议版本**: ACP v1