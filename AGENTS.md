# AstrBot iFlow 插件 - 项目上下文文档

本文档为 iFlow AI Agent 提供项目上下文信息，用于理解和维护 AstrBot iFlow 插件。

## 项目概述

**项目名称**: AstrBot iFlow 插件 (astrbot_plugin_iflow)

**项目类型**: Python 插件项目

**主要目的**: 为 AstrBot 提供与 iFlow CLI 的集成功能，通过 iFlow CLI SDK 实现 ACP 协议消息自动转发和处理结果回复。支持容器化部署场景、独立会话管理和会话持久化。

**当前版本**: v4.0.0

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
  - `asyncio` - 异步编程、超时控制和并发处理
  - `iflow_sdk` - iFlow CLI SDK（提供 IFlowClient、IFlowOptions、AssistantMessage、TaskFinishMessage 等）
  - `astrbot.api.event` - 事件监听和消息处理
  - `astrbot.api.star` - 插件基类和注册机制
  - `astrbot.api.logger` - 日志记录
  - `astrbot.api.AstrBotConfig` - 配置管理
  - `astrbot.core.utils.astrbot_path` - 获取 AstrBot 数据目录
  - `json` - 会话元数据持久化
  - `subprocess` - 远程服务器目录创建

## 项目结构

```
astrbot_plugin_iflow/
├── main.py              # 主插件文件（核心实现）
├── metadata.yaml        # 插件元数据配置
├── requirements.txt     # Python 依赖
├── _conf_schema.json    # 配置模式定义（AstrBot 配置界面使用）
├── README.md            # 用户文档
├── AGENTS.md            # 本文档（AI Agent 上下文）
├── CHANGELOG.md         # 变更日志
├── LICENSE              # AGPL-3.0 许可证
└── .gitignore           # Git 忽略配置
```

## 核心架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      AstrBot (容器)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              iFlow 插件                               │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │            消息监听器 (priority=1)            │   │  │
│  │  └─────────────────────┬────────────────────────┘   │  │
│  │                        │                              │  │
│  │  ┌─────────────────────▼────────────────────────┐   │  │
│  │  │            会话路由器 (session_id)           │   │  │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐       │   │  │
│  │  │  │群组会话 │  │私聊会话 │  │  ...   │       │   │  │
│  │  │  └────┬────┘  └────┬────┘  └────┬────┘       │   │  │
│  │  └───────┼────────────┼────────────┼────────────┘   │  │
│  │          │            │            │                  │  │
│  │  ┌───────▼────────────▼────────────▼────────────┐   │  │
│  │  │           会话池 (Session Pool)              │   │  │
│  │  │  ┌──────────────────────────────────────┐   │   │  │
│  │  │  │ sessions: Dict[str, IFlowClient]     │   │   │  │
│  │  │  │ session_locks: Dict[str, asyncio.Lock]│  │   │  │
│  │  │  │ global_lock: asyncio.Lock             │   │   │  │
│  │  │  └──────────────────────────────────────┘   │   │  │
│  │  └─────────────────────┬────────────────────────┘   │  │
│  │                        │                              │  │
│  │  ┌─────────────────────▼────────────────────────┐   │  │
│  │  │         会话元数据管理器                     │   │  │
│  │  │  ┌──────────────────────────────────────┐   │   │  │
│  │  │  │  sessions.json (持久化存储)          │   │   │  │
│  │  │  │  - session_id                        │   │   │  │
│  │  │  │  - session_type                      │   │   │  │
│  │  │  │  - target_id                         │   │   │  │
│  │  │  │  - created_at                        │   │   │  │
│  │  │  │  - last_accessed_at                  │   │   │  │
│  │  │  │  - message_count                     │   │   │  │
│  │  │  │  - workspace_dir                     │   │   │  │
│  │  │  └──────────────────────────────────────┘   │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            工作目录 (Workspace)                      │  │
│  │  {astrbot_data}/plugin_data/astrbot_plugin_iflow/   │  │
│  │  ├── sessions.json                                  │  │
│  │  └── sessions/                                      │  │
│  │      ├── group_123456/                              │  │
│  │      ├── private_789012/                            │  │
│  │      └── ...                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                     WebSocket (ACP)
                           │
┌─────────────────────────────────────────────────────────────┐
│                    宿主机 / 远程服务器                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       iFlow ACP 服务 (8090端口)                       │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │        ACP 协议处理器                        │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │        iFlow CLI (守护进程)                  │   │  │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │   │  │
│  │  │  │会话1    │  │会话2    │  │  ...    │     │   │  │
│  │  │  └─────────┘  └─────────┘  └─────────┘     │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 插件类: `IFlowPlugin`

继承自 `astrbot.api.star.Star`，是插件的核心类。

#### 主要属性

**配置属性**:
- `config: AstrBotConfig` - AstrBot 配置对象
- `iflow_enabled: bool` - 控制消息转发是否启用
- `timeout: int` - iFlow 处理超时时间（默认30秒）
- `acp_url: str` - ACP 服务地址（默认 `ws://host.docker.internal:8090/acp`）

**会话池属性**:
- `sessions: Dict[str, IFlowClient]` - 会话池，键为 session_id，值为 SDK 客户端实例
- `session_locks: Dict[str, asyncio.Lock]` - 每个会话的异步锁，防止并发冲突
- `global_lock: asyncio.Lock` - 保护共享资源（会话池、元数据）的全局锁

**目录属性**:
- `base_data_dir: str` - 插件基础数据目录
- `sessions_dir: str` - 会话目录，存储各会话的工作空间

#### 生命周期方法

1. **`__init__(self, context: Context, config: AstrBotConfig)`**
   - 初始化插件实例
   - 从配置对象读取设置（enabled、timeout、acp_url）
   - 初始化会话池和锁字典

2. **`async initialize(self)`**
   - 插件加载时自动调用
   - 创建插件基础数据目录和会话目录
   - 调用 `_restore_sessions()` 恢复历史会话
   - 记录初始化结果

3. **`async terminate(self)`**
   - 插件卸载/停用时调用
   - 调用 `close_all_sessions()` 关闭所有会话
   - 清理资源

#### 会话管理方法

1. **`async get_session_id(self, event: AstrMessageEvent) -> str`**
   - 从消息事件中提取会话ID
   - 群聊消息返回 `group_{group_id}`
   - 私聊消息返回 `private_{user_id}`
   - 兜底返回 `unknown_{id(event)}`

2. **`async get_or_create_session(self, session_id: str) -> Optional[IFlowClient]`**
   - 获取或创建会话客户端
   - 如果会话已存在，更新最后访问时间并返回
   - 如果会话不存在，创建新的客户端并保持长连接
   - 创建会话目录（本地和远程服务器）
   - 添加会话元数据到持久化存储

3. **`async close_session(self, session_id: str)`**
   - 关闭指定会话并清理资源
   - 关闭客户端连接
   - 从会话池中移除
   - 移除会话锁和元数据

4. **`async close_all_sessions(self)`**
   - 关闭所有会话并清理资源
   - 遍历会话池，关闭所有客户端
   - 清空会话池和锁字典
   - 清空元数据文件

#### 元数据管理方法

1. **`_get_sessions_metadata_file(self) -> str`**
   - 获取会话元数据文件路径

2. **`async _load_sessions_metadata(self) -> Dict`**
   - 加载会话元数据文件
   - 文件不存在时返回空结构

3. **`async _save_sessions_metadata(self, metadata: Dict)`**
   - 保存会话元数据文件（原子操作）
   - 使用临时文件 + 重命名确保数据安全

4. **`_parse_session_id(self, session_id: str) -> tuple`**
   - 解析会话ID，返回 (session_type, target_id)

5. **`async _add_session_metadata(self, session_id, session_type, target_id, workspace_dir)`**
   - 添加会话元数据

6. **`async _update_session_access_time(self, session_id: str)`**
   - 更新会话的最后访问时间

7. **`async _remove_session_metadata(self, session_id: str)`**
   - 移除会话元数据

#### 会话恢复方法

1. **`async _restore_sessions(self)`**
   - 恢复历史会话
   - 读取元数据文件，获取所有历史会话
   - 使用 `asyncio.gather` 并发恢复会话
   - 统计并记录恢复结果

2. **`async _restore_single_session(self, session_meta: Dict) -> bool`**
   - 恢复单个会话
   - 在远程服务器创建会话目录
   - 创建 SDK 客户端并连接
   - 保存到会话池

#### 核心功能方法

1. **`@filter.event_message_type(filter.EventMessageType.ALL, priority=1)`**
   - `async on_message(self, event: AstrMessageEvent)`
   - 监听所有消息事件（群聊和私聊）
   - 优先级设为 1，确保先于其他插件执行
   - 处理流程：
     - 检查插件启用状态
     - 提取消息内容（跳过空消息）
     - 获取会话ID
     - 获取或创建会话客户端
     - 获取会话锁，防止并发冲突
     - 直接发送消息（不使用 `async with`，保持长连接）
     - 流式接收响应并累积
     - 回复用户处理结果
     - 处理超时和异常情况

2. **`@filter.command("iflow")`**
   - `async iflow_cmd(self, event: AstrMessageEvent, action: str = None, target: str = None)`
   - 控制指令处理器
   - 支持操作：
     - 无参数：显示基本状态
     - `on`: 启用消息转发
     - `off`: 禁用消息转发
     - `status`: 显示详细状态和会话列表
     - `sessions`: 查看所有活跃会话及工作目录
     - `clear all`: 清除所有会话
     - `clear current`: 清除当前会话
     - `clear <id>`: 清除指定群组/用户会话

### SDK 客户端: `IFlowClient`

使用 `iflow_cli_sdk` 提供的 SDK 客户端，负责与 iFlow ACP 服务的通信。

#### SDK 配置选项 (`IFlowOptions`)

- `url` - ACP 服务地址
- `auto_start_process` - 是否自动启动 iFlow 进程（设为 false，假设 iFlow 已独立运行）
- `timeout` - 超时时间
- `cwd` - 工作目录（设置为插件数据目录下的会话目录）
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
检查插件启用状态
    ↓
提取消息内容（跳过空消息）
    ↓
获取会话ID（group_xxx 或 private_xxx）
    ↓
获取或创建会话客户端
    ├─ 会话已存在 → 更新最后访问时间
    └─ 会话不存在 → 创建新会话
        ├─ 创建会话目录（本地 + 远程服务器）
        ├─ 配置 IFlowOptions
        ├─ 创建 IFlowClient 并连接
        └─ 保存到会话池和元数据
    ↓
获取会话锁（防止并发冲突）
    ↓
直接发送消息（保持长连接）
    ↓
等待并流式接收响应
    ├─ AssistantMessage → 累积响应内容
    └─ TaskFinishMessage → 结束接收
    ↓
回复用户处理结果
    ↓
释放会话锁
```

### 插件初始化流程

```
AstrBot 加载插件
    ↓
实例化 IFlowPlugin
    ↓
从配置对象读取设置（enabled, timeout, acp_url）
    ↓
调用 initialize()
    ↓
创建插件基础数据目录
    ↓
创建会话目录
    ↓
调用 _restore_sessions()
    ├─ 加载会话元数据文件
    ├─ 并发恢复所有历史会话
    │   ├─ 在远程服务器创建会话目录
    │   ├─ 创建 IFlowClient 并连接
    │   └─ 保存到会话池
    └─ 统计恢复结果
    ↓
记录初始化结果
```

### 会话创建流程

```
收到消息，会话不存在
    ↓
解析会话ID（session_type, target_id）
    ↓
创建本地会话目录
    ↓
在远程服务器创建会话目录（SSH）
    ↓
配置 IFlowOptions（使用服务器路径作为 cwd）
    ↓
创建 IFlowClient 实例
    ↓
调用 client.connect() 建立长连接
    ↓
保存到会话池（sessions 字典）
    ↓
创建会话锁（session_locks 字典）
    ↓
添加会话元数据（sessions.json）
    ├─ session_id
    ├─ session_type
    ├─ target_id
    ├─ created_at
    ├─ last_accessed_at
    ├─ message_count
    └─ workspace_dir
    ↓
返回客户端实例
```

### 会话关闭流程

```
调用 close_session(session_id)
    ↓
获取全局锁
    ↓
检查会话是否存在
    ↓
关闭客户端连接（client.close()）
    ↓
从会话池中移除（sessions 字典）
    ↓
移除会话锁（session_locks 字典）
    ↓
移除会话元数据（从 sessions.json）
    ↓
释放全局锁
    ↓
记录日志
```

### 会话恢复流程

```
插件启动，调用 _restore_sessions()
    ↓
加载会话元数据文件（sessions.json）
    ↓
获取所有历史会话列表
    ↓
并发恢复会话（asyncio.gather）
    ├─ 任务1: 恢复会话1
    ├─ 任务2: 恢复会话2
    └─ 任务N: 恢复会话N
        ↓
        在远程服务器创建会话目录
        ↓
        配置 IFlowOptions
        ↓
        创建 IFlowClient 并连接
        ↓
        保存到会话池
    ↓
等待所有恢复任务完成
    ↓
统计恢复结果（成功/失败）
    ↓
记录日志
```

## 配置

### 配置模式 (_conf_schema.json)

插件使用 `_conf_schema.json` 定义配置模式，用于 AstrBot 配置界面：

```json
{
  "acp_url": {
    "description": "iFlow ACP 服务地址",
    "type": "string",
    "default": "ws://host.docker.internal:8090/acp",
    "hint": "iFlow CLI 的 ACP WebSocket 服务地址，通常格式为 ws://host:port/acp"
  },
  "timeout": {
    "description": "处理超时时间（秒）",
    "type": "int",
    "default": 30,
    "hint": "iFlow 处理请求的最大等待时间，超时后将取消请求"
  },
  "enabled": {
    "description": "启用消息转发",
    "type": "bool",
    "default": true,
    "hint": "是否自动将消息转发到 iFlow 处理"
  }
}
```

### 配置说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enabled` | bool | true | 是否启用消息转发 |
| `timeout` | int | 30 | 处理超时时间（秒） |
| `acp_url` | string | `ws://host.docker.internal:8090/acp` | iFlow ACP 服务地址 |

### metadata.yaml

插件元数据配置文件，AstrBot 识别插件的关键文件：

```yaml
name: astrbot_plugin_iflow                      # 插件唯一标识
display_name: iFlow 插件                        # 显示名称
desc: AstrBot iFlow 插件 - 自动转发消息到 iFlow CLI (心流 CLI) 并回复处理结果，支持群组独立会话和会话持久化
version: v4.0.0                                 # 版本号
author: tongrenlu114514                         # 作者
repo: https://github.com/tongrenlu114514/astrbot_plugin_iflow
```

### requirements.txt

Python 依赖管理文件：

```
iflow-cli-sdk >= 0.1.11
```

### 会话元数据文件 (sessions.json)

存储会话持久化信息，位于 `{astrbot_data}/plugin_data/astrbot_plugin_iflow/sessions.json`：

```json
{
  "version": "1.0.0",
  "created_at": "2026-02-01T00:00:00.000Z",
  "updated_at": "2026-02-01T12:00:00.000Z",
  "sessions": [
    {
      "session_id": "group_123456",
      "session_type": "group",
      "target_id": "123456",
      "created_at": "2026-02-01T00:00:00.000Z",
      "last_accessed_at": "2026-02-01T12:00:00.000Z",
      "message_count": 10,
      "workspace_dir": "/path/to/sessions/group_123456"
    },
    {
      "session_id": "private_789012",
      "session_type": "private",
      "target_id": "789012",
      "created_at": "2026-02-01T01:00:00.000Z",
      "last_accessed_at": "2026-02-01T11:00:00.000Z",
      "message_count": 5,
      "workspace_dir": "/path/to/sessions/private_789012"
    }
  ]
}
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

### 4. 会话池架构

从单客户端架构重构为会话池架构，每个群组和私聊拥有独立的会话：
- **会话隔离**: 不同群组/私聊的对话上下文完全独立
- **并发处理**: 使用会话锁防止同一会话的并发请求冲突
- **资源管理**: 动态创建和销毁会话，按需分配资源
- **可扩展性**: 支持无限数量的独立会话

### 5. 长连接模式

移除 `async with` 上下文管理器，使用长连接保持会话：
- **持久性**: 会话在插件重启后自动恢复
- **上下文保持**: 保留对话历史和上下文
- **性能优化**: 避免重复建立连接的开销
- **状态管理**: iFlow 可以维护会话内部状态

### 6. 会话持久化

使用 JSON 文件持久化会话元数据：
- **自动恢复**: 插件启动时自动恢复所有历史会话
- **元数据管理**: 记录会话类型、创建时间、访问时间等
- **原子操作**: 使用临时文件 + 重命名确保数据安全
- **版本控制**: 元数据包含版本信息，便于未来升级

### 7. 并发恢复

使用 `asyncio.gather` 并发恢复多个会话：
- **启动优化**: 并发恢复所有会话，大幅减少启动时间
- **容错机制**: 单个会话恢复失败不影响其他会话
- **结果统计**: 统计成功和失败的会话数量

### 8. 工作目录隔离

每个会话使用独立的工作目录：
- **数据隔离**: 不同会话的文件数据完全隔离
- **远程支持**: 支持在远程服务器上创建工作目录（SSH）
- **路径管理**: 使用服务器路径作为 SDK 的 cwd 参数

### 9. 锁机制

使用多级锁机制保护共享资源：
- **全局锁**: 保护会话池和元数据的读写操作
- **会话锁**: 保护单个会话的消息处理，防止并发冲突
- **异步安全**: 所有锁都是异步锁，支持协程环境

### 10. 优先级设置

消息监听器优先级设为 `priority=1`，确保在 LLM 处理之前拦截消息。

### 11. 超时保护

30秒超时机制防止 iFlow 长时间无响应导致阻塞。

### 12. 错误处理

- 捕获所有异常并记录日志
- 超时错误单独处理并回复用户
- 会话恢复失败不影响插件启动
- iFlow 不可用时返回友好错误信息

### 13. 文件访问控制

设置 `file_access=False` 禁用文件访问：
- 避免路径检查问题
- 提高安全性
- 简化配置需求

### 14. 运行时控制

提供丰富的运行时控制指令：
- 动态启用/禁用消息转发
- 查看会话列表和状态
- 清除指定会话或所有会话
- 支持多种清除方式（all、current、指定ID）

## 控制指令

### /iflow

插件控制指令，支持全局控制和会话管理：

```
# 基本控制
/iflow              # 显示基本状态（启用状态、ACP地址、活跃会话数）
/iflow on           # 启用消息转发
/iflow off          # 禁用消息转发
/iflow status       # 显示详细状态（包括会话列表）

# 会话管理
/iflow sessions     # 查看所有活跃会话及工作目录
/iflow clear all    # 清除所有会话
/iflow clear current # 清除当前会话
/iflow clear <id>   # 清除指定会话（群组ID或用户ID）
```

### 指令详细说明

#### `/iflow` - 基本状态查询

显示插件的基本状态信息：

```
iFlow 消息转发: 启用
ACP 地址: ws://host.docker.internal:8090/acp
活跃会话数: 3
```

#### `/iflow on` - 启用消息转发

启用插件的消息转发功能：

```
iFlow 消息转发已启用
```

#### `/iflow off` - 禁用消息转发

禁用插件的消息转发功能：

```
iFlow 消息转发已禁用
```

#### `/iflow status` - 详细状态查询

显示插件的详细状态信息，包括所有活跃会话列表：

```
iFlow 消息转发: 启用
ACP 地址: ws://host.docker.internal:8090/acp
活跃会话数: 3
会话列表:
  - group_123456
  - group_789012
  - private_111222
```

#### `/iflow sessions` - 查看所有会话

显示所有活跃会话及其工作目录：

```
活跃会话列表 (3 个):
  - group_123456: /path/to/sessions/group_123456
  - group_789012: /path/to/sessions/group_789012
  - private_111222: /path/to/sessions/private_111222
```

#### `/iflow clear all` - 清除所有会话

清除所有活跃会话：

```
已清除所有会话
```

#### `/iflow clear current` - 清除当前会话

清除当前消息来源的会话（群组或私聊）：

```
已清除当前会话: group_123456
```

#### `/iflow clear <id>` - 清除指定会话

清除指定群组或用户的会话：

```
已清除群组会话: 123456
```

或

```
已清除私聊会话: 111222
```

如果指定的会话不存在：

```
未找到会话: 999888
```

#### 错误提示

使用无效的参数时会显示帮助信息：

```
用法: /iflow [on|off|status|sessions|clear [target]]
  /iflow on              - 启用消息转发
  /iflow off             - 禁用消息转发
  /iflow status          - 查看详细状态
  /iflow sessions        - 查看所有会话
  /iflow clear all       - 清除所有会话
  /iflow clear current   - 清除当前会话
  /iflow clear <id>      - 清除指定会话
```

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

3. **会话管理**
   - 测试群组会话创建和隔离
   - 测试私聊会话创建和隔离
   - 测试不同会话的对话上下文独立性
   - 测试会话持久化（重启后恢复）
   - 测试会话并发处理（同一会话的并发请求）

4. **控制指令**
   - 测试 `/iflow` 基本状态查询
   - 测试 `/iflow on` 启用功能
   - 测试 `/iflow off` 禁用功能
   - 测试 `/iflow status` 详细状态
   - 测试 `/iflow sessions` 会话列表查询
   - 测试 `/iflow clear all` 清除所有会话
   - 测试 `/iflow clear current` 清除当前会话
   - 测试 `/iflow clear <id>` 清除指定会话

5. **元数据持久化**
   - 测试会话元数据保存
   - 测试会话元数据加载
   - 测试元数据原子操作（崩溃恢复）
   - 测试元数据版本兼容性

6. **远程服务器集成**
   - 测试 SSH 远程目录创建
   - 测试远程目录创建失败的处理
   - 测试远程路径作为 SDK cwd 参数

### 边界测试

- iFlow 返回空响应
- iFlow 返回大量流式响应
- iFlow 返回错误消息
- 并发消息处理（同一会话）
- 并发消息处理（不同会话）
- 网络中断场景
- 会话池满载场景
- 元数据文件损坏场景
- 远程服务器不可达场景

## 常见问题

### Q: 插件启动后显示 "初始化 iFlow 插件失败"？

A: 检查以下事项：
1. 确保 AstrBot 插件数据目录有写权限
2. 检查日志中的详细错误信息
3. 确认配置文件格式正确

### Q: iFlow ACP 服务不可用时会发生什么？

A: 插件会尝试恢复历史会话，失败的会话会被记录但不影响插件启动。用户在发送消息时会收到错误提示。

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

A: 在 AstrBot 插件配置中修改 `timeout` 值（单位：秒）。

### Q: 如何修改 ACP 服务地址？

A: 在 AstrBot 插件配置中修改 `acp_url` 值。

### Q: 会话是如何隔离的？

A: 每个群组和私聊都有独立的会话ID：
- 群聊会话ID格式：`group_{group_id}`
- 私聊会话ID格式：`private_{user_id}`

不同会话的对话上下文完全独立，互不干扰。

### Q: 插件重启后会话会丢失吗？

A: 不会。插件使用 `sessions.json` 文件持久化会话元数据，重启后会自动恢复所有历史会话。

### Q: 如何清除所有会话？

A: 使用指令 `/iflow clear all`。

### Q: 如何清除特定会话？

A: 使用指令 `/iflow clear <id>`，其中 `<id>` 是群组ID或用户ID。例如：
- 清除群组会话：`/iflow clear 123456`
- 清除私聊会话：`/iflow clear 789012`

### Q: 支持哪些消息类型？

A: 支持所有文本消息（群聊和私聊），空消息和纯表情消息会被跳过。

### Q: 插件数据存储在哪里？

A: 插件数据存储在 AstrBot 的插件数据目录：
- 基础目录：`{astrbot_data_path}/plugin_data/astrbot_plugin_iflow`
- 会话目录：`{astrbot_data_path}/plugin_data/astrbot_plugin_iflow/sessions`
- 元数据文件：`{astrbot_data_path}/plugin_data/astrbot_plugin_iflow/sessions.json`

### Q: 为什么使用远程服务器路径作为工作目录？

A: 当前配置在远程服务器（121.37.183.44）上创建会话目录，以便 iFlow CLI 可以访问持久化的会话数据。这确保了容器重启后会话数据仍然可用。

### Q: 如何禁用远程服务器目录创建？

A: 修改 `main.py` 中的 `_get_or_create_session` 和 `_restore_single_session` 方法，移除 SSH 命令调用，使用本地路径作为 `cwd` 参数。

### Q: 为什么禁用了文件访问？

A: 设置 `file_access=False` 可以避免路径检查问题，简化配置需求，并提高安全性。如果需要文件访问功能，可以修改配置。

### Q: 如何安装 iflow-cli-sdk？

A: 插件会自动安装 requirements.txt 中定义的依赖。如果需要手动安装：

```bash
pip install iflow-cli-sdk>=0.1.11
```

### Q: 会话恢复失败怎么办？

A: 会话恢复失败不会影响插件启动。失败的会话会在日志中记录，用户可以发送消息重新创建会话，或使用 `/iflow clear <id>` 清除失败的会话。

### Q: 如何查看所有活跃会话？

A: 使用指令 `/iflow sessions` 查看所有活跃会话及其工作目录。

### Q: 同一会话的并发消息会如何处理？

A: 使用会话锁确保同一会话的并发消息按顺序处理，避免冲突。

## 扩展方向

### 可能的改进

1. **自动重连机制**
   - 实现连接断开后的自动重连
   - 指数退避重连策略
   - 检测会话健康状态

2. **会话生命周期管理**
   - 添加会话空闲超时自动关闭
   - 添加会话最大消息数限制
   - 添加会话统计信息（消息数、活跃时长等）

3. **消息过滤**
   - 支持按群组/用户过滤
   - 支持关键词过滤
   - 支持正则表达式过滤

4. **日志记录**
   - 记录转发历史
   - 提供查询指令
   - 支持日志导出

5. **性能优化**
   - 消息队列处理
   - 批量转发支持
   - 客户端连接池管理
   - 会话缓存优化

6. **SDK 功能扩展**
   - 启用文件访问功能
   - 支持工具调用
   - 支持更复杂的消息类型（图片、文件等）

7. **健康检查**
   - 定期检查 iFlow ACP 服务状态
   - 提供健康状态报告
   - 自动重启失败的会话

8. **配置增强**
   - 支持配置文件
   - 支持多服务器配置
   - 支持热重载配置

9. **用户界面**
   - 提供会话管理 Web 界面
   - 支持查看会话详情
   - 支持导出会话数据

10. **监控和告警**
    - 添加 Prometheus 指标
    - 添加告警通知
    - 支持监控面板集成

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
4. 更新 `CHANGELOG.md` 添加变更记录
5. 更新 `README.md` 中的变更日志（如有需要）
6. 更新 `AGENTS.md` 文档版本和相关内容
7. 测试所有功能（包括会话管理和持久化）
8. 提交 Git commit
9. 推送到远程仓库

### Bug 修复流程

1. 在 issue 中描述问题
2. 定位问题代码
3. 编写测试用例
4. 修复代码
5. 验证修复
6. 更新文档（如有必要）
7. 提交 commit

### 版本兼容性

- **v1.x.x**: 初始版本，单客户端架构
- **v2.x.x**: 使用 iFlow CLI SDK，单客户端架构
- **v4.0.0+**: 会话池架构，支持独立会话和持久化

从 v2.x.x 升级到 v4.0.0 会破坏现有会话（历史会话丢失），首次运行时会重新创建所有会话。

---

**文档版本**: 4.0.0

**文档生成时间**: 2026-02-01

**最后更新**: 2026-02-04

**插件版本**: v4.0.0

**SDK 版本**: iflow-cli-sdk >= 0.1.11

**协议版本**: ACP v1

**架构模式**: 会话池 + 持久化