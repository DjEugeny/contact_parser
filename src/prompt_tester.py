#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для тестирования промптов извлечения контактов

Автор: IMPLEMENT агент
Дата: 09.09.2025
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class PromptTester:
    """Класс для тестирования промптов извлечения контактов"""
    
    def __init__(self):
        """Инициализация тестера промптов"""
        # Определяем корневую директорию проекта динамически
        project_root = Path(__file__).resolve().parent.parent
        self.prompts_dir = project_root / "prompts"
        self.results = []
        
    def load_prompt(self, prompt_file: str) -> str:
        """Загрузить промпт из файла"""
        prompt_path = self.prompts_dir / prompt_file
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Промпт файл не найден: {prompt_path}")
            
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def load_email(self, email_file: str, email_dir: str) -> Dict[str, Any]:
        """Загрузить email из JSON файла"""
        email_path = Path(email_dir) / email_file
        
        if not email_path.exists():
            raise FileNotFoundError(f"Email файл не найден: {email_path}")
            
        with open(email_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def simulate_llm_response(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Симуляция ответа LLM для тестирования
        
        В реальной системе здесь будет вызов к LLM API
        Для тестирования генерируем mock-данные на основе содержимого письма
        """
        
        # Извлекаем базовую информацию из письма
        email_body = email_data.get('body', '')
        subject = email_data.get('subject', '')
        from_email = email_data.get('from', '')
        
        # Простая симуляция извлечения контактов
        mock_response = {
            "contacts": [],
            "business_context": {
                "company_name": "",
                "industry": "",
                "request_type": "коммерческое предложение"
            },
            "commercial_proposal": {
                "products": [],
                "total_amount": None,
                "currency": "RUB"
            },
            "metadata": {
                "confidence_score": 0.8,
                "processing_notes": "Симуляция для тестирования"
            }
        }
        
        # Попытка извлечь ИНН из текста
        import re
        inn_pattern = r'\b\d{10,12}\b'
        inn_matches = re.findall(inn_pattern, email_body)
        
        # Попытка извлечь телефоны
        phone_pattern = r'\+?[78][-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}'
        phone_matches = re.findall(phone_pattern, email_body)
        
        # Попытка извлечь email адреса
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, email_body)
        
        # Создаем контакт на основе найденных данных
        if inn_matches or phone_matches or email_matches:
            contact = {
                "name": "Извлеченный контакт",
                "position": "",
                "company": "",
                "phone": phone_matches[0] if phone_matches else "",
                "email": email_matches[0] if email_matches else from_email,
                "inn": inn_matches[0] if inn_matches else "",
                "website": "",
                "address": ""
            }
            mock_response["contacts"].append(contact)
        
        return mock_response
    
    def evaluate_response(self, response: Dict[str, Any], email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Оценить качество ответа LLM"""
        
        score = 0
        max_score = 10
        evaluation_details = []
        
        # Проверка наличия контактов
        contacts = response.get('contacts', [])
        if contacts:
            score += 3
            evaluation_details.append("✅ Контакты найдены (+3)")
        else:
            evaluation_details.append("❌ Контакты не найдены (0)")
        
        # Проверка качества JSON структуры
        try:
            if isinstance(response, dict) and 'contacts' in response:
                score += 2
                evaluation_details.append("✅ Корректная JSON структура (+2)")
        except:
            evaluation_details.append("❌ Некорректная JSON структура (0)")
        
        # Проверка наличия ИНН
        has_inn = any(contact.get('inn') for contact in contacts)
        if has_inn:
            score += 2
            evaluation_details.append("✅ ИНН найден (+2)")
        else:
            evaluation_details.append("❌ ИНН не найден (0)")
        
        # Проверка наличия телефонов
        has_phone = any(contact.get('phone') for contact in contacts)
        if has_phone:
            score += 2
            evaluation_details.append("✅ Телефон найден (+2)")
        else:
            evaluation_details.append("❌ Телефон не найден (0)")
        
        # Проверка наличия email
        has_email = any(contact.get('email') for contact in contacts)
        if has_email:
            score += 1
            evaluation_details.append("✅ Email найден (+1)")
        else:
            evaluation_details.append("❌ Email не найден (0)")
        
        return {
            "score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "evaluation_details": evaluation_details
        }
    
    def test_single_email(self, prompt_file: str, email_file: str, email_dir: str) -> Optional[Dict[str, Any]]:
        """Тестировать промпт на одном письме"""
        
        try:
            # Загружаем промпт и email
            prompt = self.load_prompt(prompt_file)
            email_data = self.load_email(email_file, email_dir)
            
            # Симулируем ответ LLM
            llm_response = self.simulate_llm_response(email_data)
            
            # Оцениваем качество ответа
            evaluation = self.evaluate_response(llm_response, email_data)
            
            # Формируем результат
            result = {
                "email_file": email_file,
                "prompt_file": prompt_file,
                "timestamp": datetime.now().isoformat(),
                "email_metadata": {
                    "from": email_data.get('from', ''),
                    "subject": email_data.get('subject', ''),
                    "date": email_data.get('date', ''),
                    "attachments_count": len(email_data.get('attachments', []))
                },
                "llm_response": llm_response,
                "evaluation": evaluation,
                "success": True
            }
            
            return result
            
        except Exception as e:
            return {
                "email_file": email_file,
                "prompt_file": prompt_file,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            }
    
    def test_multiple_emails(self, prompt_file: str, email_files: List[str], email_dir: str) -> List[Dict[str, Any]]:
        """Тестировать промпт на нескольких письмах"""
        
        results = []
        
        for email_file in email_files:
            result = self.test_single_email(prompt_file, email_file, email_dir)
            if result:
                results.append(result)
        
        return results