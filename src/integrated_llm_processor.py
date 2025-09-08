#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 Интегрированный LLM процессор для анализа писем с вложениями
"""

import json
import re
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from .email_loader import ProcessedEmailLoader
# from attachment_processor import AttachmentProcessor  # АРХИВИРОВАН
from .ocr_processor_adapter import OCRProcessorAdapter
from .llm_extractor import ContactExtractor
from .rate_limit_manager import RateLimitManager
from .config.regions import calculate_contact_priority
from .advanced_deduplication import AdvancedContactDeduplicator

# Загружаем переменные окружения
load_dotenv()


class IntegratedLLMProcessor:
    """🔥 Главный процессор для LLM анализа писем + вложений + КП"""
    
    def __init__(self, test_mode=False):
        self.email_loader = ProcessedEmailLoader()
        self.attachment_processor = OCRProcessorAdapter()
        # Передаем test_mode в ContactExtractor для корректной работы тестового режима
        self.contact_extractor = ContactExtractor(test_mode=test_mode)
        self.rate_limit_manager = RateLimitManager()  # Адаптивное управление rate limit
        self.test_mode = test_mode  # Режим тестирования без LLM для других операций
        self.advanced_deduplicator = AdvancedContactDeduplicator()
        
        # Папки для результатов
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        self.data_dir = project_root / "data"
        self.results_dir = self.data_dir / "llm_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Папка с промптами
        self.prompts_dir = project_root / "prompts"
        
        # Счетчики
        self.stats = {
            'emails_processed': 0,
            'emails_with_contacts': 0,
            'total_contacts_found': 0,
            'emails_with_attachments': 0,
            'attachments_processed': 0,
            'commercial_offers_found': 0,
            'processing_errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        print("🤖 Инициализация интегрированного LLM процессора v2.0")
        print(f"   📊 Результаты будут сохранены в: {self.results_dir}")

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

    def _parse_commercial_analysis(self, response_text: str) -> dict:
        """💼 Парсинг анализа коммерческого предложения"""
        
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            else:
                return {"commercial_offer_found": False, "error": "JSON не найден в ответе"}
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON анализа КП: {e}")
            return {"commercial_offer_found": False, "error": f"Ошибка парсинга: {e}"}


    def process_emails_by_date(self, target_date: str, max_emails: int = None) -> Dict:
        """📅 Обработка писем за конкретную дату
        
        Args:
            target_date (str): Дата в формате YYYY-MM-DD
            max_emails (int, optional): Максимальное количество писем для обработки. 
                                       Если None, обрабатываются все письма.
        """
        
        print(f"\n🎯 ОБРАБОТКА ПИСЕМ ЗА {target_date}")
        print("="*60)
        
        self.stats['start_time'] = datetime.now()
        
        # Загружаем письма
        emails = self.email_loader.load_emails_by_date(target_date)
        if not emails:
            print(f"❌ Нет писем для обработки за {target_date}")
            return self._create_empty_result(target_date)
        
        # Определяем количество писем для обработки
        max_emails_to_process = len(emails) if max_emails is None else min(max_emails, len(emails))
        
        # Выводим информацию о количестве писем
        print(f"📊 Загружено писем: {len(emails)}")
        if max_emails is not None:
            print(f"🎯 К обработке: {max_emails_to_process} писем (лимит: {max_emails})")
        else:
            print(f"🎯 К обработке: все {max_emails_to_process} писем")
        
        # Обрабатываем каждое письмо
        processed_results = []
        
        for email_idx, email in enumerate(emails, 1):
            # Проверяем лимит писем для обработки
            if email_idx > max_emails_to_process:
                print(f"\n🛑 Достигнут лимит обработки: {max_emails_to_process} писем")
                break
                
            try:
                print(f"\n{'─'*40}")
                print(f"📧 Обработка письма {email_idx}/{max_emails_to_process}")
                print(f"   От: {email.get('from', 'N/A')[:50]}...")
                print(f"   Тема: {email.get('subject', 'N/A')[:60]}...")
                
                result = self.process_single_email(email)
                if result:
                    processed_results.append(result)
                    
                    # Обновляем статистику
                    self.stats['emails_processed'] += 1
                    if result.get('contacts'):
                        self.stats['emails_with_contacts'] += 1
                        self.stats['total_contacts_found'] += len(result['contacts'])
                    if result.get('attachments_processed', 0) > 0:
                        self.stats['emails_with_attachments'] += 1
                        self.stats['attachments_processed'] += result['attachments_processed']
                    # Обновляем статистику коммерческих предложений
                    commercial_offers_count = len(result.get('commercial_offers', []))
                    if commercial_offers_count > 0:
                        self.stats['commercial_offers_found'] += commercial_offers_count
                
                # Адаптивная задержка между LLM запросами
                # Не делаем задержку после последнего письма
                if email_idx < max_emails_to_process:
                    # Записываем результат запроса для адаптации задержки
                    request_result = result.get('request_result', 'other_error')
                    self.rate_limit_manager.record_request(request_result)
                    
                    # Применяем адаптивную задержку
                    delay_used = self.rate_limit_manager.wait_if_needed()
                    if delay_used > 0:
                        print(f"   ⏳ Адаптивная задержка {delay_used:.1f} секунд для соблюдения rate limit")
                    
            except Exception as e:
                print(f"❌ Ошибка обработки письма {email_idx}: {e}")
                self.stats['processing_errors'] += 1
                continue
        
        self.stats['end_time'] = datetime.now()
        
        # Создаем итоговый результат
        final_result = self._create_final_result(target_date, processed_results)
        
        # Сохраняем результат
        self._save_results(target_date, final_result)
        
        # Печатаем итоговую статистику
        self._print_final_statistics()
        
        return final_result

    def process_single_email(self, email: Dict) -> Optional[Dict]:
        """📧 Обработка одного письма с вложениями + анализ КП"""
        
        try:
            # 1. Обрабатываем вложения
            attachments_result = self.attachment_processor.process_email_attachments(
                email, self.email_loader
            )
            
            # 2. Объединяем текст письма с содержимым вложений
            combined_text = self.attachment_processor.combine_email_with_attachments(
                email, attachments_result
            )
            
            print(f"   📝 Общий объем текста: {len(combined_text)} символов")
            print(f"   📎 Обработано вложений: {attachments_result['attachments_processed']}")
            
            # 3. Подготавливаем метаданные для LLM
            email_metadata = {
                'from': email.get('from', ''),
                'to': email.get('to', ''),
                'cc': email.get('cc', ''),
                'subject': email.get('subject', ''),
                'date': email.get('date', ''),
                'thread_id': email.get('thread_id', ''),
                'has_attachments': len(email.get('attachments', [])) > 0,
                'attachments_count': len(email.get('attachments', []))
            }
            
            # 4. Извлекаем контакты через LLM
            if self.test_mode:
                print("   🧪 ТЕСТОВЫЙ РЕЖИМ: Пропускаем LLM запросы")
                llm_result = {
                    "contacts": [
                        {
                            "name": "Тестовый Контакт",
                            "phone": "+7-999-123-45-67",
                            "email": "test@example.com",
                            "organization": "Тестовая Компания",
                            "position": "Менеджер",
                            "city": "Москва",
                            "confidence": 0.95
                        }
                    ],
                    "business_context": {
                        "topic": "Тестовое взаимодействие",
                        "product_interest": "Амплификаторы",
                        "communication_stage": "Начальный контакт",
                        "request_type": "Запрос информации",
                        "urgency": "средняя"
                    },
                    "action_items": [
                        "Отправить коммерческое предложение",
                        "Связаться по телефону"
                    ]
                }
            else:
                print("   🤖 Отправка в LLM для единого анализа данных...")
                llm_result = self.contact_extractor.extract_all_data(combined_text, email_metadata)
                
                # Задержка между LLM запросами перенесена в основной цикл
            
            # 5. Получаем коммерческие предложения из единого LLM результата
            if self.test_mode:
                print("   🧪 ТЕСТОВЫЙ РЕЖИМ: Используем тестовые КП")
                commercial_offers = []
            else:
                commercial_offers = llm_result.get('commercial_offers', [])
                print(f"   💼 Получено КП из единого запроса: {len(commercial_offers)}")
            
            # 6. Рассчитываем приоритеты контактов
            if llm_result and isinstance(llm_result, dict):
                for contact in llm_result.get('contacts', []):
                    if contact and isinstance(contact, dict):
                        business_context = llm_result.get('business_context', {}) or {}
                        priority_info = calculate_contact_priority(contact, business_context)
                        contact['priority'] = priority_info
            
            # 7. Формируем итоговый результат
            result = {
                'original_email': {
                    'thread_id': email.get('thread_id'),
                    'from': email.get('from'),
                    'subject': email.get('subject'),
                    'date': email.get('date'),
                    'json_file_path': email.get('json_file_path')
                },
                'attachments_processed': attachments_result['attachments_processed'],
                'attachments_details': attachments_result['attachments_text'],
                'combined_text_length': len(combined_text),
                'llm_analysis': llm_result,
                'commercial_offers': commercial_offers,  # Из единого LLM запроса
                'contacts': llm_result.get('contacts', []),
                'business_context': llm_result.get('business_context', ''),
                'processed_at': datetime.now().isoformat()
            }
            
            # Логируем результат
            contacts_count = len(result['contacts'])
            if contacts_count > 0:
                print(f"   👥 Найдено контактов: {contacts_count}")
                for contact in result['contacts'][:2]:  # Показываем первые 2
                    priority = contact.get('priority', {})
                    conf = contact.get('confidence', 0)
                    print(f"      • {contact.get('name', 'N/A')} (confidence: {conf}, приоритет: {priority.get('level', 'N/A')})")
            else:
                print(f"   👤 Контакты не найдены")
            
            # Логируем коммерческие предложения
            if commercial_offers:
                print(f"   💼 Найдено КП: {len(commercial_offers)}")
                for i, offer in enumerate(commercial_offers[:2]):  # Показываем первые 2
                    supplier = offer.get('supplier', 'N/A')
                    amount = offer.get('total_amount', 'N/A')
                    currency = offer.get('currency', 'RUB')
                    print(f"      • {supplier}: {amount} {currency}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Ошибка обработки письма: {e}")
            return None

    def _normalize_email(self, email: str) -> str:
        """🔧 Нормализация email для сравнения"""
        if not email:
            return ""
        return email.lower().strip()
    
    def _normalize_phone(self, phone: str) -> str:
        """🔧 Нормализация телефона для сравнения"""
        if not phone:
            return ""
        # Убираем все символы кроме цифр и +
        import re
        normalized = re.sub(r'[^\d+]', '', phone)
        # Приводим к единому формату: если начинается с 8, заменяем на +7
        if normalized.startswith('8') and len(normalized) == 11:
            normalized = '+7' + normalized[1:]
        return normalized
    
    def _normalize_name(self, name: str) -> str:
        """🔧 Нормализация имени для сравнения"""
        if not name:
            return ""
        return ' '.join(name.lower().strip().split())
    
    def _merge_contact_group(self, contacts: List[Dict]) -> Dict:
        """🔗 Объединение группы дубликатов контактов"""
        if not contacts:
            return {}
        
        if len(contacts) == 1:
            return contacts[0]
        
        print(f"   🔗 Объединяю {len(contacts)} дубликатов контакта")
        
        # Базовый контакт - берем первый
        merged = contacts[0].copy()
        
        # Собираем все телефоны
        all_phones = set()
        max_confidence = 0
        
        for contact in contacts:
            # Обновляем поля, выбирая наиболее полные значения
            for field in ['name', 'organization', 'position', 'city']:
                current_value = merged.get(field, '')
                new_value = contact.get(field, '')
                
                # Берем более длинное непустое значение
                if len(str(new_value)) > len(str(current_value)):
                    merged[field] = new_value
            
            # Email берем первый непустой
            if not merged.get('email') and contact.get('email'):
                merged['email'] = contact['email']
            
            # Собираем все телефоны
            if contact.get('phone'):
                all_phones.add(contact['phone'])
            
            # Максимальный confidence
            contact_conf = contact.get('confidence', 0)
            if contact_conf > max_confidence:
                max_confidence = contact_conf
        
        # Устанавливаем объединенные данные
        if all_phones:
            merged['phone'] = list(all_phones)[0]  # Основной телефон
            if len(all_phones) > 1:
                merged['other_phones'] = list(all_phones)[1:]  # Дополнительные
        
        merged['confidence'] = max_confidence
        
        return merged
    
    def _deduplicate_contacts(self, contacts: List[Dict]) -> List[Dict]:
        """🔍 Дедупликация контактов по email, телефону и имени"""
        if not contacts:
            return []
        
        print(f"   🔍 Начинаю дедупликацию {len(contacts)} контактов")
        
        # Группируем контакты по ключам
        groups_by_email = {}
        groups_by_phone = {}
        groups_by_name_org = {}
        processed_contacts = set()
        
        # Группировка по email (приоритет 1)
        for i, contact in enumerate(contacts):
            email = contact.get('email')
            if email:
                norm_email = self._normalize_email(email)
                if norm_email:
                    if norm_email not in groups_by_email:
                        groups_by_email[norm_email] = []
                    groups_by_email[norm_email].append((i, contact))
                    processed_contacts.add(i)
        
        # Группировка по телефону (приоритет 2)
        for i, contact in enumerate(contacts):
            if i in processed_contacts:
                continue
            
            phone = contact.get('phone')
            if phone:
                norm_phone = self._normalize_phone(phone)
                if norm_phone:
                    if norm_phone not in groups_by_phone:
                        groups_by_phone[norm_phone] = []
                    groups_by_phone[norm_phone].append((i, contact))
                    processed_contacts.add(i)
        
        # Группировка по имени + организации (приоритет 3)
        for i, contact in enumerate(contacts):
            if i in processed_contacts:
                continue
            
            name = contact.get('name')
            org = contact.get('organization')
            if name and org:
                norm_key = f"{self._normalize_name(name)}|{self._normalize_name(org)}"
                if norm_key not in groups_by_name_org:
                    groups_by_name_org[norm_key] = []
                groups_by_name_org[norm_key].append((i, contact))
                processed_contacts.add(i)
        
        # Объединяем группы и создаем уникальные контакты
        unique_contacts = []
        
        # Обрабатываем группы по email
        for email, group in groups_by_email.items():
            contacts_in_group = [contact for _, contact in group]
            merged = self._merge_contact_group(contacts_in_group)
            unique_contacts.append(merged)
        
        # Обрабатываем группы по телефону
        for phone, group in groups_by_phone.items():
            contacts_in_group = [contact for _, contact in group]
            merged = self._merge_contact_group(contacts_in_group)
            unique_contacts.append(merged)
        
        # Обрабатываем группы по имени+организации
        for key, group in groups_by_name_org.items():
            contacts_in_group = [contact for _, contact in group]
            merged = self._merge_contact_group(contacts_in_group)
            unique_contacts.append(merged)
        
        # Добавляем необработанные контакты
        for i, contact in enumerate(contacts):
            if i not in processed_contacts:
                unique_contacts.append(contact)
        
        duplicates_found = len(contacts) - len(unique_contacts)
        if duplicates_found > 0:
            print(f"   ✅ Найдено и объединено {duplicates_found} дубликатов")
            print(f"   📊 Итого уникальных контактов: {len(unique_contacts)}")
        else:
            print(f"   ℹ️ Дубликаты не найдены")
        
        return unique_contacts
    
    def _create_final_result(self, target_date: str, processed_results: List[Dict]) -> Dict:
        """📊 Создание итогового результата обработки"""
        
        # Собираем все контакты
        all_contacts = []
        all_business_contexts = []
        all_action_items = []
        all_commercial_offers = []
        
        for result in processed_results:
            all_contacts.extend(result.get('contacts', []))
            if result.get('business_context'):
                all_business_contexts.append(result['business_context'])
            all_action_items.extend(result.get('action_items', []))
            
            # НОВОЕ: собираем все КП
            commercial_analysis = result.get('commercial_analysis', {})
            if commercial_analysis.get('commercial_offer_found'):
                all_commercial_offers.append({
                    'email_thread_id': result.get('original_email', {}).get('thread_id'),
                    'email_from': result.get('original_email', {}).get('from'),
                    'commercial_offer': commercial_analysis
                })
        
        # Дедупликация контактов - используем продвинутый алгоритм для больших писем
        total_text_size = sum(result.get('combined_text_length', 0) for result in processed_results)
        if total_text_size > 50000:  # Для больших писем используем продвинутую дедупликацию
            print(f"   🔍 Большой объем текста ({total_text_size} символов) - используем продвинутую дедупликацию")
            unique_contacts = self.advanced_deduplicator.deduplicate_contacts(all_contacts)
        else:
            unique_contacts = self._deduplicate_contacts(all_contacts)
        
        # Группируем контакты по приоритету
        contacts_by_priority = {
            'high': [c for c in unique_contacts if c.get('priority', {}).get('score', 0) >= 0.8],
            'medium': [c for c in unique_contacts if 0.6 <= c.get('priority', {}).get('score', 0) < 0.8],
            'low': [c for c in unique_contacts if c.get('priority', {}).get('score', 0) < 0.6]
        }
        
        # Преобразуем время в строку для корректной сериализации в JSON
        processing_time = None
        if self.stats['start_time'] and self.stats['end_time']:
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
        # Преобразуем datetime объекты в строки ISO для JSON
        processed_at = datetime.now().isoformat()
        
        return {
            'processing_date': target_date,
            'processed_at': processed_at,
            'processing_time_seconds': processing_time,
            'statistics': {
                'emails_processed': self.stats['emails_processed'],
                'emails_with_contacts': self.stats['emails_with_contacts'],
                'total_contacts_found': self.stats['total_contacts_found'],
                'emails_with_attachments': self.stats['emails_with_attachments'],
                'attachments_processed': self.stats['attachments_processed'],
                'commercial_offers_found': self.stats['commercial_offers_found'],
                'processing_errors': self.stats['processing_errors']
            },
            'emails_results': processed_results,
            'summary': {
                'total_contacts': len(unique_contacts),
                'contacts_by_priority': {
                    'high': len(contacts_by_priority['high']),
                    'medium': len(contacts_by_priority['medium']),
                    'low': len(contacts_by_priority['low'])
                },
                'total_action_items': len(all_action_items),
                'total_business_contexts': len(all_business_contexts),
                'total_commercial_offers': len(all_commercial_offers)  # НОВОЕ
            },
            'all_contacts': unique_contacts,
            'all_action_items': all_action_items,
            'all_commercial_offers': all_commercial_offers,  # НОВОЕ
            'high_priority_contacts': contacts_by_priority['high']
        }

    def _create_empty_result(self, target_date: str) -> Dict:
        """📭 Пустой результат когда нет писем"""
        
        return {
            'processing_date': target_date,
            'processed_at': datetime.now().isoformat(),
            'processing_time_seconds': 0,
            'statistics': {'emails_processed': 0, 'errors': 'No emails found'},
            'emails_results': [],
            'summary': {'total_contacts': 0, 'total_action_items': 0, 'total_commercial_offers': 0},
            'all_contacts': [],
            'all_action_items': [],
            'all_commercial_offers': []
        }

    def _save_results(self, target_date: str, results: Dict):
        """💾 Сохранение результатов обработки"""
        
        # Основной файл с результатами
        results_filename = f"llm_analysis_{target_date.replace('-', '')}.json"
        results_path = self.results_dir / results_filename
        
        try:
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"💾 Результаты сохранены: {results_path}")
            
            # Сохраняем краткую сводку отдельно
            summary_data = {
                'date': target_date,
                'processed_at': results['processed_at'],
                'statistics': results['statistics'],
                'summary': results['summary'],
                'high_priority_contacts_preview': [
                    {
                        'name': c.get('name'),
                        'organization': c.get('organization'), 
                        'city': c.get('city'),
                        'confidence': c.get('confidence'),
                        'priority_score': c.get('priority', {}).get('score')
                    }
                    for c in results['high_priority_contacts'][:5]  # Топ-5
                ],
                'commercial_offers_preview': [  # НОВОЕ: превью КП
                    {
                        'from': co.get('email_from'),
                        'total_cost': co.get('commercial_offer', {}).get('total_cost'),
                        'supplier': co.get('commercial_offer', {}).get('supplier_info', {}).get('company'),
                        'delivery_terms': co.get('commercial_offer', {}).get('delivery_terms')
                    }
                    for co in results.get('all_commercial_offers', [])[:3]  # Топ-3
                ]
            }
            
            summary_path = self.results_dir / f"summary_{target_date.replace('-', '')}.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            print(f"📊 Краткая сводка: {summary_path}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения результатов: {e}")

    def _print_final_statistics(self):
        """📊 Печать итоговой статистики"""
        
        print(f"\n{'='*60}")
        print(f"📊 ИТОГОВАЯ СТАТИСТИКА ОБРАБОТКИ")
        print(f"{'='*60}")
        
        print(f"📧 Писем обработано: {self.stats['emails_processed']}")
        print(f"👥 Писем с найденными контактами: {self.stats['emails_with_contacts']}")
        print(f"🎯 Всего контактов найдено: {self.stats['total_contacts_found']}")
        print(f"📎 Писем с вложениями: {self.stats['emails_with_attachments']}")
        print(f"📎 Вложений обработано: {self.stats['attachments_processed']}")
        print(f"💼 Коммерческих предложений найдено: {self.stats['commercial_offers_found']}")  # НОВОЕ
        print(f"❌ Ошибок обработки: {self.stats['processing_errors']}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            print(f"⏱️ Время обработки: {processing_time:.1f} секунд")
            
            if self.stats['emails_processed'] > 0:
                avg_time = processing_time / self.stats['emails_processed']
                print(f"⚡ Среднее время на письмо: {avg_time:.1f} секунд")
        
        print(f"{'='*60}")

def main():
    """🚀 Главная функция тестирования интегрированной системы"""
    
    print("🤖 ТЕСТИРОВАНИЕ ИНТЕГРИРОВАННОГО LLM ПРОЦЕССОРА")
    print("="*70)
    
    # Создаем процессор в обычном режиме (с LLM запросами)
    processor = IntegratedLLMProcessor(test_mode=False)
    
    # Получаем доступные даты
    available_dates = processor.email_loader.get_available_date_folders()
    
    if not available_dates:
        print("❌ Нет обработанных писем для тестирования")
        print("   Сначала запустите advanced_email_fetcher.py")
        return
    
    print(f"📅 Доступные даты: {available_dates}")
    
    # Выбираем дату с наибольшим количеством писем для тестирования
    target_date = "2025-07-29"  # Дата с 30 письмами
    print(f"🎯 Тестируем на дате: {target_date}")
    
    # Запускаем обработку
    results = processor.process_emails_by_date(target_date)
    
    # Показываем краткие результаты
    if results and results['summary']['total_contacts'] > 0:
        print(f"\n🏆 ТОП НАЙДЕННЫЕ КОНТАКТЫ:")
        for contact_idx, contact in enumerate(results.get('high_priority_contacts', [])[:3], 1):
            priority = contact.get('priority', {})
            print(f"   {contact_idx}. {contact.get('name', 'N/A')} ({contact.get('organization', 'N/A')})")
            print(f"      Город: {contact.get('city', 'N/A')}, Confidence: {contact.get('confidence', 0)}")
            print(f"      Приоритет: {priority.get('level', 'N/A')} (score: {priority.get('score', 0)})")
    
    print(f"\n🎉 Тестирование завершено! Результаты готовы для Sprint 3 (Google Sheets)!")


if __name__ == '__main__':
    main()
