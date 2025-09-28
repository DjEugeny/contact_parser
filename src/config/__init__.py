#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""⚙️ Конфигурационный пакет Contact Parser."""

from .config_validator import ConfigValidator, ValidationResult
from .config_manager import (
    UnifiedConfigManager,
    LLMProviderConfig,
    ProcessingConfig,
    ExportConfig,
)
from .paths import (
    PROJECT_ROOT,
    CONFIG_DIR,
    DATA_DIR,
    LOGS_DIR,
    get_config_path,
    ensure_config_structure,
)
from .regions import (
    WIFE_REGIONS,
    calculate_region_priority,
    calculate_contact_priority,
)

__all__ = [
    "ConfigValidator",
    "ValidationResult",
    "UnifiedConfigManager",
    "LLMProviderConfig",
    "ProcessingConfig",
    "ExportConfig",
    "PROJECT_ROOT",
    "CONFIG_DIR",
    "DATA_DIR",
    "LOGS_DIR",
    "get_config_path",
    "ensure_config_structure",
    "WIFE_REGIONS",
    "calculate_region_priority",
    "calculate_contact_priority",
]
