"""
增强的可观测性模块
提供结构化日志、指标聚合、性能分析等功能
外挂模块，不影响现有系统
"""
import json
import time
import threading
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging
from pathlib import Path

from utils.logger import get_logger
from ..base import EnhancementModule, ModuleStatus
from ..feature_toggle import is_feature_enabled


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StructuredLogEntry:
    """结构化日志条目"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 移除 None 值
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class StructuredLogger:
    """
    结构化日志记录器
    支持 JSON 格式输出，便于日志聚合和分析
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self._name = name
        self._config = config or {}
        self._logger = get_logger(name)
        self._lock = threading.Lock()
        
        # 配置
        self._format = self._config.get("format", "json")
        self._include_trace_id = self._config.get("include_trace_id", True)
        self._include_span_id = self._config.get("include_span_id", True)
        self._output_path = self._config.get("output_path")
        
        # 输出文件句柄
        self._file_handler = None
        if self._output_path:
            self._setup_file_handler()
    
    def _setup_file_handler(self):
        """设置文件处理器"""
        try:
            output_path = Path(self._output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._file_handler = open(output_path, 'a', encoding='utf-8')
        except Exception as e:
            self._logger.error(f"Failed to setup file handler: {e}")
    
    def _create_entry(
        self,
        level: LogLevel,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        **kwargs
    ) -> StructuredLogEntry:
        """创建日志条目"""
        import inspect
        
        # 获取调用者信息
        frame = inspect.currentframe().f_back.f_back
        module = frame.f_globals.get('__name__', '')
        function = frame.f_code.co_name
        line_number = frame.f_lineno
        
        return StructuredLogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level.value,
            logger_name=self._name,
            message=message,
            trace_id=trace_id if self._include_trace_id else None,
            span_id=span_id if self._include_span_id else None,
            module=module,
            function=function,
            line_number=line_number,
            extra=kwargs,
        )
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        **kwargs
    ):
        """记录日志"""
        entry = self._create_entry(level, message, trace_id, span_id, **kwargs)
        
        # 输出到控制台
        self._log_to_console(entry)
        
        # 输出到文件
        if self._file_handler:
            self._log_to_file(entry)
        
        # 输出到标准日志系统
        self._log_to_standard(entry)
    
    def _log_to_console(self, entry: StructuredLogEntry):
        """输出到控制台"""
        if self._format == "json":
            print(entry.to_json())
        else:
            # 文本格式
            trace_info = f" [trace:{entry.trace_id}]" if entry.trace_id else ""
            print(f"{entry.timestamp} {entry.level.upper():8s} {entry.logger_name}{trace_info} - {entry.message}")
    
    def _log_to_file(self, entry: StructuredLogEntry):
        """输出到文件"""
        try:
            with self._lock:
                self._file_handler.write(entry.to_json() + "\n")
                self._file_handler.flush()
        except Exception as e:
            self._logger.error(f"Failed to write to log file: {e}")
    
    def _log_to_standard(self, entry: StructuredLogEntry):
        """输出到标准日志系统"""
        log_func = getattr(self._logger, entry.level, self._logger.info)
        log_func(entry.message)
    
    def debug(self, message: str, trace_id: Optional[str] = None, **kwargs):
        """记录 DEBUG 级别日志"""
        self._log(LogLevel.DEBUG, message, trace_id, **kwargs)
    
    def info(self, message: str, trace_id: Optional[str] = None, **kwargs):
        """记录 INFO 级别日志"""
        self._log(LogLevel.INFO, message, trace_id, **kwargs)
    
    def warning(self, message: str, trace_id: Optional[str] = None, **kwargs):
        """记录 WARNING 级别日志"""
        self._log(LogLevel.WARNING, message, trace_id, **kwargs)
    
    def error(self, message: str, trace_id: Optional[str] = None, **kwargs):
        """记录 ERROR 级别日志"""
        self._log(LogLevel.ERROR, message, trace_id, **kwargs)
    
    def critical(self, message: str, trace_id: Optional[str] = None, **kwargs):
        """记录 CRITICAL 级别日志"""
        self._log(LogLevel.CRITICAL, message, trace_id, **kwargs)
    
    def exception(self, message: str, trace_id: Optional[str] = None, **kwargs):
        """记录异常日志"""
        import traceback
        kwargs["exception"] = traceback.format_exc()
        self._log(LogLevel.ERROR, message, trace_id, **kwargs)
    
    def close(self):
        """关闭日志记录器"""
        if self._file_handler:
            try:
                self._file_handler.close()
            except Exception:
                pass


class MetricsAggregator:
    """
    指标聚合器
    支持多种指标类型的聚合和导出
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 指标存储
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list[float]] = {}
        self._timers: Dict[str, list[float]] = {}
        
        # 导出配置
        self._export_interval = self._config.get("export_interval_seconds", 60)
        self._export_format = self._config.get("export_format", "json")
        self._export_path = self._config.get("export_path")
        
        # 导出线程
        self._export_thread = None
        self._stop_event = threading.Event()
        
        # 启动导出线程
        if self._export_path and self._export_interval > 0:
            self._start_export_thread()
    
    def _start_export_thread(self):
        """启动导出线程"""
        def export_worker():
            while not self._stop_event.wait(self._export_interval):
                self._export_metrics()
        
        self._export_thread = threading.Thread(target=export_worker, daemon=True)
        self._export_thread.start()
    
    def _export_metrics(self):
        """导出指标"""
        try:
            if not self._export_path:
                return
            
            export_path = Path(self._export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            metrics = self.get_all_metrics()
            
            if self._export_format == "json":
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(metrics, f, indent=2, ensure_ascii=False)
            elif self._export_format == "prometheus":
                self._export_prometheus(export_path, metrics)
            elif self._export_format == "csv":
                self._export_csv(export_path, metrics)
            
        except Exception as e:
            logging.error(f"Failed to export metrics: {e}")
    
    def _export_prometheus(self, export_path: Path, metrics: Dict[str, Any]):
        """导出 Prometheus 格式"""
        with open(export_path, 'w', encoding='utf-8') as f:
            for name, value in metrics.get("counters", {}).items():
                f.write(f"# TYPE {name} counter\n")
                f.write(f"{name} {value}\n")
            
            for name, value in metrics.get("gauges", {}).items():
                f.write(f"# TYPE {name} gauge\n")
                f.write(f"{name} {value}\n")
            
            for name, stats in metrics.get("histograms", {}).items():
                f.write(f"# TYPE {name} histogram\n")
                f.write(f"{name}_count {stats.get('count', 0)}\n")
                f.write(f"{name}_sum {stats.get('sum', 0)}\n")
                f.write(f"{name}_bucket{{le=\"+Inf\"}} {stats.get('count', 0)}\n")
    
    def _export_csv(self, export_path: Path, metrics: Dict[str, Any]):
        """导出 CSV 格式"""
        import csv
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["metric_type", "metric_name", "value"])
            
            for name, value in metrics.get("counters", {}).items():
                writer.writerow(["counter", name, value])
            
            for name, value in metrics.get("gauges", {}).items():
                writer.writerow(["gauge", name, value])
            
            for name, stats in metrics.get("histograms", {}).items():
                writer.writerow(["histogram", name, json.dumps(stats)])
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """增加计数器"""
        with self._lock:
            key = self._create_key(name, tags)
            self._counters[key] = self._counters.get(key, 0) + value
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表值"""
        with self._lock:
            key = self._create_key(name, tags)
            self._gauges[key] = value
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图值"""
        with self._lock:
            key = self._create_key(name, tags)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
    
    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """记录计时器值"""
        with self._lock:
            key = self._create_key(name, tags)
            if key not in self._timers:
                self._timers[key] = []
            self._timers[key].append(duration_ms)
    
    def _create_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """创建指标键"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"
    
    def get_counter(self, name: str, tags: Dict[str, str] = None) -> float:
        """获取计数器值"""
        with self._lock:
            key = self._create_key(name, tags)
            return self._counters.get(key, 0)
    
    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """获取仪表值"""
        with self._lock:
            key = self._create_key(name, tags)
            return self._gauges.get(key)
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, Any]:
        """获取直方图统计"""
        with self._lock:
            key = self._create_key(name, tags)
            values = self._histograms.get(key, [])
            
            if not values:
                return {"count": 0}
            
            sorted_values = sorted(values)
            return {
                "count": len(values),
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": sorted_values[len(sorted_values) // 2],
                "p90": sorted_values[int(len(sorted_values) * 0.9)],
                "p95": sorted_values[int(len(sorted_values) * 0.95)],
                "p99": sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[0],
            }
    
    def get_timer_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, Any]:
        """获取计时器统计"""
        return self.get_histogram_stats(name, tags)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            return {
                "counters": self._counters.copy(),
                "gauges": self._gauges.copy(),
                "histograms": {
                    name: self.get_histogram_stats(name)
                    for name in self._histograms
                },
                "timers": {
                    name: self.get_timer_stats(name)
                    for name in self._timers
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
    
    def clear(self):
        """清除所有指标"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
    
    def stop(self):
        """停止导出线程"""
        self._stop_event.set()
        if self._export_thread:
            self._export_thread.join(timeout=5)


class PerformanceProfiler:
    """
    性能分析器
    支持函数级耗时统计、内存使用监控等
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 性能数据存储
        self._function_stats: Dict[str, Dict[str, Any]] = {}
        self._memory_snapshots: list[Dict[str, Any]] = []
        
        # 配置
        self._enable_memory_profiling = self._config.get("memory_profiling", False)
        self._snapshot_interval = self._config.get("snapshot_interval_seconds", 30)
        
        # 内存监控线程
        self._memory_thread = None
        self._stop_event = threading.Event()
        
        if self._enable_memory_profiling:
            self._start_memory_monitoring()
    
    def _start_memory_monitoring(self):
        """启动内存监控"""
        def memory_worker():
            while not self._stop_event.wait(self._snapshot_interval):
                self._take_memory_snapshot()
        
        self._memory_thread = threading.Thread(target=memory_worker, daemon=True)
        self._memory_thread.start()
    
    def _take_memory_snapshot(self):
        """获取内存快照"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            snapshot = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }
            
            with self._lock:
                self._memory_snapshots.append(snapshot)
                # 保留最近 100 个快照
                if len(self._memory_snapshots) > 100:
                    self._memory_snapshots = self._memory_snapshots[-100:]
            
        except ImportError:
            # psutil 不可用
            pass
        except Exception as e:
            logging.error(f"Failed to take memory snapshot: {e}")
    
    def profile_function(self, func_name: str, duration_ms: float, success: bool = True):
        """记录函数性能数据"""
        with self._lock:
            if func_name not in self._function_stats:
                self._function_stats[func_name] = {
                    "call_count": 0,
                    "total_duration_ms": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "min_duration_ms": float('inf'),
                    "max_duration_ms": 0,
                    "durations": [],
                }
            
            stats = self._function_stats[func_name]
            stats["call_count"] += 1
            stats["total_duration_ms"] += duration_ms
            stats["min_duration_ms"] = min(stats["min_duration_ms"], duration_ms)
            stats["max_duration_ms"] = max(stats["max_duration_ms"], duration_ms)
            stats["durations"].append(duration_ms)
            
            if success:
                stats["success_count"] += 1
            else:
                stats["error_count"] += 1
            
            # 保留最近 1000 个持续时间
            if len(stats["durations"]) > 1000:
                stats["durations"] = stats["durations"][-1000:]
    
    def get_function_stats(self, func_name: str = None) -> Dict[str, Any]:
        """获取函数性能统计"""
        with self._lock:
            if func_name:
                stats = self._function_stats.get(func_name, {})
                if not stats:
                    return {}
                
                # 计算统计信息
                durations = stats["durations"]
                if durations:
                    sorted_durations = sorted(durations)
                    return {
                        "call_count": stats["call_count"],
                        "total_duration_ms": stats["total_duration_ms"],
                        "avg_duration_ms": stats["total_duration_ms"] / stats["call_count"],
                        "min_duration_ms": stats["min_duration_ms"],
                        "max_duration_ms": stats["max_duration_ms"],
                        "success_count": stats["success_count"],
                        "error_count": stats["error_count"],
                        "success_rate": stats["success_count"] / stats["call_count"] * 100,
                        "p50_duration_ms": sorted_durations[len(sorted_durations) // 2],
                        "p90_duration_ms": sorted_durations[int(len(sorted_durations) * 0.9)],
                        "p95_duration_ms": sorted_durations[int(len(sorted_durations) * 0.95)],
                        "p99_duration_ms": sorted_durations[int(len(sorted_durations) * 0.99)] if len(sorted_durations) > 1 else sorted_durations[0],
                    }
                else:
                    return {
                        "call_count": stats["call_count"],
                        "total_duration_ms": stats["total_duration_ms"],
                        "success_count": stats["success_count"],
                        "error_count": stats["error_count"],
                    }
            else:
                # 返回所有函数的统计
                result = {}
                for name, stats in self._function_stats.items():
                    result[name] = self.get_function_stats(name)
                return result
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计"""
        with self._lock:
            if not self._memory_snapshots:
                return {"snapshots": 0}
            
            rss_values = [s["rss_mb"] for s in self._memory_snapshots]
            vms_values = [s["vms_mb"] for s in self._memory_snapshots]
            
            return {
                "snapshots": len(self._memory_snapshots),
                "current_rss_mb": rss_values[-1] if rss_values else 0,
                "current_vms_mb": vms_values[-1] if vms_values else 0,
                "avg_rss_mb": sum(rss_values) / len(rss_values),
                "max_rss_mb": max(rss_values),
                "min_rss_mb": min(rss_values),
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有性能统计"""
        return {
            "function_stats": self.get_function_stats(),
            "memory_stats": self.get_memory_stats(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    def clear(self):
        """清除所有性能数据"""
        with self._lock:
            self._function_stats.clear()
            self._memory_snapshots.clear()
    
    def stop(self):
        """停止内存监控"""
        self._stop_event.set()
        if self._memory_thread:
            self._memory_thread.join(timeout=5)


class ObservabilityModule(EnhancementModule):
    """
    可观测性增强模块
    集成结构化日志、指标聚合、性能分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        self._structured_logger = None
        self._metrics_aggregator = None
        self._performance_profiler = None
    
    @property
    def name(self) -> str:
        return "observability"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Enhanced observability with structured logging, metrics aggregation, and performance profiling"
    
    def initialize(self) -> bool:
        """初始化模块"""
        try:
            self._logger.info("Initializing ObservabilityModule...")
            
            # 初始化结构化日志
            logging_config = self._config.get("structured_logging", {})
            if logging_config.get("enabled", False):
                self._structured_logger = StructuredLogger("enhanced", logging_config)
                self._logger.info("Structured logging initialized")
            
            # 初始化指标聚合器
            metrics_config = self._config.get("metrics_aggregation", {})
            if metrics_config.get("enabled", False):
                self._metrics_aggregator = MetricsAggregator(metrics_config)
                self._logger.info("Metrics aggregator initialized")
            
            # 初始化性能分析器
            profiling_config = self._config.get("performance_profiling", {})
            if profiling_config.get("enabled", False):
                self._performance_profiler = PerformanceProfiler(profiling_config)
                self._logger.info("Performance profiler initialized")
            
            self._status = ModuleStatus.LOADED
            self._logger.info("ObservabilityModule initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize ObservabilityModule: {e}")
            self._status = ModuleStatus.ERROR
            self._config["error_message"] = str(e)
            return False
    
    def cleanup(self) -> bool:
        """清理模块"""
        try:
            self._logger.info("Cleaning up ObservabilityModule...")
            
            if self._structured_logger:
                self._structured_logger.close()
                self._structured_logger = None
            
            if self._metrics_aggregator:
                self._metrics_aggregator.stop()
                self._metrics_aggregator = None
            
            if self._performance_profiler:
                self._performance_profiler.stop()
                self._performance_profiler = None
            
            self._status = ModuleStatus.UNLOADED
            self._logger.info("ObservabilityModule cleaned up successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup ObservabilityModule: {e}")
            return False
    
    def get_structured_logger(self, name: str) -> Optional[StructuredLogger]:
        """获取结构化日志记录器"""
        if not self._structured_logger:
            return None
        
        # 创建子日志记录器
        return StructuredLogger(name, self._config.get("structured_logging", {}))
    
    def get_metrics_aggregator(self) -> Optional[MetricsAggregator]:
        """获取指标聚合器"""
        return self._metrics_aggregator
    
    def get_performance_profiler(self) -> Optional[PerformanceProfiler]:
        """获取性能分析器"""
        return self._performance_profiler
    
    def record_metric(self, name: str, value: float, metric_type: str = "counter", tags: Dict[str, str] = None):
        """记录指标"""
        if not self._metrics_aggregator:
            return
        
        if metric_type == "counter":
            self._metrics_aggregator.increment_counter(name, value, tags)
        elif metric_type == "gauge":
            self._metrics_aggregator.set_gauge(name, value, tags)
        elif metric_type == "histogram":
            self._metrics_aggregator.record_histogram(name, value, tags)
        elif metric_type == "timer":
            self._metrics_aggregator.record_timer(name, value, tags)
    
    def profile_function(self, func_name: str, duration_ms: float, success: bool = True):
        """记录函数性能"""
        if self._performance_profiler:
            self._performance_profiler.profile_function(func_name, duration_ms, success)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        stats = {
            "module": self.get_info().to_dict(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self._metrics_aggregator:
            stats["metrics"] = self._metrics_aggregator.get_all_metrics()
        
        if self._performance_profiler:
            stats["performance"] = self._performance_profiler.get_all_stats()
        
        return stats