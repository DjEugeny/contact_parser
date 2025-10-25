#!/usr/bin/env python3
"""
🔍 Упрощённый скрипт верификации миграции GID v2

Проверяет, что все контакты и организации в реестре имеют корректные v2 ключи.
Работает без зависимостей от модуля global_registry.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


def load_registry(registry_dir: Path) -> Tuple[List[Dict], List[Dict]]:
    """Загружает реестр контактов и организаций."""
    contacts_file = registry_dir / "contacts.jsonl"
    organizations_file = registry_dir / "organizations.jsonl"
    
    contacts = []
    organizations = []
    
    if contacts_file.exists():
        with open(contacts_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    contacts.append(json.loads(line))
    
    if organizations_file.exists():
        with open(organizations_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    organizations.append(json.loads(line))
    
    return contacts, organizations


def extract_contact_data(registry_record: Dict) -> Dict[str, Any]:
    """Извлекает данные контакта из записи реестра."""
    event_type = registry_record.get("event", "")
    
    # Собираем все ключи из записи
    keys = []
    if event_type == "create":
        # Основной ключ
        key = registry_record.get("key", [])
        if key:
            keys.append(key)
        # Алиасы
        aliases = registry_record.get("aliases", [])
        keys.extend(aliases)
    elif event_type == "alias":
        # Только алиас
        alias = registry_record.get("alias", [])
        if alias:
            keys.append(alias)
    
    # Извлекаем email и телефон из ключей для анализа
    email = None
    phones = []
    
    for key in keys:
        if len(key) >= 3 and key[1] in ["EMAIL", "EMAIL_GLOBAL", "EMAIL_IN_ORG"]:
            email = key[-1]  # Последний элемент - email
        elif len(key) >= 3 and key[1] in ["PHONE", "PHONE_GLOBAL", "PHONE_IN_ORG"]:
            phones.append({"number": key[-1]})  # Последний элемент - телефон
    
    # Извлекаем organization_id из ключей
    org_id = None
    for key in keys:
        if len(key) >= 3 and key[2] not in ["PERSONAL"] and "-" in key[2]:
            org_id = key[2]
            break
    
    return {
        "gid": registry_record.get("gid"),
        "name": None,  # Не хранится в реестре
        "email": email,
        "phones": phones,
        "organization_id": org_id,
        "position": None,  # Не хранится в реестре
        "keys": keys
    }


def extract_organization_data(registry_record: Dict) -> Dict[str, Any]:
    """Извлекает данные организации из записи реестра."""
    event_type = registry_record.get("event", "")
    
    # Собираем все ключи из записи
    keys = []
    if event_type == "create":
        # Основной ключ
        key = registry_record.get("key", [])
        if key:
            keys.append(key)
        # Алиасы
        aliases = registry_record.get("aliases", [])
        keys.extend(aliases)
    elif event_type == "alias":
        # Только алиас
        alias = registry_record.get("alias", [])
        if alias:
            keys.append(alias)
    
    # Извлекаем данные из ключей для анализа
    name = None
    inn = None
    website = None
    city = None
    
    for key in keys:
        if len(key) >= 3:
            key_type = key[1]
            if key_type == "NAME" and len(key) >= 3:
                name = key[2]
            elif key_type == "INN" and len(key) >= 3:
                inn = key[2]
            elif key_type == "DOMAIN" and len(key) >= 3:
                website = f"https://{key[2]}"
            elif key_type == "NAME_CITY" and len(key) >= 4:
                name = key[2]
                city = key[3]
    
    return {
        "gid": registry_record.get("gid"),
        "name": name,
        "inn": inn,
        "website": website,
        "city": city,
        "keys": keys
    }


def analyze_contact_keys(contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Анализирует ключи контакта."""
    gid = contact_data["gid"]
    email = contact_data["email"]
    phones = contact_data["phones"]
    org_id = contact_data["organization_id"]
    
    # Анализируем существующие ключи
    existing_keys = contact_data["keys"]
    key_types = defaultdict(list)
    
    for key in existing_keys:
        if len(key) >= 2:
            key_types[key[1]].append(key)
    
    # Проверяем наличие v2 ключей
    has_v2_keys = any(key[1] in ["EMAIL_GLOBAL", "EMAIL_IN_ORG", "PHONE_GLOBAL", "PHONE_IN_ORG"] 
                       for key in existing_keys if len(key) >= 2)
    
    # Проверяем наличие v1 ключей
    has_v1_keys = any(key[1] in ["EMAIL", "PHONE", "NAME_POSITION"] 
                       for key in existing_keys if len(key) >= 2)
    
    return {
        "gid": gid,
        "email": email,
        "existing_keys": existing_keys,
        "key_types": dict(key_types),
        "has_v2_keys": has_v2_keys,
        "has_v1_keys": has_v1_keys,
        "org_id": org_id,
        "total_keys": len(existing_keys)
    }


def analyze_organization_keys(org_data: Dict[str, Any]) -> Dict[str, Any]:
    """Анализирует ключи организации."""
    gid = org_data["gid"]
    
    # Анализируем существующие ключи
    existing_keys = org_data["keys"]
    key_types = defaultdict(list)
    
    for key in existing_keys:
        if len(key) >= 2:
            key_types[key[1]].append(key)
    
    # Проверяем наличие NAME ключа (детерминированный fallback)
    has_name_key = any(key[1] == "NAME" for key in existing_keys if len(key) >= 2)
    has_fallback_key = any(key[1] == "FALLBACK" for key in existing_keys if len(key) >= 2)
    
    # Другие типы ключей
    has_domain_key = any(key[1] == "DOMAIN" for key in existing_keys if len(key) >= 2)
    has_inn_key = any(key[1] == "INN" for key in existing_keys if len(key) >= 2)
    has_name_city_key = any(key[1] == "NAME_CITY" for key in existing_keys if len(key) >= 2)
    
    return {
        "gid": gid,
        "name": org_data["name"],
        "website": org_data["website"],
        "existing_keys": existing_keys,
        "key_types": dict(key_types),
        "has_name_key": has_name_key,
        "has_fallback_key": has_fallback_key,
        "has_domain_key": has_domain_key,
        "has_inn_key": has_inn_key,
        "has_name_city_key": has_name_city_key,
        "total_keys": len(existing_keys)
    }


def verify_contacts_migration(contacts: List[Dict]) -> Dict[str, Any]:
    """Проверяет миграцию контактов."""
    print("🔍 Проверка миграции контактов...")
    
    analysis_results = []
    stats = {
        "total": len(contacts),
        "has_v2_keys": 0,
        "missing_v2_keys": 0,
        "has_v1_keys": 0,
        "has_email_global": 0,
        "has_email_in_org": 0,
        "has_phone_keys": 0,
        "only_v1_keys": 0,
        "no_keys": 0,
        "errors": 0
    }
    
    for contact_record in contacts:
        try:
            contact_data = extract_contact_data(contact_record)
            analysis = analyze_contact_keys(contact_data)
            analysis_results.append(analysis)
            
            if analysis["has_v2_keys"]:
                stats["has_v2_keys"] += 1
            else:
                stats["missing_v2_keys"] += 1
                if stats["missing_v2_keys"] <= 5:  # Показываем только первые 5
                    print(f"  ⚠️ Контакт без v2 ключей: {analysis['gid'][:12]}... (email: {analysis['email']})")
            
            if analysis["has_v1_keys"]:
                stats["has_v1_keys"] += 1
            
            # Считаем типы ключей
            key_types = analysis["key_types"]
            if "EMAIL_GLOBAL" in key_types:
                stats["has_email_global"] += len(key_types["EMAIL_GLOBAL"])
            if "EMAIL_IN_ORG" in key_types:
                stats["has_email_in_org"] += len(key_types["EMAIL_IN_ORG"])
            if any(k.startswith("PHONE") for k in key_types):
                stats["has_phone_keys"] += 1
            
            if not analysis["existing_keys"]:
                stats["no_keys"] += 1
            elif not analysis["has_v2_keys"] and analysis["has_v1_keys"]:
                stats["only_v1_keys"] += 1
                
        except Exception as e:
            stats["errors"] += 1
            print(f"  ❌ Ошибка анализа контакта: {e}")
    
    return {
        "stats": stats,
        "analysis": analysis_results
    }


def verify_organizations_migration(organizations: List[Dict]) -> Dict[str, Any]:
    """Проверяет миграцию организаций."""
    print("🔍 Проверка миграции организаций...")
    
    analysis_results = []
    stats = {
        "total": len(organizations),
        "has_name_key": 0,
        "has_fallback_key": 0,
        "has_domain_key": 0,
        "has_inn_key": 0,
        "has_name_city_key": 0,
        "missing_name_key": 0,
        "no_keys": 0,
        "errors": 0
    }
    
    for org_record in organizations:
        try:
            org_data = extract_organization_data(org_record)
            analysis = analyze_organization_keys(org_data)
            analysis_results.append(analysis)
            
            if analysis["has_name_key"]:
                stats["has_name_key"] += 1
            else:
                stats["missing_name_key"] += 1
                if stats["missing_name_key"] <= 5:  # Показываем только первые 5
                    print(f"  ⚠️ Организация без NAME ключа: {analysis['gid'][:12]}... ({analysis['name']})")
            
            if analysis["has_fallback_key"]:
                stats["has_fallback_key"] += 1
            
            # Считаем типы ключей
            if analysis["has_domain_key"]:
                stats["has_domain_key"] += 1
            if analysis["has_inn_key"]:
                stats["has_inn_key"] += 1
            if analysis["has_name_city_key"]:
                stats["has_name_city_key"] += 1
            
            if not analysis["existing_keys"]:
                stats["no_keys"] += 1
                
        except Exception as e:
            stats["errors"] += 1
            print(f"  ❌ Ошибка анализа организации: {e}")
    
    return {
        "stats": stats,
        "analysis": analysis_results
    }


def print_migration_report(contact_results: Dict, org_results: Dict):
    """Выводит отчёт о миграции."""
    print("\n" + "="*80)
    print("📊 ОТЧЁТ О ВЕРИФИКАЦИИ МИГРАЦИИ GID V2")
    print("="*80)
    
    # Статистика по контактам
    contact_stats = contact_results["stats"]
    print(f"\n👥 КОНТАКТЫ:")
    print(f"   Всего записей: {contact_stats['total']}")
    print(f"   Имеют v2 ключи: {contact_stats['has_v2_keys']} ({contact_stats['has_v2_keys']/contact_stats['total']*100:.1f}%)")
    print(f"   Пропущены v2 ключи: {contact_stats['missing_v2_keys']}")
    print(f"   Имеют v1 ключи: {contact_stats['has_v1_keys']}")
    print(f"   EMAIL_GLOBAL ключей: {contact_stats['has_email_global']}")
    print(f"   EMAIL_IN_ORG ключей: {contact_stats['has_email_in_org']}")
    print(f"   С телефонными ключами: {contact_stats['has_phone_keys']}")
    print(f"   Только v1 ключи: {contact_stats['only_v1_keys']}")
    print(f"   Без ключей: {contact_stats['no_keys']}")
    print(f"   Ошибок: {contact_stats['errors']}")
    
    # Статистика по организациям
    org_stats = org_results["stats"]
    print(f"\n🏢 ОРГАНИЗАЦИИ:")
    print(f"   Всего записей: {org_stats['total']}")
    print(f"   Имеют NAME ключ: {org_stats['has_name_key']} ({org_stats['has_name_key']/org_stats['total']*100:.1f}%)")
    print(f"   Пропущены NAME ключи: {org_stats['missing_name_key']}")
    print(f"   Остались FALLBACK ключи: {org_stats['has_fallback_key']}")
    print(f"   DOMAIN ключей: {org_stats['has_domain_key']}")
    print(f"   INN ключей: {org_stats['has_inn_key']}")
    print(f"   NAME_CITY ключей: {org_stats['has_name_city_key']}")
    print(f"   Без ключей: {org_stats['no_keys']}")
    print(f"   Ошибок: {org_stats['errors']}")
    
    # Общий статус
    print(f"\n🎯 ОБЩИЙ СТАТУС:")
    
    # Критерии успеха
    if contact_stats['total'] > 0:
        contact_success_rate = contact_stats['has_v2_keys'] / contact_stats['total'] * 100
    else:
        contact_success_rate = 100
    
    if org_stats['total'] > 0:
        org_success_rate = org_stats['has_name_key'] / org_stats['total'] * 100
    else:
        org_success_rate = 100
    
    if contact_success_rate >= 95 and org_success_rate >= 95:
        print("   ✅ МИГРАЦИЯ УСПЕШНА (>=95% v2 ключей)")
    elif contact_success_rate >= 90 and org_success_rate >= 90:
        print("   ⚠️ МИГРАЦИЯ В ПОРЯДКЕ (90-94% v2 ключей)")
    else:
        print("   ❌ МИГРАЦИЯ ТРЕБУЕТ ВНИМАНИЯ (<90% v2 ключей)")
    
    print(f"   📈 Успешность контактов: {contact_success_rate:.1f}%")
    print(f"   📈 Успешность организаций: {org_success_rate:.1f}%")
    
    # Проблемы
    if contact_stats['missing_v2_keys'] > 0 or org_stats['missing_name_key'] > 0:
        print(f"\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
        if contact_stats['missing_v2_keys'] > 0:
            print(f"   • {contact_stats['missing_v2_keys']} контактов без v2 ключей")
        if org_stats['missing_name_key'] > 0:
            print(f"   • {org_stats['missing_name_key']} организаций без NAME ключа")
        if org_stats['has_fallback_key'] > 0:
            print(f"   • {org_stats['has_fallback_key']} организаций всё ещё с FALLBACK ключами")
    
    # Детализация по типам ключей
    print(f"\n📋 ДЕТАЛИЗАЦИЯ ПО ТИПАМ КЛЮЧЕЙ:")
    
    # Контакты
    if contact_stats['total'] > 0:
        print(f"   👥 Контакты с EMAIL_GLOBAL: {contact_stats['has_email_global']}")
        print(f"   👥 Контакты с EMAIL_IN_ORG: {contact_stats['has_email_in_org']}")
        print(f"   👥 Контакты с PHONE ключами: {contact_stats['has_phone_keys']}")
    
    # Организации  
    if org_stats['total'] > 0:
        print(f"   🏢 Организации с DOMAIN: {org_stats['has_domain_key']}")
        print(f"   🏢 Организации с INN: {org_stats['has_inn_key']}")
        print(f"   🏢 Организации с NAME_CITY: {org_stats['has_name_city_key']}")


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Верификация миграции GID v2")
    parser.add_argument("--registry-dir", default="src/registry", 
                       help="Директория с реестром (по умолчанию: src/registry)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Подробный вывод")
    
    args = parser.parse_args()
    
    registry_dir = Path(args.registry_dir)
    
    if not registry_dir.exists():
        print(f"❌ Директория реестра не найдена: {registry_dir}")
        return 1
    
    print(f"🔍 Верификация миграции GID v2")
    print(f"📁 Директория реестра: {registry_dir}")
    
    # Загрузка данных
    contacts, organizations = load_registry(registry_dir)
    print(f"📂 Загружено: {len(contacts)} контактов, {len(organizations)} организаций")
    
    if not contacts and not organizations:
        print("❌ Реестр пуст или не найден")
        return 1
    
    # Верификация
    contact_results = verify_contacts_migration(contacts)
    org_results = verify_organizations_migration(organizations)
    
    # Отчёт
    print_migration_report(contact_results, org_results)
    
    # Подробный вывод
    if args.verbose:
        print(f"\n🔍 ПОДРОБНЫЙ АНАЛИЗ:")
        
        print(f"\n👥 Проблемные контакты (первые 10):")
        problematic_contacts = [a for a in contact_results["analysis"] if not a["has_v2_keys"]][:10]
        for analysis in problematic_contacts:
            print(f"   GID: {analysis['gid']}")
            print(f"   Email: {analysis['email']}")
            print(f"   Keys: {analysis['existing_keys']}")
            print()
        
        print(f"\n🏢 Проблемные организации (первые 10):")
        problematic_orgs = [a for a in org_results["analysis"] if not a["has_name_key"]][:10]
        for analysis in problematic_orgs:
            print(f"   GID: {analysis['gid']}")
            print(f"   Name: {analysis['name']}")
            print(f"   Keys: {analysis['existing_keys']}")
            print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())