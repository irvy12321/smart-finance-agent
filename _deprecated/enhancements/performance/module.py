"""
性能分析模块
支持 CPU profiling、网络 I/O 分析、LLM 调用分析
外挂模块，不影响现有系统
"""
import cProfile
import pstats
import io
import time
import threading
import json
import os
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from utils.logger import get_logger
from ..base import EnhancementModule, ModuleStatus
from ..feature_toggle import is_feature_enabled


@dataclass
class CPUProfile:
    """CPU 性能分析结果"""
    profile_id: str
    start_time: float
    end_time: float
    duration_ms: float
    total_calls: int
    total_time_ms: float
    function_stats: List[Dict[str, Any]]
    top_functions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    def print_stats(self, top_n: int = 20):
        """打印统计信息"""
        print(f"\n{'='*60}")
        print(f"CPU Profile: {self.profile_id}")
        print(f"{'='*60}")
        print(f"Duration: {self.duration_ms:.2f}ms")
        print(f"Total Calls: {self.total_calls}")
        print(f"Total Time: {self.total_time_ms:.2f}ms")
        print(f"\nTop {top_n} Functions:")
        print(f"{'-'*60}")
        
        for i, func in enumerate(self.top_functions[:top_n]):
            print(f"{i+1:3d}. {func['function']:<50s} {func['total_time_ms']:8.2f}ms {func['calls']:5d} calls")


class CPUProfiler:
    """
    CPU 性能分析器
    支持函数级 profiling 和热点分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 配置
        self._sampling_rate_hz = self._config.get("sampling_rate_hz", 100)
        self._output_format = self._config.get("output_format", "snakeviz")
        self._output_path = Path(self._config.get("output_path", "output/cpu_profiles"))
        
        # 确保输出目录存在
        self._output_path.mkdir(parents=True, exist_ok=True)
        
        # 当前 profiler
        self._current_profiler: Optional[cProfile.Profile] = None
        self._profiling = False
        
        # 历史记录
        self._profiles: List[CPUProfile] = []
        
        self._logger = get_logger("cpu_profiler")
    
    def start_profiling(self):
        """开始 CPU profiling"""
        with self._lock:
            if self._profiling:
                self._logger.warning("Profiling already in progress")
                return
            
            self._current_profiler = cProfile.Profile()
            self._current_profiler.enable()
            self._profiling = True
            
            self._logger.info("CPU profiling started")
    
    def stop_profiling(self) -> Optional[CPUProfile]:
        """停止 CPU profiling"""
        with self._lock:
            if not self._profiling or not self._current_profiler:
                self._logger.warning("No profiling in progress")
                return None
            
            self._current_profiler.disable()
            
            # 分析结果
            profile = self._analyze_profile()
            
            # 保存结果
            self._save_profile(profile)
            
            # 清理
            self._current_profiler = None
            self._profiling = False
            
            self._logger.info(f"CPU profiling stopped, {profile.total_calls} calls captured")
            
            return profile
    
    def _analyze_profile(self) -> CPUProfile:
        """分析 profiling 结果"""
        import uuid
        
        # 获取统计信息
        stream = io.StringIO()
        stats = pstats.Stats(self._current_profiler, stream=stream)
        stats.sort_stats('cumulative')
        
        # 提取函数统计
        function_stats = []
        top_functions = []
        
        for func_key, (cc, nc, tt, ct, callers) in stats.stats.items():
            filename, line, func_name = func_key
            
            func_stat = {
                "function": f"{filename}:{line}({func_name})",
                "filename": filename,
                "line": line,
                "func_name": func_name,
                "call_count": cc,
                "total_time_ms": tt * 1000,
                "cumulative_time_ms": ct * 1000,
                "avg_time_ms": (tt / cc * 1000) if cc > 0 else 0,
            }
            
            function_stats.append(func_stat)
            top_functions.append(func_stat)
        
        # 按累计时间排序
        top_functions.sort(key=lambda x: x["cumulative_time_ms"], reverse=True)
        
        # 计算总时间和调用次数
        total_calls = sum(f["call_count"] for f in function_stats)
        total_time_ms = sum(f["total_time_ms"] for f in function_stats)
        
        return CPUProfile(
            profile_id=str(uuid.uuid4())[:8],
            start_time=time.time() - (total_time_ms / 1000),
            end_time=time.time(),
            duration_ms=total_time_ms,
            total_calls=total_calls,
            total_time_ms=total_time_ms,
            function_stats=function_stats,
            top_functions=top_functions[:100],  # 只保留前 100 个
        )
    
    def _save_profile(self, profile: CPUProfile):
        """保存 profiling 结果"""
        try:
            timestamp = datetime.fromtimestamp(profile.end_time).strftime("%Y%m%d_%H%M%S")
            filename = f"cpu_profile_{timestamp}_{profile.profile_id}.json"
            filepath = self._output_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(profile.to_json())
            
            # 如果配置了 snakeviz 格式，也保存 pstats 文件
            if self._output_format == "snakeviz":
                stats_file = self._output_path / f"cpu_profile_{timestamp}_{profile.profile_id}.prof"
                stats = pstats.Stats(self._current_profiler)
                stats.dump_stats(str(stats_file))
            
            self._logger.info(f"Saved CPU profile to {filepath}")
            
        except Exception as e:
            self._logger.error(f"Failed to save CPU profile: {e}")
    
    @contextmanager
    def profile_context(self, name: str = ""):
        """Profile 上下文管理器"""
        self.start_profiling()
        try:
            yield self
        finally:
            profile = self.stop_profiling()
            if profile:
                profile.metadata["name"] = name
                self._profiles.append(profile)
    
    def get_profiles(self) -> List[CPUProfile]:
        """获取所有 profiling 结果"""
        return self._profiles.copy()
    
    def get_latest_profile(self) -> Optional[CPUProfile]:
        """获取最新的 profiling 结果"""
        return self._profiles[-1] if self._profiles else None
    
    def clear_profiles(self):
        """清除所有 profiling 结果"""
        self._profiles.clear()


@dataclass
class NetworkRequest:
    """网络请求记录"""
    request_id: str
    method: str
    url: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class NetworkProfiler:
    """
    网络 I/O 分析器
    支持 HTTP 请求监控和性能分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 配置
        self._track_requests = self._config.get("track_requests", True)
        self._track_dns = self._config.get("track_dns", False)
        
        # 请求记录
        self._requests: List[NetworkRequest] = []
        self._active_requests: Dict[str, NetworkRequest] = {}
        
        # 统计信息
        self._total_requests = 0
        self._total_errors = 0
        self._total_bytes_sent = 0
        self._total_bytes_received = 0
        
        self._logger = get_logger("network_profiler")
    
    def start_request(self, method: str, url: str, metadata: Dict[str, Any] = None) -> str:
        """开始记录请求"""
        import uuid
        
        request_id = str(uuid.uuid4())[:8]
        request = NetworkRequest(
            request_id=request_id,
            method=method,
            url=url,
            start_time=time.time(),
            metadata=metadata or {},
        )
        
        with self._lock:
            self._active_requests[request_id] = request
            self._total_requests += 1
        
        return request_id
    
    def end_request(
        self,
        request_id: str,
        status_code: int = None,
        request_size_bytes: int = None,
        response_size_bytes: int = None,
        error: str = None,
    ):
        """结束记录请求"""
        with self._lock:
            request = self._active_requests.pop(request_id, None)
            if not request:
                self._logger.warning(f"Request {request_id} not found")
                return
            
            request.end_time = time.time()
            request.duration_ms = (request.end_time - request.start_time) * 1000
            request.status_code = status_code
            request.request_size_bytes = request_size_bytes
            request.response_size_bytes = response_size_bytes
            request.error = error
            
            # 更新统计
            if error:
                self._total_errors += 1
            if request_size_bytes:
                self._total_bytes_sent += request_size_bytes
            if response_size_bytes:
                self._total_bytes_received += response_size_bytes
            
            # 保存到历史记录
            self._requests.append(request)
            
            # 限制历史记录数量
            if len(self._requests) > 1000:
                self._requests = self._requests[-1000:]
    
    def get_requests(self, limit: int = 100) -> List[NetworkRequest]:
        """获取请求记录"""
        with self._lock:
            return self._requests[-limit:]
    
    def get_active_requests(self) -> List[NetworkRequest]:
        """获取活跃请求"""
        with self._lock:
            return list(self._active_requests.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            durations = [r.duration_ms for r in self._requests if r.duration_ms]
            
            return {
                "total_requests": self._total_requests,
                "active_requests": len(self._active_requests),
                "completed_requests": len(self._requests),
                "total_errors": self._total_errors,
                "error_rate": (self._total_errors / self._total_requests * 100) if self._total_requests > 0 else 0,
                "total_bytes_sent": self._total_bytes_sent,
                "total_bytes_received": self._total_bytes_received,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
            }
    
    def get_slow_requests(self, threshold_ms: float = 1000) -> List[NetworkRequest]:
        """获取慢请求"""
        with self._lock:
            return [r for r in self._requests if r.duration_ms and r.duration_ms > threshold_ms]
    
    def get_error_requests(self) -> List[NetworkRequest]:
        """获取错误请求"""
        with self._lock:
            return [r for r in self._requests if r.error]
    
    def clear(self):
        """清除所有记录"""
        with self._lock:
            self._requests.clear()
            self._active_requests.clear()
            self._total_requests = 0
            self._total_errors = 0
            self._total_bytes_sent = 0
            self._total_bytes_received = 0


@dataclass
class LLMCall:
    """LLM 调用记录"""
    call_id: str
    model: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class LLMProfiler:
    """
    LLM 调用分析器
    支持 token 使用、延迟、成本分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 配置
        self._track_token_usage = self._config.get("track_token_usage", True)
        self._track_latency = self._config.get("track_latency", True)
        self._track_costs = self._config.get("track_costs", True)
        
        # 价格表（每 1000 tokens）
        self._pricing = self._config.get("pricing", {
            "openai/mimo-v2.5-pro": {"input": 0.002, "output": 0.006},
            "openai/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "openai/gpt-4o": {"input": 0.005, "output": 0.015},
        })
        
        # 调用记录
        self._calls: List[LLMCall] = []
        self._active_calls: Dict[str, LLMCall] = {}
        
        # 统计信息
        self._total_calls = 0
        self._total_errors = 0
        self._total_tokens = 0
        self._total_cost_usd = 0.0
        
        self._logger = get_logger("llm_profiler")
    
    def start_call(self, model: str, metadata: Dict[str, Any] = None) -> str:
        """开始记录 LLM 调用"""
        import uuid
        
        call_id = str(uuid.uuid4())[:8]
        call = LLMCall(
            call_id=call_id,
            model=model,
            start_time=time.time(),
            metadata=metadata or {},
        )
        
        with self._lock:
            self._active_calls[call_id] = call
            self._total_calls += 1
        
        return call_id
    
    def end_call(
        self,
        call_id: str,
        prompt_tokens: int = None,
        completion_tokens: int = None,
        success: bool = True,
        error: str = None,
    ):
        """结束记录 LLM 调用"""
        with self._lock:
            call = self._active_calls.pop(call_id, None)
            if not call:
                self._logger.warning(f"LLM call {call_id} not found")
                return
            
            call.end_time = time.time()
            call.duration_ms = (call.end_time - call.start_time) * 1000
            call.prompt_tokens = prompt_tokens
            call.completion_tokens = completion_tokens
            call.total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
            call.success = success
            call.error = error
            
            # 计算成本
            if self._track_costs and call.total_tokens:
                call.cost_usd = self._calculate_cost(call.model, prompt_tokens, completion_tokens)
                self._total_cost_usd += call.cost_usd
            
            # 更新统计
            if not success:
                self._total_errors += 1
            if call.total_tokens:
                self._total_tokens += call.total_tokens
            
            # 保存到历史记录
            self._calls.append(call)
            
            # 限制历史记录数量
            if len(self._calls) > 1000:
                self._calls = self._calls[-1000:]
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算调用成本"""
        pricing = self._pricing.get(model, {})
        if not pricing:
            return 0.0
        
        input_cost = (prompt_tokens or 0) / 1000 * pricing.get("input", 0)
        output_cost = (completion_tokens or 0) / 1000 * pricing.get("output", 0)
        
        return input_cost + output_cost
    
    def get_calls(self, limit: int = 100) -> List[LLMCall]:
        """获取调用记录"""
        with self._lock:
            return self._calls[-limit:]
    
    def get_active_calls(self) -> List[LLMCall]:
        """获取活跃调用"""
        with self._lock:
            return list(self._active_calls.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            durations = [c.duration_ms for c in self._calls if c.duration_ms]
            tokens = [c.total_tokens for c in self._calls if c.total_tokens]
            costs = [c.cost_usd for c in self._calls if c.cost_usd]
            
            return {
                "total_calls": self._total_calls,
                "active_calls": len(self._active_calls),
                "completed_calls": len(self._calls),
                "total_errors": self._total_errors,
                "error_rate": (self._total_errors / self._total_calls * 100) if self._total_calls > 0 else 0,
                "total_tokens": self._total_tokens,
                "total_cost_usd": self._total_cost_usd,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "avg_tokens_per_call": sum(tokens) / len(tokens) if tokens else 0,
                "avg_cost_per_call": sum(costs) / len(costs) if costs else 0,
            }
    
    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取按模型分组的统计信息"""
        with self._lock:
            model_stats = {}
            
            for call in self._calls:
                if call.model not in model_stats:
                    model_stats[call.model] = {
                        "calls": 0,
                        "errors": 0,
                        "total_tokens": 0,
                        "total_cost_usd": 0.0,
                        "total_duration_ms": 0.0,
                    }
                
                stats = model_stats[call.model]
                stats["calls"] += 1
                
                if not call.success:
                    stats["errors"] += 1
                if call.total_tokens:
                    stats["total_tokens"] += call.total_tokens
                if call.cost_usd:
                    stats["total_cost_usd"] += call.cost_usd
                if call.duration_ms:
                    stats["total_duration_ms"] += call.duration_ms
            
            # 计算平均值
            for model, stats in model_stats.items():
                if stats["calls"] > 0:
                    stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["calls"]
                    stats["avg_tokens_per_call"] = stats["total_tokens"] / stats["calls"]
                    stats["avg_cost_per_call"] = stats["total_cost_usd"] / stats["calls"]
                    stats["error_rate"] = stats["errors"] / stats["calls"] * 100
            
            return model_stats
    
    def get_slow_calls(self, threshold_ms: float = 5000) -> List[LLMCall]:
        """获取慢调用"""
        with self._lock:
            return [c for c in self._calls if c.duration_ms and c.duration_ms > threshold_ms]
    
    def get_error_calls(self) -> List[LLMCall]:
        """获取错误调用"""
        with self._lock:
            return [c for c in self._calls if not c.success]
    
    def get_expensive_calls(self, threshold_usd: float = 0.1) -> List[LLMCall]:
        """获取昂贵调用"""
        with self._lock:
            return [c for c in self._calls if c.cost_usd and c.cost_usd > threshold_usd]
    
    def clear(self):
        """清除所有记录"""
        with self._lock:
            self._calls.clear()
            self._active_calls.clear()
            self._total_calls = 0
            self._total_errors = 0
            self._total_tokens = 0
            self._total_cost_usd = 0.0


class PerformanceModule(EnhancementModule):
    """
    性能分析增强模块
    集成 CPU profiling、网络 I/O 分析、LLM 调用分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        self._cpu_profiler = None
        self._network_profiler = None
        self._llm_profiler = None
    
    @property
    def name(self) -> str:
        return "performance"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Performance profiling with CPU profiling, network I/O analysis, and LLM call analysis"
    
    def initialize(self) -> bool:
        """初始化模块"""
        try:
            self._logger.info("Initializing PerformanceModule...")
            
            # 初始化 CPU profiler
            cpu_config = self._config.get("cpu_profiling", {})
            if cpu_config.get("enabled", False):
                self._cpu_profiler = CPUProfiler(cpu_config)
                self._logger.info("CPU profiler initialized")
            
            # 初始化网络 profiler
            network_config = self._config.get("network_profiling", {})
            if network_config.get("enabled", False):
                self._network_profiler = NetworkProfiler(network_config)
                self._logger.info("Network profiler initialized")
            
            # 初始化 LLM profiler
            llm_config = self._config.get("llm_profiling", {})
            if llm_config.get("enabled", False):
                self._llm_profiler = LLMProfiler(llm_config)
                self._logger.info("LLM profiler initialized")
            
            self._status = ModuleStatus.LOADED
            self._logger.info("PerformanceModule initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize PerformanceModule: {e}")
            self._status = ModuleStatus.ERROR
            self._config["error_message"] = str(e)
            return False
    
    def cleanup(self) -> bool:
        """清理模块"""
        try:
            self._logger.info("Cleaning up PerformanceModule...")
            
            if self._cpu_profiler:
                self._cpu_profiler = None
            
            if self._network_profiler:
                self._network_profiler.clear()
                self._network_profiler = None
            
            if self._llm_profiler:
                self._llm_profiler.clear()
                self._llm_profiler = None
            
            self._status = ModuleStatus.UNLOADED
            self._logger.info("PerformanceModule cleaned up successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup PerformanceModule: {e}")
            return False
    
    def get_cpu_profiler(self) -> Optional[CPUProfiler]:
        """获取 CPU profiler"""
        return self._cpu_profiler
    
    def get_network_profiler(self) -> Optional[NetworkProfiler]:
        """获取网络 profiler"""
        return self._network_profiler
    
    def get_llm_profiler(self) -> Optional[LLMProfiler]:
        """获取 LLM profiler"""
        return self._llm_profiler
    
    def start_cpu_profiling(self):
        """开始 CPU profiling"""
        if self._cpu_profiler:
            self._cpu_profiler.start_profiling()
    
    def stop_cpu_profiling(self) -> Optional[CPUProfile]:
        """停止 CPU profiling"""
        if self._cpu_profiler:
            return self._cpu_profiler.stop_profiling()
        return None
    
    def record_network_request(
        self,
        method: str,
        url: str,
        status_code: int = None,
        request_size_bytes: int = None,
        response_size_bytes: int = None,
        duration_ms: float = None,
        error: str = None,
    ):
        """记录网络请求"""
        if not self._network_profiler:
            return
        
        request_id = self._network_profiler.start_request(method, url)
        self._network_profiler.end_request(
            request_id,
            status_code=status_code,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            error=error,
        )
    
    def record_llm_call(
        self,
        model: str,
        prompt_tokens: int = None,
        completion_tokens: int = None,
        duration_ms: float = None,
        success: bool = True,
        error: str = None,
    ):
        """记录 LLM 调用"""
        if not self._llm_profiler:
            return
        
        call_id = self._llm_profiler.start_call(model)
        self._llm_profiler.end_call(
            call_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=success,
            error=error,
        )
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        stats = {
            "module": self.get_info().to_dict(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self._cpu_profiler:
            stats["cpu"] = {
                "profiles": len(self._cpu_profiler.get_profiles()),
                "latest_profile": self._cpu_profiler.get_latest_profile().to_dict() if self._cpu_profiler.get_latest_profile() else None,
            }
        
        if self._network_profiler:
            stats["network"] = self._network_profiler.get_stats()
        
        if self._llm_profiler:
            stats["llm"] = self._llm_profiler.get_stats()
        
        return stats