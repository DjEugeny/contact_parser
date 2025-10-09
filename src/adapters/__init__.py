#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптеры для обеспечения совместимости с новым реестром вложений
"""

from .ocr_processor_adapter import OCRProcessorAdapter
from .file_tokens_adapter import FileTokensAdapter
from .contact_phone_adapter import ContactPhoneAdapter

__all__ = [
    "OCRProcessorAdapter",
    "FileTokensAdapter", 
    "ContactPhoneAdapter"
]