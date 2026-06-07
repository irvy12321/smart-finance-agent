"""
增强系统集成测试
验证所有增强模块的集成和功能
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhancements import (
    get_enhancement_manager,
    initialize_enhancements,
    cleanup_enhancements,
    get_enhancement_status,
    is_feature_enabled,
    enable_feature,
    disable_feature,
)
from enhancements.bridge import get_enhancement_bridge


async def test_feature_toggle():
    """测试功能开关系统"""
    print("\n" + "="*60)
    print("Testing Feature Toggle System")
    print("="*60)
    
    # 测试功能开关
    print(f"Observability enabled: {is_feature_enabled('observability')}")
    print(f"Replay enabled: {is_feature_enabled('replay')}")
    print(f"Performance enabled: {is_feature_enabled('performance')}")
    print(f"Testing enabled: {is_feature_enabled('testing')}")
    
    # 启用功能
    enable_feature("observability")
    print(f"After enabling observability: {is_feature_enabled('observability')}")
    
    # 禁用功能
    disable_feature("observability")
    print(f"After disabling observability: {is_feature_enabled('observability')}")


async def test_enhancement_modules():
    """测试增强模块"""
    print("\n" + "="*60)
    print("Testing Enhancement Modules")
    print("="*60)
    
    # 初始化增强系统
    success = initialize_enhancements()
    print(f"Enhancement system initialized: {success}")
    
    # 获取状态
    status = get_enhancement_status()
    print(f"Enhancement status: {status}")
    
    # 获取桥接器
    bridge = get_enhancement_bridge()
    
    # 测试可观测性模块
    obs_module = bridge.get_observability_module()
    if obs_module:
        print(f"Observability module loaded: {obs_module.status}")
        
        # 测试结构化日志
        logger = obs_module.get_structured_logger("test")
        if logger:
            logger.info("Test structured log message")
        
        # 测试指标聚合器
        metrics = obs_module.get_metrics_aggregator()
        if metrics:
            metrics.increment_counter("test_counter", 1.0)
            metrics.set_gauge("test_gauge", 42.0)
            print(f"Metrics: {metrics.get_all_metrics()}")
    
    # 测试回放模块
    replay_module = bridge.get_replay_module()
    if replay_module:
        print(f"Replay module loaded: {replay_module.status}")
        
        # 测试事件记录
        from enhancements.replay import EventType
        replay_module.record_event(
            event_type=EventType.CUSTOM,
            data={"test": "data"},
        )
    
    # 测试性能分析模块
    perf_module = bridge.get_performance_module()
    if perf_module:
        print(f"Performance module loaded: {perf_module.status}")
        
        # 测试 LLM 调用记录
        perf_module.record_llm_call(
            model="openai/mimo-v2.5-pro",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1000,
            success=True,
        )
    
    # 测试测试增强模块
    testing_module = bridge.get_testing_module()
    if testing_module:
        print(f"Testing module loaded: {testing_module.status}")
        
        # 测试 fixture 创建
        fixture = testing_module.create_fixture(
            name="test_fixture",
            data={"key": "value"},
            description="Test fixture",
        )
        if fixture:
            print(f"Created fixture: {fixture.name}")


async def test_integration():
    """测试集成"""
    print("\n" + "="*60)
    print("Testing Integration")
    print("="*60)
    
    # 测试装饰器
    from enhancements.bridge import instrument_with_observability
    
    @instrument_with_observability
    def test_function():
        import time
        time.sleep(0.1)
        return "test_result"
    
    # 调用函数
    result = test_function()
    print(f"Function result: {result}")
    
    # 测试代理
    from enhancements.bridge import create_observability_proxy
    
    class TestClass:
        def test_method(self):
            return "proxy_result"
    
    proxy = create_observability_proxy(TestClass())
    result = proxy.test_method()
    print(f"Proxy result: {result}")


async def main():
    """主测试函数"""
    print("Enhancement System Integration Test")
    print("="*60)
    
    try:
        # 测试功能开关
        await test_feature_toggle()
        
        # 测试增强模块
        await test_enhancement_modules()
        
        # 测试集成
        await test_integration()
        
        print("\n" + "="*60)
        print("All tests completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        cleanup_enhancements()


if __name__ == "__main__":
    asyncio.run(main())