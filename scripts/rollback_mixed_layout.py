#!/usr/bin/env python3
"""
🔧 Откат сломанных mixed-layout контактов.

10 контактов были испорчены неправильным fix_mixed_layout:
- Faizer, Camino, IT, Smartlab, Lek54, Imbian, e.ovcharenko, АГУ, Сиб ФНКЦ
были конвертированы в кириллицу, хотя были нормальными латинскими словами.

Этот скрипт восстанавливает их givenName из displayName.
"""

import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "config" / "google_token.json"
SCOPES = ["https://www.googleapis.com/auth/contacts"]


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("people", "v1", credentials=creds)


def api_call_with_retry(request_fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return request_fn().execute()
        except (BrokenPipeError, ConnectionError) as e:
            if attempt < max_retries - 1:
                print(f"      ⚠️ {type(e).__name__}, retry {attempt+1}...")
                time.sleep(60)
                continue
            raise
        except HttpError as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                print(f"      ⏳ Rate limit, retry {attempt+1}...")
                time.sleep(60)
                continue
            raise


def load_all_contacts(service):
    contacts = []
    page_token = None
    page = 0
    while True:
        page += 1
        r = api_call_with_retry(
            lambda pt=page_token: service.people().connections().list(
                resourceName="people/me", pageSize=500, pageToken=pt,
                personFields="names,emailAddresses,phoneNumbers,organizations,metadata",
                sources=["READ_SOURCE_TYPE_CONTACT"],
            )
        )
        batch = r.get("connections", [])
        contacts.extend(batch)
        page_token = r.get("nextPageToken")
        if not page_token:
            break
        if page % 3 == 0:
            print(f"   Загружено {len(contacts)} контактов...")
    return contacts


# Контакты, которые были сломаны — восстанавливаем givenName из displayName
# Формат: (search_display_substring, correct_gn)
BROKEN_CONTACTS = [
    ("Дарья Smartlab", "Дарья"),
    ("IT Специалист", "IT Специалист"),
    ("Коленский Alexey", "Alexey"),
    ("Аптеки Lek54", "Аптеки"),
    ("Елизавета Овчаренко", "Елизавета"),
    ("Imbian Артём", "Артём"),
    ("Казин Евгений Faizer", "Евгений"),
    ("Игорь Ананьин танго Camino", "Игорь"),
    ("Колтунова Анастасия Максимовна", "Анастасия"),
    ("Сергей. IT Сиб ФНКЦ", "Сергей."),
]


def main():
    do_update = "--update" in sys.argv
    if not do_update:
        print("Использование: python scripts/rollback_mixed_layout.py --update")
        return

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    fixed = 0
    errors = 0

    for search_str, correct_gn in BROKEN_CONTACTS:
        # Найти контакт
        found = None
        for c in contacts:
            names = c.get("names", [{}])
            if names:
                dn = names[0].get("displayName", "")
                if search_str in dn:
                    found = c
                    break
        
        if not found:
            print(f"   ⚠️ Не найден: {search_str}")
            continue

        resource = found["resourceName"]
        names = found.get("names", [{}])
        n = names[0] if names else {}
        current_gn = n.get("givenName", "")
        fn = n.get("familyName", "")
        mn = n.get("middleName", "")
        display = n.get("displayName", "")

        if current_gn == correct_gn:
            print(f"   ✅ Уже ОК: {display}")
            continue

        print(f"   🔧 {display}: gn '{current_gn}' → '{correct_gn}'")

        # Получаем свежий контакт
        try:
            fresh = api_call_with_retry(
                lambda r=resource: service.people().get(
                    resourceName=r,
                    personFields="names,metadata",
                )
            )
        except Exception as e:
            print(f"      ❌ get failed: {e}")
            errors += 1
            continue

        etag = fresh.get("etag", "")
        existing_names = fresh.get("names", [{}])
        if not existing_names:
            errors += 1
            continue

        name_obj = existing_names[0].copy()
        name_obj["givenName"] = correct_gn

        body = {
            "etag": etag,
            "names": [name_obj],
        }

        try:
            api_call_with_retry(
                lambda r=resource, b=body: service.people().updateContact(
                    resourceName=r,
                    updatePersonFields="names",
                    body=b,
                )
            )
            fixed += 1
            print(f"      ✅ Исправлено")
        except Exception as e:
            print(f"      ❌ {e}")
            errors += 1

        time.sleep(0.5)

    print(f"\n✅ Результат: {fixed} восстановлено, {errors} ошибок")


if __name__ == "__main__":
    main()
