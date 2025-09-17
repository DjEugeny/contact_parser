#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ Конфигурация Contact Parser
Фаза 5: Архитектурная оптимизация
"""

# from .provider_manager_old import ProviderManager, ProviderManagerConfig  # Удален - заменен на UnifiedConfigManager
from .config_validator import ConfigValidator
from .config_manager import UnifiedConfigManager, LLMProviderConfig, ProcessingConfig, ExportConfig

__all__ = [
    'ProviderManager',
    'ProviderManagerConfig',
    'ConfigValidator',
    'UnifiedConfigManager',
    'LLMProviderConfig',
    'ProcessingConfig',
    'ExportConfig',
    'ValidationResult'
]
