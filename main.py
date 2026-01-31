import asyncio
import json
import os
from typing import Optional

import websockets
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


class ACPClient:
    """ACP (Agent Communication Protocol) WebSocket 客户端"""

    def __init__(self, url: str):
        self.url = url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False

    async def connect(self) -> bool:
        """连接到 iFlow ACP 服务"""
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.url), timeout=5
            )
            self.connected = True
            logger.info(f"已连接到 iFlow ACP 服务: {self.url}")
            return True
        except Exception as e:
            logger.error(f"连接 iFlow ACP 服务失败: {e}")
            self.connected = False
            return False

    async def send_message(self, content: str, timeout: int = 30) -> str:
        """发送消息到 iFlow 并获取响应"""
        if not self.connected or not self.websocket:
            raise RuntimeError("未连接到 iFlow ACP 服务")

        # 发送用户消息
        message = {"type": "user_message", "content": content}
        await self.websocket.send(json.dumps(message))

        # 接收响应
        response_parts = []
        task_start = asyncio.get_event_loop().time()

        while True:
            try:
                # 检查超时
                elapsed = asyncio.get_event_loop().time() - task_start
                remaining = timeout - elapsed
                if remaining <= 0:
                    raise asyncio.TimeoutError()

                # 接收消息
                response = await asyncio.wait_for(
                    self.websocket.recv(), timeout=remaining
                )
                data = json.loads(response)

                # 处理不同类型的消息
                if data.get("type") == "agent_message_chunk":
                    # AI 响应片段
                    chunk = data.get("chunk", {})
                    text = chunk.get("text", "")
                    response_parts.append(text)
                elif data.get("type") == "task_finish":
                    # 任务完成
                    break
                elif data.get("type") == "error":
                    # 错误消息
                    raise RuntimeError(data.get("message", "未知错误"))

            except asyncio.TimeoutError:
                logger.error(f"iFlow ACP 响应超时（{timeout}秒）")
                raise
            except Exception as e:
                logger.error(f"接收 iFlow ACP 响应失败: {e}")
                raise

        return "".join(response_parts)

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("iFlow ACP 连接已关闭")


@register(
    "astrbot_plugin_iflow",
    "tongrenlu114514",
    "AstrBot iflow 插件 - 通过 ACP 协议转发消息到 iFlow",
    "v1.0.0",
    "https://github.com/tongrenlu114514/astrbot_plugin_iflow",
)
class IFlowPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.iflow_available = False
        self.iflow_enabled = True
        self.timeout = 30  # 默认超时30秒
        self.acp_url = os.getenv("IFLOW_ACP_URL", "ws://host.docker.internal:8090/acp")
        self.acp_client: Optional[ACPClient] = None

    async def initialize(self):
        """插件初始化方法，连接到 iFlow ACP 服务"""
        try:
            self.acp_client = ACPClient(self.acp_url)
            self.iflow_available = await self.acp_client.connect()
            if self.iflow_available:
                logger.info("iFlow ACP 服务连接成功")
            else:
                logger.warning("iFlow ACP 服务连接失败，请确保 iFlow 以守护进程运行")
        except Exception as e:
            logger.error(f"初始化 iFlow ACP 客户端失败: {e}")
            self.iflow_available = False

    @filter.event_message_type(filter.EventMessageType.ALL, priority=1)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，转发到 iFlow 并回复结果"""
        if not self.iflow_available or not self.iflow_enabled:
            return

        message_str = event.message_str
        if not message_str or not message_str.strip():
            return

        try:
            # 通过 ACP 协议发送消息
            result = await self.acp_client.send_message(message_str, self.timeout)
            if result:
                yield event.plain_result(result)
        except asyncio.TimeoutError:
            logger.error(f"iFlow ACP 处理超时（{self.timeout}秒）")
            yield event.plain_result("iFlow 处理超时，请稍后重试")
        except Exception as e:
            logger.error(f"调用 iFlow ACP 失败: {e}")

    @filter.command("iflow")
    async def iflow_cmd(self, event: AstrMessageEvent, action: str = None):
        """iFlow 插件控制指令

        Args:
            action(string): 操作类型 (on/off/status)
        """
        if not action:
            status = "启用" if self.iflow_enabled else "禁用"
            available = "可用" if self.iflow_available else "不可用"
            url_info = f"\nACP 地址: {self.acp_url}" if self.iflow_available else ""
            yield event.plain_result(
                f"iFlow 状态: {available}\n消息转发: {status}{url_info}"
            )
        elif action == "on":
            self.iflow_enabled = True
            yield event.plain_result("iFlow 消息转发已启用")
        elif action == "off":
            self.iflow_enabled = False
            yield event.plain_result("iFlow 消息转发已禁用")
        elif action == "status":
            status = "启用" if self.iflow_enabled else "禁用"
            available = "可用" if self.iflow_available else "不可用"
            url_info = f"\nACP 地址: {self.acp_url}" if self.iflow_available else ""
            yield event.plain_result(
                f"iFlow 状态: {available}\n消息转发: {status}{url_info}"
            )
        else:
            yield event.plain_result("用法: /iflow [on|off|status]")

    async def terminate(self):
        """插件销毁方法，清理资源"""
        if self.acp_client:
            await self.acp_client.close()
        logger.info("iFlow 插件已卸载")
