#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Верификация интеграции ContactPhoneEnricher в PostProcessor
Проверяет структуру кода без запуска
"""

import ast
import sys
from pathlib import Path


def verify_integration():
    """Проверяет, что интеграция выполнена корректно"""
    
    postprocessor_path = Path("src/postprocessing/postprocessor.py")
    
    if not postprocessor_path.exists():
        print(f"❌ Файл не найден: {postprocessor_path}")
        return False
    
    with open(postprocessor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "Импорт ContactPhoneEnricher": "from .contact_phone_enricher import ContactPhoneEnricher",
        "Инициализация в __init__": "self.contact_phone_enricher = ContactPhoneEnricher()",
        "Метод _enrich_contacts_phones": "def _enrich_contacts_phones(",
        "Вызов обогащения в пайплайне": "contact_phone_enrichment_metadata = self._enrich_contacts_phones(",
        "Передача метаданных в _build_final_result": "contact_phone_enrichment_metadata,",
        "Параметр в _build_final_result": "contact_phone_enrichment_metadata: Optional[Dict[str, Any]] = None",
        "Добавление метаданных в результат": "['enrichment']['contact_phone_enrichment'] = contact_phone_enrichment_metadata"
    }
    
    print("🔍 Проверка интеграции ContactPhoneEnricher в PostProcessor\n")
    
    all_passed = True
    for check_name, check_string in checks.items():
        if check_string in content:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name} - НЕ НАЙДЕНО")
            all_passed = False
    
    # Проверяем синтаксис Python
    print("\n🔍 Проверка синтаксиса Python...")
    try:
        ast.parse(content)
        print("✅ Синтаксис корректен")
    except SyntaxError as e:
        print(f"❌ Ошибка синтаксиса: {e}")
        all_passed = False
    
    # Проверяем порядок вызовов в пайплайне
    print("\n🔍 Проверка порядка вызовов в пайплайне...")
    
    # Ищем последовательность: phone_conflicts -> phone_enrichment -> backfill
    phone_conflicts_pos = content.find("phone_conflicts = self._resolve_phone_conflicts(")
    phone_enrichment_pos = content.find("contact_phone_enrichment_metadata = self._enrich_contacts_phones(")
    backfill_pos = content.find("contacts_after_backfill, provenance = self._backfill_contact_city_address(")
    normalize_pos = content.find("final_contacts, final_organizations = self._normalize_data(")
    
    if phone_conflicts_pos < phone_enrichment_pos < backfill_pos < normalize_pos:
        print("✅ Порядок вызовов корректен:")
        print("   1. Разрешение конфликтов телефонов")
        print("   2. Обогащение телефонов контактов")
        print("   3. Backfill города/адреса")
        print("   4. Нормализация данных")
    else:
        print("❌ Неправильный порядок вызовов в пайплайне")
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО")
        print("✅ Интеграция ContactPhoneEnricher выполнена корректно")
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = verify_integration()
    sys.exit(0 if success else 1)
