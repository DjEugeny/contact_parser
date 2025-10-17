#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Пилотное тестирование GID v2 на реальных данных.

Обрабатывает 100-200 писем и собирает метрики:
- Количество созданных дублей
- Деградация GID (потеря связей)
- Количество миграций v1→v2
- Распределение по типам ключей

Критерии успеха:
- Дублей <5%
- Деградация <0.1%
"""

import json
import tempfile
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any

from src.registry.global_registry import GlobalIDRegistry


def load_processed_emails(data_dir: Path, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Загружает обработанные письма из data/llm_results.
    
    Args:
        data_dir: Путь к папке data/llm_results
        limit: Максимальное количество писем
    
    Returns:
        Список словарей с данными писем
    """
    emails = []
    
    # Ищем JSON файлы
    for date_dir in sorted(data_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        
        for json_file in sorted(date_dir.glob("*_processed.json")):
            if len(emails) >= limit:
                break
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Извлекаем processed_result
                result = data.get('processed_result', {})
                if result:
                    emails.append({
                        'file': str(json_file),
                        'organizations': result.get('organizations', []),
                        'contacts': result.get('contacts', []),
                    })
            except Exception as e:
                print(f"⚠️ Ошибка при чтении {json_file}: {e}")
                continue
        
        if len(emails) >= limit:
            break
    
    return emails


def test_gid_v2_pilot():
    """Запускает пилотное тестирование GID v2."""
    
    print("=" * 80)
    print("🧪 ПИЛОТНОЕ ТЕСТИРОВАНИЕ GID V2")
    print("=" * 80)
    print()
    
    # Загружаем данные
    data_dir = Path("data/llm_results")
    if not data_dir.exists():
        print(f"❌ Папка {data_dir} не найдена")
        return
    
    print("📂 Загрузка писем...")
    emails = load_processed_emails(data_dir, limit=200)
    print(f"   ✅ Загружено: {len(emails)} писем")
    print()
    
    if len(emails) < 50:
        print(f"⚠️ Недостаточно писем для тестирования (минимум 50, найдено {len(emails)})")
        return
    
    # Создаём временные реестры
    print("🔧 Создание реестров...")
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_v1_dir = Path(tmpdir) / "registry_v1"
        registry_v2_dir = Path(tmpdir) / "registry_v2"
        registry_v1_dir.mkdir()
        registry_v2_dir.mkdir()
        
        registry_v1 = GlobalIDRegistry(registry_dir=registry_v1_dir)
        registry_v2 = GlobalIDRegistry(registry_dir=registry_v2_dir)
        print("   ✅ Реестры созданы")
        print()
        
        # Метрики
        stats_v1 = {
            'total_contacts': 0,
            'unique_gids': set(),
            'key_types': Counter(),
        }
        
        stats_v2 = {
            'total_contacts': 0,
            'unique_gids': set(),
            'key_types': Counter(),
            'migrations': 0,
            'new_keys': 0,
        }
        
        # Обработка писем
        print("📧 Обработка писем...")
        print()
        
        for i, email in enumerate(emails, 1):
            if i % 20 == 0:
                print(f"   Обработано: {i}/{len(emails)} писем...")
            
            # Обрабатываем организации
            org_gids = {}
            for org in email['organizations']:
                try:
                    # v1
                    result_v1 = registry_v1.resolve_organization(org)
                    
                    # v2 (используем тот же метод, т.к. для организаций пока нет v2)
                    result_v2 = registry_v2.resolve_organization(org)
                    
                    org_gids[org.get('organization_id')] = {
                        'v1': result_v1.gid,
                        'v2': result_v2.gid,
                    }
                except Exception as e:
                    continue
            
            # Обрабатываем контакты
            for contact in email['contacts']:
                org_id = contact.get('organization_id')
                org_gid_v1 = org_gids.get(org_id, {}).get('v1')
                org_gid_v2 = org_gids.get(org_id, {}).get('v2')
                
                try:
                    # v1: resolve_contact
                    result_v1 = registry_v1.resolve_contact(contact, org_gid_v1)
                    stats_v1['total_contacts'] += 1
                    stats_v1['unique_gids'].add(result_v1.gid)
                    stats_v1['key_types'][result_v1.match_rule] += 1
                    
                    # v2: resolve_contact_v2
                    result_v2 = registry_v2.resolve_contact_v2(contact, org_gid_v2)
                    stats_v2['total_contacts'] += 1
                    stats_v2['unique_gids'].add(result_v2.gid)
                    stats_v2['key_types'][result_v2.match_rule] += 1
                    
                    # Проверяем миграцию
                    if 'v1_migrated' in result_v2.source.lower():
                        stats_v2['migrations'] += 1
                    
                    # Проверяем новые ключи
                    if result_v2.match_rule in ['EMAIL_GLOBAL', 'PHONE_GLOBAL']:
                        stats_v2['new_keys'] += 1
                    
                except Exception as e:
                    continue
        
        print()
        print("   ✅ Обработка завершена")
        print()
        
        # Анализ результатов
        print("=" * 80)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        print()
        
        # Общая статистика
        print("📈 Общая статистика:")
        print(f"   Писем обработано: {len(emails)}")
        print(f"   Контактов обработано: {stats_v1['total_contacts']}")
        print()
        
        # Сравнение v1 vs v2
        print("🔄 Сравнение v1 vs v2:")
        print(f"   v1 уникальных GID: {len(stats_v1['unique_gids'])}")
        print(f"   v2 уникальных GID: {len(stats_v2['unique_gids'])}")
        
        # Дубли
        duplicates_v1 = stats_v1['total_contacts'] - len(stats_v1['unique_gids'])
        duplicates_v2 = stats_v2['total_contacts'] - len(stats_v2['unique_gids'])
        
        duplicate_rate_v1 = (duplicates_v1 / stats_v1['total_contacts'] * 100) if stats_v1['total_contacts'] > 0 else 0
        duplicate_rate_v2 = (duplicates_v2 / stats_v2['total_contacts'] * 100) if stats_v2['total_contacts'] > 0 else 0
        
        print(f"   v1 дублей: {duplicates_v1} ({duplicate_rate_v1:.1f}%)")
        print(f"   v2 дублей: {duplicates_v2} ({duplicate_rate_v2:.1f}%)")
        print()
        
        # Деградация
        gid_degradation = len(stats_v1['unique_gids'] - stats_v2['unique_gids'])
        degradation_rate = (gid_degradation / len(stats_v1['unique_gids']) * 100) if len(stats_v1['unique_gids']) > 0 else 0
        
        print(f"🔻 Деградация GID:")
        print(f"   Потеряно связей: {gid_degradation}")
        print(f"   Процент деградации: {degradation_rate:.2f}%")
        print()
        
        # Миграции
        migration_rate = (stats_v2['migrations'] / stats_v2['total_contacts'] * 100) if stats_v2['total_contacts'] > 0 else 0
        print(f"🔄 Миграции v1→v2:")
        print(f"   Всего миграций: {stats_v2['migrations']}")
        print(f"   Процент миграций: {migration_rate:.1f}%")
        print()
        
        # Новые ключи
        new_keys_rate = (stats_v2['new_keys'] / stats_v2['total_contacts'] * 100) if stats_v2['total_contacts'] > 0 else 0
        print(f"🆕 Новые ключи v2:")
        print(f"   EMAIL_GLOBAL/PHONE_GLOBAL: {stats_v2['new_keys']}")
        print(f"   Процент новых ключей: {new_keys_rate:.1f}%")
        print()
        
        # Распределение по типам ключей
        print("📊 Распределение по типам ключей (v2):")
        for key_type, count in stats_v2['key_types'].most_common(10):
            percentage = (count / stats_v2['total_contacts'] * 100) if stats_v2['total_contacts'] > 0 else 0
            print(f"   {key_type}: {count} ({percentage:.1f}%)")
        print()
        
        # Проверка критериев успеха
        print("=" * 80)
        print("✅ ПРОВЕРКА КРИТЕРИЕВ УСПЕХА")
        print("=" * 80)
        print()
        
        success = True
        
        # Критерий 1: Дубли <5%
        if duplicate_rate_v2 < 5.0:
            print(f"✅ Дубли: {duplicate_rate_v2:.1f}% < 5% (PASS)")
        else:
            print(f"❌ Дубли: {duplicate_rate_v2:.1f}% >= 5% (FAIL)")
            success = False
        
        # Критерий 2: Деградация <0.1%
        if degradation_rate < 0.1:
            print(f"✅ Деградация: {degradation_rate:.2f}% < 0.1% (PASS)")
        else:
            print(f"❌ Деградация: {degradation_rate:.2f}% >= 0.1% (FAIL)")
            success = False
        
        print()
        
        if success:
            print("🎉 ВСЕ КРИТЕРИИ УСПЕХА ВЫПОЛНЕНЫ!")
        else:
            print("⚠️ НЕКОТОРЫЕ КРИТЕРИИ НЕ ВЫПОЛНЕНЫ")
        
        print()
        print("=" * 80)
        
        return {
            'emails_processed': len(emails),
            'contacts_processed': stats_v1['total_contacts'],
            'v1_unique_gids': len(stats_v1['unique_gids']),
            'v2_unique_gids': len(stats_v2['unique_gids']),
            'duplicate_rate_v2': duplicate_rate_v2,
            'degradation_rate': degradation_rate,
            'migration_rate': migration_rate,
            'new_keys_rate': new_keys_rate,
            'success': success,
        }


if __name__ == "__main__":
    try:
        results = test_gid_v2_pilot()
        exit(0 if results and results['success'] else 1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
