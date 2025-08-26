#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧹 Модуль для агрессивной очистки текста писем от HTML мусора и Base64 данных
Версия: 1.0
Дата: 2025-01-21

Основные функции:
- Удаление вложенных blockquote с Base64 данными
- Очистка HTML тегов и атрибутов
- Удаление повторяющихся подписей
- Извлечение полезного текста из многоуровневых цитат
"""

import re
import html
from typing import Optional, List, Dict
from pathlib import Path
import logging

class EmailTextCleaner:
    """🧹 Класс для агрессивной очистки текста писем"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Паттерны для удаления
        self.base64_patterns = [
            r'sid=YWVzX3NpZDp7[^"]*',  # Base64 данные в sid параметрах
            r'data:[^;]*;base64,[A-Za-z0-9+/=]+',  # Data URLs с Base64
            r'[A-Za-z0-9+/]{50,}={0,2}',  # Длинные Base64 строки
        ]
        
        # Паттерны HTML для удаления
        self.html_cleanup_patterns = [
            (r'<img[^>]*>', ''),  # Удаляем все изображения
            (r'<div[^>]*class="[^"]*moz-signature[^"]*"[^>]*>.*?</div>', ''),  # Подписи Mozilla
            (r'<div[^>]*class="[^"]*signature[^"]*"[^>]*>.*?</div>', ''),  # Другие подписи
            (r'<style[^>]*>.*?</style>', ''),  # CSS стили
            (r'<script[^>]*>.*?</script>', ''),  # JavaScript
            (r'<!--.*?-->', ''),  # HTML комментарии
            (r'<meta[^>]*>', ''),  # Meta теги
            (r'<link[^>]*>', ''),  # Link теги
        ]
        
        # Паттерны для очистки текста
        self.text_cleanup_patterns = [
            (r'\n\s*\n\s*\n+', '\n\n'),  # Множественные переносы строк
            (r'\s{3,}', ' '),  # Множественные пробелы
            (r'&[a-zA-Z0-9#]+;', ' '),  # HTML entities
            (r'https://webattach\.mail\.yandex\.net[^\s]*', ''),  # Ссылки на вложения Yandex
            (r'https://[^\s]*\.png[^\s]*', ''),  # Ссылки на PNG изображения
            (r'https://[^\s]*\.jpg[^\s]*', ''),  # Ссылки на JPG изображения
            (r'https://[^\s]*\.gif[^\s]*', ''),  # Ссылки на GIF изображения
        ]
        
        # Подписи для удаления
        self.signature_patterns = [
            r'--\s*$',
            r'Отправлено из мобильного приложения.*',
            r'Sent from my .*',
            r'С уважением,?\s*$',
            r'Best regards,?\s*$',
            r'Regards,?\s*$',
        ]
    
    def clean_html_aggressively(self, html_text: str) -> str:
        """🧹 Агрессивная очистка HTML с удалением Base64 данных"""
        if not html_text:
            return ""
        
        text = html_text
        original_length = len(text)
        
        self.logger.debug(f"🧹 Начинаем очистку HTML текста ({original_length} символов)")
        
        # 1. Удаляем Base64 данные
        for pattern in self.base64_patterns:
            before_len = len(text)
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
            removed = before_len - len(text)
            if removed > 0:
                self.logger.debug(f"   🗑️ Удалено Base64 данных: {removed} символов")
        
        # 2. Удаляем blockquote только с Base64 данными
        before_len = len(text)
        # Ищем blockquote с длинными строками Base64
        text = re.sub(r'<blockquote[^>]*>[^<]*[A-Za-z0-9+/]{100,}[^<]*</blockquote>', '', text, flags=re.IGNORECASE | re.DOTALL)
        removed = before_len - len(text)
        if removed > 0:
            self.logger.debug(f"   🗑️ Удалено blockquote с Base64: {removed} символов")
        
        # 3. Удаляем проблемные HTML блоки
        for pattern, replacement in self.html_cleanup_patterns:
            before_len = len(text)
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.DOTALL)
            removed = before_len - len(text)
            if removed > 0:
                self.logger.debug(f"   🗑️ Удалено HTML блоков: {removed} символов")
        
        # 4. Удаляем все оставшиеся HTML теги
        before_len = len(text)
        text = re.sub(r'<[^>]+>', '', text)
        removed = before_len - len(text)
        if removed > 0:
            self.logger.debug(f"   🗑️ Удалено HTML тегов: {removed} символов")
        
        # 5. Декодируем HTML entities
        text = html.unescape(text)
        
        # 6. Очищаем текст от мусора
        for pattern, replacement in self.text_cleanup_patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        
        # 7. Удаляем подписи
        text = self.remove_signatures(text)
        
        # 8. Финальная очистка
        text = text.strip()
        
        final_length = len(text)
        reduction = original_length - final_length
        reduction_percent = (reduction / original_length * 100) if original_length > 0 else 0
        
        self.logger.info(f"🧹 Очистка завершена: {original_length} → {final_length} символов (-{reduction_percent:.1f}%)")
        
        return text
    
    def remove_signatures(self, text: str) -> str:
        """✂️ Удаление подписей из текста"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Проверяем, является ли строка подписью
            is_signature = False
            for pattern in self.signature_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_signature = True
                    break
            
            if not is_signature:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_meaningful_content(self, text: str, max_length: int = 10000) -> str:
        """📝 Извлечение осмысленного контента из очищенного текста"""
        if not text:
            return ""
        
        # Разбиваем на строки для более точной обработки
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Фильтруем строки по содержанию
        meaningful_lines = []
        for line in lines:
            # Пропускаем очень короткие строки (менее 3 символов)
            if len(line) < 3:
                continue
            
            # Пропускаем строки, состоящие только из символов пунктуации
            if re.match(r'^[^a-zA-Zа-яА-Я0-9]*$', line):
                continue
            
            # Пропускаем строки с только цифрами и точками (возможно, номера страниц)
            if re.match(r'^[0-9\.\s]*$', line):
                continue
                
            # Пропускаем повторяющиеся строки
            if line not in meaningful_lines:
                meaningful_lines.append(line)
        
        # Объединяем строки с переносами
        result = '\n'.join(meaningful_lines)
        
        # Убираем лишние переносы строк
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        if len(result) > max_length:
            result = result[:max_length] + "\n\n[ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ]"
        
        return result
    
    def clean_email_body(self, body_text: str, max_length: int = 10000) -> Dict[str, any]:
        """🔧 Полная очистка тела письма с метриками"""
        if not body_text:
            return {
                'cleaned_text': '',
                'original_length': 0,
                'final_length': 0,
                'reduction_percent': 0,
                'status': 'empty_input'
            }
        
        original_length = len(body_text)
        
        # Этап 1: Агрессивная очистка HTML
        cleaned_html = self.clean_html_aggressively(body_text)
        
        # Этап 2: Извлечение осмысленного контента
        meaningful_content = self.extract_meaningful_content(cleaned_html, max_length)
        
        final_length = len(meaningful_content)
        reduction_percent = ((original_length - final_length) / original_length * 100) if original_length > 0 else 0
        
        return {
            'cleaned_text': meaningful_content,
            'original_length': original_length,
            'final_length': final_length,
            'reduction_percent': reduction_percent,
            'status': 'success' if meaningful_content else 'no_content_extracted'
        }

def test_cleaner():
    """🧪 Тестирование очистителя текста"""
    import logging
    
    # Настраиваем логирование
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Создаем очиститель
    cleaner = EmailTextCleaner(logger)
    
    # Тестовый HTML с Base64 данными
    test_html = '''
    <blockquote>
        <div>Важное сообщение</div>
        <img src="https://webattach.mail.yandex.net/message_part_real/_.png?sid=YWVzX3NpZDp7ImFlc0tleUlkIjoiMTc4IiwiaG1hY0tleUlkIjoiMTc4IiwiaXZCYXNlNjQiOiJKZXkwYXlJOWRGbGVGUks0a2syZ2J3PT0iLCJzaWRCYXNlNjQiOiJ4cTFqdDdlNDh6eUFXczI3NjNpSjd6TWxjUTNnY0tkSzljeDE3RjB6YVo5TGNuNUxFdERTVERWa2xTY2ZpOS9hUVZIdUJHc3NpWjgrNWhmVCtPSWxSYStkam5ibE1zdTg5UmFBa2J2TjdxRTY5Q1VwSUxwU0I1Yy94TWZTK2Uxelk3V3RVWnB3Rnd5aXA0M1NSRjF6ZGc9PSIsImhtYWNCYXNlNjQiOiJtYmcyYjdtK3dUK21kOXZIWFk1am1ZajRITytqUmtJQVZ0cVhhWk8vdVlzPSJ9" />
        <blockquote>
            <div>Вложенная цитата</div>
            <div class="moz-signature">-- <br />Подпись</div>
        </blockquote>
    </blockquote>
    <br /><br />-- <br />Отправлено из мобильного приложения Яндекс Почты
    '''
    
    # Тестируем очистку
    result = cleaner.clean_email_body(test_html)
    
    print(f"Исходный размер: {result['original_length']} символов")
    print(f"Финальный размер: {result['final_length']} символов")
    print(f"Сокращение: {result['reduction_percent']:.1f}%")
    print(f"Очищенный текст: '{result['cleaned_text']}'")

if __name__ == '__main__':
    test_cleaner()