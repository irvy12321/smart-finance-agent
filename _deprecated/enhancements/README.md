# Smart Finance Agent 增强系统使用指南

## 概述

增强系统是 Smart Finance Agent 的外挂模块，提供以下功能：

1. **功能开关系统** - 配置文件驱动，支持环境变量覆盖
2. **可观测性模块** - 结构化日志、指标聚合、性能分析
3. **回放系统** - 事件记录、本地JSON存储、确定性回放
4. **性能分析模块** - CPU profiling、网络I/O分析、LLM调用分析
5. **测试增强工具** - fixtures、mocks、测试数据管理

所有功能都是可选的，不影响现有核心架构。

## 快速开始

### 1. 启用增强系统

在 `enhancements/config.yaml` 中启用所需功能：

```yaml
# 启用功能开关系统
feature_toggle:
  enabled: true

# 启用可观测性模块
observability:
  enabled: true
  structured_logging:
    enabled: true
  metrics_aggregation:
    enabled: true
```

### 2. 使用环境变量覆盖

所有功能都可以通过环境变量覆盖，环境变量前缀为 `SFA_`：

```bash
# 启用可观测性模块
export SFA_OBSERVABILITY_ENABLED=true

# 启用结构化日志
export SFA_OBSERVABILITY_STRUCTURED_LOGGING_ENABLED=true
```

### 3. 在代码中使用

```python
from enhancements import (
    get_enhancement_manager,
    initialize_enhancements,
    is_feature_enabled,
)
from enhancements.bridge import get_enhancement_bridge

# 初始化增强系统
initialize_enhancements()

# 检查功能是否启用
if is_feature_enabled("observability"):
    bridge = get_enhancement_bridge()
    obs_module = bridge.get_observability_module()
    
    # 使用结构化日志
    logger = obs_module.get_structured_logger("my_module")
    logger.info("Hello from enhanced logging!")
    
    # 记录指标
    metrics = obs_module.get_metrics_aggregator()
    metrics.increment_counter("my_counter", 1.0)
```

## 功能开关系统

### 配置文件

功能开关配置文件位于 `enhancements/feature_toggle/config.yaml`：

```yaml
feature_toggle:
  enabled: true
  config_path: "enhancements/feature_toggle/config.yaml"
  env_prefix: "SFA_"
  log_changes: true

observability:
  enabled: false
  structured_logging:
    enabled: false
```

### 使用装饰器

```python
from enhancements import feature_toggle

@feature_toggle("observability.structured_logging")
def my_function():
    # 只有当功能启用时才会执行
    pass
```

### 动态开关

```python
from enhancements import enable_feature, disable_feature

# 启用功能
enable_feature("observability")

# 禁用功能
disable_feature("observability")
```

## 可观测性模块

### 结构化日志

```python
from enhancements.observability import StructuredLogger

logger = StructuredLogger("my_module", {
    "format": "json",
    "include_trace_id": True,
    "output_path": "output/logs/my_module.json",
})

logger.info("User logged in", user_id="123", ip="192.168.1.1")
logger.error("Database connection failed", error="timeout")
```

### 指标聚合

```python
from enhancements.observability import MetricsAggregator

metrics = MetricsAggregator({
    "export_interval_seconds": 60,
    "export_format": "json",
    "export_path": "output/metrics/metrics.json",
})

# 计数器
metrics.increment_counter("requests", 1.0, {"method": "GET", "path": "/api"})

# 仪表
metrics.set_gauge("queue_size", 42.0)

# 直方图
metrics.record_histogram("response_time", 150.0, {"endpoint": "/api"})

# 计时器
metrics.record_timer("db_query", 50.0, {"query": "SELECT * FROM users"})
```

### 性能分析

```python
from enhancements.observability import PerformanceProfiler

profiler = PerformanceProfiler({
    "memory_profiling": True,
    "snapshot_interval_seconds": 30,
})

# 记录函数性能
profiler.profile_function("my_function", 150.0, success=True)

# 获取统计信息
stats = profiler.get_all_stats()
print(stats)
```

## 回放系统

### 事件记录

```python
from enhancements.replay import ReplayModule, EventType

replay_module = ReplayModule({
    "recording": {
        "enabled": True,
        "storage_path": "output/replay_recordings",
    },
})

# 开始记录
session_id = replay_module.start_recording(
    trace_id="trace_123",
    query="分析苹果公司股票",
)

# 记录事件
replay_module.record_event(
    event_type=EventType.TASK_START,
    data={"task_id": "task_1", "tool": "crawler"},
)

# 停止记录
session = replay_module.stop_recording()
```

### 回放播放

```python
from enhancements.replay import ReplayPlayer

player = ReplayPlayer({
    "deterministic_mode": False,
    "speed_factor": 2.0,  # 2倍速
})

# 加载会话
player.load_from_file("output/replay_recordings/replay_20240101_120000_abc123.json")

# 设置回调
def on_event(event):
    print(f"Event: {event.event_type} - {event.data}")

player.set_callbacks(on_event=on_event)

# 开始播放
player.play()
```

## 性能分析模块

### CPU Profiling

```python
from enhancements.performance import PerformanceModule

perf_module = PerformanceModule({
    "cpu_profiling": {
        "enabled": True,
        "sampling_rate_hz": 100,
        "output_format": "snakeviz",
    },
})

# 开始 profiling
perf_module.start_cpu_profiling()

# 执行代码
for i in range(1000):
    _ = i * i

# 停止 profiling
profile = perf_module.stop_cpu_profiling()
profile.print_stats()
```

### 网络 I/O 分析

```python
from enhancements.performance import NetworkProfiler

network_profiler = NetworkProfiler({
    "track_requests": True,
})

# 记录请求
request_id = network_profiler.start_request("GET", "https://api.example.com/data")
network_profiler.end_request(request_id, status_code=200, response_size_bytes=1024)

# 获取统计信息
stats = network_profiler.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Error rate: {stats['error_rate']:.2f}%")
```

### LLM 调用分析

```python
from enhancements.performance import LLMProfiler

llm_profiler = LLMProfiler({
    "track_token_usage": True,
    "track_costs": True,
    "pricing": {
        "openai/mimo-v2.5-pro": {"input": 0.002, "output": 0.006},
    },
})

# 记录 LLM 调用
call_id = llm_profiler.start_call("openai/mimo-v2.5-pro")
llm_profiler.end_call(call_id, prompt_tokens=100, completion_tokens=50, success=True)

# 获取统计信息
stats = llm_profiler.get_stats()
print(f"Total tokens: {stats['total_tokens']}")
print(f"Total cost: ${stats['total_cost_usd']:.4f}")
```

## 测试增强工具

### Fixtures

```python
from enhancements.testing import TestingModule

testing_module = TestingModule({
    "fixtures": {
        "enabled": True,
        "fixtures_path": "tests/fixtures",
    },
})

# 创建 fixture
fixture = testing_module.create_fixture(
    name="user_data",
    data={"id": 1, "name": "John", "email": "john@example.com"},
    description="Test user data",
)

# 保存 fixture
testing_module.get_fixture_manager().save_fixture("user_data", format="json")

# 加载 fixture
loaded_fixture = testing_module.get_fixture("user_data")
print(loaded_fixture.data)
```

### Mocks

```python
from enhancements.testing import MockManager, MockConfig

mock_manager = MockManager()

# 创建 mock
mock_config = MockConfig(
    target="database.query",
    return_value=[{"id": 1, "name": "John"}],
)

mock = mock_manager.create_mock("db_query_mock", mock_config)

# 使用 mock
result = mock("SELECT * FROM users")
print(result)  # [{"id": 1, "name": "John"}]
```

### 测试数据生成

```python
from enhancements.testing import TestDataGenerator

generator = TestDataGenerator()

# 注册模板
generator.register_template("user", {
    "id": "{{auto_increment}}",
    "name": "{{random_name}}",
    "email": "{{random_email}}",
    "created_at": "{{current_timestamp}}",
})

# 生成数据
users = generator.generate_batch("user", count=10)
print(users)
```

## 集成到现有系统

### 使用装饰器

```python
from enhancements.bridge import (
    instrument_with_observability,
    instrument_with_replay,
    instrument_with_performance,
)

@instrument_with_observability
def my_function():
    pass

@instrument_with_replay("task_start")
def process_task(task_id):
    pass

@instrument_with_performance
def cpu_intensive_function():
    pass
```

### 使用代理

```python
from enhancements.bridge import (
    create_observability_proxy,
    create_replay_proxy,
    create_performance_proxy,
)

class MyService:
    def process(self):
        pass

# 创建代理
service = MyService()
observed_service = create_observability_proxy(service)

# 使用代理
observed_service.process()  # 自动记录性能数据
```

## 测试

运行增强系统集成测试：

```bash
python tests/test_enhancements.py
```

## 配置参考

### 环境变量

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `SFA_FEATURE_TOGGLE_ENABLED` | 功能开关系统 | `true` |
| `SFA_OBSERVABILITY_ENABLED` | 可观测性模块 | `false` |
| `SFA_REPLAY_ENABLED` | 回放系统 | `false` |
| `SFA_PERFORMANCE_ENABLED` | 性能分析模块 | `false` |
| `SFA_TESTING_ENABLED` | 测试增强模块 | `false` |

### 配置文件

- `enhancements/config.yaml` - 主配置文件
- `enhancements/feature_toggle/config.yaml` - 功能开关配置
- `enhancements/observability/config.yaml` - 可观测性配置
- `enhancements/replay/config.yaml` - 回放系统配置
- `enhancements/performance/config.yaml` - 性能分析配置
- `enhancements/testing/config.yaml` - 测试增强配置

## 目录结构

```
enhancements/
├── __init__.py
├── base.py              # 基础架构和接口
├── bridge.py            # 集成桥接器
├── config.yaml          # 主配置文件
├── manager.py           # 增强系统管理器
├── feature_toggle/      # 功能开关系统
├── observability/       # 可观测性模块
├── replay/              # 回放系统
├── performance/         # 性能分析模块
└── testing/             # 测试增强模块
```

## 最佳实践

1. **渐进式启用** - 一次只启用一个模块，确保系统稳定
2. **环境变量优先** - 使用环境变量覆盖配置文件，便于部署
3. **监控资源使用** - 性能分析模块会消耗额外资源，生产环境谨慎使用
4. **定期清理** - 定期清理回放记录和性能数据，避免磁盘空间不足
5. **测试覆盖** - 为增强功能编写测试，确保集成正确性