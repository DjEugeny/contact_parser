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
    
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        
        # Настройка провайдеров (приоритет: OpenRouter -> Groq)
        self.providers = {
            'openrouter': {
                'name': 'OpenRouter',
                'api_key': os.getenv('OPENROUTER_API_KEY', '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'),
                'model': "qwen/qwen3-235b-a22b:free",
                'base_url': "https://openrouter.ai/api/v1/chat/completions",
                'priority': 1,
                'active': True,
                'failure_count': 0,
                'last_failure': None,
                'headers': {
                    'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY", "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")}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://localhost:3000',
                    'X-Title': 'Contact Extractor LLM'
                }
            },
            'groq': {
                'name': 'Groq',
                'api_key': os.getenv('GROQ_API_KEY', ''),
                'model': os.getenv('GROQ_MODEL', 'llama3-8b-8192'),
                'base_url': "https://api.groq.com/openai/v1/chat/completions",
                'priority': 2,
                'active': True,
                'failure_count': 0,
                'last_failure': None,
                'headers': {
                    'Authorization': f'Bearer {os.getenv("GROQ_API_KEY", "")}',
                    'Content-Type': 'application/json'
                }
            }
        }
        
        # Текущий активный провайдер
        self.current_provider = 'openrouter'
        
        # Максимальное количество попыток fallback
        self.max_fallback_attempts = 2
        
        # Папка с промптами
        current_file = Path(__file__)
        project_root = current_file.parent
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
                'groq': 0
            }
        }
        
        print(f"🤖 ContactExtractor инициализирован (test_mode={test_mode})")
        print(f"   🔄 Fallback система: OpenRouter -> Groq")
        print(f"   🎯 Текущий провайдер: {self.providers[self.current_provider]['name']}")
    
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
        """✅ Валидация JSON Schema для ответа LLM"""
        
        required_fields = ['contacts', 'business_context', 'recommended_actions']
        
        # Проверяем основные поля
        for field in required_fields:
            if field not in response_data:
                print(f"❌ Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем структуру contacts
        if not isinstance(response_data['contacts'], list):
            print("❌ Поле 'contacts' должно быть списком")
            return False
        
        # Проверяем каждый контакт
        for i, contact in enumerate(response_data['contacts']):
            if not isinstance(contact, dict):
                print(f"❌ Контакт {i} должен быть объектом")
                return False
            
            # Проверяем обязательные поля контакта
            contact_required = ['name', 'email', 'phone', 'organization', 'confidence']
            for field in contact_required:
                if field not in contact:
                    print(f"❌ Контакт {i}: отсутствует поле {field}")
                    return False
        
        return True
    
    def _make_llm_request_with_retries(self, prompt: str, text: str, max_retries: int = 3) -> dict:
        """🔄 Выполнение запроса к LLM с повторными попытками при ошибках валидации"""
        
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
                print(f"❌ Попытка {attempt + 1}: Ошибка запроса к LLM: {e}")
                
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
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_provider['api_key']}"
        }
        
        # Добавляем специфичные заголовки для OpenRouter
        if self.current_provider == 'openrouter':
            headers["HTTP-Referer"] = "https://github.com/contact-parser"
            headers["X-Title"] = "Contact Parser"
        
        try:
            # Выполняем запрос
            response = requests.post(
                current_provider['base_url'],
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                # Увеличиваем счетчик ошибок провайдера
                current_provider['failure_count'] += 1
                current_provider['last_failure'] = datetime.now().isoformat()
                self.stats['provider_failures'][self.current_provider] += 1
                
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                # Увеличиваем счетчик ошибок провайдера
                current_provider['failure_count'] += 1
                current_provider['last_failure'] = datetime.now().isoformat()
                self.stats['provider_failures'][self.current_provider] += 1
                
                raise Exception("Пустой ответ от LLM")
            
            content = response_data['choices'][0]['message']['content']
            
            # Парсим JSON из ответа
            result = self._parse_llm_response(content)
            result['provider_used'] = current_provider['name']
            
            return result
            
        except Exception as e:
            # Увеличиваем счетчик ошибок провайдера
            current_provider['failure_count'] += 1
            current_provider['last_failure'] = datetime.now().isoformat()
            self.stats['provider_failures'][self.current_provider] += 1
            
            print(f"❌ Ошибка провайдера {current_provider['name']}: {e}")
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
                
                # Небольшая пауза между запросами
                if i < len(chunks) - 1:
                    time.sleep(2)
            
            except Exception as e:
                print(f"   ❌ Ошибка обработки части {i + 1}: {e}")
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


if __name__ == "__main__":
    # Тестирование
    extractor = ContactExtractor(test_mode=True)
    
    test_text = "Тестовое письмо от test@example.com"
    result = extractor.extract_contacts(test_text)
    
    print("\n📊 Результат тестирования:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n📈 Статистика:")
    print(json.dumps(extractor.get_stats(), ensure_ascii=False, indent=2))