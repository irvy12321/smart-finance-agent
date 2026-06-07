"""
测试增强工具
提供 fixtures、mocks、测试数据管理等功能
外挂模块，不影响现有系统
"""
import json
import yaml
import shutil
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from utils.logger import get_logger
from ..base import EnhancementModule, ModuleStatus
from ..feature_toggle import is_feature_enabled


@dataclass
class Fixture:
    """测试夹具"""
    name: str
    description: str
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fixture":
        """从字典创建"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Fixture":
        """从 JSON 字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class FixtureManager:
    """
    测试夹具管理器
    支持加载、保存、管理测试夹具
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 配置
        self._fixtures_path = Path(self._config.get("fixtures_path", "tests/fixtures"))
        self._auto_load = self._config.get("auto_load", True)
        
        # 夹具存储
        self._fixtures: Dict[str, Fixture] = {}
        self._fixture_factories: Dict[str, Callable[[], Any]] = {}
        
        # 确保目录存在
        self._fixtures_path.mkdir(parents=True, exist_ok=True)
        
        # 自动加载夹具
        if self._auto_load:
            self._load_fixtures_from_disk()
        
        self._logger = get_logger("fixture_manager")
    
    def _load_fixtures_from_disk(self):
        """从磁盘加载夹具"""
        try:
            for filepath in self._fixtures_path.glob("*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    fixture = Fixture.from_dict(data)
                    self._fixtures[fixture.name] = fixture
                    
                except Exception as e:
                    self._logger.warning(f"Failed to load fixture from {filepath}: {e}")
            
            for filepath in self._fixtures_path.glob("*.yaml"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    
                    fixture = Fixture.from_dict(data)
                    self._fixtures[fixture.name] = fixture
                    
                except Exception as e:
                    self._logger.warning(f"Failed to load fixture from {filepath}: {e}")
            
            self._logger.info(f"Loaded {len(self._fixtures)} fixtures from disk")
            
        except Exception as e:
            self._logger.error(f"Failed to load fixtures from disk: {e}")
    
    def get_fixture(self, name: str) -> Optional[Fixture]:
        """获取夹具"""
        with self._lock:
            # 首先检查内存中的夹具
            if name in self._fixtures:
                return self._fixtures[name]
            
            # 检查是否有工厂函数
            if name in self._fixture_factories:
                try:
                    data = self._fixture_factories[name]()
                    fixture = Fixture(
                        name=name,
                        description=f"Generated fixture: {name}",
                        data=data,
                    )
                    self._fixtures[name] = fixture
                    return fixture
                except Exception as e:
                    self._logger.error(f"Failed to create fixture {name}: {e}")
            
            return None
    
    def create_fixture(self, name: str, data: Any, description: str = "", metadata: Dict[str, Any] = None) -> Fixture:
        """创建夹具"""
        with self._lock:
            fixture = Fixture(
                name=name,
                description=description,
                data=data,
                metadata=metadata or {},
            )
            
            self._fixtures[name] = fixture
            self._logger.info(f"Created fixture: {name}")
            
            return fixture
    
    def save_fixture(self, name: str, format: str = "json"):
        """保存夹具到磁盘"""
        with self._lock:
            fixture = self._fixtures.get(name)
            if not fixture:
                self._logger.error(f"Fixture {name} not found")
                return False
            
            try:
                if format == "json":
                    filepath = self._fixtures_path / f"{name}.json"
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(fixture.to_dict(), f, indent=2, ensure_ascii=False)
                elif format == "yaml":
                    filepath = self._fixtures_path / f"{name}.yaml"
                    with open(filepath, 'w', encoding='utf-8') as f:
                        yaml.dump(fixture.to_dict(), f, default_flow_style=False, allow_unicode=True)
                else:
                    self._logger.error(f"Unsupported format: {format}")
                    return False
                
                self._logger.info(f"Saved fixture {name} to {filepath}")
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to save fixture {name}: {e}")
                return False
    
    def delete_fixture(self, name: str, delete_from_disk: bool = False):
        """删除夹具"""
        with self._lock:
            if name in self._fixtures:
                del self._fixtures[name]
                self._logger.info(f"Deleted fixture: {name}")
            
            if delete_from_disk:
                # 删除磁盘上的文件
                for ext in [".json", ".yaml"]:
                    filepath = self._fixtures_path / f"{name}{ext}"
                    if filepath.exists():
                        filepath.unlink()
                        self._logger.info(f"Deleted fixture file: {filepath}")
    
    def list_fixtures(self) -> List[Dict[str, Any]]:
        """列出所有夹具"""
        with self._lock:
            return [
                {
                    "name": fixture.name,
                    "description": fixture.description,
                    "created_at": fixture.created_at,
                    "metadata": fixture.metadata,
                }
                for fixture in self._fixtures.values()
            ]
    
    def register_factory(self, name: str, factory: Callable[[], Any]):
        """注册夹具工厂函数"""
        with self._lock:
            self._fixture_factories[name] = factory
            self._logger.info(f"Registered fixture factory: {name}")
    
    def unregister_factory(self, name: str):
        """取消注册夹具工厂函数"""
        with self._lock:
            if name in self._fixture_factories:
                del self._fixture_factories[name]
                self._logger.info(f"Unregistered fixture factory: {name}")
    
    def clear(self):
        """清除所有夹具"""
        with self._lock:
            self._fixtures.clear()
            self._fixture_factories.clear()


@dataclass
class MockConfig:
    """Mock 配置"""
    target: str
    return_value: Any = None
    side_effect: Optional[Callable] = None
    spec: Optional[type] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockManager:
    """
    Mock 管理器
    支持创建和管理测试 Mock
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 配置
        self._auto_mock_external = self._config.get("auto_mock_external", True)
        self._mock_llm_responses = self._config.get("mock_llm_responses", False)
        
        # Mock 存储
        self._mock_configs: Dict[str, MockConfig] = {}
        self._active_mocks: Dict[str, Any] = {}
        
        self._logger = get_logger("mock_manager")
    
    def create_mock(self, name: str, config: MockConfig) -> Any:
        """创建 Mock"""
        try:
            from unittest.mock import MagicMock, AsyncMock
            
            # 创建 Mock 对象
            if config.spec:
                mock = MagicMock(spec=config.spec)
            else:
                mock = MagicMock()
            
            # 配置返回值
            if config.return_value is not None:
                mock.return_value = config.return_value
            
            # 配置副作用
            if config.side_effect:
                mock.side_effect = config.side_effect
            
            with self._lock:
                self._mock_configs[name] = config
                self._active_mocks[name] = mock
            
            self._logger.info(f"Created mock: {name}")
            return mock
            
        except Exception as e:
            self._logger.error(f"Failed to create mock {name}: {e}")
            return None
    
    def create_async_mock(self, name: str, config: MockConfig) -> Any:
        """创建异步 Mock"""
        try:
            from unittest.mock import AsyncMock
            
            # 创建异步 Mock 对象
            if config.spec:
                mock = AsyncMock(spec=config.spec)
            else:
                mock = AsyncMock()
            
            # 配置返回值
            if config.return_value is not None:
                mock.return_value = config.return_value
            
            # 配置副作用
            if config.side_effect:
                mock.side_effect = config.side_effect
            
            with self._lock:
                self._mock_configs[name] = config
                self._active_mocks[name] = mock
            
            self._logger.info(f"Created async mock: {name}")
            return mock
            
        except Exception as e:
            self._logger.error(f"Failed to create async mock {name}: {e}")
            return None
    
    def get_mock(self, name: str) -> Optional[Any]:
        """获取 Mock"""
        with self._lock:
            return self._active_mocks.get(name)
    
    def get_mock_config(self, name: str) -> Optional[MockConfig]:
        """获取 Mock 配置"""
        with self._lock:
            return self._mock_configs.get(name)
    
    def delete_mock(self, name: str):
        """删除 Mock"""
        with self._lock:
            if name in self._active_mocks:
                del self._active_mocks[name]
            if name in self._mock_configs:
                del self._mock_configs[name]
            self._logger.info(f"Deleted mock: {name}")
    
    def list_mocks(self) -> List[Dict[str, Any]]:
        """列出所有 Mock"""
        with self._lock:
            return [
                {
                    "name": name,
                    "target": config.target,
                    "has_return_value": config.return_value is not None,
                    "has_side_effect": config.side_effect is not None,
                    "metadata": config.metadata,
                }
                for name, config in self._mock_configs.items()
            ]
    
    def clear(self):
        """清除所有 Mock"""
        with self._lock:
            self._mock_configs.clear()
            self._active_mocks.clear()
    
    @contextmanager
    def mock_context(self, name: str, config: MockConfig):
        """Mock 上下文管理器"""
        mock = self.create_mock(name, config)
        try:
            yield mock
        finally:
            self.delete_mock(name)


class TestDataGenerator:
    """
    测试数据生成器
    支持生成各种测试数据
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._lock = threading.Lock()
        
        # 数据模板
        self._templates: Dict[str, Dict[str, Any]] = {}
        
        self._logger = get_logger("test_data_generator")
    
    def register_template(self, name: str, template: Dict[str, Any]):
        """注册数据模板"""
        with self._lock:
            self._templates[name] = template
            self._logger.info(f"Registered template: {name}")
    
    def generate(self, template_name: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """根据模板生成数据"""
        with self._lock:
            template = self._templates.get(template_name)
            if not template:
                self._logger.error(f"Template {template_name} not found")
                return {}
            
            # 深拷贝模板
            import copy
            data = copy.deepcopy(template)
            
            # 应用覆盖
            if overrides:
                self._apply_overrides(data, overrides)
            
            return data
    
    def _apply_overrides(self, data: Dict[str, Any], overrides: Dict[str, Any]):
        """应用覆盖"""
        for key, value in overrides.items():
            if isinstance(value, dict) and key in data and isinstance(data[key], dict):
                self._apply_overrides(data[key], value)
            else:
                data[key] = value
    
    def generate_batch(self, template_name: str, count: int, overrides_list: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """批量生成数据"""
        results = []
        
        for i in range(count):
            overrides = overrides_list[i] if overrides_list and i < len(overrides_list) else {}
            data = self.generate(template_name, overrides)
            results.append(data)
        
        return results
    
    def list_templates(self) -> List[str]:
        """列出所有模板"""
        with self._lock:
            return list(self._templates.keys())
    
    def clear(self):
        """清除所有模板"""
        with self._lock:
            self._templates.clear()


class TestingModule(EnhancementModule):
    """
    测试增强模块
    集成 fixtures、mocks、测试数据管理
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        self._fixture_manager = None
        self._mock_manager = None
        self._data_generator = None
    
    @property
    def name(self) -> str:
        return "testing"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Testing enhancement with fixtures, mocks, and test data management"
    
    def initialize(self) -> bool:
        """初始化模块"""
        try:
            self._logger.info("Initializing TestingModule...")
            
            # 初始化 fixture 管理器
            fixtures_config = self._config.get("fixtures", {})
            if fixtures_config.get("enabled", False):
                self._fixture_manager = FixtureManager(fixtures_config)
                self._logger.info("Fixture manager initialized")
            
            # 初始化 mock 管理器
            mocks_config = self._config.get("mocks", {})
            if mocks_config.get("enabled", False):
                self._mock_manager = MockManager(mocks_config)
                self._logger.info("Mock manager initialized")
            
            # 初始化数据生成器
            data_config = self._config.get("data_management", {})
            if data_config.get("enabled", False):
                self._data_generator = TestDataGenerator(data_config)
                self._logger.info("Test data generator initialized")
            
            self._status = ModuleStatus.LOADED
            self._logger.info("TestingModule initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize TestingModule: {e}")
            self._status = ModuleStatus.ERROR
            self._config["error_message"] = str(e)
            return False
    
    def cleanup(self) -> bool:
        """清理模块"""
        try:
            self._logger.info("Cleaning up TestingModule...")
            
            if self._fixture_manager:
                self._fixture_manager.clear()
                self._fixture_manager = None
            
            if self._mock_manager:
                self._mock_manager.clear()
                self._mock_manager = None
            
            if self._data_generator:
                self._data_generator.clear()
                self._data_generator = None
            
            self._status = ModuleStatus.UNLOADED
            self._logger.info("TestingModule cleaned up successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup TestingModule: {e}")
            return False
    
    def get_fixture_manager(self) -> Optional[FixtureManager]:
        """获取 fixture 管理器"""
        return self._fixture_manager
    
    def get_mock_manager(self) -> Optional[MockManager]:
        """获取 mock 管理器"""
        return self._mock_manager
    
    def get_data_generator(self) -> Optional[TestDataGenerator]:
        """获取数据生成器"""
        return self._data_generator
    
    def get_fixture(self, name: str) -> Optional[Fixture]:
        """获取 fixture"""
        if self._fixture_manager:
            return self._fixture_manager.get_fixture(name)
        return None
    
    def create_fixture(self, name: str, data: Any, description: str = "", metadata: Dict[str, Any] = None) -> Optional[Fixture]:
        """创建 fixture"""
        if self._fixture_manager:
            return self._fixture_manager.create_fixture(name, data, description, metadata)
        return None
    
    def create_mock(self, name: str, target: str, return_value: Any = None, side_effect: Callable = None) -> Optional[Any]:
        """创建 mock"""
        if self._mock_manager:
            config = MockConfig(
                target=target,
                return_value=return_value,
                side_effect=side_effect,
            )
            return self._mock_manager.create_mock(name, config)
        return None
    
    def generate_test_data(self, template_name: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成测试数据"""
        if self._data_generator:
            return self._data_generator.generate(template_name, overrides)
        return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        stats = {
            "module": self.get_info().to_dict(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self._fixture_manager:
            stats["fixtures"] = {
                "count": len(self._fixture_manager.list_fixtures()),
                "fixtures": self._fixture_manager.list_fixtures(),
            }
        
        if self._mock_manager:
            stats["mocks"] = {
                "count": len(self._mock_manager.list_mocks()),
                "mocks": self._mock_manager.list_mocks(),
            }
        
        if self._data_generator:
            stats["templates"] = {
                "count": len(self._data_generator.list_templates()),
                "templates": self._data_generator.list_templates(),
            }
        
        return stats