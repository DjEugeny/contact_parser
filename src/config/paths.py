#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🗺️ Утилиты для работы с путями конфигурации проекта."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR: Path = PROJECT_ROOT / "config"
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = DATA_DIR / "logs"


def get_config_path(*parts: str) -> Path:
    """🔍 Возвращает путь внутри папки `config`.

    Args:
        *parts: последовательность сегментов пути (например, "providers.json").

    Returns:
        Path: абсолютный путь до требуемого файла/директории конфигурации.
    """
    if not parts:
        return CONFIG_DIR
    return CONFIG_DIR.joinpath(*parts)


def ensure_config_structure() -> None:
    """🔧 Создаёт базовые директории (`config`, `data`, `logs`) при необходимости."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
