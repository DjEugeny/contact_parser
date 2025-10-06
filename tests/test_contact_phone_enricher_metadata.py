#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы метаданных и статистики ContactPhoneEnricher
Проверяет Requirements 5.1, 5.2, 5.3, 5.4
"""

import sys
import json
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.postprocessing.contact_phone_enricher import ContactPhoneEnricher


def test_metadata_and_statistics():
    """Тест системы метаданных и статистики"""
    
    print("🧪 Тест системы метаданных и статистики ContactPhoneEnricher\n")
    
    # Инициализация enricher
    config = {
        "enabled": True,
        "min_confidence_threshold": 0.5,
        "review_threshold": 0.75,
        "allowed_phone_types": ["main", "office", "fax"],
        "enrichment_mode": "balanced",
    }
    
    enricher = ContactPhoneEnricher(config)
    
    # Тестовые данные
    organizations = [
        {
            "gid": "org_001",
            "name": "ООО Тестовая Компания",
            "domain": "test.com",
            "city": "Москва",
            "phones": [
                {
                    "type": "main",
                    "number": "+7 (495) 123-45-67",
                    "normalized": "+74951234567",
                },
                {
                    "type": "office",
                    "number": "+7 (495) 123-45-68",
                    "normalized": "+74951234568",
                },
                {
                    "type": "mobile",
                    "number": "+7 (999) 888-77-66",
                    "normalized": "+79998887766",
                },
            ],
        },
        {
            "gid": "org_002",
            "name": "ООО Компания без телефонов",
            "domain": "nophones.com",
            "city": "Санкт-Петербург",
            "phones": [],
        },
    ]
    
    contacts = [
        # Контакт 1: Высокий confidence, должен быть обогащен
        {
            "gid": "contact_001",
            "name": "Иван Иванов",
            "organization_id": "org_001",
            "emails": [{"email": "ivan@test.com"}],
            "position": "Директор",
            "role_in_message": "sender",
            "city": "Москва",
            "value_score": 8,
            "phones": [],
        },
        # Контакт 2: Низкий confidence, не должен быть обогащен
        {
            "gid": "contact_002",
            "name": "Петр Петров",
            "organization_id": "org_001",
            "emails": [],
            "position": None,
            "role_in_message": None,
            "city": None,
            "value_score": 3,
            "phones": [],
        },
        # Контакт 3: Организация без телефонов
        {
            "gid": "contact_003",
            "name": "Сидор Сидоров",
            "organization_id": "org_002",
            "emails": [{"email": "sidor@nophones.com"}],
            "position": "Менеджер",
            "role_in_message": "recipient",
            "city": "Санкт-Петербург",
            "value_score": 7,
            "phones": [],
        },
        # Контакт 4: Без organization_id
        {
            "gid": "contact_004",
            "name": "Анна Аннова",
            "organization_id": None,
            "emails": [],
            "position": None,
            "role_in_message": None,
            "city": None,
            "value_score": 5,
            "phones": [],
        },
    ]
    
    # Выполняем обогащение
    result = enricher.enrich_contacts_phones(contacts, organizations)
    
    print("=" * 80)
    print("📊 РЕЗУЛЬТАТЫ ОБОГАЩЕНИЯ")
    print("=" * 80)
    
    # Проверяем структуру результата
    print("\n✅ Проверка структуры результата:")
    assert "contacts" in result, "Отсутствует поле 'contacts'"
    assert "statistics" in result, "Отсутствует поле 'statistics'"
    assert "timestamp" in result, "Отсутствует поле 'timestamp'"
    assert "config" in result, "Отсутствует поле 'config'"
    print("   ✓ Все обязательные поля присутствуют")
    
    # Проверяем статистику (Requirement 5.4)
    print("\n✅ Проверка статистики (Requirement 5.4):")
    stats = result["statistics"]
    
    required_stats = [
        "contacts_processed",
        "contacts_enriched",
        "phones_added_total",
        "avg_confidence",
        "phones_skipped_by_reason",
    ]
    
    for stat_key in required_stats:
        assert stat_key in stats, f"Отсутствует статистика '{stat_key}'"
        print(f"   ✓ {stat_key}: {stats[stat_key]}")
    
    # Проверяем причины пропуска (Requirement 5.3)
    print("\n✅ Проверка причин пропуска (Requirement 5.3):")
    skip_reasons = stats["phones_skipped_by_reason"]
    
    required_reasons = [
        "low_confidence",
        "no_org_phones",
        "already_has_phones",
        "mobile_only",
    ]
    
    for reason in required_reasons:
        assert reason in skip_reasons, f"Отсутствует причина '{reason}'"
        print(f"   ✓ {reason}: {skip_reasons[reason]}")
    
    # Проверяем метаданные контактов (Requirements 5.1, 5.2)
    print("\n✅ Проверка метаданных контактов (Requirements 5.1, 5.2):")
    contacts_metadata = result["contacts"]
    
    assert len(contacts_metadata) == 4, f"Ожидалось 4 контакта, получено {len(contacts_metadata)}"
    print(f"   ✓ Обработано контактов: {len(contacts_metadata)}")
    
    # Проверяем структуру метаданных для каждого контакта
    for contact_meta in contacts_metadata:
        required_fields = [
            "contact_gid",
            "contact_name",
            "phones_added",
            "phones_skipped",
            "confidence_scores",
            "skip_reasons",
        ]
        
        for field in required_fields:
            assert field in contact_meta, f"Отсутствует поле '{field}' в метаданных контакта"
    
    print("   ✓ Все контакты имеют корректную структуру метаданных")
    
    # Детальная проверка контакта 1 (должен быть обогащен)
    print("\n✅ Детальная проверка контакта 1 (высокий confidence):")
    contact_1_meta = next(c for c in contacts_metadata if c["contact_gid"] == "contact_001")
    
    print(f"   • Имя: {contact_1_meta['contact_name']}")
    print(f"   • Добавлено телефонов: {len(contact_1_meta['phones_added'])}")
    print(f"   • Пропущено телефонов: {len(contact_1_meta['phones_skipped'])}")
    print(f"   • Confidence scores: {contact_1_meta['confidence_scores']}")
    
    if contact_1_meta["decision"]:
        print(f"   • Решение: {contact_1_meta['decision']['decision']}")
        print(f"   • Confidence: {contact_1_meta['decision']['confidence']:.2f}")
    
    # Проверяем, что телефоны были добавлены
    assert len(contact_1_meta["phones_added"]) > 0, "Контакт 1 должен быть обогащен"
    print("   ✓ Контакт успешно обогащен")
    
    # Детальная проверка контакта 2 (низкий confidence)
    print("\n✅ Детальная проверка контакта 2 (низкий confidence):")
    contact_2_meta = next(c for c in contacts_metadata if c["contact_gid"] == "contact_002")
    
    print(f"   • Имя: {contact_2_meta['contact_name']}")
    print(f"   • Добавлено телефонов: {len(contact_2_meta['phones_added'])}")
    print(f"   • Причины пропуска: {contact_2_meta['skip_reasons']}")
    
    # Проверяем, что телефоны НЕ были добавлены
    assert len(contact_2_meta["phones_added"]) == 0, "Контакт 2 не должен быть обогащен"
    assert "low_confidence" in contact_2_meta["skip_reasons"], "Должна быть причина 'low_confidence'"
    print("   ✓ Контакт корректно пропущен из-за низкого confidence")
    
    # Детальная проверка контакта 3 (нет телефонов у организации)
    print("\n✅ Детальная проверка контакта 3 (нет телефонов у организации):")
    contact_3_meta = next(c for c in contacts_metadata if c["contact_gid"] == "contact_003")
    
    print(f"   • Имя: {contact_3_meta['contact_name']}")
    print(f"   • Причины пропуска: {contact_3_meta['skip_reasons']}")
    
    assert "no_org_phones" in contact_3_meta["skip_reasons"], "Должна быть причина 'no_org_phones'"
    print("   ✓ Контакт корректно пропущен (нет телефонов у организации)")
    
    # Детальная проверка контакта 4 (нет organization_id)
    print("\n✅ Детальная проверка контакта 4 (нет organization_id):")
    contact_4_meta = next(c for c in contacts_metadata if c["contact_gid"] == "contact_004")
    
    print(f"   • Имя: {contact_4_meta['contact_name']}")
    print(f"   • Причины пропуска: {contact_4_meta['skip_reasons']}")
    
    assert "no_organization" in contact_4_meta["skip_reasons"], "Должна быть причина 'no_organization'"
    print("   ✓ Контакт корректно пропущен (нет organization_id)")
    
    # Выводим полный результат в JSON
    print("\n" + "=" * 80)
    print("📄 ПОЛНЫЙ РЕЗУЛЬТАТ (JSON)")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)
    print("\n📋 Проверенные требования:")
    print("   ✓ Requirement 5.1: Метаданные по каждому контакту")
    print("   ✓ Requirement 5.2: Причины пропуска")
    print("   ✓ Requirement 5.3: Confidence scores")
    print("   ✓ Requirement 5.4: Общая статистика")


if __name__ == "__main__":
    test_metadata_and_statistics()
