#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки метода _filter_organization_phones
"""

import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Импортируем напрямую модуль, избегая __init__.py
import importlib.util

spec = importlib.util.spec_from_file_location(
    "contact_phone_enricher",
    os.path.join(
        os.path.dirname(__file__), "src/postprocessing/contact_phone_enricher.py"
    ),
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ContactPhoneEnricher = module.ContactPhoneEnricher


def test_filter_organization_phones():
    """Тестирует фильтрацию телефонов организации"""

    # Инициализация enricher
    enricher = ContactPhoneEnricher()

    # Тестовые данные: различные типы телефонов
    org_phones = [
        {"type": "main", "number": "+7 (495) 123-45-67", "normalized": "+74951234567"},
        {
            "type": "office",
            "number": "+7 (495) 123-45-68",
            "normalized": "+74951234568",
        },
        {"type": "fax", "number": "+7 (495) 123-45-69", "normalized": "+74951234569"},
        {
            "type": "mobile",
            "number": "+7 (916) 123-45-67",
            "normalized": "+79161234567",
        },
        {"type": None, "number": "+7 (495) 123-45-70", "normalized": "+74951234570"},
        {
            "type": "direct",
            "number": "+7 (495) 123-45-71",
            "normalized": "+74951234571",
        },
    ]

    print("📞 Тестирование фильтрации телефонов организации\n")
    print(f"Входные данные: {len(org_phones)} телефонов")
    for phone in org_phones:
        print(f"  - type: {phone['type']}, number: {phone['number']}")

    # Выполняем фильтрацию
    filtered = enricher._filter_organization_phones(org_phones)

    print(f"\n✅ Результат фильтрации: {len(filtered)} телефонов прошли фильтр\n")

    for phone in filtered:
        print(f"  ✓ type: {phone['type']}, number: {phone['number']}")
        print(f"    confidence_adjustment: {phone.get('confidence_adjustment', 0.0)}")
        if phone.get("_original_type") is not None:
            print(f"    _original_type: {phone.get('_original_type')}")

    # Проверки
    assert len(filtered) == 4, f"Ожидалось 4 телефона, получено {len(filtered)}"

    # Проверяем, что mobile исключен
    mobile_phones = [
        p
        for p in filtered
        if p.get("_original_type") == "mobile" or p.get("type") == "mobile"
    ]
    assert len(mobile_phones) == 0, "Mobile телефоны должны быть исключены"

    # Проверяем, что null тип обработан как main с пониженным confidence
    null_type_phones = [
        p for p in filtered if "_original_type" in p and p["_original_type"] is None
    ]
    assert (
        len(null_type_phones) == 1
    ), f"Должен быть 1 телефон с null типом, найдено {len(null_type_phones)}"
    assert (
        null_type_phones[0]["type"] == "main"
    ), "Null тип должен быть преобразован в main"
    assert (
        null_type_phones[0]["confidence_adjustment"] == -0.1
    ), "Confidence должен быть понижен на 0.1"

    # Проверяем разрешенные типы
    allowed_types = [p["type"] for p in filtered]
    for phone_type in ["main", "office", "fax"]:
        assert phone_type in allowed_types, f"Тип {phone_type} должен присутствовать"

    print("\n✅ Все проверки пройдены!")
    print(f"\n📊 Статистика:")
    print(f"  - Всего телефонов: {len(org_phones)}")
    print(f"  - Прошли фильтр: {len(filtered)}")
    print(
        f"  - Исключено mobile: {enricher.stats['phones_skipped_by_reason']['mobile_only']}"
    )


if __name__ == "__main__":
    test_filter_organization_phones()
