import asyncio
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("astrbot_plugin_iflow", "tongrenlu114514", "AstrBot iflow 插件 - 转发消息到 iFlow CLI", "v1.0.0", "https://github.com/tongrenlu114514/astrbot_plugin_iflow")
class IFlowPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.iflow_available = False
        self.iflow_enabled = True
        self.timeout = 30  # 默认超时30秒

    async def initialize(self):
        """插件初始化方法，检查 iFlow CLI 是否可用"""
        try:
            # 检查 iflow 命令是否可用
            proc = await asyncio.create_subprocess_exec(
                "iflow", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                self.iflow_available = True
                logger.info(f"iFlow CLI 检测成功: {stdout.decode().strip()}")
            else:
                logger.warning(f"iFlow CLI 检测失败: {stderr.decode().strip()}")
        except Exception as e:
            logger.warning(f"iFlow CLI 不可用: {e}")
            self.iflow_available = False

    @filter.event_message_type(filter.EventMessageType.ALL, priority=1)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，转发到 iFlow CLI 并回复结果"""
        if not self.iflow_available or not self.iflow_enabled:
            return

        message_str = event.message_str
        if not message_str or not message_str.strip():
            return

        try:
            # 调用 iFlow CLI 处理消息
            proc = await asyncio.create_subprocess_exec(
                "iflow", message_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            
            if stdout:
                result = stdout.decode().strip()
                if result:
                    yield event.plain_result(result)
            
            if stderr:
                error_msg = stderr.decode().strip()
                if error_msg:
                    logger.error(f"iFlow CLI 错误: {error_msg}")
                    
        except asyncio.TimeoutError:
            logger.error(f"iFlow CLI 处理超时（{self.timeout}秒）")
            yield event.plain_result("iFlow 处理超时，请稍后重试")
        except Exception as e:
            logger.error(f"调用 iFlow CLI 失败: {e}")

    @filter.command("iflow")
    async def iflow_cmd(self, event: AstrMessageEvent, action: str = None):
        """iFlow 插件控制指令
        
        Args:
            action(string): 操作类型 (on/off/status)
        """
        if not action:
            status = "启用" if self.iflow_enabled else "禁用"
            available = "可用" if self.iflow_available else "不可用"
            yield event.plain_result(f"iFlow 状态: {available}\n消息转发: {status}")
        elif action == "on":
            self.iflow_enabled = True
            yield event.plain_result("iFlow 消息转发已启用")
        elif action == "off":
            self.iflow_enabled = False
            yield event.plain_result("iFlow 消息转发已禁用")
        elif action == "status":
            status = "启用" if self.iflow_enabled else "禁用"
            available = "可用" if self.iflow_available else "不可用"
            yield event.plain_result(f"iFlow 状态: {available}\n消息转发: {status}")
        else:
            yield event.plain_result("用法: /iflow [on|off|status]")

    async def terminate(self):
        """插件销毁方法，清理资源"""
        logger.info("iFlow 插件已卸载")
