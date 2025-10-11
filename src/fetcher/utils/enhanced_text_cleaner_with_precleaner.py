#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧹 Улучшенный модуль очистки текста писем с интегрированным PreCleaner
Версия: 3.0 с PreCleaner интеграцией
Дата: 2025-10-10

Ключевые улучшения:
- Интеграция с PreCleaner для интеллектуальной очистки
- Сохранение полной обратной совместимости
- Улучшенная статистика и логирование
- Гибкая настройка через конфигурацию
"""

import re
import html
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import yaml

from .enhanced_text_cleaner import EnhancedTextCleaner
from .precleaner_adapter import PreCleanerAdapter


class EnhancedTextCleanerWithPreCleaner:
    """🧹 Улучшенный очиститель текста писем с интегрированным PreCleaner"""
    
    def __init__(self, logger: Optional[logging.Logger] = None, enable_precleaner: bool = True):
        self.logger = logger or logging.getLogger(__name__)
        self.enable_precleaner = enable_precleaner
        
        # Инициализируем базовый очиститель
        self.base_cleaner = EnhancedTextCleaner(logger)
        
        # Инициализируем PreCleaner адаптер
        if enable_precleaner:
            self.precleaner = PreCleanerAdapter(logger)
            self.logger.info("🧹 EnhancedTextCleanerWithPreCleaner инициализирован (С PreCleaner)")
        else:
            self.precleaner = None
            self.logger.info("🧹 EnhancedTextCleanerWithPreCleaner инициализирован (БЕЗ PreCleaner)")
    
    def clean_html_aggressively(self, html_text: str) -> str:
        """🧹 Агрессивная очистка HTML с сохранением полезного контента"""
        return self.base_cleaner.clean_html_aggressively(html_text)
    
    def remove_signatures(self, text: str) -> str:
        """✂️ Удаление подписей из текста"""
        return self.base_cleaner.remove_signatures(text)
    
    def extract_meaningful_content(self, text: str, max_length: Optional[int] = None, 
                                 thread_id: str = "unknown", sender_email: str = "unknown") -> str:
        """
        📝 Извлечение осмысленного контента с интеллектуальной пред-очисткой
        
        Args:
            text: Входной текст
            max_length: Опциональное ограничение длины (None = без ограничений)
            thread_id: ID треда для PreCleaner
            sender_email: Email отправителя для PreCleaner
        
        Returns:
            Очищенный текст с применением PreCleaner (если включен)
        """
        if not text:
            return ""
        
        # Этап 1: Базовая очистка через EnhancedTextCleaner
        base_cleaned = self.base_cleaner.extract_meaningful_content(text, max_length)
        
        # Этап 2: Интеллектуальная пред-очистка через PreCleaner (если включен)
        if self.enable_precleaner and self.precleaner:
            try:
                preclean_result = self.precleaner.preclean_text(
                    base_cleaned, thread_id, sender_email
                )
                
                # Логируем результаты пред-очистки
                original_len = len(base_cleaned)
                cleaned_len = len(preclean_result.body_clean_llm)
                reduction = original_len - cleaned_len
                reduction_percent = (reduction / original_len * 100) if original_len > 0 else 0
                
                self.logger.debug(
                    f"🧹 PreCleaner: {original_len} → {cleaned_len} символов "
                    f"(-{reduction_percent:.1f}%)"
                )
                
                # Применяем ограничение длины если нужно
                final_text = preclean_result.body_clean_llm
                if max_length is not None and len(final_text) > max_length:
                    self.logger.warning(f"⚠️ Текст обрезан до {max_length} символов по явному запросу")
                    final_text = final_text[:max_length] + f"\n\n[ТЕКСТ ОБРЕЗАН ДО {max_length} СИМВОЛОВ]"
                
                return final_text
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка PreCleaner: {e}, используем базовую очистку")
                return base_cleaned
        else:
            # PreCleaner отключен, используем только базовую очистку
            return base_cleaned
    
    def clean_email_body(self, body_text: str, max_length: Optional[int] = None,
                        thread_id: str = "unknown", sender_email: str = "unknown") -> Dict[str, Any]:
        """
        🔧 Полная очистка тела письма с метриками и PreCleaner
        
        Args:
            body_text: Исходный текст письма
            max_length: Опциональное ограничение длины (None = без ограничений)
            thread_id: ID треда для PreCleaner
            sender_email: Email отправителя для PreCleaner
        
        Returns:
            Словарь с очищенным текстом и метриками
        """
        if not body_text:
            return {
                'cleaned_text': '',
                'original_length': 0,
                'final_length': 0,
                'reduction_percent': 0,
                'status': 'empty_input',
                'precleaner_enabled': self.enable_precleaner
            }
        
        original_length = len(body_text)
        
        # Этап 1: Агрессивная очистка HTML
        cleaned_html = self.clean_html_aggressively(body_text)
        
        # Этап 2: Извлечение осмысленного контента с PreCleaner
        meaningful_content = self.extract_meaningful_content(
            cleaned_html, max_length, thread_id, sender_email
        )
        
        final_length = len(meaningful_content)
        reduction_percent = ((original_length - final_length) / original_length * 100) if original_length > 0 else 0
        
        result = {
            'cleaned_text': meaningful_content,
            'original_length': original_length,
            'final_length': final_length,
            'reduction_percent': reduction_percent,
            'status': 'success' if meaningful_content else 'no_content_extracted',
            'precleaner_enabled': self.enable_precleaner
        }
        
        # Добавляем статистику PreCleaner если доступна
        if self.enable_precleaner and self.precleaner:
            try:
                precleaner_stats = self.precleaner.get_processing_stats()
                result['precleaner_stats'] = precleaner_stats
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось получить статистику PreCleaner: {e}")
        
        return result
    
    def clean_email_body_full(self, body_text: str, thread_id: str = "unknown", 
                            sender_email: str = "unknown") -> Dict[str, Any]:
        """
        🔧 Полная очистка тела письма БЕЗ ЛЮБЫХ ОГРАНИЧЕНИЙ с PreCleaner
        
        Args:
            body_text: Исходный текст письма
            thread_id: ID треда для PreCleaner
            sender_email: Email отправителя для PreCleaner
        
        Returns:
            Словарь с полным очищенным текстом и метриками
        """
        return self.clean_email_body(body_text, max_length=None, thread_id=thread_id, sender_email=sender_email)
    
    def get_precleaner_stats(self) -> Optional[Dict[str, Any]]:
        """📊 Получить статистику PreCleaner"""
        if self.enable_precleaner and self.precleaner:
            return self.precleaner.get_processing_stats()
        return None
    
    def save_precleaner_stats(self, prefix: str = "enhanced_precleaner") -> Optional[str]:
        """💾 Сохранить статистику PreCleaner"""
        if self.enable_precleaner and self.precleaner:
            return self.precleaner.save_stats(prefix)
        return None
    
    def reset_precleaner_stats(self):
        """🔄 Сбросить статистику PreCleaner"""
        if self.enable_precleaner and self.precleaner:
            self.precleaner.reset_stats()
    
    def print_precleaner_summary(self):
        """📋 Вывести сводную статистику PreCleaner"""
        if self.enable_precleaner and self.precleaner:
            self.precleaner.print_summary()
        else:
            print("📋 PreCleaner отключен")


# Фабрика для создания очистителя с нужной конфигурацией
def create_text_cleaner(logger: Optional[logging.Logger] = None, 
                      enable_precleaner: bool = True,
                      config_path: Optional[str] = None) -> EnhancedTextCleanerWithPreCleaner:
    """
    🏭 Фабрика для создания текстового очистителя
    
    Args:
        logger: Логгер
        enable_precleaner: Включить PreCleaner
        config_path: Путь к конфигурационному файлу PreCleaner
    
    Returns:
        Настроенный экземпляр EnhancedTextCleanerWithPreCleaner
    """
    cleaner = EnhancedTextCleanerWithPreCleaner(logger, enable_precleaner)
    
    # Загружаем конфигурацию PreCleaner если указан путь
    if config_path and enable_precleaner and cleaner.precleaner:
        try:
            with open(config_path, 'r', encoding='utf-8') as handler:
                loaded = yaml.safe_load(handler) or {}

            if not isinstance(loaded, dict):
                raise ValueError("Некорректный формат YAML для precleaner")

            cleaner.precleaner.config.update(loaded.get("precleaner", loaded))
            cleaner.logger.info(f"📋 Конфигурация PreCleaner загружена из {config_path}")

        except Exception as e:
            cleaner.logger.warning(f"⚠️ Ошибка загрузки конфигурации PreCleaner: {e}")
    
    return cleaner


# Функция для тестирования интеграции
def test_enhanced_cleaner_with_precleaner():
    """🧪 Тестирование улучшенного очистителя текста с PreCleaner"""
    import logging
    
    # Настраиваем логирование
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Создаем очиститель с PreCleaner
    cleaner = create_text_cleaner(logger, enable_precleaner=True)
    
    # Тестовый HTML с различными типами контента
    test_html = '''
    <html>
    <body>
        <div>Важное сообщение с контактами:</div>
        <div>Телефон: +7 (495) 123-45-67</div>
        <div>Email: contact@example.com</div>
        <div>Адрес: Москва, ул. Тестовая, 123</div>
        
        <blockquote>
            <div>Это цитата предыдущего сообщения</div>
            <div>Содержит много повторяющегося текста</div>
        </blockquote>
        
        <div class="signature">
            --
            <br>С уважением,
            <br>Иван Иванов
            <br>Компания
        </div>
        
        <div class="disclaimer">
            Это конфиденциальное сообщение. Если вы получили его по ошибке, 
            пожалуйста, удалите и сообщите отправителю.
        </div>
        
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" />
    </body>
    </html>
    '''
    
    print("🧪 ТЕСТИРОВАНИЕ ENHANCED TEXT CLEANER WITH PRECLEANER")
    print("="*70)
    
    # Тестируем очистку с PreCleaner
    result = cleaner.clean_email_body_full(
        test_html, 
        thread_id="test_thread_123", 
        sender_email="test@example.com"
    )
    
    print(f"Исходный размер: {result['original_length']} символов")
    print(f"Финальный размер: {result['final_length']} символов")
    print(f"Сокращение: {result['reduction_percent']:.1f}%")
    print(f"PreCleaner включен: {result['precleaner_enabled']}")
    
    print(f"\nОчищенный текст:")
    print("-"*50)
    print(result['cleaned_text'])
    print("-"*50)
    
    # Проверяем наличие важной информации
    if "+7 (495) 123-45-67" in result['cleaned_text']:
        print("✅ Контактная информация сохранена")
    else:
        print("❌ Контактная информация потеряна")
    
    # Выводим статистику PreCleaner
    cleaner.print_precleaner_summary()
    
    # Сохраняем статистику
    stats_file = cleaner.save_precleaner_stats("test_run")
    if stats_file:
        print(f"\n📊 Статистика сохранена: {stats_file}")


if __name__ == '__main__':
    test_enhanced_cleaner_with_precleaner()
