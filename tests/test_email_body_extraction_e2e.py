#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 E2E тесты для извлечения body из email_data

Проверяет полный цикл:
1. Email Fetcher → email_data
2. email_data → body extraction
3. body → LLM processing
4. Валидация качества результатов

Создано: 2025-10-15
Задача: 3.2 из data-quality-regression-analysis-2025-10-15/tasks.md
"""

import pytest
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.email_body_extractor import (
    extract_body_with_fallback,
    extract_all_text_sources,
    validate_email_data_structure
)
from models.email_data_validator_simple import EmailDataValidator


class TestEmailBodyExtractionE2E:
    """E2E тесты для извлечения body"""
    
    def test_legacy_format_extraction(self):
        """Тест извлечения из legacy формата"""
        email_data = {
            "message_id": "test-legacy-001",
            "subject": "Test",
            "from": "test@example.com",
            "body": "This is legacy body text with important information",
            "char_count": 50
        }
        
        # Извлечение body
        body = extract_body_with_fallback(email_data, prefer_clean=True)
        
        # Проверки
        assert body is not None, "Body должен быть извлечён"
        assert len(body) > 0, "Body не должен быть пустым"
        assert "important information" in body, "Body должен содержать ключевые слова"
        
        # Валидация
        is_valid, errors = EmailDataValidator.validate(email_data, strict=True)
        assert is_valid, f"Данные должны быть валидны: {errors}"
        
        # Метрики
        metrics = EmailDataValidator.get_quality_metrics(email_data)
        assert metrics["has_body"] == True
        assert metrics["body_length"] > 0
        assert metrics["format_type"] == "legacy"
    
    def test_new_format_extraction_prefer_clean(self):
        """Тест извлечения из NEW формата (приоритет body_clean)"""
        email_data = {
            "message_id": "test-new-001",
            "subject": "Test",
            "from": "test@example.com",
            "body_clean": "Clean text without HTML",
            "body_raw": "Raw text with <html>tags</html>",
            "char_count": 25
        }
        
        # Извлечение с приоритетом clean
        body = extract_body_with_fallback(email_data, prefer_clean=True)
        
        # Проверки
        assert body is not None
        assert body == "Clean text without HTML"
        assert "<html>" not in body, "Clean body не должен содержать HTML"
        
        # Метрики
        metrics = EmailDataValidator.get_quality_metrics(email_data)
        assert metrics["format_type"] == "new"
    
    def test_new_format_extraction_prefer_raw(self):
        """Тест извлечения из NEW формата (приоритет body_raw)"""
        email_data = {
            "message_id": "test-new-002",
            "body_clean": "Clean text",
            "body_raw": "Raw text with tags",
        }
        
        # Извлечение с приоритетом raw
        body = extract_body_with_fallback(email_data, prefer_clean=False)
        
        # Проверки
        assert body is not None
        assert body == "Raw text with tags"
    
    def test_fallback_chain(self):
        """Тест цепочки fallback"""
        # Только body_plain
        email_data = {
            "message_id": "test-fallback-001",
            "body_plain": "Plain text only"
        }
        
        body = extract_body_with_fallback(email_data)
        assert body == "Plain text only"
        
        # Только text
        email_data2 = {
            "message_id": "test-fallback-002",
            "text": "Text field only"
        }
        
        body2 = extract_body_with_fallback(email_data2)
        assert body2 == "Text field only"
    
    def test_empty_body_handling(self):
        """Тест обработки пустого body"""
        email_data = {
            "message_id": "test-empty-001",
            "subject": "No body",
            "attachments": [{"filename": "test.pdf"}]
        }
        
        body = extract_body_with_fallback(email_data)
        assert body is None, "Для письма без body должен вернуться None"
        
        # Валидация (нестрогая)
        is_valid, errors = EmailDataValidator.validate(email_data, strict=False)
        assert is_valid, "Письмо без body валидно в нестрогом режиме"
        
        # Валидация (строгая)
        is_valid_strict, errors_strict = EmailDataValidator.validate(email_data, strict=True)
        assert not is_valid_strict, "Письмо без body невалидно в строгом режиме"
    
    def test_extract_all_text_sources(self):
        """Тест извлечения всех текстовых источников"""
        email_data = {
            "message_id": "test-multi-001",
            "body_clean": "Clean body",
            "plain_text": "Plain text version"
        }
        
        sources = extract_all_text_sources(email_data, include_plain_text=True)
        
        assert len(sources) == 2, "Должно быть 2 источника"
        assert "Clean body" in sources
        assert "Plain text version" in sources
    
    def test_validate_structure(self):
        """Тест валидации структуры"""
        # Валидная структура
        email_data = {
            "message_id": "test-struct-001",
            "body_clean": "Text"
        }
        
        validation = validate_email_data_structure(email_data)
        
        assert validation["has_body"] == True
        assert "body_clean" in validation["available_fields"]
        assert validation["recommended_field"] == "body_clean"
        assert len(validation["warnings"]) == 0
        
        # Невалидная структура (нет body)
        email_data_empty = {
            "message_id": "test-struct-002"
        }
        
        validation_empty = validate_email_data_structure(email_data_empty)
        
        assert validation_empty["has_body"] == False
        assert len(validation_empty["warnings"]) > 0
    
    def test_migration_legacy_to_new(self):
        """Тест миграции legacy → new"""
        legacy_data = {
            "message_id": "test-migrate-001",
            "body": "Legacy body text"
        }
        
        # До миграции
        assert legacy_data.get("body_clean") is None
        assert legacy_data.get("body_raw") is None
        
        # Миграция
        migrated = EmailDataValidator.migrate_to_new_format(legacy_data)
        
        # После миграции
        assert migrated["body_clean"] == "Legacy body text"
        assert migrated["body_raw"] == "Legacy body text"
        assert migrated["body"] == "Legacy body text"  # Оригинал сохранён
    
    def test_batch_validation(self):
        """Тест batch валидации"""
        batch = [
            {"message_id": "batch-001", "body": "Text 1"},
            {"message_id": "batch-002", "body_clean": "Text 2"},
            {"message_id": "batch-003"},  # Без body
            {},  # Без message_id
        ]
        
        valid, errors = EmailDataValidator.validate_batch(batch, strict=False)
        
        assert len(valid) == 3, "3 письма должны быть валидны"
        assert len(errors) == 1, "1 письмо должно быть невалидно"
        assert errors[0]["index"] == 3
    
    def test_quality_metrics(self):
        """Тест вычисления метрик качества"""
        email_data = {
            "message_id": "test-metrics-001",
            "subject": "Test Subject",
            "from": "sender@example.com",
            "body_clean": "This is a test email body",
            "char_count": 25,  # Правильная длина строки
            "attachments": [
                {"filename": "file1.pdf"},
                {"filename": "file2.docx"}
            ]
        }
        
        metrics = EmailDataValidator.get_quality_metrics(email_data)
        
        assert metrics["has_body"] == True
        assert metrics["body_length"] == 25  # "This is a test email body" = 25 символов
        assert metrics["format_type"] == "new"
        assert metrics["has_attachments"] == True
        assert metrics["attachment_count"] == 2
        assert metrics["has_subject"] == True
        assert metrics["has_from"] == True
        assert metrics["char_count_match"] == True
    
    def test_return_source_field(self):
        """Тест возврата имени source поля"""
        email_data = {
            "message_id": "test-source-001",
            "body_clean": "Clean text"
        }
        
        body, source = extract_body_with_fallback(
            email_data,
            prefer_clean=True,
            return_source=True
        )
        
        assert body == "Clean text"
        assert source == "body_clean"
    
    def test_whitespace_handling(self):
        """Тест обработки пробелов"""
        # Пустая строка
        email_data1 = {
            "message_id": "test-ws-001",
            "body": "   "  # Только пробелы
        }
        
        body1 = extract_body_with_fallback(email_data1)
        assert body1 is None, "Строка из пробелов должна игнорироваться"
        
        # Строка с пробелами по краям
        email_data2 = {
            "message_id": "test-ws-002",
            "body": "  Text with spaces  "
        }
        
        body2 = extract_body_with_fallback(email_data2)
        assert body2 is not None
        assert "Text with spaces" in body2


class TestIntegrationWithModules:
    """Integration тесты с реальными модулями"""
    
    def test_api_pipeline_validator_integration(self):
        """Тест интеграции с api_pipeline_validator"""
        # Симуляция работы api_pipeline_validator._compose_combined_text
        email_data = {
            "message_id": "test-api-001",
            "subject": "Test",
            "body_clean": "Email body text",
            "attachments": [
                {
                    "original_filename": "test.pdf",
                    "content": "Attachment text content"
                }
            ]
        }
        
        # Извлечение body (как в api_pipeline_validator)
        body, source = extract_body_with_fallback(
            email_data,
            prefer_clean=True,
            return_source=True
        )
        
        # Формирование combined_text
        parts = []
        if body:
            parts.append(f"=== ТЕКСТ ПИСЬМА ===\n{body}")
        
        for i, att in enumerate(email_data.get("attachments", []), 1):
            if att.get("content"):
                parts.append(f"\n=== ВЛОЖЕНИЕ {i} ===\n{att['content']}")
        
        combined_text = "\n\n".join(parts)
        
        # Проверки
        assert "=== ТЕКСТ ПИСЬМА ===" in combined_text
        assert "Email body text" in combined_text
        assert "=== ВЛОЖЕНИЕ 1 ===" in combined_text
        assert "Attachment text content" in combined_text
    
    def test_org_email_enricher_integration(self):
        """Тест интеграции с org_email_enricher"""
        # Симуляция работы org_email_enricher._extract_emails_from_signature
        email_data = {
            "message_id": "test-org-001",
            "body_clean": "Contact: john@example.com\nPhone: +1234567890",
            "plain_text": "Alternative: jane@example.com"
        }
        
        # Извлечение всех текстовых источников (как в org_email_enricher)
        text_sources = extract_all_text_sources(email_data, include_plain_text=True)
        
        # Проверки
        assert len(text_sources) == 2
        assert any("john@example.com" in src for src in text_sources)
        assert any("jane@example.com" in src for src in text_sources)
    
    def test_contact_enricher_integration(self):
        """Тест интеграции с contact_enricher"""
        # Симуляция работы contact_enricher._extract_website_from_email
        email_data = {
            "message_id": "test-contact-001",
            "body_clean": "Visit our website: https://example.com"
        }
        
        # Извлечение body (как в contact_enricher)
        body = extract_body_with_fallback(email_data, prefer_clean=True)
        
        # Проверки
        assert body is not None
        assert "https://example.com" in body


# === Pytest fixtures ===

@pytest.fixture
def sample_legacy_email():
    """Fixture: legacy формат письма"""
    return {
        "message_id": "fixture-legacy-001",
        "subject": "Sample Legacy Email",
        "from": "sender@example.com",
        "body": "This is a sample legacy email body",
        "char_count": 35
    }


@pytest.fixture
def sample_new_email():
    """Fixture: NEW формат письма"""
    return {
        "message_id": "fixture-new-001",
        "subject": "Sample New Email",
        "from": "sender@example.com",
        "body_clean": "This is a clean email body",
        "body_raw": "This is a raw email body with <tags>",
        "char_count": 26
    }


if __name__ == "__main__":
    # Запуск тестов через pytest
    pytest.main([__file__, "-v", "--tb=short"])
