#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест нормализации на реальных данных email_004
Проверяет, что "ООО Экомед" нормализуется корректно
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.postprocessing.postprocessor import PostProcessor


def test_email_004_normalization():
    """Тест нормализации email_004 с ООО Экомед"""

    # Найдем файл email_004
    email_004_path = "data/llm_results/2025-07-29/email_004_20250729_20250729_dna_technology_ru_6e851453_20251005_193708_193945_processed.json"

    if not os.path.exists(email_004_path):
        print(f"❌ Файл {email_004_path} не найден")
        return False

    print(f"📧 Загружаем email_004: {email_004_path}")

    try:
        with open(email_004_path, "r", encoding="utf-8") as f:
            email_data = json.load(f)

        # Получаем результат LLM
        llm_result = email_data.get("processed_result", {})

        print(f"📊 Исходные данные:")
        print(f"  Организаций: {len(llm_result.get('organizations', []))}")
        print(f"  Контактов: {len(llm_result.get('contacts', []))}")

        # Ищем организацию "ООО Экомед"
        ecomed_org = None
        for org in llm_result.get("organizations", []):
            if "Экомед" in org.get("name", ""):
                ecomed_org = org
                break

        if not ecomed_org:
            print("❌ Организация с 'Экомед' не найдена в исходных данных")
            return False

        print(f"\n🏢 Найдена организация: {ecomed_org['name']}")

        # Инициализируем постпроцессор
        postprocessor = PostProcessor()

        # Обрабатываем данные
        print("\n🔄 Запускаем постобработку...")
        processed_result = postprocessor.process_llm_response(llm_result)

        # Ищем обработанную организацию
        processed_ecomed = None
        for org in processed_result.get("organizations", []):
            if org.get("organization_id") == ecomed_org.get("organization_id"):
                processed_ecomed = org
                break

        if not processed_ecomed:
            print("❌ Обработанная организация не найдена")
            return False

        print(f"\n📋 Результаты нормализации:")
        print(f"  Исходное название: '{ecomed_org['name']}'")
        print(f"  Нормализованное: '{processed_ecomed['name']}'")

        # Проверяем результат
        expected_name = "Экомед"
        if processed_ecomed["name"] == expected_name:
            print(
                f"✅ УСПЕХ! Название нормализовано корректно: '{processed_ecomed['name']}'"
            )
            return True
        else:
            print(
                f"❌ ОШИБКА! Ожидалось '{expected_name}', получено '{processed_ecomed['name']}'"
            )
            return False

    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_all_organizations_normalization():
    """Тест нормализации всех организаций в email_004"""

    email_004_path = "data/llm_results/2025-07-29/email_004_20250729_20250729_dna_technology_ru_6e851453_20251005_193708_193945_processed.json"

    if not os.path.exists(email_004_path):
        print(f"❌ Файл {email_004_path} не найден")
        return False

    try:
        with open(email_004_path, "r", encoding="utf-8") as f:
            email_data = json.load(f)

        llm_result = email_data.get("processed_result", {})

        print(f"\n🏢 Все организации в email_004:")
        print("=" * 60)

        postprocessor = PostProcessor()
        processed_result = postprocessor.process_llm_response(llm_result)

        for i, (orig_org, proc_org) in enumerate(
            zip(
                llm_result.get("organizations", []),
                processed_result.get("organizations", []),
            )
        ):
            orig_name = orig_org.get("name", "Unknown")
            proc_name = proc_org.get("name", "Unknown")

            status = "🔄" if orig_name != proc_name else "➡️"
            print(f"{i+1}. {status} '{orig_name}' → '{proc_name}'")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Тестирование нормализации на реальных данных email_004\n")

    success1 = test_email_004_normalization()
    success2 = test_all_organizations_normalization()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎯 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Нормализация работает на реальных данных.")
        sys.exit(0)
    else:
        print("💥 ЕСТЬ ПРОБЛЕМЫ! Требуется проверка.")
        sys.exit(1)
