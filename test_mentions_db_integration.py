#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест интеграции mentions с БД на реальных данных.

Обрабатывает несколько писем и проверяет сохранение в crm.db.
"""

import json
import sqlite3
from pathlib import Path

from src.postprocessing.postprocessor import PostProcessor

def test_mentions_integration():
    """Тестирует полный цикл: обработка → сохранение в БД → проверка."""
    
    print("=" * 80)
    print("🧪 ТЕСТ ИНТЕГРАЦИИ MENTIONS С БД")
    print("=" * 80)
    print()
    
    # Инициализация постпроцессора
    print("1️⃣ Инициализация постпроцессора...")
    processor = PostProcessor()
    print(f"   ✅ Постпроцессор создан")
    print(f"   📊 Mentions repository: {processor.mentions_repository is not None}")
    print()
    
    # Подготовка тестовых данных
    print("2️⃣ Подготовка тестовых данных...")
    llm_result = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ООО Тестовая Компания",
                "inn": "1234567890",
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Иванов Иван Иванович",
                "email": "ivanov@test.ru",
                "organization_id": 1,
            },
            {
                "contact_id": 2,
                "name": "Петров Пётр Петрович",
                # Нет email и телефона → будет отфильтрован
                "position": "Директор",
                "organization_id": 1,
            },
            {
                "contact_id": 3,
                "name": "Сидорова Анна",
                # Нет email и телефона → будет отфильтрован
                "organization_id": 1,
            },
        ],
        "interactions": [],
        "commercial_offers": [],
    }
    
    email_data = {
        "interaction_id": 999,
        "source_file": "test_email_integration.json",
        "message_id": "test-message-id-999",
    }
    
    print(f"   📧 Тестовое письмо: interaction_id={email_data['interaction_id']}")
    print(f"   👥 Контактов в LLM результате: {len(llm_result['contacts'])}")
    print()
    
    # Обработка
    print("3️⃣ Обработка через постпроцессор...")
    result = processor.process_llm_response(llm_result, email_data)
    print(f"   ✅ Обработка завершена")
    print(f"   👥 Валидных контактов: {len(result['contacts'])}")
    print(f"   🗑️ Mentions: {len(result['contact_mentions'])}")
    print()
    
    # Проверка результата
    print("4️⃣ Проверка результата обработки...")
    assert len(result['contacts']) == 1, f"Ожидался 1 валидный контакт, получено {len(result['contacts'])}"
    assert result['contacts'][0]['name'] == "Иванов Иван Иванович"
    print(f"   ✅ Валидный контакт: {result['contacts'][0]['name']}")
    
    assert len(result['contact_mentions']) == 2, f"Ожидалось 2 mentions, получено {len(result['contact_mentions'])}"
    mention_names = {m['name'] for m in result['contact_mentions']}
    assert mention_names == {"Петров Пётр Петрович", "Сидорова Анна"}
    print(f"   ✅ Mentions: {', '.join(mention_names)}")
    print()
    
    # Проверка БД
    print("5️⃣ Проверка данных в crm.db...")
    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()
    
    # Проверяем общее количество
    cursor.execute("SELECT COUNT(*) FROM contact_mentions WHERE interaction_id = ?", (999,))
    count = cursor.fetchone()[0]
    print(f"   📊 Записей в БД для interaction_id=999: {count}")
    
    if count == 0:
        print(f"   ❌ ОШИБКА: Mentions не сохранились в БД!")
        conn.close()
        return False
    
    # Получаем данные
    cursor.execute("""
        SELECT id, name, position, organization_id, interaction_id, source_file, created_at
        FROM contact_mentions 
        WHERE interaction_id = ?
        ORDER BY name
    """, (999,))
    
    rows = cursor.fetchall()
    print(f"   ✅ Найдено записей: {len(rows)}")
    print()
    
    print("6️⃣ Детали сохранённых mentions:")
    for row in rows:
        print(f"   📋 ID: {row[0]}")
        print(f"      • Имя: {row[1]}")
        print(f"      • Должность: {row[2]}")
        print(f"      • Организация: {row[3]}")
        print(f"      • Interaction: {row[4]}")
        print(f"      • Источник: {row[5]}")
        print(f"      • Создано: {row[6]}")
        print()
    
    # Проверяем корректность данных
    saved_names = {row[1] for row in rows}
    assert saved_names == mention_names, f"Имена в БД не совпадают: {saved_names} != {mention_names}"
    
    # Проверяем organization_id
    for row in rows:
        assert row[3] == 1, f"Неверный organization_id: {row[3]}"
    
    # Проверяем interaction_id
    for row in rows:
        assert row[4] == 999, f"Неверный interaction_id: {row[4]}"
    
    print("   ✅ Все проверки пройдены!")
    print()
    
    # Очистка тестовых данных
    print("7️⃣ Очистка тестовых данных...")
    cursor.execute("DELETE FROM contact_mentions WHERE interaction_id = ?", (999,))
    conn.commit()
    deleted = cursor.rowcount
    print(f"   🗑️ Удалено записей: {deleted}")
    
    conn.close()
    print()
    
    print("=" * 80)
    print("🎉 ТЕСТ УСПЕШНО ПРОЙДЕН!")
    print("=" * 80)
    print()
    print("✅ Результаты:")
    print(f"   • Фильтрация работает: 2 из 3 контактов отфильтрованы")
    print(f"   • Mentions сохраняются в БД: {count} записей")
    print(f"   • Данные корректны: имена, org_id, interaction_id")
    print(f"   • Интеграция работает end-to-end")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = test_mentions_integration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
