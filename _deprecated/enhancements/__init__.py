"""
Smart Finance Agent 增强系统
外挂模块，不影响现有核心架构
"""

from .base import (
    EnhancementModule,
    ModuleRegistry,
    ModuleLoader,
    ModuleStatus,
    ModuleInfo,
    get_module_registry,
    get_module_loader,
    register_module,
    get_module,
    initialize_all_modules,
    cleanup_all_modules,
)

from .manager import (
    EnhancementManager,
    get_enhancement_manager,
    initialize_enhancements,
    cleanup_enhancements,
    get_enhancement_status,
)

from .feature_toggle import (
    FeatureToggleManager,
    get_feature_manager,
    is_feature_enabled,
    enable_feature,
    disable_feature,
    feature_toggle,
    conditional_import,
)

__all__ = [
    # 基础架构
    "EnhancementModule",
    "ModuleRegistry",
    "ModuleLoader",
    "ModuleStatus",
    "ModuleInfo",
    "get_module_registry",
    "get_module_loader",
    "register_module",
    "get_module",
    "initialize_all_modules",
    "cleanup_all_modules",
    
    # 管理器
    "EnhancementManager",
    "get_enhancement_manager",
    "initialize_enhancements",
    "cleanup_enhancements",
    "get_enhancement_status",
    
    # 功能开关
    "FeatureToggleManager",
    "get_feature_manager",
    "is_feature_enabled",
    "enable_feature",
    "disable_feature",
    "feature_toggle",
    "conditional_import",
]