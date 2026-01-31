import asyncio
import os
from typing import Optional

from iflow_sdk import IFlowClient, IFlowOptions, AssistantMessage, TaskFinishMessage
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register(
    "astrbot_plugin_iflow",
    "tongrenlu114514",
    "AstrBot iflow 插件 - 通过 iFlow CLI SDK 转发消息到 iFlow",
    "v2.0.0",
    "https://github.com/tongrenlu114514/astrbot_plugin_iflow",
)
class IFlowPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.iflow_enabled = True
        self.timeout = 30  # 默认超时30秒
        self.acp_url = os.getenv("IFLOW_ACP_URL", "ws://host.docker.internal:8090/acp")
        self.client: Optional[IFlowClient] = None

    async def initialize(self):
        """插件初始化方法，创建 iFlow SDK 客户端"""
        try:
            # 配置 iFlow SDK 选项
            options = IFlowOptions(
                url=self.acp_url,
                auto_start_process=False,  # 假设 iFlow 已独立运行
                timeout=self.timeout,
            )
            self.client = IFlowClient(options)
            logger.info(f"iFlow SDK 客户端已初始化，连接地址: {self.acp_url}")
        except Exception as e:
            logger.error(f"初始化 iFlow SDK 客户端失败: {e}")

    @filter.event_message_type(filter.EventMessageType.ALL, priority=1)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，转发到 iFlow 并回复结果"""
        if not self.client or not self.iflow_enabled:
            return

        message_str = event.message_str
        if not message_str or not message_str.strip():
            return

        try:
            # 使用 iFlow SDK 发送消息
            async with self.client:
                await self.client.send_message(message_str)

                # 收集响应
                response_parts = []
                async for message in self.client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        response_parts.append(message.chunk.text)
                    elif isinstance(message, TaskFinishMessage):
                        break

                result = "".join(response_parts)
                if result:
                    yield event.plain_result(result)

        except asyncio.TimeoutError:
            logger.error(f"iFlow 处理超时（{self.timeout}秒）")
            yield event.plain_result("iFlow 处理超时，请稍后重试")
        except Exception as e:
            logger.error(f"调用 iFlow SDK 失败: {e}")

    @filter.command("iflow")
    async def iflow_cmd(self, event: AstrMessageEvent, action: str = None):
        """iFlow 插件控制指令

        Args:
            action(string): 操作类型 (on/off/status)
        """
        if not action:
            status = "启用" if self.iflow_enabled else "禁用"
            url_info = f"\nACP 地址: {self.acp_url}" if self.client else ""
            yield event.plain_result(
                f"iFlow 消息转发: {status}{url_info}"
            )
        elif action == "on":
            self.iflow_enabled = True
            yield event.plain_result("iFlow 消息转发已启用")
        elif action == "off":
            self.iflow_enabled = False
            yield event.plain_result("iFlow 消息转发已禁用")
        elif action == "status":
            status = "启用" if self.iflow_enabled else "禁用"
            url_info = f"\nACP 地址: {self.acp_url}" if self.client else ""
            yield event.plain_result(
                f"iFlow 消息转发: {status}{url_info}"
            )
        else:
            yield event.plain_result("用法: /iflow [on|off|status]")

    async def terminate(self):
        """插件销毁方法，清理资源"""
        if self.client:
            await self.client.close()
        logger.info("iFlow 插件已卸载")