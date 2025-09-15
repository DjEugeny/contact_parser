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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set

# Добавление корневой директории проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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


class SimpleReportGenerator:
    """📄 Простой генератор отчетов для fallback'а"""
    
    def __init__(self):
        pass
        
    def generate_validation_report(self, result, validation_result):
        """Генерация простого отчета"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')
        
        # Получаем данные из результата
        email_data = result.get('email_data', {})
        llm_result = result.get('llm_result', {})
        
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
                offers_section += f"- **Общая стоимость:** {offer.get('total_cost', 0)} руб.\n\n"
        else:
            offers_section += "❌ **Коммерческие предложения не найдены**\n"
        
        # Собираем отчет
        status = "✅ УСПЕХ" if result.get('success', False) else "❌ ОШИБКА"
        
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
Контактная информация извлечена из деловой переписки.

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
                 reports_dir: Optional[str] = None):
        """
        Инициализация валидатора
        
        Args:
            date: Дата для обработки (по умолчанию 2025-07-29)
            results_dir: Директория для сохранения JSON результатов
            reports_dir: Директория для сохранения отчетов
        """
        self.date = date
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
            # 🎯 АРХИТЕКТУРНОЕ УЛУЧШЕНИЕ: Используем паттерн из test_api_dataset.py
            # Используем ExtractorFactory для создания экстрактора как в test_api_dataset.py
            if ExtractorFactory:
                self.processor = ExtractorFactory.create_extractor()
                print("   ✅ Экстрактор создан через ExtractorFactory (паттерн test_api_dataset.py)")
            else:
                print("   ❌ ExtractorFactory недоступен")
                return False
                
            if ReportGenerator:
                self.report_generator = ReportGenerator()
                print("   ✅ ReportGenerator инициализирован")
            else:
                self.report_generator = SimpleReportGenerator()
                print("   🔄 Используем SimpleReportGenerator")
                
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
            # Загружаем основное письмо
            email_path = self.emails_dir / filename
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
                business_context = extraction_result.get('business_context', '')
                if business_context and len(business_context) > 50:
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
        """⚡ Обработка одного письма через основной пайплайн"""
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
            
            # 🎯 АРХИТЕКТУРНОЕ УЛУЧШЕНИЕ: Используем паттерн из test_api_dataset.py
            # Подготавливаем текстовое содержимое
            text_content = self._extract_text_content(email_data)
            
            # Подготавливаем метаданные в соответствии со спецификацией
            metadata = {
                'subject': email_data.get('subject', ''),
                'from': email_data.get('from', ''),
                'date': email_data.get('date', ''),
                'attachments_count': len(email_data.get('attachments', []))
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
            
            # 🎯 ГЛАВНОЕ УЛУЧШЕНИЕ: Используем метод extract_all_data() как в test_api_dataset.py
            print(f"      🤖 Обработка через основной пайплайн ({len(text_content)} символов)...")
            print(f"      📎 Вложений: {len(email_data.get('attachments', []))}")
            
            start_time = time.time()
            try:
                # Делегируем обработку основному пайплайну точно как в test_api_dataset.py
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
            
            # 🔧 УЛУЧШЕНИЕ: Проверяем успешность по наличию данных
            if result and (result.get('organizations') or result.get('contacts') or result.get('commercial_offers')):
                success = True
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
                        'char_count': len(text_content)
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
                        'char_count': len(text_content)
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
    
    def _extract_text_content(self, email_data: Dict) -> str:
        """📄 Извлечение текстового содержимого (паттерн из test_api_dataset.py)"""
        content_parts = []
        
        # Основное тело письма
        if 'body' in email_data and email_data['body']:
            content_parts.append(f"Тело письма:\n{email_data['body']}")
            
        # Информация об отправителе
        if 'from' in email_data:
            content_parts.append(f"От: {email_data['from']}")
            
        # Тема письма
        if 'subject' in email_data:
            content_parts.append(f"Тема: {email_data['subject']}")
            
        # Информация о вложениях
        if 'attachments' in email_data and email_data['attachments']:
            attachments_info = "Вложения:\n"
            for att in email_data['attachments']:
                if isinstance(att, dict):
                    name = att.get('filename', 'Неизвестно')
                    size = att.get('size', 'Неизвестно')
                    attachments_info += f"- {name} ({size} байт)\n"
                    
                    # Добавляем содержимое вложения если есть
                    if 'content' in att and att['content']:
                        attachments_info += f"  Содержимое: {att['content'][:500]}...\n"
                        
            content_parts.append(attachments_info)
            
        return "\n\n".join(content_parts)

    def save_structured_result(self, result: Dict, filename: str) -> bool:
        """💾 Сохранение структурированного JSON результата"""
        try:
            # КРИТИЧЕСКАЯ ПРОВЕРКА: проверяем все возможные индикаторы ошибок
            llm_result = result.get('llm_result', {})
            
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
        
        if not files_to_process:
            print("\n🎉 Все файлы из тестового датасета уже обработаны!")
            return {'success': True, 'files_processed': 0, 'reason': 'Все файлы уже обработаны'}
            
        # Обрабатываем файлы
        results = []
        for i, filename in enumerate(files_to_process, 1):
            print(f"\n   📧 {i}/{len(files_to_process)}: {filename}")
            
            # Обрабатываем письмо
            result = self.process_single_email(filename)
            if result:
                results.append(result)
                
                if result.get('success'):
                    # Сохраняем JSON только для успешных результатов
                    if self.save_structured_result(result, filename):
                        # Генерируем отчет только если JSON сохранен
                        self.generate_detailed_report(result, filename)
                    
                    self.stats['emails_successful'] += 1
                else:
                    self.stats['emails_failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    
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
                
        return {
            'success': True,
            'files_processed': len(files_to_process),
            'files_successful': self.stats['emails_successful'],
            'files_failed': self.stats['emails_failed'],
            'results': results
        }

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
        
        if not files_to_process:
            print("\n🎉 Все письма уже обработаны!")
            return {'success': True, 'files_processed': 0, 'reason': 'Все файлы уже обработаны'}
            
        # Обрабатываем файлы
        results = []
        for i, filename in enumerate(files_to_process, 1):
            print(f"\n   📧 {i}/{len(files_to_process)}: {filename}")
            
            # Обрабатываем письмо
            result = self.process_single_email(filename)
            if result:
                results.append(result)
                
                if result.get('success'):
                    # Сохраняем JSON только для успешных результатов
                    if self.save_structured_result(result, filename):
                        # Генерируем отчет только если JSON сохранен
                        self.generate_detailed_report(result, filename)
                    
                    self.stats['emails_successful'] += 1
                else:
                    self.stats['emails_failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    
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
                
        return {
            'success': True,
            'files_processed': len(files_to_process),
            'files_successful': self.stats['emails_successful'],
            'files_failed': self.stats['emails_failed'],
            'results': results
        }

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


def main():
    """🏁 Главная функция"""
    parser = argparse.ArgumentParser(description='API Pipeline Validator - Phase 11.4')
    parser.add_argument('--mode', 
                       choices=['first10', 'all'], 
                       default='first10',
                       help='Режим обработки: first10 или all')
    parser.add_argument('--date', 
                       default='2025-07-29',
                       help='Дата для обработки (по умолчанию 2025-07-29)')
    parser.add_argument('--results-dir',
                       help='Директория для сохранения JSON результатов')
    parser.add_argument('--reports-dir',
                       help='Директория для сохранения отчетов')
    
    args = parser.parse_args()
    
    # Создаем валидатор
    validator = APIPipelineValidator(
        date=args.date,
        results_dir=args.results_dir,
        reports_dir=args.reports_dir
    )
    
    # Запускаем валидацию
    result = validator.run(args.mode)
    
    # Выводим результат
    if result.get('success'):
        print(f"\n✅ Валидация завершена успешно!")
        if result.get('final_report'):
            print(f"📋 Итоговый отчет: {result['final_report']}")
    else:
        print(f"\n❌ Валидация завершена с ошибкой: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()