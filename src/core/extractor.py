#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Новый ContactExtractor с Dependency Injection
Фаза 5: Архитектурная оптимизация
"""

import asyncio
import json
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from functools import lru_cache

from ..providers.base_provider import BaseProvider
from ..config.provider_manager import ProviderManager, ProviderManagerConfig
from ..phone_normalizer import PhoneNormalizer
from .validator import LLMResponseValidator
from .cache_manager import MultiLevelCache
from .memory_optimizer import MemoryOptimizer
from .chunker import TextChunker, ChunkingConfig


@dataclass
class ChunkingConfig:
    """📋 Конфигурация для chunking текста"""
    max_chunk_size: int = 8000
    overlap_size: int = 1000
    use_tokens: bool = True


@dataclass
class RetryConfig:
    """📋 Конфигурация для retry логики"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


@dataclass
class ExtractorConfig:
    """📋 Полная конфигурация экстрактора"""
    provider_manager: ProviderManager
    phone_normalizer: PhoneNormalizer
    json_validator: LLMResponseValidator
    chunking_config: ChunkingConfig = field(default_factory=ChunkingConfig)
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    prompts_dir: Optional[Path] = None


class ContactExtractor:
    """
    🎯 Новый ContactExtractor с Dependency Injection

    Использует принципы:
    - Dependency Injection для модульной архитектуры
    - Асинхронная обработка для производительности
    - Строгая типизация для надежности
    - Circuit Breaker паттерн для отказоустойчивости
    """

    def __init__(self, config: ExtractorConfig):
        self.config = config

        # Расширенная статистика
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'json_parsing_errors': 0,
            'json_schema_validation_errors': 0,
            'json_schema_auto_corrections': 0,
            'fallback_switches': 0,
            'provider_failures': {
                'openrouter': 0,
                'groq': 0,
                'replicate': 0
            },
            'async_operations': 0,
            'chunked_operations': 0,
            'cached_requests': 0  # Фаза 6: кэшированные запросы
        }

        # 💾 Многоуровневое кэширование (Фаза 6)
        self.cache = MultiLevelCache()

        # 🧠 Memory оптимизатор (Фаза 6)
        self.memory_optimizer = MemoryOptimizer(max_memory_mb=300, gc_threshold_mb=150)

        # ✂️ Text chunker (Фаза 5+)
        self.chunker = TextChunker(config.chunking_config)

        # Устаревший кэш промптов (для совместимости)
        self._prompt_cache: Dict[str, str] = {}

        print("🎯 Новый ContactExtractor инициализирован с Dependency Injection")
        print(f"   📁 Промпты: {self.config.prompts_dir}")
        print(f"   🔧 Провайдеры: {len(self.config.provider_manager.providers)}")
        print("   📞 PhoneNormalizer: интегрирован")
        print("   📊 JSON Schema Validator: интегрирован")
    def load_prompt(self, filename: str) -> str:
        """
        📝 Загрузка промпта с многоуровневым кэшированием (Фаза 6)

        Сначала проверяет новый MultiLevelCache, затем падает обратно на старый метод
        """
        # 🚀 Сначала пробуем новый кэш (Фаза 6)
        cached_prompt = self.cache.get_prompt(filename)
        if cached_prompt:
            return cached_prompt

        # 🔄 Fallback на старый метод (для совместимости)
        if filename in self._prompt_cache:
            return self._prompt_cache[filename]

        prompts_dir = self.config.prompts_dir or Path(__file__).parent.parent.parent / "prompts"
        prompt_path = prompts_dir / filename

        if not prompt_path.exists():
            raise FileNotFoundError(f"❌ Промпт не найден: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()

        # Кэшируем в старом кэше для совместимости
        self._prompt_cache[filename] = prompt
        return prompt

    def extract_all_data(self, text: str, metadata: dict = None) -> dict:
        """
        👤 Основной метод извлечения контактов, бизнес-контекста и КП
        Единый LLM запрос для всех трех задач

        Args:
            text: Текст для анализа
            metadata: Дополнительные метаданные

        Returns:
            dict: {
                "contacts": [...],
                "business_context": "...",
                "commercial_offers": [...]
            }
        """
        self.stats['total_requests'] += 1

        try:
            # 🧠 Проверяем размер текста и оптимизируем память (Фаза 6)
            text_size_mb = len(text) / 1024 / 1024

            if text_size_mb > 1.0:  # > 1MB
                print(".1f")
                # Используем memory monitor для больших текстов
                with self.memory_optimizer.memory_monitor():
                    prompt = self._prepare_unified_prompt(text, metadata)
            else:
                prompt = self._prepare_unified_prompt(text, metadata)

            # 💾 Проверяем кэш перед запросом (Фаза 6)
            prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
            cached_result = self.cache.get_llm_response(prompt_hash, "unified_extraction")

            if cached_result:
                print("💾 Используем кэшированный результат")
                llm_response = cached_result
                self.stats['cached_requests'] += 1
            else:
                # Запрос к LLM с fallback системой
                print("🤖 Запрос к LLM провайдерам...")
                llm_response = self.config.provider_manager.make_request_with_fallback(
                    prompt,
                    temperature=0.1,
                    max_tokens=4000
                )

                # 💾 Кэшируем результат (Фаза 6)
                self.cache.set_llm_response(prompt_hash, "unified_extraction", llm_response)

            # Парсинг JSON ответа
            if isinstance(llm_response, dict) and 'content' in llm_response:
                result = self._parse_llm_response(llm_response['content'])
            else:
                result = llm_response

            # Постобработка контактов
            if 'contacts' in result and result['contacts']:
                print(f"   📞 Постобработка {len(result['contacts'])} контактов...")
                result['contacts'] = self._postprocess_contacts(result['contacts'])
                print("   ✅ Контакты обработаны")

            # Добавление метаданных ответа
            result.update({
                'provider_used': llm_response.get('provider'),
                'processing_time': llm_response.get('response_time', 0),
                'text_length': len(text),
                'chunks_processed': 1,
                'total_contacts_found': len(result.get('contacts', [])),
                'unique_contacts_found': len(result.get('contacts', []))
            })

            self.stats['successful_requests'] += 1
            return result

        except Exception as e:
            self.stats['failed_requests'] += 1
            print(f"❌ Ошибка в extract_all_data: {e}")

            # Возврат минимально валидного ответа
            return self.config.json_validator.graceful_degradation_fallback({
                'error': str(e),
                'text_length': len(text)
            })

    async def extract_all_data_async(self, text: str, metadata: dict = None) -> dict:
        """
        🚀 Асинхронная версия extract_all_data
        Для лучшей производительности при параллельной обработке
        """
        self.stats['async_operations'] += 1

        # В текущей реализации используем ThreadPoolExecutor
        # В будущем можно добавить полноценную асинхронную поддержку
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                self.extract_all_data,
                text,
                metadata
            )

        return result

    def _prepare_unified_prompt(self, text: str, metadata: dict = None) -> str:
        """📝 Подготовка единого промпта для всех задач"""
        try:
            # Загрузка основного промпта
            base_prompt = self.load_prompt("unified_contact_extraction.txt")

            # Замена плейсхолдера на текст
            prompt = base_prompt.replace("{combined_text}", text)

            # Добавление метаданных если есть
            if metadata:
                metadata_str = f"\n\nДополнительная информация:\n{json.dumps(metadata, ensure_ascii=False, indent=2)}"
                prompt += metadata_str

            return prompt

        except Exception as e:
            print(f"⚠️  Ошибка подготовки промпта: {e}")
            # Fallback на простой промпт
            return self._create_simple_fallback_prompt(text)

    def _create_simple_fallback_prompt(self, text: str) -> str:
        """🛡️ Простой fallback промпт при проблемах с загрузкой"""
        return f"""Проанализируй следующий текст и верни JSON с контактами, бизнес-контекстом и коммерческими предложениями:

Текст: {text}

Формат ответа:
{{
  "contacts": [],
  "business_context": "",
  "commercial_offers": []
}}"""

    def _postprocess_contacts(self, contacts: List[dict]) -> List[dict]:
        """🔧 Постобработка контактов: нормализация телефонов, обработка ИНН и сайтов"""
        if not contacts:
            return contacts
            
        processed_contacts = []
        
        for contact in contacts:
            try:
                # 1. Нормализация телефонов
                if contact.get('phone'):
                    normalized_phones = self.config.phone_normalizer.normalize_contact_list([contact])
                    if normalized_phones:
                        contact = normalized_phones[0]
                
                # 2. Обработка ИНН
                if contact.get('inn'):
                    inn = str(contact['inn']).strip()
                    # Базовая валидация ИНН (10 или 12 цифр)
                    if inn.isdigit() and len(inn) in [10, 12]:
                        contact['inn'] = inn
                        contact['inn_type'] = 'organization' if len(inn) == 10 else 'individual'
                        contact['inn_validated'] = True
                    else:
                        contact['inn'] = None
                        contact['inn_type'] = 'invalid'
                        contact['inn_validated'] = False
                else:
                    contact['inn'] = None
                    contact['inn_type'] = None
                    contact['inn_validated'] = False
                
                # 3. Обработка сайтов
                if contact.get('website'):
                    website = str(contact['website']).strip()
                    # Базовая нормализация URL
                    if website and not website.startswith(('http://', 'https://')):
                        if '.' in website:
                            website = f'https://{website}'
                        else:
                            website = None
                    
                    if website:
                        contact['website'] = website
                        contact['website_confidence'] = 0.8  # Базовая уверенность
                    else:
                        contact['website'] = None
                        contact['website_confidence'] = None
                else:
                    # Попытка извлечь сайт из email домена
                    if contact.get('email'):
                        email = contact['email']
                        if '@' in email:
                            domain = email.split('@')[1]
                            # Исключаем популярные почтовые сервисы
                            if domain not in ['gmail.com', 'yandex.ru', 'mail.ru', 'yahoo.com', 'outlook.com']:
                                contact['website'] = f'https://{domain}'
                                contact['website_confidence'] = 0.6  # Средняя уверенность
                            else:
                                contact['website'] = None
                                contact['website_confidence'] = None
                        else:
                            contact['website'] = None
                            contact['website_confidence'] = None
                    else:
                        contact['website'] = None
                        contact['website_confidence'] = None
                
                processed_contacts.append(contact)
                
            except Exception as e:
                print(f"⚠️ Ошибка постобработки контакта: {e}")
                # Возвращаем контакт как есть при ошибке
                processed_contacts.append(contact)
        
        return processed_contacts

    def _parse_llm_response(self, response_text: str) -> dict:
        """
        🔍 Парсинг ответа LLM с валидацией JSON Schema

        Args:
            response_text: Сырой текст ответа от LLM

        Returns:
            dict: Валидированный и обработанный результат
        """
        try:
            # Попытка парсинга JSON
            if response_text.strip().startswith('{'):
                result = json.loads(response_text)
            else:
                # Поиск JSON в тексте
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("JSON не найден в ответе LLM")

            # ФАЗА 4: Строгая JSON Schema валидация
            print(f"🔍 Применение строгой JSON Schema валидации...")
            is_valid, validation_errors, corrected_result = self.config.json_validator.validate_llm_response(result)

            if not is_valid:
                self.stats['json_schema_validation_errors'] += 1
                print(f"❌ JSON Schema валидация не пройдена: {len(validation_errors)} ошибок")

                # Детальная диагностика
                for error in validation_errors:
                    print(f"   ⚠️ {error}")

                # Автоматическое исправление
                if corrected_result != result:
                    self.stats['json_schema_auto_corrections'] += 1
                    result = corrected_result
                    print("✅ Использован автоматически исправленный результат")
                else:
                    # Graceful degradation
                    result = self.config.json_validator.graceful_degradation_fallback(result)
                    print("✅ Создан минимально валидный ответ")
            else:
                print("✅ JSON Schema валидация пройдена успешно")

            return result

        except json.JSONDecodeError as e:
            self.stats['json_parsing_errors'] += 1
            print(f"❌ Ошибка парсинга JSON: {e}")

            # Попытка исправления распространенных ошибок
            fixed_text = self._fix_common_json_errors(response_text)
            try:
                return json.loads(fixed_text)
            except:
                # Graceful degradation
                return self.config.json_validator.graceful_degradation_fallback({})

        except Exception as e:
            print(f"❌ Неожиданная ошибка парсинга: {e}")
            return self.config.json_validator.graceful_degradation_fallback({})

    def _fix_common_json_errors(self, text: str) -> str:
        """🔧 Исправление распространенных ошибок JSON"""
        # Удаление лишних запятых перед закрывающими скобками
        text = re.sub(r',(\s*[}\]])', r'\1', text)

        # Исправление неэкранированных кавычек
        text = re.sub(r'(?<!\\)"(?![,\}\]\s])', r'\"', text)

        return text

    def get_stats(self) -> Dict[str, Any]:
        """📊 Получить статистику экстрактора"""
        provider_stats = self.config.provider_manager.get_stats()

        return {
            'extractor_stats': self.stats,
            'provider_stats': provider_stats,
            'phone_normalizer_stats': self.config.phone_normalizer.get_phone_stats([]),  # TODO: передать контакты
            'json_validator_stats': self.config.json_validator.get_validation_stats()
        }

    # Обратная совместимость
    def extract_contacts(self, text: str, metadata: dict = None) -> dict:
        """
        🔄 УСТАРЕВШИЙ МЕТОД: Используйте extract_all_data()
        Оставлен для обратной совместимости
        """
        print("⚠️  Используется устаревший метод extract_contacts, рекомендуется extract_all_data")
        return self.extract_all_data(text, metadata)
