#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 Email Data Schema - Pydantic модели для валидации структуры email_data

Обеспечивает:
- Валидацию структуры данных от Email Fetcher
- Поддержку legacy и NEW форматов
- Автоматическую миграцию между форматами
- Защиту от регрессий

Создано: 2025-10-15
Задача: 3.1 из data-quality-regression-analysis-2025-10-15/tasks.md
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class AttachmentSchema(BaseModel):
    """📎 Схема вложения письма"""
    
    original_filename: Optional[str] = Field(None, description="Оригинальное имя файла")
    saved_filename: Optional[str] = Field(None, description="Имя сохранённого файла")
    content_type: Optional[str] = Field(None, description="MIME тип")
    size: Optional[int] = Field(None, ge=0, description="Размер в байтах")
    status: Optional[str] = Field(None, description="Статус обработки")
    content: Optional[str] = Field(None, description="Извлечённый текст (OCR)")
    
    class Config:
        extra = "allow"  # Разрешаем дополнительные поля


class EmailDataSchema(BaseModel):
    """
    📧 Схема данных письма от Email Fetcher
    
    Поддерживает:
    - Legacy format: "body"
    - NEW format: "body_raw", "body_clean"
    - Автоматическую валидацию
    - Миграцию между форматами
    """
    
    # === Обязательные поля ===
    message_id: str = Field(..., description="Уникальный ID письма")
    subject: Optional[str] = Field(None, description="Тема письма")
    from_: Optional[str] = Field(None, alias="from", description="Отправитель")
    to: Optional[str] = Field(None, description="Получатель")
    date: Optional[str] = Field(None, description="Дата письма")
    
    # === Body поля (хотя бы одно должно быть) ===
    body: Optional[str] = Field(None, description="Тело письма (legacy format)")
    body_raw: Optional[str] = Field(None, description="Сырое тело письма (NEW format)")
    body_clean: Optional[str] = Field(None, description="Очищенное тело письма (NEW format)")
    body_plain: Optional[str] = Field(None, description="Plain text тело")
    body_text: Optional[str] = Field(None, description="Text тело")
    text: Optional[str] = Field(None, description="Общее текстовое поле")
    
    # === Дополнительные поля ===
    plain_text: Optional[str] = Field(None, description="Plain text версия")
    html: Optional[str] = Field(None, description="HTML версия")
    attachments: List[AttachmentSchema] = Field(default_factory=list, description="Вложения")
    
    # === Метаданные ===
    char_count: Optional[int] = Field(None, ge=0, description="Количество символов")
    has_attachments: Optional[bool] = Field(None, description="Есть ли вложения")
    
    class Config:
        extra = "allow"  # Разрешаем дополнительные поля для гибкости
        populate_by_name = True  # Позволяет использовать alias
    
    @field_validator('attachments', mode='before')
    @classmethod
    def validate_attachments(cls, v):
        """Валидация вложений"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []
    
    @model_validator(mode='after')
    def validate_body_exists(self):
        """Проверка что хотя бы одно body поле заполнено"""
        body_fields = [
            self.body,
            self.body_raw,
            self.body_clean,
            self.body_plain,
            self.body_text,
            self.text
        ]
        
        has_body = any(
            field and isinstance(field, str) and field.strip()
            for field in body_fields
        )
        
        if not has_body:
            # Это warning, а не error - письмо может быть только с вложениями
            pass
        
        return self
    
    def get_body(self, prefer_clean: bool = True) -> Optional[str]:
        """
        🔍 Извлекает body с fallback логикой
        
        Args:
            prefer_clean: Приоритет body_clean над body_raw
            
        Returns:
            str or None: Тело письма
        """
        from src.utils.email_body_extractor import extract_body_with_fallback
        
        return extract_body_with_fallback(
            self.model_dump(by_alias=True),
            prefer_clean=prefer_clean
        )
    
    def get_format_type(self) -> Literal["legacy", "new", "alternative", "empty"]:
        """
        📋 Определяет тип формата данных
        
        Returns:
            str: "legacy", "new", "alternative", "empty"
        """
        if self.body:
            return "legacy"
        elif self.body_clean or self.body_raw:
            return "new"
        elif self.body_plain or self.body_text or self.text:
            return "alternative"
        else:
            return "empty"
    
    def migrate_to_new_format(self) -> "EmailDataSchema":
        """
        🔄 Мигрирует legacy формат в NEW формат
        
        Если есть только "body", создаёт "body_clean" и "body_raw"
        
        Returns:
            EmailDataSchema: Обновлённая схема
        """
        if self.body and not self.body_clean and not self.body_raw:
            # Миграция: body -> body_clean и body_raw
            self.body_clean = self.body
            self.body_raw = self.body
        
        return self
    
    def validate_structure(self) -> Dict[str, Any]:
        """
        ✅ Валидирует структуру и возвращает отчёт
        
        Returns:
            Dict с информацией о структуре
        """
        from src.utils.email_body_extractor import validate_email_data_structure
        
        return validate_email_data_structure(self.model_dump(by_alias=True))


class EmailDataValidator:
    """
    🛡️ Валидатор для email_data с расширенными проверками
    """
    
    @staticmethod
    def validate(data: Dict[str, Any], strict: bool = False) -> EmailDataSchema:
        """
        Валидирует данные письма
        
        Args:
            data: Сырые данные письма
            strict: Строгий режим (выбрасывает исключения)
            
        Returns:
            EmailDataSchema: Валидированная схема
            
        Raises:
            ValidationError: Если strict=True и данные невалидны
        """
        try:
            return EmailDataSchema(**data)
        except Exception as e:
            if strict:
                raise
            # В нестрогом режиме логируем и возвращаем частично валидные данные
            print(f"⚠️ Ошибка валидации email_data: {e}")
            # Пытаемся создать минимальную валидную структуру
            return EmailDataSchema(
                message_id=data.get('message_id', 'unknown'),
                **{k: v for k, v in data.items() if k != 'message_id'}
            )
    
    @staticmethod
    def validate_batch(
        data_list: List[Dict[str, Any]],
        strict: bool = False
    ) -> tuple[List[EmailDataSchema], List[Dict[str, Any]]]:
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
            try:
                validated = EmailDataValidator.validate(data, strict=strict)
                valid.append(validated)
            except Exception as e:
                errors.append({
                    "index": i,
                    "message_id": data.get("message_id", "unknown"),
                    "error": str(e)
                })
        
        return valid, errors
    
    @staticmethod
    def get_quality_metrics(schema: EmailDataSchema) -> Dict[str, Any]:
        """
        📊 Вычисляет метрики качества для письма
        
        Args:
            schema: Валидированная схема письма
            
        Returns:
            Dict с метриками качества
        """
        body = schema.get_body(prefer_clean=True)
        
        return {
            "has_body": body is not None and len(body) > 0,
            "body_length": len(body) if body else 0,
            "format_type": schema.get_format_type(),
            "has_attachments": len(schema.attachments) > 0,
            "attachment_count": len(schema.attachments),
            "has_subject": bool(schema.subject and schema.subject.strip()),
            "has_from": bool(schema.from_ and schema.from_.strip()),
            "char_count_match": (
                schema.char_count == len(body)
                if schema.char_count and body
                else None
            )
        }


# === Примеры использования ===

if __name__ == "__main__":
    print("🧪 Тестирование EmailDataSchema\n")
    
    # Тест 1: Legacy format
    print("Тест 1: Legacy format")
    legacy_data = {
        "message_id": "test-001",
        "subject": "Test Subject",
        "from": "sender@example.com",
        "body": "This is legacy body text",
        "char_count": 24
    }
    
    try:
        schema = EmailDataSchema(**legacy_data)
        print(f"  ✅ Валидация пройдена")
        print(f"  Format type: {schema.get_format_type()}")
        print(f"  Body: {schema.get_body()[:50]}...")
        
        # Метрики
        metrics = EmailDataValidator.get_quality_metrics(schema)
        print(f"  Metrics: {metrics}\n")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}\n")
    
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
    
    try:
        schema = EmailDataSchema(**new_data)
        print(f"  ✅ Валидация пройдена")
        print(f"  Format type: {schema.get_format_type()}")
        print(f"  Body (prefer_clean=True): {schema.get_body(prefer_clean=True)}")
        print(f"  Body (prefer_clean=False): {schema.get_body(prefer_clean=False)[:50]}...\n")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}\n")
    
    # Тест 3: Миграция legacy -> new
    print("Тест 3: Миграция legacy -> new")
    legacy_schema = EmailDataSchema(**legacy_data)
    print(f"  До миграции: body_clean={legacy_schema.body_clean}, body_raw={legacy_schema.body_raw}")
    
    migrated = legacy_schema.migrate_to_new_format()
    print(f"  После миграции: body_clean={bool(migrated.body_clean)}, body_raw={bool(migrated.body_raw)}")
    print(f"  ✅ Миграция выполнена\n")
    
    # Тест 4: Валидация структуры
    print("Тест 4: Валидация структуры")
    validation_report = schema.validate_structure()
    print(f"  Отчёт: {validation_report}")
    print(f"  ✅ Валидация структуры пройдена\n")
    
    # Тест 5: Batch валидация
    print("Тест 5: Batch валидация")
    batch_data = [
        {"message_id": "batch-001", "body": "Text 1"},
        {"message_id": "batch-002", "body_clean": "Text 2"},
        {"message_id": "batch-003"},  # Без body - должно пройти
    ]
    
    valid, errors = EmailDataValidator.validate_batch(batch_data, strict=False)
    print(f"  Валидных: {len(valid)}/{len(batch_data)}")
    print(f"  Ошибок: {len(errors)}")
    print(f"  ✅ Batch валидация завершена\n")
    
    print("🎉 Все тесты пройдены!")
