#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Сервисы - обертки над существующими модулями
Фаза 5+: Интеграция в новую архитектуру
"""

from .email_service import EmailService
from .ocr_service import OCRService
from .export_service import ExportService

__all__ = [
    'EmailService',
    'OCRService',
    'ExportService'
]
