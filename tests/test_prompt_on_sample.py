Возможно, проблема в кэшировании, потому что в логе в терминале, я вижу сейчас, что есть информация о кэшировании.#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования промптов извлечения контактов на тестовой выборке.
Использует созданную систему генерации отчетов.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Добавляем путь к tests для импорта модулей
sys.path.append('/Users/evgenyzach/contact_parser/tests')

from prompt_test_reporter import PromptTestReporter


class PromptTester:
    """Тестировщик промптов на выборке писем."""
    
    def __init__(self):
        """Инициализация тестера."""
        self.base_path = "/Users/evgenyzach/contact_parser"
        self.data_path = f"{self.base_path}/data/emails/2025-07-29"
        self.prompts_path = f"{self.base_path}/prompts"
        self.reporter = PromptTestReporter()
        
        # Список файлов тестовой выборки (реальные имена из описания)
        self.test_emails = [
            "email_001_20250729_20250729_centerld_ru_d03bd60b.json",
            "email_008_20250729_20250729_mail_ru_8f55fa3f.json",  # Заменяем на реальный
            "email_022_20250729_20250729_dna-technology_ru_6360137e.json",  # Заменяем на реальный
            "email_012_20250729_20250729_dna-technology_ru_6fd74dbf.json",
            "email_015_20250729_20250729_dna-technology_ru_41fbdf51.json",
            "email_004_20250729_20250729_dna-technology_ru_6e851453.json",
            "email_028_20250729_20250729_dna-technology_ru_46932b3d.json",
            "email_014_20250729_20250729_millab_ru_62cf1268.json",  # Заменяем на реальный
            "email_016_20250729_20250729_dna-technology_ru_6360137e.json",
            "email_025_20250729_20250729_dna-technology_ru_4aee22c5.json"
        ]
    
    def load_email_data(self, email_file: str) -> Optional[Dict[str, Any]]:
        """Загружает данные письма из JSON файла.
        
        Args:
            email_file: Имя файла письма
            
        Returns:
            Данные письма или None при ошибке
        """
        file_path = f"{self.data_path}/{email_file}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Файл не найден: {file_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON в {email_file}: {e}")
            return None
    
    def load_prompt(self, prompt_file: str) -> Optional[str]:
        """Загружает промпт из файла.
        
        Args:
            prompt_file: Имя файла промпта
            
        Returns:
            Текст промпта или None при ошибке
        """
        file_path = f"{self.prompts_path}/{prompt_file}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Промпт не найден: {file_path}")
            return None
    
    def extract_text_content(self, email_data: Dict[str, Any]) -> str:
        """Извлекает текстовое содержимое письма для анализа.
        
        Args:
            email_data: Данные письма
            
        Returns:
            Объединенный текст письма
        """
        content_parts = []
        
        # Добавляем тему
        if email_data.get('subject'):
            content_parts.append(f"Тема: {email_data['subject']}")
        
        # Добавляем отправителя
        if email_data.get('from'):
            content_parts.append(f"От: {email_data['from']}")
        
        # Добавляем тело письма
        if email_data.get('body'):
            content_parts.append(f"Содержимое:\n{email_data['body']}")
        
        # Добавляем информацию о вложениях
        attachments = email_data.get('attachments', [])
        if attachments:
            content_parts.append(f"\nВложения ({len(attachments)} шт.):")
            for i, attachment in enumerate(attachments, 1):
                att_info = f"{i}. {attachment.get('filename', 'unknown')}"
                if attachment.get('content'):
                    # Добавляем полное содержимое вложения для анализа
                    att_content = attachment['content']
                    att_info += f"\nСодержимое: {att_content}"
                content_parts.append(att_info)
        
        return "\n\n".join(content_parts)
    
    def test_prompt_on_email(self, 
                            email_data: Dict[str, Any], 
                            prompt_text: str, 
                            email_file: str) -> Dict[str, Any]:
        """Тестирует промпт на одном письме.
        
        Args:
            email_data: Данные письма
            prompt_text: Текст промпта
            email_file: Имя файла письма
            
        Returns:
            Результат тестирования
        """
        result = {
            'email_file': email_file,
            'json_valid': False,
            'structured': False,
            'complete_fields': False,
            'extracted_data': None,
            'error': None,
            'raw_response': None
        }
        
        try:
            # Извлекаем текстовое содержимое
            text_content = self.extract_text_content(email_data)
            
            # Создаем экстрактор (используем заглушку, так как нет реального LLM)
            # В реальном использовании здесь будет вызов LLM API
            extracted_data = self._mock_llm_extraction(text_content, prompt_text)
            
            result['raw_response'] = str(extracted_data)
            
            # Проверяем валидность JSON
            if isinstance(extracted_data, dict):
                result['json_valid'] = True
                result['extracted_data'] = extracted_data
                
                # Проверяем структурированность
                required_fields = ['phones', 'emails', 'inn', 'websites', 'company_name']
                if all(field in extracted_data for field in required_fields):
                    result['structured'] = True
                
                # Проверяем полноту полей
                filled_fields = sum(1 for field in required_fields 
                                  if extracted_data.get(field) and 
                                  (isinstance(extracted_data[field], list) and extracted_data[field] or 
                                   isinstance(extracted_data[field], str) and extracted_data[field].strip()))
                
                if filled_fields >= 3:  # Минимум 3 поля должны быть заполнены
                    result['complete_fields'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _mock_llm_extraction(self, text_content: str, prompt_text: str) -> Dict[str, Any]:
        """Заглушка для извлечения данных (имитация работы LLM).
        
        В реальном использовании здесь будет вызов LLM API.
        
        Args:
            text_content: Текст для анализа
            prompt_text: Промпт для LLM
            
        Returns:
            Извлеченные данные
        """
        # Простая имитация извлечения данных на основе регулярных выражений
        import re
        
        extracted = {
            'phones': [],
            'emails': [],
            'inn': '',
            'websites': [],
            'company_name': ''
        }
        
        # Поиск телефонов
        phone_patterns = [
            r'\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            r'8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            r'\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text_content)
            extracted['phones'].extend(phones)
        
        # Поиск email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text_content)
        extracted['emails'] = list(set(emails))  # Убираем дубликаты
        
        # Поиск ИНН
        inn_pattern = r'\b\d{10,12}\b'
        inn_matches = re.findall(inn_pattern, text_content)
        if inn_matches:
            extracted['inn'] = inn_matches[0]
        
        # Поиск сайтов
        website_patterns = [
            r'https?://[\w\.-]+\.[a-zA-Z]{2,}',
            r'www\.[\w\.-]+\.[a-zA-Z]{2,}',
            r'\b[\w\.-]+\.(ru|com|org|net|info)\b'
        ]
        
        for pattern in website_patterns:
            websites = re.findall(pattern, text_content, re.IGNORECASE)
            extracted['websites'].extend(websites)
        
        extracted['websites'] = list(set(extracted['websites']))  # Убираем дубликаты
        
        # Поиск названия компании (простая эвристика)
        company_patterns = [
            r'ООО\s+"?([^"\n]+)"?',
            r'ЗАО\s+"?([^"\n]+)"?',
            r'ОАО\s+"?([^"\n]+)"?',
            r'компани[яи]\s+"?([^"\n]+)"?'
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                extracted['company_name'] = matches[0].strip()
                break
        
        return extracted
    
    def test_prompt_on_sample(self, prompt_file: str) -> List[Dict[str, Any]]:
        """Тестирует промпт на всей выборке.
        
        Args:
            prompt_file: Имя файла промпта
            
        Returns:
            Список результатов для каждого письма
        """
        print(f"Тестирование промпта: {prompt_file}")
        
        # Загружаем промпт
        prompt_text = self.load_prompt(prompt_file)
        if not prompt_text:
            return []
        
        results = []
        
        for i, email_file in enumerate(self.test_emails, 1):
            print(f"Обработка {i}/{len(self.test_emails)}: {email_file}")
            
            # Загружаем данные письма
            email_data = self.load_email_data(email_file)
            if not email_data:
                continue
            
            # Тестируем промпт
            result = self.test_prompt_on_email(email_data, prompt_text, email_file)
            results.append(result)
        
        return results
    
    def run_test(self, prompt_file: str) -> str:
        """Запускает полный тест промпта и генерирует отчет.
        
        Args:
            prompt_file: Имя файла промпта
            
        Returns:
            Путь к созданному отчету
        """
        # Тестируем промпт
        results = self.test_prompt_on_sample(prompt_file)
        
        if not results:
            print("Нет результатов для генерации отчета")
            return ""
        
        # Генерируем отчет
        report_path = self.reporter.generate_report(
            results=results,
            prompt_name=prompt_file,
            dataset_name="test_dataset_10_emails"
        )
        
        print(f"Отчет создан: {report_path}")
        return report_path


if __name__ == "__main__":
    tester = PromptTester()
    
    # Тестируем оба промпта
    prompts_to_test = [
        "unified_contact_extraction_structured.txt",
        "unified_contact_extraction.txt"
    ]
    
    for prompt_file in prompts_to_test:
        print(f"\n{'='*50}")
        print(f"Тестирование: {prompt_file}")
        print(f"{'='*50}")
        
        report_path = tester.run_test(prompt_file)
        
        if report_path:
            print(f"✅ Отчет готов: {report_path}")
        else:
            print(f"❌ Ошибка при тестировании {prompt_file}")
    
    print("\n🎉 Тестирование завершено!")