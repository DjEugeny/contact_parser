#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для принудительной миграции всех существующих GID на v2.

Логика:
1. Загружаем все записи из реестра
2. Для каждого контакта/организации генерируем v2 ключи
3. Добавляем v2 ключи как алиасы к существующим GID
4. Сохраняем изменения
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Добавляем src в path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# Устанавливаем PYTHONPATH
os.environ["PYTHONPATH"] = str(project_root / "src") + ":" + os.environ.get("PYTHONPATH", "")

from registry.global_registry import (
    GlobalIDRegistry,
    iter_contact_keys_v2,
    iter_org_keys,
    iter_contact_keys
)


def migrate_contacts_to_v2(registry: GlobalIDRegistry) -> Dict[str, Any]:
    """Мигрирует контакты на v2 ключи."""
    print("🔄 Миграция контактов на v2...")
    
    migrated_count = 0
    skipped_count = 0
    
    # Загружаем все контакты из реестра
    contacts_file = registry.contact_file
    if not contacts_file.exists():
        print("⚠️ Файл контактов не найден")
        return {"migrated": 0, "skipped": 0}
    
    with open(contacts_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка парсинга строки {line_num}: {e}")
                continue
            
            event_type = record.get("event", "")
            gid = record.get("gid")
            
            if event_type != "create" or not gid:
                continue
            
            # Извлекаем данные контакта из ключей
            keys = []
            primary_key = tuple(record.get("key", []))
            if primary_key:
                keys.append(primary_key)
            
            aliases = [tuple(alias) for alias in record.get("aliases", [])]
            keys.extend(aliases)
            
            # Восстанавливаем данные контакта из ключей
            contact_data = extract_contact_from_keys(keys)
            
            if not contact_data.get("email"):
                skipped_count += 1
                continue
            
            # Генерируем v2 ключи
            v2_keys = list(iter_contact_keys_v2(contact_data, contact_data.get("org_gid")))
            
            if not v2_keys:
                skipped_count += 1
                continue
            
            # Проверяем, есть ли уже v2 ключи
            has_v2_keys = any(
                key[1] in ["EMAIL_GLOBAL", "EMAIL_IN_ORG", "PHONE_GLOBAL", "PHONE_IN_ORG"]
                for key in keys if len(key) >= 2
            )
            
            if has_v2_keys:
                skipped_count += 1
                continue
            
            # Добавляем v2 ключи как алиасы
            alias_added, conflicts = registry._ensure_aliases(
                gid, v2_keys, bucket="contacts"
            )
            
            if alias_added:
                migrated_count += 1
                print(f"  ✅ Мигрирован контакт: {contact_data.get('email', 'unknown')} ({gid[:8]}...)")
                
                # Добавляем события алиасов в файл
                for v2_key in v2_keys:
                    if v2_key not in keys:
                        alias_event = {
                            "event": "alias",
                            "gid": gid,
                            "alias": list(v2_key),
                            "created_at": "2025-10-23T16:00:00Z",
                            "source": "v2_migration"
                        }
                        registry._append_event("contacts", alias_event)
            else:
                skipped_count += 1
    
    return {"migrated": migrated_count, "skipped": skipped_count}


def extract_contact_from_keys(keys: List[tuple]) -> Dict[str, Any]:
    """Восстанавливает данные контакта из ключей."""
    email = None
    phones = []
    org_gid = None
    
    for key in keys:
        if len(key) >= 3:
            key_type = key[1]
            
            if key_type in ["EMAIL", "EMAIL_GLOBAL", "EMAIL_IN_ORG"]:
                email = key[-1]
            elif key_type in ["PHONE", "PHONE_GLOBAL", "PHONE_IN_ORG"]:
                phones.append({"number": key[-1]})
            
            # Извлекаем org_gid
            if len(key) >= 3 and key[2] not in ["PERSONAL"] and "-" in key[2]:
                org_gid = key[2]
    
    return {
        "email": email,
        "phones": phones,
        "org_gid": org_gid
    }


def migrate_organizations_to_v2(registry: GlobalIDRegistry) -> Dict[str, Any]:
    """Мигрирует организации на v2 ключи (добавляет NAME ключ)."""
    print("🔄 Миграция организаций на v2...")
    
    migrated_count = 0
    skipped_count = 0
    
    # Загружаем все организации из реестра
    orgs_file = registry.org_file
    if not orgs_file.exists():
        print("⚠️ Файл организаций не найден")
        return {"migrated": 0, "skipped": 0}
    
    with open(orgs_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка парсинга строки {line_num}: {e}")
                continue
            
            event_type = record.get("event", "")
            gid = record.get("gid")
            
            if event_type != "create" or not gid:
                continue
            
            # Извлекаем данные организации из ключей
            keys = []
            primary_key = tuple(record.get("key", []))
            if primary_key:
                keys.append(primary_key)
            
            aliases = [tuple(alias) for alias in record.get("aliases", [])]
            keys.extend(aliases)
            
            # Восстанавливаем данные организации из ключей
            org_data = extract_org_from_keys(keys)
            
            if not org_data.get("name"):
                skipped_count += 1
                continue
            
            # Генерируем все ключи (включая NAME)
            all_keys = list(iter_org_keys(org_data))
            
            # Проверяем, есть ли уже NAME ключ
            has_name_key = any(
                key[1] == "NAME" for key in keys if len(key) >= 2
            )
            
            if has_name_key:
                skipped_count += 1
                continue
            
            # Находим NAME ключ и добавляем его
            name_key = None
            for key in all_keys:
                if len(key) >= 2 and key[1] == "NAME":
                    name_key = key
                    break
            
            if not name_key:
                skipped_count += 1
                continue
            
            # Добавляем NAME ключ как алиас
            alias_added, conflicts = registry._ensure_aliases(
                gid, [name_key], bucket="organizations"
            )
            
            if alias_added:
                migrated_count += 1
                print(f"  ✅ Мигрирована организация: {org_data.get('name', 'unknown')} ({gid[:8]}...)")
                
                # Добавляем событие алиаса в файл
                alias_event = {
                    "event": "alias",
                    "gid": gid,
                    "alias": list(name_key),
                    "created_at": "2025-10-23T16:00:00Z",
                    "source": "v2_migration"
                }
                registry._append_event("organizations", alias_event)
            else:
                skipped_count += 1
    
    return {"migrated": migrated_count, "skipped": skipped_count}


def extract_org_from_keys(keys: List[tuple]) -> Dict[str, Any]:
    """Восстанавливает данные организации из ключей."""
    name = None
    inn = None
    website = None
    city = None
    
    for key in keys:
        if len(key) >= 3:
            key_type = key[1]
            
            if key_type == "INN":
                inn = key[2]
            elif key_type == "DOMAIN":
                website = f"https://{key[2]}"
            elif key_type == "NAME_CITY":
                name = key[2]
                city = key[3]
            elif key_type == "NAME":
                name = key[2]
    
    return {
        "name": name,
        "inn": inn,
        "website": website,
        "city": city
    }


def main():
    print("🚀 Начинаем миграцию реестра на GID v2")
    print("=" * 60)
    
    # Инициализируем реестр
    registry = GlobalIDRegistry()
    
    # Создаём бэкап перед миграцией
    backup_path = Path("registry/backups/pre-migration-v2-20251023.tar.gz")
    if not backup_path.exists():
        print("💾 Создаём бэкап...")
        import tarfile
        
        backup_path.parent.mkdir(exist_ok=True)
        with tarfile.open(backup_path, "w:gz") as tar:
            for file in ["registry/contacts.jsonl", "registry/organizations.jsonl"]:
                if Path(file).exists():
                    tar.add(file)
        print(f"✅ Бэкап сохранён: {backup_path}")
    
    # Мигрируем контакты
    contact_results = migrate_contacts_to_v2(registry)
    
    # Мигрируем организации
    org_results = migrate_organizations_to_v2(registry)
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ МИГРАЦИИ")
    print("=" * 60)
    print(f"👥 Контакты:")
    print(f"   ✅ Мигрировано: {contact_results['migrated']}")
    print(f"   ⏭️ Пропущено: {contact_results['skipped']}")
    print(f"🏢 Организации:")
    print(f"   ✅ Мигрировано: {org_results['migrated']}")
    print(f"   ⏭️ Пропущено: {org_results['skipped']}")
    
    total_migrated = contact_results['migrated'] + org_results['migrated']
    if total_migrated > 0:
        print(f"\n🎉 Успешно мигрировано записей: {total_migrated}")
        print("🔄 Запускаем верификацию...")
        
        # Запускаем верификацию
        import subprocess
        result = subprocess.run([
            sys.executable, "scripts/verify_gid_v2_migration_simple.py"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Ошибки:", result.stderr)
    else:
        print("\n⚠️ Ничего не мигрировано. Возможно, всё уже на v2.")


if __name__ == "__main__":
    main()