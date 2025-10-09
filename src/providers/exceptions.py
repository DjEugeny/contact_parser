#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Provider Exceptions
Кастомные исключения для провайдеров LLM
"""

from typing import Optional


class EmptyResponseError(Exception):
    """
    Исключение для случаев, когда LLM возвращает пустой ответ
    
    Attributes:
        model_name: Название модели, которая вернула пустой ответ
        request_id: ID запроса (если доступен)
        input_length: Длина входного текста в символах
    """
    
    def __init__(
        self, 
        model_name: str, 
        request_id: Optional[str] = None, 
        input_length: Optional[int] = None,
        message: Optional[str] = None
    ):
        self.model_name = model_name
        self.request_id = request_id
        self.input_length = input_length
        
        # Формируем читаемое сообщение
        if message:
            self.message = message
        else:
            self.message = f"Empty response from model '{model_name}'"
            if request_id:
                self.message += f" (request_id: {request_id})"
            if input_length is not None:
                self.message += f" (input_length: {input_length} chars)"
        
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Возвращает читаемое представление ошибки"""
        return self.message
