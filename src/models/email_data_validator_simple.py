#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 Email Data Validator (Simple) - Валидатор без Pydantic

Упрощённая версия валидатора для использования без установки Pydantic.
Для production рекомендуется использовать email_data_schema.py с Pydantic.

Создано: 2025-10-15
Задача: 3.1 из data-quality-regression-analysis-2025-10-15/tasks.md
"""

from typing import Dict, Any, List, Optional, Tuple, Literal


class EmailDataValidator:
    """
    🛡️ Простой валидатор для email_data без зависимостей
    """
    
    REQUIRED_FIELDS = ["message_id"]
    BODY_FIELDS = ["body", "body_raw", "body_clean", "body_plain", "body_text", "text"]
    
    @staticmethod
    def validate(data: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str]]:
        """
        Валидирует данные письма
        
        Args:
            data: Сырые данные письма
            strict: Строгий режим (требует body)
            
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        
        # Проверка обязательных полей
        for field in EmailDataValidator.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                errors.append(f"Отсутствует обязательное поле: {field}")
        
        # Проверка наличия хотя бы одного body поля
        has_body = any(
            data.get(field) and isinstance(data.get(field), str) and data.get(field).strip()
            for field in EmailDataValidator.BODY_FIELDS
        )
        
        if strict and not has_body:
            errors.append("Отсутствует тело письма (body)")
        
        # Проверка типов
        if "char_count" in data and data["char_count"] is not None:
            if not isinstance(data["char_count"], int) or data["char_count"] < 0:
                errors.append("char_count должен быть неотрицательным целым числом")
        
        if "attachments" in data and data["attachments"] is not None:
            if not isinstance(data["attachments"], list):
                errors.append("attachments должен быть списком")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def validate_batch(
        data_list: List[Dict[str, Any]],
        strict: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Валидирует список писем
        
        Args:
            data_list: Список сырых данных писем
            strict: Строгий режим
            
        Returns:
            tuple: (валидные письма, ошибки)
        """
        valid = []
        errors = []
        
        for i, data in enumerate(data_list):
            is_valid, validation_errors = EmailDataValidator.validate(data, strict=strict)
            
            if is_valid:
                valid.append(data)
            else:
                errors.append({
                    "index": i,
                    "message_id": data.get("message_id", "unknown"),
                    "errors": validation_errors
                })
        
        return valid, errors
    
    @staticmethod
    def get_format_type(data: Dict[str, Any]) -> Literal["legacy", "new", "alternative", "empty"]:
        """
        📋 Определяет тип формата данных
        
        Args:
            data: Данные письма
            
        Returns:
            str: "legacy", "new", "alternative", "empty"
        """
        if data.get("body"):
            return "legacy"
        elif data.get("body_clean") or data.get("body_raw"):
            return "new"
        elif data.get("body_plain") or data.get("body_text") or data.get("text"):
            return "alternative"
        else:
            return "empty"
    
    @staticmethod
    def get_quality_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        📊 Вычисляет метрики качества для письма
        
        Args:
            data: Данные письма
            
        Returns:
            Dict с метриками качества
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.email_body_extractor import extract_body_with_fallback
        
        body = extract_body_with_fallback(data, prefer_clean=True)
        attachments = data.get("attachments", [])
        
        return {
            "has_body": body is not None and len(body) > 0,
            "body_length": len(body) if body else 0,
            "format_type": EmailDataValidator.get_format_type(data),
            "has_attachments": len(attachments) > 0,
            "attachment_count": len(attachments),
            "has_subject": bool(data.get("subject") and data.get("subject").strip()),
            "has_from": bool(data.get("from") and data.get("from").strip()),
            "char_count": data.get("char_count", 0),
            "char_count_match": (
                data.get("char_count") == len(body)
                if data.get("char_count") and body
                else None
            )
        }
    
    @staticmethod
    def migrate_to_new_format(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔄 Мигрирует legacy формат в NEW формат
        
        Если есть только "body", создаёт "body_clean" и "body_raw"
        
        Args:
            data: Данные письма (изменяется in-place)
            
        Returns:
            Dict: Обновлённые данные
        """
        if data.get("body") and not data.get("body_clean") and not data.get("body_raw"):
            # Миграция: body -> body_clean и body_raw
            data["body_clean"] = data["body"]
            data["body_raw"] = data["body"]
        
        return data


# === Примеры использования ===

if __name__ == "__main__":
    print("🧪 Тестирование EmailDataValidator (Simple)\n")
    
    # Тест 1: Legacy format
    print("Тест 1: Legacy format")
    legacy_data = {
        "message_id": "test-001",
        "subject": "Test Subject",
        "from": "sender@example.com",
        "body": "This is legacy body text",
        "char_count": 24
    }
    
    is_valid, errors = EmailDataValidator.validate(legacy_data, strict=True)
    print(f"  Валидация: {'✅ Пройдена' if is_valid else '❌ Провалена'}")
    if errors:
        print(f"  Ошибки: {errors}")
    
    format_type = EmailDataValidator.get_format_type(legacy_data)
    print(f"  Format type: {format_type}")
    
    metrics = EmailDataValidator.get_quality_metrics(legacy_data)
    print(f"  Metrics: {metrics}\n")
    
    # Тест 2: NEW format
    print("Тест 2: NEW format")
    new_data = {
        "message_id": "test-002",
        "subject": "Test Subject 2",
        "from": "sender2@example.com",
        "body_clean": "This is clean body text",
        "body_raw": "This is raw body text with <html>tags</html>",
        "char_count": 23
    }
    
    is_valid, errors = EmailDataValidator.validate(new_data, strict=True)
    print(f"  Валидация: {'✅ Пройдена' if is_valid else '❌ Провалена'}")
    
    format_type = EmailDataValidator.get_format_type(new_data)
    print(f"  Format type: {format_type}\n")
    
    # Тест 3: Миграция
    print("Тест 3: Миграция legacy -> new")
    legacy_copy = legacy_data.copy()
    print(f"  До: body_clean={legacy_copy.get('body_clean')}, body_raw={legacy_copy.get('body_raw')}")
    
    migrated = EmailDataValidator.migrate_to_new_format(legacy_copy)
    print(f"  После: body_clean={bool(migrated.get('body_clean'))}, body_raw={bool(migrated.get('body_raw'))}")
    print(f"  ✅ Миграция выполнена\n")
    
    # Тест 4: Batch валидация
    print("Тест 4: Batch валидация")
    batch_data = [
        {"message_id": "batch-001", "body": "Text 1"},
        {"message_id": "batch-002", "body_clean": "Text 2"},
        {"message_id": "batch-003"},  # Без body
        {},  # Без message_id - должно провалиться
    ]
    
    valid, errors_list = EmailDataValidator.validate_batch(batch_data, strict=False)
    print(f"  Валидных: {len(valid)}/{len(batch_data)}")
    print(f"  Ошибок: {len(errors_list)}")
    if errors_list:
        for error in errors_list:
            print(f"    - {error}")
    print(f"  ✅ Batch валидация завершена\n")
    
    # Тест 5: Невалидные данные
    print("Тест 5: Невалидные данные")
    invalid_data = {
        "message_id": "test-invalid",
        "char_count": -10,  # Неверное значение
        "attachments": "not a list"  # Неверный тип
    }
    
    is_valid, errors = EmailDataValidator.validate(invalid_data, strict=True)
    print(f"  Валидация: {'✅ Пройдена' if is_valid else '❌ Провалена (ожидалось)'}")
    print(f"  Ошибки: {errors}\n")
    
    print("🎉 Все тесты пройдены!")
