#!/usr/bin/env python3
"""
🔍 Скрипт верификации миграции GID v2

Проверяет, что все контакты и организации в реестре имеют корректные v2 ключи.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

# Добавляем src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from registry.global_registry import (
    iter_contact_keys_v1, 
    iter_contact_keys_v2,
    iter_organization_keys_v1,
    iter_organization_keys_v2,
    norm_email
)


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
    event = registry_record.get("event", {})
    data = event.get("data", {})
    
    return {
        "gid": registry_record.get("gid"),
        "name": data.get("name"),
        "email": data.get("email"),
        "phones": data.get("phones", []),
        "organization_id": data.get("organization_id"),
        "position": data.get("position"),
        "keys": registry_record.get("keys", [])
    }


def extract_organization_data(registry_record: Dict) -> Dict[str, Any]:
    """Извлекает данные организации из записи реестра."""
    event = registry_record.get("event", {})
    data = event.get("data", {})
    
    return {
        "gid": registry_record.get("gid"),
        "name": data.get("name"),
        "inn": data.get("inn"),
        "website": data.get("website"),
        "city": data.get("city"),
        "keys": registry_record.get("keys", [])
    }


def analyze_contact_keys(contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Анализирует ключи контакта."""
    gid = contact_data["gid"]
    email = contact_data["email"]
    phones = contact_data["phones"]
    org_id = contact_data["organization_id"]
    
    # Генерируем ожидаемые ключи
    v1_keys = list(iter_contact_keys_v1({
        "name": contact_data["name"],
        "email": email,
        "phones": phones,
        "position": contact_data["position"]
    }, org_id))
    
    v2_keys = list(iter_contact_keys_v2({
        "name": contact_data["name"],
        "email": email,
        "phones": phones,
        "position": contact_data["position"]
    }, org_id))
    
    # Анализируем существующие ключи
    existing_keys = contact_data["keys"]
    key_types = defaultdict(list)
    for key in existing_keys:
        if len(key) >= 2:
            key_types[key[1]].append(key)
    
    # Проверяем наличие v2 ключей
    has_v2_keys = any(key[1] in ["EMAIL_GLOBAL", "EMAIL_IN_ORG", "PHONE_GLOBAL", "PHONE_IN_ORG"] 
                       for key in existing_keys if len(key) >= 2)
    
    return {
        "gid": gid,
        "email": email,
        "v1_keys": v1_keys,
        "v2_keys": v2_keys,
        "existing_keys": existing_keys,
        "key_types": dict(key_types),
        "has_v2_keys": has_v2_keys,
        "org_id": org_id
    }


def analyze_organization_keys(org_data: Dict[str, Any]) -> Dict[str, Any]:
    """Анализирует ключи организации."""
    gid = org_data["gid"]
    
    # Генерируем ожидаемые ключи
    v1_keys = list(iter_organization_keys_v1({
        "name": org_data["name"],
        "inn": org_data["inn"],
        "website": org_data["website"],
        "city": org_data["city"]
    }))
    
    v2_keys = list(iter_organization_keys_v2({
        "name": org_data["name"],
        "inn": org_data["inn"],
        "website": org_data["website"],
        "city": org_data["city"]
    }))
    
    # Анализируем существующие ключи
    existing_keys = org_data["keys"]
    key_types = defaultdict(list)
    for key in existing_keys:
        if len(key) >= 2:
            key_types[key[1]].append(key)
    
    # Проверяем наличие NAME ключа (детерминированный fallback)
    has_name_key = any(key[1] == "NAME" for key in existing_keys if len(key) >= 2)
    has_fallback_key = any(key[1] == "FALLBACK" for key in existing_keys if len(key) >= 2)
    
    return {
        "gid": gid,
        "name": org_data["name"],
        "website": org_data["website"],
        "v1_keys": v1_keys,
        "v2_keys": v2_keys,
        "existing_keys": existing_keys,
        "key_types": dict(key_types),
        "has_name_key": has_name_key,
        "has_fallback_key": has_fallback_key
    }


def verify_contacts_migration(contacts: List[Dict]) -> Dict[str, Any]:
    """Проверяет миграцию контактов."""
    print("🔍 Проверка миграции контактов...")
    
    analysis_results = []
    stats = {
        "total": len(contacts),
        "has_v2_keys": 0,
        "missing_v2_keys": 0,
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
                print(f"  ⚠️ Контакт без v2 ключей: {analysis['gid']} (email: {analysis['email']})")
            
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
            elif not analysis["has_v2_keys"]:
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
                print(f"  ⚠️ Организация без NAME ключа: {analysis['gid']} ({analysis['name']})")
            
            if analysis["has_fallback_key"]:
                stats["has_fallback_key"] += 1
            
            # Считаем типы ключей
            key_types = analysis["key_types"]
            if "DOMAIN" in key_types:
                stats["has_domain_key"] += len(key_types["DOMAIN"])
            if "INN" in key_types:
                stats["has_inn_key"] += len(key_types["INN"])
            if "NAME_CITY" in key_types:
                stats["has_name_city_key"] += len(key_types["NAME_CITY"])
            
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
    contact_success_rate = contact_stats['has_v2_keys'] / contact_stats['total'] * 100
    org_success_rate = org_stats['has_name_key'] / org_stats['total'] * 100
    
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
        
        print(f"\n👥 Проблемные контакты:")
        for analysis in contact_results["analysis"]:
            if not analysis["has_v2_keys"]:
                print(f"   GID: {analysis['gid']}")
                print(f"   Email: {analysis['email']}")
                print(f"   Keys: {analysis['existing_keys']}")
                print()
        
        print(f"\n🏢 Проблемные организации:")
        for analysis in org_results["analysis"]:
            if not analysis["has_name_key"]:
                print(f"   GID: {analysis['gid']}")
                print(f"   Name: {analysis['name']}")
                print(f"   Keys: {analysis['existing_keys']}")
                print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())