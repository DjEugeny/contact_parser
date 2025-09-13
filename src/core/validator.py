#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 JSON Schema валидатор для новой структуры organizations/contacts
Поддерживает только новый формат согласно мини-ТЗ
"""

import json
import jsonschema
from typing import Dict, List, Optional, Any, Tuple
from jsonschema import ValidationError, SchemaError

class LLMResponseValidator:
    """🔍 Валидатор JSON Schema для новой структуры organizations/contacts"""

    def __init__(self):
        """Инициализация валидатора только для новой структуры"""
        self.phone_schema = self._create_phone_schema()
        self.organization_schema = self._create_organization_schema()
        self.contact_schema = self._create_contact_schema()
        self.commercial_offer_schema = self._create_commercial_offer_schema()
        self.full_response_schema = self._create_full_response_schema()

        print("✅ LLMResponseValidator инициализирован для новой структуры organizations/contacts")

    def _create_phone_schema(self) -> Dict[str, Any]:
        """📞 Создание схемы для телефона в новом формате"""
        return {
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
            "additionalProperties": True
        }

    def _create_organization_schema(self) -> Dict[str, Any]:
        """🏢 Создание схемы для организации"""
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
                "inn_validated": {
                    "type": ["boolean", "null"],
                    "description": "Результат валидации ИНН"
                },
                "website": {
                    "type": ["string", "null"],
                    "description": "Сайт организации"
                },
                "website_confidence": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Уверенность в сайте"
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
        """👤 Создание схемы для контакта"""
        return {
            "type": "object",
            "required": ["name", "email", "confidence"],
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
                    "description": "ID связанной организации"
                },
                "position": {
                    "type": ["string", "null"],
                    "maxLength": 200,
                    "description": "Должность контакта"
                },
                "email": {
                    "type": ["string", "null"],
                    "format": "email",
                    "description": "Email контакта"
                },
                "email_valid": {
                    "type": ["boolean", "null"],
                    "description": "Результат валидации email"
                },
                "phones": {
                    "type": "array",
                    "items": self.phone_schema,
                    "description": "Массив телефонов контакта"
                },
                "city": {
                    "type": ["string", "null"],
                    "maxLength": 100,
                    "description": "Город контакта"
                },
                "address": {
                    "type": ["string", "null"],
                    "maxLength": 500,
                    "description": "Адрес контакта"
                },
                "inn": {
                    "type": ["string", "null"],
                    "pattern": "^[0-9]{10,12}$",
                    "description": "ИНН контакта"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Уверенность в контакте"
                },
                "value_score": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "description": "Оценка ценности контакта"
                },
                "priority": {
                    "type": ["object", "null"],
                    "description": "Приоритет контакта"
                }
            },
            "additionalProperties": False
        }

    def _create_commercial_offer_schema(self) -> Dict[str, Any]:
        """💼 Создание схемы для коммерческого предложения"""
        return {
            "type": "object",
            "required": ["found"],
            "properties": {
                "found": {
                    "type": "boolean",
                    "description": "Найдено ли коммерческое предложение"
                },
                "offer_number": {
                    "type": ["string", "null"],
                    "description": "Номер коммерческого предложения"
                },
                "offer_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "description": "Дата коммерческого предложения"
                },
                "end_user": {
                    "type": ["string", "null"],
                    "description": "Конечный пользователь/заказчик"
                },
                "end_user_inn": {
                    "type": ["string", "null"],
                    "pattern": "^[0-9]{10,12}$",
                    "description": "ИНН конечного пользователя"
                },
                "intermediary": {
                    "type": ["string", "null"],
                    "description": "Посредник/контактное лицо"
                },
                "intermediary_data": {
                    "type": ["string", "null"],
                    "description": "Данные посредника (организация, телефон, email)"
                },
                "payment_terms": {
                    "type": ["string", "null"],
                    "description": "Условия оплаты"
                },
                "delivery_time": {
                    "type": ["string", "null"],
                    "description": "Срок поставки"
                },
                "delivery_terms": {
                    "type": ["string", "null"],
                    "description": "Условия поставки"
                },
                "valid_until": {
                    "type": ["string", "null"],
                    "description": "Действительно до"
                },
                "equipment_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Название оборудования"
                            },
                            "model": {
                                "type": ["string", "null"],
                                "description": "Модель"
                            },
                            "article": {
                                "type": ["string", "null"],
                                "description": "Артикул"
                            },
                            "quantity": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Количество"
                            },
                            "unit_price": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Цена за единицу"
                            },
                            "total_price": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Общая стоимость позиции"
                            },
                            "vat": {
                                "type": ["string", "null"],
                                "description": "НДС"
                            }
                        },
                        "required": ["name", "quantity", "unit_price", "total_price"],
                        "additionalProperties": False
                    },
                    "description": "Список оборудования в КП"
                },
                "total_cost": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "description": "Общая стоимость КП"
                },
                "currency": {
                    "type": ["string", "null"],
                    "default": "RUB",
                    "description": "Валюта"
                },
                "comments": {
                    "type": ["string", "null"],
                    "description": "Комментарии к КП"
                },
                "reason": {
                    "type": ["string", "null"],
                    "description": "Причина, по которой КП не найдено"
                }
            },
            "additionalProperties": False
        }

    def _create_full_response_schema(self) -> Dict[str, Any]:
        """📋 Создание полной схемы ответа в новом формате"""
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
                    "items": self.commercial_offer_schema,
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

    def validate_llm_response(self, response: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """🔍 Валидация ответа LLM в новом формате organizations/contacts"""
        errors = []
        corrected_response = response.copy()
        
        print("🔍 Валидация ответа в новом формате organizations/contacts")
        
        try:
            # Проверяем новую схему
            jsonschema.validate(response, self.full_response_schema)
            print("✅ JSON Schema валидация прошла успешно")
            return True, [], corrected_response
            
        except ValidationError as e:
            print(f"❌ JSON Schema валидация не прошла: {e.message}")
            
            # Детальный анализ ошибки
            detailed_errors = self._analyze_validation_error(e)
            errors.extend(detailed_errors)
            
            # Попытка автокоррекции
            try:
                corrected_response = self._auto_correct_response(response, e)
                
                # Повторная валидация исправленного ответа
                jsonschema.validate(corrected_response, self.full_response_schema)
                print("✅ Автокоррекция успешна, валидация прошла")
                return True, errors, corrected_response
                
            except (ValidationError, SchemaError) as correction_error:
                print(f"❌ Автокоррекция не удалась: {correction_error}")
                errors.append(f"Автокоррекция не удалась: {correction_error}")
                
                # Graceful degradation fallback
                fallback_response = self.graceful_degradation_fallback(response)
                return False, errors, fallback_response
                
        except SchemaError as e:
            print(f"❌ Ошибка в самой схеме: {e.message}")
            errors.append(f"Ошибка схемы: {e.message}")
            return False, errors, response

    def _analyze_validation_error(self, error: ValidationError) -> List[str]:
        """🔍 Детальный анализ ошибки валидации"""
        errors = []
        
        # Основная ошибка
        errors.append(f"Ошибка валидации: {error.message}")
        
        # Путь к ошибке
        if error.absolute_path:
            path = ' -> '.join(str(p) for p in error.absolute_path)
            errors.append(f"Путь к ошибке: {path}")
        
        # Значение, вызвавшее ошибку
        if hasattr(error, 'instance'):
            errors.append(f"Проблемное значение: {error.instance}")
        
        return errors

    def _auto_correct_response(self, response: Dict[str, Any], error: ValidationError) -> Dict[str, Any]:
        """🔧 Автокоррекция ответа"""
        corrected = response.copy()
        
        # Добавляем отсутствующие обязательные поля
        if 'organizations' not in corrected:
            corrected['organizations'] = []
            print("🔧 Добавлен пустой массив organizations")
        
        if 'contacts' not in corrected:
            corrected['contacts'] = []
            print("🔧 Добавлен пустой массив contacts")
        
        # Исправляем контакты
        if 'contacts' in corrected:
            for i, contact in enumerate(corrected['contacts']):
                if not isinstance(contact, dict):
                    continue
                    
                # Добавляем обязательные поля контакта
                if 'confidence' not in contact:
                    contact['confidence'] = 0.5
                    print(f"🔧 Добавлен confidence для контакта {i}")
        
        # Исправляем организации
        if 'organizations' in corrected:
            for i, org in enumerate(corrected['organizations']):
                if not isinstance(org, dict):
                    continue
                    
                # Добавляем обязательные поля организации
                if 'organization_id' not in org:
                    org['organization_id'] = i + 1
                    print(f"🔧 Добавлен organization_id для организации {i}")
                    
                if 'name' not in org or not org['name']:
                    org['name'] = f"Организация {i + 1}"
                    print(f"🔧 Добавлено название для организации {i}")
        
        return corrected

    def graceful_degradation_fallback(self, invalid_response: Dict[str, Any]) -> Dict[str, Any]:
        """🛡️ Fallback для невалидных ответов"""
        print("🛡️ Применяем graceful degradation fallback")
        
        return {
            "organizations": [],
            "contacts": [],
            "business_context": "Ошибка валидации",
            "summary": {"topic": "Ошибка обработки"},
            "key_points": [],
            "commercial_offers": [],
            "validation_error": True,
            "original_response": invalid_response
        }

    def validate_organizations(self, organizations: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """🏢 Валидация массива организаций"""
        errors = []
        
        for i, org in enumerate(organizations):
            try:
                jsonschema.validate(org, self.organization_schema)
            except ValidationError as e:
                errors.append(f"Организация {i}: {e.message}")
        
        return len(errors) == 0, errors

    def validate_contacts(self, contacts: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """👤 Валидация массива контактов"""
        errors = []
        
        for i, contact in enumerate(contacts):
            try:
                jsonschema.validate(contact, self.contact_schema)
            except ValidationError as e:
                errors.append(f"Контакт {i}: {e.message}")
        
        return len(errors) == 0, errors

    def validate_commercial_offers(self, commercial_offers: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """💼 Валидация массива коммерческих предложений"""
        errors = []
        
        for i, offer in enumerate(commercial_offers):
            try:
                jsonschema.validate(offer, self.commercial_offer_schema)
                
                # Дополнительная бизнес-валидация
                validation_errors = self._validate_commercial_offer_business_rules(offer, i)
                errors.extend(validation_errors)
                
            except ValidationError as e:
                errors.append(f"КП {i}: {e.message}")
        
        return len(errors) == 0, errors

    def _validate_commercial_offer_business_rules(self, offer: Dict[str, Any], index: int) -> List[str]:
        """🔍 Валидация бизнес-правил для коммерческого предложения"""
        errors = []
        
        # Если КП найдено, должны быть заполнены ключевые поля
        if offer.get('found', False):
            required_fields = ['offer_number', 'offer_date', 'total_cost']
            for field in required_fields:
                if not offer.get(field):
                    errors.append(f"КП {index}: Для найденного КП обязательно поле '{field}'")
            
            # Проверка equipment_items
            equipment_items = offer.get('equipment_items', [])
            if not equipment_items:
                errors.append(f"КП {index}: Для найденного КП должен быть список оборудования")
            else:
                # Проверка соответствия total_cost сумме позиций
                total_from_items = sum(item.get('total_price', 0) for item in equipment_items)
                total_cost = offer.get('total_cost', 0)
                if total_cost and abs(total_from_items - total_cost) > 0.01:
                    errors.append(f"КП {index}: Несоответствие общей суммы ({total_cost}) и суммы позиций ({total_from_items})")
        
        return errors

    def postprocess_commercial_offers(self, commercial_offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """💼 Постобработка коммерческих предложений"""
        processed_offers = []
        
        for offer in commercial_offers:
            processed_offer = offer.copy()
            
            # Нормализация валюты
            if 'currency' not in processed_offer or not processed_offer['currency']:
                processed_offer['currency'] = 'RUB'
            
            # Валидация и исправление equipment_items
            if 'equipment_items' in processed_offer:
                processed_items = []
                for item in processed_offer['equipment_items']:
                    processed_item = item.copy()
                    
                    # Проверка соответствия total_price = quantity * unit_price
                    if all(k in processed_item for k in ['quantity', 'unit_price']):
                        calculated_total = processed_item['quantity'] * processed_item['unit_price']
                        if 'total_price' not in processed_item or abs(processed_item['total_price'] - calculated_total) > 0.01:
                            processed_item['total_price'] = calculated_total
                    
                    processed_items.append(processed_item)
                
                processed_offer['equipment_items'] = processed_items
                
                # Пересчет общей стоимости
                if processed_items:
                    calculated_total_cost = sum(item.get('total_price', 0) for item in processed_items)
                    processed_offer['total_cost'] = calculated_total_cost
            
            processed_offers.append(processed_offer)
        
        return processed_offers

    def validate_and_postprocess(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """🔄 Основной метод валидации и постобработки"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'processed_data': data.copy(),
            'stats': {}
        }
        
        # Валидация контактов
        if 'contacts' in data:
            contacts_valid, contacts_errors = self.validate_contacts(data['contacts'])
            if not contacts_valid:
                result['valid'] = False
                result['errors'].extend(contacts_errors)
            
            # Постобработка контактов
            processed_contacts = self.postprocess_contacts(data['contacts'])
            result['processed_data']['contacts'] = processed_contacts
        
        # Валидация коммерческих предложений
        if 'commercial_offers' in data:
            offers_valid, offers_errors = self.validate_commercial_offers(data['commercial_offers'])
            if not offers_valid:
                result['valid'] = False
                result['errors'].extend(offers_errors)
            
            # Постобработка коммерческих предложений
            processed_offers = self.postprocess_commercial_offers(data['commercial_offers'])
            result['processed_data']['commercial_offers'] = processed_offers
        
        # Сбор статистики
        result['stats'] = self.get_validation_stats()
        
        return result

    def get_validation_stats(self) -> Dict[str, Any]:
        """📊 Получение статистики валидации"""
        return {
            "validator_version": "2.0.0",
            "supported_format": "organizations/contacts",
            "schemas_loaded": {
                "organization_schema": bool(self.organization_schema),
                "contact_schema": bool(self.contact_schema),
                "phone_schema": bool(self.phone_schema),
                "commercial_offer_schema": bool(self.commercial_offer_schema),
                "full_response_schema": bool(self.full_response_schema)
            }
        }


# Пример использования
if __name__ == "__main__":
    validator = LLMResponseValidator()
    
    # Тестовый ответ в новом формате
    test_response = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            }
        ],
        "contacts": [
            {
                "name": "Гоголева Мария",
                "organization_id": 1,
                "email": "m.gogoleva@dna-technology.ru",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7(495) 640-17-71"
                    }
                ],
                "confidence": 0.95
            }
        ]
    }
    
    # Валидация
    is_valid, errors, corrected = validator.validate_llm_response(test_response)
    print(f"Валидация: {is_valid}")
    if errors:
        print(f"Ошибки: {errors}")
    
    # Статистика
    stats = validator.get_validation_stats()
    print(f"Статистика: {stats}")
