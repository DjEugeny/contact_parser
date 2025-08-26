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

from dotenv import load_dotenv
import os

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
        
        print(f"🤖 ContactExtractor инициализирован (test_mode={test_mode})")
        print(f"   📁 Конфигурация: {self.config_path}")
        print(f"   🔄 Fallback система: OpenRouter -> Groq")
        print(f"   🎯 Текущий провайдер: {self.providers[self.current_provider]['name']}")
    
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
                'active': True,
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
                'active': True,
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
        
        required_fields = ['contacts', 'business_context', 'recommended_actions']
        
        # Проверяем основные поля
        for field in required_fields:
            if field not in response_data:
                print(f"❌ Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем типы основных полей
        if not isinstance(response_data['business_context'], str):
            print("❌ Поле 'business_context' должно быть строкой")
            return False
            
        if not isinstance(response_data['recommended_actions'], str):
            print("❌ Поле 'recommended_actions' должно быть строкой")
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
        has_name = contact.get('name', '').strip()
        has_email = contact.get('email', '').strip()
        has_phone = contact.get('phone', '').strip()
        
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
                'recommended_actions': 'Тестовые рекомендации',
                'provider_used': 'Test Mode'
            }
        
        for attempt in range(max_retries):
            try:
                self.stats['total_requests'] += 1
                if attempt > 0:
                    self.stats['retry_attempts'] += 1
                    print(f"🔄 Повторная попытка {attempt + 1}/{max_retries}")
                    time.sleep(2 ** attempt)  # Экспоненциальная задержка
                
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
                            'recommended_actions': 'Проверить формат ответа LLM',
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
                
                # Пробуем переключиться на другого провайдера
                if self._switch_to_next_provider():
                    print(f"🔄 Повторяем запрос с новым провайдером")
                    continue  # Повторяем попытку с новым провайдером
                
                if attempt == max_retries - 1:
                    self.stats['failed_requests'] += 1
                    return {
                        'contacts': [],
                        'business_context': f'Ошибка LLM: {str(e)}',
                        'recommended_actions': 'Проверить подключение к LLM и API ключи',
                        'error': str(e)
                    }
        
        # Этот код не должен выполняться, но на всякий случай
        self.stats['failed_requests'] += 1
        return {
            'contacts': [],
            'business_context': 'Неизвестная ошибка',
            'recommended_actions': 'Обратиться к разработчику',
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
        
        try:
            # Выполняем запрос с обработкой SSL ошибок
            response = requests.post(
                current_provider['base_url'],
                headers=headers,
                json=payload,
                timeout=60,
                verify=True  # Включаем проверку SSL сертификатов
            )
            
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
    
    def _wait_for_replicate_result(self, prediction_id: str, provider_config: dict, max_wait: int = 300) -> str:
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
        
        # Разбиваем текст на части по 3000 символов (примерно 750 токенов)
        chunk_size = 3000
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
                key_parts.append(contact['email'].lower().strip())
            if contact.get('phone'):
                # Нормализуем телефон (убираем пробелы, скобки, дефисы)
                phone_normalized = ''.join(filter(str.isdigit, contact['phone']))
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
        
        # Логируем сырой ответ для диагностики
        print(f"🔍 Сырой ответ LLM ({len(response_text)} символов):")
        print(f"'{response_text[:500]}{'...' if len(response_text) > 500 else ''}'")
        
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"🔍 Найденный JSON: {json_str[:200]}{'...' if len(json_str) > 200 else ''}")
                result = json.loads(json_str)  # Post-валидация JSON
                
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
        """📄 Обработка больших текстов через разбивку на части с оптимизацией памяти"""
        
        # Оптимизированные размеры для предотвращения `zsh: killed`
        chunk_size = 8000   # Уменьшено для экономии памяти
        overlap = 800       # Пропорционально уменьшено
        
        import gc  # Для принудительной очистки памяти
        
        # Разбиваем текст на части
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            
            # Добавляем информацию о части
            chunk_info = f"\n\n[ЧАСТЬ {len(chunks) + 1} ИЗ БОЛЬШОГО ПИСЬМА, СИМВОЛЫ {start}-{end}]\n"
            chunk = chunk_info + chunk
            
            chunks.append(chunk)
            
            # Следующая часть с перекрытием
            start = end - overlap
            if start >= len(text):
                break
        
        print(f"   📊 Разбито на {len(chunks)} частей по ~{chunk_size} символов")
        
        # Обрабатываем каждую часть
        all_contacts = []
        all_contexts = []
        all_actions = []
        
        for i, chunk in enumerate(chunks):
            print(f"   🔍 Обработка части {i + 1}/{len(chunks)}")
            
            try:
                # Обрабатываем часть
                chunk_result = self._make_llm_request_with_retries(prompt, chunk)
                
                # Собираем результаты
                if 'contacts' in chunk_result and chunk_result['contacts']:
                    all_contacts.extend(chunk_result['contacts'])
                
                if 'business_context' in chunk_result:
                    all_contexts.append(f"Часть {i + 1}: {chunk_result['business_context']}")
                
                if 'recommended_actions' in chunk_result:
                    all_actions.append(f"Часть {i + 1}: {chunk_result['recommended_actions']}")
                
                # Небольшая пауза между запросами и очистка памяти
                if i < len(chunks) - 1:
                    time.sleep(2)
                    
                # Принудительная очистка памяти после каждой части
                del chunk_result
                gc.collect()
            
            except Exception as e:
                print(f"   ❌ Ошибка обработки части {i + 1}: {e}")
                all_contexts.append(f"Часть {i + 1}: Ошибка обработки - {str(e)}")
                # Очистка памяти даже при ошибке
                gc.collect()
        
        # Удаляем дубликаты контактов
        unique_contacts = self._deduplicate_contacts(all_contacts)
        
        # Очищаем промежуточные данные для экономии памяти
        del all_contacts, chunks
        gc.collect()
        
        # Формируем итоговый результат
        result = {
            'contacts': unique_contacts,
            'business_context': ' | '.join(all_contexts) if all_contexts else 'Контекст не извлечен',
            'recommended_actions': ' | '.join(all_actions) if all_actions else 'Рекомендации не получены',
            'provider_used': f"{self.providers[self.current_provider]['name']} ({self.providers[self.current_provider]['model']}) - {len(chunks)} частей",
            'processing_time': datetime.now().isoformat(),
            'text_length': len(text),
            'chunks_processed': len(chunks),
            'total_contacts_found': len(all_contacts),
            'unique_contacts_found': len(unique_contacts)
        }
        
        print(f"   ✅ Обработка завершена: {len(unique_contacts)} уникальных контактов из {len(all_contacts)} найденных")
        
        return result
    
    def _deduplicate_contacts(self, contacts: List[dict]) -> List[dict]:
        """🔄 Удаление дубликатов контактов"""
        
        if not contacts:
            return []
        
        unique_contacts = []
        seen_emails = set()
        seen_phones = set()
        
        for contact in contacts:
            email = contact.get('email', '').lower().strip()
            phone = contact.get('phone', '').strip()
            
            # Нормализуем телефон (убираем пробелы, скобки, дефисы)
            normalized_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
            
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
            
            # Временно отключаем тестовый режим для реальных писем
            if metadata and not self.test_mode:
                self.test_mode = False
            
            # Загружаем промпт
            prompt = self._load_prompt("contact_extraction.txt")
            
            if prompt.startswith("ERROR:"):
                return {
                    'contacts': [],
                    'business_context': prompt,
                    'recommended_actions': 'Проверить наличие файла промпта',
                    'error': 'Prompt loading failed'
                }
            
            # Обработка больших текстов через разбивку на части
            if len(text) > 12000:
                print(f"   📄 Большой текст ({len(text)} символов), разбиваем на части")
                return self._process_large_text(text, prompt, metadata)
            else:
                print(f"   📝 Обычный размер текста: {len(text)} символов")
            
            # Определяем провайдера
            provider_info = f"{self.providers[self.current_provider]['name']} ({self.providers[self.current_provider]['model']})"
            
            # Тестовый режим
            if self.test_mode and not metadata:
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
                    'recommended_actions': 'Тестовые рекомендации',
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
                    'recommended_actions': 'Проверить логику обработки ответа LLM',
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
                'recommended_actions': 'Проверить настройки LLM и повторить',
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
        """🔄 Переключение на следующий доступный провайдер"""
        # Получаем список активных провайдеров, отсортированных по приоритету
        active_providers = [
            (pid, provider) for pid, provider in self.providers.items()
            if provider['active'] and provider['api_key']
        ]
        active_providers.sort(key=lambda x: x[1]['priority'])
        
        # Ищем следующий провайдер после текущего
        current_index = -1
        for i, (pid, _) in enumerate(active_providers):
            if pid == self.current_provider:
                current_index = i
                break
        
        # Переключаемся на следующий провайдер
        if current_index >= 0 and current_index + 1 < len(active_providers):
            next_provider_id = active_providers[current_index + 1][0]
            old_provider = self.current_provider
            self.current_provider = next_provider_id
            self.stats['fallback_switches'] += 1
            
            print(f"🔄 Fallback: переключение с {self.providers[old_provider]['name']} на {self.providers[next_provider_id]['name']}")
            return True
        
        # Если нет следующего провайдера, пробуем первый в списке (если он не текущий)
        if active_providers and active_providers[0][0] != self.current_provider:
            next_provider_id = active_providers[0][0]
            old_provider = self.current_provider
            self.current_provider = next_provider_id
            self.stats['fallback_switches'] += 1
            
            print(f"🔄 Fallback: переключение с {self.providers[old_provider]['name']} на {self.providers[next_provider_id]['name']}")
            return True
        
        print("❌ Нет доступных провайдеров для fallback")
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
    json_files = list(emails_dir.glob("*.json"))
    
    print(f"   📁 Найдено {len(json_files)} JSON файлов писем")
    
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