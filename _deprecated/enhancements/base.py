"""
外挂增强模块基础架构
定义所有增强模块的接口规范和基础类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum
import threading
from utils.logger import get_logger

logger = get_logger("enhancement_base")


class ModuleStatus(Enum):
    """模块状态枚举"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    status: ModuleStatus = ModuleStatus.UNLOADED
    error_message: Optional[str] = None


class EnhancementModule(ABC):
    """
    增强模块基类
    所有外挂增强模块必须继承此类
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._status = ModuleStatus.UNLOADED
        self._lock = threading.RLock()
        self._logger = get_logger(f"enhancement.{self.name}")
        
    @property
    @abstractmethod
    def name(self) -> str:
        """模块名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """模块版本"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """模块描述"""
        pass
    
    @property
    def status(self) -> ModuleStatus:
        """模块状态"""
        return self._status
    
    @property
    def config(self) -> Dict[str, Any]:
        """模块配置"""
        return self._config.copy()
    
    def get_info(self) -> ModuleInfo:
        """获取模块信息"""
        return ModuleInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self._config.get("author", ""),
            dependencies=self._config.get("dependencies", []),
            config_schema=self.get_config_schema(),
            status=self._status,
            error_message=self._config.get("error_message"),
        )
    
    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """获取配置模式（可选）"""
        return None
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化模块
        返回：True 表示成功，False 表示失败
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """
        清理模块资源
        返回：True 表示成功，False 表示失败
        """
        pass
    
    def reload(self, new_config: Dict[str, Any] = None) -> bool:
        """
        重新加载模块
        参数：new_config - 新的配置（可选）
        返回：True 表示成功，False 表示失败
        """
        with self._lock:
            try:
                # 清理现有资源
                if not self.cleanup():
                    self._logger.warning(f"Failed to cleanup module {self.name} during reload")
                
                # 更新配置
                if new_config is not None:
                    self._config.update(new_config)
                
                # 重新初始化
                return self.initialize()
                
            except Exception as e:
                self._logger.error(f"Failed to reload module {self.name}: {e}")
                self._status = ModuleStatus.ERROR
                self._config["error_message"] = str(e)
                return False
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证配置
        返回：(是否有效, 错误信息)
        """
        # 默认实现：接受任何配置
        return True, None
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "name": self.name,
            "version": self.version,
            "status": self._status.value,
            "error_message": self._config.get("error_message"),
        }


class ModuleRegistry:
    """
    模块注册表
    管理所有增强模块的注册和发现
    """
    _instance: "ModuleRegistry | None" = None
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
        
        self._modules: Dict[str, EnhancementModule] = {}
        self._module_lock = threading.RLock()
        self._initialized = True
        
        logger.info("ModuleRegistry initialized")
    
    def register(self, module: EnhancementModule) -> bool:
        """注册模块"""
        with self._module_lock:
            if module.name in self._modules:
                logger.warning(f"Module {module.name} already registered, replacing")
            
            self._modules[module.name] = module
            logger.info(f"Registered module: {module.name} v{module.version}")
            return True
    
    def unregister(self, module_name: str) -> bool:
        """取消注册模块"""
        with self._module_lock:
            if module_name not in self._modules:
                logger.warning(f"Module {module_name} not found")
                return False
            
            module = self._modules[module_name]
            if module.status == ModuleStatus.LOADED:
                if not module.cleanup():
                    logger.warning(f"Failed to cleanup module {module_name} during unregister")
            
            del self._modules[module_name]
            logger.info(f"Unregistered module: {module_name}")
            return True
    
    def get_module(self, module_name: str) -> Optional[EnhancementModule]:
        """获取模块"""
        with self._module_lock:
            return self._modules.get(module_name)
    
    def get_all_modules(self) -> Dict[str, EnhancementModule]:
        """获取所有模块"""
        with self._module_lock:
            return self._modules.copy()
    
    def get_loaded_modules(self) -> Dict[str, EnhancementModule]:
        """获取所有已加载的模块"""
        with self._module_lock:
            return {
                name: module for name, module in self._modules.items()
                if module.status == ModuleStatus.LOADED
            }
    
    def initialize_module(self, module_name: str) -> bool:
        """初始化模块"""
        with self._module_lock:
            module = self._modules.get(module_name)
            if not module:
                logger.error(f"Module {module_name} not found")
                return False
            
            if module.status == ModuleStatus.LOADED:
                logger.warning(f"Module {module_name} already loaded")
                return True
            
            try:
                module._status = ModuleStatus.LOADING
                success = module.initialize()
                
                if success:
                    module._status = ModuleStatus.LOADED
                    logger.info(f"Module {module_name} initialized successfully")
                else:
                    module._status = ModuleStatus.ERROR
                    logger.error(f"Failed to initialize module {module_name}")
                
                return success
                
            except Exception as e:
                module._status = ModuleStatus.ERROR
                module._config["error_message"] = str(e)
                logger.error(f"Exception during initialization of module {module_name}: {e}")
                return False
    
    def cleanup_module(self, module_name: str) -> bool:
        """清理模块"""
        with self._module_lock:
            module = self._modules.get(module_name)
            if not module:
                logger.error(f"Module {module_name} not found")
                return False
            
            if module.status != ModuleStatus.LOADED:
                logger.warning(f"Module {module_name} not loaded, status: {module.status}")
                return True
            
            try:
                success = module.cleanup()
                
                if success:
                    module._status = ModuleStatus.UNLOADED
                    logger.info(f"Module {module_name} cleaned up successfully")
                else:
                    logger.error(f"Failed to cleanup module {module_name}")
                
                return success
                
            except Exception as e:
                logger.error(f"Exception during cleanup of module {module_name}: {e}")
                return False
    
    def initialize_all(self) -> Dict[str, bool]:
        """初始化所有模块"""
        results = {}
        with self._module_lock:
            for name, module in self._modules.items():
                if module.status == ModuleStatus.UNLOADED:
                    results[name] = self.initialize_module(name)
                else:
                    results[name] = module.status == ModuleStatus.LOADED
        return results
    
    def cleanup_all(self) -> Dict[str, bool]:
        """清理所有模块"""
        results = {}
        with self._module_lock:
            for name, module in self._modules.items():
                if module.status == ModuleStatus.LOADED:
                    results[name] = self.cleanup_module(name)
                else:
                    results[name] = True
        return results
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        with self._module_lock:
            summary = {
                "total_modules": len(self._modules),
                "loaded_modules": 0,
                "error_modules": 0,
                "disabled_modules": 0,
                "modules": {},
            }
            
            for name, module in self._modules.items():
                status_info = module.get_status_info()
                summary["modules"][name] = status_info
                
                if module.status == ModuleStatus.LOADED:
                    summary["loaded_modules"] += 1
                elif module.status == ModuleStatus.ERROR:
                    summary["error_modules"] += 1
                elif module.status == ModuleStatus.DISABLED:
                    summary["disabled_modules"] += 1
            
            return summary


class ModuleLoader:
    """
    模块加载器
    负责动态加载和管理增强模块
    """
    
    def __init__(self, registry: ModuleRegistry = None):
        self._registry = registry or ModuleRegistry()
        self._logger = get_logger("module_loader")
    
    def load_module(self, module_class: type, config: Dict[str, Any] = None) -> bool:
        """加载模块类"""
        try:
            # 创建模块实例
            module = module_class(config)
            
            # 注册模块
            if not self._registry.register(module):
                return False
            
            # 初始化模块
            return self._registry.initialize_module(module.name)
            
        except Exception as e:
            self._logger.error(f"Failed to load module {module_class.__name__}: {e}")
            return False
    
    def load_from_config(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """从配置加载模块"""
        results = {}
        
        # 遍历配置中的模块
        for module_name, module_config in config.items():
            if isinstance(module_config, dict) and module_config.get("enabled", False):
                # 尝试动态导入模块类
                module_class = self._import_module_class(module_name)
                if module_class:
                    results[module_name] = self.load_module(module_class, module_config)
                else:
                    self._logger.error(f"Failed to import module class for {module_name}")
                    results[module_name] = False
        
        return results
    
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
            
            self._logger.error(f"No EnhancementModule subclass found in {module_path}")
            return None
            
        except ImportError as e:
            self._logger.error(f"Failed to import module {module_name}: {e}")
            return None
        except Exception as e:
            self._logger.error(f"Error importing module {module_name}: {e}")
            return None


# 便捷函数
_module_registry: ModuleRegistry = None
_module_loader: ModuleLoader = None


def get_module_registry() -> ModuleRegistry:
    """获取模块注册表实例"""
    global _module_registry
    if _module_registry is None:
        _module_registry = ModuleRegistry()
    return _module_registry


def get_module_loader() -> ModuleLoader:
    """获取模块加载器实例"""
    global _module_loader
    if _module_loader is None:
        _module_loader = ModuleLoader()
    return _module_loader


def register_module(module: EnhancementModule) -> bool:
    """注册模块"""
    return get_module_registry().register(module)


def get_module(module_name: str) -> Optional[EnhancementModule]:
    """获取模块"""
    return get_module_registry().get_module(module_name)


def initialize_all_modules() -> Dict[str, bool]:
    """初始化所有模块"""
    return get_module_registry().initialize_all()


def cleanup_all_modules() -> Dict[str, bool]:
    """清理所有模块"""
    return get_module_registry().cleanup_all()