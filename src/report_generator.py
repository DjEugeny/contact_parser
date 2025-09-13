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
        
        # Формируем таблицу организаций
        organizations = llm_response.get('organizations', [])
        organizations_table = "\n| ID | Название | ИНН | Сайт | Город | Адрес | Email | Телефоны |\n"
        organizations_table += "|----|---------|----|-----|-------|-------|-------|----------|\n"
        
        if organizations:
            for org in organizations:
                org_id = org.get('organization_id', '')
                name = org.get('name', '')
                inn = org.get('inn', '') or 'Не указан'
                website = org.get('website', '') or 'Не указан'
                city = org.get('city', '') or 'Не указан'
                address = org.get('address', '') or 'Не указан'
                emails = ', '.join(org.get('emails', [])) or 'Не указаны'
                phones = ', '.join(org.get('phones', [])) or 'Не указаны'
                organizations_table += f"| {org_id} | {name} | {inn} | {website} | {city} | {address} | {emails} | {phones} |\n"
        else:
            organizations_table += "| - | - | - | - | - | - | - | - |\n"
        
        # Формируем таблицу контактов
        contacts = llm_response.get('contacts', [])
        contacts_table = "\n| ID | Имя | Орг.ID | Должность | Email | Телефоны | Город | Адрес | Уверенность |\n"
        contacts_table += "|----|----|-------|-----------|-------|----------|-------|-------|-------------|\n"
        
        if contacts:
            for contact in contacts:
                contact_id = contact.get('contact_id', '')
                name = contact.get('name', '')
                org_id = contact.get('organization_id', '')
                position = contact.get('position', '') or 'Не указана'
                email = contact.get('email', '') or 'Не указан'
                
                # Форматируем телефоны
                phones_data = contact.get('phones', [])
                if phones_data:
                    phones_str = ', '.join([f"{p.get('type', 'main')}: {p.get('number', '')}" for p in phones_data])
                else:
                    phones_str = 'Не указаны'
                
                city = contact.get('city', '') or 'Не указан'
                address = contact.get('address', '') or 'Не указан'
                confidence = contact.get('confidence', 0)
                
                contacts_table += f"| {contact_id} | {name} | {org_id} | {position} | {email} | {phones_str} | {city} | {address} | {confidence:.2f} |\n"
        else:
            contacts_table += "| - | - | - | - | - | - | - | - | - |\n"
        
        # Формируем таблицу коммерческих предложений
        commercial_offers = llm_response.get('commercial_offers', [])
        offers_section = "\n"
        
        if commercial_offers:
            for i, offer in enumerate(commercial_offers, 1):
                if offer.get('found', False):
                    offers_section += f"### КП #{i}\n\n"
                    offers_section += f"- **Номер КП:** {offer.get('offer_number', 'Не указан')}\n"
                    offers_section += f"- **Дата КП:** {offer.get('offer_date', 'Не указана')}\n"
                    offers_section += f"- **Конечный заказчик:** {offer.get('end_user', 'Не указан')}\n"
                    offers_section += f"- **ИНН заказчика:** {offer.get('end_user_inn', 'Не указан')}\n"
                    offers_section += f"- **Посредник:** {offer.get('intermediary', 'Не указан')}\n"
                    offers_section += f"- **Данные посредника:** {offer.get('intermediary_data', 'Не указаны')}\n"
                    offers_section += f"- **Условия оплаты:** {offer.get('payment_terms', 'Не указаны')}\n"
                    offers_section += f"- **Срок поставки:** {offer.get('delivery_time', 'Не указан')}\n"
                    offers_section += f"- **Условия поставки:** {offer.get('delivery_terms', 'Не указаны')}\n"
                    offers_section += f"- **Действительно до:** {offer.get('valid_until', 'Не указано')}\n"
                    offers_section += f"- **Общая стоимость:** {offer.get('total_cost', 'Не указана')} руб.\n"
                    
                    equipment_items = offer.get('equipment_items', [])
                    if equipment_items:
                        offers_section += f"\n**Позиции оборудования ({len(equipment_items)} шт.):**\n\n"
                        offers_section += "| Название | Модель | Артикул | Кол-во | Цена за ед. | Общая цена | НДС |\n"
                        offers_section += "|----------|--------|---------|--------|-------------|------------|-----|\n"
                        for item in equipment_items:
                            offers_section += f"| {item.get('name', '')} | {item.get('model', '')} | {item.get('article', '')} | {item.get('quantity', '')} | {item.get('unit_price', '')} | {item.get('total_price', '')} | {item.get('vat', '')} |\n"
                    
                    comments = offer.get('comments', '')
                    if comments:
                        offers_section += f"\n**Комментарии:** {comments}\n"
                    
                    offers_section += "\n"
        else:
            offers_section += "❌ **Коммерческие предложения не найдены**\n\n"
        
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

## Извлеченные организации
{organizations_table}

## Извлеченные контакты
{contacts_table}

## Коммерческие предложения
{offers_section}

## Бизнес-контекст

- **Компания:** {llm_response.get('business_context', {}).get('company_name', 'Не определено')}
- **Отрасль:** {llm_response.get('business_context', {}).get('industry', 'Не определено')}
- **Тип запроса:** {llm_response.get('business_context', {}).get('request_type', 'Не определено')}

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
        
        # Статистика по организациям
        organizations_found = len([r for r in results if r.get('success', False) and r.get('llm_response', {}).get('organizations')])
        orgs_with_inn = len([r for r in results if r.get('success', False) and any(org.get('inn') for org in r.get('llm_response', {}).get('organizations', []))])
        orgs_with_website = len([r for r in results if r.get('success', False) and any(org.get('website') for org in r.get('llm_response', {}).get('organizations', []))])
        orgs_with_emails = len([r for r in results if r.get('success', False) and any(org.get('emails') for org in r.get('llm_response', {}).get('organizations', []))])
        
        # Статистика по контактам
        contacts_found = len([r for r in results if r.get('success', False) and r.get('llm_response', {}).get('contacts')])
        contacts_with_phones = len([r for r in results if r.get('success', False) and any(c.get('phones') for c in r.get('llm_response', {}).get('contacts', []))])
        contacts_with_emails = len([r for r in results if r.get('success', False) and any(c.get('email') for c in r.get('llm_response', {}).get('contacts', []))])
        contacts_with_position = len([r for r in results if r.get('success', False) and any(c.get('position') for c in r.get('llm_response', {}).get('contacts', []))])
        
        # Статистика по коммерческим предложениям
        commercial_offers_found = len([r for r in results if r.get('success', False) and any(offer.get('found', False) for offer in r.get('llm_response', {}).get('commercial_offers', []))])
        
        # Формируем сводный отчет
        report = f"""# Сводный отчет полномасштабного тестирования

**Prompt:** {prompt_file}
**Дата тестирования:** {datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')}
**Всего тестов:** {total_tests}

## Общая статистика

- ✅ **Успешных тестов:** {successful_tests}/{total_tests} ({(successful_tests/total_tests*100):.1f}%)
- ❌ **Неудачных тестов:** {failed_tests}/{total_tests} ({(failed_tests/total_tests*100):.1f}%)
- 📊 **Средний балл:** {avg_score:.1f}/{max_possible_score} ({avg_percentage:.1f}%)

## Статистика извлечения организаций

- 🏢 **Письма с организациями:** {organizations_found}/{successful_tests} ({(organizations_found/successful_tests*100):.1f}%)
- 🏛️ **Организации с ИНН:** {orgs_with_inn}/{successful_tests} ({(orgs_with_inn/successful_tests*100):.1f}%)
- 🌐 **Организации с сайтами:** {orgs_with_website}/{successful_tests} ({(orgs_with_website/successful_tests*100):.1f}%)
- 📧 **Организации с email:** {orgs_with_emails}/{successful_tests} ({(orgs_with_emails/successful_tests*100):.1f}%)

## Статистика извлечения контактов

- 👥 **Письма с контактами:** {contacts_found}/{successful_tests} ({(contacts_found/successful_tests*100):.1f}%)
- 📞 **Контакты с телефонами:** {contacts_with_phones}/{successful_tests} ({(contacts_with_phones/successful_tests*100):.1f}%)
- 📧 **Контакты с email:** {contacts_with_emails}/{successful_tests} ({(contacts_with_emails/successful_tests*100):.1f}%)
- 💼 **Контакты с должностями:** {contacts_with_position}/{successful_tests} ({(contacts_with_position/successful_tests*100):.1f}%)

## Статистика коммерческих предложений

- 💰 **Письма с КП:** {commercial_offers_found}/{successful_tests} ({(commercial_offers_found/successful_tests*100):.1f}%)

## Детальные результаты

| № | Email файл | Статус | Балл | Организации | Контакты | КП | Телефоны | Email |
|---|------------|--------|------|-------------|----------|----|---------|---------|
"""
        
        # Добавляем строки таблицы
        for i, result in enumerate(results, 1):
            if result.get('success', False):
                evaluation = result.get('evaluation', {})
                llm_response = result.get('llm_response', {})
                organizations = llm_response.get('organizations', [])
                contacts = llm_response.get('contacts', [])
                commercial_offers = llm_response.get('commercial_offers', [])
                
                has_organizations = "✅" if organizations else "❌"
                has_contacts = "✅" if contacts else "❌"
                has_commercial_offers = "✅" if any(offer.get('found', False) for offer in commercial_offers) else "❌"
                has_phones = "✅" if any(c.get('phones') for c in contacts) else "❌"
                has_emails = "✅" if any(c.get('email') for c in contacts) else "❌"
                
                score = evaluation.get('score', 0)
                status = "✅ Успех"
            else:
                has_organizations = has_contacts = has_commercial_offers = has_phones = has_emails = "❌"
                score = 0
                status = "❌ Ошибка"
            
            email_file = result.get('email_file', 'Unknown')
            report += f"| {i} | {email_file} | {status} | {score}/10 | {has_organizations} | {has_contacts} | {has_commercial_offers} | {has_phones} | {has_emails} |\n"
        
        # Добавляем рекомендации
        report += f"\n## Рекомендации\n\n"
        
        if avg_percentage >= 80:
            report += "✅ **Отличные результаты!** Промпт показывает высокую эффективность.\n\n"
        elif avg_percentage >= 60:
            report += "⚠️ **Хорошие результаты** с возможностями для улучшения.\n\n"
        else:
            report += "❌ **Требуется доработка** промпта для повышения эффективности.\n\n"
        
        if orgs_with_inn / successful_tests < 0.5:
            report += "- 🔍 **Улучшить распознавание ИНН** - найдено только в {:.0f}% случаев\n".format(orgs_with_inn/successful_tests*100)
        
        if contacts_with_phones / successful_tests < 0.7:
            report += "- 📞 **Улучшить извлечение телефонов** - найдено только в {:.0f}% случаев\n".format(contacts_with_phones/successful_tests*100)
        
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

## Извлеченные организации

"""
        
        organizations = llm_response.get('organizations', [])
        if organizations:
            report += "| Название | ИНН | Сайт | Email | Адрес |\n"
            report += "|----------|-----|------|-------|-------|\n"
            
            for org in organizations:
                name = org.get('name', 'Не указано')
                inn = org.get('inn', 'Не указано')
                website = org.get('website', 'Не указано')
                email = org.get('email', 'Не указано')
                address = org.get('address', 'Не указано')
                
                report += f"| {name} | {inn} | {website} | {email} | {address} |\n"
        else:
            report += "❌ **Организации не найдены**\n\n"
        
        report += "\n## Извлеченные контакты\n\n"
        
        contacts = llm_response.get('contacts', [])
        if contacts:
            report += "| Имя | Должность | Организация | Телефоны | Email |\n"
            report += "|-----|-----------|-------------|----------|-------|\n"
            
            for contact in contacts:
                name = contact.get('name', 'Не указано')
                position = contact.get('position', 'Не указано')
                organization = contact.get('organization', 'Не указано')
                phones = ', '.join(contact.get('phones', [])) if contact.get('phones') else 'Не указано'
                email = contact.get('email', 'Не указано')
                
                report += f"| {name} | {position} | {organization} | {phones} | {email} |\n"
        else:
            report += "❌ **Контакты не найдены**\n\n"
        
        # Бизнес-контекст
        business_context = llm_response.get('business_context', {})
        report += f"""\n## Бизнес-контекст

- **Компания:** {business_context.get('company_name', 'Не указано')}
- **Отрасль:** {business_context.get('industry', 'Не указано')}
- **Тип запроса:** {business_context.get('request_type', 'Не указано')}

"""
        
        # Коммерческие предложения
        commercial_offers = llm_response.get('commercial_offers', [])
        report += "\n## Коммерческие предложения\n\n"
        
        if commercial_offers:
            for i, offer in enumerate(commercial_offers, 1):
                found = "✅ Найдено" if offer.get('found', False) else "❌ Не найдено"
                description = offer.get('description', 'Описание отсутствует')
                report += f"**Предложение {i}:**\n"
                report += f"- **Статус:** {found}\n"
                report += f"- **Описание:** {description}\n\n"
        else:
            report += "❌ **Коммерческие предложения не найдены**\n\n"
        
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