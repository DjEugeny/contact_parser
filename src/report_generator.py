#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации отчетов тестирования промптов в markdown формате

Автор: IMPLEMENT агент
Дата: 09.09.2025
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

class ReportGenerator:
    """Класс для генерации отчетов тестирования"""
    
    def __init__(self, reports_dir: str = "/Users/evgenyzach/contact_parser/memory-bank/reports"):
        """Инициализация генератора отчетов"""
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_single_email_report(self, result: Dict[str, Any]) -> str:
        """Генерировать отчет для одного письма"""
        
        if not result.get('success', False):
            return f"""# Ошибка тестирования

**Email:** {result.get('email_file', 'Unknown')}
**Prompt:** {result.get('prompt_file', 'Unknown')}
**Время:** {result.get('timestamp', 'Unknown')}

## Ошибка
```
{result.get('error', 'Неизвестная ошибка')}
```
"""
        
        email_meta = result.get('email_metadata', {})
        llm_response = result.get('llm_response', {})
        evaluation = result.get('evaluation', {})
        
        # Формируем таблицу контактов
        contacts_table = "\n| Имя | Должность | Компания | Телефон | Email | ИНН | Сайт |\n"
        contacts_table += "|-----|-----------|----------|---------|-------|-----|------|\n"
        
        contacts = llm_response.get('contacts', [])
        if contacts:
            for contact in contacts:
                contacts_table += f"| {contact.get('name', '')} | {contact.get('position', '')} | {contact.get('company', '')} | {contact.get('phone', '')} | {contact.get('email', '')} | {contact.get('inn', '')} | {contact.get('website', '')} |\n"
        else:
            contacts_table += "| - | - | - | - | - | - | - |\n"
        
        # Формируем отчет
        report = f"""# Отчет тестирования: {result['email_file']}

**Prompt:** {result['prompt_file']}
**Время тестирования:** {result['timestamp']}
**Оценка:** {evaluation.get('score', 0)}/{evaluation.get('max_score', 10)} ({evaluation.get('percentage', 0):.1f}%)

## Метаданные письма

- **От:** {email_meta.get('from', 'Не указано')}
- **Тема:** {email_meta.get('subject', 'Не указано')}
- **Дата:** {email_meta.get('date', 'Не указано')}
- **Вложения:** {email_meta.get('attachments_count', 0)}

## Извлеченные контакты
{contacts_table}

## Бизнес-контекст

- **Компания:** {llm_response.get('business_context', {}).get('company_name', 'Не определено')}
- **Отрасль:** {llm_response.get('business_context', {}).get('industry', 'Не определено')}
- **Тип запроса:** {llm_response.get('business_context', {}).get('request_type', 'Не определено')}

## Коммерческое предложение

- **Продукты/услуги:** {', '.join(llm_response.get('commercial_proposal', {}).get('products', []))}
- **Сумма:** {llm_response.get('commercial_proposal', {}).get('total_amount', 'Не указано')}
- **Валюта:** {llm_response.get('commercial_proposal', {}).get('currency', 'RUB')}

## Детали оценки

"""
        
        # Добавляем детали оценки
        for detail in evaluation.get('evaluation_details', []):
            report += f"- {detail}\n"
        
        # Добавляем метаданные обработки
        metadata = llm_response.get('metadata', {})
        if metadata:
            report += f"\n## Метаданные обработки\n\n"
            report += f"- **Уверенность:** {metadata.get('confidence_score', 'Не указано')}\n"
            report += f"- **Заметки:** {metadata.get('processing_notes', 'Нет заметок')}\n"
        
        return report
    
    def generate_summary_report(self, results: List[Dict[str, Any]], prompt_file: str) -> str:
        """Генерировать сводный отчет по всем результатам"""
        
        total_tests = len(results)
        successful_tests = len([r for r in results if r.get('success', False)])
        failed_tests = total_tests - successful_tests
        
        # Подсчет статистики
        scores = [r.get('evaluation', {}).get('score', 0) for r in results if r.get('success', False)]
        avg_score = sum(scores) / len(scores) if scores else 0
        max_possible_score = 10
        avg_percentage = (avg_score / max_possible_score) * 100 if max_possible_score > 0 else 0
        
        # Статистика по типам данных
        contacts_found = len([r for r in results if r.get('success', False) and r.get('llm_response', {}).get('contacts')])
        inn_found = len([r for r in results if r.get('success', False) and any(c.get('inn') for c in r.get('llm_response', {}).get('contacts', []))])
        phones_found = len([r for r in results if r.get('success', False) and any(c.get('phone') for c in r.get('llm_response', {}).get('contacts', []))])
        emails_found = len([r for r in results if r.get('success', False) and any(c.get('email') for c in r.get('llm_response', {}).get('contacts', []))])
        
        # Формируем сводный отчет
        report = f"""# Сводный отчет полномасштабного тестирования

**Prompt:** {prompt_file}
**Дата тестирования:** {datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')}
**Всего тестов:** {total_tests}

## Общая статистика

- ✅ **Успешных тестов:** {successful_tests}/{total_tests} ({(successful_tests/total_tests*100):.1f}%)
- ❌ **Неудачных тестов:** {failed_tests}/{total_tests} ({(failed_tests/total_tests*100):.1f}%)
- 📊 **Средний балл:** {avg_score:.1f}/{max_possible_score} ({avg_percentage:.1f}%)

## Статистика извлечения данных

- 👥 **Письма с контактами:** {contacts_found}/{successful_tests} ({(contacts_found/successful_tests*100):.1f}%)
- 🏢 **Письма с ИНН:** {inn_found}/{successful_tests} ({(inn_found/successful_tests*100):.1f}%)
- 📞 **Письма с телефонами:** {phones_found}/{successful_tests} ({(phones_found/successful_tests*100):.1f}%)
- 📧 **Письма с email:** {emails_found}/{successful_tests} ({(emails_found/successful_tests*100):.1f}%)

## Детальные результаты

| № | Email файл | Статус | Балл | Контакты | ИНН | Телефон | Email |
|---|------------|--------|------|----------|-----|---------|-------|
"""
        
        # Добавляем строки таблицы
        for i, result in enumerate(results, 1):
            if result.get('success', False):
                evaluation = result.get('evaluation', {})
                llm_response = result.get('llm_response', {})
                contacts = llm_response.get('contacts', [])
                
                has_contacts = "✅" if contacts else "❌"
                has_inn = "✅" if any(c.get('inn') for c in contacts) else "❌"
                has_phone = "✅" if any(c.get('phone') for c in contacts) else "❌"
                has_email = "✅" if any(c.get('email') for c in contacts) else "❌"
                
                score = evaluation.get('score', 0)
                status = "✅ Успех"
            else:
                has_contacts = has_inn = has_phone = has_email = "❌"
                score = 0
                status = "❌ Ошибка"
            
            email_file = result.get('email_file', 'Unknown')
            report += f"| {i} | {email_file} | {status} | {score}/10 | {has_contacts} | {has_inn} | {has_phone} | {has_email} |\n"
        
        # Добавляем рекомендации
        report += f"\n## Рекомендации\n\n"
        
        if avg_percentage >= 80:
            report += "✅ **Отличные результаты!** Промпт показывает высокую эффективность.\n\n"
        elif avg_percentage >= 60:
            report += "⚠️ **Хорошие результаты** с возможностями для улучшения.\n\n"
        else:
            report += "❌ **Требуется доработка** промпта для повышения эффективности.\n\n"
        
        if inn_found / successful_tests < 0.5:
            report += "- 🔍 **Улучшить распознавание ИНН** - найдено только в {:.0f}% случаев\n".format(inn_found/successful_tests*100)
        
        if phones_found / successful_tests < 0.7:
            report += "- 📞 **Улучшить извлечение телефонов** - найдено только в {:.0f}% случаев\n".format(phones_found/successful_tests*100)
        
        if contacts_found / successful_tests < 0.8:
            report += "- 👥 **Улучшить извлечение контактов** - найдено только в {:.0f}% случаев\n".format(contacts_found/successful_tests*100)
        
        return report
    
    def generate_detailed_email_report(self, result: Dict[str, Any]) -> str:
        """Генерировать детальный отчет для одного письма"""
        
        if not result.get('success', False):
            return f"""# Детальный отчет - Ошибка тестирования

**Email:** {result.get('email_file', 'Unknown')}
**Prompt:** {result.get('prompt_file', 'Unknown')}
**Время:** {result.get('timestamp', 'Unknown')}

## Ошибка
```
{result.get('error', 'Неизвестная ошибка')}
```
"""
        
        email_meta = result.get('email_metadata', {})
        llm_response = result.get('llm_response', {})
        evaluation = result.get('evaluation', {})
        
        report = f"""# Детальный отчет анализа письма

**Email файл:** {result.get('email_file', 'Unknown')}
**Промпт:** {result.get('prompt_file', 'Unknown')}
**Время анализа:** {result.get('timestamp', 'Unknown')}

## Метаданные письма

- **От:** {email_meta.get('from', 'Не указано')}
- **Тема:** {email_meta.get('subject', 'Не указано')}
- **Дата:** {email_meta.get('date', 'Не указано')}
- **Количество вложений:** {email_meta.get('attachments_count', 0)}

## Извлеченные контакты

"""
        
        contacts = llm_response.get('contacts', [])
        if contacts:
            report += "| Имя | Должность | Компания | Телефон | Email | ИНН | Сайт |\n"
            report += "|-----|-----------|----------|---------|-------|-----|------|\n"
            
            for contact in contacts:
                name = contact.get('name', 'Не указано')
                position = contact.get('position', 'Не указано')
                company = contact.get('company', 'Не указано')
                phone = contact.get('phone', 'Не указано')
                email = contact.get('email', 'Не указано')
                inn = contact.get('inn', 'Не указано')
                website = contact.get('website', 'Не указано')
                
                report += f"| {name} | {position} | {company} | {phone} | {email} | {inn} | {website} |\n"
        else:
            report += "❌ **Контакты не найдены**\n\n"
        
        # Бизнес-контекст
        business_context = llm_response.get('business_context', {})
        report += f"""\n## Бизнес-контекст

- **Компания:** {business_context.get('company_name', 'Не указано')}
- **Отрасль:** {business_context.get('industry', 'Не указано')}
- **Тип запроса:** {business_context.get('request_type', 'Не указано')}

"""
        
        # Коммерческое предложение
        commercial = llm_response.get('commercial_proposal', {})
        report += f"""## Коммерческое предложение

- **Продукты/услуги:** {len(commercial.get('products', []))} позиций
- **Общая сумма:** {commercial.get('total_amount', 'Не указано')}
- **Валюта:** {commercial.get('currency', 'Не указано')}

"""
        
        # Оценка качества
        report += f"""## Оценка качества

- **Общий балл:** {evaluation.get('score', 0)}/{evaluation.get('max_score', 10)}
- **Процент успеха:** {evaluation.get('percentage', 0):.1f}%

### Детали оценки:
"""
        
        for detail in evaluation.get('evaluation_details', []):
            report += f"- {detail}\n"
        
        return report
    
    def save_report(self, content: str, filename: str) -> str:
        """Сохранить отчет в файл"""
        
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    def update_index(self, new_report_filename: str, description: str):
        """Обновить индексный файл отчетов"""
        
        index_path = self.reports_dir / "index.md"
        
        # Читаем существующий индекс или создаем новый
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# Индекс отчетов\n\n"
        
        # Добавляем новую запись в конец
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')
        new_entry = f"- [{description}]({new_report_filename}) - {timestamp}\n"
        content += new_entry
        
        # Сохраняем обновленный индекс
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)