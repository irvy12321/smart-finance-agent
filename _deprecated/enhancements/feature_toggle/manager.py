"""
功能开关系统 - 配置文件驱动，支持环境变量覆盖
外挂模块，不影响现有系统
"""
import os
import yaml
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger("feature_toggle")


@dataclass
class FeatureToggle:
    """功能开关配置"""
    enabled: bool = False
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    env_override: Optional[str] = None  # 环境变量名


class FeatureToggleManager:
    """
    功能开关管理器
    - 配置文件驱动
    - 支持环境变量覆盖
    - 线程安全
    - 支持运行时动态修改
    """
    _instance: "FeatureToggleManager | None" = None
    _lock = threading.Lock()

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = None):
        if self._initialized:
            return
        
        self._config_path = config_path or self._find_config_path()
        self._features: Dict[str, FeatureToggle] = {}
        self._config: Dict[str, Any] = {}
        self._watchers: list[callable] = []
        self._feature_lock = threading.RLock()
        
        # 环境变量前缀
        self._env_prefix = "SFA_"
        
        # 加载配置
        self._load_config()
        self._initialized = True
        
        logger.info(f"FeatureToggleManager initialized with {len(self._features)} features")

    def _find_config_path(self) -> str:
        """查找配置文件路径"""
        # 按优先级查找
        possible_paths = [
            "enhancements/feature_toggle/config.yaml",
            "config/feature_toggle.yaml",
            "feature_toggle.yaml",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        # 如果找不到，返回默认路径
        return "enhancements/feature_toggle/config.yaml"

    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = Path(self._config_path)
            if not config_path.exists():
                logger.warning(f"Config file not found: {self._config_path}, using defaults")
                self._create_default_config()
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            # 解析功能开关
            self._parse_features()
            
            # 应用环境变量覆盖
            self._apply_env_overrides()
            
            logger.info(f"Loaded config from {self._config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置"""
        self._config = {
            "feature_toggle": {"enabled": True},
            "observability": {"enabled": False},
            "replay": {"enabled": False},
            "performance": {"enabled": False},
            "testing": {"enabled": False},
        }
        self._parse_features()

    def _parse_features(self):
        """解析配置文件中的功能开关"""
        self._features.clear()
        
        # 解析顶级功能模块
        for module_name, module_config in self._config.items():
            if isinstance(module_config, dict):
                enabled = module_config.get("enabled", False)
                description = module_config.get("description", f"{module_name} module")
                dependencies = module_config.get("dependencies", [])
                env_override = module_config.get("env_override")
                
                self._features[module_name] = FeatureToggle(
                    enabled=enabled,
                    description=description,
                    dependencies=dependencies,
                    env_override=env_override,
                )
                
                # 解析子功能
                self._parse_sub_features(module_name, module_config)

    def _parse_sub_features(self, parent_name: str, config: dict):
        """解析子功能开关"""
        for key, value in config.items():
            if key == "enabled" or key == "description":
                continue
            
            if isinstance(value, dict) and "enabled" in value:
                feature_name = f"{parent_name}.{key}"
                self._features[feature_name] = FeatureToggle(
                    enabled=value.get("enabled", False),
                    description=value.get("description", f"{feature_name} feature"),
                    dependencies=value.get("dependencies", []),
                    env_override=value.get("env_override"),
                )
                
                # 递归解析
                self._parse_sub_features(feature_name, value)

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        for feature_name, feature in self._features.items():
            # 检查特定功能的环境变量
            env_var = feature.env_override or f"{self._env_prefix}{feature_name.upper().replace('.', '_')}"
            env_value = os.getenv(env_var)
            
            if env_value is not None:
                # 解析布尔值
                if env_value.lower() in ("true", "1", "yes", "on"):
                    feature.enabled = True
                elif env_value.lower() in ("false", "0", "no", "off"):
                    feature.enabled = False
                else:
                    logger.warning(f"Invalid env value for {env_var}: {env_value}")
                
                logger.info(f"Feature {feature_name} overridden by env {env_var}={env_value}")

    def is_enabled(self, feature_name: str) -> bool:
        """检查功能是否启用"""
        with self._feature_lock:
            feature = self._features.get(feature_name)
            if feature is None:
                logger.warning(f"Unknown feature: {feature_name}")
                return False
            
            # 检查依赖
            if not self._check_dependencies(feature_name):
                return False
            
            return feature.enabled

    def _check_dependencies(self, feature_name: str) -> bool:
        """检查功能依赖是否满足"""
        feature = self._features.get(feature_name)
        if not feature or not feature.dependencies:
            return True
        
        for dep in feature.dependencies:
            if not self.is_enabled(dep):
                logger.debug(f"Feature {feature_name} disabled: dependency {dep} not met")
                return False
        
        return True

    def enable(self, feature_name: str) -> bool:
        """启用功能"""
        with self._feature_lock:
            if feature_name not in self._features:
                logger.error(f"Unknown feature: {feature_name}")
                return False
            
            # 检查依赖
            if not self._check_dependencies(feature_name):
                logger.error(f"Cannot enable {feature_name}: dependencies not met")
                return False
            
            old_state = self._features[feature_name].enabled
            self._features[feature_name].enabled = True
            
            if old_state != True:
                self._notify_watchers(feature_name, True)
                logger.info(f"Feature {feature_name} enabled")
            
            return True

    def disable(self, feature_name: str) -> bool:
        """禁用功能"""
        with self._feature_lock:
            if feature_name not in self._features:
                logger.error(f"Unknown feature: {feature_name}")
                return False
            
            # 检查是否有其他功能依赖此功能
            dependents = self._get_dependents(feature_name)
            if dependents:
                logger.error(f"Cannot disable {feature_name}: depended by {dependents}")
                return False
            
            old_state = self._features[feature_name].enabled
            self._features[feature_name].enabled = False
            
            if old_state != False:
                self._notify_watchers(feature_name, False)
                logger.info(f"Feature {feature_name} disabled")
            
            return True

    def _get_dependents(self, feature_name: str) -> list[str]:
        """获取依赖于指定功能的功能列表"""
        dependents = []
        for name, feature in self._features.items():
            if feature_name in feature.dependencies and feature.enabled:
                dependents.append(name)
        return dependents

    def get_all_features(self) -> Dict[str, Dict[str, Any]]:
        """获取所有功能开关状态"""
        with self._feature_lock:
            result = {}
            for name, feature in self._features.items():
                result[name] = {
                    "enabled": feature.enabled,
                    "description": feature.description,
                    "dependencies": feature.dependencies,
                    "env_override": feature.env_override,
                }
            return result

    def get_enabled_features(self) -> list[str]:
        """获取所有启用的功能"""
        with self._feature_lock:
            return [name for name, feature in self._features.items() if feature.enabled]

    def get_disabled_features(self) -> list[str]:
        """获取所有禁用的功能"""
        with self._feature_lock:
            return [name for name, feature in self._features.items() if not feature.enabled]

    def reload_config(self):
        """重新加载配置文件"""
        with self._feature_lock:
            logger.info("Reloading feature toggle config")
            self._load_config()

    def watch(self, callback: callable):
        """注册功能状态变更观察者"""
        with self._feature_lock:
            self._watchers.append(callback)

    def unwatch(self, callback: callable):
        """取消注册观察者"""
        with self._feature_lock:
            self._watchers = [w for w in self._watchers if w != callback]

    def _notify_watchers(self, feature_name: str, enabled: bool):
        """通知观察者功能状态变更"""
        for watcher in self._watchers:
            try:
                watcher(feature_name, enabled)
            except Exception as e:
                logger.error(f"Error in feature watcher: {e}")

    def export_config(self, output_path: str = None) -> str:
        """导出当前配置"""
        config = {
            "feature_toggle": {
                "enabled": True,
                "config_path": self._config_path,
                "env_prefix": self._env_prefix,
            }
        }
        
        # 重建配置结构
        for name, feature in self._features.items():
            parts = name.split(".")
            current = config
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[parts[-1]] = {
                "enabled": feature.enabled,
                "description": feature.description,
                "dependencies": feature.dependencies,
                "env_override": feature.env_override,
            }
        
        # 输出到文件或返回字符串
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            return output_path
        else:
            return yaml.dump(config, default_flow_style=False, allow_unicode=True)


# 便捷函数
_feature_manager: FeatureToggleManager = None


def get_feature_manager() -> FeatureToggleManager:
    """获取功能开关管理器实例"""
    global _feature_manager
    if _feature_manager is None:
        _feature_manager = FeatureToggleManager()
    return _feature_manager


def is_feature_enabled(feature_name: str) -> bool:
    """检查功能是否启用"""
    return get_feature_manager().is_enabled(feature_name)


def enable_feature(feature_name: str) -> bool:
    """启用功能"""
    return get_feature_manager().enable(feature_name)


def disable_feature(feature_name: str) -> bool:
    """禁用功能"""
    return get_feature_manager().disable(feature_name)


def feature_toggle(feature_name: str):
    """
    功能开关装饰器
    用法：
        @feature_toggle("observability.structured_logging")
        def my_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if is_feature_enabled(feature_name):
                return func(*args, **kwargs)
            else:
                logger.debug(f"Feature {feature_name} is disabled, skipping {func.__name__}")
                return None
        return wrapper
    return decorator


def conditional_import(feature_name: str, module_name: str):
    """
    条件导入装饰器
    用法：
        @conditional_import("observability", "enhancements.observability.metrics")
        def get_metrics():
            from enhancements.observability.metrics import MetricsCollector
            return MetricsCollector()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if is_feature_enabled(feature_name):
                try:
                    return func(*args, **kwargs)
                except ImportError as e:
                    logger.error(f"Failed to import {module_name}: {e}")
                    return None
            else:
                logger.debug(f"Feature {feature_name} is disabled, skipping import of {module_name}")
                return None
        return wrapper
    return decorator