#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интеграции ContactPhoneEnricher в PostProcessor
Проверяет, что обогащение телефонов контактов работает в пайплайне
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from postprocessing.postprocessor import PostProcessor


def test_phone_enrichment_integration():
    """Тест интеграции обогащения телефонов в постпроцессор"""
    
    # Создаем тестовые данные
    llm_result = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ООО Тестовая Компания",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7 (495) 123-45-67",
                        "normalized": "+74951234567",
                        "original": "495 123-45-67"
                    },
                    {
                        "type": "office",
                        "number": "+7 (495) 765-43-21",
                        "normalized": "+74957654321",
                        "original": "495 765-43-21"
                    }
                ],
                "emails": ["info@test.com"],
                "city": "Москва",
                "domain": "test.com"
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "organization_id": 1,
                "name": "Иван Иванов",
                "position": "Менеджер",
                "email": "ivanov@test.com",
                "phones": [],  # Пустой массив - кандидат для обогащения
                "city": "Москва",
                "role_in_message": "sender",
                "value_score": 8
            },
            {
                "contact_id": 2,
                "organization_id": 1,
                "name": "Петр Петров",
                "email": "petrov@test.com",
                "phones": [],
                "value_score": 5
            }
        ],
        "interactions": [],
        "summary": {"brief": "Тестовое письмо"},
        "key_points": [],
        "business_context": "",
        "commercial_offers": []
    }
    
    # Создаем постпроцессор
    processor = PostProcessor()
    
    # Проверяем, что ContactPhoneEnricher инициализирован
    assert processor.contact_phone_enricher is not None, "ContactPhoneEnricher не инициализирован"
    print("✅ ContactPhoneEnricher успешно инициализирован")
    
    # Обрабатываем результат
    result = processor.process_llm_response(llm_result)
    
    # Проверяем, что обработка прошла успешно
    assert "contacts" in result, "Отсутствует поле contacts в результате"
    assert "postprocessing_metadata" in result, "Отсутствует postprocessing_metadata"
    
    # Проверяем метаданные обогащения телефонов
    metadata = result.get("postprocessing_metadata", {})
    enrichment = metadata.get("enrichment", {})
    
    assert "contact_phone_enrichment" in enrichment, "Отсутствуют метаданные contact_phone_enrichment"
    print("✅ Метаданные contact_phone_enrichment присутствуют")
    
    phone_enrichment = enrichment["contact_phone_enrichment"]
    stats = phone_enrichment.get("statistics", {})
    
    print(f"\n📊 Статистика обогащения телефонов:")
    print(f"  • Обработано контактов: {stats.get('contacts_processed', 0)}")
    print(f"  • Обогащено контактов: {stats.get('contacts_enriched', 0)}")
    print(f"  • Добавлено телефонов: {stats.get('phones_added_total', 0)}")
    print(f"  • Пропущено телефонов: {stats.get('phones_skipped_total', 0)}")
    print(f"  • Средняя уверенность: {stats.get('avg_confidence', 0):.2f}")
    
    # Проверяем, что контакты получили телефоны
    contacts = result.get("contacts", [])
    enriched_contacts = [c for c in contacts if c.get("phones")]
    
    print(f"\n📞 Контакты с телефонами: {len(enriched_contacts)} из {len(contacts)}")
    
    for contact in enriched_contacts:
        contact_name = contact.get("name", "unknown")
        phones = contact.get("phones", [])
        print(f"\n  👤 {contact_name}:")
        for phone in phones:
            phone_number = phone.get("number", "unknown")
            phone_source = phone.get("source", "unknown")
            phone_confidence = phone.get("confidence", 0)
            print(f"    📱 {phone_number} (source: {phone_source}, confidence: {phone_confidence})")
    
    # Проверяем, что телефоны нормализованы
    for contact in contacts:
        for phone in contact.get("phones", []):
            if isinstance(phone, dict):
                # Проверяем наличие обязательных полей
                assert "number" in phone, f"Отсутствует поле 'number' в телефоне контакта {contact.get('name')}"
                assert "normalized" in phone, f"Отсутствует поле 'normalized' в телефоне контакта {contact.get('name')}"
                
                # Проверяем, что нет лишних полей (санитизация)
                allowed_fields = {"type", "number", "normalized", "original", "extension", "source", "org_gid", "confidence", "enriched_at"}
                extra_fields = set(phone.keys()) - allowed_fields
                if extra_fields:
                    print(f"⚠️ Обнаружены дополнительные поля в телефоне: {extra_fields}")
    
    print("\n✅ Все проверки пройдены успешно!")
    print("✅ Интеграция ContactPhoneEnricher в PostProcessor работает корректно")
    
    return result


if __name__ == "__main__":
    try:
        result = test_phone_enrichment_integration()
        print("\n" + "="*60)
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО")
        print("="*60)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
