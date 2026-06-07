"""
增强系统集成桥接器
无侵入式地连接增强模块和现有系统
"""
import threading
from typing import Any, Dict, Optional, Callable
from functools import wraps

from utils.logger import get_logger
from .base import EnhancementModule, ModuleStatus
from .feature_toggle import is_feature_enabled
from .manager import get_enhancement_manager

logger = get_logger("enhancement_bridge")


class EnhancementBridge:
    """
    增强系统桥接器
    提供无侵入式的集成点，连接增强模块和现有系统
    """
    _instance: "EnhancementBridge | None" = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._enhancement_manager = get_enhancement_manager()
        self._hooks: Dict[str, list[Callable]] = {}
        self._initialized = True
        
        logger.info("EnhancementBridge initialized")
    
    def register_hook(self, hook_name: str, callback: Callable):
        """注册钩子"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)
        logger.debug(f"Registered hook: {hook_name}")
    
    def unregister_hook(self, hook_name: str, callback: Callable):
        """取消注册钩子"""
        if hook_name in self._hooks:
            self._hooks[hook_name] = [h for h in self._hooks[hook_name] if h != callback]
    
    def execute_hooks(self, hook_name: str, *args, **kwargs):
        """执行钩子"""
        hooks = self._hooks.get(hook_name, [])
        for hook in hooks:
            try:
                hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing hook {hook_name}: {e}")
    
    def get_module(self, module_name: str) -> Optional[EnhancementModule]:
        """获取增强模块"""
        return self._enhancement_manager.get_module(module_name)
    
    def is_module_loaded(self, module_name: str) -> bool:
        """检查模块是否已加载"""
        module = self.get_module(module_name)
        return module is not None and module.status == ModuleStatus.LOADED
    
    def get_observability_module(self):
        """获取可观测性模块"""
        return self.get_module("observability")
    
    def get_replay_module(self):
        """获取回放模块"""
        return self.get_module("replay")
    
    def get_performance_module(self):
        """获取性能分析模块"""
        return self.get_module("performance")
    
    def get_testing_module(self):
        """获取测试增强模块"""
        return self.get_module("testing")


# 全局桥接器实例
_bridge: EnhancementBridge = None


def get_enhancement_bridge() -> EnhancementBridge:
    """获取增强系统桥接器实例"""
    global _bridge
    if _bridge is None:
        _bridge = EnhancementBridge()
    return _bridge


def enhancement_hook(hook_name: str):
    """
    增强钩子装饰器
    用于在现有函数中插入增强功能
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行前置钩子
            bridge = get_enhancement_bridge()
            bridge.execute_hooks(f"before_{hook_name}", *args, **kwargs)
            
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 执行后置钩子
            bridge.execute_hooks(f"after_{hook_name}", result, *args, **kwargs)
            
            return result
        return wrapper
    return decorator


def enhancement_async_hook(hook_name: str):
    """
    异步增强钩子装饰器
    用于在现有异步函数中插入增强功能
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行前置钩子
            bridge = get_enhancement_bridge()
            bridge.execute_hooks(f"before_{hook_name}", *args, **kwargs)
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 执行后置钩子
            bridge.execute_hooks(f"after_{hook_name}", result, *args, **kwargs)
            
            return result
        return wrapper
    return decorator


class InstrumentationProxy:
    """
    仪器化代理
    用于在不修改原始类的情况下添加增强功能
    """
    
    def __init__(self, target: Any, module_name: str = None):
        self._target = target
        self._module_name = module_name
        self._bridge = get_enhancement_bridge()
    
    def __getattr__(self, name: str):
        attr = getattr(self._target, name)
        
        if callable(attr):
            def instrumented_method(*args, **kwargs):
                # 检查功能开关
                if self._module_name and not is_feature_enabled(self._module_name):
                    return attr(*args, **kwargs)
                
                # 执行前置钩子
                hook_name = f"{self._target.__class__.__name__}.{name}"
                self._bridge.execute_hooks(f"before_{hook_name}", *args, **kwargs)
                
                # 执行原方法
                result = attr(*args, **kwargs)
                
                # 执行后置钩子
                self._bridge.execute_hooks(f"after_{hook_name}", result, *args, **kwargs)
                
                return result
            
            return instrumented_method
        
        return attr


class ObservabilityProxy(InstrumentationProxy):
    """可观测性代理"""
    
    def __init__(self, target: Any):
        super().__init__(target, "observability")


class ReplayProxy(InstrumentationProxy):
    """回放代理"""
    
    def __init__(self, target: Any):
        super().__init__(target, "replay")


class PerformanceProxy(InstrumentationProxy):
    """性能分析代理"""
    
    def __init__(self, target: Any):
        super().__init__(target, "performance")


# 便捷函数
def create_observability_proxy(target: Any) -> ObservabilityProxy:
    """创建可观测性代理"""
    return ObservabilityProxy(target)


def create_replay_proxy(target: Any) -> ReplayProxy:
    """创建回放代理"""
    return ReplayProxy(target)


def create_performance_proxy(target: Any) -> PerformanceProxy:
    """创建性能分析代理"""
    return PerformanceProxy(target)


def instrument_with_observability(func: Callable) -> Callable:
    """使用可观测性装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        bridge = get_enhancement_bridge()
        obs_module = bridge.get_observability_module()
        
        if obs_module and obs_module.status == ModuleStatus.LOADED:
            # 记录函数调用
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # 记录性能数据
                obs_module.profile_function(func.__name__, duration_ms, success=True)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                obs_module.profile_function(func.__name__, duration_ms, success=False)
                raise
        else:
            return func(*args, **kwargs)
    
    return wrapper


def instrument_with_replay(event_type: str) -> Callable:
    """使用回放装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            bridge = get_enhancement_bridge()
            replay_module = bridge.get_replay_module()
            
            if replay_module and replay_module.status == ModuleStatus.LOADED:
                # 记录事件
                replay_module.record_event(
                    event_type=event_type,
                    data={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def instrument_with_performance(func: Callable) -> Callable:
    """使用性能分析装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        bridge = get_enhancement_bridge()
        perf_module = bridge.get_performance_module()
        
        if perf_module and perf_module.status == ModuleStatus.LOADED:
            # 开始 CPU profiling
            perf_module.start_cpu_profiling()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # 停止 CPU profiling
                perf_module.stop_cpu_profiling()
        else:
            return func(*args, **kwargs)
    
    return wrapper