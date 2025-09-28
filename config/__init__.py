#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🎛️ Пакет данных конфигурации (совместимость)."""

from src.config.paths import CONFIG_DIR, DATA_DIR, LOGS_DIR, get_config_path, ensure_config_structure
from src.config.regions import WIFE_REGIONS, calculate_region_priority, calculate_contact_priority

__all__ = [
    "CONFIG_DIR",
    "DATA_DIR",
    "LOGS_DIR",
    "get_config_path",
    "ensure_config_structure",
    "WIFE_REGIONS",
    "calculate_region_priority",
    "calculate_contact_priority",
]
