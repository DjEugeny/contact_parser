#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 LLM экстрактор контактов с JSON Schema валидацией и повторными запросами
"""

import json
import re
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import concurrent.futures
from functools import partial

from dotenv import load_dotenv
import os

# Импорт для токен-ориентированного chunking
try:
    import tiktoken
except ImportError:
    tiktoken = None
    print("⚠️ tiktoken не установлен, используется символьный chunking")

# Загружаем переменные окружения
load_dotenv()


class ContactExtractor:
    """🔥 Экстрактор контактов с LLM и JSON Schema валидацией + Fallback система"""
    
    def __init__(self, test_mode=False, config_path=None):
        self.test_mode = test_mode
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "providers.json"
        
        # Загружаем конфигурацию провайдеров
        self.provider_config = self._load_provider_config()
        
        # Настройка провайдеров с учетом конфигурации
        self.providers = self._initialize_providers()
        
        # Устанавливаем текущего провайдера согласно конфигурации
        self.current_provider = self._get_first_active_provider()
        
        # Максимальное количество попыток fallback
        self.max_fallback_attempts = 2
        
        # Папка с промптами
        current_file = Path(__file__)
        project_root = current_file.parent.parent  # Поднимаемся на уровень выше от src к корню проекта
        self.prompts_dir = project_root / "prompts"
        
        # Расширенная статистика
        self.stats = {
             'total_requests': 0,
             'successful_requests': 0,
             'failed_requests': 0,
             'retry_attempts': 0,
             'json_validation_errors': 0,
             'fallback_switches': 0,
             'provider_failures': {
                 'openrouter': 0,
                 'groq': 0,
                 'replicate': 0
             }
         }
        
        # Валидация конфигурации при инициализации
        self._validate_configuration()

        print(f"🤖 ContactExtractor инициализирован (test_mode={test_mode})")
        print(f"   📁 Конфигурация: {self.config_path}")
        print(f"   🔄 Fallback система: OpenRouter -> Groq -> Replicate")
        print(f"   🎯 Текущий провайдер: {self.providers[self.current_provider]['name']}")
        print("   ✅ Конфигурация провайдеров валидирована")

    def _validate_configuration(self):
        """✅ Валидация конфигурации при инициализации"""
        print("🔍 Валидация конфигурации...")

        # Проверка наличия API ключей
        required_keys = ['OPENROUTER_API_KEY', 'GROQ_API_KEY', 'REPLICATE_API_KEY']
        missing_keys = []
        for key in required_keys:
            if not os.getenv(key):
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(f"❌ Отсутствуют обязательные API ключи: {', '.join(missing_keys)}")

        # Проверка доступности провайдеров
        active_providers = 0
        for provider_id, provider in self.providers.items():
            if provider['api_key']:
                active_providers += 1
                print(f"   ✅ {provider['name']}: API ключ найден")
            else:
                print(f"   ⚠️  {provider['name']}: API ключ отсутствует")

        if active_providers == 0:
            raise ValueError("❌ Нет ни одного провайдера с API ключом")

        # Проверка сетевых настроек (базовая)
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            print("   ✅ Сетевое подключение: доступно")
        except OSError:
            print("   ⚠️  Сетевое подключение: ограничено (работа возможна только с кэшем)")

        print("✅ Валидация конфигурации завершена успешно")

    def _initialize_providers(self) -> dict:
        """🔧 Инициализация провайдеров с учетом конфигурации"""
        # Базовая структура провайдеров с техническими настройками
        providers = {
            'openrouter': {
                'name': 'OpenRouter',
                'api_key': os.getenv('OPENROUTER_API_KEY'),
                'model': os.getenv('OPENROUTER_MODEL'),
                'base_url': os.getenv('OPENROUTER_BASE_URL', "https://openrouter.ai/api/v1/chat/completions"),
                'priority': 3,  # Значение по умолчанию, будет переопределено из конфигурации
                'active': False,
                'failure_count': 0,
                'last_failure': None,
                'headers': {
                    'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://localhost:3000',
                    'X-Title': 'Contact Extractor LLM'
                }
            },
            'groq': {
                'name': 'Groq',
                'api_key': os.getenv('GROQ_API_KEY'),
                'model': os.getenv('GROQ_MODEL'),
                'base_url': os.getenv('GROQ_BASE_URL', "https://api.groq.com/openai/v1/chat/completions"),
                'priority': 2,  # Значение по умолчанию, будет переопределено из конфигурации
                'active': False,
                'failure_count': 0,
                'last_failure': None,
                'headers': {
                    'Authorization': f'Bearer {os.getenv("GROQ_API_KEY")}',
                    'Content-Type': 'application/json'
                }
            },
            'replicate': {
                'name': 'Replicate',
                'api_key': os.getenv('REPLICATE_API_KEY'),
                'model': os.getenv('REPLICATE_MODEL'),
                'base_url': "https://api.replicate.com/v1/predictions",
                'priority': 1,  # Значение по умолчанию, будет переопределено из конфигурации
                'active': True,
                'failure_count': 0,
                'last_failure': None,
                'headers': {
                    'Authorization': f'Bearer {os.getenv("REPLICATE_API_KEY")}',
                    'Content-Type': 'application/json'
                }
            }
        }
        
        # Применяем настройки из конфигурации providers.json
        if self.provider_config and 'provider_settings' in self.provider_config:
            for provider_id, provider_data in providers.items():
                if provider_id in self.provider_config['provider_settings']:
                    config = self.provider_config['provider_settings'][provider_id]
                    
                    # Обновляем настройки приоритета и активности из конфигурации
                    if 'enabled' in config:
                        provider_data['active'] = config['enabled']
                    if 'priority' in config:
                        provider_data['priority'] = config['priority']
                    
                    print(f"✅ Провайдер {provider_data['name']}: настройки обновлены из конфигурации")
        
        return providers
    
    def _get_first_active_provider(self) -> str:
        """🎯 Получение первого активного провайдера по приоритету"""
        active_providers = [
            (pid, provider) for pid, provider in self.providers.items()
            if provider['active'] and provider['api_key']
        ]
        
        if not active_providers:
            print("⚠️ Нет активных провайдеров с API ключами, используем openrouter")
            return 'openrouter'
        
        # Сортируем по приоритету и возвращаем первый
        active_providers.sort(key=lambda x: x[1]['priority'])
        return active_providers[0][0]
    
    def _load_provider_config(self) -> dict:
        """📁 Загрузка конфигурации провайдеров из файла"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"✅ Конфигурация провайдеров загружена из {self.config_path}")
                    return config
            else:
                print(f"⚠️ Файл конфигурации не найден: {self.config_path}")
                return {}
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации провайдеров: {e}")
            return {}
    
    def _load_prompt(self, filename: str) -> str:
        """📄 Загрузка промпта из файла"""
        
        prompt_path = self.prompts_dir / filename
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content
        except FileNotFoundError:
            print(f"❌ Промпт не найден: {prompt_path}")
            return f"ERROR: Промпт {filename} не найден"
        except Exception as e:
            print(f"❌ Ошибка загрузки промпта {filename}: {e}")
            return f"ERROR: Не удалось загрузить {filename}"
    
    def _validate_json_schema(self, response_data: dict) -> bool:
        """✅ Улучшенная валидация JSON Schema для ответа LLM"""
        
        if not isinstance(response_data, dict):
            print("❌ Ответ должен быть объектом")
            return False
        
        required_fields = ['contacts', 'business_context', 'commercial_offers']
        
        # Проверяем основные поля
        for field in required_fields:
            if field not in response_data:
                print(f"❌ Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем типы основных полей
        if not isinstance(response_data['business_context'], str):
            print("❌ Поле 'business_context' должно быть строкой")
            return False
            
        if not isinstance(response_data['commercial_offers'], list):
            print("❌ Поле 'commercial_offers' должно быть списком")
            return False
        
        # Проверяем структуру contacts
        if not isinstance(response_data['contacts'], list):
            print("❌ Поле 'contacts' должно быть списком")
            return False
        
        # Проверяем каждый контакт
        valid_contacts = []
        for i, contact in enumerate(response_data['contacts']):
            if not isinstance(contact, dict):
                print(f"⚠️ Контакт {i} не является объектом, пропускаем")
                continue
            
            # Проверяем обязательные поля контакта
            contact_required = ['name', 'email', 'phone', 'organization', 'confidence']
            
            for field in contact_required:
                if field not in contact:
                    print(f"⚠️ Контакт {i}: отсутствует поле {field}, добавляем пустое значение")
                    contact[field] = '' if field != 'confidence' else 0.0
            
            # Используем детальную валидацию
            if self._validate_contact_fields(contact, i):
                valid_contacts.append(contact)
        
        # Обновляем список контактов только валидными
        response_data['contacts'] = valid_contacts
        
        # Считаем валидацию успешной, если есть хотя бы основные поля
        # (даже если некоторые контакты были отфильтрованы)
        return True

    def _validate_contact_fields(self, contact: dict, index: int) -> bool:
        """🔍 Детальная валидация полей контакта"""
        
        # Валидация email
        email = contact.get('email', '')
        if email and not self._is_valid_email(email):
            print(f"⚠️ Контакт {index}: некорректный email '{email}'")
            contact['email'] = ''  # Очищаем некорректный email
        
        # Валидация телефона
        phone = contact.get('phone', '')
        if phone and not self._is_valid_phone(phone):
            print(f"⚠️ Контакт {index}: некорректный телефон '{phone}'")
            contact['phone'] = ''  # Очищаем некорректный телефон
        
        # Валидация confidence
        confidence = contact.get('confidence', 0)
        if not isinstance(confidence, (int, float)):
            print(f"⚠️ Контакт {index}: confidence должен быть числом, получен {type(confidence)}")
            contact['confidence'] = 0.0
        elif confidence < 0 or confidence > 1:
            print(f"⚠️ Контакт {index}: confidence должен быть от 0 до 1, получен {confidence}")
            contact['confidence'] = max(0, min(1, float(confidence)))
        
        # Валидация строковых полей
        string_fields = ['name', 'organization', 'position', 'city']
        for field in string_fields:
            if field in contact and not isinstance(contact[field], str):
                print(f"⚠️ Контакт {index}: поле '{field}' должно быть строкой")
                contact[field] = str(contact[field]) if contact[field] is not None else ''
        
        # Проверяем, что есть хотя бы имя или email или телефон
        has_name = contact.get('name')
        has_email = contact.get('email')
        has_phone = contact.get('phone')
        
        # Безопасная проверка с обработкой None
        has_name = (has_name.strip() if has_name and isinstance(has_name, str) else '')
        has_email = (has_email.strip() if has_email and isinstance(has_email, str) else '')
        has_phone = (has_phone.strip() if has_phone and isinstance(has_phone, str) else '')
        
        if not (has_name or has_email or has_phone):
            print(f"⚠️ Контакт {index}: отсутствуют ключевые данные (имя, email, телефон)")
            return False
        
        return True
    
    def _is_valid_email(self, email: str) -> bool:
        """📧 Проверка корректности email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """📞 Проверка корректности телефона"""
        import re
        # Убираем все нецифровые символы кроме +
        cleaned = re.sub(r'[^\d+]', '', phone.strip())
        # Проверяем, что остались только цифры и возможно + в начале
        # Минимум 7 цифр, максимум 15 (международный стандарт)
        if cleaned.startswith('+'):
            digits = cleaned[1:]
        else:
            digits = cleaned
        
        return len(digits) >= 7 and len(digits) <= 15 and digits.isdigit()

    def _load_chunking_config(self) -> dict:
        """📁 Загрузка конфигурации chunking из processing_config.json"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "processing_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('chunking', {})
            else:
                print(f"⚠️ Файл конфигурации не найден: {config_path}")
                return {}
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации chunking: {e}")
            return {}
    
    def _create_text_chunks(self, text: str, config: dict) -> List[str]:
        """✂️ Создание частей текста с токен-ориентированным или символьным chunking"""
        
        # Параметры по умолчанию
        default_config = {
            'use_token_based': True,
            'max_tokens_per_chunk': 3000,
            'overlap_tokens': 300,
            'max_chunks_per_text': 20,
            'encoding_model': 'cl100k_base',
            'auto_adjust_chunk_size': True,
            'min_chunk_size': 1000,
            'max_chunk_size': 6000
        }
        
        # Объединяем с загруженной конфигурацией
        chunking_config = {**default_config, **config}
        
        # Выбираем метод chunking
        if tiktoken and chunking_config.get('use_token_based', True):
            return self._create_token_based_chunks(text, chunking_config)
        else:
            return self._create_character_based_chunks(text, chunking_config)
    
    def _create_token_based_chunks(self, text: str, config: dict) -> List[str]:
        """🎯 Токен-ориентированное разбиение текста с контролем числа чанков"""
        
        try:
            # Инициализируем энкодер
            encoding = tiktoken.get_encoding(config.get('encoding_model', 'cl100k_base'))
            
            # Кодируем весь текст
            tokens = encoding.encode(text)
            total_tokens = len(tokens)
            
            print(f"   🎯 Токен-ориентированное разбиение: {total_tokens} токенов")
            
            # Параметры chunking
            max_tokens = config.get('max_tokens_per_chunk', 3000)
            overlap_tokens = config.get('overlap_tokens', 300)
            max_chunks = config.get('max_chunks_per_text', 20)
            
            # Контроль числа чанков
            chunk_alert_threshold = config.get('chunk_alert_threshold', 20)
            chunk_abort_threshold = config.get('chunk_abort_threshold', 50)
            allow_chunk_abort = config.get('allow_chunk_abort', True)
            
            # Предварительная оценка количества чанков
            estimated_chunks = max(1, total_tokens // (max_tokens - overlap_tokens))
            
            print(f"   📊 Предварительная оценка: ~{estimated_chunks} чанков")
            
            # Alert при превышении порога
            if estimated_chunks > chunk_alert_threshold:
                print(f"   ⚠️ ВНИМАНИЕ: Ожидается {estimated_chunks} чанков (>{chunk_alert_threshold})")
                print(f"   📈 Это может привести к высокому потреблению API токенов")
            
            # Прерывание при критическом превышении
            if allow_chunk_abort and estimated_chunks > chunk_abort_threshold:
                print(f"   🚫 КРИТИЧЕСКОЕ ПРЕВЫШЕНИЕ: {estimated_chunks} чанков (>{chunk_abort_threshold})")
                print(f"   ⛔ Обработка прервана для защиты от чрезмерного потребления API")
                print(f"   💡 Рекомендация: увеличьте max_tokens_per_chunk или уменьшите размер текста")
                
                # Возвращаем только первые несколько чанков как fallback
                fallback_chunks = min(5, chunk_abort_threshold // 2)
                print(f"   🔄 Fallback: создаем только {fallback_chunks} чанков")
                max_chunks = fallback_chunks
            
            # Автоматическая корректировка размера chunk для очень больших текстов
            if config.get('auto_adjust_chunk_size', True) and total_tokens > max_tokens * max_chunks:
                adjusted_max_tokens = min(
                    config.get('max_chunk_size', 6000),
                    total_tokens // max_chunks + overlap_tokens
                )
                if adjusted_max_tokens > max_tokens:
                    max_tokens = adjusted_max_tokens
                    print(f"   📈 Автокорректировка: увеличен размер chunk до {max_tokens} токенов")
            
            chunks = []
            start_token = 0
            smart_boundary_detection = config.get('smart_boundary_detection', True)
            
            while start_token < total_tokens and len(chunks) < max_chunks:
                # Определяем конец текущего chunk
                end_token = min(start_token + max_tokens, total_tokens)
                
                # Проверяем, что у нас есть содержимое для обработки
                if start_token >= end_token:
                    print(f"   ⚠️ Достигнут конец текста: start_token={start_token}, end_token={end_token}")
                    break
                
                # Умное определение границ для лучшего разбиения
                if smart_boundary_detection and end_token < total_tokens:
                    # Декодируем область вокруг предполагаемой границы
                    boundary_start = max(0, end_token - 100)
                    boundary_end = min(total_tokens, end_token + 100)
                    boundary_text = encoding.decode(tokens[boundary_start:boundary_end])
                    
                    # Ищем лучшие места для разрыва (в порядке приоритета)
                    boundary_patterns = [
                        r'\n\n',  # Двойной перенос строки (новый абзац)
                        r'\n[A-ZА-Я]',  # Начало нового предложения с заглавной буквы
                        r'\. [A-ZА-Я]',  # Конец предложения + начало нового
                        r'\n',  # Обычный перенос строки
                        r'[.!?] ',  # Конец предложения
                        r', ',  # Запятая
                    ]
                    
                    best_boundary = None
                    relative_pos = end_token - boundary_start
                    
                    for pattern in boundary_patterns:
                        matches = list(re.finditer(pattern, boundary_text))
                        if matches:
                            # Ищем ближайшее совпадение к нашей позиции
                            closest_match = min(matches, key=lambda m: abs(m.start() - relative_pos))
                            if abs(closest_match.start() - relative_pos) <= 50:  # В пределах 50 символов
                                best_boundary = boundary_start + closest_match.end()
                                break
                    
                    if best_boundary and boundary_start <= best_boundary <= boundary_end:
                        end_token = best_boundary
                        print(f"   🎯 Умная граница найдена на токене {end_token}")
                
                # Извлекаем токены для текущего chunk
                chunk_tokens = tokens[start_token:end_token]
                
                # Проверяем, что chunk не пустой
                if not chunk_tokens:
                    print(f"   ⚠️ Пустой chunk на позиции {start_token}-{end_token}, завершаем")
                    break
                
                # Декодируем обратно в текст
                chunk_text = encoding.decode(chunk_tokens)
                
                # Добавляем информацию о части
                chunk_info = f"\n\n[ЧАСТЬ {len(chunks) + 1} ИЗ БОЛЬШОГО ПИСЬМА, ТОКЕНЫ {start_token}-{end_token}]\n"
                chunk_with_info = chunk_info + chunk_text
                
                chunks.append(chunk_with_info)
                
                # Проверяем, достигли ли мы конца текста
                if end_token >= total_tokens:
                    print(f"   ✅ Весь текст обработан: {end_token}/{total_tokens} токенов")
                    break
                
                # Следующая часть с перекрытием
                next_start = end_token - overlap_tokens
                
                # Предотвращаем бесконечный цикл при слишком большом overlap
                if next_start <= start_token:
                    print(f"   ⚠️ Overlap слишком большой ({overlap_tokens}), корректируем")
                    next_start = start_token + max(1, max_tokens // 2)
                
                start_token = next_start
            
            print(f"   ✅ Создано {len(chunks)} частей (токен-ориентированный метод)")
            return chunks
            
        except Exception as e:
            print(f"❌ Ошибка токен-ориентированного chunking: {e}")
            print("🔄 Переключение на символьный chunking")
            return self._create_character_based_chunks(text, config)
    
    def _create_character_based_chunks(self, text: str, config: dict) -> List[str]:
        """📝 Символьное разбиение текста (fallback метод)"""
        
        # Адаптивные размеры в зависимости от провайдера
        if self.current_provider == 'replicate':
            base_chunk_size = 6000
            base_overlap = 600
        else:
            base_chunk_size = 4000
            base_overlap = 400
        
        # Применяем настройки из конфигурации если есть
        chunk_size = config.get('max_chunk_size', base_chunk_size)
        overlap = min(config.get('overlap_tokens', base_overlap), chunk_size // 10)
        max_chunks = config.get('max_chunks_per_text', 20)
        
        print(f"   📝 Символьное разбиение: {len(text)} символов, chunk_size={chunk_size}")
        
        chunks = []
        start = 0
        
        while start < len(text) and len(chunks) < max_chunks:
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            
            # Добавляем информацию о части
            chunk_info = f"\n\n[ЧАСТЬ {len(chunks) + 1} ИЗ БОЛЬШОГО ПИСЬМА, СИМВОЛЫ {start}-{end}]\n"
            chunk_with_info = chunk_info + chunk
            
            chunks.append(chunk_with_info)
            
            # Следующая часть с перекрытием
            start = end - overlap
            if start >= len(text):
                break
        
        print(f"   ✅ Создано {len(chunks)} частей (символьный метод)")
        return chunks

    def _make_llm_request_with_retries(self, prompt: str, text: str, max_retries: int = 3) -> dict:
        """🔄 Выполнение запроса к LLM с повторными попытками при ошибках валидации"""
        
        # Тестовый режим - возвращаем заранее подготовленный результат
        if self.test_mode:
            return {
                'contacts': [{
                    'name': 'Тестовый Контакт',
                    'email': 'test@example.com',
                    'phone': '+7 (999) 123-45-67',
                    'organization': 'Тестовая Организация',
                    'position': 'Тестовая Должность',
                    'city': 'Тестовый Город',
                    'confidence': 0.95
                }],
                'business_context': 'Тестовый бизнес-контекст',
                'commercial_offers': [],
                'provider_used': 'Test Mode'
            }
        
        for attempt in range(max_retries):
            try:
                self.stats['total_requests'] += 1
                if attempt > 0:
                    self.stats['retry_attempts'] += 1
                    print(f"🔄 Повторная попытка {attempt + 1}/{max_retries}")
                    
                    # Оптимизированные задержки согласно мастер-плану
                    base_delay = 1.0  # Начальная задержка 1 сек для быстрого переключения

                    # Учитываем тип провайдера
                    if self.current_provider == 'replicate':
                        # Для Replicate увеличиваем базовую задержку
                        base_delay = 3.0

                    # Экспоненциальная задержка с максимумом 30 сек
                    delay = min(base_delay * (2 ** attempt), 30)

                    # Добавляем jitter для распределения нагрузки
                    import random
                    jitter = random.uniform(0.1, 0.5)
                    delay = delay * (1 + jitter)
                    
                    print(f"⏳ Ожидание {delay} секунд перед повтором...")
                    time.sleep(delay)
                
                # Выполняем запрос
                result = self._make_llm_request(prompt, text)
                
                # Проверяем валидацию JSON Schema
                if self._validate_json_schema(result):
                    self.stats['successful_requests'] += 1
                    return result
                else:
                    self.stats['json_validation_errors'] += 1
                    print(f"❌ Попытка {attempt + 1}: JSON Schema валидация не прошла")
                    
                    if attempt == max_retries - 1:
                        print("❌ Все попытки исчерпаны, возвращаем результат с ошибкой")
                        self.stats['failed_requests'] += 1
                        return {
                            'contacts': [],
                            'business_context': 'Ошибка валидации JSON Schema',
                            'commercial_offers': [],
                            'error': 'JSON Schema validation failed after retries'
                        }
            
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Попытка {attempt + 1}: Ошибка запроса к LLM: {e}")
                
                # Специальная обработка JSON ошибок с перезапросом
                if "Ошибка парсинга JSON" in error_msg and attempt < max_retries - 1:
                    print(f"🔄 JSON ошибка: перезапрос с 'Strict JSON only!' (попытка {attempt + 2})")
                    # Модифицируем prompt для следующей попытки
                    if "STRICT JSON ONLY!" not in prompt:
                        prompt += "\n\nSTRICT JSON ONLY! Отвечай только валидным JSON без дополнительного текста."
                    continue
                
                # Специальная обработка rate limit с exponential backoff
                if "Rate limit (HTTP 429)" in error_msg:
                    # Извлекаем время ожидания из сообщения об ошибке
                    import re
                    wait_match = re.search(r'ожидание (\d+) сек', error_msg)
                    base_wait_time = int(wait_match.group(1)) if wait_match else 60
                    
                    # Exponential backoff: базовое время * 2^попытка
                    exponential_wait = base_wait_time * (2 ** attempt)
                    max_wait = 300  # Максимум 5 минут
                    actual_wait = min(exponential_wait, max_wait)
                    
                    print(f"⏳ Rate limit: exponential backoff {actual_wait} сек (попытка {attempt + 1})")
                    
                    if attempt < max_retries - 1:  # Не ждем на последней попытке
                        time.sleep(actual_wait)
                        self.stats['retry_attempts'] += 1
                        continue
                
                # Проверяем Circuit Breaker перед переключением
                if self._is_provider_in_circuit_break():
                    print(f"🔌 Circuit Breaker: провайдер {self.providers[self.current_provider]['name']} отключен")
                    # Пробуем переключиться на другого провайдера
                    if self._switch_to_next_provider():
                        print(f"🔄 Повторяем запрос с новым провайдером")
                        continue  # Повторяем попытку с новым провайдером
                    else:
                        print("❌ Нет доступных провайдеров для fallback")
                        break  # Выходим из цикла retry
                else:
                    # Пробуем переключиться на другого провайдера
                    if self._switch_to_next_provider():
                        print(f"🔄 Повторяем запрос с новым провайдером")
                        continue  # Повторяем попытку с новым провайдером
                
                if attempt == max_retries - 1:
                    self.stats['failed_requests'] += 1
                    return {
                        'contacts': [],
                            'business_context': f'Ошибка LLM: {str(e)}',
                            'commercial_offers': [],
                        'error': str(e)
                    }
        
        # Этот код не должен выполняться, но на всякий случай
        self.stats['failed_requests'] += 1
        return {
            'contacts': [],
            'business_context': 'Неизвестная ошибка',
            'commercial_offers': [],
            'error': 'Unknown error in retry logic'
        }
    
    def _make_llm_request(self, prompt: str, text: str) -> dict:
        """🤖 Базовый запрос к LLM с поддержкой fallback"""
        
        # Получаем текущего провайдера
        current_provider = self.providers[self.current_provider]
        
        # Формируем запрос в зависимости от провайдера
        if self.current_provider == 'replicate':
            # Специальный формат для Replicate API
            payload = {
                "version": current_provider['model'],  # Используем version вместо model
                "input": {
                    "prompt": f"{prompt}\n\n📧 ТЕКСТ ДЛЯ АНАЛИЗА:\n{text}\n\nSTRICT JSON ONLY! Отвечай только валидным JSON без дополнительного текста.",
                    "max_tokens": 8000,  # Увеличено для длинных списков
                    "temperature": 0,     # Убираем фантазии
                    "top_p": 0.9,
                    "frequency_penalty": 0,
                    "presence_penalty": 0
                }
            }
        else:
            # Стандартный OpenAI-совместимый формат для OpenRouter и Groq
            messages = [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n📧 ТЕКСТ ДЛЯ АНАЛИЗА:\n{text}"
                }
            ]
            
            # Адаптивный max_tokens для Groq с учетом лимитов
            if self.current_provider == 'groq':
                # Для Groq лимит 6000 токенов на запрос
                estimated_input_tokens = len(f"{prompt}\n\n📧 ТЕКСТ ДЛЯ АНАЛИЗА:\n{text}") // 4  # Примерно 4 символа = 1 токен
                max_output_tokens = min(2000, 6000 - estimated_input_tokens - 500)  # Оставляем запас
                
                if estimated_input_tokens > 5000:  # Если входной текст слишком большой
                    print(f"⚠️ Groq: входной текст слишком большой ({estimated_input_tokens} токенов), используем разбивку")
                    return self._process_large_text_for_groq(text, prompt, metadata={})
                    
                max_output_tokens = max(500, max_output_tokens)  # Минимум 500 токенов для ответа
            else:
                max_output_tokens = 4000
            
            payload = {
                "model": current_provider['model'],
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": max_output_tokens
            }
        
        # Формируем заголовки для текущего провайдера
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_provider['api_key']}"
        }
        
        # Добавляем специфичные заголовки для OpenRouter
        if self.current_provider == 'openrouter':
            headers["HTTP-Referer"] = "https://github.com/contact-parser"
            headers["X-Title"] = "Contact Parser"
        
        # Расширенное логирование для Replicate
        if self.current_provider == 'replicate':
            print(f"🔧 Replicate запрос:")
            print(f"   URL: {current_provider['base_url']}")
            print(f"   Model: {current_provider['model']}")
            print(f"   Payload size: {len(str(payload))} символов")
            print(f"   Text length: {len(text)} символов")
            print(f"   Headers: {list(headers.keys())}")
        
        try:
            # Выполняем запрос с обработкой SSL ошибок
            response = requests.post(
                current_provider['base_url'],
                headers=headers,
                json=payload,
                timeout=60,
                verify=True  # Включаем проверку SSL сертификатов
            )
            
            # Дополнительное логирование для Replicate
            if self.current_provider == 'replicate':
                print(f"📡 Replicate ответ: status={response.status_code}, size={len(response.text)} символов")
            
            # Специальная обработка rate limit (HTTP 429)
            if response.status_code == 429:
                # Увеличиваем счетчик ошибок провайдера
                current_provider['failure_count'] += 1
                current_provider['last_failure'] = datetime.now().isoformat()
                self.stats['provider_failures'][self.current_provider] += 1
                
                # Извлекаем время ожидания из заголовков (если есть)
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                        print(f"⏳ Rate limit от {current_provider['name']}: ожидание {wait_time} сек")
                    except ValueError:
                        wait_time = 60  # По умолчанию 60 секунд
                else:
                    wait_time = 60  # По умолчанию 60 секунд
                
                raise Exception(f"Rate limit (HTTP 429): требуется ожидание {wait_time} сек. {response.text}")
            
            # Проверяем успешность запроса (для Replicate принимаем 200 и 201)
            success_codes = [200, 201] if self.current_provider == 'replicate' else [200]
            if response.status_code not in success_codes:
                # Увеличиваем счетчик ошибок провайдера
                current_provider['failure_count'] += 1
                current_provider['last_failure'] = datetime.now().isoformat()
                self.stats['provider_failures'][self.current_provider] += 1
                
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            response_data = response.json()
            
            # Обработка ответа в зависимости от провайдера
            content = None  # Инициализируем переменную
            
            if self.current_provider == 'replicate':
                # Для Replicate API проверяем статус и получаем результат
                if 'status' in response_data:
                    if response_data['status'] == 'failed':
                        raise Exception(f"Replicate prediction failed: {response_data.get('error', 'Unknown error')}")
                    elif response_data['status'] in ['starting', 'processing']:
                        # Если предсказание создается или обрабатывается, ждем
                        prediction_id = response_data.get('id')
                        content = self._wait_for_replicate_result(prediction_id, current_provider)
                    elif response_data['status'] == 'succeeded':
                        # Получаем результат из output
                        output = response_data.get('output', [])
                        if isinstance(output, list) and output:
                            content = ''.join(output)
                        elif isinstance(output, str):
                            content = output
                        else:
                            raise Exception("Некорректный формат ответа от Replicate")
                    else:
                        raise Exception(f"Неизвестный статус Replicate: {response_data['status']}")
                else:
                    raise Exception("Ответ от Replicate не содержит статус")
            else:
                # Стандартная обработка для OpenAI-совместимых API
                if 'choices' not in response_data or not response_data['choices']:
                    # Увеличиваем счетчик ошибок провайдера
                    current_provider['failure_count'] += 1
                    current_provider['last_failure'] = datetime.now().isoformat()
                    self.stats['provider_failures'][self.current_provider] += 1
                    
                    # Добавляем диагностику для отладки
                    print(f"🔍 Диагностика ответа от {current_provider['name']}:")
                    print(f"   Response data keys: {list(response_data.keys()) if response_data else 'None'}")
                    print(f"   Response data: {response_data}")
                    
                    raise Exception(f"Пустой ответ от LLM {current_provider['name']}: {response_data}")
                
                content = response_data['choices'][0]['message']['content']
            
            # Проверяем, что content получен
            if content is None:
                raise Exception("Не удалось получить содержимое ответа от LLM")
            
            # Парсим JSON из ответа
            try:
                result = self._parse_llm_response(content)
                result['provider_used'] = current_provider['name']
                return result
            except ValueError as parse_error:
                # Обработка ошибок парсинга JSON
                current_provider['failure_count'] += 1
                current_provider['last_failure'] = datetime.now().isoformat()
                self.stats['provider_failures'][self.current_provider] += 1
                
                print(f"❌ Ошибка парсинга ответа от {current_provider['name']}: {parse_error}")
                raise Exception(f"Ошибка парсинга JSON: {parse_error}")
            
        except requests.exceptions.SSLError as ssl_error:
            # Специальная обработка SSL ошибок
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            self.stats['provider_failures'][self.current_provider] += 1
            
            print(f"🔒 SSL ошибка провайдера {current_provider['name']}: {ssl_error}")
            print(f"💡 Попробуйте проверить сетевое соединение или настройки SSL")
            raise Exception(f"SSL record layer failure: {ssl_error}")
            
        except requests.exceptions.ConnectionError as conn_error:
            # Обработка ошибок соединения
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            self.stats['provider_failures'][self.current_provider] += 1
            
            print(f"🌐 Ошибка соединения с провайдером {current_provider['name']}: {conn_error}")
            raise Exception(f"Connection error: {conn_error}")
            
        except requests.exceptions.Timeout as timeout_error:
            # Обработка таймаутов
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            self.stats['provider_failures'][self.current_provider] += 1
            
            print(f"⏰ Таймаут провайдера {current_provider['name']}: {timeout_error}")
            raise Exception(f"Request timeout: {timeout_error}")
            
        except Exception as e:
            # Увеличиваем счетчик ошибок провайдера
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            self.stats['provider_failures'][self.current_provider] += 1
            
            print(f"❌ Ошибка провайдера {current_provider['name']}: {e}")
            raise e
    
    def _wait_for_replicate_result(self, prediction_id: str, provider_config: dict, max_wait: int = 600) -> str:
        """⏳ Ожидание результата от Replicate API"""
        import time
        
        if not prediction_id:
            raise Exception("Не получен ID предсказания от Replicate")
        
        # URL для получения статуса предсказания
        status_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        headers = {
            "Authorization": f"Bearer {provider_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(status_url, headers=headers, timeout=30, verify=True)
                
                if response.status_code != 200:
                    raise Exception(f"Ошибка при получении статуса Replicate: HTTP {response.status_code}")
                
                data = response.json()
                status = data.get('status')
                
                if status == 'succeeded':
                    output = data.get('output', [])
                    if isinstance(output, list) and output:
                        return ''.join(output)
                    elif isinstance(output, str):
                        return output
                    else:
                        raise Exception("Некорректный формат результата от Replicate")
                
                elif status == 'failed':
                    error_msg = data.get('error', 'Unknown error')
                    raise Exception(f"Replicate prediction failed: {error_msg}")
                
                elif status in ['starting', 'processing']:
                    print(f"⏳ Replicate обрабатывает запрос... (статус: {status})")
                    time.sleep(2)  # Ждем 2 секунды перед следующей проверкой
                    continue
                
                else:
                    raise Exception(f"Неизвестный статус Replicate: {status}")
                    
            except requests.exceptions.SSLError as ssl_error:
                print(f"🔒 SSL ошибка при ожидании результата Replicate: {ssl_error}")
                raise Exception(f"SSL record layer failure при ожидании результата: {ssl_error}")
                
            except requests.exceptions.ConnectionError as conn_error:
                print(f"🌐 Ошибка соединения при ожидании результата Replicate: {conn_error}")
                raise Exception(f"Connection error при ожидании результата: {conn_error}")
                
            except requests.exceptions.Timeout as timeout_error:
                print(f"⏰ Таймаут при ожидании результата Replicate: {timeout_error}")
                raise Exception(f"Request timeout при ожидании результата: {timeout_error}")
                
            except requests.RequestException as e:
                raise Exception(f"Ошибка сети при ожидании результата Replicate: {e}")
        
        raise Exception(f"Превышено время ожидания результата от Replicate ({max_wait} сек)")
    
    def _process_large_text_for_groq(self, text: str, prompt: str, metadata: dict = None) -> dict:
        """🔄 Обработка больших текстов для Groq с разбивкой на части"""
        
        # Разбиваем текст на части по 2000 символов для стабильности (примерно 500 токенов)
        chunk_size = 2000
        text_chunks = []
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            text_chunks.append(chunk)
        
        print(f"📄 Groq: разбиваем текст на {len(text_chunks)} частей")
        
        all_contacts = []
        all_business_contexts = []
        all_recommendations = []
        
        # Обрабатываем каждую часть отдельно
        for i, chunk in enumerate(text_chunks):
            print(f"⏳ Groq: обрабатываем часть {i+1}/{len(text_chunks)}")
            
            try:
                # Временно сохраняем текущий провайдер
                original_provider = self.current_provider
                
                # Принудительно используем Groq для этой части
                self.current_provider = 'groq'
                
                # Делаем запрос для части текста
                chunk_result = self._make_llm_request(prompt, chunk)
                
                # Восстанавливаем провайдера
                self.current_provider = original_provider
                
                # Собираем результаты
                if 'contacts' in chunk_result and chunk_result['contacts']:
                    all_contacts.extend(chunk_result['contacts'])
                
                if 'business_context' in chunk_result:
                    all_business_contexts.append(chunk_result['business_context'])
                
                if 'recommended_actions' in chunk_result:
                    all_recommendations.append(chunk_result['recommended_actions'])
                    
            except Exception as e:
                print(f"❌ Ошибка при обработке части {i+1}: {e}")
                continue
        
        # Объединяем результаты
        combined_result = {
            'contacts': self._deduplicate_contacts(all_contacts),
            'business_context': ' | '.join(all_business_contexts) if all_business_contexts else 'Контекст не определен',
            'recommended_actions': ' | '.join(all_recommendations) if all_recommendations else 'Рекомендации не определены',
            'provider_used': 'Groq (chunked)',
            'chunks_processed': len(text_chunks),
            'total_contacts_found': len(all_contacts)
        }
        
        print(f"✅ Groq: обработка завершена, найдено {len(all_contacts)} контактов")
        return combined_result
    
    def _deduplicate_contacts(self, contacts: list) -> list:
        """🔄 Удаление дубликатов контактов по email и телефону"""
        seen = set()
        unique_contacts = []
        
        for contact in contacts:
            # Создаем ключ для идентификации дубликатов
            key_parts = []
            if contact.get('email'):
                email = contact.get('email')
                if email and isinstance(email, str):
                    key_parts.append(email.lower().strip())
            if contact.get('phone'):
                # Нормализуем телефон (убираем пробелы, скобки, дефисы)
                phone = contact['phone']
                if phone and isinstance(phone, str):
                    phone_normalized = ''.join(filter(str.isdigit, phone))
                    key_parts.append(phone_normalized)
            
            if key_parts:
                contact_key = '|'.join(key_parts)
                if contact_key not in seen:
                    seen.add(contact_key)
                    unique_contacts.append(contact)
            else:
                # Если нет email и телефона, добавляем как есть
                unique_contacts.append(contact)
        
        return unique_contacts
    
    def _parse_llm_response(self, response_text: str) -> dict:
        """📝 Парсинг ответа LLM с строгой валидацией JSON"""
        
        # Проверяем, что response_text не None
        if response_text is None:
            raise ValueError("Получен None вместо текста ответа от LLM")
        
        # Логируем сырой ответ для диагностики
        print(f"🔍 Сырой ответ LLM ({len(response_text)} символов):")
        print(f"'{response_text[:500]}{'...' if len(response_text) > 500 else ''}'")
        
        try:
            # Очистка ответа для Replicate
            if self.current_provider == 'replicate':
                # Убираем возможные префиксы и суффиксы
                response_text = response_text.strip()
                # Убираем markdown блоки если есть
                response_text = re.sub(r'^```json\s*', '', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'\s*```$', '', response_text, flags=re.MULTILINE)
                # Убираем возможные текстовые пояснения до JSON
                response_text = re.sub(r'^[^{]*(?=\{)', '', response_text, flags=re.DOTALL)
            
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"🔍 Найденный JSON: {json_str[:200]}{'...' if len(json_str) > 200 else ''}")
                
                # Попытка парсинга с обработкой ошибок
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка парсинга JSON: {e}")
                    # Попытка исправить распространенные ошибки
                    json_str = json_str.replace("'", '"')  # Одинарные кавычки
                    json_str = re.sub(r',\s*}', '}', json_str)  # Лишние запятые
                    json_str = re.sub(r',\s*]', ']', json_str)  # Лишние запятые в массивах
                    result = json.loads(json_str)
                
                # Дополнительная проверка структуры
                if not isinstance(result, dict):
                    raise ValueError("Ответ не является JSON объектом")
                
                # Нормализация ответа от Replicate
                result = self._normalize_replicate_response(result)
                    
                return result
            else:
                raise ValueError("JSON не найден в ответе LLM")
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON: {e}. Требуется перезапрос с 'Strict JSON only!'")
    
    def _normalize_replicate_response(self, response: dict) -> dict:
        """🔧 Нормализация ответа от Replicate API"""
        
        # Преобразуем action_items в recommended_actions
        if 'action_items' in response and 'recommended_actions' not in response:
            action_items = response.get('action_items', [])
            if isinstance(action_items, list):
                response['recommended_actions'] = '; '.join(action_items) if action_items else 'Нет рекомендаций'
            else:
                response['recommended_actions'] = str(action_items)
            print("🔧 Преобразовано action_items -> recommended_actions")
        
        # Преобразуем объект business_context в строку
        if 'business_context' in response and isinstance(response['business_context'], dict):
            bc = response['business_context']
            context_parts = []
            for key, value in bc.items():
                if value:
                    context_parts.append(f"{key}: {value}")
            response['business_context'] = '; '.join(context_parts) if context_parts else 'Контекст не определен'
            print("🔧 Преобразован объект business_context в строку")
        
        return response
    
    def _process_large_text(self, text: str, prompt: str, metadata: dict = None) -> dict:
        """📄 Обработка больших текстов через токен-ориентированную разбивку на части с оптимизацией памяти"""
        
        # Проверка тестового режима
        if self.test_mode:
            print("   🧪 Тестовый режим: возвращаем тестовые данные для большого текста")
            return {
                'success': True,
                'contacts': [{
                    'name': 'Тестовый Контакт',
                    'email': 'test@example.com',
                    'phone': '+7 (999) 123-45-67',
                    'organization': 'Тестовая Организация',
                    'position': 'Тестовая Должность',
                    'city': 'Тестовый Город',
                    'confidence': 0.95
                }],
                'business_context': 'Тестовый бизнес-контекст для большого текста',
                'recommended_actions': 'Тестовые рекомендации для большого текста',
                'provider_used': 'Test Mode'
            }
        
        import gc  # Для принудительной очистки памяти
        
        # Загружаем конфигурацию chunking
        chunking_config = self._load_chunking_config()
        
        # Специальная обработка для очень больших текстов (250K+ символов)
        text_length = len(text)
        very_large_threshold = chunking_config.get('very_large_text_threshold', 250000)
        
        if text_length > very_large_threshold:
            print(f"   🔥 ОЧЕНЬ БОЛЬШОЙ ТЕКСТ: {text_length} символов (>{very_large_threshold})")
            # Применяем специальные настройки для очень больших текстов
            chunking_config.update({
                'max_tokens_per_chunk': chunking_config.get('very_large_max_tokens_per_chunk', 6000),
                'overlap_tokens': chunking_config.get('very_large_overlap_tokens', 600),
                'max_chunks_per_text': chunking_config.get('very_large_max_chunks', 50)
            })
        
        # Создаем части текста
        chunks = self._create_text_chunks(text, chunking_config)
        
        print(f"   📊 Разбито на {len(chunks)} частей (метод: {'токен-ориентированный' if tiktoken else 'символьный'})")
        
        # Обрабатываем каждую часть с оптимизацией памяти
        all_contacts = []
        all_contexts = []
        all_actions = []
        
        # Определяем стратегию обработки
        memory_optimization = chunking_config.get('memory_optimization', True)
        progressive_chunking = chunking_config.get('progressive_chunking', True)
        
        # Для очень больших текстов используем прогрессивную обработку
        if text_length > very_large_threshold and progressive_chunking:
            print(f"   🚀 Прогрессивная обработка {len(chunks)} частей")
            
            # Обрабатываем по батчам для экономии памяти
            batch_size = min(5, len(chunks))  # Максимум 5 частей одновременно
            
            for batch_start in range(0, len(chunks), batch_size):
                batch_end = min(batch_start + batch_size, len(chunks))
                batch_chunks = chunks[batch_start:batch_end]
                
                print(f"   📦 Батч {batch_start//batch_size + 1}: части {batch_start + 1}-{batch_end}")
                
                for i, chunk in enumerate(batch_chunks):
                    chunk_index = batch_start + i
                    self._process_single_chunk(chunk, chunk_index + 1, len(chunks), prompt, 
                                             all_contacts, all_contexts, all_actions, memory_optimization)
                
                # Очистка памяти после каждого батча
                if memory_optimization:
                    del batch_chunks
                    gc.collect()
                    print(f"   🧹 Очистка памяти после батча {batch_start//batch_size + 1}")
        else:
            # Выбираем метод обработки: асинхронный или синхронный
            if chunking_config.get('enable_async_processing', True) and len(chunks) > 2:
                return self._process_chunks_async(chunks, prompt, chunking_config)
            else:
                return self._process_chunks_sync(chunks, prompt, chunking_config)
    
    def _process_single_chunk(self, chunk, chunk_index, total_chunks, prompt, 
                             all_contacts, all_contexts, all_actions, memory_optimization):
        """Обрабатывает одну часть текста"""
        print(f"   🔍 Обработка части {chunk_index}/{total_chunks} (размер: {len(chunk)} символов)")
        
        try:
            # Обрабатываем часть
            chunk_result = self._make_llm_request_with_retries(prompt, chunk)
            
            # Собираем результаты
            if 'contacts' in chunk_result and chunk_result['contacts']:
                all_contacts.extend(chunk_result['contacts'])
            
            if 'business_context' in chunk_result:
                all_contexts.append(f"Часть {chunk_index}: {chunk_result['business_context']}")
            
            if 'recommended_actions' in chunk_result:
                all_actions.append(f"Часть {chunk_index}: {chunk_result['recommended_actions']}")
            
            # Небольшая пауза между запросами
            if chunk_index < total_chunks:
                time.sleep(2)
                
            # Принудительная очистка памяти после каждой части
            if memory_optimization:
                del chunk_result
                gc.collect()
        
        except Exception as e:
            print(f"   ❌ Ошибка обработки части {chunk_index}: {e}")
            all_contexts.append(f"Часть {chunk_index}: Ошибка обработки - {str(e)}")
            # Очистка памяти даже при ошибке
            if memory_optimization:
                gc.collect()
    
    def _process_chunks_async(self, chunks: List[str], prompt: str, chunking_config: dict) -> dict:
        """🚀 Асинхронная обработка чанков для ускорения процесса"""
        
        import gc
        
        # Параметры асинхронной обработки
        max_concurrent_chunks = chunking_config.get('max_concurrent_chunks', 3)
        api_rate_limit_delay = chunking_config.get('api_rate_limit_delay', 1.0)
        enable_async_processing = chunking_config.get('enable_async_processing', True)
        
        if not enable_async_processing or len(chunks) <= 2:
            print(f"   📝 Синхронная обработка {len(chunks)} чанков (async отключен или мало чанков)")
            return self._process_chunks_sync(chunks, prompt, chunking_config)
        
        print(f"   🚀 Асинхронная обработка {len(chunks)} чанков (max_concurrent: {max_concurrent_chunks})")
        
        all_contacts = []
        all_contexts = []
        all_actions = []
        
        def process_single_chunk_wrapper(chunk_data):
            """Обертка для синхронной функции обработки чанка"""
            chunk, chunk_index = chunk_data
            try:
                # Добавляем задержку для соблюдения rate limits
                if chunk_index > 1:
                    time.sleep(api_rate_limit_delay)
                
                print(f"   🔍 Асинхронная обработка части {chunk_index}/{len(chunks)}")
                
                # Обрабатываем чанк
                chunk_result = self._make_llm_request_with_retries(prompt, chunk)
                
                # Возвращаем результат с индексом для правильной сортировки
                return {
                    'index': chunk_index,
                    'contacts': chunk_result.get('contacts', []),
                    'business_context': chunk_result.get('business_context', ''),
                    'recommended_actions': chunk_result.get('recommended_actions', ''),
                    'success': True
                }
                
            except Exception as e:
                print(f"   ❌ Ошибка асинхронной обработки части {chunk_index}: {e}")
                return {
                    'index': chunk_index,
                    'contacts': [],
                    'business_context': f"Ошибка обработки - {str(e)}",
                    'recommended_actions': '',
                    'success': False
                }
        
        # Подготавливаем данные для обработки
        chunk_data = [(chunk, i+1) for i, chunk in enumerate(chunks)]
        
        # Используем ThreadPoolExecutor для параллельной обработки
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_chunks) as executor:
            try:
                # Запускаем обработку всех чанков
                future_to_chunk = {executor.submit(process_single_chunk_wrapper, data): data[1] 
                                 for data in chunk_data}
                
                # Собираем результаты по мере завершения
                completed_chunks = 0
                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    completed_chunks += 1
                    
                    try:
                        result = future.result()
                        
                        # Собираем результаты
                        if result['contacts']:
                            all_contacts.extend(result['contacts'])
                        
                        if result['business_context']:
                            all_contexts.append(f"Часть {result['index']}: {result['business_context']}")
                        
                        if result['recommended_actions']:
                            all_actions.append(f"Часть {result['index']}: {result['recommended_actions']}")
                        
                        print(f"   ✅ Завершена часть {result['index']} ({completed_chunks}/{len(chunks)})")
                        
                    except Exception as e:
                        print(f"   ❌ Ошибка получения результата части {chunk_index}: {e}")
                        all_contexts.append(f"Часть {chunk_index}: Ошибка получения результата - {str(e)}")
                
            except Exception as e:
                print(f"   ❌ Критическая ошибка асинхронной обработки: {e}")
                print(f"   🔄 Переключение на синхронную обработку")
                return self._process_chunks_sync(chunks, prompt, chunking_config)
        
        # Принудительная очистка памяти
        if chunking_config.get('memory_optimization', True):
            gc.collect()
        
        # Дедупликация контактов
        unique_contacts = self._deduplicate_contacts(all_contacts)
        
        print(f"   🎯 Асинхронная обработка завершена: {len(all_contacts)} -> {len(unique_contacts)} уникальных контактов")
        
        return {
            'contacts': unique_contacts,
            'business_context': ' | '.join(all_contexts) if all_contexts else 'Контекст не определен',
            'recommended_actions': ' | '.join(all_actions) if all_actions else 'Рекомендации не определены',
            'provider_used': f'{self.providers[self.current_provider]["name"]} (async chunked)',
            'chunks_processed': len(chunks),
            'total_contacts_found': len(all_contacts),
            'unique_contacts_found': len(unique_contacts),
            'processing_method': 'async'
        }
    
    def _process_chunks_sync(self, chunks: List[str], prompt: str, chunking_config: dict) -> dict:
        """📝 Синхронная обработка чанков (fallback метод)"""
        
        import gc
        
        print(f"   📝 Синхронная обработка {len(chunks)} чанков")
        
        all_contacts = []
        all_contexts = []
        all_actions = []
        memory_optimization = chunking_config.get('memory_optimization', True)
        
        # Обрабатываем каждую часть последовательно
        for i, chunk in enumerate(chunks):
            self._process_single_chunk(
                chunk, i+1, len(chunks), prompt,
                all_contacts, all_contexts, all_actions, memory_optimization
            )
        
        # Дедупликация контактов
        unique_contacts = self._deduplicate_contacts(all_contacts)
        
        print(f"   🎯 Синхронная обработка завершена: {len(all_contacts)} -> {len(unique_contacts)} уникальных контактов")
        
        return {
            'contacts': unique_contacts,
            'business_context': ' | '.join(all_contexts) if all_contexts else 'Контекст не определен',
            'recommended_actions': ' | '.join(all_actions) if all_actions else 'Рекомендации не определены',
            'provider_used': f'{self.providers[self.current_provider]["name"]} (sync chunked)',
            'chunks_processed': len(chunks),
            'total_contacts_found': len(all_contacts),
            'unique_contacts_found': len(unique_contacts),
            'processing_method': 'sync'
        }
    
    def _deduplicate_contacts(self, contacts: List[dict]) -> List[dict]:
        """🔄 Удаление дубликатов контактов"""
        
        if not contacts:
            return []
        
        unique_contacts = []
        seen_emails = set()
        seen_phones = set()
        
        for contact in contacts:
            email = contact.get('email', '')
            if email and isinstance(email, str):
                email = email.lower().strip()
            else:
                email = ''
            
            phone = contact.get('phone', '')
            if phone and isinstance(phone, str):
                phone = phone.strip()
            else:
                phone = ''
            
            # Нормализуем телефон (убираем пробелы, скобки, дефисы, плюсы)
            # Оставляем только цифры для сравнения
            normalized_phone = re.sub(r'[^0-9]', '', phone)
            
            # Для российских номеров приводим к единому формату
            if normalized_phone.startswith('8') and len(normalized_phone) == 11:
                normalized_phone = '7' + normalized_phone[1:]  # 8xxx -> 7xxx
            elif normalized_phone.startswith('7') and len(normalized_phone) == 11:
                pass  # Уже в правильном формате
            elif len(normalized_phone) == 10:
                normalized_phone = '7' + normalized_phone  # xxx -> 7xxx
            
            # Проверяем дубликаты по email или телефону
            is_duplicate = False
            
            if email and email in seen_emails:
                is_duplicate = True
            
            if normalized_phone and len(normalized_phone) > 6 and normalized_phone in seen_phones:
                is_duplicate = True
            
            if not is_duplicate:
                unique_contacts.append(contact)
                if email:
                    seen_emails.add(email)
                if normalized_phone and len(normalized_phone) > 6:
                    seen_phones.add(normalized_phone)
        
        return unique_contacts
    
    def extract_contacts(self, text: str, metadata: dict = None) -> dict:
        """👤 Основной метод извлечения контактов"""
        
        # Сохраняем исходный test_mode
        original_test_mode = self.test_mode
        
        try:
            # Логирование
            print(f"\n🔍 Извлечение контактов (test_mode={self.test_mode})")
            print(f"   📝 Длина текста: {len(text)} символов")
            
            if metadata:
                print(f"   📧 Метаданные: {metadata.get('subject', 'Без темы')}")
            
            # Сохраняем тестовый режим как есть
            # (убрана логика принудительного отключения тестового режима)
            
            # Загружаем промпт
            prompt = self._load_prompt("unified_contact_extraction.txt")
            
            if prompt.startswith("ERROR:"):
                return {
                    'contacts': [],
                    'business_context': prompt,
                    'commercial_offers': [],
                    'error': 'Prompt loading failed'
                }
            
            # Загружаем конфигурацию для определения порога больших текстов
            chunking_config = self._load_chunking_config()
            large_text_threshold = chunking_config.get('max_chunk_size', 6000)
            
            # Обработка больших текстов через разбивку на части
            if len(text) > large_text_threshold:
                print(f"   📄 Большой текст ({len(text)} символов > {large_text_threshold}), разбиваем на части")
                return self._process_large_text(text, prompt, metadata)
            else:
                print(f"   📝 Обычный размер текста: {len(text)} символов (≤ {large_text_threshold})")
            
            # Определяем провайдера
            provider_info = f"{self.providers[self.current_provider]['name']} ({self.providers[self.current_provider]['model']})"
            
            # Тестовый режим
            if self.test_mode:
                print("   🧪 Активирован тестовый режим")
                result = {
                    'success': True,
                    'contacts': [{
                        'name': 'Тестовый Контакт',
                        'email': 'test@example.com',
                        'phone': '+7 (999) 123-45-67',
                        'organization': 'Тестовая Организация',
                        'position': 'Тестовая Должность',
                        'city': 'Тестовый Город',
                        'confidence': 0.95
                    }],
                    'business_context': 'Тестовый бизнес-контекст',
                    'commercial_offers': [],
                    'provider_used': 'Test Mode'
                }
                
                # Восстанавливаем исходный test_mode
                self.test_mode = original_test_mode
                return result
            
            # Выполняем запрос с повторными попытками
            result = self._make_llm_request_with_retries(prompt, text)
            
            # Проверяем, что result является словарем
            if not isinstance(result, dict):
                print(f"❌ Неожиданный тип результата: {type(result)}")
                return {
                    'contacts': [],
                    'business_context': f'Ошибка: получен {type(result)} вместо dict',
                    'commercial_offers': [],
                    'error': f'Invalid result type: {type(result)}',
                    'provider_used': 'Error'
                }
            
            # Добавляем метаинформацию
            result['provider_used'] = provider_info
            result['processing_time'] = datetime.now().isoformat()
            result['text_length'] = len(text)
            
            # Статистика
            contacts_count = len(result.get('contacts', []))
            print(f"   ✅ Извлечено контактов: {contacts_count}")
            print(f"   🤖 Провайдер: {provider_info}")
            
            return result
        
        except Exception as e:
            print(f"❌ Ошибка извлечения контактов: {e}")
            return {
                'contacts': [],
                'business_context': f'Ошибка обработки: {str(e)}',
                'commercial_offers': [],
                'error': str(e),
                'provider_used': 'Error'
            }
        
        finally:
            # Восстанавливаем исходный test_mode
            self.test_mode = original_test_mode
    
    def get_stats(self) -> dict:
        """📊 Получение статистики работы"""
        return self.stats.copy()
    
    def reset_stats(self):
        """🔄 Сброс статистики"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'json_validation_errors': 0,
            'fallback_switches': 0,
            'provider_failures': {
                'openrouter': 0,
                'groq': 0
            }
        }
        print("📊 Статистика сброшена")
    
    def get_provider_health(self) -> dict:
        """🏥 Получение статуса здоровья всех провайдеров"""
        health_status = {
            'current_provider': self.current_provider,
            'system_health': 'healthy',
            'providers': {},
            'recommendations': []
        }
        
        for provider_id, provider in self.providers.items():
            # Проверяем наличие API ключа
            has_api_key = bool(provider['api_key'])
            
            # Определяем статус провайдера
            if not provider['active']:
                status = 'disabled'
            elif not has_api_key:
                status = 'no_api_key'
            elif provider['failure_count'] > 3:
                status = 'unhealthy'
            elif provider['failure_count'] > 0:
                status = 'degraded'
            else:
                status = 'healthy'
            
            health_status['providers'][provider_id] = {
                'name': provider['name'],
                'status': status,
                'active': provider['active'],
                'has_api_key': has_api_key,
                'failure_count': provider['failure_count'],
                'last_failure': provider['last_failure'],
                'priority': provider['priority']
            }
            
            # Добавляем рекомендации
            if not has_api_key:
                health_status['recommendations'].append(f"Добавить API ключ для {provider['name']}")
            elif status == 'unhealthy':
                health_status['recommendations'].append(f"Проверить настройки {provider['name']} - много ошибок")
        
        # Определяем общее здоровье системы
        active_providers = [p for p in self.providers.values() if p['active'] and p['api_key']]
        if not active_providers:
            health_status['system_health'] = 'critical'
            health_status['recommendations'].append('Нет доступных провайдеров с API ключами')
        elif len(active_providers) == 1:
            health_status['system_health'] = 'warning'
            health_status['recommendations'].append('Только один активный провайдер - нет резервного')
        
        return health_status
    
    def _switch_to_next_provider(self) -> bool:
        """🔄 Переключение на следующий доступный провайдер с Circuit Breaker"""
        # Получаем список активных провайдеров, отсортированных по приоритету
        active_providers = [
            (pid, provider) for pid, provider in self.providers.items()
            if provider['active'] and provider['api_key'] and not self._is_provider_in_circuit_break(pid)
        ]
        active_providers.sort(key=lambda x: x[1]['priority'])

        if not active_providers:
            print("❌ Нет доступных провайдеров (все в circuit break или неактивны)")
            return False

        # Ищем следующий провайдер после текущего
        current_index = -1
        for i, (pid, _) in enumerate(active_providers):
            if pid == self.current_provider:
                current_index = i
                break

        # Переключаемся на следующий провайдер
        if current_index >= 0 and current_index + 1 < len(active_providers):
            next_provider_id = active_providers[current_index + 1][0]
        else:
            # Если текущий провайдер последний или не найден, берем первый
            next_provider_id = active_providers[0][0]

        # Не переключаемся на тот же провайдер
        if next_provider_id == self.current_provider:
            print("❌ Следующий провайдер совпадает с текущим")
            return False

        old_provider = self.current_provider
        self.current_provider = next_provider_id
        self.stats['fallback_switches'] += 1

        print(f"🔄 Fallback: переключение с {self.providers[old_provider]['name']} на {self.providers[next_provider_id]['name']}")
        return True

    def _is_provider_in_circuit_break(self, provider_id: str = None) -> bool:
        """🔌 Проверка Circuit Breaker для провайдера"""
        if provider_id is None:
            provider_id = self.current_provider

        if provider_id not in self.providers:
            return False

        provider = self.providers[provider_id]

        # Проверяем условия circuit break
        failure_threshold = 5  # Максимум 5 неудач
        recovery_timeout = 300  # 5 минут восстановления

        if provider['failure_count'] >= failure_threshold:
            if provider['last_failure']:
                # Проверяем, прошло ли время восстановления
                from datetime import datetime
                last_failure_time = datetime.fromisoformat(provider['last_failure'])
                time_since_failure = (datetime.now() - last_failure_time).total_seconds()

                if time_since_failure < recovery_timeout:
                    # Провайдер все еще в circuit break
                    return True
                else:
                    # Время восстановления прошло, сбрасываем счетчик
                    print(f"🔄 Circuit Breaker: провайдер {provider['name']} восстановлен")
                    provider['failure_count'] = 0
                    provider['last_failure'] = None
                    return False
            else:
                # Нет времени последней ошибки, но счетчик высок - включаем circuit break
                return True

        return False
    
    def simulate_provider_failure(self, provider_id: str) -> dict:
        """🧪 Симуляция отказа провайдера для тестирования fallback"""
        if provider_id not in self.providers:
            return {
                'success': False,
                'error': f'Провайдер {provider_id} не найден'
            }
        
        # Отключаем провайдера
        self.providers[provider_id]['active'] = False
        self.providers[provider_id]['failure_count'] += 1
        self.providers[provider_id]['last_failure'] = datetime.now().isoformat()
        
        # Если это текущий провайдер, переключаемся на следующий
        if self.current_provider == provider_id:
            self._switch_to_next_provider()
        
        return {
            'success': True,
            'message': f'Провайдер {self.providers[provider_id]["name"]} отключен',
            'current_provider': self.current_provider,
            'fallback_occurred': True
        }
    
    def reset_system_state(self) -> dict:
        """🔄 Сброс состояния fallback системы"""
        # Сбрасываем состояние всех провайдеров
        for provider in self.providers.values():
            provider['active'] = True
            provider['failure_count'] = 0
            provider['last_failure'] = None
        
        # Возвращаемся к приоритетному провайдеру
        self.current_provider = 'openrouter'
        
        # Сбрасываем статистику fallback
        self.stats['fallback_switches'] = 0
        self.stats['provider_failures'] = {
            'openrouter': 0,
            'groq': 0
        }
        
        return {
            'success': True,
            'message': 'Состояние fallback системы сброшено',
            'current_provider': self.current_provider,
            'active_providers': [pid for pid, p in self.providers.items() if p['active']]
        }


def get_available_dates():
    """📅 Получение списка доступных дат из папки data/emails"""
    from pathlib import Path
    import os
    
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    emails_dir = project_root / "data" / "emails"
    
    if not emails_dir.exists():
        print(f"❌ Папка с данными не найдена: {emails_dir}")
        return []
    
    dates = []
    for item in os.listdir(emails_dir):
        item_path = emails_dir / item
        if item_path.is_dir() and item.startswith('2025-'):
            dates.append(item)
    
    return sorted(dates)

def show_date_menu():
    """📋 Показать меню выбора дат"""
    dates = get_available_dates()
    
    if not dates:
        print("❌ Доступные даты не найдены")
        return None
    
    print("\n📅 Доступные даты:")
    for i, date in enumerate(dates, 1):
        print(f"   {i:2d}. {date}")
    
    print(f"   {len(dates)+1:2d}. Диапазон дат")
    print(f"   {len(dates)+2:2d}. Все даты")
    print("    0. Назад")
    
    while True:
        try:
            choice = input("\n🎯 Выберите опцию (номер): ").strip()
            
            if choice == '0':
                return None
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(dates):
                return [dates[choice_num - 1]]
            elif choice_num == len(dates) + 1:
                # Диапазон дат
                print("\n📊 Выбор диапазона дат:")
                start_idx = int(input(f"Начальная дата (1-{len(dates)}): ")) - 1
                end_idx = int(input(f"Конечная дата (1-{len(dates)}): ")) - 1
                
                if 0 <= start_idx <= end_idx < len(dates):
                    return dates[start_idx:end_idx + 1]
                else:
                    print("❌ Неверный диапазон дат")
                    continue
            elif choice_num == len(dates) + 2:
                return dates
            else:
                print("❌ Неверный выбор")
                continue
                
        except (ValueError, IndexError):
            print("❌ Введите корректный номер")
            continue

def show_provider_menu():
    """🔧 Показать меню выбора провайдера"""
    providers = {
        '1': 'groq',
        '2': 'replicate', 
        '3': 'openrouter'
    }
    
    print("\n🤖 Доступные LLM провайдеры:")
    print("   1. Groq (рекомендуется)")
    print("   2. Replicate")
    print("   3. OpenRouter")
    print("   4. Автовыбор (fallback система)")
    print("   0. Назад")
    
    while True:
        choice = input("\n🎯 Выберите провайдера (номер): ").strip()
        
        if choice == '0':
            return None
        elif choice in providers:
            return providers[choice]
        elif choice == '4':
            return 'auto'
        else:
            print("❌ Неверный выбор")
            continue

def run_interactive_mode():
    """🎮 Интерактивный режим работы с меню"""
    print("\n" + "="*60)
    print("🤖 LLM ЭКСТРАКТОР КОНТАКТОВ - ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("="*60)
    
    while True:
        print("\n📋 Главное меню:")
        print("   1. Обработка писем с извлечением контактов")
        print("   2. Экспорт в Google Sheets")
        print("   3. Тестирование провайдеров")
        print("   4. Статистика системы")
        print("   0. Выход")
        
        choice = input("\n🎯 Выберите действие (номер): ").strip()
        
        if choice == '0':
            print("👋 До свидания!")
            break
        elif choice == '1':
            # Обработка писем
            selected_dates = show_date_menu()
            if selected_dates:
                selected_provider = show_provider_menu()
                if selected_provider:
                    process_emails_for_dates(selected_dates, selected_provider)
        elif choice == '2':
            # Экспорт в Google Sheets
            selected_dates = show_date_menu()
            if selected_dates:
                export_to_sheets(selected_dates)
        elif choice == '3':
            # Тестирование провайдеров
            test_providers()
        elif choice == '4':
            # Статистика
            show_system_stats()
        else:
            print("❌ Неверный выбор")

def load_emails_for_date(date):
    """📁 Загрузка JSON файлов писем за конкретную дату"""
    from pathlib import Path
    import json
    
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    emails_dir = project_root / "data" / "emails" / date
    
    if not emails_dir.exists():
        print(f"❌ Папка с письмами за {date} не найдена: {emails_dir}")
        return []
    
    emails = []
    json_files = sorted(list(emails_dir.glob("*.json")), key=lambda x: x.name)
    
    print(f"   📁 Найдено {len(json_files)} JSON файлов писем (отсортированы по имени)")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
                emails.append(email_data)
        except Exception as e:
            print(f"   ⚠️ Ошибка загрузки {json_file.name}: {e}")
    
    return emails

def check_and_run_ocr_for_date(date):
    """🔍 Проверка и запуск OCR для вложений за дату"""
    from pathlib import Path
    import subprocess
    import sys
    
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    final_results_dir = project_root / "data" / "final_results" / "texts" / date
    attachments_dir = project_root / "data" / "attachments" / date
    
    # Проверяем наличие вложений
    if not attachments_dir.exists():
        print(f"   📎 Папка с вложениями за {date} не найдена")
        return False
    
    attachment_files = list(attachments_dir.glob("*"))
    attachment_files = [f for f in attachment_files if f.is_file() and not f.name.startswith('.')]
    
    if not attachment_files:
        print(f"   📎 Вложения за {date} не найдены")
        return False
    
    # Проверяем наличие результатов OCR
    if final_results_dir.exists():
        ocr_files = list(final_results_dir.glob("*.txt"))
        if len(ocr_files) >= len(attachment_files):
            print(f"   ✅ OCR результаты уже существуют ({len(ocr_files)} файлов)")
            return True
    
    print(f"   🔄 Запускаю OCR для {len(attachment_files)} вложений...")
    
    # Запускаем OCR процессор
    ocr_script = project_root / "src" / "ocr_processor.py"
    try:
        # Запускаем OCR процессор в автоматическом режиме для конкретной даты
        result = subprocess.run([
            sys.executable, str(ocr_script), "--auto", "--date", date
        ], capture_output=True, text=True, cwd=str(project_root))
        
        if result.returncode == 0:
            print(f"   ✅ OCR завершен успешно")
            return True
        else:
            print(f"   ❌ Ошибка OCR: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка запуска OCR: {e}")
        return False

def load_ocr_results_for_date(date):
    """📄 Загрузка результатов OCR за дату"""
    from pathlib import Path
    
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    final_results_dir = project_root / "data" / "final_results" / "texts" / date
    
    if not final_results_dir.exists():
        return []
    
    ocr_results = []
    txt_files = list(final_results_dir.glob("*.txt"))
    
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Извлекаем текст (пропускаем заголовки)
                lines = content.split('\n')
                text_start_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('# ==='):
                        text_start_idx = i + 1
                        break
                
                text = '\n'.join(lines[text_start_idx:]).strip()
                
                if text:
                    ocr_results.append({
                        'file_name': txt_file.name,
                        'text': text,
                        'source': 'ocr_attachment'
                    })
        except Exception as e:
            print(f"   ⚠️ Ошибка загрузки OCR результата {txt_file.name}: {e}")
    
    return ocr_results

def process_emails_for_dates(dates, provider):
    """📧 Обработка писем за выбранные даты"""
    print(f"\n🚀 Начинаю обработку писем за {len(dates)} дат(ы) с провайдером {provider}")
    
    # Инициализируем экстрактор
    extractor = ContactExtractor(test_mode=False)
    
    # Устанавливаем выбранного провайдера
    if provider != 'auto':
        if provider in extractor.providers:
            extractor.current_provider = provider
            print(f"✅ Установлен провайдер: {extractor.providers[provider]['name']}")
        else:
            print(f"⚠️ Провайдер {provider} не найден, используем автовыбор")
    
    total_contacts = 0
    total_emails_processed = 0
    
    for date in dates:
        print(f"\n📅 Обработка даты: {date}")
        
        # Загружаем письма за дату
        print(f"   📁 Загрузка писем за {date}...")
        emails = load_emails_for_date(date)
        
        if not emails:
            print(f"   📭 Письма за {date} не найдены")
            continue
        
        # Проверяем и запускаем OCR если нужно
        print(f"   🔍 Проверка результатов OCR...")
        check_and_run_ocr_for_date(date)
        
        # Загружаем результаты OCR
        ocr_results = load_ocr_results_for_date(date)
        print(f"   📄 Загружено {len(ocr_results)} результатов OCR")
        
        # Обрабатываем каждое письмо
        print(f"   🤖 Извлечение контактов с помощью {extractor.providers[extractor.current_provider]['name']}...")
        
        date_contacts = 0
        for email in emails:
            try:
                # Формируем текст для анализа
                text_parts = []
                
                # Добавляем текст письма
                if email.get('body'):
                    text_parts.append(f"ПИСЬМО:\n{email['body']}")
                
                # Добавляем результаты OCR вложений
                for ocr_result in ocr_results:
                    text_parts.append(f"ВЛОЖЕНИЕ ({ocr_result['file_name']}):\n{ocr_result['text']}")
                
                if not text_parts:
                    continue
                
                combined_text = "\n\n" + "="*50 + "\n\n".join(text_parts)
                
                # Формируем метаданные
                metadata = {
                    'subject': email.get('subject', ''),
                    'from': email.get('from', ''),
                    'date': email.get('date', ''),
                    'message_id': email.get('message_id', '')
                }
                
                # Извлекаем контакты
                result = extractor.extract_contacts(combined_text, metadata)
                
                if result.get('contacts'):
                    contacts_count = len(result['contacts'])
                    date_contacts += contacts_count
                    print(f"     ✅ Найдено {contacts_count} контактов в письме {email.get('subject', 'Без темы')[:50]}...")
                    
                    # Здесь можно добавить сохранение результатов
                    
            except Exception as e:
                print(f"     ❌ Ошибка обработки письма: {e}")
        
        total_emails_processed += len(emails)
        total_contacts += date_contacts
        print(f"   ✅ Обработано писем: {len(emails)}, найдено контактов: {date_contacts}")
    
    print(f"\n🎉 Обработка завершена! Всего найдено контактов: {total_contacts}")
    print(f"📊 Обработано писем: {total_emails_processed}")
    print(f"📊 Статистика: {extractor.get_stats()}")

def export_to_sheets(dates):
    """📊 Экспорт данных в Google Sheets"""
    print(f"\n📊 Экспорт данных в Google Sheets за {len(dates)} дат(ы)")
    
    # Импортируем экспортер
    try:
        from google_sheets_exporter import GoogleSheetsExporter
        exporter = GoogleSheetsExporter()
        
        for date in dates:
            print(f"📅 Экспорт данных за {date}...")
            success = exporter.export_results_by_date(date)
            if success:
                print(f"   ✅ Данные за {date} экспортированы")
            else:
                print(f"   ❌ Ошибка экспорта за {date}")
                
    except ImportError as e:
        print(f"❌ Ошибка импорта Google Sheets экспортера: {e}")
    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")

def test_providers():
    """🧪 Тестирование всех провайдеров"""
    print("\n🧪 Тестирование LLM провайдеров...")
    
    test_text = """
    Добрый день!
    
    Меня зовут Иван Петров, я работаю в компании "ТехноЛаб" на должности менеджера по продажам.
    Мой email: ivan.petrov@technolab.ru, телефон: +7 (495) 123-45-67.
    
    Хотел бы обсудить возможность сотрудничества.
    
    С уважением,
    Иван Петров
    ООО "ТехноЛаб"
    г. Москва
    """
    
    extractor = ContactExtractor(test_mode=False)
    
    for provider_id, provider_info in extractor.providers.items():
        if provider_info['active'] and provider_info['api_key']:
            print(f"\n🔧 Тестирование {provider_info['name']}...")
            
            # Временно устанавливаем провайдера
            original_provider = extractor.current_provider
            extractor.current_provider = provider_id
            
            try:
                result = extractor.extract_contacts(test_text)
                contacts_count = len(result.get('contacts', []))
                print(f"   ✅ {provider_info['name']}: найдено {contacts_count} контактов")
            except Exception as e:
                print(f"   ❌ {provider_info['name']}: ошибка - {e}")
            
            # Восстанавливаем провайдера
            extractor.current_provider = original_provider
        else:
            print(f"   ⚠️ {provider_info['name']}: неактивен или нет API ключа")

def show_system_stats():
    """📈 Показать статистику системы"""
    print("\n📈 Статистика системы:")
    
    extractor = ContactExtractor(test_mode=False)
    stats = extractor.get_stats()
    
    print(f"   📊 Всего запросов: {stats['total_requests']}")
    print(f"   ✅ Успешных запросов: {stats['successful_requests']}")
    print(f"   ❌ Неудачных запросов: {stats['failed_requests']}")
    print(f"   🔄 Повторных попыток: {stats['retry_attempts']}")
    print(f"   📝 Ошибок валидации JSON: {stats['json_validation_errors']}")
    print(f"   🔀 Переключений провайдеров: {stats['fallback_switches']}")
    
    print("\n🤖 Статистика провайдеров:")
    for provider, failures in stats['provider_failures'].items():
        status = "✅ Активен" if extractor.providers[provider]['active'] else "❌ Неактивен"
        print(f"   {provider}: {failures} ошибок, {status}")

if __name__ == "__main__":
    import sys
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Тестовый режим
        print("🧪 Запуск в тестовом режиме...")
        extractor = ContactExtractor(test_mode=True)
        
        test_text = """
        Добрый день!
        
        Меня зовут Иван Петров, я работаю в компании "ТехноЛаб" на должности менеджера по продажам.
        Мой email: ivan.petrov@technolab.ru, телефон: +7 (495) 123-45-67.
        
        Хотел бы обсудить возможность сотрудничества.
        
        С уважением,
        Иван Петров
        ООО "ТехноЛаб"
        г. Москва
        """
        
        print("🚀 Тестирование экстрактора контактов...")
        result = extractor.extract_contacts(test_text)
        
        print("\n📊 Результат:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\n📈 Статистика:")
        print(json.dumps(extractor.get_stats(), ensure_ascii=False, indent=2))
    else:
        # Интерактивный режим
        run_interactive_mode()