#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор отчетов для тестирования промптов извлечения контактов.
Создает .md файлы с результатами анализа в удобном для чтения формате.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class PromptTestReporter:
    """Генератор отчетов для результатов тестирования промптов."""
    
    def __init__(self, template_path: str = None):
        """Инициализация репортера.
        
        Args:
            template_path: Путь к шаблону отчета
        """
        self.template_path = template_path or "/Users/evgenyzach/contact_parser/memory-bank/prompt_test_result_template.md"
        self.template = self._load_template()
    
    def _load_template(self) -> str:
        """Загружает шаблон отчета."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Возвращает базовый шаблон отчета."""
        return """
# Результаты тестирования промпта

**Дата:** {date}
**Промпт:** {prompt_name}
**Писем:** {total_emails}

## Статистика
- Контакты: {contacts_extracted}/{total_emails}
- JSON валидность: {valid_json}/{total_emails}

## Детали
{detailed_results}
"""
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализирует результаты тестирования.
        
        Args:
            results: Список результатов для каждого письма
            
        Returns:
            Словарь с агрегированной статистикой
        """
        total = len(results)
        stats = {
            'total_emails': total,
            'contacts_extracted': 0,
            'phones_found': 0,
            'emails_found': 0,
            'inn_found': 0,
            'websites_found': 0,
            'valid_json': 0,
            'structured_output': 0,
            'complete_fields': 0,
            'errors': [],
            'best_result': None,
            'worst_result': None
        }
        
        best_score = -1
        worst_score = 11
        
        for result in results:
            # Анализ извлеченных данных
            extracted_data = result.get('extracted_data', {})
            
            if extracted_data:
                stats['contacts_extracted'] += 1
                
                # Проверка наличия различных типов данных
                if self._has_phones(extracted_data):
                    stats['phones_found'] += 1
                if self._has_emails(extracted_data):
                    stats['emails_found'] += 1
                if self._has_inn(extracted_data):
                    stats['inn_found'] += 1
                if self._has_websites(extracted_data):
                    stats['websites_found'] += 1
            
            # Проверка качества JSON
            if result.get('json_valid', False):
                stats['valid_json'] += 1
            if result.get('structured', False):
                stats['structured_output'] += 1
            if result.get('complete_fields', False):
                stats['complete_fields'] += 1
            
            # Сбор ошибок
            if result.get('error'):
                stats['errors'].append(result['error'])
            
            # Поиск лучшего и худшего результата
            score = self._calculate_score(result)
            if score > best_score:
                best_score = score
                stats['best_result'] = result
            if score < worst_score:
                worst_score = score
                stats['worst_result'] = result
        
        # Вычисление процентов
        for key in ['contacts_extracted', 'phones_found', 'emails_found', 
                   'inn_found', 'websites_found', 'valid_json', 
                   'structured_output', 'complete_fields']:
            stats[f'{key}_percentage'] = round((stats[key] / total) * 100, 1) if total > 0 else 0
        
        return stats
    
    def _has_phones(self, data: Dict) -> bool:
        """Проверяет наличие телефонов в данных."""
        phones = data.get('phones', [])
        return bool(phones and any(phone.strip() for phone in phones))
    
    def _has_emails(self, data: Dict) -> bool:
        """Проверяет наличие email в данных."""
        emails = data.get('emails', [])
        return bool(emails and any(email.strip() for email in emails))
    
    def _has_inn(self, data: Dict) -> bool:
        """Проверяет наличие ИНН в данных."""
        inn = data.get('inn', '')
        return bool(inn and inn.strip())
    
    def _has_websites(self, data: Dict) -> bool:
        """Проверяет наличие сайтов в данных."""
        websites = data.get('websites', [])
        return bool(websites and any(site.strip() for site in websites))
    
    def _calculate_score(self, result: Dict) -> float:
        """Вычисляет общий балл для результата."""
        score = 0
        
        if result.get('json_valid'):
            score += 2
        if result.get('structured'):
            score += 2
        if result.get('complete_fields'):
            score += 2
        
        extracted = result.get('extracted_data', {})
        if extracted:
            score += 1
            if self._has_phones(extracted):
                score += 1
            if self._has_emails(extracted):
                score += 1
            if self._has_inn(extracted):
                score += 1
        
        return score
    
    def generate_detailed_results(self, results: List[Dict[str, Any]]) -> str:
        """Генерирует детальные результаты по каждому письму."""
        detailed = []
        
        for i, result in enumerate(results, 1):
            email_file = result.get('email_file', f'email_{i:03d}')
            score = self._calculate_score(result)
            
            detail = f"### {i}. {email_file}\n"
            detail += f"**Балл:** {score}/10\n"
            
            if result.get('json_valid'):
                detail += "✅ JSON валидный\n"
            else:
                detail += "❌ JSON невалидный\n"
            
            extracted = result.get('extracted_data', {})
            if extracted:
                detail += "**Извлечено:**\n"
                if self._has_phones(extracted):
                    phones = ', '.join(extracted.get('phones', []))
                    detail += f"- Телефоны: {phones}\n"
                if self._has_emails(extracted):
                    emails = ', '.join(extracted.get('emails', []))
                    detail += f"- Email: {emails}\n"
                if self._has_inn(extracted):
                    detail += f"- ИНН: {extracted.get('inn')}\n"
                if self._has_websites(extracted):
                    websites = ', '.join(extracted.get('websites', []))
                    detail += f"- Сайты: {websites}\n"
            else:
                detail += "❌ Данные не извлечены\n"
            
            if result.get('error'):
                detail += f"**Ошибка:** {result['error']}\n"
            
            detail += "\n"
            detailed.append(detail)
        
        return ''.join(detailed)
    
    def generate_error_analysis(self, stats: Dict[str, Any]) -> str:
        """Генерирует анализ ошибок."""
        errors = stats.get('errors', [])
        if not errors:
            return "Критических ошибок не обнаружено."
        
        # Группировка ошибок по типам
        error_types = {}
        for error in errors:
            error_type = type(error).__name__ if isinstance(error, Exception) else str(error)[:50]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        analysis = "**Типы ошибок:**\n"
        for error_type, count in error_types.items():
            analysis += f"- {error_type}: {count} раз\n"
        
        return analysis
    
    def generate_recommendations(self, stats: Dict[str, Any]) -> str:
        """Генерирует рекомендации по улучшению."""
        recommendations = []
        
        if stats['contacts_extracted_percentage'] < 80:
            recommendations.append("- Улучшить алгоритм извлечения контактов")
        
        if stats['valid_json_percentage'] < 90:
            recommendations.append("- Добавить валидацию JSON в промпт")
        
        if stats['phones_found_percentage'] < 70:
            recommendations.append("- Улучшить распознавание телефонных номеров")
        
        if stats['inn_found_percentage'] < 60:
            recommendations.append("- Добавить более точные паттерны для ИНН")
        
        if not recommendations:
            recommendations.append("- Промпт показывает хорошие результаты")
        
        return '\n'.join(recommendations)
    
    def format_example(self, result: Dict[str, Any]) -> str:
        """Форматирует пример результата."""
        if not result:
            return "Нет данных"
        
        example = f"**Файл:** {result.get('email_file', 'unknown')}\n"
        example += f"**Балл:** {self._calculate_score(result)}/10\n"
        
        extracted = result.get('extracted_data', {})
        if extracted:
            example += "**Извлеченные данные:**\n"
            example += f"```json\n{json.dumps(extracted, ensure_ascii=False, indent=2)}\n```\n"
        
        return example
    
    def generate_report(self, 
                      results: List[Dict[str, Any]], 
                      prompt_name: str,
                      dataset_name: str = "test_dataset_10_emails",
                      output_path: str = None) -> str:
        """Генерирует полный отчет.
        
        Args:
            results: Результаты тестирования
            prompt_name: Название промпта
            dataset_name: Название тестовой выборки
            output_path: Путь для сохранения отчета
            
        Returns:
            Путь к созданному файлу отчета
        """
        stats = self.analyze_results(results)
        
        # Подготовка данных для шаблона
        template_data = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)'),
            'prompt_name': prompt_name,
            'dataset_name': dataset_name,
            'total_emails': stats['total_emails'],
            'contacts_extracted': stats['contacts_extracted'],
            'contacts_percentage': stats['contacts_extracted_percentage'],
            'phones_found': stats['phones_found'],
            'phones_percentage': stats['phones_found_percentage'],
            'emails_found': stats['emails_found'],
            'emails_percentage': stats['emails_found_percentage'],
            'inn_found': stats['inn_found'],
            'inn_percentage': stats['inn_found_percentage'],
            'websites_found': stats['websites_found'],
            'websites_percentage': stats['websites_found_percentage'],
            'valid_json': stats['valid_json'],
            'json_percentage': stats['valid_json_percentage'],
            'structured_output': stats['structured_output'],
            'structured_percentage': stats['structured_output_percentage'],
            'complete_fields': stats['complete_fields'],
            'complete_percentage': stats['complete_fields_percentage'],
            'detailed_results': self.generate_detailed_results(results),
            'error_analysis': self.generate_error_analysis(stats),
            'recommendations': self.generate_recommendations(stats),
            'best_example': self.format_example(stats.get('best_result')),
            'worst_example': self.format_example(stats.get('worst_result')),
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)'),
            'overall_rating': round(sum(self._calculate_score(r) for r in results) / len(results), 1) if results else 0
        }
        
        # Генерация отчета
        report_content = self.template.format(**template_data)
        
        # Сохранение отчета
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            safe_prompt_name = prompt_name.replace('.txt', '').replace('/', '_')
            output_path = f"/Users/evgenyzach/contact_parser/memory-bank/reports/{timestamp}_test_{safe_prompt_name}.md"
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return output_path


if __name__ == "__main__":
    # Пример использования
    reporter = PromptTestReporter()
    
    # Тестовые данные
    test_results = [
        {
            'email_file': 'email_001.json',
            'json_valid': True,
            'structured': True,
            'complete_fields': True,
            'extracted_data': {
                'phones': ['+7-123-456-78-90'],
                'emails': ['test@example.com'],
                'inn': '1234567890'
            }
        }
    ]
    
    report_path = reporter.generate_report(
        results=test_results,
        prompt_name="test_prompt",
        dataset_name="test_dataset"
    )
    
    print(f"Отчет создан: {report_path}")