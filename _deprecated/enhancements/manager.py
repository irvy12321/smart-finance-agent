"""
增强系统集成管理器
协调所有增强模块的加载、初始化和生命周期管理
"""
import threading
from typing import Any, Dict, Optional
from pathlib import Path
import yaml

from utils.logger import get_logger
from .base import (
    EnhancementModule,
    ModuleRegistry,
    ModuleLoader,
    ModuleStatus,
    get_module_registry,
    get_module_loader,
)
from .feature_toggle import get_feature_manager, is_feature_enabled

logger = get_logger("enhancement_manager")


class EnhancementManager:
    """
    增强系统管理器
    统一管理所有增强模块的生命周期
    """
    _instance: "EnhancementManager | None" = None
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
        self._config: Dict[str, Any] = {}
        self._registry = get_module_registry()
        self._loader = get_module_loader()
        self._feature_manager = get_feature_manager()
        
        # 加载配置
        self._load_config()
        
        # 初始化模块
        self._initialized = True
        
        logger.info("EnhancementManager initialized")
    
    def _find_config_path(self) -> str:
        """查找配置文件路径"""
        possible_paths = [
            "enhancements/config.yaml",
            "config/enhancements.yaml",
            "enhancements.yaml",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        return "enhancements/config.yaml"
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = Path(self._config_path)
            if not config_path.exists():
                logger.warning(f"Config file not found: {self._config_path}")
                self._create_default_config()
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            logger.info(f"Loaded enhancement config from {self._config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load enhancement config: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self._config = {
            "auto_load_on_startup": True,
            "load_order": [
                "feature_toggle",
                "observability",
                "performance",
                "replay",
                "testing",
            ],
            "modules": {},
        }
    
    def initialize(self) -> bool:
        """初始化增强系统"""
        try:
            logger.info("Initializing enhancement system...")
            
            # 检查功能开关系统是否启用
            if not is_feature_enabled("feature_toggle"):
                logger.info("Feature toggle system is disabled, skipping enhancement initialization")
                return True
            
            # 按顺序加载模块
            load_order = self._config.get("load_order", [])
            modules_config = self._config.get("modules", {})
            
            success_count = 0
            total_count = 0
            
            for module_name in load_order:
                if module_name == "feature_toggle":
                    continue  # 功能开关系统已经初始化
                
                module_config = modules_config.get(module_name, {})
                
                # 检查功能开关
                if not is_feature_enabled(module_name):
                    logger.info(f"Module {module_name} is disabled by feature toggle")
                    continue
                
                total_count += 1
                
                # 尝试加载模块
                if self._load_module(module_name, module_config):
                    success_count += 1
                else:
                    logger.warning(f"Failed to load module {module_name}")
            
            logger.info(f"Enhancement system initialized: {success_count}/{total_count} modules loaded")
            
            # 如果配置了自动加载，初始化所有已注册的模块
            if self._config.get("auto_load_on_startup", True):
                self._registry.initialize_all()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize enhancement system: {e}")
            return False
    
    def _load_module(self, module_name: str, module_config: Dict[str, Any]) -> bool:
        """加载单个模块"""
        try:
            # 动态导入模块类
            module_class = self._import_module_class(module_name)
            if not module_class:
                return False
            
            # 加载模块
            return self._loader.load_module(module_class, module_config)
            
        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return False
    
    def _import_module_class(self, module_name: str) -> Optional[type]:
        """动态导入模块类"""
        try:
            # 根据模块名推断模块路径
            module_path = f"enhancements.{module_name}.module"
            
            # 动态导入
            import importlib
            module = importlib.import_module(module_path)
            
            # 查找 EnhancementModule 子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, EnhancementModule) and 
                    attr != EnhancementModule):
                    return attr
            
            logger.error(f"No EnhancementModule subclass found in {module_path}")
            return None
            
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return None
    
    def get_module(self, module_name: str) -> Optional[EnhancementModule]:
        """获取模块实例"""
        return self._registry.get_module(module_name)
    
    def get_all_modules(self) -> Dict[str, EnhancementModule]:
        """获取所有模块"""
        return self._registry.get_all_modules()
    
    def get_loaded_modules(self) -> Dict[str, EnhancementModule]:
        """获取所有已加载的模块"""
        return self._registry.get_loaded_modules()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        return self._registry.get_status_summary()
    
    def reload_module(self, module_name: str, new_config: Dict[str, Any] = None) -> bool:
        """重新加载模块"""
        module = self._registry.get_module(module_name)
        if not module:
            logger.error(f"Module {module_name} not found")
            return False
        
        return module.reload(new_config)
    
    def reload_all(self) -> Dict[str, bool]:
        """重新加载所有模块"""
        results = {}
        for name, module in self._registry.get_all_modules().items():
            results[name] = module.reload()
        return results
    
    def cleanup(self) -> bool:
        """清理增强系统"""
        try:
            logger.info("Cleaning up enhancement system...")
            
            # 清理所有模块
            results = self._registry.cleanup_all()
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Enhancement system cleaned up: {success_count}/{total_count} modules cleaned")
            
            return success_count == total_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup enhancement system: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self._config.update(new_config)
    
    def export_status(self, output_path: str = None) -> str:
        """导出状态信息"""
        import json
        
        status = {
            "enhancement_system": {
                "config_path": self._config_path,
                "initialized": self._initialized,
            },
            "modules": self.get_status_summary(),
            "feature_toggles": self._feature_manager.get_all_features(),
        }
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            return output_path
        else:
            return json.dumps(status, indent=2, ensure_ascii=False)


# 便捷函数
_enhancement_manager: EnhancementManager = None


def get_enhancement_manager() -> EnhancementManager:
    """获取增强系统管理器实例"""
    global _enhancement_manager
    if _enhancement_manager is None:
        _enhancement_manager = EnhancementManager()
    return _enhancement_manager


def initialize_enhancements() -> bool:
    """初始化增强系统"""
    return get_enhancement_manager().initialize()


def cleanup_enhancements() -> bool:
    """清理增强系统"""
    return get_enhancement_manager().cleanup()


def get_enhancement_status() -> Dict[str, Any]:
    """获取增强系统状态"""
    return get_enhancement_manager().get_status_summary()