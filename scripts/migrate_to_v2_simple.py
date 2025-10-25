#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт миграции реестра на v2 без сложных импортов.
Работает напрямую с JSONL файлами.
"""

import json
import tarfile
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple


def norm_email(value: str) -> str:
    """Нормализует email."""
    if not value:
        return None
    return str(value).strip().lower() or None


def norm_domain(value: str) -> str:
    """Нормализует домен."""
    if not value:
        return None
    value = str(value).strip().lower()
    if "@" in value:
        value = value.split("@", 1)[1]
    if "://" in value:
        from urllib.parse import urlparse
        value = urlparse(value).hostname or ""
    value = value.split("/")[0]
    value = value.split(":")[0]
    value = value.strip(".")
    return value or None


def is_personal_email(email: str) -> bool:
    """Проверяет, является ли email личным."""
    if not email or "@" not in email:
        return False
    
    domain = email.split("@", 1)[1].lower()
    personal_domains = {
        "gmail.com", "yandex.ru", "mail.ru", "yahoo.com", "outlook.com",
        "hotmail.com", "icloud.com", "rambler.ru", "list.ru", "bk.ru",
        "inbox.ru", "mail.ua", "ukr.net", "yandex.com", "ya.ru",
        "gmail.ru", "email.com", "protonmail.com", "tutanota.com"
    }
    return domain in personal_domains


def extract_contact_from_keys(keys: List[List[str]]) -> Dict[str, Any]:
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


def generate_v2_contact_keys(contact_data: Dict[str, Any]) -> List[List[str]]:
    """Генерирует v2 ключи для контакта."""
    email = contact_data.get("email")
    org_gid = contact_data.get("org_gid")
    
    if not email:
        return []
    
    keys = []
    org_key = org_gid if org_gid else "PERSONAL"
    
    if is_personal_email(email):
        # Личный домен - старая логика
        key = ["CONTACT", "EMAIL", org_key, email]
        keys.append(key)
    else:
        # Корпоративный домен - новая логика
        # EMAIL_GLOBAL
        key_global = ["CONTACT", "EMAIL_GLOBAL", email]
        keys.append(key_global)
        
        # EMAIL_IN_ORG (если есть организация)
        if org_gid:
            key_in_org = ["CONTACT", "EMAIL_IN_ORG", org_gid, email]
            keys.append(key_in_org)
    
    return keys


def extract_org_from_keys(keys: List[List[str]]) -> Dict[str, Any]:
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
            elif key_type == "FALLBACK":
                # Извлекаем имя из FALLBACK если возможно
                try:
                    import hashlib
                    # FALLBACK это хеш, но попробуем извлечь имя из других ключей
                    pass
                except:
                    pass
    
    return {
        "name": name,
        "inn": inn,
        "website": website,
        "city": city
    }


def generate_v2_org_keys(org_data: Dict[str, Any]) -> List[List[str]]:
    """Генерирует v2 ключи для организации."""
    keys = []
    
    inn = org_data.get("inn")
    if inn:
        key = ["ORG", "INN", inn]
        keys.append(key)
    
    website = org_data.get("website")
    if website:
        domain = norm_domain(website)
        if domain:
            key = ["ORG", "DOMAIN", domain]
            keys.append(key)
    
    name = org_data.get("name")
    city = org_data.get("city")
    
    if name and city:
        key = ["ORG", "NAME_CITY", name.lower(), city.lower()]
        keys.append(key)
    
    # v2: Детерминированный NAME ключ
    if name:
        key = ["ORG", "NAME", name.lower()]
        keys.append(key)
    
    return keys


def migrate_contacts():
    """Мигрирует контакты."""
    print("🔄 Миграция контактов на v2...")
    
    contacts_file = Path("src/registry/contacts.jsonl")
    if not contacts_file.exists():
        print("⚠️ Файл контактов не найден")
        return 0
    
    migrated = 0
    
    with open(contacts_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if record.get("event") != "create":
                continue
            
            gid = record.get("gid")
            if not gid:
                continue
            
            # Извлекаем существующие ключи
            existing_keys = []
            primary_key = record.get("key", [])
            if primary_key:
                existing_keys.append(primary_key)
            
            aliases = record.get("aliases", [])
            for alias in aliases:
                existing_keys.append(alias)
            
            # Восстанавливаем данные контакта
            contact_data = extract_contact_from_keys(existing_keys)
            
            if not contact_data.get("email"):
                continue
            
            # Генерируем v2 ключи
            v2_keys = generate_v2_contact_keys(contact_data)
            
            if not v2_keys:
                continue
            
            # Проверяем, есть ли уже v2 ключи
            has_v2 = any(
                key[1] in ["EMAIL_GLOBAL", "EMAIL_IN_ORG", "PHONE_GLOBAL", "PHONE_IN_ORG"]
                for key in existing_keys if len(key) >= 2
            )
            
            if has_v2:
                continue
            
            # Добавляем v2 ключи как алиасы
            for v2_key in v2_keys:
                if v2_key not in existing_keys:
                    alias_event = {
                        "event": "alias",
                        "gid": gid,
                        "alias": v2_key,
                        "created_at": "2025-10-23T16:00:00Z",
                        "source": "v2_migration"
                    }
                    
                    # Записываем в файл
                    with open(contacts_file, 'a', encoding='utf-8') as out_f:
                        out_f.write(json.dumps(alias_event, ensure_ascii=False) + "\n")
                    
                    migrated += 1
                    print(f"  ✅ {contact_data.get('email')} ({gid[:8]}...) -> {v2_key[1]}")
    
    return migrated


def migrate_organizations():
    """Мигрирует организации."""
    print("🔄 Миграция организаций на v2...")
    
    orgs_file = Path("src/registry/organizations.jsonl")
    if not orgs_file.exists():
        print("⚠️ Файл организаций не найден")
        return 0
    
    migrated = 0
    
    with open(orgs_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if record.get("event") != "create":
                continue
            
            gid = record.get("gid")
            if not gid:
                continue
            
            # Извлекаем существующие ключи
            existing_keys = []
            primary_key = record.get("key", [])
            if primary_key:
                existing_keys.append(primary_key)
            
            aliases = record.get("aliases", [])
            for alias in aliases:
                existing_keys.append(alias)
            
            # Восстанавливаем данные организации
            org_data = extract_org_from_keys(existing_keys)
            
            if not org_data.get("name"):
                continue
            
            # Генерируем все ключи (включая NAME)
            all_keys = generate_v2_org_keys(org_data)
            
            # Проверяем, есть ли уже NAME ключ
            has_name = any(
                key[1] == "NAME" for key in existing_keys if len(key) >= 2
            )
            
            if has_name:
                continue
            
            # Находим NAME ключ и добавляем его
            for key in all_keys:
                if len(key) >= 2 and key[1] == "NAME":
                    if key not in existing_keys:
                        alias_event = {
                            "event": "alias",
                            "gid": gid,
                            "alias": key,
                            "created_at": "2025-10-23T16:00:00Z",
                            "source": "v2_migration"
                        }
                        
                        # Записываем в файл
                        with open(orgs_file, 'a', encoding='utf-8') as out_f:
                            out_f.write(json.dumps(alias_event, ensure_ascii=False) + "\n")
                        
                        migrated += 1
                        print(f"  ✅ {org_data.get('name')} ({gid[:8]}...) -> NAME")
                    break
    
    return migrated


def create_backup():
    """Создаёт бэкап реестра."""
    print("💾 Создаём бэкап...")
    
    backup_path = Path("registry/backups/pre-migration-v2-simple-20251023.tar.gz")
    backup_path.parent.mkdir(exist_ok=True)
    
    with tarfile.open(backup_path, "w:gz") as tar:
        for file in ["src/registry/contacts.jsonl", "src/registry/organizations.jsonl"]:
            if Path(file).exists():
                tar.add(file)
    
    print(f"✅ Бэкап сохранён: {backup_path}")


def main():
    print("🚀 Начинаем простую миграцию реестра на GID v2")
    print("=" * 60)
    
    # Создаём бэкап
    create_backup()
    
    # Мигрируем контакты
    contacts_migrated = migrate_contacts()
    
    # Мигрируем организации
    orgs_migrated = migrate_organizations()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ МИГРАЦИИ")
    print("=" * 60)
    print(f"👥 Контактов мигрировано: {contacts_migrated}")
    print(f"🏢 Организаций мигрировано: {orgs_migrated}")
    
    total_migrated = contacts_migrated + orgs_migrated
    if total_migrated > 0:
        print(f"\n🎉 Успешно мигрировано записей: {total_migrated}")
        print("🔄 Запускаем верификацию...")
        
        # Запускаем верификацию
        import subprocess
        import sys
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