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
from datetime import datetime, timedelta
import random

from dotenv import load_dotenv
import os
from src.utils.logger import get_logger

# Загружаем переменные окружения
load_dotenv()


class ContactExtractor:
    """🔥 Экстрактор контактов с LLM и JSON Schema валидацией + Fallback система"""
    
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.logger = get_logger(__name__)
        
        # Импортируем конфигурацию
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from src.config import config
        self.config = config
        
        # Проверяем наличие API ключей (пропускаем в тестовом режиме)
        if not test_mode and not self.config.validate_api_keys():
            raise ValueError("Missing required API keys. Please check your environment variables.")
        
        # Конфигурация провайдеров из конфигурации
        self.providers = self.config.providers
        
        # Инициализируем состояние провайдеров из конфигурации
        self.provider_states = {}
        for provider_name in self.config.providers.keys():
            self.provider_states[provider_name] = {
                'is_healthy': True,
                'consecutive_failures': 0,
                'last_success': datetime.now().isoformat(),
                'circuit_breaker_open_until': None
            }
        
        # Текущий активный провайдер (первый из списка приоритетов)
        self.current_provider = self.config.provider_order[0]
        
        # Параметры из конфигурации
        self.max_fallback_attempts = self.config.max_fallback_attempts
        self.timeout = self.config.timeout
        self.retry_delay = self.config.retry_delay
        
        # Папка с промптами
        current_file = Path(__file__)
        project_root = current_file.parent
        self.prompts_dir = project_root.parent / "prompts"
        
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
                'groq': 0
            },
            'circuit_breaker_activations': {
                'openrouter': 0,
                'groq': 0
            }
        }
        
        self.logger.info(f"🤖 ContactExtractor инициализирован (test_mode={test_mode})")
        self.logger.info(f"   🔄 Fallback система: OpenRouter -> Groq")
        self.logger.info(f"   🎯 Текущий провайдер: {self.providers[self.current_provider]['name']}")
        self.logger.info(f"   ⚡ Circuit breaker: активен")
        self.logger.info(f"   ⏱️  Timeout: {self.timeout}s, Retry delay: {self.retry_delay}s")
    
    def _load_prompt(self, filename: str) -> str:
        """📄 Загрузка промпта из файла"""
        
        prompt_path = self.prompts_dir / filename
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content
        except FileNotFoundError:
            self.logger.error(f"❌ Промпт не найден: {prompt_path}")
            return f"ERROR: Промпт {filename} не найден"
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки промпта {filename}: {e}")
            return f"ERROR: Не удалось загрузить {filename}"
    
    def _validate_json_schema(self, response_data: dict) -> bool:
        """✅ Улучшенная валидация JSON Schema для ответа LLM"""
        
        if not isinstance(response_data, dict):
            self.logger.error("❌ Ответ должен быть объектом")
            return False
        
        required_fields = ['contacts', 'business_context', 'recommended_actions']
        
        # Проверяем основные поля
        for field in required_fields:
            if field not in response_data:
                self.logger.error(f"❌ Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем типы основных полей
        if not isinstance(response_data['business_context'], str):
            self.logger.error("❌ Поле 'business_context' должно быть строкой")
            return False
            
        if not isinstance(response_data['recommended_actions'], str):
            self.logger.error("❌ Поле 'recommended_actions' должно быть строкой")
            return False
        
        # Проверяем структуру contacts
        if not isinstance(response_data['contacts'], list):
            self.logger.error("❌ Поле 'contacts' должно быть списком")
            return False
        
        # Проверяем каждый контакт
        valid_contacts = []
        for i, contact in enumerate(response_data['contacts']):
            if not isinstance(contact, dict):
                self.logger.warning(f"⚠️ Контакт {i} не является объектом, пропускаем")
                continue
            
            # Проверяем обязательные поля контакта
            contact_required = ['name', 'email', 'phone', 'organization', 'confidence']
            
            for field in contact_required:
                if field not in contact:
                    self.logger.warning(f"⚠️ Контакт {i}: отсутствует поле {field}, добавляем пустое значение")
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
            self.logger.warning(f"⚠️ Контакт {index}: некорректный email '{email}'")
            contact['email'] = ''  # Очищаем некорректный email
        
        # Валидация телефона
        phone = contact.get('phone', '')
        if phone and not self._is_valid_phone(phone):
            self.logger.warning(f"⚠️ Контакт {index}: некорректный телефон '{phone}'")
            contact['phone'] = ''  # Очищаем некорректный телефон
        
        # Валидация confidence
        confidence = contact.get('confidence', 0)
        if not isinstance(confidence, (int, float)):
            self.logger.warning(f"⚠️ Контакт {index}: confidence должен быть числом, получен {type(confidence)}")
            contact['confidence'] = 0.0
        elif confidence < 0 or confidence > 1:
            self.logger.warning(f"⚠️ Контакт {index}: confidence должен быть от 0 до 1, получен {confidence}")
            contact['confidence'] = max(0, min(1, float(confidence)))
        
        # Валидация строковых полей
        string_fields = ['name', 'organization', 'position', 'city']
        for field in string_fields:
            if field in contact and not isinstance(contact[field], str):
                self.logger.warning(f"⚠️ Контакт {index}: поле '{field}' должно быть строкой")
                contact[field] = str(contact[field]) if contact[field] is not None else ''
        
        # Проверяем, что есть хотя бы имя или email или телефон
        has_name = contact.get('name', '').strip()
        has_email = contact.get('email', '').strip()
        has_phone = contact.get('phone', '').strip()
        
        if not (has_name or has_email or has_phone):
            self.logger.warning(f"⚠️ Контакт {index}: отсутствуют ключевые данные (имя, email, телефон)")
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
        
        return digits.isdigit() and 7 <= len(digits) <= 15

    def _is_circuit_breaker_open(self, provider: str) -> bool:
        """⚡ Проверка состояния circuit breaker для провайдера"""
        state = self.provider_states[provider]
        if state['circuit_breaker_open_until']:
            open_until = datetime.fromisoformat(state['circuit_breaker_open_until'])
            if datetime.now() < open_until:
                return True
            else:
                # Circuit breaker закрывается
                state['circuit_breaker_open_until'] = None
                state['consecutive_failures'] = 0
                state['is_healthy'] = True
                self.logger.info(f"✅ Circuit breaker для {provider} закрыт")
        return False

    def _open_circuit_breaker(self, provider: str):
        """🔒 Открытие circuit breaker для провайдера"""
        state = self.provider_states[provider]
        state['circuit_breaker_open_until'] = (datetime.now() + 
                                             timedelta(minutes=5)).isoformat()
        state['is_healthy'] = False
        state['consecutive_failures'] = 0
        self.stats['circuit_breaker_activations'][provider] += 1
        self.logger.warning(f"🔒 Circuit breaker открыт для {provider} на 5 минут")

    def _record_success(self, provider: str):
        """✅ Запись успешного запроса для провайдера"""
        state = self.provider_states[provider]
        state['consecutive_failures'] = 0
        state['last_success'] = datetime.now().isoformat()
        state['is_healthy'] = True

    def _record_failure(self, provider: str):
        """❌ Запись неудачного запроса для провайдера"""
        state = self.provider_states[provider]
        state['consecutive_failures'] += 1
        
        # Открываем circuit breaker при 3+ подряд неудачах
        if state['consecutive_failures'] >= 3:
            self._open_circuit_breaker(provider)

    def _get_next_healthy_provider(self, current: str) -> Optional[str]:
        """🔄 Получение следующего здорового провайдера по порядку из конфигурации"""
        providers_order = self.config.provider_order
        current_index = providers_order.index(current) if current in providers_order else -1
        
        for i in range(current_index + 1, len(providers_order)):
            next_provider = providers_order[i]
            if (self.provider_states[next_provider]['is_healthy'] and 
                not self._is_circuit_breaker_open(next_provider)):
                return next_provider
        
        return None

    def _log_provider_status(self):
        """📊 Вывод статуса провайдеров"""
        status_lines = []
        for provider in self.config.provider_order:
            if provider in self.provider_states:
                state = self.provider_states[provider]
                health = "🟢" if state['is_healthy'] else "🔴"
                cb = "🔒" if self._is_circuit_breaker_open(provider) else "🔓"
                failures = state['consecutive_failures']
                status_lines.append(f"   {provider}: {health} {cb} (failures: {failures})")
        
        self.logger.info("\n📊 Статус провайдеров:")
        for line in status_lines:
            self.logger.info(line)

    def _make_llm_request_with_retries(self, prompt: str, text: str, max_retries: int = None) -> dict:
        """🔄 Улучшенный запрос с circuit breaker и интеллектуальным fallback"""
        
        if max_retries is None:
            max_retries = self.config.max_retries
            
        last_exception = None
        original_provider = self.current_provider
        
        # Показываем текущий статус провайдеров
        self._log_provider_status()
        
        for attempt in range(max_retries + 1):
            try:
                # Проверяем, доступен ли текущий провайдер
                if self._is_circuit_breaker_open(self.current_provider):
                    next_provider = self._get_next_healthy_provider(self.current_provider)
                    if next_provider:
                        self.current_provider = next_provider
                        self.logger.info(f"🔄 Автоматическое переключение на {self.providers[next_provider]['name']} (circuit breaker)")
                        self.stats['fallback_switches'] += 1
                    else:
                        raise Exception("Все провайдеры недоступны (circuit breaker)")
                
                # Делаем запрос
                result = self._make_llm_request(prompt, text)
                
                # Успешный запрос - записываем успех
                self._record_success(self.current_provider)
                
                # Проверяем валидацию JSON Schema
                if self._validate_json_schema(result):
                    self.stats['successful_requests'] += 1
                    
                    # Возвращаемся к оригинальному провайдеру если был переключен
                    if self.current_provider != original_provider and attempt == 0:
                        self.current_provider = original_provider
                    
                    return result
                else:
                    self.stats['json_validation_errors'] += 1
                    
                    # Пробуем исправить структуру ответа
                    fixed_result = self._fix_json_structure(result)
                    if fixed_result and self._validate_json_schema(fixed_result):
                        self.logger.info(f"✅ JSON Schema исправлена")
                        self.stats['successful_requests'] += 1
                        return fixed_result
                    
                    raise Exception("JSON Schema валидация не пройдена")
                
            except Exception as e:
                last_exception = e
                self.stats['failed_requests'] += 1
                
                # Записываем неудачу
                self._record_failure(self.current_provider)
                
                if attempt < max_retries:
                    # Проверяем доступность следующего провайдера
                    next_provider = self._get_next_healthy_provider(self.current_provider)
                    
                    if next_provider and next_provider != self.current_provider:
                        self.current_provider = next_provider
                        self.logger.warning(f"🔄 Переключение на {self.providers[next_provider]['name']} (ошибка: {e})")
                        self.stats['fallback_switches'] += 1
                        continue  # Переходим к следующей попытке без задержки
                    
                    # Экспоненциальная задержка с jitter для текущего провайдера
                    base_delay = min(2 ** attempt, 300)  # Максимум 5 минут
                    jitter = random.uniform(0.1, 0.5) * base_delay
                    delay = base_delay + jitter
                    
                    # Специальная обработка rate limit
                    if "Rate limit" in str(e) or "HTTP 429" in str(e):
                        import re
                        wait_match = re.search(r'ожидание (\d+) сек', str(e))
                        if wait_match:
                            delay = int(wait_match.group(1))
                        else:
                            delay = 60
                        
                        self.logger.warning(f"⏳ Rate limit: ожидание {delay} сек")
                    else:
                        self.logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
                        self.logger.info(f"⏳ Ожидание {delay:.1f} сек перед повтором...")
                    
                    time.sleep(delay)
                else:
                    self.logger.error(f"❌ Все попытки исчерпаны после {max_retries} попыток")
                    break
        
        # Все попытки исчерпаны
        error_response = {
            'contacts': [],
            'business_context': f'Ошибка: {str(last_exception)}',
            'recommended_actions': 'Проверьте подключение к интернету и API ключи',
            'provider_used': self.providers[self.current_provider]['name'],
            'error': str(last_exception),
            'provider_status': {
                provider: {
                    'is_healthy': state['is_healthy'],
                    'consecutive_failures': state['consecutive_failures'],
                    'circuit_breaker_open': self._is_circuit_breaker_open(provider)
                }
                for provider, state in self.provider_states.items()
            }
        }
        
        return error_response
    
    def _make_llm_request(self, prompt: str, text: str) -> dict:
        """🤖 Улучшенный базовый запрос к LLM с лучшей обработкой ошибок"""
        
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
        
        # Получаем текущего провайдера
        current_provider = self.providers[self.current_provider]
        
        # Формируем запрос
        messages = [
            {
                "role": "user",
                "content": f"{prompt}\n\n📧 ТЕКСТ ДЛЯ АНАЛИЗА:\n{text}"
            }
        ]
        
        payload = {
            "model": current_provider['model'],
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        # Формируем заголовки для текущего провайдера
        headers = current_provider['headers'].copy()
        headers["Authorization"] = f"Bearer {self.config.get_api_key(self.current_provider)}"
        
        try:
            # Выполняем запрос с таймаутом из конфигурации
            response = requests.post(
                current_provider['base_url'],
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # Обработка ответов
            if response.status_code == 429:
                # Rate limit - извлекаем время ожидания
                retry_after = response.headers.get('Retry-After')
                wait_time = 60
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        pass
                
                # Обновляем статистику провайдера
                current_provider['failure_count'] += 1
                current_provider['last_failure'] = datetime.now().isoformat()
                self.stats['provider_failures'][self.current_provider] += 1
                
                raise Exception(f"Rate limit (HTTP 429): ожидание {wait_time} сек")
            
            response.raise_for_status()  # Проверка на другие HTTP ошибки
            
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                raise Exception("Пустой ответ от LLM")
            
            content = response_data['choices'][0]['message']['content']
            
            # Парсим JSON из ответа
            result = self._parse_llm_response(content)
            result['provider_used'] = current_provider['name']
            
            return result
            
        except requests.exceptions.Timeout:
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            raise Exception(f"Timeout при запросе к {current_provider['name']}")
            
        except requests.exceptions.ConnectionError as e:
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            raise Exception(f"Ошибка подключения к {current_provider['name']}: {str(e)}")
            
        except Exception as e:
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            self.stats['provider_failures'][self.current_provider] += 1
            raise e
    
    def _parse_llm_response(self, response_text: str) -> dict:
        """📝 Парсинг ответа LLM"""
        
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("JSON не найден в ответе LLM")
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON: {e}")
    
    def _process_large_text(self, text: str, prompt: str, metadata: dict = None) -> dict:
        """📄 Обработка больших текстов через разбивку на части"""
        
        chunk_size = 10000  # Размер части
        overlap = 1000      # Перекрытие между частями
        
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
        
        self.logger.info(f"   📊 Разбито на {len(chunks)} частей по ~{chunk_size} символов")
        
        # Обрабатываем каждую часть
        all_contacts = []
        all_contexts = []
        all_actions = []
        
        for i, chunk in enumerate(chunks):
            self.logger.info(f"   🔍 Обработка части {i + 1}/{len(chunks)}")
            
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
                
                # Небольшая пауза между запросами
                if i < len(chunks) - 1:
                    time.sleep(2)
            
            except Exception as e:
                self.logger.error(f"   ❌ Ошибка обработки части {i + 1}: {e}")
                all_contexts.append(f"Часть {i + 1}: Ошибка обработки - {str(e)}")
        
        # Удаляем дубликаты контактов
        unique_contacts = self._deduplicate_contacts(all_contacts)
        
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
        
        self.logger.info(f"   ✅ Обработка завершена: {len(unique_contacts)} уникальных контактов из {len(all_contacts)} найденных")
        
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
            
            # 🧪 Тестовый режим должен срабатывать раньше, до загрузки промпта,
            # чтобы не зависеть от наличия файлов и внешних ресурсов
            if self.test_mode and not metadata:
                print("   🧪 Активирован тестовый режим")
                result = {
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
                
                # Восстанавливаем исходный test_mode (на случай внешнего использования)
                self.test_mode = original_test_mode
                return result
            
            # Временно отключаем тестовый режим для реальных писем
            if metadata and self.test_mode:
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
            
            # Тестовый режим (старый блок оставлен нетронутым, но больше не достижим)
            # if self.test_mode and not metadata:
            #     print("   🧪 Активирован тестовый режим")
            #     result = {
            #         'contacts': [{
            #             'name': 'Тестовый Контакт',
            #             'email': 'test@example.com',
            #             'phone': '+7 (999) 123-45-67',
            #             'organization': 'Тестовая Организация',
            #             'position': 'Тестовая Должность',
            #             'city': 'Тестовый Город',
            #             'confidence': 0.95
            #         }],
            #         'business_context': 'Тестовый бизнес-контекст',
            #         'recommended_actions': 'Тестовые рекомендации',
            #         'provider_used': 'Test Mode'
            #     }
            #     
            #     # Восстанавливаем исходный test_mode
            #     self.test_mode = original_test_mode
            #     return result
            
            # Выполняем запрос с повторными попытками
            result = self._make_llm_request_with_retries(prompt, text)
            
            # Добавляем метаинформацию
            result['provider_used'] = provider_info
            result['processing_time'] = datetime.now().isoformat()
            result['text_length'] = len(text)
            
            # Статистика
            contacts_count = len(result.get('contacts', []))
            print(f"   ✅ Найдено контактов: {contacts_count}")
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
        
        # Отключаем провайдер
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


if __name__ == "__main__":
    # Тестирование
    extractor = ContactExtractor(test_mode=True)
    
    test_text = "Тестовое письмо от test@example.com"
    result = extractor.extract_contacts(test_text)
    
    print("\n📊 Результат тестирования:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n📈 Статистика:")
    print(json.dumps(extractor.get_stats(), ensure_ascii=False, indent=2))