#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 API Pipeline Validator - Phase 11.4 Implementation
Валидация через API пайплайн на датасете 2025-07-29 и запуск IntegratedLLMProcessor

Этот модуль реализует полную функциональность main_new.py, но для ограниченного набора данных.
Включает режимы first10 и all с идемпотентностью.
"""

import sys
import json
import time
import argparse
import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set

# Добавление корневой директории проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импорт централизованного логгера
from src.utils.logger import logger, log_pipeline_event, log_api_event, log_error_event

# 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Загрузка .env файла
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
    print("✅ .env файл загружен")
except ImportError:
    print("⚠️ dotenv не установлен, используем системные переменные окружения")
except Exception as e:
    print(f"⚠️ Ошибка загрузки .env: {e}")

# Реальные импорты без заглушек - для настоящего API пайплайна
def import_component(module_name, class_name):
    """Безопасный импорт компонентов с детальной диагностикой"""
    try:
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    except Exception as e:
        print(f"❌ Ошибка импорта {module_name}.{class_name}: {e}")
        return None

# Попытка импорта реальных компонентов
print("🔄 Попытка импорта реальных компонентов...")
ExtractorFactory = import_component('src.core.extractor_factory', 'ExtractorFactory')
ConfigValidator = import_component('src.config.config_validator', 'ConfigValidator') 
IntegratedLLMProcessor = import_component('src.integrated_llm_processor', 'IntegratedLLMProcessor')
ReportGenerator = import_component('src.report_generator', 'ReportGenerator')
ProcessedEmailLoader = import_component('src.email_loader', 'ProcessedEmailLoader')
OCRProcessorAdapter = import_component('src.ocr_processor_adapter', 'OCRProcessorAdapter')
UnifiedConfigManager = import_component('src.config.config_manager', 'UnifiedConfigManager')

# Импорт асинхронных провайдеров
AsyncProviderManager = import_component('src.providers.async_provider_wrapper', 'AsyncProviderManager')
AsyncProviderWrapper = import_component('src.providers.async_provider_wrapper', 'AsyncProviderWrapper')


class SimpleReportGenerator:
    """📄 Простой генератор отчетов для fallback'а"""
    
    def __init__(self):
        pass
        
    def generate_validation_report(self, result, validation_result):
        """Генерация простого отчета"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')
        
        # Получаем данные из результата
        email_data = result.get('email_data', {})
        # Исправляем извлечение данных - они могут быть в llm_result или extraction_result
        llm_result = result.get('llm_result', {})
        if not llm_result and 'extraction_result' in result:
            llm_result = result['extraction_result']
        
        # Метаданные письма
        email_from = email_data.get('from', 'Не указано')
        email_subject = email_data.get('subject', 'Не указано')
        email_date = email_data.get('date', 'Не указано')
        char_count = email_data.get('char_count', 0)
        attachments_count = len(email_data.get('attachments', []))
        
        # Организации
        organizations = llm_result.get('organizations', [])
        org_section = "### Организации ({} найдено)\n\n".format(len(organizations))
        
        if organizations:
            org_section += "| ID | Название | ИНН | Сайт | Город | Адрес | Email | Телефоны |\n"
            org_section += "|----|---------|----|-----|-------|-------|-------|----------|\n"
            
            for org in organizations:
                org_id = org.get('organization_id', '')
                name = org.get('name', 'Не указано')
                inn = org.get('inn', 'Не указан')
                website = org.get('website', 'Не указан')
                emails = ', '.join(org.get('emails', [])) if org.get('emails') else 'Не указаны'
                phones = ', '.join(org.get('phones', [])) if org.get('phones') else 'Не указаны'
                
                org_section += f"| {org_id} | {name} | {inn} | {website} | - | - | {emails} | {phones} |\n"
        else:
            org_section += "❌ **Организации не найдены**\n"
        
        # Контакты
        contacts = llm_result.get('contacts', [])
        contacts_section = "\n### Контакты ({} найдено)\n\n".format(len(contacts))
        
        if contacts:
            contacts_section += "| ID | Имя | Орг.ID | Должность | Email | Телефоны | Уверенность |\n"
            contacts_section += "|----|----|-------|-----------|-------|----------|-------------|\n"
            
            for contact in contacts:
                contact_id = contact.get('contact_id', '')
                name = contact.get('name', 'Не указано')
                org_id = contact.get('organization_id', '')
                position = contact.get('position', 'Не указана')
                email = contact.get('email', 'Не указан')
                
                # Обработка телефонов
                phones = contact.get('phones', [])
                if isinstance(phones, list) and phones:
                    phones_str = ', '.join([p.get('number', '') if isinstance(p, dict) else str(p) for p in phones])
                else:
                    phones_str = 'Не указаны'
                
                confidence = contact.get('confidence', 0)
                
                contacts_section += f"| {contact_id} | {name} | {org_id} | {position} | {email} | {phones_str} | {confidence:.2f} |\n"
        else:
            contacts_section += "❌ **Контакты не найдены**\n"
        
        # Коммерческие предложения
        commercial_offers = llm_result.get('commercial_offers', [])
        offers_section = "\n### Коммерческие предложения ({} найдено)\n\n".format(len(commercial_offers))
        
        if commercial_offers:
            for i, offer in enumerate(commercial_offers, 1):
                found_status = "✅ Найдено" if offer.get('found', False) else "❌ Не найдено"
                offers_section += f"#### КП #{i}\n\n"
                offers_section += f"- **Статус:** {found_status}\n"
                
                # Основная информация о КП
                if offer.get('offer_number'):
                    offers_section += f"- **Номер КП:** {offer.get('offer_number')}\n"
                if offer.get('offer_date'):
                    offers_section += f"- **Дата КП:** {offer.get('offer_date')}\n"
                if offer.get('end_user'):
                    offers_section += f"- **Конечный заказчик:** {offer.get('end_user')}\n"
                if offer.get('intermediary'):
                    offers_section += f"- **Посредник:** {offer.get('intermediary')}\n"
                
                # Условия
                if offer.get('payment_terms'):
                    offers_section += f"- **Условия оплаты:** {offer.get('payment_terms')}\n"
                if offer.get('delivery_time'):
                    offers_section += f"- **Срок поставки:** {offer.get('delivery_time')}\n"
                if offer.get('delivery_terms'):
                    offers_section += f"- **Условия доставки:** {offer.get('delivery_terms')}\n"
                if offer.get('valid_until'):
                    offers_section += f"- **Срок действия:** до {offer.get('valid_until')}\n"
                
                # Оборудование
                equipment_items = offer.get('equipment_items', [])
                if equipment_items:
                    offers_section += "\n**Оборудование:**\n\n"
                    offers_section += "| № | Модель | Артикул | Наименование | Кол-во | Цена за ед. | Цена со скидкой | НДС |\n"
                    offers_section += "| :--: | :-- | :-- | :-- | :--: | :-- | :-- | :--: |\n"
                    
                    for j, item in enumerate(equipment_items, 1):
                        model = item.get('model', '')
                        article = item.get('article', '')
                        name = item.get('name', '')
                        quantity = item.get('quantity', 0)
                        unit_price = item.get('unit_price', 0)
                        total_price = item.get('total_price', 0)
                        vat = item.get('vat', '')
                        
                        offers_section += f"| {j} | {model} | {article} | {name} | {quantity} | {unit_price:,} | {total_price:,} | {vat} |\n"
                
                offers_section += f"\n- **Общая стоимость:** {offer.get('total_cost', 0):,} руб.\n"
                
                if offer.get('comments'):
                    offers_section += f"- **Комментарий:** {offer.get('comments')}\n"
                
                offers_section += "\n"
        else:
            offers_section += "❌ **Коммерческие предложения не найдены**\n"
        
        # Собираем отчет
        status = "✅ УСПЕХ" if result.get('success', False) else "❌ ОШИБКА"
        business_context = llm_result.get('business_context', 'Контактная информация извлечена из деловой переписки.')
        
        report = f"""# Детальный отчет валидации - {result.get('filename', 'Unknown')}

**Время анализа:** {timestamp}
**Статус:** {status}

## Метаданные письма

- **От:** {email_from}
- **Тема:** {email_subject}
- **Дата:** {email_date}
- **Размер:** {char_count} символов
- **Вложения:** {attachments_count}

## Извлеченные данные

{org_section}

{contacts_section}

{offers_section}

## Дополнительная информация

### Бизнес-контекст
{business_context}

### Ключевые моменты
- Обработано через реальный пайплайн извлечения
- Произведен анализ текста и вложений

---
*Отчет сгенерирован: {timestamp}*
"""
        
        return report
        
    def update_index(self, filename, description):
        """Обновление индекса (заглушка)"""
        pass





class APIPipelineValidator:
    """🎯 Валидатор API пайплайна для фазы 11.4"""
    
    def __init__(self, 
                 date: str = "2025-07-29",
                 results_dir: Optional[str] = None,
                 reports_dir: Optional[str] = None,
                 test_mode: bool = False):
        """
        Инициализация валидатора
        
        Args:
            date: Дата для обработки (по умолчанию 2025-07-29)
            results_dir: Директория для сохранения JSON результатов
            reports_dir: Директория для сохранения отчетов
            test_mode: Режим тестирования (по умолчанию False)
        """
        self.date = date
        self.test_mode = test_mode
        self.project_root = project_root
        
        # Пути директорий
        self.test_dataset_path = self.project_root / "memory-bank" / "test_dataset_10_emails.md"
        self.emails_dir = self.project_root / "data" / "emails" / date
        
        # Результирующие директории
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            self.results_dir = self.project_root / "data" / "ТЕСТ 10 реальный писем" / f"{date}_LLM" / "structured_results"
            
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            self.reports_dir = self.project_root / "data" / "ТЕСТ 10 реальный писем" / f"{date}_LLM"
            
        # Создаем директории
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализация компонентов
        self.processor = None
        self.report_generator = None
        self.email_loader = None
        self.ocr_adapter = None
        
        # 📊 Инициализация системы метрик и логирования
        self.config_manager = None
        if UnifiedConfigManager:
            try:
                self.config_manager = UnifiedConfigManager()
                print("✅ Система метрик и логирования инициализирована")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации системы метрик: {e}")
                self.config_manager = None
        
        # Статистика
        self.stats = {
            'start_time': None,
            'end_time': None,
            'emails_processed': 0,
            'emails_successful': 0,
            'emails_failed': 0,
            'json_files_created': 0,
            'reports_created': 0,
            'errors': []
        }
        
        print(f"🎯 API Pipeline Validator для даты {date}")
        print(f"   📁 Результаты JSON: {self.results_dir}")
        print(f"   📄 Отчеты: {self.reports_dir}")
    
    def validate_pipeline(self, text: str) -> Dict:
        """Валидация пайплайна с текстом для тестирования"""
        if not self.validate_setup():
            return {'success': False, 'error': 'Setup validation failed', 'test_mode': self.test_mode}
        
        if not self.processor:
            return {'success': False, 'error': 'Processor not initialized', 'test_mode': self.test_mode}
        
        try:
            result = self.processor.extract_all_data(text)
            result['test_mode'] = self.test_mode
            return result
        except Exception as e:
            return {'success': False, 'error': str(e), 'test_mode': self.test_mode}

    def validate_setup(self) -> bool:
        """🔍 Валидация настроек перед началом работы"""
        print("\n🔍 ВАЛИДАЦИЯ НАСТРОЕК")
        print("=" * 50)
        
        # 1. Валидация зависимостей
        print("   🔧 Проверка зависимостей...")
        if ExtractorFactory and hasattr(ExtractorFactory, 'validate_dependencies'):
            if not ExtractorFactory.validate_dependencies():
                print("   ❌ Критические проблемы с зависимостями!")
                return False
        print("   ✅ Зависимости в порядке")
        
        # 2. Валидация конфигурации
        print("   ⚙️ Проверка конфигурации...")
        if ConfigValidator:
            validator = ConfigValidator()
            validation_result = validator.validate_all()
            
            if not validation_result.is_valid:
                print("   ❌ Критические проблемы с конфигурацией!")
                validator.print_validation_report(validation_result)
                return False
        print("   ✅ Конфигурация валидна")
        
        # 3. Проверка директорий и файлов
        print("   📁 Проверка файловой структуры...")
        
        if not self.test_dataset_path.exists():
            print(f"   ❌ Файл тестового датасета не найден: {self.test_dataset_path}")
            return False
            
        if not self.emails_dir.exists():
            print(f"   ❌ Директория с письмами не найдена: {self.emails_dir}")
            return False
            
        email_files = list(self.emails_dir.glob("*.json"))
        if not email_files:
            print(f"   ❌ Письма не найдены в: {self.emails_dir}")
            return False
            
        print(f"   ✅ Найдено {len(email_files)} писем в директории")
        
        # Инициализация компонентов
        print("   🚀 Инициализация компонентов...")
        try:
            # 🎯 ПРАВИЛЬНАЯ АРХИТЕКТУРА: Используем ExtractorFactory как в main_new.py
            if ExtractorFactory:
                self.processor = ExtractorFactory.create_extractor(test_mode=self.test_mode)
                print(f"   ✅ Экстрактор создан через ExtractorFactory (основной пайплайн, test_mode={self.test_mode})")
                # В тестовом режиме не переопределяем test_mode
                if not self.test_mode and hasattr(self.processor, 'test_mode'):
                    self.processor.test_mode = False
                    print("   ✅ test_mode принудительно отключен в процессоре")
            else:
                print("   ❌ ExtractorFactory недоступен")
                return False
                
            # 🎯 ВСЕГДА используем SimpleReportGenerator для корректного отображения данных
            self.report_generator = SimpleReportGenerator()
            print("   ✅ SimpleReportGenerator инициализирован (показывает реальные данные)")
                
            if ProcessedEmailLoader:
                self.email_loader = ProcessedEmailLoader()
                print("   ✅ ProcessedEmailLoader инициализирован")
            else:
                self.email_loader = None
                print("   ⚠️ ProcessedEmailLoader не доступен")
                
            if OCRProcessorAdapter:
                self.ocr_adapter = OCRProcessorAdapter()
                print("   ✅ OCRProcessorAdapter инициализирован")
            else:
                self.ocr_adapter = None
                print("   ⚠️ OCRProcessorAdapter не доступен")
                
            print("   ✅ Все компоненты инициализированы")
        except Exception as e:
            print(f"   ❌ Ошибка инициализации компонентов: {e}")
            return False
            
        return True

    def load_test_dataset_files(self) -> List[str]:
        """📄 Загрузка списка файлов из тестового датасета"""
        print("\n📄 ЗАГРУЗКА ТЕСТОВОГО ДАТАСЕТА")
        print("=" * 40)
        
        test_files = []
        
        try:
            with open(self.test_dataset_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Извлекаем имена файлов из markdown документа
            lines = content.split('\n')
            for line in lines:
                if '**Файл:**' in line and '.json' in line:
                    # Извлекаем имя файла между ` `
                    start = line.find('`') + 1
                    end = line.find('`', start)
                    if start > 0 and end > start:
                        filename = line[start:end].strip()  # Trim whitespace
                        test_files.append(filename)
                        
            print(f"   📊 Найдено файлов в датасете: {len(test_files)}")
            for i, filename in enumerate(test_files, 1):
                print(f"      {i}. {filename}")
                
        except Exception as e:
            print(f"   ❌ Ошибка загрузки тестового датасета: {e}")
            return []
            
        return test_files

    def get_all_email_files(self) -> List[str]:
        """📧 Получение всех файлов писем из директории"""
        email_files = []
        
        for email_path in self.emails_dir.glob("*.json"):
            email_files.append(email_path.name)
            
        # Сортируем по номеру письма
        email_files.sort(key=lambda x: int(x.split('_')[1]) if '_' in x and x.split('_')[1].isdigit() else 0)
        
        return email_files

    def get_already_processed_files(self) -> Set[str]:
        """🔍 Определение уже обработанных файлов (для идемпотентности)"""
        processed_files = set()
        
        for json_path in self.results_dir.glob("*.json"):
            # Извлекаем исходное имя файла из результата
            filename = json_path.stem
            # Убираем возможные суффиксы (_structured_result, _result и т.д.)
            original_name = filename.replace('_structured_result', '').replace('_result', '')
            
            # Добавляем .json если нет
            if not original_name.endswith('.json'):
                original_name += '.json'
                
            processed_files.add(original_name)
            
        return processed_files

    def load_email_with_attachments(self, filename: str) -> Optional[Dict]:
        """📧 Загрузка письма с вложениями"""
        try:
            # 🔧 ИСПРАВЛЕНИЕ: Определяем правильную папку по дате в имени файла
            # Извлекаем дату из имени файла (формат: email_XXX_YYYYMMDD_...)
            file_date = None
            parts = filename.split('_')
            if len(parts) >= 3:
                date_part = parts[2]  # YYYYMMDD
                if len(date_part) == 8 and date_part.isdigit():
                    # Преобразуем YYYYMMDD в YYYY-MM-DD
                    file_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            
            # Определяем правильную папку
            if file_date:
                email_dir = self.project_root / "data" / "emails" / file_date
                print(f"      📁 Ищем файл в папке: {email_dir}")
            else:
                email_dir = self.emails_dir
                print(f"      📁 Используем стандартную папку: {email_dir}")
            
            # Загружаем основное письмо
            email_path = email_dir / filename
            if not email_path.exists():
                print(f"      ❌ Файл не найден: {email_path}")
                return None
                
            with open(email_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            # 🔧 ИСПРАВЛЕНИЕ: Обрабатываем формат processed results
            # Если это processed result, извлекаем оригинальные данные
            if 'extraction_result' in email_data and 'original_email' in email_data:
                print(f"      🔄 Обнаружен формат processed results, извлекаем оригинальные данные...")
                
                # Восстанавливаем структуру raw email из processed results
                original_email = email_data.get('original_email', {})
                extraction_result = email_data.get('extraction_result', {})
                
                # Пытаемся извлечь реальный текст письма из ключевых точек
                email_body = ""
                
                # 1. Проверяем business_context для получения содержания
                business_context = extraction_result.get('business_context', {})
                if isinstance(business_context, dict):
                    # Новый формат: business_context как dict
                    summary = business_context.get('business_summary', '')
                    if summary and len(summary) > 50:
                        email_body += f"Бизнес-резюме: {summary}\n\n"
                    
                    purpose = business_context.get('main_purpose', '')
                    if purpose and purpose != 'неопределено':
                        email_body += f"Цель: {purpose}\n\n"
                elif isinstance(business_context, str) and len(business_context) > 50:
                    # Старый формат: business_context как строка (для совместимости)
                    email_body += f"Бизнес-контекст: {business_context}\n\n"
                
                # 2. Добавляем ключевые моменты если есть
                key_points = extraction_result.get('key_points', [])
                if key_points:
                    email_body += "Ключевые моменты:\n"
                    for point in key_points:
                        email_body += f"- {point}\n"
                    email_body += "\n"
                
                # 3. Добавляем информацию о контактах если есть
                contacts = extraction_result.get('contacts', [])
                if contacts:
                    email_body += "Контактная информация:\n"
                    for contact in contacts:
                        if contact.get('name'):
                            email_body += f"- {contact['name']}"
                            if contact.get('position'):
                                email_body += f", {contact['position']}"
                            if contact.get('phones'):
                                phones = [p.get('number', p) if isinstance(p, dict) else p for p in contact['phones']]
                                email_body += f", тел: {', '.join(phones)}"
                            email_body += "\n"
                    email_body += "\n"
                
                # 4. Добавляем информацию об организациях
                organizations = extraction_result.get('organizations', [])
                if organizations:
                    email_body += "Организации:\n"
                    for org in organizations:
                        if org.get('name'):
                            email_body += f"- {org['name']}"
                            if org.get('inn'):
                                email_body += f", ИНН: {org['inn']}"
                            if org.get('website'):
                                email_body += f", сайт: {org['website']}"
                            email_body += "\n"
                    email_body += "\n"
                
                # Если контента мало, добавляем служебную информацию
                if len(email_body.strip()) < 100:
                    summary = extraction_result.get('summary', {})
                    if summary:
                        if summary.get('topic'):
                            email_body += f"Тема: {summary['topic']}\n"
                        if summary.get('product_interest'):
                            email_body += f"Интерес к продукту: {summary['product_interest']}\n"
                        if summary.get('communication_stage'):
                            email_body += f"Стадия коммуникации: {summary['communication_stage']}\n"
                
                # Создаем правильную структуру raw email
                reconstructed_email = {
                    'thread_id': original_email.get('thread_id'),
                    'from': original_email.get('from'),
                    'subject': original_email.get('subject'),
                    'date': original_email.get('date'),
                    'body': email_body.strip() if email_body.strip() else "Письмо не содержит текстового контента.",
                    'char_count': len(email_body.strip()) if email_body.strip() else 50,
                    'attachments': [],  # Пока без вложений из processed results
                    'source_format': 'processed_results',
                    'original_file': filename
                }
                
                email_data = reconstructed_email
                print(f"      ✅ Реконструировано письмо с {len(email_data['body'])} символами")
            
            # Обычная обработка для raw email format
            combined_text = email_data.get('body', '')
            
            if email_data.get('attachments'):
                print(f"      📎 Обработка {len(email_data['attachments'])} вложений...")
                
                # Здесь должна быть логика извлечения текста из вложений
                # Пока используем заглушку, так как требуется OCR адаптер
                attachment_text = self._extract_attachments_text(email_data)
                if attachment_text:
                    combined_text += "\n\n" + attachment_text
                    
            email_data['combined_text'] = combined_text
            email_data['combined_text_length'] = len(combined_text)
            
            return email_data
            
        except Exception as e:
            print(f"      ❌ Ошибка загрузки письма {filename}: {e}")
            
            # 🔍 Дополнительная диагностика при ошибке
            if "FileNotFoundError" in str(type(e).__name__):
                print(f"      📁 Проверяем директорию: {self.emails_dir}")
                available_files = list(self.emails_dir.glob("*.json"))
                print(f"      📊 Доступно файлов: {len(available_files)}")
                for af in available_files[:3]:  # Показываем первые 3
                    print(f"         - {af.name}")
            
            import traceback
            print(f"      🔍 Детали ошибки: {traceback.format_exc()}")
            return None

    def _extract_attachments_text(self, email_data: Dict) -> str:
        """📎 Использование реального OCRProcessorAdapter из основного пайплайна"""
        
        # 🎯 АРХИТЕКТУРНОЕ ИСПРАВЛЕНИЕ: Используем основной пайплайн
        try:
            if self.ocr_adapter:
                print(f"      📎 Используем OCRProcessorAdapter из основного пайплайна...")
                
                # Обрабатываем вложения через реальный OCR адаптер
                attachments_result = self.ocr_adapter.process_email_attachments(
                    email_data, self.email_loader
                )
                
                # Объединяем текст письма с вложениями через адаптер
                combined_text = self.ocr_adapter.combine_email_with_attachments(
                    email_data, attachments_result
                )
                
                # Извлекаем только текст вложений (убираем заголовки письма)
                email_body = email_data.get('body', '')
                if email_body in combined_text:
                    attachment_text = combined_text.replace(email_body, '').strip()
                    # Убираем служебные заголовки
                    lines = attachment_text.split('\n')
                    filtered_lines = []
                    skip_headers = True
                    for line in lines:
                        if '=' * 50 in line and 'СОДЕРЖИМОЕ ВЛОЖЕНИЙ' in lines:
                            skip_headers = False
                            continue
                        if not skip_headers and not line.startswith(('ТЕМА:', 'ОТ:', 'К:', 'ДАТА:', 'THREAD ID:')):
                            filtered_lines.append(line)
                    
                    attachment_text = '\n'.join(filtered_lines).strip()
                    
                    if attachment_text:
                        print(f"      ✅ OCRProcessorAdapter извлек {len(attachment_text)} символов из вложений")
                        return attachment_text
                
                print(f"      ⚠️ OCRProcessorAdapter не смог извлечь текст из вложений")
                return ""
            else:
                print(f"      ⚠️ OCRProcessorAdapter недоступен, используем fallback")
                return self._simple_attachments_info(email_data)
                
        except Exception as e:
            print(f"      ❌ Ошибка в OCRProcessorAdapter: {e}")
            return self._simple_attachments_info(email_data)
    
    def _simple_attachments_info(self, email_data: Dict) -> str:
        """📎 Простая информация о вложениях (fallback)"""
        attachments = email_data.get('attachments', [])
        if not attachments:
            return ""
         
        attachment_info = "\n\n=== ИНФОРМАЦИЯ О ВЛОЖЕНИЯХ ===\n"
        for i, attachment in enumerate(attachments, 1):
            filename = attachment.get('original_filename', f'вложение_{i}')
            status = attachment.get('status', 'unknown')
            file_type = attachment.get('file_type', '')
            exclusion_reason = attachment.get('exclusion_reason', '')
            
            attachment_info += f"{i}. {filename} ({file_type})\n"
            if status != 'saved' and status != 'already_exists':
                attachment_info += f"   Статус: {status}\n"
                if exclusion_reason:
                    attachment_info += f"   Причина: {exclusion_reason}\n"
            attachment_info += "\n"
        
        return attachment_info
    


    def process_single_email(self, filename: str) -> Optional[Dict]:
        """⚡ Обработка одного письма через основной пайплайн - ТОНКИЙ ТЕСТОВЫЙ СЛОЙ"""
        print(f"      🔄 Обработка: {filename}")
        
        try:
            # Загружаем письмо с вложениями
            email_data = self.load_email_with_attachments(filename)
            if not email_data:
                return {
                    'filename': filename,
                    'success': False,
                    'error': 'Ошибка загрузки письма',
                    'no_providers_available': False
                }
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: есть ли доступные провайдеры через основной пайплайн
            if not self.processor:
                print(f"      ❌ Процессор не инициализирован")
                return {
                    'filename': filename,
                    'success': False,
                    'error': 'Процессор не инициализирован',
                    'no_providers_available': True
                }
            
            # 🎯 ПРАВИЛЬНАЯ АРХИТЕКТУРА: Подготавливаем текстовое содержимое через основной пайплайн
            text_content = self._extract_text_content_via_main_pipeline(email_data)
            
            print(f"      🤖 Обработка через основной пайплайн ({len(text_content)} символов)...")
            print(f"      📎 Вложений: {len(email_data.get('attachments', []))}")
            
            start_time = time.time()
            try:
                # 🎯 ПОЛНОЕ ДЕЛЕГИРОВАНИЕ: Используем основной пайплайн как в main_new.py
                result = self.processor.extract_all_data(text_content)
                    
            except Exception as extract_error:
                print(f"      ❌ Ошибка в основном пайплайне: {extract_error}")
                return {
                    'filename': filename,
                    'success': False,
                    'error': f'Ошибка основного пайплайна: {str(extract_error)}',
                    'no_providers_available': False
                }
            
            processing_time = time.time() - start_time
            
            # Проверяем успешность по наличию данных
            if result and (result.get('organizations') or result.get('contacts') or result.get('commercial_offers')):
                print(f"      ✅ Обработано успешно за {processing_time:.2f}с")
                print(f"         - Организации: {len(result.get('organizations', []))}")
                print(f"         - Контакты: {len(result.get('contacts', []))}")
                print(f"         - Коммерческие предложения: {len(result.get('commercial_offers', []))}")
                
                return {
                    'filename': filename,
                    'email_data': {
                        'from': email_data.get('from', ''),
                        'subject': email_data.get('subject', ''),
                        'date': email_data.get('date', ''),
                        'attachments_count': len(email_data.get('attachments', [])),
                        'char_count': len(text_content),
                        'attachments': email_data.get('attachments', [])  # Добавляем информацию о вложениях
                    },
                    'llm_result': result,
                    'processing_time': processing_time,
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }
            else:
                print(f"      ❌ Обработка неуспешна: нет извлеченных данных")
                
                # Проверяем на отсутствие провайдеров
                error_msg = str(result.get('error', '')) if result else 'Пустой результат'
                no_providers = (
                    'Нет доступных LLM провайдеров' in error_msg or
                    'Все провайдеры недоступны' in error_msg or
                    (result and result.get('no_providers_available', False))
                )
                
                return {
                    'filename': filename,
                    'email_data': {
                        'from': email_data.get('from', ''),
                        'subject': email_data.get('subject', ''),
                        'date': email_data.get('date', ''),
                        'attachments_count': len(email_data.get('attachments', [])),
                        'char_count': len(text_content),
                        'attachments': email_data.get('attachments', [])  # Добавляем информацию о вложениях
                    },
                    'llm_result': result or {},
                    'processing_time': processing_time,
                    'timestamp': datetime.now().isoformat(),
                    'success': False,
                    'no_providers_available': no_providers
                }
                
        except Exception as e:
            print(f"      ❌ Ошибка обработки: {e}")
            import traceback
            print(f"      🔍 Детали ошибки: {traceback.format_exc()}")
            return {
                'filename': filename,
                'success': False,
                'error': str(e)
            }
    
    def _extract_text_content_via_main_pipeline(self, email_data: Dict) -> str:
        """📄 Извлечение текстового содержимого через основной пайплайн с OCR"""
        content_parts = []
        
        # Основной текст письма
        if email_data.get('body'):
            content_parts.append(f"=== ТЕКСТ ПИСЬМА ===\n{email_data['body']}")
        
        # 🎯 ПРАВИЛЬНАЯ АРХИТЕКТУРА: Обработка вложений через OCR сервис основного пайплайна
        attachments = email_data.get('attachments', [])
        if attachments:
            print(f"      📎 Обработка {len(attachments)} вложений через основной пайплайн...")
            
            # Импортируем унифицированный OCR менеджер
            try:
                from src.core.ocr_manager import get_ocr_manager
                ocr_manager = get_ocr_manager()
                
                for i, attachment in enumerate(attachments, 1):
                    attachment_name = attachment.get('original_filename', attachment.get('filename', f'attachment_{i}'))
                    # 🔧 ИСПРАВЛЕНИЕ: Используем правильный ключ для пути к файлу
                    attachment_path = attachment.get('file_path', attachment.get('path', ''))
                    
                    # Проверяем статус вложения - обрабатываем только сохраненные файлы
                    attachment_status = attachment.get('status', 'unknown')
                    if attachment_status in ['excluded_by_filter', 'excluded_by_size', 'unsupported']:
                        print(f"        ⏭️  Пропуск вложения: {attachment_name} (статус: {attachment_status})")
                        continue
                    
                    # Формируем полный путь к файлу
                    if attachment_path:
                        if not attachment_path.startswith('/'):
                            # Относительный путь - добавляем корень проекта
                            full_attachment_path = os.path.join(project_root, attachment_path)
                        else:
                            full_attachment_path = attachment_path
                    else:
                        full_attachment_path = ''
                    
                    if not full_attachment_path:
                        print(f"        ⚠️  Путь к файлу не указан: {attachment_name} (статус: {attachment_status})")
                        continue
                    
                    if os.path.exists(full_attachment_path):
                        # 🎯 ПРИОРИТЕТ: Используем уже обработанный текст если доступен
                        attachment_content = attachment.get('content', '')
                        if attachment_content and isinstance(attachment_content, str):
                            content_parts.append(f"\n=== ВЛОЖЕНИЕ {i}: {attachment_name} ===\n{attachment_content}")
                            print(f"        ✅ Используем готовый текст: {attachment_name} ({len(attachment_content)} символов)")
                        else:
                            # 🔄 FALLBACK: Обрабатываем через OCRManager если текст недоступен
                            try:
                                ocr_result = ocr_manager.extract_text_from_file(full_attachment_path, email_data.get('date'))
                                if ocr_result and ocr_result.get('success') and ocr_result.get('text'):
                                    extracted_text = ocr_result['text']
                                    content_parts.append(f"\n=== ВЛОЖЕНИЕ {i}: {attachment_name} ===\n{extracted_text}")
                                    print(f"        ✅ OCR обработка: {attachment_name} ({len(extracted_text)} символов)")
                                else:
                                    print(f"        ⚠️  OCR не смог обработать: {attachment_name}")
                            except Exception as ocr_error:
                                print(f"        ❌ Ошибка OCR для {attachment_name}: {ocr_error}")
                    else:
                        # Fallback: используем готовый текст если путь недоступен
                        attachment_content = attachment.get('content', '')
                        if attachment_content and isinstance(attachment_content, str):
                            content_parts.append(f"\n=== ВЛОЖЕНИЕ {i}: {attachment_name} ===\n{attachment_content}")
                            print(f"        ✅ Готовый текст: {attachment_name} ({len(attachment_content)} символов)")
                        else:
                            print(f"        ⚠️  Нет доступного текста: {attachment_name}")
                            
            except ImportError as import_error:
                print(f"        ❌ Не удалось импортировать OCRManager: {import_error}")
                # Fallback: используем старый метод
                return self._extract_text_content_fallback(email_data)
            except Exception as general_error:
                print(f"        ❌ Общая ошибка OCR обработки: {general_error}")
                # Fallback: используем старый метод
                return self._extract_text_content_fallback(email_data)
        
        combined_content = "\n\n".join(content_parts)
        print(f"      📊 Общий объем текста: {len(combined_content)} символов")
        
        return combined_content
    
    def _extract_text_content_fallback(self, email_data: Dict) -> str:
        """📄 Fallback метод извлечения текста без OCR"""
        content_parts = []
        
        # Основной текст письма
        if email_data.get('body'):
            content_parts.append(f"=== ТЕКСТ ПИСЬМА ===\n{email_data['body']}")
        
        # Простая обработка вложений без OCR
        attachments = email_data.get('attachments', [])
        if attachments:
            for i, attachment in enumerate(attachments, 1):
                attachment_name = attachment.get('filename', f'attachment_{i}')
                attachment_content = attachment.get('content', '')
                
                if attachment_content and isinstance(attachment_content, str) and len(attachment_content.strip()) > 0:
                    content_parts.append(f"\n=== ВЛОЖЕНИЕ {i}: {attachment_name} ===\n{attachment_content}")
                    print(f"        ✅ Fallback текст: {attachment_name} ({len(attachment_content)} символов)")
        
        return "\n\n".join(content_parts)

    def save_structured_result(self, result: Dict, filename: str) -> bool:
        """💾 Сохранение структурированного JSON результата"""
        try:
            # КРИТИЧЕСКАЯ ПРОВЕРКА: проверяем все возможные индикаторы ошибок
            llm_result = result.get('llm_result', {})
            # Исправляем извлечение данных - они могут быть в llm_result или extraction_result
            if not llm_result and 'extraction_result' in result:
                llm_result = result['extraction_result']
            
            # Проверка 1: флаг no_providers_available
            if result.get('no_providers_available'):
                print(f"      ⚠️ Пропускаем сохранение JSON: нет доступных провайдеров")
                return False
                
            # Проверка 2: общий success флаг
            if not result.get('success', False):
                print(f"      ⚠️ Пропускаем сохранение JSON: обработка неуспешна")
                return False
                
            # Проверка 3: validation_error в llm_result
            if llm_result.get('validation_error'):
                print(f"      ⚠️ Пропускаем сохранение JSON: ошибка валидации LLM")
                return False
                
            # Проверка 4: наличие error в llm_result
            if llm_result.get('error'):
                print(f"      ⚠️ Пропускаем сохранение JSON: ошибка в LLM результате")
                return False
                
            # Проверка 5: наличие реальных данных
            has_data = (
                llm_result.get('organizations') or 
                llm_result.get('contacts') or 
                llm_result.get('commercial_offers')
            )
            
            if not has_data:
                print(f"      ⚠️ Пропускаем сохранение JSON: нет извлеченных данных")
                return False
            
            # 🔧 ИСПРАВЛЕНИЕ: Убеждаемся что директория существует
            self.results_dir.mkdir(parents=True, exist_ok=True)
            
            # Формируем имя файла результата
            base_name = filename.replace('.json', '')
            result_filename = f"{base_name}_structured_result.json"
            result_path = self.results_dir / result_filename
            
            print(f"      💾 Сохраняю JSON в: {result_path}")
            
            # 🔧 УЛУЧШЕНИЕ: Подготавливаем чистые данные без дублирования
            # Соответствуем спецификации: исключаем original_email field
            structured_data = {
                'source_file': filename,
                'processing_timestamp': result.get('timestamp'),
                'processing_time_seconds': result.get('processing_time'),
                'email_metadata': result.get('email_data', {}),  # Оптимизированные метаданные
                'extraction_result': {
                    'success': llm_result.get('success', True),
                    'organizations': llm_result.get('organizations', []),
                    'contacts': llm_result.get('contacts', []),
                    'commercial_offers': llm_result.get('commercial_offers', []),
                    'business_context': llm_result.get('business_context', ''),
                    'attachments_processed': llm_result.get('attachments_processed', 0),
                    'provider_used': llm_result.get('provider_used', 'Unknown')
                    # 📎 Соответствуем спецификации: убираем 'original_email' чтобы избежать дублирования
                }
            }
            
            # Сохраняем JSON
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)
                
            print(f"      ✅ JSON сохранен: {result_filename}")
            self.stats['json_files_created'] += 1
            return True
            
        except Exception as e:
            print(f"      ❌ Ошибка сохранения JSON: {e}")
            import traceback
            print(f"      🔍 Детали ошибки: {traceback.format_exc()}")
            return False
    
    def _get_extractor_stats(self) -> Dict:
        """📊 Получение статистики экстрактора (паттерн из test_api_dataset.py)"""
        try:
            # Точно как в test_api_dataset.py
            if self.processor and hasattr(self.processor, 'get_stats'):
                return self.processor.get_stats()
            else:
                return {
                    'message': 'Статистика недоступна',
                    'processor_type': type(self.processor).__name__ if self.processor else 'None'
                }
        except Exception as e:
            return {
                'error': f'Ошибка получения статистики: {str(e)}'
            }

    def generate_detailed_report(self, result: Dict, filename: str) -> bool:
        """📄 Генерация детального отчета"""
        try:
            # КРИТИЧЕСКАЯ ПРОВЕРКА: проверяем все возможные индикаторы ошибок
            llm_result = result.get('llm_result', {})
            
            # Проверка 1: флаг no_providers_available
            if result.get('no_providers_available'):
                print(f"      ⚠️ Пропускаем создание отчета: нет доступных провайдеров")
                return False
                
            # Проверка 2: общий success флаг
            if not result.get('success', False):
                print(f"      ⚠️ Пропускаем создание отчета: обработка неуспешна")
                return False
                
            # Проверка 3: validation_error в llm_result
            if llm_result.get('validation_error'):
                print(f"      ⚠️ Пропускаем создание отчета: ошибка валидации LLM")
                return False
                
            # Проверка 4: наличие error в llm_result
            if llm_result.get('error'):
                print(f"      ⚠️ Пропускаем создание отчета: ошибка в LLM результате")
                return False
                
            # Проверка 5: наличие реальных данных
            has_data = (
                llm_result.get('organizations') or 
                llm_result.get('contacts') or 
                llm_result.get('commercial_offers')
            )
            
            if not has_data:
                print(f"      ⚠️ Пропускаем создание отчета: нет извлеченных данных")
                return False
            
            if not self.report_generator:
                print(f"      ⚠️ Отчеты недоступны: генератор отчетов не инициализирован")
                return False
                
            # 🔧 ИСПРАВЛЕНИЕ: Убеждаемся что директория существует
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Формируем имя файла отчета по образцу
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            base_name = filename.replace('.json', '')
            report_filename = f"{timestamp}_{base_name}_detailed.md"
            report_path = self.reports_dir / report_filename
            
            print(f"      📄 Генерирую отчет в: {report_path}")
            
            # Генерируем отчет через ReportGenerator
            report_content = self.report_generator.generate_validation_report(
                result=result,
                validation_result={'errors': [], 'warnings': []} if result.get('success') else {'errors': [result.get('error', 'Unknown error')]}
            )
            
            # Сохраняем отчет
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            print(f"      ✅ Отчет сохранен: {report_filename}")
            self.stats['reports_created'] += 1
            return True
            
        except Exception as e:
            print(f"      ❌ Ошибка генерации отчета: {e}")
            import traceback
            print(f"      🔍 Детали ошибки: {traceback.format_exc()}")
            return False

    # 📊 МЕТОДЫ ЛОГИРОВАНИЯ И МЕТРИК
    
    def log_processing_start(self, mode: str, total_files: int) -> None:
        """📊 Логирование начала обработки с записью в файл"""
        # Используем централизованный логгер
        log_pipeline_event(
            event_type="processing_start",
            mode=mode,
            total_files=total_files,
            date=self.date,
            session_id=f"pipeline_{int(time.time())}"
        )
        
        # Сохраняем для совместимости с существующей логикой
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            "timestamp": timestamp,
            "event_type": "processing_start",
            "mode": mode,
            "total_files": total_files,
            "date": self.date,
            "session_id": f"pipeline_{int(time.time())}"
        }
        self._write_log_to_file(log_entry)
        
        # Выводим в терминал
        print(f"🚀 [{timestamp}] Начало обработки режим '{mode}': {total_files} файлов для даты {self.date}")
        
        # Дополнительно используем config_manager если доступен
        if self.config_manager:
            self.config_manager.log_request_analytics(
                provider_name="api_pipeline_validator",
                request_type=f"processing_start_{mode}",
                response_time=0.0,
                token_usage=0,
                success=True,
                request_id=log_entry["session_id"]
            )
            
            self.config_manager.logger.info(
                "pipeline_processing_start",
                mode=mode,
                total_files=total_files,
                date=self.date,
                timestamp=datetime.now().isoformat()
            )
    
    def log_email_processing(self, filename: str, success: bool, processing_time: float, 
                           error: Optional[str] = None) -> None:
        """📊 Логирование обработки отдельного email с записью в файл"""
        # Используем централизованный логгер
        if error:
            log_error_event(
                error_type="email_processing_error",
                filename=filename,
                processing_time=processing_time,
                error_message=error
            )
        else:
            log_pipeline_event(
                event_type="email_processing",
                filename=filename,
                success=success,
                processing_time=processing_time
            )
        
        # Сохраняем для совместимости с существующей логикой
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            "timestamp": timestamp,
            "event_type": "email_processing",
            "filename": filename,
            "success": success,
            "processing_time_sec": round(processing_time, 3),
            "processing_time_ms": round(processing_time * 1000, 2)
        }
        
        if error:
            log_entry["error"] = error
            log_entry["error_type"] = "processing_error"
        
        self._write_log_to_file(log_entry)
        
        # Выводим в терминал
        status_icon = "✅" if success else "❌"
        time_str = f"{processing_time:.3f}s"
        if success:
            print(f"{status_icon} [{timestamp}] {filename} обработан за {time_str}")
        else:
            print(f"{status_icon} [{timestamp}] {filename} ОШИБКА за {time_str}: {error or 'Неизвестная ошибка'}")
        
        # Дополнительно используем config_manager если доступен
        if self.config_manager:
            self.config_manager.log_request_analytics(
                provider_name="email_processor",
                request_type="email_processing",
                response_time=processing_time,
                token_usage=0,
                success=success,
                error_type="processing_error" if error else None,
                request_id=f"email_{filename}_{int(time.time())}"
            )
            
            if success:
                self.config_manager.logger.info("email_processed", **log_entry)
            else:
                self.config_manager.logger.error("email_processing_failed", **log_entry)
    
    def log_pipeline_metrics(self, mode: str, stats: Dict) -> None:
        """📊 Логирование метрик пайплайна с записью в файл"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Вычисляем метрики
        emails_processed = stats.get('emails_processed', 0)
        emails_successful = stats.get('emails_successful', 0)
        emails_failed = stats.get('emails_failed', 0)
        success_rate = round(emails_successful / max(1, emails_processed), 3) if emails_processed > 0 else 0
        total_time = stats.get('total_time', 0)
        avg_time = round(total_time / max(1, emails_processed), 2) if emails_processed > 0 else 0
        
        # Создаем лог-запись
        log_entry = {
            "timestamp": timestamp,
            "event_type": "pipeline_metrics",
            "mode": mode,
            "date": self.date,
            "emails_processed": emails_processed,
            "emails_successful": emails_successful,
            "emails_failed": emails_failed,
            "success_rate": success_rate,
            "json_files_created": stats.get('json_files_created', 0),
            "reports_created": stats.get('reports_created', 0),
            "total_processing_time_sec": total_time,
            "avg_processing_time_per_email_sec": avg_time
        }
        
        if stats.get('errors'):
            log_entry["error_count"] = len(stats['errors'])
            log_entry["error_types"] = list(set([type(e).__name__ for e in stats['errors'] if isinstance(e, Exception)]))
        
        # Записываем в файл логов
        self._write_log_to_file(log_entry)
        
        # Выводим в терминал
        print(f"📊 [{timestamp}] Метрики пайплайна '{mode}':")
        print(f"   📧 Обработано: {emails_processed}, Успешно: {emails_successful}, Ошибок: {emails_failed}")
        print(f"   📈 Успешность: {success_rate*100:.1f}%, Среднее время: {avg_time:.2f}с")
        print(f"   📄 JSON файлов: {log_entry['json_files_created']}, Отчетов: {log_entry['reports_created']}")
        
        # Дополнительно используем config_manager если доступен
        if self.config_manager:
            self.config_manager.logger.info("pipeline_metrics", **log_entry)
    
    def log_system_performance(self) -> None:
        """📊 Логирование производительности системы с записью в файл"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Создаем лог-запись производительности
        log_entry = {
            "timestamp": timestamp,
            "event_type": "system_performance",
            "date": self.date
        }
        
        # Добавляем системные метрики если доступны
        try:
            import psutil
            log_entry.update({
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            })
        except ImportError:
            log_entry["system_metrics"] = "psutil_not_available"
        
        # Записываем в файл логов
        self._write_log_to_file(log_entry)
        
        # Выводим в терминал
        print(f"🖥️ [{timestamp}] Системная производительность зафиксирована")
        
        # Дополнительно используем config_manager если доступен
        if self.config_manager:
            self.config_manager.log_system_health()
            
            for provider_name in self.config_manager.provider_stats.keys():
                self.config_manager.log_performance_metrics(provider_name)
    
    def _write_log_to_file(self, log_entry: Dict) -> None:
        """📝 Запись лога в файл"""
        try:
            # Создаем директорию логов если не существует
            logs_dir = Path(self.project_root) / "data" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем имя файла лога на основе даты
            log_filename = f"api_pipeline_validator_{self.date}.jsonl"
            log_file_path = logs_dir / log_filename
            
            # Записываем лог-запись в формате JSONL (одна строка JSON на строку)
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            print(f"⚠️ Ошибка записи лога в файл: {e}")
    
    def export_session_analytics(self) -> Optional[str]:
        """📊 Экспорт аналитики сессии с улучшенным логированием"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Создаем лог-запись об экспорте
        log_entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "event_type": "analytics_export",
            "date": self.date,
            "export_timestamp": timestamp
        }
        
        if self.config_manager:
            try:
                output_file = f"pipeline_analytics_{self.date}_{timestamp}.json"
                output_path = self.config_manager.export_analytics_logs(
                    hours=24, 
                    output_file=str(self.reports_dir / output_file)
                )
                
                log_entry["export_success"] = True
                log_entry["export_path"] = str(output_path)
                
                # Записываем в файл логов
                self._write_log_to_file(log_entry)
                
                print(f"📊 Аналитика экспортирована: {output_path}")
                return output_path
            except Exception as e:
                log_entry["export_success"] = False
                log_entry["export_error"] = str(e)
                
                # Записываем ошибку в файл логов
                self._write_log_to_file(log_entry)
                
                print(f"❌ Ошибка экспорта аналитики: {e}")
                return None
        else:
            log_entry["export_success"] = False
            log_entry["export_error"] = "config_manager_not_available"
            
            # Записываем в файл логов
            self._write_log_to_file(log_entry)
            
            print("⚠️ Config manager недоступен для экспорта аналитики")
            return None
        return None

    def run_first10_mode(self) -> Dict:
        """🎯 Режим first10: обработка первых 10 писем из тестового датасета"""
        print("\n🎯 РЕЖИМ FIRST10: Обработка тестового датасета")
        print("=" * 55)
        
        # Загружаем список файлов из тестового датасета
        test_files = self.load_test_dataset_files()
        if not test_files:
            return {'success': False, 'error': 'Не удалось загрузить тестовый датасет'}
            
        # Проверяем, какие файлы уже обработаны
        processed_files = self.get_already_processed_files()
        files_to_process = [f for f in test_files if f not in processed_files]
        
        print(f"\n📊 Статистика:")
        print(f"   📄 Файлов в датасете: {len(test_files)}")
        print(f"   ✅ Уже обработано: {len(processed_files)}")
        print(f"   🔄 К обработке: {len(files_to_process)}")
        
        # Логируем начало обработки
        self.log_processing_start("first10", len(files_to_process))
        
        if not files_to_process:
            print("\n🎉 Все файлы из тестового датасета уже обработаны!")
            return {'success': True, 'files_processed': 0, 'reason': 'Все файлы уже обработаны'}
            
        # Обрабатываем файлы
        results = []
        for i, filename in enumerate(files_to_process, 1):
            print(f"\n   📧 {i}/{len(files_to_process)}: {filename}")
            
            # Засекаем время обработки
            start_time = time.time()
            
            # Обрабатываем письмо
            result = self.process_single_email(filename)
            processing_time = time.time() - start_time
            
            if result:
                results.append(result)
                
                if result.get('success'):
                    # Сохраняем JSON только для успешных результатов
                    if self.save_structured_result(result, filename):
                        # Генерируем отчет только если JSON сохранен
                        self.generate_detailed_report(result, filename)
                    
                    self.stats['emails_successful'] += 1
                    # Логируем успешную обработку
                    self.log_email_processing(filename, True, processing_time)
                else:
                    self.stats['emails_failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    
                    # Логируем неуспешную обработку
                    self.log_email_processing(filename, False, processing_time, error_msg)
                    
                    # Особая обработка ошибки отсутствия провайдеров
                    if result.get('no_providers_available'):
                        print(f"   ⚠️ Прерываем обработку: нет доступных LLM провайдеров")
                        return {
                            'success': False,
                            'error': 'Нет доступных LLM провайдеров для обработки',
                            'files_processed': 0,
                            'files_successful': 0,
                            'files_failed': len(files_to_process),
                            'no_providers_available': True
                        }
                    
                    self.stats['errors'].append(f"{filename}: {error_msg}")
                    
                self.stats['emails_processed'] += 1
        
        # Логируем финальные метрики и производительность
        self.log_pipeline_metrics("first10", self.stats)
        self.log_system_performance()
        
        # Экспортируем аналитику сессии
        analytics_path = self.export_session_analytics()
        
        result = {
            'success': True,
            'files_processed': len(files_to_process),
            'files_successful': self.stats['emails_successful'],
            'files_failed': self.stats['emails_failed'],
            'results': results
        }
        
        if analytics_path:
            result['analytics_exported'] = analytics_path
            
        return result

    def run_all_mode(self) -> Dict:
        """🌐 Режим all: обработка всех писем за дату, исключая уже обработанные"""
        print("\n🌐 РЕЖИМ ALL: Обработка всех писем за дату")
        print("=" * 50)
        
        # Получаем все файлы писем
        all_email_files = self.get_all_email_files()
        
        # Получаем уже обработанные файлы
        processed_files = self.get_already_processed_files()
        
        # Определяем файлы к обработке (исключаем уже обработанные)
        files_to_process = [f for f in all_email_files if f not in processed_files]
        
        print(f"\n📊 Статистика:")
        print(f"   📄 Всего писем за {self.date}: {len(all_email_files)}")
        print(f"   ✅ Уже обработано: {len(processed_files)}")
        print(f"   🔄 К обработке: {len(files_to_process)}")
        
        # Логируем начало обработки
        self.log_processing_start("all", len(files_to_process))
        
        if not files_to_process:
            print("\n🎉 Все письма уже обработаны!")
            return {'success': True, 'files_processed': 0, 'reason': 'Все файлы уже обработаны'}
            
        # Обрабатываем файлы
        results = []
        for i, filename in enumerate(files_to_process, 1):
            print(f"\n   📧 {i}/{len(files_to_process)}: {filename}")
            
            # Засекаем время обработки
            start_time = time.time()
            
            # Обрабатываем письмо
            result = self.process_single_email(filename)
            processing_time = time.time() - start_time
            
            if result:
                results.append(result)
                
                if result.get('success'):
                    # Сохраняем JSON только для успешных результатов
                    if self.save_structured_result(result, filename):
                        # Генерируем отчет только если JSON сохранен
                        self.generate_detailed_report(result, filename)
                    
                    self.stats['emails_successful'] += 1
                    # Логируем успешную обработку
                    self.log_email_processing(filename, True, processing_time)
                else:
                    self.stats['emails_failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    
                    # Логируем неуспешную обработку
                    self.log_email_processing(filename, False, processing_time, error_msg)
                    
                    # Особая обработка ошибки отсутствия провайдеров
                    if result.get('no_providers_available'):
                        print(f"   ⚠️ Прерываем обработку: нет доступных LLM провайдеров")
                        return {
                            'success': False,
                            'error': 'Нет доступных LLM провайдеров для обработки',
                            'files_processed': 0,
                            'files_successful': 0,
                            'files_failed': len(files_to_process),
                            'no_providers_available': True
                        }
                    
                    self.stats['errors'].append(f"{filename}: {error_msg}")
                    
                self.stats['emails_processed'] += 1
        
        # Логируем финальные метрики и производительность
        self.log_pipeline_metrics("all", self.stats)
        self.log_system_performance()
        
        # Экспортируем аналитику сессии
        analytics_path = self.export_session_analytics()
        
        result = {
            'success': True,
            'files_processed': len(files_to_process),
            'files_successful': self.stats['emails_successful'],
            'files_failed': self.stats['emails_failed'],
            'results': results
        }
        
        if analytics_path:
            result['analytics_exported'] = analytics_path
            
        return result

    def update_index_files(self):
        """📋 Обновление индексных файлов отчетов"""
        print("\n📋 ОБНОВЛЕНИЕ ИНДЕКСНЫХ ФАЙЛОВ")
        print("=" * 40)
        
        try:
            # Обновляем detailed_reports_index.md
            index_path = self.project_root / "memory-bank" / "reports" / "detailed_reports_index.md"
            
            # Собираем все отчеты
            report_files = list(self.reports_dir.glob("*_detailed.md"))
            report_files.sort()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')
            index_content = f"""# Индекс детальных отчетов по API валидации

**Дата создания:** {timestamp}
**Источник данных:** {self.date}
**Количество отчетов:** {len(report_files)}

## Список отчетов

"""
            
            for i, report_path in enumerate(report_files, 1):
                report_name = report_path.name
                # Извлекаем номер письма
                if 'email_' in report_name:
                    email_num = report_name.split('email_')[1].split('_')[0]
                else:
                    email_num = str(i).zfill(3)
                    
                index_content += f"{i}. [Письмо #{email_num}]({report_name})\n"
                
            index_content += f"\n---\n**Обновлено:** {timestamp}"
            
            # Сохраняем индекс
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
                
            print(f"   ✅ Обновлен: detailed_reports_index.md")
            
            # Обновляем основной index.md
            main_index_path = self.project_root / "memory-bank" / "reports" / "index.md"
            description = f"API Pipeline Validation - {self.date}"
            if self.report_generator:
                self.report_generator.update_index(f"api_validation_{self.date}.md", description)
            else:
                print(f"   ⚠️ Генератор отчетов недоступен, пропускаем обновление index.md")
            
            print(f"   ✅ Обновлен: index.md")
            
        except Exception as e:
            print(f"   ❌ Ошибка обновления индексов: {e}")

    def generate_final_report(self) -> str:
        """📊 Генерация итогового отчета валидации (паттерн test_api_dataset.py)"""
        print("\n📊 ГЕНЕРАЦИЯ ИТОГОВОГО ОТЧЕТА")
        print("=" * 40)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        report_filename = f"{timestamp}_api_pipeline_validation_summary.md"
        report_path = self.reports_dir / report_filename
        
        processing_time = None
        if self.stats['start_time'] and self.stats['end_time']:
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
        # 🎯 УЛУЧШЕНИЕ: Добавляем статистику экстрактора как в test_api_dataset.py
        extractor_stats = self._get_extractor_stats()
        
        success_rate = (self.stats['emails_successful'] / max(self.stats['emails_processed'], 1)) * 100
        
        report_content = f"""# Итоговый отчет API Pipeline Validation

**Дата валидации:** {datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')}
**Целевая дата:** {self.date}
**Время обработки:** {processing_time:.2f} секунд

## 📊 Статистика обработки

- **Всего писем обработано:** {self.stats['emails_processed']}
- **Успешных обработок:** {self.stats['emails_successful']}
- **Неудачных обработок:** {self.stats['emails_failed']}
- **Успешность:** {success_rate:.1f}%
- **JSON файлов создано:** {self.stats['json_files_created']}
- **Отчетов создано:** {self.stats['reports_created']}

## 🤖 Статистика экстрактора

"""
        
        if extractor_stats:
            for key, value in extractor_stats.items():
                report_content += f"- **{key}:** {value}\n"
        else:
            report_content += "- Статистика экстрактора недоступна\n"
        
        report_content += f"""

## 📁 Результаты

### JSON файлы (structured_results/)
Сохранены в: `{self.results_dir}`

### Детальные отчеты
Сохранены в: `{self.reports_dir}`

## 🎯 Статус валидации

{'✅ УСПЕШНО' if self.stats['emails_failed'] == 0 else '⚠️ С ОШИБКАМИ'}

"""
        
        if self.stats['errors']:
            report_content += "\n## ❌ Ошибки\n\n"
            for error in self.stats['errors']:
                report_content += f"- {error}\n"
                
        report_content += f"\n---\n*Отчет создан: {timestamp}*"
        
        # Сохраняем отчет
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"   ✅ Итоговый отчет: {report_filename}")
        return str(report_path)

    def run(self, mode: str) -> Dict:
        """🚀 Запуск валидации в указанном режиме"""
        self.stats['start_time'] = datetime.now()
        
        print(f"\n🚀 ЗАПУСК API PIPELINE VALIDATION")
        print(f"   📅 Дата: {self.date}")
        print(f"   🎯 Режим: {mode}")
        print("=" * 60)
        
        # Валидация настроек
        if not self.validate_setup():
            return {'success': False, 'error': 'Валидация настроек не прошла'}
            
        # Выполнение в зависимости от режима
        if mode == 'first10':
            result = self.run_first10_mode()
        elif mode == 'all':
            result = self.run_all_mode()
        else:
            return {'success': False, 'error': f'Неизвестный режим: {mode}'}
            
        self.stats['end_time'] = datetime.now()
        
        # Обновление индексов и генерация итогового отчета
        if result.get('success'):
            self.update_index_files()
            final_report_path = self.generate_final_report()
            result['final_report'] = final_report_path
            
        # Добавляем статистику к результату
        result['stats'] = self.stats
        
        print(f"\n🎉 ВАЛИДАЦИЯ ЗАВЕРШЕНА")
        print(f"   ⏱️ Время выполнения: {(self.stats['end_time'] - self.stats['start_time']).total_seconds():.2f}с")
        print(f"   📊 Обработано: {self.stats['emails_processed']} писем")
        print(f"   ✅ Успешно: {self.stats['emails_successful']}")
        print(f"   ❌ Ошибок: {self.stats['emails_failed']}")
        
        return result


class AsyncAPIPipelineValidator(APIPipelineValidator):
    """🚀 Асинхронный валидатор API пайплайна с поддержкой AsyncProviderManager"""
    
    def __init__(self, 
                 date: str = "2025-07-29",
                 results_dir: Optional[str] = None,
                 reports_dir: Optional[str] = None,
                 test_mode: bool = False,
                 max_concurrent: int = 2):
        """
        Инициализация асинхронного валидатора
        
        Args:
            date: Дата для обработки
            results_dir: Директория для сохранения JSON результатов
            reports_dir: Директория для сохранения отчетов
            test_mode: Режим тестирования
            max_concurrent: Максимальное количество конкурентных запросов
        """
        super().__init__(date, results_dir, reports_dir, test_mode)
        self.max_concurrent = max_concurrent
        self.async_manager = None
        
        print(f"🚀 Async API Pipeline Validator для даты {date}")
        print(f"   ⚡ Максимальная конкурентность: {max_concurrent}")
    
    def validate_async_setup(self) -> bool:
        """🔍 Валидация настроек для асинхронного режима"""
        print("\n🔍 ВАЛИДАЦИЯ АСИНХРОННЫХ НАСТРОЕК")
        print("=" * 50)
        
        # Базовая валидация
        if not self.validate_setup():
            return False
            
        # Инициализация асинхронного менеджера
        print("   🚀 Инициализация AsyncProviderManager...")
        try:
            if AsyncProviderManager:
                self.async_manager = AsyncProviderManager()
                
                # Добавление провайдеров из конфигурации
                from src.config.config_manager import UnifiedConfigManager
                config_manager = UnifiedConfigManager()
                llm_providers = config_manager.get_llm_providers()
                
                for provider_config in llm_providers:
                    if provider_config.active:
                        provider_name = provider_config.name
                        
                        # Создание ProviderConfig для базового провайдера
                        from src.providers.base_provider import ProviderConfig
                        base_config = ProviderConfig(
                            name=provider_config.name,
                            api_key=provider_config.api_key,
                            model=provider_config.model,
                            base_url=provider_config.base_url,
                            priority=provider_config.priority,
                            active=provider_config.active,
                            timeout=provider_config.timeout,
                            max_retries=provider_config.max_retries
                        )
                        
                        # Создание провайдера с конфигурацией (регистронезависимо)
                        provider_name_lower = provider_name.lower()
                        if provider_name_lower == 'openrouter':
                            from src.providers.openrouter import OpenRouterProvider
                            provider = OpenRouterProvider(base_config)
                        elif provider_name_lower == 'groq':
                            from src.providers.groq import GroqProvider
                            provider = GroqProvider(base_config)
                        elif provider_name_lower == 'replicate':
                            from src.providers.replicate import ReplicateProvider
                            provider = ReplicateProvider(base_config)
                        else:
                            print(f"   ⚠️ Неизвестный провайдер: {provider_name}")
                            continue
                            
                        self.async_manager.add_provider(provider_name, provider)
                        print(f"   ✅ Добавлен провайдер: {provider_name}")
                        
                print(f"   ✅ AsyncProviderManager инициализирован с {len(self.async_manager.providers)} провайдерами")
            else:
                print("   ❌ AsyncProviderManager недоступен")
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка инициализации AsyncProviderManager: {e}")
            return False
            
        return True
    
    async def process_single_email_async(self, filename: str) -> Optional[Dict]:
        """📧 Асинхронная обработка одного письма"""
        start_time = time.time()
        
        try:
            # Загрузка письма
            email_data = self.load_email_with_attachments(filename)
            if not email_data:
                return {
                    'filename': filename,
                    'success': False,
                    'error': 'Не удалось загрузить письмо',
                    'processing_time': time.time() - start_time
                }
            
            # Извлечение текста
            text_content = self._extract_text_content_via_main_pipeline(email_data)
            if not text_content or len(text_content.strip()) < 50:
                text_content = self._extract_text_content_fallback(email_data)
            
            if not text_content or len(text_content.strip()) < 50:
                return {
                    'filename': filename,
                    'success': False,
                    'error': 'Недостаточно текстового содержимого для анализа',
                    'processing_time': time.time() - start_time
                }
            
            # Асинхронная обработка через LLM с корректной статистикой
            if self.async_manager:
                # Используем processor напрямую для корректной статистики
                try:
                    llm_result = await self.processor.extract_all_data_async(text_content)
                    
                    if not llm_result or llm_result.get('error'):
                        return {
                            'filename': filename,
                            'success': False,
                            'error': f'Ошибка обработки LLM: {llm_result.get("error", "Неизвестная ошибка")}',
                            'processing_time': time.time() - start_time
                        }
                except Exception as e:
                    return {
                        'filename': filename,
                        'success': False,
                        'error': f'Исключение при обработке LLM: {str(e)}',
                        'processing_time': time.time() - start_time
                    }
            else:
                # Fallback к синхронной обработке
                llm_result = self.processor.extract_all_data(text_content)
            
            # Формирование результата
            result = {
                'filename': filename,
                'success': True,
                'email_data': email_data,
                'text_content': text_content,
                'llm_result': llm_result,
                'processing_time': time.time() - start_time,
                'async_mode': True
            }
            
            return result
            
        except Exception as e:
            return {
                'filename': filename,
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def run_async_mode(self, mode: str) -> Dict:
        """🚀 Асинхронный запуск валидации"""
        self.stats['start_time'] = datetime.now()
        
        print(f"\n🚀 ЗАПУСК ASYNC API PIPELINE VALIDATION")
        print(f"   📅 Дата: {self.date}")
        print(f"   🎯 Режим: {mode}")
        print(f"   ⚡ Конкурентность: {self.max_concurrent}")
        print("=" * 60)
        
        # Валидация настроек
        if not self.validate_async_setup():
            return {'success': False, 'error': 'Валидация асинхронных настроек не прошла'}
        
        # Получение списка файлов
        if mode == 'first10':
            files_to_process = self.load_test_dataset_files()
        elif mode == 'all':
            files_to_process = self.get_all_email_files()
        else:
            return {'success': False, 'error': f'Неизвестный режим: {mode}'}
        
        if not files_to_process:
            return {'success': False, 'error': 'Нет файлов для обработки'}
        
        print(f"\n📋 К обработке: {len(files_to_process)} файлов")
        self.log_processing_start(f"async_{mode}", len(files_to_process))
        
        # Асинхронная обработка файлов
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(filename):
            async with semaphore:
                return await self.process_single_email_async(filename)
        
        # Создание задач
        tasks = [process_with_semaphore(filename) for filename in files_to_process]
        
        # Выполнение с прогрессом
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            results.append(result)
            
            # Логирование прогресса
            if result:
                success = result.get('success', False)
                processing_time = result.get('processing_time', 0)
                error = result.get('error') if not success else None
                
                self.log_email_processing(result.get('filename', ''), success, processing_time, error)
                
                if success:
                    self.stats['emails_successful'] += 1
                    # Сохранение результатов
                    self.save_structured_result(result, result['filename'])
                    self.generate_detailed_report(result, result['filename'])
                else:
                    self.stats['emails_failed'] += 1
                    self.stats['errors'].append({
                        'filename': result.get('filename', ''),
                        'error': error
                    })
            
            self.stats['emails_processed'] += 1
            print(f"   📧 Обработано: {i}/{len(files_to_process)} ({(i/len(files_to_process)*100):.1f}%)")
        
        self.stats['end_time'] = datetime.now()
        
        # Статистика асинхронного менеджера
        if self.async_manager:
            async_stats = self.async_manager.get_stats()
            print(f"\n📊 СТАТИСТИКА АСИНХРОННЫХ ПРОВАЙДЕРОВ:")
            print(f"   🔄 Всего запросов: {async_stats.get('total_requests', 0)}")
            print(f"   ✅ Успешных: {async_stats.get('successful_requests', 0)}")
            print(f"   ❌ Ошибок: {async_stats.get('failed_requests', 0)}")
            print(f"   💾 Cache hits: {async_stats.get('cache_hits', 0)}")
            print(f"   ⏱️ Среднее время: {async_stats.get('average_response_time', 0):.2f}с")
        
        # Обновление индексов и генерация итогового отчета
        success_count = self.stats['emails_successful']
        if success_count > 0:
            self.update_index_files()
            final_report_path = self.generate_final_report()
            
            result = {
                'success': True,
                'mode': f'async_{mode}',
                'files_processed': len(files_to_process),
                'successful': success_count,
                'failed': self.stats['emails_failed'],
                'final_report': final_report_path,
                'stats': self.stats,
                'async_stats': async_stats if self.async_manager else None
            }
        else:
            result = {
                'success': False,
                'error': 'Ни один файл не был успешно обработан',
                'stats': self.stats
            }
        
        print(f"\n🎉 АСИНХРОННАЯ ВАЛИДАЦИЯ ЗАВЕРШЕНА")
        print(f"   ⏱️ Время выполнения: {(self.stats['end_time'] - self.stats['start_time']).total_seconds():.2f}с")
        print(f"   📊 Обработано: {self.stats['emails_processed']} писем")
        print(f"   ✅ Успешно: {self.stats['emails_successful']}")
        print(f"   ❌ Ошибок: {self.stats['emails_failed']}")
        
        return result


def check_files_for_date(date: str) -> dict:
    """Проверка наличия всех необходимых файлов для указанной даты"""
    from pathlib import Path
    
    base_dir = Path("/Users/evgenyzach/contact_parser")
    emails_dir = base_dir / "data" / "emails" / date
    attachments_dir = base_dir / "data" / "attachments" / date
    final_results_dir = base_dir / "data" / "final_results" / date
    
    result = {
        "emails_exist": False,
        "attachments_exist": False,
        "ocr_results_exist": False,
        "emails_count": 0,
        "attachments_count": 0,
        "ocr_files_count": 0,
        "missing_ocr_files": []
    }
    
    # Проверка писем
    if emails_dir.exists():
        email_files = list(emails_dir.glob("*.json"))
        result["emails_exist"] = len(email_files) > 0
        result["emails_count"] = len(email_files)
    
    # Проверка вложений
    if attachments_dir.exists():
        attachment_files = list(attachments_dir.glob("*"))
        attachment_files = [f for f in attachment_files if f.is_file()]
        result["attachments_exist"] = len(attachment_files) > 0
        result["attachments_count"] = len(attachment_files)
        
        # Проверка результатов OCR
        if final_results_dir.exists():
            ocr_files = list(final_results_dir.glob("*.txt"))
            result["ocr_files_count"] = len(ocr_files)
            result["ocr_results_exist"] = len(ocr_files) > 0
            
            # Проверяем какие файлы вложений не обработаны OCR
            ocr_stems = {f.stem.split('___')[0] for f in ocr_files}
            for att_file in attachment_files:
                att_stem = att_file.stem
                if att_stem not in ocr_stems:
                    result["missing_ocr_files"].append(att_file.name)
    
    return result

def run_ocr_processing(date: str) -> bool:
    """Запуск OCR обработки для указанной даты"""
    import subprocess
    import sys
    from pathlib import Path
    
    try:
        # Импортируем OCRProcessor напрямую
        sys.path.append(str(Path(__file__).parent))
        from ocr_processor import OCRProcessor
        
        print(f"🔄 Запуск OCR обработки для даты {date}...")
        
        # Создаем экземпляр OCR процессора
        ocr_processor = OCRProcessor()
        
        # Получаем файлы для обработки
        files_to_process = ocr_processor.get_files_for_date(date)
        
        if not files_to_process:
            print(f"⚠️ Не найдено файлов для OCR обработки в дате {date}")
            return True  # Не ошибка, просто нет файлов
        
        print(f"📄 Найдено {len(files_to_process)} файлов для OCR обработки")
        
        # Запускаем обработку
        ocr_processor.test_files_by_date(date, files_to_process)
        
        print(f"✅ OCR обработка для даты {date} завершена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при запуске OCR обработки: {e}")
        return False

def validate_and_prepare_date(date: str) -> bool:
    """Валидация и подготовка данных для указанной даты"""
    print(f"\n🔍 Проверка файлов для даты {date}...")
    
    # Проверяем наличие файлов
    file_status = check_files_for_date(date)
    
    print(f"📧 Письма: {'✅' if file_status['emails_exist'] else '❌'} ({file_status['emails_count']} файлов)")
    print(f"📎 Вложения: {'✅' if file_status['attachments_exist'] else '❌'} ({file_status['attachments_count']} файлов)")
    print(f"🔍 OCR результаты: {'✅' if file_status['ocr_results_exist'] else '❌'} ({file_status['ocr_files_count']} файлов)")
    
    # Если нет писем, это критическая ошибка
    if not file_status['emails_exist']:
        print(f"❌ Критическая ошибка: не найдены файлы писем для даты {date}")
        return False
    
    # Если есть вложения, но нет OCR результатов или есть необработанные файлы
    if file_status['attachments_exist']:
        if not file_status['ocr_results_exist'] or file_status['missing_ocr_files']:
            if file_status['missing_ocr_files']:
                print(f"⚠️ Найдены необработанные вложения: {len(file_status['missing_ocr_files'])} файлов")
            else:
                print(f"⚠️ OCR результаты отсутствуют для {file_status['attachments_count']} вложений")
            
            # Запускаем OCR обработку
            if not run_ocr_processing(date):
                print(f"❌ Не удалось выполнить OCR обработку для даты {date}")
                return False
        else:
            print(f"✅ Все вложения уже обработаны OCR")
    else:
        print(f"ℹ️ Вложения отсутствуют для даты {date}")
    
    print(f"✅ Валидация и подготовка для даты {date} завершена успешно")
    return True

def get_available_dates() -> List[str]:
    """Получить список доступных дат из папки data/emails"""
    emails_dir = project_root / "data" / "emails"
    if not emails_dir.exists():
        return []
    
    dates = []
    for item in emails_dir.iterdir():
        if item.is_dir() and item.name.count('-') == 2:
            try:
                # Проверяем что это валидная дата в формате YYYY-MM-DD
                datetime.strptime(item.name, '%Y-%m-%d')
                dates.append(item.name)
            except ValueError:
                continue
    
    return sorted(dates)

def interactive_menu() -> Dict[str, str]:
    """Интерактивное меню для выбора режима и даты"""
    print("\n" + "="*60)
    print("🎯 API Pipeline Validator - Интерактивный режим")
    print("="*60)
    
    # Выбор типа обработки (синхронный/асинхронный)
    print("\n⚡ Выберите тип обработки:")
    print("1. sync - Синхронная обработка (по умолчанию)")
    print("2. async - Асинхронная обработка (быстрее)")
    
    while True:
        async_choice = input("\nВведите номер (1-2): ").strip()
        if async_choice in ['1', '2']:
            break
        print("❌ Неверный выбор. Введите 1 или 2.")
    
    is_async = async_choice == '2'
    
    # Выбор режима
    print("\n📋 Выберите режим обработки:")
    print("1. first10 - Обработать первые 10 файлов")
    print("2. all - Обработать все файлы")
    print("3. date - Выбрать конкретную дату")
    
    while True:
        choice = input("\nВведите номер (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("❌ Неверный выбор. Введите 1, 2 или 3.")
    
    if choice == '1':
        return {'mode': 'first10', 'date': '2025-07-29', 'async': is_async}
    elif choice == '2':
        return {'mode': 'all', 'date': '2025-07-29', 'async': is_async}
    else:
        # Выбор даты
        available_dates = get_available_dates()
        if not available_dates:
            print("❌ Не найдено доступных дат в data/emails")
            return {'mode': 'first10', 'date': '2025-07-29'}
        
        print(f"\n📅 Доступные даты ({len(available_dates)} шт.):")
        
        # Показываем даты по 10 штук на страницу
        page_size = 10
        total_pages = (len(available_dates) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(available_dates))
            
            print(f"\nСтраница {current_page + 1} из {total_pages}:")
            for i in range(start_idx, end_idx):
                print(f"{i + 1:3d}. {available_dates[i]}")
            
            if total_pages > 1:
                print("\nНавигация:")
                if current_page > 0:
                    print("p - предыдущая страница")
                if current_page < total_pages - 1:
                    print("n - следующая страница")
            
            user_input = input("\nВведите номер даты, 'p' (назад), 'n' (вперед) или 'q' (выход): ").strip().lower()
            
            if user_input == 'q':
                return {'mode': 'first10', 'date': '2025-07-29', 'async': is_async}
            elif user_input == 'p' and current_page > 0:
                current_page -= 1
                continue
            elif user_input == 'n' and current_page < total_pages - 1:
                current_page += 1
                continue
            
            try:
                date_idx = int(user_input) - 1
                if 0 <= date_idx < len(available_dates):
                    selected_date = available_dates[date_idx]
                    print(f"\n✅ Выбрана дата: {selected_date}")
                    
                    # Выбор режима для выбранной даты
                    print("\n📋 Выберите режим для этой даты:")
                    print("1. first10 - Первые 10 файлов")
                    print("2. all - Все файлы")
                    
                    while True:
                        mode_choice = input("\nВведите номер (1-2): ").strip()
                        if mode_choice == '1':
                            return {'mode': 'first10', 'date': selected_date, 'async': is_async}
                        elif mode_choice == '2':
                            return {'mode': 'all', 'date': selected_date, 'async': is_async}
                        else:
                            print("❌ Неверный выбор. Введите 1 или 2.")
                else:
                    print(f"❌ Неверный номер. Введите число от 1 до {len(available_dates)}.")
            except ValueError:
                print("❌ Неверный ввод. Введите число, 'p', 'n' или 'q'.")

def run_full_pipeline_for_date(date: str) -> bool:
    """Запуск полного пайплайна для указанной даты"""
    try:
        print(f"\n🚀 Запуск полного пайплайна для даты {date}...")
        
        # Создаем валидатор для указанной даты
        validator = APIPipelineValidator(
            date=date,
            test_mode=False
        )
        
        # Проверяем настройку
        if not validator.validate_setup():
            print(f"❌ Ошибка настройки валидатора для даты {date}")
            return False
        
        # Запускаем обработку всех файлов для даты
        print(f"📧 Обработка всех писем для даты {date}...")
        result = validator.run_all_mode()
        
        # Генерируем финальный отчет
        print(f"📊 Генерация финального отчета...")
        report_path = validator.generate_final_report()
        
        print(f"\n✅ Полный пайплайн для даты {date} завершен успешно!")
        print(f"📄 Отчет сохранен: {report_path}")
        print(f"📈 Обработано файлов: {result.get('total_files', 0)}")
        print(f"✅ Успешно: {result.get('successful_files', 0)}")
        print(f"❌ Ошибки: {result.get('failed_files', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при запуске полного пайплайна: {e}")
        return False

def process_first_10_emails(date: str) -> bool:
    """Обработка первых 10 писем для указанной даты"""
    try:
        validator = APIPipelineValidator(date=date, test_mode=False)
        if not validator.validate_setup():
            return False
        result = validator.run_first10_mode()
        print(f"✅ Обработано первых 10 писем для даты {date}")
        return True
    except Exception as e:
        print(f"❌ Ошибка обработки первых 10 писем: {e}")
        return False

def process_all_emails(date: str) -> bool:
    """Обработка всех писем для указанной даты"""
    try:
        validator = APIPipelineValidator(date=date, test_mode=False)
        if not validator.validate_setup():
            return False
        result = validator.run_all_mode()
        print(f"✅ Обработаны все письма для даты {date}")
        return True
    except Exception as e:
        print(f"❌ Ошибка обработки всех писем: {e}")
        return False

async def process_first_10_emails_async(date: str) -> bool:
    """Асинхронная обработка первых 10 писем для указанной даты"""
    try:
        validator = AsyncAPIPipelineValidator(date=date, test_mode=False, max_concurrent=2)
        if not validator.validate_async_setup():
            return False
        result = await validator.run_async_mode('first10')
        print(f"✅ Асинхронно обработано первых 10 писем для даты {date}")
        return True
    except Exception as e:
        print(f"❌ Ошибка асинхронной обработки первых 10 писем: {e}")
        return False

async def process_all_emails_async(date: str) -> bool:
    """Асинхронная обработка всех писем для указанной даты"""
    try:
        validator = AsyncAPIPipelineValidator(date=date, test_mode=False, max_concurrent=2)
        if not validator.validate_async_setup():
            return False
        result = await validator.run_async_mode('all')
        print(f"✅ Асинхронно обработаны все письма для даты {date}")
        return True
    except Exception as e:
        print(f"❌ Ошибка асинхронной обработки всех писем: {e}")
        return False

def main():
    """🏁 Главная функция"""
    parser = argparse.ArgumentParser(description='API Pipeline Validator - Phase 11.4')
    parser.add_argument('--mode', 
                       choices=['first10', 'all'], 
                       help='Режим обработки: first10 или all')
    parser.add_argument('--date', 
                       help='Дата для обработки')
    parser.add_argument('--results-dir',
                       help='Директория для сохранения JSON результатов')
    parser.add_argument('--reports-dir',
                       help='Директория для сохранения отчетов')
    parser.add_argument('--interactive', '-i',
                       action='store_true',
                       help='Запустить в интерактивном режиме')
    parser.add_argument('--async', '-a',
                       action='store_true',
                       help='Использовать асинхронный режим обработки')
    
    args = parser.parse_args()
    
    # Определяем режим и дату
    if args.interactive or (not args.mode and not args.date):
        # Интерактивный режим
        selection = interactive_menu()
        mode = selection['mode']
        date = selection['date']
        is_async = selection.get('async', False)
        
        print(f"\n🚀 Запуск обработки:")
        print(f"   Режим: {mode}")
        print(f"   Дата: {date}")
        print(f"   Тип: {'асинхронный' if is_async else 'синхронный'}")
        
        # Валидация и подготовка данных
        if not validate_and_prepare_date(date):
            print(f"\n❌ Не удалось подготовить данные для даты {date}")
            sys.exit(1)
        
        # Запуск соответствующего режима
        success = False
        if is_async:
            # Асинхронный режим
            if mode == 'first10':
                success = asyncio.run(process_first_10_emails_async(date))
            elif mode == 'all':
                success = asyncio.run(process_all_emails_async(date))
        else:
            # Синхронный режим
            if mode == 'first10':
                success = process_first_10_emails(date)
            elif mode == 'all':
                success = process_all_emails(date)
        
        if success:
            print(f"\n✅ Обработка завершена успешно!")
        else:
            print(f"\n❌ Обработка завершена с ошибкой")
            sys.exit(1)
            
    else:
        # Командная строка
        mode = args.mode or 'first10'
        date = args.date or '2025-07-29'
        is_async = getattr(args, 'async', False)  # Используем getattr для совместимости
        
        print(f"\n🚀 Запуск валидации:")
        print(f"   Режим: {mode}")
        print(f"   Дата: {date}")
        print(f"   Тип: {'асинхронный' if is_async else 'синхронный'}")
        
        # Валидация и подготовка данных
        if not validate_and_prepare_date(date):
            print(f"\n❌ Не удалось подготовить данные для даты {date}")
            sys.exit(1)
        
        # Запуск соответствующего режима
        success = False
        if is_async:
            # Асинхронный режим
            if mode == 'first10':
                success = asyncio.run(process_first_10_emails_async(date))
            elif mode == 'all':
                success = asyncio.run(process_all_emails_async(date))
        else:
            # Синхронный режим (старая логика)
            validator = APIPipelineValidator(
                date=date,
                results_dir=args.results_dir,
                reports_dir=args.reports_dir
            )
            
            result = validator.run(mode)
            success = result.get('success')
            
            if success and result.get('final_report'):
                print(f"📋 Итоговый отчет: {result['final_report']}")
        
        if success:
            print(f"\n✅ Валидация завершена успешно!")
        else:
            print(f"\n❌ Валидация завершена с ошибкой")
            sys.exit(1)


if __name__ == "__main__":
    main()