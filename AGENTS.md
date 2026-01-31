# AstrBot iFlow 插件 - 项目上下文文档

本文档为 iFlow AI Agent 提供项目上下文信息，用于理解和维护 AstrBot iFlow 插件。

## 项目概述

**项目名称**: AstrBot iFlow 插件 (astrbot_plugin_iflow)

**项目类型**: Python 插件项目

**主要目的**: 为 AstrBot 提供与 iFlow CLI (心流 CLI) 的集成功能，实现消息自动转发和处理结果回复。

**当前版本**: v1.0.0

**许可证**: GNU Affero General Public License v3.0 (AGPL-3.0)

**作者**: tongrenlu114514

**仓库地址**: https://github.com/tongrenlu114514/astrbot_plugin_iflow

## 技术栈

- **语言**: Python 3.x
- **框架**: AstrBot Plugin SDK (astrbot.api)
- **依赖工具**:
  - AstrBot >= v4.0.0
  - iFlow CLI (需要在系统 PATH 中可用)
- **核心库**:
  - `asyncio` - 异步进程管理和超时控制
  - `astrbot.api.event` - 事件监听和消息处理
  - `astrbot.api.star` - 插件基类和注册机制

## 项目结构

```
astrbot_plugin_iflow/
├── main.py           # 主插件文件（核心实现）
├── metadata.yaml     # 插件元数据配置
├── README.md         # 用户文档
├── AGENTS.md         # 本文档（AI Agent 上下文）
├── LICENSE           # AGPL-3.0 许可证
└── .gitignore        # Git 忽略配置
```

## 核心架构

### 插件类: `IFlowPlugin`

继承自 `astrbot.api.star.Star`，是插件的核心类。

#### 主要属性

- `iflow_available: bool` - 标记 iFlow CLI 是否可用
- `iflow_enabled: bool` - 控制消息转发是否启用
- `timeout: int` - iFlow CLI 处理超时时间（默认30秒）

#### 生命周期方法

1. **`__init__(self, context: Context)`**
   - 初始化插件实例
   - 设置默认属性值

2. **`async initialize(self)`**
   - 插件加载时自动调用
   - 检测 iFlow CLI 是否可用（执行 `iflow --version`）
   - 记录检测结果到日志

3. **`async terminate(self)`**
   - 插件卸载/停用时调用
   - 清理资源并记录日志

#### 核心功能方法

1. **`@filter.event_message_type(filter.EventMessageType.ALL, priority=1)`**
   - 监听所有消息事件（群聊和私聊）
   - 优先级设为 1，确保先于其他插件执行
   - 处理流程：
     - 检查 iFlow 可用性和启用状态
     - 提取消息内容（跳过空消息）
     - 异步调用 iFlow CLI 处理消息
     - 捕获处理结果并回复用户
     - 处理超时和异常情况

2. **`@filter.command("iflow")`**
   - 控制指令处理器
   - 支持操作：
     - 无参数：显示当前状态
     - `on`: 启用消息转发
     - `off`: 禁用消息转发
     - `status`: 显示详细状态

## 工作流程

### 消息处理流程

```
用户发送消息
    ↓
AstrBot 接收消息
    ↓
触发 on_message 监听器（priority=1）
    ↓
检查 iFlow 可用性和启用状态
    ↓
提取消息内容
    ↓
异步调用: iflow <消息内容>
    ↓
等待处理结果（30秒超时）
    ↓
捕获 stdout/stderr
    ↓
回复用户处理结果
```

### 插件初始化流程

```
AstrBot 加载插件
    ↓
实例化 IFlowPlugin
    ↓
调用 initialize()
    ↓
执行: iflow --version
    ↓
设置 iflow_available 状态
    ↓
记录检测结果
```

## 配置文件

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

## 关键设计决策

### 1. 异步进程调用

使用 `asyncio.create_subprocess_exec` 而非同步调用，避免阻塞 AstrBot 事件循环。

### 2. 优先级设置

消息监听器优先级设为 `priority=1`，确保在 LLM 处理之前拦截消息。

### 3. 超时保护

30秒超时机制防止 iFlow CLI 长时间无响应导致阻塞。

### 4. 错误处理

- 捕获所有异常并记录日志
- 超时错误单独处理并回复用户
- iFlow 不可用时静默返回，不干扰正常功能

### 5. 开关控制

提供运行时控制指令，允许用户动态启用/禁用消息转发。

## 开发约定

### 代码风格

- 使用 Python 异步编程模式（async/await）
- 所有插件方法必须使用装饰器注册
- 日志使用 `astrbot.api.logger`
- 文档字符串使用中文

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

1. **iFlow CLI 检测**
   - 测试 iFlow CLI 可用时的初始化
   - 测试 iFlow CLI 不可用时的降级处理

2. **消息转发**
   - 测试普通文本消息转发
   - 测试空消息跳过
   - 测试超时场景
   - 测试异常场景

3. **控制指令**
   - 测试 `/iflow` 状态查询
   - 测试 `/iflow on` 启用功能
   - 测试 `/iflow off` 禁用功能
   - 测试 `/iflow status` 详细状态

### 边界测试

- iFlow CLI 返回空输出
- iFlow CLI 返回大量输出
- iFlow CLI 返回错误信息
- 并发消息处理

## 常见问题

### Q: 插件启动后显示 "iFlow CLI 不可用"？

A: 确保 iFlow CLI 已安装并在系统 PATH 中可用。可以尝试在终端执行 `iflow --version` 验证。

### Q: 消息没有转发到 iFlow？

A: 检查以下事项：
1. 使用 `/iflow` 查看插件状态
2. 确认消息转发已启用（`/iflow on`）
3. 检查 AstrBot 日志中的错误信息

### Q: 如何调整超时时间？

A: 修改 `main.py` 中的 `self.timeout = 30` 值（单位：秒）

### Q: 支持哪些消息类型？

A: 支持所有文本消息（群聊和私聊），空消息和纯表情消息会被跳过。

## 扩展方向

### 可能的改进

1. **配置文件支持**
   - 添加配置文件支持超时时间、默认状态等

2. **消息过滤**
   - 支持按群组/用户过滤
   - 支持关键词过滤

3. **日志记录**
   - 记录转发历史
   - 提供查询指令

4. **性能优化**
   - 消息队列处理
   - 批量转发支持

## 相关资源

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [iFlow CLI 文档](https://github.com/iFlow-CLI/iflow)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)

## 维护说明

### 发布新版本流程

1. 更新 `metadata.yaml` 中的版本号
2. 更新 `main.py` 中的版本号
3. 更新 `README.md` 中的变更日志
4. 测试所有功能
5. 提交 Git commit
6. 推送到远程仓库

### Bug 修复流程

1. 在 issue 中描述问题
2. 定位问题代码
3. 编写测试用例
4. 修复代码
5. 验证修复
6. 提交 commit

---

**文档版本**: 1.0.0

**文档生成时间**: 2026-01-31

**最后更新**: 2026-01-31

**插件版本**: v1.0.0