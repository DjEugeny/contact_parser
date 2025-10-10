#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 Утилита для улучшенного логирования ошибок обработки
Задача 10.1: Реализация log_processing_error
"""

import json
import traceback
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging


class ProcessingErrorLogger:
    """📝 Логгер ошибок обработки с сохранением debug данных"""
    
    def __init__(self, errors_dir: str = "data/errors"):
        """
        Args:
            errors_dir: Директория для сохранения debug данных ошибок
        """
        self.errors_dir = Path(errors_dir)
        self.errors_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка стандартного логгера
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_processing_error(
        self,
        error: Exception,
        email_file: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        llm_request: Optional[Dict[str, Any]] = None,
        llm_response: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        📝 Логирование ошибки обработки с сохранением debug данных
        
        Сохраняет:
        - Информацию об ошибке (type, message, traceback)
        - Контекст (email_file, input_data, llm_request, llm_response)
        - Дополнительные данные (context)
        
        Args:
            error: Исключение, которое произошло
            email_file: Путь к файлу письма
            input_data: Входные данные (текст, метаданные)
            llm_request: Данные запроса к LLM
            llm_response: Ответ от LLM
            context: Дополнительный контекст
        
        Returns:
            str: Путь к сохранённому файлу с debug данными
        
        Examples:
            >>> logger = ProcessingErrorLogger()
            >>> try:
            ...     # Обработка письма
            ...     process_email(email_data)
            ... except Exception as e:
            ...     error_file = logger.log_processing_error(
            ...         error=e,
            ...         email_file="email_035.json",
            ...         input_data={'text_length': 5000},
            ...         llm_request={'provider': 'OpenRouter'}
            ...     )
            ...     print(f"Debug данные сохранены: {error_file}")
        """
        # Собираем информацию об ошибке
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': self._get_traceback(error)
        }
        
        # Собираем контекст
        context_info = {
            'timestamp': datetime.now().isoformat(),
            'email_file': email_file,
            'input_data': self._sanitize_data(input_data),
            'llm_request': self._sanitize_data(llm_request),
            'llm_response': self._sanitize_data(llm_response),
            'additional_context': context or {}
        }
        
        # Объединяем всё
        error_data = {
            **error_info,
            **context_info
        }
        
        # Сохраняем в JSON файл
        error_file_path = self._save_error_data(error_data, email_file)
        
        # Логируем в консоль
        self._log_to_console(error_info, context_info, error_file_path)
        
        return str(error_file_path)
    
    def _get_traceback(self, error: Exception) -> str:
        """🔍 Получить полный traceback ошибки"""
        return ''.join(traceback.format_exception(
            type(error),
            error,
            error.__traceback__
        ))
    
    def _sanitize_data(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """🧹 Очистка данных для сохранения (обрезка больших строк)"""
        if data is None:
            return {}
        
        if not isinstance(data, dict):
            return {'value': str(data)[:1000]}
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Обрезаем длинные строки
                if len(value) > 5000:
                    sanitized[key] = value[:5000] + f"... (truncated, total length: {len(value)})"
                else:
                    sanitized[key] = value
            elif isinstance(value, (dict, list)):
                # Для вложенных структур сохраняем как есть, но с ограничением
                try:
                    json_str = json.dumps(value, ensure_ascii=False)
                    if len(json_str) > 10000:
                        sanitized[key] = f"<large object, {len(json_str)} chars>"
                    else:
                        sanitized[key] = value
                except (TypeError, ValueError):
                    sanitized[key] = str(value)[:1000]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _save_error_data(
        self,
        error_data: Dict[str, Any],
        email_file: Optional[str]
    ) -> Path:
        """💾 Сохранение debug данных в JSON файл"""
        # Формируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if email_file:
            # Извлекаем имя файла без расширения
            email_name = Path(email_file).stem
            filename = f"error_{timestamp}_{email_name}.json"
        else:
            filename = f"error_{timestamp}.json"
        
        error_file_path = self.errors_dir / filename
        
        # Сохраняем в JSON
        try:
            with open(error_file_path, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Не удалось сохранить debug данные: {e}")
            # Пытаемся сохранить хотя бы базовую информацию
            with open(error_file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'error': 'Failed to save full error data',
                    'save_error': str(e),
                    'original_error': error_data.get('error_message', 'Unknown')
                }, f, ensure_ascii=False, indent=2)
        
        return error_file_path
    
    def _log_to_console(
        self,
        error_info: Dict[str, Any],
        context_info: Dict[str, Any],
        error_file_path: Path
    ):
        """📺 Логирование в консоль"""
        self.logger.error("=" * 80)
        self.logger.error(f"❌ ОШИБКА ОБРАБОТКИ: {error_info['error_type']}")
        self.logger.error(f"   Сообщение: {error_info['error_message']}")
        
        if context_info.get('email_file'):
            self.logger.error(f"   Файл письма: {context_info['email_file']}")
        
        # Логируем информацию о входных данных
        input_data = context_info.get('input_data', {})
        if input_data:
            text_length = input_data.get('text_length', 0)
            attachments_count = input_data.get('attachments_count', 0)
            has_ocr = input_data.get('has_ocr', False)
            
            if text_length or attachments_count:
                self.logger.error(
                    f"   Входные данные: текст {text_length} символов, "
                    f"{attachments_count} вложений, OCR: {has_ocr}"
                )
        
        # Логируем информацию о LLM запросе
        llm_request = context_info.get('llm_request', {})
        if llm_request:
            provider = llm_request.get('provider', 'N/A')
            model = llm_request.get('model', 'N/A')
            timeout = llm_request.get('timeout', 'N/A')
            
            self.logger.error(
                f"   LLM запрос: {provider} / {model}, таймаут: {timeout}с"
            )
        
        # Логируем информацию о LLM ответе
        llm_response = context_info.get('llm_response', {})
        if llm_response:
            status_code = llm_response.get('status_code', 'N/A')
            processing_time = llm_response.get('processing_time', 'N/A')
            
            self.logger.error(
                f"   LLM ответ: статус {status_code}, время {processing_time}с"
            )
        
        self.logger.error(f"   📁 Debug данные сохранены: {error_file_path}")
        self.logger.error("")
        self.logger.error("   Traceback:")
        
        # Выводим traceback построчно
        for line in error_info['traceback'].split('\n'):
            if line.strip():
                self.logger.error(f"   {line}")
        
        self.logger.error("=" * 80)


# Глобальный экземпляр для удобного использования
_global_error_logger = None


def get_error_logger(errors_dir: str = "data/errors") -> ProcessingErrorLogger:
    """
    🌍 Получить глобальный экземпляр логгера ошибок
    
    Args:
        errors_dir: Директория для сохранения debug данных
    
    Returns:
        ProcessingErrorLogger: Экземпляр логгера
    """
    global _global_error_logger
    
    if _global_error_logger is None:
        _global_error_logger = ProcessingErrorLogger(errors_dir)
    
    return _global_error_logger


def log_processing_error(
    error: Exception,
    email_file: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None,
    llm_request: Optional[Dict[str, Any]] = None,
    llm_response: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    📝 Удобная функция для логирования ошибок (использует глобальный логгер)
    
    Args:
        error: Исключение, которое произошло
        email_file: Путь к файлу письма
        input_data: Входные данные
        llm_request: Данные запроса к LLM
        llm_response: Ответ от LLM
        context: Дополнительный контекст
    
    Returns:
        str: Путь к сохранённому файлу с debug данными
    
    Examples:
        >>> from src.utils.error_logger import log_processing_error
        >>> 
        >>> try:
        ...     process_email(email_data)
        ... except Exception as e:
        ...     log_processing_error(
        ...         error=e,
        ...         email_file="email_035.json",
        ...         input_data={'text_length': 5000}
        ...     )
    """
    logger = get_error_logger()
    return logger.log_processing_error(
        error=error,
        email_file=email_file,
        input_data=input_data,
        llm_request=llm_request,
        llm_response=llm_response,
        context=context
    )
