import asyncio
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
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
from .extractor import ExtractorConfig, RetryConfig


class AsyncContactExtractor:
    """
    🚀 Асинхронный ContactExtractor с параллельной обработкой
    
    Реализует рекомендацию 8 из отчета по архитектуре:
    - Параллельная обработка организаций, контактов и предложений
    - Асинхронные LLM запросы
    - Кеширование результатов
    - Оптимизация производительности
    """

    def __init__(self, config: ExtractorConfig):
        self.config = config
        self.test_mode = config.test_mode

        # Расширенная статистика с асинхронными метриками
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
            'parallel_tasks': 0,
            'chunked_operations': 0,
            'cached_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0.0,
            'total_processing_time': 0.0
        }

        # Кэширование результатов
        self.cache = MultiLevelCache()
        
        # Memory оптимизатор
        self.memory_optimizer = MemoryOptimizer(max_memory_mb=300, gc_threshold_mb=150)
        
        # Text chunker
        self.chunker = TextChunker(config.chunking_config)
        
        # OCR Manager
        self.ocr_manager = config.ocr_manager
        
        # Кэш промптов
        self._prompt_cache: Dict[str, str] = {}
        
        print("🚀 AsyncContactExtractor инициализирован")
        print(f"   📁 Промпты: {self.config.prompts_dir}")
        print(f"   🔧 Провайдеры: {len(self.config.provider_manager.get_llm_providers())}")
        print("   ⚡ Асинхронная обработка: включена")
        print("   💾 Кеширование: включено")

    async def extract_all_data_async(self, text: str, metadata: dict = None) -> dict:
        """
        🚀 Основной асинхронный метод извлечения данных с единым промптом
        
        Использует unified_contact_extraction_structured.txt для извлечения:
        - Организаций
        - Контактов
        - Коммерческих предложений
        - Бизнес-контекста
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        self.stats['async_operations'] += 1

        # Тестовый режим
        if self.test_mode:
            return await self._get_test_data_async(text)

        try:
            # Проверяем кеш
            content_hash = self._generate_content_hash(text, metadata)
            cached_result = await self._get_cached_result_async(content_hash)
            if cached_result:
                self.stats['cache_hits'] += 1
                self.stats['cached_requests'] += 1
                return cached_result
            
            self.stats['cache_misses'] += 1

            # Оптимизация памяти
            text_size_mb = len(text) / 1024 / 1024
            if text_size_mb > 5:
                self.memory_optimizer.optimize_before_processing()

            # Единый запрос к LLM с unified промптом
            prompt = await self._load_prompt_async("unified_contact_extraction_structured.txt")
            
            # Подготавливаем полный контент (письмо + вложения)
            full_content = text
            if metadata and 'attachments_text' in metadata:
                attachments_text = metadata['attachments_text']
                if attachments_text:
                    full_content += f"\n\n=== ВЛОЖЕНИЯ ===\n{attachments_text}"
            
            # Заменяем плейсхолдер на полный контент
            prompt = prompt.replace("{text}", full_content)
            
            # Выполняем единый запрос
            response = await self._make_llm_request_async(prompt, "unified_extraction")
            
            # Извлекаем данные из ответа
            organizations_result = response.get('organizations', []) if response else []
            contacts_result = response.get('contacts', []) if response else []
            offers_result = response.get('commercial_offers', []) if response else []
            business_context = response.get('business_context', '') if response else ''
            
            # Постобработка контактов
            if contacts_result:
                contacts_result = await self._postprocess_contacts_async(contacts_result)
            
            # Формируем итоговый результат
            final_result = {
                'contacts': contacts_result,
                'organizations': organizations_result,
                'commercial_offers': offers_result,
                'business_context': business_context,
                'provider_used': self.config.provider_manager.get_active_provider_name(),
                'text_length': len(text),
                'total_contacts_found': len(contacts_result),
                'total_organizations_found': len(organizations_result),
                'total_offers_found': len(offers_result),
                'async_processing': True,
                'unified_prompt': True
            }
            
            # Кешируем результат
            await self._cache_result_async(content_hash, final_result)
            
            # Обновляем статистику
            processing_time = time.time() - start_time
            self.stats['successful_requests'] += 1
            self.stats['total_processing_time'] += processing_time
            self.stats['avg_processing_time'] = (
                self.stats['total_processing_time'] / self.stats['successful_requests']
            )
            
            final_result['processing_time'] = processing_time
            
            return final_result
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            print(f"❌ Ошибка асинхронной обработки: {e}")
            
            # Fallback на синхронную обработку
            return await self._fallback_sync_processing(text, metadata)



    async def _make_llm_request_async(self, prompt: str, request_type: str) -> dict:
        """
        🤖 Асинхронный запрос к LLM провайдеру с fallback системой
        """
        try:
            # Генерируем уникальный ID запроса
            import uuid
            request_id = str(uuid.uuid4())
            
            # Подготавливаем данные запроса для fallback системы в формате Replicate API
            # Получаем версию модели из конфигурации провайдера
            provider_config = self.config.provider_manager.get_current_provider_config()
            model_version = provider_config.model if provider_config else "deepseek-ai/deepseek-v3"
            
            request_data = {
                "version": model_version,
                "input": {
                    "prompt": prompt,
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "system_prompt": "You are a helpful assistant that extracts contact information from text."
                }
            }
            
            # Используем асинхронную fallback систему
            response_data = await self.config.provider_manager.make_request_with_fallback(
                request_data=request_data,
                request_id=request_id
            )
            
            # Извлекаем текст ответа из структуры ответа
            response = response_data.get('content', '') if isinstance(response_data, dict) else str(response_data)
            
            # Парсим ответ
            if response and response.strip():
                return self._parse_llm_response(response)
            
            return {}
            
        except Exception as e:
            print(f"❌ Ошибка LLM запроса ({request_type}): {e}")
            return {}

    async def _postprocess_contacts_async(self, contacts: List[dict]) -> List[dict]:
        """
        🔧 Асинхронная постобработка контактов
        """
        if not contacts:
            return contacts
        
        # Нормализация телефонов асинхронно
        tasks = []
        for contact in contacts:
            if 'phone' in contact and contact['phone']:
                task = self._normalize_phone_async(contact)
                tasks.append(task)
            else:
                tasks.append(asyncio.create_task(self._return_contact_async(contact)))
        
        processed_contacts = await asyncio.gather(*tasks)
        return processed_contacts

    async def _normalize_phone_async(self, contact: dict) -> dict:
        """
        📞 Асинхронная нормализация телефона
        """
        loop = asyncio.get_event_loop()
        normalized_phone = await loop.run_in_executor(
            None,
            self.config.phone_normalizer.normalize,
            contact['phone']
        )
        contact['phone'] = normalized_phone
        return contact

    async def _return_contact_async(self, contact: dict) -> dict:
        """
        📋 Возврат контакта без изменений (для совместимости с gather)
        """
        return contact

    async def _merge_results_async(
        self, 
        organizations: List[dict], 
        contacts: List[dict], 
        offers: List[dict],
        text: str,
        metadata: dict = None
    ) -> dict:
        """
        🔄 Асинхронное объединение результатов
        
        Теперь business_context - это полноценный JSON-объект с детальной аналитикой:
        - business_summary: краткое резюме всего контента
        - main_purpose: основная цель письма/документов
        - content_quality: оценка качества и полноты информации
        - key_insights: ключевые выводы и находки
        """
        # Извлекаем структурированный бизнес-контекст
        business_context_data = await self._extract_business_context_async(text, metadata)
        
        return {
            'contacts': contacts,
            'organizations': organizations,
            'commercial_offers': offers,
            'business_context': business_context_data,  # Теперь это dict, а не строка
            'provider_used': self.config.provider_manager.get_active_provider_name(),
            'text_length': len(text),
            'total_contacts_found': len(contacts),
            'total_organizations_found': len(organizations),
            'total_offers_found': len(offers),
            'async_processing': True,
            # Добавляем краткое резюме для быстрого доступа
            'business_summary': business_context_data.get('business_summary', 'Нет резюме'),
            'main_purpose': business_context_data.get('main_purpose', 'неопределено')
        }



    async def _load_prompt_async(self, filename: str) -> str:
        """
        📝 Асинхронная загрузка промпта
        """
        if filename in self._prompt_cache:
            return self._prompt_cache[filename]
        
        prompts_dir = self.config.prompts_dir or Path(__file__).parent.parent.parent / "prompts"
        prompt_path = prompts_dir / filename
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"❌ Промпт не найден: {prompt_path}")
        
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            self._read_file_sync,
            prompt_path
        )
        
        self._prompt_cache[filename] = content
        return content

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
  "commercial_offers": [],
  "organizations": []
}}"""
    
    def load_prompt(self, filename: str) -> str:
        """📝 Синхронная загрузка промпта из файла (для совместимости)"""
        try:
            prompts_dir = self.config.prompts_dir or Path(__file__).parent.parent.parent / "prompts"
            prompt_path = prompts_dir / filename
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
                    
        except Exception as e:
            print(f"⚠️  Ошибка загрузки промпта {filename}: {e}")
            return "Проанализируй текст и верни JSON с контактами, организациями и коммерческими предложениями."
    
    def _parse_llm_response(self, response_text: str) -> dict:
        """🔍 Парсинг JSON ответа от LLM с обработкой ошибок"""
        try:
            # Очистка ответа от markdown разметки
            cleaned_text = response_text.strip()
            
            # Удаляем markdown блоки если есть
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Попытка парсинга JSON
            try:
                result = json.loads(cleaned_text)
                return result
            except json.JSONDecodeError as e:
                print(f"⚠️  Ошибка парсинга JSON: {e}")
                self.stats['json_parsing_errors'] += 1
                
                # Попытка исправления распространенных ошибок
                fixed_text = self._fix_common_json_errors(cleaned_text)
                try:
                    result = json.loads(fixed_text)
                    print("✅ JSON исправлен автоматически")
                    return result
                except json.JSONDecodeError:
                    print("❌ Не удалось исправить JSON автоматически")
                    return self._create_empty_result()
                    
        except Exception as e:
            print(f"❌ Критическая ошибка парсинга ответа: {e}")
            return self._create_empty_result()
    
    def _fix_common_json_errors(self, text: str) -> str:
        """🔧 Исправление распространенных ошибок в JSON"""
        # Удаление лишних запятых перед закрывающими скобками
        text = re.sub(r',\s*([}\]])', r'\1', text)
        # Добавление кавычек к ключам без кавычек
        text = re.sub(r'(\w+):', r'"\1":', text)
        return text
    
    def _create_empty_result(self) -> dict:
        """📝 Создание пустого результата при ошибках парсинга"""
        return {
            'contacts': [],
            'organizations': [],
            'commercial_offers': [],
            'business_context': '',
            'error': 'JSON parsing failed'
        }

    def _read_file_sync(self, file_path: Path) -> str:
        """
        📄 Синхронное чтение файла (для executor)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    async def _get_cached_result_async(self, content_hash: str) -> Optional[dict]:
        """
        💾 Асинхронное получение результата из кеша
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.cache.get_extraction_result,
            content_hash
        )

    async def _cache_result_async(self, content_hash: str, result: dict) -> None:
        """
        💾 Асинхронное кеширование результата
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.cache.cache_extraction_result,
            content_hash,
            result
        )

    def _generate_content_hash(self, text: str, metadata: dict = None) -> str:
        """
        🔐 Генерация хеша контента для кеширования
        """
        content = text
        if metadata:
            content += json.dumps(metadata, sort_keys=True)
        
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _parse_llm_response(self, response_text: str) -> dict:
        """
        📊 Парсинг ответа LLM
        """
        try:
            # Очистка ответа
            cleaned_response = response_text.strip()
            
            # Поиск JSON блока
            json_start = cleaned_response.find('{')
            json_end = cleaned_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = cleaned_response[json_start:json_end]
                return json.loads(json_text)
            
            return {}
            
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            return {}

    async def _get_test_data_async(self, text: str) -> dict:
        """
        🧪 Асинхронные тестовые данные
        """
        await asyncio.sleep(0.1)  # Имитация обработки
        
        return {
            'contacts': [{
                'name': 'Тестовый Контакт (Async)',
                'email': 'async@example.com',
                'phone': '+7 (999) 123-45-67',
                'organization': 'Async Организация',
                'position': 'Async Должность',
                'city': 'Async Город',
                'website': 'https://async.example.com',
                'inn': '1234567890',
                'confidence': 0.95
            }],
            'business_context': 'Async бизнес-контекст для демонстрации',
            'commercial_offers': [{
                'title': 'Async предложение',
                'description': 'Описание async коммерческого предложения',
                'price': '100000 руб.',
                'confidence': 0.9
            }],
            'organizations': [{
                'name': 'Async Организация',
                'inn': '1234567890',
                'website': 'https://async.example.com',
                'confidence': 0.95
            }],
            'provider_used': 'async_test_mode',
            'processing_time': 0.1,
            'text_length': len(text),
            'chunks_processed': 1,
            'total_contacts_found': 1,
            'unique_contacts_found': 1,
            'async_processing': True,
            'test_mode': True
        }

    async def _fallback_sync_processing(self, text: str, metadata: dict = None) -> dict:
        """
        🛡️ Fallback на синхронную обработку при ошибках
        """
        print("🔄 Переключение на синхронную обработку...")
        
        # Импортируем синхронный экстрактор
        from .extractor import ContactExtractor
        
        sync_extractor = ContactExtractor(self.config)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            sync_extractor.extract_all_data,
            text,
            metadata
        )
        
        result['async_processing'] = False
        result['fallback_used'] = True
        
        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        📊 Получение статистики асинхронного экстрактора
        """
        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
            ) * 100,
            'success_rate': (
                self.stats['successful_requests'] / max(1, self.stats['total_requests'])
            ) * 100,
            'avg_parallel_tasks': (
                self.stats['parallel_tasks'] / max(1, self.stats['async_operations'])
            )
        }