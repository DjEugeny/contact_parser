#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧹 Улучшенный модуль очистки текста писем БЕЗ ОБРЕЗКИ
Версия: 2.0
Дата: 2025-10-09

Ключевые отличия от оригинального TextCleaner:
- НЕ обрезает тексты для экономии токенов
- Сохраняет всю контактную информацию
- Опциональная обрезка только по явному запросу
- Улучшенная очистка HTML с сохранением полезного контента
"""

import re
import html
from typing import Optional, List, Dict
import logging


class EnhancedTextCleaner:
    """🧹 Улучшенный очиститель текста писем БЕЗ ОБРЕЗКИ"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("🧹 EnhancedTextCleaner инициализирован (БЕЗ ОБРЕЗКИ ТЕКСТОВ)")
        
        # Паттерны для удаления (улучшенные)
        self.base64_patterns = [
            r'sid=YWVzX3NpZDp7[^"]*',  # Base64 данные в sid параметрах
            r'data:[^;]*;base64,[A-Za-z0-9+/=]+',  # Data URLs с Base64
            r'[A-Za-z0-9+/]{50,}={0,2}',  # Длинные Base64 строки
        ]
        
        # Паттерны HTML для удаления (более точные)
        self.html_cleanup_patterns = [
            (r'<img[^>]*src="[^"]*base64[^"]*"[^>]*>', ''),  # Только Base64 изображения
            (r'<div[^>]*class="[^"]*moz-signature[^"]*"[^>]*>.*?</div>', ''),  # Подписи Mozilla
            (r'<div[^>]*class="[^"]*signature[^"]*"[^>]*>.*?</div>', ''),  # Другие подписи
            (r'<style[^>]*>.*?</style>', ''),  # CSS стили
            (r'<script[^>]*>.*?</script>', ''),  # JavaScript
            (r'<!--.*?-->', ''),  # HTML комментарии
            (r'<meta[^>]*>', ''),  # Meta теги
            (r'<link[^>]*>', ''),  # Link теги
        ]
        
        # Паттерны для очистки текста (более консервативные)
        self.text_cleanup_patterns = [
            (r'\n\s*\n\s*\n+', '\n\n'),  # Множественные переносы строк
            (r'[ \t]{3,}', ' '),  # Множественные пробелы без затрагивания переносов
            (r'&[a-zA-Z0-9#]+;', ' '),  # HTML entities
            (r'https://webattach\.mail\.yandex\.net[^\s]*', ''),  # Ссылки на вложения Yandex
        ]
        
        # Подписи для удаления (более точные)
        self.signature_patterns = [
            r'^--\s*$',
            r'^Отправлено из мобильного приложения.*$',
            r'^Sent from my .*',
            r'^С уважением,?\s*$',
            r'^Best regards,?\s*$',
            r'^Regards,?\s*$',
        ]
    
    def clean_html_aggressively(self, html_text: str, preserve_signatures: bool = False) -> str:
        """🧹 Агрессивная очистка HTML с сохранением полезного контента"""
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

        # 3.1. Сохраняем содержимое псевдо-тегов (контакты в угловых скобках)
        pseudo_tag_whitelist = {
            "html",
            "body",
            "head",
            "meta",
            "style",
            "link",
            "script",
            "title",
            "table",
            "tbody",
            "thead",
            "tfoot",
            "tr",
            "td",
            "th",
            "colgroup",
            "col",
            "div",
            "span",
            "p",
            "br",
            "hr",
            "li",
            "ul",
            "ol",
            "strong",
            "em",
            "b",
            "i",
            "u",
            "font",
            "a",
            "img",
            "blockquote",
            "pre",
            "code",
            "center",
            "o:p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }

        def _restore_pseudo_tag(match: re.Match[str]) -> str:
            content = match.group(1).strip()
            if not content:
                return ""

            # Пропускаем комментарии и спец-конструкции
            if content.startswith(("!--", "![CDATA", "?")) or content.endswith("--"):
                return match.group(0)

            tag_candidate = content.split()[0].lstrip("/").lower()
            if tag_candidate in pseudo_tag_whitelist:
                return match.group(0)

            if "=" in content and "@" not in content:
                return match.group(0)

            return content

        text = re.sub(r"<([^<>]+)>", _restore_pseudo_tag, text)

        # 4. Сохраняем переносы строк для блочных элементов перед удалением тегов
        block_break_patterns = (
            (r'<\s*br\s*/?>', '\n'),
            (r'</\s*p\s*>', '\n'),
            (r'<\s*/?div[^>]*>', '\n'),
            (r'</\s*li\s*>', '\n'),
            (r'</\s*tr\s*>', '\n'),
            (r'</\s*table\s*>', '\n'),
        )
        for pattern, replacement in block_break_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 5. Удаляем все оставшиеся HTML теги
        before_len = len(text)
        text = re.sub(r'<[^>]+>', '', text)
        removed = before_len - len(text)
        if removed > 0:
            self.logger.debug(f"   🗑️ Удалено HTML тегов: {removed} символов")

        # 6. Декодируем HTML entities
        text = html.unescape(text)
        text = text.replace('\u00a0', ' ')

        # 7. Очищаем текст от мусора
        for pattern, replacement in self.text_cleanup_patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)

        # 8. Удаляем подписи, если это явно разрешено
        if not preserve_signatures:
            text = self.remove_signatures(text)

        # 9. Финальная очистка
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
    
    def extract_meaningful_content(self, text: str, max_length: Optional[int] = None) -> str:
        """
        📝 Извлечение осмысленного контента БЕЗ ОБРЕЗКИ (если не указан max_length)
        
        Args:
            text: Входной текст
            max_length: Опциональное ограничение длины (None = без ограничений)
        
        Returns:
            Очищенный текст БЕЗ обрезки (если не указан max_length)
        """
        if not text:
            return ""
        
        # Разбиваем на строки для более точной обработки
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Фильтруем строки по содержанию
        meaningful_lines = []
        for line in lines:
            # Пропускаем строки, состоящие только из символов пунктуации
            if re.match(r'^[^a-zA-Zа-яА-Я0-9]*$', line):
                continue
            
            # Пропускаем повторяющиеся строки
            if line not in meaningful_lines:
                meaningful_lines.append(line)
        
        # Объединяем строки с переносами
        result = '\n'.join(meaningful_lines)
        
        # Убираем лишние переносы строк
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Обрезка только если явно указан max_length
        if max_length is not None and len(result) > max_length:
            self.logger.warning(f"⚠️ Текст обрезан до {max_length} символов по явному запросу")
            result = result[:max_length] + f"\n\n[ТЕКСТ ОБРЕЗАН ДО {max_length} СИМВОЛОВ]"
        else:
            self.logger.info(f"✅ Текст сохранен полностью ({len(result)} символов) БЕЗ ОБРЕЗКИ")
        
        return result
    
    def clean_email_body(self, body_text: str, max_length: Optional[int] = None) -> Dict[str, any]:
        """
        🔧 Полная очистка тела письма с метриками БЕЗ ОБРЕЗКИ
        
        Args:
            body_text: Исходный текст письма
            max_length: Опциональное ограничение длины (None = без ограничений)
        
        Returns:
            Словарь с очищенным текстом и метриками
        """
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
        
        # Этап 2: Извлечение осмысленного контента БЕЗ ОБРЕЗКИ
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
    
    def clean_email_body_full(self, body_text: str) -> Dict[str, any]:
        """
        🔧 Полная очистка тела письма БЕЗ ЛЮБЫХ ОГРАНИЧЕНИЙ
        
        Args:
            body_text: Исходный текст письма
        
        Returns:
            Словарь с полным очищенным текстом и метриками
        """
        return self.clean_email_body(body_text, max_length=None)


def test_enhanced_cleaner():
    """🧪 Тестирование улучшенного очистителя текста"""
    import logging
    
    # Настраиваем логирование
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Создаем очиститель
    cleaner = EnhancedTextCleaner(logger)
    
    # Тестовый HTML с Base64 данными
    test_html = '''
    <blockquote>
        <div>Важное сообщение с контактами:</div>
        <div>Телефон: +7 (495) 123-45-67</div>
        <div>Email: contact@example.com</div>
        <div>Адрес: Москва, ул. Тестовая, 123</div>
        <img src="https://webattach.mail.yandex.net/message_part_real/_.png?sid=YWVzX3NpZDp7ImFlc0tleUlkIjoiMTc4IiwiaG1hY2tleUlkIjoiMTc4IiwiaXZCYXNlNjQiOiJKZXkwYXlJOWRGbGVGUks0a2syZ2J3PT0iLCJzaWRCYXNlNjQiOiJ4cTFqdDdlNDh6eUFXczI3NjNpSjd6TWxjUTNnY0tkSzljeDE3RjB6YVo5TGNuNUxFdERTVERWa2xTY2ZpOS9hUVZIdUJHc3NpWjgrNWhmVCtPSWxSYStkam5ibE1zdTg5UmFBa2J2TjdxRTY5Q1VwSUxwU0I1Yy94TWZTK2Uxelk3V3RVWnB3Rnd5aXA0M1NSRjF6ZGc9PSIsImhtYWNCYXNlNjQiOiJtYmcyYjdtK3dUK21kOXZIWFk1am1ZajRITytqUmtJQVZ0cVhhWk8vdVlzPSJ9" />
        <blockquote>
            <div>Вложенная цитата</div>
            <div class="moz-signature">-- <br />Подпись</div>
        </blockquote>
    </blockquote>
    <br /><br />-- <br />Отправлено из мобильного приложения Яндекс Почты
    '''
    
    # Тестируем очистку БЕЗ ОБРЕЗКИ
    result = cleaner.clean_email_body_full(test_html)
    
    print(f"Исходный размер: {result['original_length']} символов")
    print(f"Финальный размер: {result['final_length']} символов")
    print(f"Сокращение: {result['reduction_percent']:.1f}%")
    print(f"Очищенный текст: '{result['cleaned_text']}'")
    
    # Проверяем наличие контактной информации
    if "+7 (495) 123-45-67" in result['cleaned_text']:
        print("✅ Контактная информация сохранена")
    else:
        print("❌ Контактная информация потеряна")
    
    if "ТЕКСТ ОБРЕЗАН" in result['cleaned_text']:
        print("❌ Текст был обрезан")
    else:
        print("✅ Текст НЕ обрезан")


if __name__ == '__main__':
    test_enhanced_cleaner()
