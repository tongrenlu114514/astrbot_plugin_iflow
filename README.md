# AstrBot iFlow 插件

AstrBot iFlow 插件 - 自动转发消息到 iFlow CLI (心流 CLI) 并回复处理结果

AstrBot plugin that automatically forwards messages to iFlow CLI and replies with the results.

## 功能特性

- 📥 **自动消息转发**: 监听所有消息，自动转发到 iFlow CLI 处理
- ⚡ **实时回复**: 将 iFlow CLI 的处理结果实时回复给用户
- 🔧 **可用性检测**: 插件启动时自动检测 iFlow CLI 是否可用
- 🎛️ **开关控制**: 支持通过指令启用/禁用消息转发功能
- ⏱️ **超时保护**: 30秒超时机制，防止长时间等待
- 🛡️ **错误处理**: 完善的异常捕获和日志记录

## 安装

1. 将插件目录放置到 AstrBot 的 `data/plugins` 目录下
2. 确保 iFlow CLI 已安装并在系统 PATH 中可用
3. 在 AstrBot WebUI 中启用插件

## 使用方法

### 自动转发

插件启用后，所有非空消息都会自动转发到 iFlow CLI 处理，处理结果会自动回复。

### 控制指令

- `/iflow` - 查看当前状态
- `/iflow on` - 启用消息转发
- `/iflow off` - 禁用消息转发
- `/iflow status` - 查看详细状态

## 依赖

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) >= v4.0.0
- [iFlow CLI](https://github.com/iFlow-CLI/iflow) - 需要在系统 PATH 中可用

## 配置

插件会在启动时自动检测 iFlow CLI 是否可用。如果检测失败，插件会记录警告日志但仍会加载。

## 开发

### 插件结构

```
astrbot_plugin_iflow/
├── main.py           # 主插件文件
├── metadata.yaml     # 插件元数据
├── README.md         # 说明文档
└── LICENSE           # 许可证
```

### 主要功能

- `initialize()` - 检测 iFlow CLI 可用性
- `on_message()` - 监听所有消息并转发
- `iflow_cmd()` - 控制指令处理
- `terminate()` - 清理资源

## 许可证

GNU Affero General Public License v3.0

## 支持

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [iFlow CLI 文档](https://github.com/iFlow-CLI/iflow)

## 作者

tongrenlu114514
