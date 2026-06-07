"""
功能开关系统 - 外挂模块
配置文件驱动，支持环境变量覆盖，不影响现有系统
"""

from .manager import (
    FeatureToggleManager,
    get_feature_manager,
    is_feature_enabled,
    enable_feature,
    disable_feature,
    feature_toggle,
    conditional_import,
)

__all__ = [
    "FeatureToggleManager",
    "get_feature_manager",
    "is_feature_enabled",
    "enable_feature",
    "disable_feature",
    "feature_toggle",
    "conditional_import",
]