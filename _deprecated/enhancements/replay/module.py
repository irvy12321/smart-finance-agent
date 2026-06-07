"""
回放系统
支持事件记录、本地JSON存储、确定性回放
外挂模块，不影响现有系统
"""
import json
import time
import threading
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

from utils.logger import get_logger
from ..base import EnhancementModule, ModuleStatus
from ..feature_toggle import is_feature_enabled


class EventType(Enum):
    """事件类型"""
    PIPELINE_START = "pipeline_start"
    PIPELINE_END = "pipeline_end"
    STAGE_START = "stage_start"
    STAGE_END = "stage_end"
    TASK_START = "task_start"
    TASK_END = "task_end"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    EVENT_EMIT = "event_emit"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class ReplayEvent:
    """回放事件"""
    event_id: str
    event_type: EventType
    timestamp: float
    wall_time: str  # 人类可读时间
    trace_id: str
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    agent_name: Optional[str] = None
    task_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplayEvent":
        """从字典创建"""
        data["event_type"] = EventType(data["event_type"])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ReplayEvent":
        """从 JSON 字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ReplaySession:
    """回放会话"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    trace_id: str = ""
    query: str = ""
    events: List[ReplayEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "trace_id": self.trace_id,
            "query": self.query,
            "events": [event.to_dict() for event in self.events],
            "metadata": self.metadata,
            "event_count": len(self.events),
            "duration_ms": (self.end_time - self.start_time) * 1000 if self.end_time else None,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplaySession":
        """从字典创建"""
        events = [ReplayEvent.from_dict(event_data) for event_data in data.get("events", [])]
        return cls(
            session_id=data["session_id"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            trace_id=data.get("trace_id", ""),
            query=data.get("query", ""),
            events=events,
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "ReplaySession":
        """从 JSON 字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class EventRecorder:
    """
    事件记录器
    记录系统运行时的所有事件
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.RLock()
        
        # 配置
        self._storage_path = Path(self._config.get("storage_path", "output/replay_recordings"))
        self._max_file_size_mb = self._config.get("max_file_size_mb", 100)
        self._compression = self._config.get("compression", True)
        
        # 当前会话
        self._current_session: Optional[ReplaySession] = None
        self._recording = False
        
        # 事件过滤器
        self._event_filters: List[Callable[[ReplayEvent], bool]] = []
        
        # 事件处理器
        self._event_handlers: List[Callable[[ReplayEvent], None]] = []
        
        # 确保存储目录存在
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        self._logger = get_logger("event_recorder")
    
    def start_recording(self, trace_id: str = "", query: str = "", metadata: Dict[str, Any] = None) -> str:
        """开始记录"""
        with self._lock:
            if self._recording:
                self._logger.warning("Recording already in progress")
                return self._current_session.session_id
            
            session_id = str(uuid.uuid4())[:8]
            self._current_session = ReplaySession(
                session_id=session_id,
                start_time=time.time(),
                trace_id=trace_id,
                query=query,
                metadata=metadata or {},
            )
            
            self._recording = True
            self._logger.info(f"Started recording session {session_id}")
            
            return session_id
    
    def stop_recording(self) -> Optional[ReplaySession]:
        """停止记录"""
        with self._lock:
            if not self._recording:
                self._logger.warning("No recording in progress")
                return None
            
            self._current_session.end_time = time.time()
            session = self._current_session
            
            # 保存到文件
            self._save_session(session)
            
            self._recording = False
            self._current_session = None
            
            self._logger.info(f"Stopped recording session {session.session_id}, {len(session.events)} events recorded")
            
            return session
    
    def record_event(self, event: ReplayEvent):
        """记录事件"""
        with self._lock:
            if not self._recording or not self._current_session:
                return
            
            # 应用过滤器
            for filter_func in self._event_filters:
                if not filter_func(event):
                    return
            
            # 添加到当前会话
            self._current_session.events.append(event)
            
            # 通知处理器
            for handler in self._event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    self._logger.error(f"Error in event handler: {e}")
    
    def record(
        self,
        event_type: EventType,
        trace_id: str = "",
        agent_name: str = "",
        task_id: str = "",
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        duration_ms: float = None,
    ):
        """记录事件（便捷方法）"""
        event = ReplayEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            timestamp=time.time(),
            wall_time=datetime.utcnow().isoformat() + "Z",
            trace_id=trace_id or (self._current_session.trace_id if self._current_session else ""),
            agent_name=agent_name,
            task_id=task_id,
            data=data or {},
            metadata=metadata or {},
            duration_ms=duration_ms,
        )
        
        self.record_event(event)
    
    def add_filter(self, filter_func: Callable[[ReplayEvent], bool]):
        """添加事件过滤器"""
        with self._lock:
            self._event_filters.append(filter_func)
    
    def remove_filter(self, filter_func: Callable[[ReplayEvent], bool]):
        """移除事件过滤器"""
        with self._lock:
            self._event_filters = [f for f in self._event_filters if f != filter_func]
    
    def add_handler(self, handler: Callable[[ReplayEvent], None]):
        """添加事件处理器"""
        with self._lock:
            self._event_handlers.append(handler)
    
    def remove_handler(self, handler: Callable[[ReplayEvent], None]):
        """移除事件处理器"""
        with self._lock:
            self._event_handlers = [h for h in self._event_handlers if h != handler]
    
    def _save_session(self, session: ReplaySession):
        """保存会话到文件"""
        try:
            # 生成文件名
            timestamp = datetime.fromtimestamp(session.start_time).strftime("%Y%m%d_%H%M%S")
            filename = f"replay_{timestamp}_{session.session_id}.json"
            filepath = self._storage_path / filename
            
            # 检查文件大小
            json_content = session.to_json()
            size_mb = len(json_content.encode('utf-8')) / 1024 / 1024
            
            if size_mb > self._max_file_size_mb:
                self._logger.warning(f"Session file too large: {size_mb:.2f}MB > {self._max_file_size_mb}MB")
                # 可以在这里实现分割逻辑
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            self._logger.info(f"Saved session to {filepath}")
            
        except Exception as e:
            self._logger.error(f"Failed to save session: {e}")
    
    def load_session(self, filepath: str) -> Optional[ReplaySession]:
        """从文件加载会话"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            session = ReplaySession.from_json(json_content)
            self._logger.info(f"Loaded session {session.session_id} from {filepath}")
            
            return session
            
        except Exception as e:
            self._logger.error(f"Failed to load session from {filepath}: {e}")
            return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有保存的会话"""
        sessions = []
        
        try:
            for filepath in self._storage_path.glob("replay_*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    sessions.append({
                        "filepath": str(filepath),
                        "session_id": data.get("session_id"),
                        "start_time": data.get("start_time"),
                        "trace_id": data.get("trace_id"),
                        "query": data.get("query", "")[:100],
                        "event_count": data.get("event_count", 0),
                        "duration_ms": data.get("duration_ms"),
                    })
                except Exception as e:
                    self._logger.warning(f"Failed to read session file {filepath}: {e}")
            
            # 按开始时间排序
            sessions.sort(key=lambda x: x.get("start_time", 0), reverse=True)
            
        except Exception as e:
            self._logger.error(f"Failed to list sessions: {e}")
        
        return sessions
    
    def get_current_session(self) -> Optional[ReplaySession]:
        """获取当前会话"""
        return self._current_session
    
    def is_recording(self) -> bool:
        """是否正在记录"""
        return self._recording


class ReplayPlayer:
    """
    回放播放器
    支持确定性回放和速度控制
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.RLock()
        
        # 配置
        self._deterministic_mode = self._config.get("deterministic_mode", False)
        self._speed_factor = self._config.get("speed_factor", 1.0)
        
        # 回放状态
        self._current_session: Optional[ReplaySession] = None
        self._current_event_index = 0
        self._playing = False
        self._paused = False
        
        # 事件处理器
        self._event_processors: Dict[EventType, List[Callable[[ReplayEvent], None]]] = {}
        
        # 回调
        self._on_event: Optional[Callable[[ReplayEvent], None]] = None
        self._on_complete: Optional[Callable[[ReplaySession], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None
        
        self._logger = get_logger("replay_player")
    
    def load_session(self, session: ReplaySession):
        """加载会话"""
        with self._lock:
            self._current_session = session
            self._current_event_index = 0
            self._playing = False
            self._paused = False
            
            self._logger.info(f"Loaded session {session.session_id} with {len(session.events)} events")
    
    def load_from_file(self, filepath: str) -> bool:
        """从文件加载会话"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            session = ReplaySession.from_json(json_content)
            self.load_session(session)
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to load session from {filepath}: {e}")
            return False
    
    def play(self, speed_factor: float = None):
        """开始回放"""
        with self._lock:
            if not self._current_session:
                self._logger.error("No session loaded")
                return
            
            if self._playing:
                self._logger.warning("Already playing")
                return
            
            self._playing = True
            self._paused = False
            
            if speed_factor is not None:
                self._speed_factor = speed_factor
            
            self._logger.info(f"Starting playback of session {self._current_session.session_id}")
            
            # 在新线程中运行回放
            playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
            playback_thread.start()
    
    def _playback_worker(self):
        """回放工作线程"""
        try:
            session = self._current_session
            events = session.events
            
            start_time = time.time()
            
            for i, event in enumerate(events):
                # 检查是否暂停
                while self._paused:
                    time.sleep(0.1)
                    if not self._playing:
                        return
                
                # 检查是否停止
                if not self._playing:
                    return
                
                # 计算延迟
                if not self._deterministic_mode and i > 0:
                    event_delay = event.timestamp - events[i-1].timestamp
                    adjusted_delay = event_delay / self._speed_factor
                    
                    # 等待
                    time.sleep(max(0, adjusted_delay))
                
                # 处理事件
                self._process_event(event)
                
                # 更新索引
                self._current_event_index = i + 1
            
            # 回放完成
            self._playing = False
            
            if self._on_complete:
                self._on_complete(session)
            
            self._logger.info(f"Playback completed for session {session.session_id}")
            
        except Exception as e:
            self._logger.error(f"Playback error: {e}")
            self._playing = False
            
            if self._on_error:
                self._on_error(e)
    
    def _process_event(self, event: ReplayEvent):
        """处理事件"""
        try:
            # 通用处理器
            if self._on_event:
                self._on_event(event)
            
            # 特定类型处理器
            processors = self._event_processors.get(event.event_type, [])
            for processor in processors:
                try:
                    processor(event)
                except Exception as e:
                    self._logger.error(f"Error in event processor: {e}")
            
        except Exception as e:
            self._logger.error(f"Error processing event: {e}")
    
    def pause(self):
        """暂停回放"""
        with self._lock:
            if self._playing and not self._paused:
                self._paused = True
                self._logger.info("Playback paused")
    
    def resume(self):
        """恢复回放"""
        with self._lock:
            if self._playing and self._paused:
                self._paused = False
                self._logger.info("Playback resumed")
    
    def stop(self):
        """停止回放"""
        with self._lock:
            self._playing = False
            self._paused = False
            self._logger.info("Playback stopped")
    
    def step(self) -> Optional[ReplayEvent]:
        """单步执行"""
        with self._lock:
            if not self._current_session:
                return None
            
            if self._current_event_index >= len(self._current_session.events):
                return None
            
            event = self._current_session.events[self._current_event_index]
            self._current_event_index += 1
            
            self._process_event(event)
            
            return event
    
    def seek(self, event_index: int):
        """跳转到指定事件"""
        with self._lock:
            if not self._current_session:
                return
            
            if 0 <= event_index < len(self._current_session.events):
                self._current_event_index = event_index
                self._logger.info(f"Seeked to event {event_index}")
    
    def register_processor(self, event_type: EventType, processor: Callable[[ReplayEvent], None]):
        """注册事件处理器"""
        with self._lock:
            if event_type not in self._event_processors:
                self._event_processors[event_type] = []
            self._event_processors[event_type].append(processor)
    
    def unregister_processor(self, event_type: EventType, processor: Callable[[ReplayEvent], None]):
        """取消注册事件处理器"""
        with self._lock:
            if event_type in self._event_processors:
                self._event_processors[event_type] = [
                    p for p in self._event_processors[event_type] if p != processor
                ]
    
    def set_callbacks(
        self,
        on_event: Callable[[ReplayEvent], None] = None,
        on_complete: Callable[[ReplaySession], None] = None,
        on_error: Callable[[Exception], None] = None,
    ):
        """设置回调函数"""
        self._on_event = on_event
        self._on_complete = on_complete
        self._on_error = on_error
    
    def get_progress(self) -> Dict[str, Any]:
        """获取回放进度"""
        with self._lock:
            if not self._current_session:
                return {"loaded": False}
            
            total_events = len(self._current_session.events)
            return {
                "loaded": True,
                "session_id": self._current_session.session_id,
                "total_events": total_events,
                "current_event": self._current_event_index,
                "progress_percent": (self._current_event_index / total_events * 100) if total_events > 0 else 0,
                "playing": self._playing,
                "paused": self._paused,
                "speed_factor": self._speed_factor,
                "deterministic_mode": self._deterministic_mode,
            }
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._playing and not self._paused
    
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._paused


class ReplayModule(EnhancementModule):
    """
    回放增强模块
    集成事件记录和回放功能
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        self._recorder = None
        self._player = None
    
    @property
    def name(self) -> str:
        return "replay"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Replay system with event recording, local JSON storage, and deterministic playback"
    
    def initialize(self) -> bool:
        """初始化模块"""
        try:
            self._logger.info("Initializing ReplayModule...")
            
            # 初始化事件记录器
            recording_config = self._config.get("recording", {})
            if recording_config.get("enabled", False):
                self._recorder = EventRecorder(recording_config)
                self._logger.info("Event recorder initialized")
            
            # 初始化回放播放器
            playback_config = self._config.get("playback", {})
            if playback_config.get("enabled", False):
                self._player = ReplayPlayer(playback_config)
                self._logger.info("Replay player initialized")
            
            self._status = ModuleStatus.LOADED
            self._logger.info("ReplayModule initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize ReplayModule: {e}")
            self._status = ModuleStatus.ERROR
            self._config["error_message"] = str(e)
            return False
    
    def cleanup(self) -> bool:
        """清理模块"""
        try:
            self._logger.info("Cleaning up ReplayModule...")
            
            if self._recorder:
                if self._recorder.is_recording():
                    self._recorder.stop_recording()
                self._recorder = None
            
            if self._player:
                if self._player.is_playing():
                    self._player.stop()
                self._player = None
            
            self._status = ModuleStatus.UNLOADED
            self._logger.info("ReplayModule cleaned up successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup ReplayModule: {e}")
            return False
    
    def get_recorder(self) -> Optional[EventRecorder]:
        """获取事件记录器"""
        return self._recorder
    
    def get_player(self) -> Optional[ReplayPlayer]:
        """获取回放播放器"""
        return self._player
    
    def start_recording(self, trace_id: str = "", query: str = "", metadata: Dict[str, Any] = None) -> Optional[str]:
        """开始记录"""
        if not self._recorder:
            self._logger.error("Event recorder not initialized")
            return None
        
        return self._recorder.start_recording(trace_id, query, metadata)
    
    def stop_recording(self) -> Optional[ReplaySession]:
        """停止记录"""
        if not self._recorder:
            self._logger.error("Event recorder not initialized")
            return None
        
        return self._recorder.stop_recording()
    
    def record_event(
        self,
        event_type: EventType,
        trace_id: str = "",
        agent_name: str = "",
        task_id: str = "",
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        duration_ms: float = None,
    ):
        """记录事件"""
        if not self._recorder:
            return
        
        self._recorder.record(
            event_type=event_type,
            trace_id=trace_id,
            agent_name=agent_name,
            task_id=task_id,
            data=data,
            metadata=metadata,
            duration_ms=duration_ms,
        )
    
    def load_session(self, filepath: str) -> Optional[ReplaySession]:
        """加载会话"""
        if not self._player:
            self._logger.error("Replay player not initialized")
            return None
        
        if self._player.load_from_file(filepath):
            return self._player._current_session
        return None
    
    def play_session(self, speed_factor: float = None):
        """播放会话"""
        if not self._player:
            self._logger.error("Replay player not initialized")
            return
        
        self._player.play(speed_factor)
    
    def list_recordings(self) -> List[Dict[str, Any]]:
        """列出所有记录"""
        if not self._recorder:
            return []
        
        return self._recorder.list_sessions()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        stats = {
            "module": self.get_info().to_dict(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self._recorder:
            stats["recorder"] = {
                "is_recording": self._recorder.is_recording(),
                "current_session": self._recorder.get_current_session().to_dict() if self._recorder.get_current_session() else None,
            }
        
        if self._player:
            stats["player"] = self._player.get_progress()
        
        return stats