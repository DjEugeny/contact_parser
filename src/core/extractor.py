#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Новый ContactExtractor с Dependency Injection
Фаза 5: Архитектурная оптимизация
"""

import asyncio
import copy
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
from ..postprocessing.postprocessor import PostProcessor
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
        # ВРЕМЕННО ОТКЛЮЧЕНО: cache_config = CacheConfig(
        #     extraction_ttl=3600,  # 1 час для результатов извлечения
        #     ocr_ttl=86400,        # 24 часа для OCR результатов
        #     prompt_ttl=7200,      # 2 часа для промптов
        #     enable_local_cache=True,
        #     enable_compression=True
        # )
        # self.result_cache = get_result_cache(cache_config)
        self.result_cache = None
        print("💾 EXTRACTOR КЭШИРОВАНИЕ ОТКЛЮЧЕНО ДЛЯ ОТЛАДКИ")

        self.postprocessor = PostProcessor()

        print("🎯 Новый ContactExtractor инициализирован с Dependency Injection")
        print(f"   📁 Промпты: {self.config.prompts_dir}")
        print(f"   🔧 Провайдеры: {len(self.config.provider_manager.get_llm_providers())}")
        print("   📞 PhoneNormalizer: интегрирован")
        print("   📊 JSON Schema Validator: интегрирован")
        print("   🔍 OCR Manager: интегрирован")
        print("   🏪 Result Cache: включен")

    def _build_empty_result(self) -> Dict[str, Any]:
        """📦 Создание пустого результата в формате JSON-схемы"""
        return {
            "organizations": [],
            "contacts": [],
            "business_context": "",
            "summary": {
                "topic": None,
                "product_interest": None,
                "communication_stage": None,
                "request_type": None
            },
            "key_points": [],
            "commercial_offers": [],
            "interactions": []
        }

    def _apply_postprocessing(self, result: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """✅ Постобработка валидного ответа LLM через централизованный PostProcessor"""
        try:
            email_data = metadata or {}
            return self.postprocessor.process_llm_response(result, email_data=email_data)
        except Exception as exc:
            print(f"⚠️ Ошибка постобработки, возвращаю исходный результат: {exc}")
            return result
    def load_prompt(self, filename: str) -> str:
        """
        📝 Загрузка промпта с поддержкой версионирования
        
        Если filename = "unified_contact_extraction_structured.txt", 
        использует систему версионирования (загружает текущую версию из version.json).
        Для других промптов - загружает напрямую.
        """
        # Для unified промпта используем систему версионирования
        if filename == "unified_contact_extraction_structured.txt":
            try:
                from src.utils.prompt_loader import load_prompt as load_versioned_prompt
                prompt = load_versioned_prompt()  # Загружает текущую версию из version.json
                return prompt
            except Exception as e:
                # Fallback на старый метод если версионирование не работает
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Ошибка загрузки версионированного промпта: {e}")
                logger.warning("⚠️ Используется fallback на прямую загрузку файла")
        
        # Для других промптов или fallback - загружаем напрямую
        prompts_dir = self.config.prompts_dir or Path(__file__).parent.parent.parent / "prompts"
        prompt_path = prompts_dir / filename

        if not prompt_path.exists():
            raise FileNotFoundError(f"❌ Промпт не найден: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        
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
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Проверяем кеш результатов (если не тестовый режим)
        # if not self.test_mode:
        #     cached_result = self.result_cache.get_extraction_result(content_hash)
        #     if cached_result and 'result' in cached_result:
        #         print(f"💾 Используем кешированный результат: {content_hash[:8]}...")
        #         self.stats['cached_requests'] += 1
        #         return cached_result['result']
        # Кэш отключен - делаем свежий запрос

        # Тестовый режим - возвращаем заранее подготовленный результат
        if self.test_mode:
            print("🧪 Тестовый режим: возвращаем тестовые данные")
            test_result = self._build_empty_result()
            test_result["organizations"] = [{
                "organization_id": 1,
                "name": "Тестовая Организация",
                "inn": "1234567890",
                "website": "https://test.example.com",
                "city": "Москва",
                "address": "ул. Тестовая, д. 1",
                "emails": ["info@test.example.com"],
                "phones": ["+7 (495) 000-00-00"]
            }]
            test_result["contacts"] = [{
                "contact_id": 1,
                "name": "Тестовый Контакт",
                "organization_id": 1,
                "position": "Менеджер",
                "email": "test@example.com",
                "phones": [{"type": "mobile", "number": "+7 (999) 123-45-67"}],
                "city": "Москва",
                "address": None,
                "role_in_message": "sender",
                "confidence": 0.95
            }]
            test_result["business_context"] = "Тестовый бизнес-контекст для демонстрации"
            test_result["summary"] = {
                "topic": "Тестовые переговоры",
                "product_interest": "Лабораторное оборудование",
                "communication_stage": "отправка КП",
                "request_type": "запрос КП"
            }
            test_result["key_points"] = [
                "Получен запрос на КП",
                "Необходимо подтвердить сроки поставки",
                "Контакт ожидает ответ до пятницы"
            ]
            test_result["commercial_offers"] = [{
                "found": True,
                "offer_type": "Приборы",
                "offer_number": "КП-2025-001",
                "offer_date": "2025-01-15",
                "end_user": "Лаборатория молекулярной диагностики",
                "end_user_inn": "123456789012",
                "intermediary": "ООО «Медтехника»",
                "intermediary_date": "г. Москва, менеджер, +7 (495) 123-45-67",
                "payment_terms": "50% предоплата, 50% после поставки",
                "delivery_time": "30 дней",
                "delivery_terms": "EXW Москва",
                "valid_until": "2025-02-15",
                "equipment_items": [
                    {
                        "name": "Амплификатор DNA Pro",
                        "model": "DT-96",
                        "article": "AP-001",
                        "quantity": 2,
                        "unit_price": 1500000,
                        "total_price": 3000000,
                        "vat": "20%"
                    }
                ],
                "total_cost": 3000000,
                "comments": "Включена доставка и монтаж"
            }]
            test_result["interactions"] = [{
                "interaction_local_id": 1,
                "contact_id": 1,
                "organization_id": 1,
                "message_subject": "Тестовое письмо",
                "message_date": "2025-05-12T10:21:00+03:00",
                "message_id_hint": "<test_message_id@example.com>",
                "role_in_message": "sender",
                "interaction_type": "sent_quote",
                "summary": "Тестовый контакт отправил КП",
                "attachments": ["Тестовое КП.pdf"],
                "confidence": 0.9
            }]
            raw_snapshot = copy.deepcopy(test_result)
            test_result.update({
                "provider_used": "test_mode",
                "model": "test_mode",
                "processing_time": 0.1,
                "text_length": len(text),
                "chunks_processed": 1,
                "total_contacts_found": len(test_result["contacts"]),
                "unique_contacts_found": len(test_result["contacts"]),
                "test_mode": True
            })
            test_result["raw_llm_result"] = raw_snapshot
            return test_result

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

            # ВРЕМЕННО ОТКЛЮЧЕНО: 💾 Проверяем кэш перед запросом (Фаза 6)
            # prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
            # cached_result = self.cache.get_llm_response(prompt_hash, "unified_extraction")

            # if cached_result:
            #     print("💾 Используем кэшированный результат")
            #     llm_response = cached_result
            #     self.stats['cached_requests'] += 1
            # else:
            # Кэш отключен
            print("🤖 Запрос к LLM провайдерам...")
            request_data = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 4000
            }
            
            # Используем синхронную версию fallback системы
            llm_response = asyncio.run(
                self.config.provider_manager.make_request_with_fallback(
                    request_data=request_data
                )
            )

            # ВРЕМЕННО ОТКЛЮЧЕНО: 💾 Кэшируем результат (Фаза 6)
            # self.cache.set_llm_response(prompt_hash, "unified_extraction", llm_response)

            # Парсинг JSON ответа
            raw_content = llm_response.get('content') if isinstance(llm_response, dict) else llm_response

            # ИСПРАВЛЕНИЕ: Сохраняем исходный ответ от LLM ДО обработки
            if isinstance(raw_content, str):
                try:
                    # Пытаемся распарсить исходный JSON без обработки
                    raw_snapshot = json.loads(raw_content)
                except json.JSONDecodeError:
                    # Если не получается, сохраняем как строку
                    raw_snapshot = {"raw_response": raw_content}
                result = self._parse_llm_response(raw_content)
            else:
                raw_snapshot = copy.deepcopy(raw_content)
                result = raw_content

            # Валидация через validate_llm_response (с автокоррекцией)
            print("🔍 Применение строгой JSON Schema валидации...")
            is_valid, errors, corrected_result = self.config.json_validator.validate_llm_response(result)

            if is_valid:
                print("✅ JSON Schema валидация пройдена успешно")
                result = corrected_result
            else:
                print(f"❌ Валидация не удалась: {errors}")
                result = corrected_result  # Используем fallback результат
            if isinstance(result, dict):
                result.setdefault('original_response', raw_content)
            processed_result = self._apply_postprocessing(result, metadata)

            print(
                f"✅ После постобработки: {len(processed_result.get('contacts', []))} контактов, "
                f"{len(processed_result.get('organizations', []))} организаций, "
                f"{len(processed_result.get('commercial_offers', []))} КП"
            )

            provider_name = (
                llm_response.get('provider') if isinstance(llm_response, dict) else None
            )
            model_name = (
                llm_response.get('model', 'Unknown') if isinstance(llm_response, dict) else 'Unknown'
            )
            response_time = (
                llm_response.get('response_time', 0) if isinstance(llm_response, dict) else 0
            )

            processed_result.update({
                'provider_used': provider_name,
                'model': model_name,
                'processing_time': response_time,
                'text_length': len(text),
                'chunks_processed': 1,
                'total_contacts_found': len(processed_result.get('contacts', [])),
                'unique_contacts_found': len(processed_result.get('contacts', []))
            })
            processed_result['raw_llm_result'] = raw_snapshot

            # ВРЕМЕННО ОТКЛЮЧЕНО: if not self.test_mode:
            #     self.result_cache.cache_extraction_result(content_hash, processed_result)

            self.stats['successful_requests'] += 1
            return processed_result

        except Exception as e:
            self.stats['failed_requests'] += 1
            print(f"❌ Ошибка в extract_all_data: {e}")

            fallback = self.config.json_validator.graceful_degradation_fallback({
                'error': str(e),
                'text_length': len(text)
            })
            processed_fallback = self._apply_postprocessing(fallback, metadata)
            processed_fallback['raw_llm_result'] = copy.deepcopy(fallback)
            return processed_fallback

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
                    fallback = self._build_empty_result()
                    fallback.update({
                        'provider_used': 'async_timeout_error',
                        'model': 'Unknown',
                        'processing_time': 120.0,
                        'error': 'Превышен таймаут асинхронной обработки',
                        'attempts_made': attempt + 1
                    })
                    return fallback
                    
            except Exception as e:
                print(f"❌ Ошибка асинхронной обработки (попытка {attempt + 1}): {e}")
                
                if attempt == self.config.retry_config.max_attempts - 1:
                    # Последняя попытка - возвращаем ошибку
                    fallback = self._build_empty_result()
                    fallback.update({
                        'provider_used': 'async_error',
                        'model': 'Unknown',
                        'processing_time': 0,
                        'error': f'Асинхронная обработка не удалась: {str(e)}',
                        'attempts_made': attempt + 1
                    })
                    return fallback
                
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
            'model': 'Unknown',
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
            fallback = self._build_empty_result()
            fallback.update({
                'provider_used': 'error_handler',
                'model': 'Unknown',
                'processing_time': 0,
                'error': f'Критическая ошибка обработки: {str(e)}'
            })
            return fallback

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
        example_template = json.dumps(self._build_empty_result(), ensure_ascii=False, indent=2)
        return (
            "Проанализируй следующий текст и верни строго валидный JSON, соответствующий шаблону:"\
            f"\n\nТекст: {text}\n\nШаблон:\n{example_template}"
        )

    def _parse_llm_response(self, response_text: str) -> dict:
        """
        🔍 Парсинг ответа LLM с валидацией JSON Schema

        Args:
            response_text: Сырой текст ответа от LLM

        Returns:
            dict: Валидированный и обработанный результат
        """
        print(f"🔍 Получен ответ LLM длиной {len(response_text)} символов")
        
        try:
            # Удален ошибочный фикс пробелов - Replicate возвращает корректный JSON
            
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
            print(f"   Позиция ошибки: строка {e.lineno}, колонка {e.colno}")
            
            # Показываем контекст ошибки
            lines = response_text.split('\n')
            if e.lineno <= len(lines):
                error_line = lines[e.lineno - 1] if e.lineno > 0 else ""
                print(f"   Проблемная строка: {error_line}")
                if e.colno > 0 and e.colno <= len(error_line):
                    pointer = " " * (e.colno - 1) + "^"
                    print(f"   Указатель:       {pointer}")

            # Попытка исправления распространенных ошибок
            print(f"🛡️ Применяем graceful degradation fallback")
            fixed_text = self._fix_common_json_errors(response_text)
            try:
                result = json.loads(fixed_text)
                print(f"✅ JSON успешно исправлен и распарсен")
                return result
            except json.JSONDecodeError as e2:
                print(f"❌ Исправление не помогло: {e2}")
                # Graceful degradation
                fallback = self.config.json_validator.graceful_degradation_fallback({})
                if isinstance(fallback, dict):
                    fallback.setdefault('original_response', response_text[:500] + "..." if len(response_text) > 500 else response_text)
                return fallback

        except Exception as e:
            print(f"❌ Неожиданная ошибка парсинга: {e}")
            fallback = self.config.json_validator.graceful_degradation_fallback({})
            if isinstance(fallback, dict):
                fallback.setdefault('original_response', response_text)
            return fallback

    def _fix_common_json_errors(self, text: str) -> str:
        """🔧 Базовое исправление JSON ошибок"""
        print(f"🔧 Попытка исправления JSON ошибок...")
        
        original_text = text
        
        # 1. Удаление markdown блоков кода
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()
        
        # 2. Исправляем числа с пробелами ("1 . 0" -> "1.0")
        text = re.sub(r'([0-9])\s+\.\s+([0-9])', r'\1.\2', text)
        
        # 3. Удаляем trailing запятые
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        if text != original_text:
            print(f"🔧 JSON был изменен для исправления ошибок")
            print(f"   Длина до: {len(original_text)}, после: {len(text)}")
        
        return text

    # Удален метод _fix_replicate_spaces - он создавал проблемы, а не решал их

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
                fallback = self._build_empty_result()
                fallback.update({
                    'success': False,
                    'error': ocr_result.get('error', 'OCR обработка не удалась'),
                    'metadata': {
                        'file_path': file_path,
                        'ocr_used': True,
                        'ocr_cached': ocr_result.get('cached', False)
                    }
                })
                return fallback
            
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
            fallback = self._build_empty_result()
            fallback.update({
                'success': False,
                'error': f'Ошибка обработки файла: {str(e)}',
                'metadata': {
                    'file_path': file_path,
                    'ocr_used': True,
                    'error_type': type(e).__name__
                }
            })
            return fallback

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
        """🧩 Обработка текста по частям с последующей объединённой постобработкой"""
        aggregated_result = self._build_empty_result()
        total_processing_time = 0.0
        summary_candidates: List[Dict[str, Any]] = []
        context_parts: List[str] = []

        print(f"🧩 Обрабатываем {len(chunks)} частей текста...")

        for index, chunk in enumerate(chunks, 1):
            print(f"   📄 Обработка части {index}/{len(chunks)}...")

            try:
                chunk_metadata = dict(metadata or {})
                chunk_metadata["chunk_index"] = index
                chunk_result = self._extract_single_chunk(chunk, chunk_metadata)

                aggregated_result['organizations'].extend(chunk_result.get('organizations', []))
                aggregated_result['contacts'].extend(chunk_result.get('contacts', []))
                aggregated_result['commercial_offers'].extend(chunk_result.get('commercial_offers', []))
                aggregated_result['interactions'].extend(chunk_result.get('interactions', []))
                aggregated_result['key_points'].extend(chunk_result.get('key_points', []))

                if isinstance(chunk_result.get('summary'), dict):
                    summary_candidates.append(chunk_result['summary'])
                if chunk_result.get('business_context'):
                    context_parts.append(str(chunk_result['business_context']))

                total_processing_time += chunk_result.get('processing_time', 0.0)
            except Exception as exc:
                print(f"❌ Ошибка обработки части {index}: {exc}")
                continue

        # Собираем summary из первых непустых полей
        for summary in summary_candidates:
            for key, value in summary.items():
                if value and not aggregated_result['summary'].get(key):
                    aggregated_result['summary'][key] = value

        aggregated_result['business_context'] = ' \n'.join(context_parts).strip()

        processed_aggregated = self._apply_postprocessing(aggregated_result, metadata)
        processed_aggregated.update({
            'provider_used': 'chunked_processing',
            'model': 'Unknown',
            'processing_time': total_processing_time,
            'text_length': sum(len(chunk) for chunk in chunks),
            'chunks_processed': len(chunks),
            'total_contacts_found': len(processed_aggregated.get('contacts', [])),
            'unique_contacts_found': len(processed_aggregated.get('contacts', []))
        })

        return processed_aggregated

    def _extract_single_chunk(self, text: str, metadata: dict = None) -> dict:
        """
        🎯 Обработка одной части текста (без фильтрации по токенам)
        
        Args:
            text: Текст для анализа
            metadata: Дополнительные метаданные
            
        Returns:
            dict: Результат обработки части
        """
        if self.test_mode:
            chunk_result = self._build_empty_result()
            chunk_result.update({
                'provider_used': 'test_mode_chunk',
                'model': 'test_mode',
                'processing_time': 0.05
            })
            return chunk_result

        try:
            prompt = self._prepare_unified_prompt(text, metadata)
            prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()

            cached_llm = self.cache.get_llm_response(prompt_hash, "unified_extraction_chunk")

            if cached_llm:
                llm_response = cached_llm
            else:
                request_data = {
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
                start_time = time.time()
                llm_response = self.config.provider_manager.make_request_sync(
                    provider=self.config.provider_manager.get_best_available_provider(),
                    request_data=request_data
                )
                elapsed = time.time() - start_time
                if isinstance(llm_response, dict):
                    llm_response.setdefault('response_time', elapsed)
                if not self.test_mode:
                    self.cache.set_llm_response(prompt_hash, "unified_extraction_chunk", llm_response)

            if isinstance(llm_response, dict) and 'content' in llm_response:
                raw_result = self._parse_llm_response(llm_response['content'])
            else:
                raw_result = llm_response

            _, _, corrected_result = self.config.json_validator.validate_llm_response(raw_result)
            provider_name = (
                llm_response.get('provider') if isinstance(llm_response, dict) else None
            )
            model_name = (
                llm_response.get('model', 'Unknown') if isinstance(llm_response, dict) else 'Unknown'
            )
            response_time = (
                llm_response.get('response_time', 0) if isinstance(llm_response, dict) else 0
            )

            corrected_result.update({
                'provider_used': provider_name,
                'model': model_name,
                'processing_time': response_time,
                'text_length': len(text),
                'chunks_processed': 1
            })

            return corrected_result

        except Exception as e:
            print(f"❌ Ошибка обработки части текста: {e}")
            fallback = self._build_empty_result()
            fallback.update({
                'provider_used': 'chunk_error',
                'model': 'Unknown',
                'processing_time': 0,
                'error': str(e)
            })
            return fallback
