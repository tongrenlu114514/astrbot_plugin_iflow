import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional, Dict

from iflow_sdk import IFlowClient, IFlowOptions, AssistantMessage, TaskFinishMessage
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path


@register(
    "astrbot_plugin_iflow",
    "tongrenlu114514",
    "AstrBot iflow 插件 - 通过 iFlow CLI SDK 转发消息到 iFlow，支持群组独立会话和会话持久化",
    "v4.0.0",
    "https://github.com/tongrenlu114514/astrbot_plugin_iflow",
)
class IFlowPlugin(Star):
    # 简单闲聊模式（不需要优化）
    SIMPLE_CHITCHAT_PATTERNS = [
        r'^(你|您)?好[啊呀]?$',           # 你好、好啊
        r'^hi+$',                         # hi, hiii
        r'^hello$',                       # hello
        r'^(早上|晚上|下午)?好[啊呀]?$',   # 早上好
        r'^[嗨哈喽]+$',                   # 嗨、哈喽
        r'^(谢谢|感谢|thanks?)[你您]?$',  # 谢谢
        r'^(再见|拜拜|bye)+$',            # 再见、拜拜
        r'^[嗯哦额]+$',                   # 嗯、哦
        r'^好[的啊呀]?$',                 # 好的
        r'^ok$',                          # ok
    ]
    
    # 需要优化的关键词模式
    OPTIMIZE_KEYWORDS = [
        '写', '帮', '代码', '脚本', '函数', '实现', '修复', '优化',
        '分析', '总结', '翻译', '解释', '比较', '生成', '创作'
    ]
    
    # 提示词优化模板
    OPTIMIZE_PROMPT_TEMPLATE = """请优化以下用户提示词，使其更加清晰、具体、有效。
{context_section}
优化原则：
1. 明确任务目标和预期输出格式
2. 添加必要的上下文和约束条件
3. 使用结构化格式提高可读性
4. 保持用户原始意图不变

原始提示词：
{original_prompt}

请直接输出优化后的提示词，不要解释：
"""

    # 历史上下文模板
    CONTEXT_TEMPLATE = """以下是之前的对话历史，供优化参考：

{history}

"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        # 从配置文件读取设置
        self.config = config
        self.iflow_enabled = config.get("enabled", True)
        self.timeout = config.get("timeout", 30)
        self.acp_url = config.get("acp_url", "ws://host.docker.internal:8090/acp")
        
        # 提示词优化配置
        self.enable_optimize = config.get("enable_optimize", False)
        self.skip_short_message = config.get("skip_short_message", 10)
        self.optimize_context_count = config.get("optimize_context_count", 5)  # 优化时包含的历史消息数
        
        # 会话池相关属性
        self.sessions: Dict[str, IFlowClient] = {}  # 会话池: session_id -> client
        self.session_locks: Dict[str, asyncio.Lock] = {}  # 每个会话的异步锁
        self.global_lock = asyncio.Lock()  # 保护共享资源的全局锁
        self.session_histories: Dict[str, list] = {}  # 会话消息历史缓存: session_id -> [(role, message), ...]
        self.base_data_dir = ""  # 基础数据目录
        self.sessions_dir = ""  # 会话目录

    async def initialize(self):
        """插件初始化方法，创建会话目录结构并恢复历史会话"""
        try:
            # 获取基础数据目录
            self.base_data_dir = os.path.join(get_astrbot_data_path(), "plugin_data", self.name)
            os.makedirs(self.base_data_dir, exist_ok=True)
            
            # 创建会话目录
            self.sessions_dir = os.path.join(self.base_data_dir, "sessions")
            os.makedirs(self.sessions_dir, exist_ok=True)
            
            logger.info(f"iFlow 插件已初始化，会话目录: {self.sessions_dir}")
            
            # 恢复历史会话
            await self._restore_sessions()
            
        except Exception as e:
            logger.error(f"初始化 iFlow 插件失败: {e}")
    
    async def get_session_id(self, event: AstrMessageEvent) -> str:
        """从消息事件中提取会话ID
        
        群聊消息使用群组ID，私聊消息使用用户ID
        """
        # 调试：打印事件对象的所有属性
        event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
        logger.debug(f"事件对象属性: {event_attrs}")
        
        # 尝试多种可能的属性名来获取群组ID
        group_id = None
        for attr in ['group_id', 'group', 'groupId', 'groupInfo']:
            if hasattr(event, attr):
                group_id = getattr(event, attr)
                if group_id:
                    logger.info(f"检测到群组ID ({attr}): {group_id}")
                    return f"group_{group_id}"
        
        # 尝试多种可能的属性名来获取用户ID
        user_id = None
        for attr in ['user_id', 'user', 'userId', 'sender_id', 'sender', 'senderId']:
            if hasattr(event, attr):
                user_id = getattr(event, attr)
                if user_id:
                    logger.info(f"检测到用户ID ({attr}): {user_id}")
                    return f"private_{user_id}"
        
        # 尝试从 session 或 channel_id 获取
        for attr in ['session', 'channel_id', 'channelId', 'chat_id', 'chatId']:
            if hasattr(event, attr):
                chat_id = getattr(event, attr)
                if chat_id:
                    logger.info(f"检测到会话ID ({attr}): {chat_id}")
                    return f"chat_{chat_id}"
        
        # 兜底方案：使用消息内容的哈希作为会话ID（不太理想，但比 unknown 更好）
        import hashlib
        content_hash = hashlib.md5(event.message_str.encode()).hexdigest()[:8]
        logger.warning(f"无法获取会话ID，使用消息内容哈希: {content_hash}")
        return f"hash_{content_hash}"
    
    async def get_or_create_session(self, session_id: str) -> Optional[IFlowClient]:
        """获取或创建会话客户端
        
        如果会话不存在，则创建新的客户端并保持连接
        """
        # 检查是否已存在会话
        async with self.global_lock:
            if session_id in self.sessions:
                # 更新最后访问时间（异步执行，不阻塞）
                asyncio.create_task(self._update_session_access_time(session_id))
                return self.sessions[session_id]
        
        # 创建新会话
        try:
            # 解析会话信息
            session_type, target_id = self._parse_session_id(session_id)
            
            # 创建会话专用工作目录（本地）
            session_dir = os.path.join(self.sessions_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # 获取服务器上的插件数据目录路径
            server_base_dir = os.path.join(get_astrbot_data_path(), "plugin_data", self.name)
            server_session_dir = os.path.join(server_base_dir, "sessions", session_id)
            
            # 在服务器上创建对应的工作目录
            try:
                import subprocess
                subprocess.run(
                    ["ssh", "iflowuser@121.37.183.44", f"mkdir -p {server_session_dir}"],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                logger.info(f"服务器目录创建成功: {server_session_dir}")
            except Exception as e:
                logger.warning(f"服务器目录创建失败: {e}，继续使用默认目录")
            
            # 配置 iFlow SDK 选项（使用服务器路径作为 cwd）
            options = IFlowOptions(
                url=self.acp_url,
                auto_start_process=False,
                timeout=self.timeout,
                cwd=server_session_dir,  # 使用服务器上的路径
                file_access=False,
            )
            
            # 创建客户端
            client = IFlowClient(options)
            
            # 初始化连接（不使用 async with，保持长连接）
            await client.connect()
            
            # 保存会话
            async with self.global_lock:
                self.sessions[session_id] = client
                self.session_locks[session_id] = asyncio.Lock()
            
            # 添加会话元数据
            await self._add_session_metadata(
                session_id=session_id,
                session_type=session_type,
                target_id=target_id,
                workspace_dir=session_dir
            )
            
            logger.info(f"创建新会话: {session_id}，工作目录: {session_dir}")
            return client
            
        except Exception as e:
            logger.error(f"创建会话 {session_id} 失败: {e}")
            return None
    
    async def close_session(self, session_id: str):
        """关闭指定会话并清理资源"""
        async with self.global_lock:
            if session_id not in self.sessions:
                return
            
            try:
                # 关闭客户端连接
                client = self.sessions[session_id]
                await client.close()
                
                # 从会话池中移除
                del self.sessions[session_id]
                
                # 移除会话锁
                if session_id in self.session_locks:
                    del self.session_locks[session_id]
                
                # 移除消息历史
                if session_id in self.session_histories:
                    del self.session_histories[session_id]
                
                # 移除会话元数据
                await self._remove_session_metadata(session_id)
                
                logger.info(f"会话 {session_id} 已关闭")
                
            except Exception as e:
                logger.error(f"关闭会话 {session_id} 失败: {e}")
    
    async def close_all_sessions(self):
        """关闭所有会话并清理资源"""
        async with self.global_lock:
            session_ids = list(self.sessions.keys())
            
            for session_id in session_ids:
                try:
                    client = self.sessions[session_id]
                    await client.close()
                    logger.info(f"会话 {session_id} 已关闭")
                except Exception as e:
                    logger.error(f"关闭会话 {session_id} 失败: {e}")
            
            # 清空会话池
            self.sessions.clear()
            self.session_locks.clear()
            self.session_histories.clear()
            
            # 清空元数据
            await self._save_sessions_metadata({
                "version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "sessions": []
            })
            
            logger.info(f"已关闭所有会话，共 {len(session_ids)} 个")
    
    def _get_sessions_metadata_file(self) -> str:
        """获取会话元数据文件路径"""
        return os.path.join(self.base_data_dir, "sessions.json")
    
    async def _load_sessions_metadata(self) -> Dict:
        """加载会话元数据文件
        
        Returns:
            元数据字典，文件不存在时返回空结构
        """
        metadata_file = self._get_sessions_metadata_file()
        
        if not os.path.exists(metadata_file):
            return {
                "version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "sessions": []
            }
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载会话元数据失败: {e}")
            return {
                "version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "sessions": []
            }
    
    async def _save_sessions_metadata(self, metadata: Dict):
        """保存会话元数据文件（原子操作）
        
        Args:
            metadata: 要保存的元数据字典
        """
        metadata_file = self._get_sessions_metadata_file()
        temp_file = metadata_file + ".tmp"
        
        try:
            # 更新时间戳
            metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 原子重命名
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            os.rename(temp_file, metadata_file)
            
        except Exception as e:
            logger.error(f"保存会话元数据失败: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _parse_session_id(self, session_id: str) -> tuple:
        """解析会话ID，返回会话类型和目标ID
        
        Returns:
            (session_type, target_id) 如 ("group", "123456") 或 ("private", "789012")
        """
        if session_id.startswith("group_"):
            return "group", session_id[6:]
        elif session_id.startswith("private_"):
            return "private", session_id[8:]
        else:
            return "unknown", session_id
    
    async def _add_session_metadata(self, session_id: str, session_type: str, 
                                     target_id: str, workspace_dir: str):
        """添加会话元数据
        
        Args:
            session_id: 会话ID
            session_type: 会话类型
            target_id: 目标ID
            workspace_dir: 工作目录路径
        """
        async with self.global_lock:
            metadata = await self._load_sessions_metadata()
            
            # 检查是否已存在
            for session in metadata["sessions"]:
                if session["session_id"] == session_id:
                    return  # 已存在，不重复添加
            
            # 添加新会话元数据
            now = datetime.now(timezone.utc).isoformat()
            new_session = {
                "session_id": session_id,
                "session_type": session_type,
                "target_id": target_id,
                "created_at": now,
                "last_accessed_at": now,
                "message_count": 0,
                "workspace_dir": workspace_dir
            }
            
            metadata["sessions"].append(new_session)
            await self._save_sessions_metadata(metadata)
    
    async def _update_session_access_time(self, session_id: str):
        """更新会话的最后访问时间
        
        Args:
            session_id: 会话ID
        """
        async with self.global_lock:
            metadata = await self._load_sessions_metadata()
            
            for session in metadata["sessions"]:
                if session["session_id"] == session_id:
                    session["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
                    await self._save_sessions_metadata(metadata)
                    break
    
    async def _remove_session_metadata(self, session_id: str):
        """移除会话元数据
        
        Args:
            session_id: 会话ID
        """
        async with self.global_lock:
            metadata = await self._load_sessions_metadata()
            
            # 过滤掉指定会话
            metadata["sessions"] = [
                s for s in metadata["sessions"] 
                if s["session_id"] != session_id
            ]
            
            await self._save_sessions_metadata(metadata)
    
    async def _restore_sessions(self):
        """恢复历史会话
        
        读取元数据文件，自动重新连接 iFlow 服务恢复会话
        """
        metadata = await self._load_sessions_metadata()
        sessions_to_restore = metadata.get("sessions", [])
        
        if not sessions_to_restore:
            logger.info("未找到历史会话记录")
            return
        
        logger.info(f"开始恢复 {len(sessions_to_restore)} 个历史会话...")
        
        # 并发恢复会话
        restore_tasks = []
        for session_meta in sessions_to_restore:
            task = asyncio.create_task(
                self._restore_single_session(session_meta)
            )
            restore_tasks.append(task)
        
        # 等待所有恢复任务完成
        results = await asyncio.gather(*restore_tasks, return_exceptions=True)
        
        # 统计恢复结果
        success_count = sum(1 for r in results if r is True)
        failed_count = len(results) - success_count
        
        logger.info(f"会话恢复完成: 成功 {success_count} 个, 失败 {failed_count} 个")
        
        if failed_count > 0:
            logger.warning(f"部分会话恢复失败，请在日志中查看详细信息")
    
    async def _restore_single_session(self, session_meta: Dict) -> bool:
        """恢复单个会话
        
        Args:
            session_meta: 会话元数据
            
        Returns:
            bool: 恢复是否成功
        """
        session_id = session_meta["session_id"]
        
        try:
            # 获取服务器上的插件数据目录路径
            server_base_dir = os.path.join(get_astrbot_data_path(), "plugin_data", self.name)
            server_session_dir = os.path.join(server_base_dir, "sessions", session_id)
            
            # 在服务器上创建会话目录（如果不存在）
            try:
                import subprocess
                subprocess.run(
                    ["ssh", "iflowuser@121.37.183.44", f"mkdir -p {server_session_dir}"],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                logger.info(f"服务器目录已创建/验证: {server_session_dir}")
            except Exception as e:
                logger.warning(f"服务器目录验证失败: {e}")
            
            # 配置 iFlow SDK 选项（使用服务器路径）
            options = IFlowOptions(
                url=self.acp_url,
                auto_start_process=False,
                timeout=self.timeout,
                cwd=server_session_dir,  # 使用服务器上的路径
                file_access=False,
            )
            
            # 创建客户端
            client = IFlowClient(options)
            
            # 初始化连接
            await client.connect()
            
            # 保存会话
            async with self.global_lock:
                self.sessions[session_id] = client
                self.session_locks[session_id] = asyncio.Lock()
            
            logger.info(f"会话 {session_id} 恢复成功")
            return True
            
        except Exception as e:
            logger.error(f"恢复会话 {session_id} 失败: {e}")
            return False

    def _is_simple_chitchat(self, message: str) -> bool:
        """判断是否是简单闲聊
        
        Args:
            message: 用户消息
            
        Returns:
            bool: 是否是简单闲聊
        """
        msg = message.strip().lower()
        for pattern in self.SIMPLE_CHITCHAT_PATTERNS:
            if re.match(pattern, msg, re.IGNORECASE):
                return True
        return False

    def _should_optimize(self, message: str) -> bool:
        """判断是否需要优化提示词
        
        Args:
            message: 用户消息
            
        Returns:
            bool: 是否需要优化
        """
        msg = message.strip()
        
        # 跳过短消息
        if len(msg) < self.skip_short_message:
            return False
        
        # 简单闲聊不优化
        if self._is_simple_chitchat(msg):
            return False
        
        # 检查是否包含需要优化的关键词
        for keyword in self.OPTIMIZE_KEYWORDS:
            if keyword in msg:
                return True
        
        # 默认不优化
        return False

    def _get_context_for_optimize(self, session_id: str) -> str:
        """获取用于优化的历史上下文
        
        Args:
            session_id: 会话ID
            
        Returns:
            str: 格式化的历史上下文字符串，如果没有历史则返回空字符串
        """
        history = self.session_histories.get(session_id, [])
        if not history:
            return ""
        
        # 只取最近 N 条消息
        recent_history = history[-self.optimize_context_count:] if len(history) > self.optimize_context_count else history
        
        # 格式化历史
        history_lines = []
        for role, msg in recent_history:
            role_name = "用户" if role == "user" else "助手"
            # 截断过长的消息
            truncated_msg = msg[:200] + "..." if len(msg) > 200 else msg
            history_lines.append(f"[{role_name}] {truncated_msg}")
        
        return self.CONTEXT_TEMPLATE.format(history="\n".join(history_lines))

    async def _optimize_prompt(self, message: str, session_id: str = None) -> str:
        """优化提示词（使用临时连接，不影响主会话上下文）
        
        Args:
            message: 原始消息
            session_id: 会话ID，用于获取历史上下文
            
        Returns:
            str: 优化后的消息
        """
        # 获取历史上下文
        context_section = ""
        if session_id:
            context_section = self._get_context_for_optimize(session_id)
        
        optimize_prompt = self.OPTIMIZE_PROMPT_TEMPLATE.format(
            context_section=context_section,
            original_prompt=message
        )
        
        # 创建临时工作目录
        temp_dir = os.path.join(self.sessions_dir, "_optimize_temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 创建临时客户端连接
        temp_options = IFlowOptions(
            url=self.acp_url,
            auto_start_process=False,
            timeout=self.timeout,
            cwd=temp_dir,
            file_access=False,
        )
        
        temp_client = IFlowClient(temp_options)
        
        try:
            await temp_client.connect()
            await temp_client.send_message(optimize_prompt)
            
            response_parts = []
            async for msg in temp_client.receive_messages():
                if isinstance(msg, AssistantMessage):
                    response_parts.append(msg.chunk.text)
                elif isinstance(msg, TaskFinishMessage):
                    break
            
            optimized = "".join(response_parts).strip()
            return optimized if optimized else message
            
        except Exception as e:
            logger.error(f"提示词优化失败: {e}")
            return message  # 失败时返回原始消息
            
        finally:
            try:
                await temp_client.close()
            except Exception:
                pass

    @filter.event_message_type(filter.EventMessageType.ALL, priority=1)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，转发到对应的 iFlow 会话并回复结果"""
        if not self.iflow_enabled:
            return

        message_str = event.message_str
        if not message_str or not message_str.strip():
            return

        try:
            # 调试：打印事件类型和部分属性
            logger.info(f"收到消息: {message_str[:50]}...")
            logger.info(f"事件类型: {type(event).__name__}")
            
            # 获取会话ID
            session_id = await self.get_session_id(event)
            logger.info(f"会话ID: {session_id}")
            
            # 获取或创建会话
            client = await self.get_or_create_session(session_id)
            if not client:
                yield event.plain_result("iFlow 会话创建失败，请检查服务状态")
                return
            
            # 获取会话锁（防止同一会话的并发请求冲突）
            session_lock = self.session_locks.get(session_id)
            if not session_lock:
                yield event.plain_result("会话锁获取失败")
                return
            
            async with session_lock:
                # 处理后的消息
                processed_message = message_str
                
                # 提示词优化逻辑
                if self.enable_optimize and self._should_optimize(message_str):
                    logger.info(f"开始优化提示词: {message_str[:30]}...")
                    optimized = await self._optimize_prompt(message_str, session_id)
                    if optimized != message_str:
                        logger.info(f"提示词已优化")
                        processed_message = optimized
                    else:
                        logger.info(f"提示词未发生变化，使用原始消息")
                
                # 保存用户消息到历史
                if session_id not in self.session_histories:
                    self.session_histories[session_id] = []
                self.session_histories[session_id].append(("user", message_str))
                
                # 添加当前时间信息到系统提示词
                current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                system_prompt = f"[系统提示] 当前时间: {current_time}\n\n用户消息:\n{processed_message}"
                
                # 发送消息（附带时间信息）
                await client.send_message(system_prompt)
                
                # 收集响应
                response_parts = []
                async for message in client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        response_parts.append(message.chunk.text)
                    elif isinstance(message, TaskFinishMessage):
                        break
                
                result = "".join(response_parts)
                if result:
                    # 保存 AI 回复到历史（保留<think>标签内容）
                    self.session_histories[session_id].append(("assistant", result))

                    # 去除<think>标签内容后再转发回复
                    cleaned_result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
                    if cleaned_result.strip():
                    # 清理多余的连续换行
                    cleaned_result = re.sub(r'
{3,}', r'

', cleaned_result)
                        yield event.plain_result(cleaned_result)

        except asyncio.TimeoutError:
            logger.error(f"会话 {session_id} 处理超时（{self.timeout}秒）")
            yield event.plain_result("iFlow 处理超时，请稍后重试")
        except Exception as e:
            logger.error(f"调用 iFlow SDK 失败（会话: {session_id}）: {e}")
            yield event.plain_result(f"iFlow 处理失败: {str(e)}")

    @filter.command("iflow")
    async def iflow_cmd(self, event: AstrMessageEvent, action: str = None, target: str = None):
        """iFlow 插件控制指令
        
        用法:
        /iflow [on|off|status]           # 全局控制
        /iflow sessions                   # 查看所有会话
        /iflow clear [group_id|user_id]   # 清除指定会话
        /iflow clear all                  # 清除所有会话
        /iflow clear current              # 清除当前会话
        """
        
        if not action:
            # 显示基本状态
            status = "启用" if self.iflow_enabled else "禁用"
            url_info = f"\nACP 地址: {self.acp_url}"
            session_count = len(self.sessions)
            yield event.plain_result(
                f"iFlow 消息转发: {status}{url_info}\n"
                f"活跃会话数: {session_count}"
            )
            
        elif action == "on":
            self.iflow_enabled = True
            self.config["enabled"] = True
            self.config.save_config()
            yield event.plain_result("iFlow 消息转发已启用")
            
        elif action == "off":
            self.iflow_enabled = False
            self.config["enabled"] = False
            self.config.save_config()
            yield event.plain_result("iFlow 消息转发已禁用")
            
        elif action == "status":
            # 显示详细状态
            status = "启用" if self.iflow_enabled else "禁用"
            url_info = f"\nACP 地址: {self.acp_url}"
            
            session_list = []
            async with self.global_lock:
                for session_id in self.sessions.keys():
                    session_list.append(f"  - {session_id}")
            
            session_info = "\n".join(session_list) if session_list else "  (无活跃会话)"
            
            yield event.plain_result(
                f"iFlow 消息转发: {status}{url_info}\n"
                f"活跃会话数: {len(self.sessions)}\n"
                f"会话列表:\n{session_info}"
            )
            
        elif action == "sessions":
            # 查看所有会话
            async with self.global_lock:
                session_list = []
                for session_id, client in self.sessions.items():
                    session_dir = getattr(client, '_options', {}).get('cwd', 'unknown')
                    session_list.append(f"  - {session_id}: {session_dir}")
                
                if not session_list:
                    yield event.plain_result("当前无活跃会话")
                else:
                    yield event.plain_result(
                        f"活跃会话列表 ({len(self.sessions)} 个):\n" +
                        "\n".join(session_list)
                    )
        
        elif action == "clear":
            # 清除会话
            if not target:
                yield event.plain_result(
                    "用法: /iflow clear [group_id|user_id|all|current]\n"
                    "  group_id: 清除指定群组会话\n"
                    "  user_id: 清除指定私聊会话\n"
                    "  all: 清除所有会话\n"
                    "  current: 清除当前会话"
                )
                return
            
            if target == "all":
                # 清除所有会话
                await self.close_all_sessions()
                yield event.plain_result(f"已清除所有会话")
                
            elif target == "current":
                # 清除当前会话
                session_id = await self.get_session_id(event)
                await self.close_session(session_id)
                yield event.plain_result(f"已清除当前会话: {session_id}")
                
            else:
                # 清除指定会话（支持群组ID或用户ID）
                # 尝试匹配群组会话
                group_session_id = f"group_{target}"
                if group_session_id in self.sessions:
                    await self.close_session(group_session_id)
                    yield event.plain_result(f"已清除群组会话: {target}")
                    return
                
                # 尝试匹配私聊会话
                private_session_id = f"private_{target}"
                if private_session_id in self.sessions:
                    await self.close_session(private_session_id)
                    yield event.plain_result(f"已清除私聊会话: {target}")
                    return
                
                yield event.plain_result(f"未找到会话: {target}")
        
        else:
            yield event.plain_result(
                "用法: /iflow [on|off|status|sessions|clear [target]]\n"
                "  /iflow on              - 启用消息转发\n"
                "  /iflow off             - 禁用消息转发\n"
                "  /iflow status          - 查看详细状态\n"
                "  /iflow sessions        - 查看所有会话\n"
                "  /iflow clear all       - 清除所有会话\n"
                "  /iflow clear current   - 清除当前会话\n"
                "  /iflow clear <id>      - 清除指定会话"
            )

    async def terminate(self):
        """插件销毁方法，清理资源"""
        # 关闭所有会话
        await self.close_all_sessions()
        
        logger.info("iFlow 插件已卸载")