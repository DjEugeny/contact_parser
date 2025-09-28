#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🪄 Совместимость: переадресация на `src.config.regions`."""

from src.config.regions import (  # noqa: F401
    WIFE_REGIONS,
    calculate_region_priority,
    calculate_contact_priority,
)

__all__ = [
    "WIFE_REGIONS",
    "calculate_region_priority",
    "calculate_contact_priority",
]
