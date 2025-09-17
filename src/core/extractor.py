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
from ..config import UnifiedConfigManager
from ..postprocessing.phone_normalizer import PhoneNormalizer
from .validator import LLMResponseValidator
from .cache_manager import MultiLevelCache
from .memory_optimizer import MemoryOptimizer
from .chunker import TextChunker, ChunkingConfig
from .ocr_manager import OCRManager, get_ocr_manager

# Импорт системы кеширования
from .result_cache import get_result_cache, CacheConfig


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
    provider_manager: UnifiedConfigManager
    phone_normalizer: PhoneNormalizer
    json_validator: LLMResponseValidator
    chunking_config: ChunkingConfig = field(default_factory=ChunkingConfig)
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    ocr_manager: Optional[OCRManager] = field(default_factory=lambda: get_ocr_manager())
    prompts_dir: Optional[Path] = None
    test_mode: bool = False


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
        self.test_mode = config.test_mode

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

        # 🔍 OCR Manager (унифицированная OCR обработка)
        self.ocr_manager = config.ocr_manager

        # Устаревший кэш промптов (для совместимости)
        self._prompt_cache: Dict[str, str] = {}

        # Инициализация системы кеширования результатов
        cache_config = CacheConfig(
            extraction_ttl=3600,  # 1 час для результатов извлечения
            ocr_ttl=86400,        # 24 часа для OCR результатов
            prompt_ttl=7200,      # 2 часа для промптов
            enable_local_cache=True,
            enable_compression=True
        )
        self.result_cache = get_result_cache(cache_config)

        print("🎯 Новый ContactExtractor инициализирован с Dependency Injection")
        print(f"   📁 Промпты: {self.config.prompts_dir}")
        print(f"   🔧 Провайдеры: {len(self.config.provider_manager.get_llm_providers())}")
        print("   📞 PhoneNormalizer: интегрирован")
        print("   📊 JSON Schema Validator: интегрирован")
        print("   🔍 OCR Manager: интегрирован")
        print("   🏪 Result Cache: включен")
    def load_prompt(self, filename: str) -> str:
        """
        📝 Загрузка промпта с многоуровневым кэшированием через ResultCache

        Использует новую систему кеширования результатов
        """
        # 🚀 Проверяем кеш результатов
        cached_prompt = self.result_cache.get_prompt(filename)
        if cached_prompt:
            return cached_prompt

        # 🚀 Сначала пробуем новый кэш (Фаза 6)
        cached_prompt = self.cache.get_prompt(filename)
        if cached_prompt:
            # Кешируем в новой системе
            self.result_cache.cache_prompt(filename, cached_prompt)
            return cached_prompt

        # 🔄 Fallback на старый метод (для совместимости)
        if filename in self._prompt_cache:
            prompt = self._prompt_cache[filename]
            # Кешируем в новой системе
            self.result_cache.cache_prompt(filename, prompt)
            return prompt

        prompts_dir = self.config.prompts_dir or Path(__file__).parent.parent.parent / "prompts"
        prompt_path = prompts_dir / filename

        if not prompt_path.exists():
            raise FileNotFoundError(f"❌ Промпт не найден: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()

        # Кешируем в новой системе
        self.result_cache.cache_prompt(filename, prompt)
        
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

        # 🎯 Этап 4: Фильтрация по токенам с конфигурируемым порогом 15000 токенов
        token_limit = 15000  # Конфигурируемый порог
        token_count = self._count_tokens(text)
        
        if token_count > token_limit:
            print(f"⚠️ Текст превышает лимит токенов: {token_count} > {token_limit}")
            print(f"🔄 Применяем chunking для обработки большого текста")
            
            # Используем chunking для больших текстов
            chunks = self.chunker.create_chunks(text)
            if len(chunks) > 1:
                print(f"✂️ Текст разбит на {len(chunks)} частей")
                return self._process_chunks(chunks, metadata)
            else:
                print(f"⚠️ Chunking не помог, обрабатываем как есть")

        # Создаем хеш контента для кеширования
        content_hash = hashlib.md5(f"{text}_{metadata}".encode()).hexdigest()
        
        # Проверяем кеш результатов (если не тестовый режим)
        if not self.test_mode:
            cached_result = self.result_cache.get_extraction_result(content_hash)
            if cached_result and 'result' in cached_result:
                print(f"💾 Используем кешированный результат: {content_hash[:8]}...")
                self.stats['cached_requests'] += 1
                return cached_result['result']

        # Тестовый режим - возвращаем заранее подготовленный результат
        if self.test_mode:
            print("🧪 Тестовый режим: возвращаем тестовые данные")
            return {
                'contacts': [{
                    'name': 'Тестовый Контакт',
                    'email': 'test@example.com',
                    'phone': '+7 (999) 123-45-67',
                    'organization': 'Тестовая Организация',
                    'position': 'Тестовая Должность',
                    'city': 'Тестовый Город',
                    'website': 'https://test.example.com',
                    'inn': '1234567890',
                    'confidence': 0.95
                }],
                'business_context': 'Тестовый бизнес-контекст для демонстрации',
                'commercial_offers': [{
                    'title': 'Тестовое предложение',
                    'description': 'Описание тестового коммерческого предложения',
                    'price': '100000 руб.',
                    'confidence': 0.9
                }],
                'organizations': [{
                    'name': 'Тестовая Организация',
                    'inn': '1234567890',
                    'website': 'https://test.example.com',
                    'confidence': 0.95
                }],
                'provider_used': 'test_mode',
                'processing_time': 0.1,
                'text_length': len(text),
                'chunks_processed': 1,
                'total_contacts_found': 1,
                'unique_contacts_found': 1,
                'test_mode': True
            }

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
                request_data = {
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
                
                # Используем синхронную версию fallback системы
                llm_response = self.config.provider_manager.make_request_sync(
                    provider=self.config.provider_manager.get_best_available_provider(),
                    request_data=request_data
                )

                # 💾 Кэшируем результат (Фаза 6)
                self.cache.set_llm_response(prompt_hash, "unified_extraction", llm_response)

            # Парсинг JSON ответа
            if isinstance(llm_response, dict) and 'content' in llm_response:
                result = self._parse_llm_response(llm_response['content'])
            else:
                result = llm_response

            # Валидация через validate_llm_response (с автокоррекцией)
            print("🔍 Применение строгой JSON Schema валидации...")
            is_valid, errors, corrected_result = self.config.json_validator.validate_llm_response(result)
            
            if is_valid:
                print("✅ JSON Schema валидация пройдена успешно")
                result = corrected_result
            else:
                print(f"❌ Валидация не удалась: {errors}")
                result = corrected_result  # Используем fallback результат
            
            print(f"🔍 После валидации: {len(result.get('contacts', []))} контактов, {len(result.get('organizations', []))} организаций")
            if result.get('organizations'):
                print(f"📋 Организации: {[org.get('name') for org in result['organizations']]}")
            
            print(f"✅ Валидация завершена: {len(result.get('contacts', []))} контактов, {len(result.get('organizations', []))} организаций")

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

            # Кешируем результат (если не тестовый режим)
            if not self.test_mode:
                self.result_cache.cache_extraction_result(content_hash, result)

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
        🚀 Улучшенная асинхронная версия extract_all_data
        С полноценной retry логикой, обработкой исключений и таймаутами
        """
        self.stats['async_operations'] += 1
        
        # Применяем retry логику для асинхронной обработки
        for attempt in range(self.config.retry_config.max_attempts):
            try:
                print(f"🚀 Асинхронная обработка (попытка {attempt + 1}/{self.config.retry_config.max_attempts})...")
                
                # Используем asyncio.wait_for для таймаута
                result = await asyncio.wait_for(
                    self._extract_with_executor(text, metadata),
                    timeout=120.0  # 2 минуты таймаут
                )
                
                print(f"✅ Асинхронная обработка успешно завершена")
                return result
                
            except asyncio.TimeoutError:
                print(f"⏰ Таймаут асинхронной обработки (попытка {attempt + 1})")
                if attempt == self.config.retry_config.max_attempts - 1:
                    return {
                        'contacts': [],
                        'business_context': '',
                        'commercial_offers': [],
                        'provider_used': 'async_timeout_error',
                        'processing_time': 120.0,
                        'error': 'Превышен таймаут асинхронной обработки',
                        'attempts_made': attempt + 1
                    }
                    
            except Exception as e:
                print(f"❌ Ошибка асинхронной обработки (попытка {attempt + 1}): {e}")
                
                if attempt == self.config.retry_config.max_attempts - 1:
                    # Последняя попытка - возвращаем ошибку
                    return {
                        'contacts': [],
                        'business_context': '',
                        'commercial_offers': [],
                        'provider_used': 'async_error',
                        'processing_time': 0,
                        'error': f'Асинхронная обработка не удалась: {str(e)}',
                        'attempts_made': attempt + 1
                    }
                
                # Экспоненциальная задержка перед повтором
                delay = min(
                    self.config.retry_config.base_delay * (self.config.retry_config.exponential_base ** attempt),
                    self.config.retry_config.max_delay
                )
                print(f"⏳ Ожидание {delay:.1f}с перед повтором...")
                await asyncio.sleep(delay)
        
        # Этот код не должен выполняться, но на всякий случай
        return {
            'contacts': [],
            'business_context': '',
            'commercial_offers': [],
            'provider_used': 'async_fallback_error',
            'processing_time': 0,
            'error': 'Неожиданная ошибка в асинхронной обработке'
        }

    async def _extract_with_executor(self, text: str, metadata: dict = None) -> dict:
        """
        🔧 Вспомогательный метод для выполнения извлечения в ThreadPoolExecutor
        
        Args:
            text: Текст для анализа
            metadata: Дополнительные метаданные
            
        Returns:
            dict: Результат обработки
        """
        import concurrent.futures
        
        # Используем ThreadPoolExecutor с ограниченным количеством потоков
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            loop = asyncio.get_event_loop()
            
            # Запускаем синхронную обработку в отдельном потоке
            result = await loop.run_in_executor(
                executor,
                self._extract_with_error_handling,
                text,
                metadata
            )
            
        return result

    def _extract_with_error_handling(self, text: str, metadata: dict = None) -> dict:
        """
        🛡️ Обертка для extract_all_data с дополнительной обработкой ошибок
        
        Args:
            text: Текст для анализа
            metadata: Дополнительные метаданные
            
        Returns:
            dict: Результат обработки
        """
        try:
            return self.extract_all_data(text, metadata)
        except Exception as e:
            print(f"❌ Критическая ошибка в _extract_with_error_handling: {e}")
            return {
                'contacts': [],
                'business_context': '',
                'commercial_offers': [],
                'provider_used': 'error_handler',
                'processing_time': 0,
                'error': f'Критическая ошибка обработки: {str(e)}'
            }

    def _prepare_unified_prompt(self, text: str, metadata: dict = None) -> str:
        """📝 Подготовка единого промпта для всех задач"""
        try:
            # Загрузка основного промпта
            base_prompt = self.load_prompt("unified_contact_extraction_structured.txt")

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

            # Возвращаем распарсенный JSON без дополнительной валидации
            # (валидация будет выполнена в extract_all_data)
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

    def extract_from_file(self, file_path: str, date: str = None) -> dict:
        """
        🔍 Извлечение контактов из файла с использованием OCR Manager
        
        Args:
            file_path: Путь к файлу для обработки
            date: Дата для фильтрации (опционально)
            
        Returns:
            dict: Результат извлечения контактов с метаданными OCR
        """
        if not self.ocr_manager:
            raise ValueError("OCR Manager не инициализирован")
            
        try:
            # Извлекаем текст через OCR Manager
            ocr_result = self.ocr_manager.extract_text_from_file(file_path, date)
            
            if not ocr_result.get('success', False):
                return {
                    'success': False,
                    'error': ocr_result.get('error', 'OCR обработка не удалась'),
                    'contacts': [],
                    'metadata': {
                        'file_path': file_path,
                        'ocr_used': True,
                        'ocr_cached': ocr_result.get('cached', False)
                    }
                }
            
            # Извлекаем контакты из полученного текста
            extracted_text = ocr_result.get('text', '')
            metadata = {
                'file_path': file_path,
                'ocr_used': True,
                'ocr_cached': ocr_result.get('cached', False),
                'ocr_processing_time': ocr_result.get('processing_time', 0),
                'date_filter': date
            }
            
            # Используем основной метод извлечения
            extraction_result = self.extract_all_data(extracted_text, metadata)
            
            # Обновляем статистику
            self.stats['total_requests'] += 1
            if extraction_result.get('success', False):
                self.stats['successful_requests'] += 1
            else:
                self.stats['failed_requests'] += 1
                
            return extraction_result
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            return {
                'success': False,
                'error': f'Ошибка обработки файла: {str(e)}',
                'contacts': [],
                'metadata': {
                    'file_path': file_path,
                    'ocr_used': True,
                    'error_type': type(e).__name__
                }
            }

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

    def _count_tokens(self, text: str) -> int:
        """
        🔢 Подсчет токенов в тексте
        
        Args:
            text: Текст для подсчета токенов
            
        Returns:
            int: Количество токенов
        """
        try:
            import tiktoken
            encoding = tiktoken.get_encoding('cl100k_base')
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: примерная оценка 1 токен = 4 символа
            return len(text) // 4
        except Exception as e:
            print(f"⚠️ Ошибка подсчета токенов: {e}")
            return len(text) // 4

    def _process_chunks(self, chunks: List[str], metadata: dict = None) -> dict:
        """
        🧩 Обработка текста по частям (chunks)
        
        Args:
            chunks: Список частей текста
            metadata: Дополнительные метаданные
            
        Returns:
            dict: Объединенный результат обработки всех частей
        """
        all_contacts = []
        all_business_contexts = []
        all_commercial_offers = []
        total_processing_time = 0
        
        print(f"🧩 Обрабатываем {len(chunks)} частей текста...")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"   📄 Обработка части {i}/{len(chunks)}...")
            
            try:
                # Обрабатываем каждую часть отдельно
                chunk_result = self._extract_single_chunk(chunk, metadata)
                
                # Собираем результаты
                if chunk_result.get('contacts'):
                    all_contacts.extend(chunk_result['contacts'])
                
                if chunk_result.get('business_context'):
                    all_business_contexts.append(chunk_result['business_context'])
                
                if chunk_result.get('commercial_offers'):
                    all_commercial_offers.extend(chunk_result['commercial_offers'])
                
                total_processing_time += chunk_result.get('processing_time', 0)
                
            except Exception as e:
                print(f"❌ Ошибка обработки части {i}: {e}")
                continue
        
        # Объединяем и дедуплицируем результаты
        unique_contacts = self._deduplicate_contacts(all_contacts)
        combined_business_context = ' '.join(all_business_contexts)
        unique_offers = self._deduplicate_offers(all_commercial_offers)
        
        print(f"✅ Обработка завершена: {len(unique_contacts)} контактов, {len(unique_offers)} предложений")
        
        return {
            'contacts': unique_contacts,
            'business_context': combined_business_context,
            'commercial_offers': unique_offers,
            'provider_used': 'chunked_processing',
            'processing_time': total_processing_time,
            'text_length': sum(len(chunk) for chunk in chunks),
            'chunks_processed': len(chunks),
            'total_contacts_found': len(all_contacts),
            'unique_contacts_found': len(unique_contacts)
        }

    def _extract_single_chunk(self, text: str, metadata: dict = None) -> dict:
        """
        🎯 Обработка одной части текста (без фильтрации по токенам)
        
        Args:
            text: Текст для анализа
            metadata: Дополнительные метаданные
            
        Returns:
            dict: Результат обработки части
        """
        # Создаем хеш контента для кеширования
        content_hash = hashlib.md5(f"{text}_{metadata}".encode()).hexdigest()
        
        # Проверяем кеш результатов (если не тестовый режим)
        if not self.test_mode:
            cached_result = self.result_cache.get_extraction_result(content_hash)
            if cached_result and 'result' in cached_result:
                return cached_result['result']

        # Тестовый режим - возвращаем заранее подготовленный результат
        if self.test_mode:
            return {
                'contacts': [{
                    'name': 'Тестовый Контакт (Chunk)',
                    'email': 'chunk@example.com',
                    'phone': '+7 (999) 123-45-67',
                    'confidence': 0.85
                }],
                'business_context': 'Тестовый контекст из части текста',
                'commercial_offers': [],
                'provider_used': 'test_mode_chunk',
                'processing_time': 0.05
            }

        try:
            # Подготавливаем промпт
            prompt = self._prepare_unified_prompt(text, metadata)
            
            # Отправляем запрос к LLM
            start_time = time.time()
            response = self.config.provider_manager.get_current_provider().generate_response(prompt)
            processing_time = time.time() - start_time
            
            # Парсим ответ
            result = self._parse_llm_response(response)
            result['processing_time'] = processing_time
            result['provider_used'] = self.config.provider_manager.get_current_provider().name
            
            # Кешируем результат
            if not self.test_mode:
                self.result_cache.save_extraction_result(content_hash, result)
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка обработки части текста: {e}")
            return {
                'contacts': [],
                'business_context': '',
                'commercial_offers': [],
                'provider_used': 'error',
                'processing_time': 0,
                'error': str(e)
            }

    def _deduplicate_contacts(self, contacts: List[dict]) -> List[dict]:
        """
        🔄 Дедупликация контактов по email и телефону
        
        Args:
            contacts: Список контактов
            
        Returns:
            List[dict]: Уникальные контакты
        """
        seen = set()
        unique_contacts = []
        
        for contact in contacts:
            # Создаем ключ для дедупликации
            key_parts = []
            if contact.get('email'):
                key_parts.append(contact['email'].lower())
            if contact.get('phone'):
                # Нормализуем телефон для сравнения
                phone = re.sub(r'[^\d+]', '', contact['phone'])
                key_parts.append(phone)
            
            if key_parts:
                key = '|'.join(key_parts)
                if key not in seen:
                    seen.add(key)
                    unique_contacts.append(contact)
            else:
                # Если нет email и телефона, добавляем как есть
                unique_contacts.append(contact)
        
        return unique_contacts

    def _deduplicate_offers(self, offers: List[dict]) -> List[dict]:
        """
        🔄 Дедупликация коммерческих предложений по названию
        
        Args:
            offers: Список предложений
            
        Returns:
            List[dict]: Уникальные предложения
        """
        seen = set()
        unique_offers = []
        
        for offer in offers:
            title = offer.get('title', '').lower().strip()
            if title and title not in seen:
                seen.add(title)
                unique_offers.append(offer)
            elif not title:
                # Если нет названия, добавляем как есть
                unique_offers.append(offer)
        
        return unique_offers
