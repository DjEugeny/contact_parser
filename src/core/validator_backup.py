#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Модуль строгой JSON Schema валидации для CONTACT_PARSER
Фаза 4: Строгая JSON Schema валидация
"""

import json
import jsonschema
from typing import Dict, List, Optional, Any, Tuple
from jsonschema import ValidationError, SchemaError

class LLMResponseValidator:
    """🔍 Строгий валидатор JSON Schema для ответов LLM"""

    def __init__(self):
        """Инициализация валидатора с детальными схемами"""
        self.organization_schema = self._create_organization_schema()  # Новая схема организаций
        self.contact_schema = self._create_contact_schema()
        self.business_context_schema = self._create_business_context_schema()
        self.commercial_offers_schema = self._create_commercial_offers_schema()
        self.full_response_schema = self._create_full_response_schema()
        self.new_format_schema = self._create_new_format_schema()  # Новый формат

        print("✅ LLMResponseValidator инициализирован с поддержкой новой структуры organizations/contacts")

    def _create_organization_schema(self) -> Dict[str, Any]:
        """🏢 Создание схемы для организации (новый формат)"""
        return {
            "type": "object",
            "required": ["organization_id", "name"],
            "properties": {
                "organization_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Уникальный ID организации"
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 300,
                    "description": "Название организации"
                },
                "inn": {
                    "type": ["string", "null"],
                    "pattern": "^[0-9]{10,12}$",
                    "description": "ИНН организации (10 или 12 цифр)"
                },
                "website": {
                    "type": ["string", "null"],
                    "format": "uri",
                    "description": "Сайт организации"
                },
                "city": {
                    "type": ["string", "null"],
                    "maxLength": 100,
                    "description": "Город организации"
                },
                "address": {
                    "type": ["string", "null"],
                    "maxLength": 500,
                    "description": "Адрес организации"
                },
                "emails": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "email"
                    },
                    "uniqueItems": True,
                    "description": "Массив email адресов организации"
                },
                "phones": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 1
                    },
                    "uniqueItems": True,
                    "description": "Массив телефонов организации"
                }
            },
            "additionalProperties": False
        }

    def _create_contact_schema(self) -> Dict[str, Any]:
        """📞 Создание схемы для контакта (поддержка старой и новой структуры)"""
        return {
            "type": "object",
            "required": ["name", "email", "confidence"],  # Убрали phone и organization из обязательных
            "properties": {
                "contact_id": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "Уникальный ID контакта"
                },
                "name": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Имя контактного лица"
                },
                "organization_id": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "ID связанной организации (новый формат)"
                },
                "organization": {
                    "type": ["string", "null"],
                    "maxLength": 300,
                    "description": "Название организации (старый формат)"
                },
                "position": {
                    "type": ["string", "null"],
                    "maxLength": 200,
                    "description": "Должность контакта"
                },
                "phones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type", "number"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["main", "mobile", "office", "fax", "other"],
                                "description": "Тип телефона"
                            },
                            "number": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Номер телефона"
                            },
                            "normalized": {
                                "type": ["string", "null"],
                                "description": "Нормализованный номер"
                            },
                            "original": {
                                "type": ["string", "null"],
                                "description": "Оригинальный номер"
                            }
                        },
                        "additionalProperties": False
                    },
                    "description": "Массив телефонов (новый формат)"
                },
                "phone": {
                    "type": ["string", "null"],
                    "description": "Оригинальный телефон из LLM (старый формат)"
                },
                "raw_phone": {
                    "type": ["string", "null"],
                    "description": "Дубликат оригинального телефона"
                },
                "normalized_phone": {
                    "type": ["string", "null"],
                    "description": "Нормализованный телефон для сравнения"
                },
                "formatted_phone": {
                    "type": ["string", "null"],
                    "description": "Форматированный телефон для отображения"
                },
                "phone_type": {
                    "type": ["string", "null"],
                    "enum": ["мобильный", "городской", "неизвестный", "короткий", None],
                    "description": "Тип телефона"
                },
                "phone_extension": {
                    "type": ["string", "null"],
                    "description": "Добавочный номер"
                },
                "phone_confidence": {
                    "type": ["number", "null"],
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Уверенность в корректности нормализации телефона"
                },
                "email": {
                    "type": ["string", "null"],
                    "format": "email",
                    "description": "Email адрес"
                },
                "organization": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "maxLength": 300,
                    "description": "Название организации"
                },
                "position": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Должность"
                },
                "city": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Город"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Общая уверенность в контакте"
                },
                "source": {
                    "type": ["string", "null"],
                    "enum": ["email_body", "attachment", "signature", None],
                    "description": "Источник извлечения контакта"
                },
                "inn": {
                    "type": ["string", "null"],
                    "pattern": "^\\d{10}(\\d{2})?$",
                    "description": "ИНН организации или ИП"
                },
                "inn_type": {
                    "type": ["string", "null"],
                    "enum": ["organization", "individual", "invalid"],
                    "description": "Тип ИНН (юридическое лицо или ИП)"
                },
                "inn_validated": {
                    "type": "boolean",
                    "description": "Прошел ли ИНН валидацию по алгоритму ФНС"
                },
                "website": {
                    "type": ["string", "null"],
                    "format": "uri",
                    "description": "Сайт компании"
                },
                "website_confidence": {
                    "type": ["number", "null"],
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Уверенность в корректности сайта"
                }            },
            "additionalProperties": False  # Запрещаем дополнительные поля
        }

    def _create_new_format_schema(self) -> Dict[str, Any]:
        """🆕 Создание схемы для нового формата с organizations/contacts"""
        return {
            "type": "object",
            "required": ["organizations", "contacts"],
            "properties": {
                "organizations": {
                    "type": "array",
                    "items": self.organization_schema,
                    "description": "Массив организаций"
                },
                "contacts": {
                    "type": "array",
                    "items": self.contact_schema,
                    "description": "Массив контактов"
                },
                "business_context": {
                    "type": ["string", "object", "null"],
                    "description": "Бизнес-контекст письма"
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": ["string", "null"]},
                        "communication_stage": {"type": ["string", "null"]}
                    },
                    "additionalProperties": True
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ключевые моменты"
                },
                "commercial_offers": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Коммерческие предложения"
                },
                "postprocessing_metadata": {
                    "type": ["object", "null"],
                    "properties": {
                        "processed_at": {"type": "string"},
                        "stats": {"type": "object"},
                        "version": {"type": "string"}
                    },
                    "additionalProperties": True,
                    "description": "Метаданные постобработки"
                }
            },
            "additionalProperties": True
        }

    def _create_business_context_schema(self) -> Dict[str, Any]:
        """💼 Создание схемы для бизнес-контекста"""
        return {
            "type": ["string", "null"],
            "minLength": 1,
            "maxLength": 2000,
            "description": "Краткое описание бизнес-контекста переписки"
        }

    def _create_commercial_offers_schema(self) -> Dict[str, Any]:
        """💰 Создание схемы для коммерческих предложений"""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["found", "supplier"],
                "properties": {
                    "found": {
                        "type": "boolean",
                        "description": "Найдено ли коммерческое предложение"
                    },
                    "supplier": {
                        "type": ["object", "string", "null"],
                        "description": "Информация о поставщике"
                    },
                    "products": {
                        "type": "array",
                        "description": "Список продуктов/услуг"
                    },
                    "total_amount": {
                        "type": ["number", "string", "null"],
                        "description": "Общая сумма"
                    },
                    "currency": {
                        "type": ["string", "null"],
                        "enum": ["RUB", "USD", "EUR", "KZT", "BYN", None],
                        "description": "Валюта"
                    },
                    "valid_until": {
                        "type": ["string", "null"],
                        "description": "Срок действия предложения"
                    },
                    "confidence": {
                        "type": ["number", "null"],
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Уверенность в анализе КП"
                    }
                },
                "additionalProperties": True
            }
        }

    def _create_full_response_schema(self) -> Dict[str, Any]:
        """📋 Создание полной схемы ответа LLM"""
        return {
            "type": "object",
            "required": ["contacts", "business_context", "commercial_offers"],
            "properties": {
                "contacts": {
                    "type": "array",
                    "items": self.contact_schema,
                    "description": "Массив извлеченных контактов"
                },
                "business_context": self.business_context_schema,
                "commercial_offers": self.commercial_offers_schema,
                "summary": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": ["string", "null"]},
                        "product_interest": {"type": ["string", "null"]},
                        "communication_stage": {"type": ["string", "null"]},
                        "request_type": {"type": ["string", "null"]}
                    },
                    "additionalProperties": False
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 0,
                    "maxItems": 10
                },
                "provider_used": {
                    "type": ["string", "null"],
                    "description": "Использованный LLM провайдер"
                },
                "processing_time": {
                    "type": ["string", "null"],
                    "description": "Время обработки"
                },
                "text_length": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "description": "Длина обработанного текста"
                },
                "chunks_processed": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "description": "Количество обработанных чанков"
                },
                "total_contacts_found": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "description": "Общее количество найденных контактов"
                },
                "unique_contacts_found": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "description": "Количество уникальных контактов"
                },
                "processing_method": {
                    "type": ["string", "null"],
                    "enum": ["sync", "async", "chunked", None],
                    "description": "Метод обработки"
                },
                "error": {
                    "type": ["string", "null"],
                    "description": "Сообщение об ошибке"
                }
            },
            "additionalProperties": False
        }

    def validate_llm_response(self, response: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        ✅ Строгая валидация ответа LLM с поддержкой старой и новой структуры

        Args:
            response: Ответ LLM для валидации

        Returns:
            tuple: (is_valid, error_messages, corrected_response)
        """
        if not isinstance(response, dict):
            return False, ["Ответ должен быть JSON объектом"], {}

        errors = []
        corrected_response = response.copy()
        
        # Определяем формат ответа
        is_new_format = 'organizations' in response and 'contacts' in response
        schema_to_use = self.new_format_schema if is_new_format else self.full_response_schema
        
        format_type = "новый (organizations/contacts)" if is_new_format else "старый (contacts)"
        print(f"🔍 Валидация ответа в {format_type} формате")

        try:
            # Основная валидация схемы
            jsonschema.validate(response, schema_to_use)
            print("✅ JSON Schema валидация пройдена успешно")
            return True, [], response

        except ValidationError as e:
            print(f"❌ Ошибка валидации JSON Schema: {e.message}")
            errors.append(f"JSON Schema: {e.message}")

            # Детальная диагностика
            error_details = self._analyze_validation_error(e)
            errors.extend(error_details)

            # Попытка автоматического исправления
            corrected_response = self._auto_correct_response(response, e)
            if corrected_response != response:
                print("🔧 Автоматическое исправление применено")
                # Повторная валидация после исправления
                try:
                    jsonschema.validate(corrected_response, schema_to_use)
                    print("✅ Исправленный ответ прошел валидацию")
                    return True, errors, corrected_response
                except ValidationError as e2:
                    errors.append(f"Исправленный ответ все еще содержит ошибки: {e2.message}")

        except SchemaError as e:
            errors.append(f"Ошибка в схеме валидации: {e.message}")

        except Exception as e:
            errors.append(f"Неожиданная ошибка валидации: {str(e)}")

        return False, errors, corrected_response

    def _analyze_validation_error(self, error: ValidationError) -> List[str]:
        """🔍 Детальный анализ ошибки валидации"""
        details = []

        # Анализ пути ошибки
        path = list(error.path)
        if path:
            path_str = ".".join(str(p) for p in path)
            details.append(f"Путь ошибки: {path_str}")

        # Анализ типа ошибки
        if "required" in error.message:
            details.append("Отсутствует обязательное поле")
        elif "type" in error.message:
            details.append("Неверный тип данных")
        elif "enum" in error.message:
            details.append("Значение не соответствует допустимым вариантам")
        elif "format" in error.message:
            details.append("Неверный формат данных")
        elif "additionalProperties" in error.message:
            details.append("Найдены недопустимые дополнительные поля")

        # Специфические рекомендации
        if "contacts" in str(error.path):
            if "phone" in str(error.path):
                details.append("Рекомендация: Проверьте формат телефона (должен быть строкой)")
            elif "email" in str(error.path):
                details.append("Рекомендация: Проверьте формат email")
            elif "confidence" in str(error.path):
                details.append("Рекомендация: Confidence должен быть числом от 0.0 до 1.0")

        return details

    def _auto_correct_response(self, response: Dict[str, Any], error: ValidationError) -> Dict[str, Any]:
        """
        🔧 Автоматическое исправление мелких несоответствий
        """
        corrected = response.copy()

        try:
            # Исправление отсутствующих обязательных полей
            if "contacts" not in corrected:
                corrected["contacts"] = []
                print("  🔧 Добавлено поле 'contacts': []")

            if "business_context" not in corrected:
                corrected["business_context"] = "Контекст не определен"
                print("  🔧 Добавлено поле 'business_context': 'Контекст не определен'")

            if "commercial_offers" not in corrected:
                corrected["commercial_offers"] = []
                print("  🔧 Добавлено поле 'commercial_offers': []")

            # Исправление типов данных
            if "contacts" in corrected and isinstance(corrected["contacts"], list):
                for i, contact in enumerate(corrected["contacts"]):
                    if isinstance(contact, dict):
                        # Исправление confidence
                        if "confidence" in contact:
                            conf = contact["confidence"]
                            if isinstance(conf, str):
                                try:
                                    contact["confidence"] = float(conf)
                                    print(f"  🔧 Исправлен confidence контакта {i}: {conf} -> {float(conf)}")
                                except ValueError:
                                    contact["confidence"] = 0.5
                                    print(f"  🔧 Установлен confidence по умолчанию для контакта {i}: 0.5")

                        # Исправление phone_confidence
                        if "phone_confidence" in contact and isinstance(contact["phone_confidence"], str):
                            try:
                                contact["phone_confidence"] = float(contact["phone_confidence"])
                                print(f"  🔧 Исправлен phone_confidence контакта {i}")
                            except ValueError:
                                contact["phone_confidence"] = None

            # Исправление business_context
            if "business_context" in corrected:
                bc = corrected["business_context"]
                if isinstance(bc, dict):
                    # Преобразуем объект в строку
                    parts = []
                    for key, value in bc.items():
                        if value:
                            parts.append(f"{key}: {value}")
                    corrected["business_context"] = "; ".join(parts) if parts else "Контекст не определен"
                    print("  🔧 Преобразован business_context из объекта в строку")

        except Exception as e:
            print(f"  ⚠️ Ошибка при автоматическом исправлении: {e}")

        return corrected

    def validate_contact_list(self, contacts: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        👥 Валидация списка контактов

        Args:
            contacts: Список контактов для валидации

        Returns:
            tuple: (is_valid, error_messages)
        """
        if not isinstance(contacts, list):
            return False, ["Контакты должны быть массивом"]

        errors = []
        valid_contacts = 0

        for i, contact in enumerate(contacts):
            try:
                jsonschema.validate(contact, self.contact_schema)
                valid_contacts += 1
            except ValidationError as e:
                errors.append(f"Контакт {i}: {e.message}")
            except Exception as e:
                errors.append(f"Контакт {i}: Неожиданная ошибка - {str(e)}")

        is_valid = len(errors) == 0
        if is_valid:
            print(f"✅ Все {valid_contacts} контактов прошли валидацию")
        else:
            print(f"❌ {len(errors)} ошибок валидации контактов из {len(contacts)}")

        return is_valid, errors

    def get_validation_stats(self) -> Dict[str, Any]:
        """📊 Статистика валидации"""
        return {
            "schemas_loaded": True,
            "contact_schema_fields": len(self.contact_schema.get("properties", {})),
            "full_schema_required_fields": len(self.full_response_schema.get("required", [])),
            "auto_correction_enabled": True
        }

    def graceful_degradation_fallback(self, invalid_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        🛡️ Graceful degradation при ошибках валидации
        Создает минимально валидный ответ
        """
        fallback = {
            "contacts": [],
            "business_context": "Ошибка обработки контекста",
            "commercial_offers": [],
            "error": "Ответ LLM не прошел валидацию JSON Schema",
            "validation_failed": True
        }

        # Попытка спасти хотя бы контакты
        if "contacts" in invalid_response and isinstance(invalid_response["contacts"], list):
            # Фильтруем только валидные контакты
            valid_contacts = []
            for contact in invalid_response["contacts"]:
                if isinstance(contact, dict):
                    # Проверяем наличие обязательных полей
                    required_fields = ["name", "phone", "email", "organization", "confidence"]
                    if all(field in contact for field in required_fields):
                        valid_contacts.append(contact)

            if valid_contacts:
                fallback["contacts"] = valid_contacts
                fallback["business_context"] = invalid_response.get("business_context", fallback["business_context"])

        print("🛡️ Применен graceful degradation - создан минимально валидный ответ")
        return fallback
