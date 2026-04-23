# 更新日志 (CHANGELOG)

本文档记录 AstrBot iFlow 插件的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 修复
- 🐛 去除智能体回复中 `<think>` 标签内容后再转发，保留历史记录完整上下文

## [4.1.0] - 2026-03-14

### 新增
- ✨ 添加提示词优化功能，自动优化用户输入的提示词
- ✨ 使用启发式规则判断场景，避免额外的 LLM 调用延迟
- ✨ 支持检测简单闲聊（打招呼、感谢、告别等）并跳过优化
- ✨ 优化时包含对话历史上下文，提供更好的优化效果
- ✨ 新增配置项：
  - `enable_optimize` - 是否启用提示词优化（默认关闭）
  - `skip_short_message` - 跳过短消息优化阈值（默认 10 字符）
  - `optimize_context_count` - 优化时包含的历史消息数（默认 5 条）

### 修复
- 🐛 使用临时连接执行提示词优化，避免污染主会话上下文

## [4.0.0] - 2026-02-01

### 新增
- ✨ 实现独立会话管理，每个群组和私聊拥有独立的 iFlow 会话
- ✨ 添加会话持久化功能，插件重启后自动恢复所有历史会话
- ✨ 新增会话管理指令：
  - `/iflow sessions` - 查看所有活跃会话
  - `/iflow clear all` - 清除所有会话
  - `/iflow clear current` - 清除当前会话
  - `/iflow clear <id>` - 清除指定群组/用户会话
- ✨ 会话元数据使用 JSON 文件持久化存储
- ✨ 插件启动时并发恢复所有历史会话
- ✨ 自动更新会话最后访问时间
- ✨ 每个会话使用独立的工作目录进行隔离

### 变更
- ♻️ 从单客户端架构重构为会话池架构
- ♻️ 移除 `async with` 上下文管理器，使用长连接保持会话
- ♻️ 重构消息处理流程，基于会话ID路由到对应会话

### 优化
- ⚡ 使用原子操作保存会话元数据文件，确保数据安全
- ⚡ 使用 `asyncio.gather` 并发恢复多个会话，提高启动速度
- ⚡ 会话恢复失败不影响插件启动，提高系统健壮性

### 文档
- 📝 更新 AGENTS.md 文档，记录会话管理和持久化架构
- 📝 更新插件版本号为 v4.0.0

### 破坏性变更
- ⚠️ 会话架构从单客户端迁移到会话池，首次运行时之前的历史会话将丢失
- ⚠️ 会话现在会在插件重启后持久化，不再每次都重新创建

---

## [2.0.0] - 2026-01-31

### 新增
- ✨ 使用 iflow-cli-sdk 替代直接实现 WebSocket 通信
- ✨ 添加工作目录配置，支持文件访问控制
- ✨ 添加超时保护机制（默认30秒）

### 变更
- ♻️ 重构架构，从直接使用 websockets 改为使用官方 SDK
- ♻️ 更新依赖：`websockets >= 12.0` → `iflow-cli-sdk >= 0.1.11`
- ♻️ 使用上下文管理器管理 SDK 生命周期

### 文档
- 📝 更新 AGENTS.md 文档，记录 SDK 架构

---

## [1.0.0] - 2026-01-31

### 新增
- ✨ 初始版本发布
- ✨ 实现基本的 ACP 协议消息转发功能
- ✨ 支持群聊和私聊消息
- ✨ 提供基本控制指令：`/iflow [on|off|status]`
- ✨ 支持容器化部署场景

---

[Unreleased]: https://github.com/tongrenlu114514/astrbot_plugin_iflow/compare/v4.1.0...HEAD
[4.1.0]: https://github.com/tongrenlu114514/astrbot_plugin_iflow/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/tongrenlu114514/astrbot_plugin_iflow/compare/v2.0.0...v4.0.0
[2.0.0]: https://github.com/tongrenlu114514/astrbot_plugin_iflow/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/tongrenlu114514/astrbot_plugin_iflow/releases/tag/v1.0.0