#!/usr/bin/env python3
"""
🔧 Обновление displayName в Google Contacts.

Проблема: при обновлении familyName/givenName/middleName через API
displayName (заголовок карточки) не пересчитывается автоматически.
Этот скрипт обновляет displayName для контактов, где он не совпадает
с Имя + Отчество + Фамилия (в любом порядке).

НЕ трогает контакты, где displayName содержит лишние слова (должности, org).

Использование:
  python scripts/google_contacts_fix_displaynames.py --report
  python scripts/google_contacts_fix_displaynames.py --update
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


def norm_layout(s: str) -> str:
    """Нормализует смешанную раскладку (латинские → кириллица)."""
    if not s:
        return s
    lat_to_rus = str.maketrans("ABCEHKMOPTXYabcehkmoptxy", "АВСЕНКМОРТХУавсенкмортху")
    return s.translate(lat_to_rus)


def needs_displayname_fix(contact: dict) -> tuple:
    """
    Проверяет, нужно ли обновлять displayName.
    Возвращает (needs_fix: bool, new_display: str, reason: str).
    """
    names = contact.get("names", [{}])
    if not names:
        return False, "", ""
    n = names[0]
    fn = (n.get("familyName") or "").strip()
    gn = (n.get("givenName") or "").strip()
    mn = (n.get("middleName") or "").strip()
    display = (n.get("displayName") or "").strip()

    if not display or not (fn or gn):
        return False, "", ""

    # Строим "правильный" displayName: Фамилия Имя Отчество
    expected = " ".join(p for p in [fn, gn, mn] if p)
    if not expected:
        return False, "", ""

    # Нормализуем для сравнения (ё→е, lower, mixed layout)
    expected_norm = norm_layout(expected).lower().replace("ё", "е")
    display_norm = norm_layout(display).lower().replace("ё", "е")

    # Проверяем: displayName содержит ТОЛЬКО слова из fn/gn/mn?
    fio_words = set(norm_layout(w).lower().replace("ё", "е") for w in [fn, gn, mn] if w)
    display_words = set(norm_layout(w).lower().replace("ё", "е") for w in display.split() if w)
    has_extra_words = not display_words.issubset(fio_words)

    # Случай 1: displayName содержит лишние слова — skip
    if has_extra_words:
        return False, "", ""

    # Случай 2: строгая проверка порядка — должен быть "Фамилия Имя Отчество"
    if expected_norm == display_norm:
        # Но проверим КАПС: displayName полностью в верхнем регистре
        if display.isupper() and not expected.isupper():
            return True, expected, f"КАПС displayName: '{display}' → '{expected}'"
        return False, "", ""

    # Случай 3: displayName содержит только ФИО, но порядок или КАПС не тот
    if display.isupper():
        return True, expected, f"КАПС: '{display}' → '{expected}'"
    else:
        return True, expected, f"порядок: '{display}' → '{expected}'"


def main():
    do_report = "--report" in sys.argv
    do_update = "--update" in sys.argv

    if not do_report and not do_update:
        print("Использование:")
        print("  python scripts/google_contacts_fix_displaynames.py --report")
        print("  python scripts/google_contacts_fix_displaynames.py --update")
        return

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    fix_list = []
    for contact in contacts:
        needs, new_display, reason = needs_displayname_fix(contact)
        if needs:
            names = contact.get("names", [{}])
            n = names[0] if names else {}
            fix_list.append({
                "resource_name": contact.get("resourceName", ""),
                "old_display": n.get("displayName", ""),
                "new_display": new_display,
                "fn": n.get("familyName", ""),
                "gn": n.get("givenName", ""),
                "mn": n.get("middleName", ""),
                "reason": reason,
            })

    print(f"\n📊 Найдено: {len(fix_list)} контактов с неправильным displayName")

    # Статистика
    reasons = {}
    for f in fix_list:
        t = f["reason"].split(":")[0]
        reasons[t] = reasons.get(t, 0) + 1
    print("\nПо типам:")
    for t, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"   {t}: {cnt}")

    if do_report:
        print("\nПервые 20:")
        for f in fix_list[:20]:
            print(f"   {f['old_display']} → {f['new_display']} ({f['reason']})")
        return

    if do_update:
        updated = 0
        errors = 0
        for f in fix_list:
            resource = f["resource_name"]
            old_display = f["old_display"]

            # Получаем свежий контакт
            try:
                fresh = api_call_with_retry(
                    lambda r=resource: service.people().get(
                        resourceName=r,
                        personFields="names,metadata",
                    )
                )
            except Exception as e:
                print(f"   ❌ {old_display}: get failed {e}")
                errors += 1
                continue

            etag = fresh.get("etag", "")
            existing_names = fresh.get("names", [{}])
            if not existing_names:
                errors += 1
                continue

            name_obj = existing_names[0].copy()
            name_obj["displayName"] = f["new_display"]

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
                updated += 1
                print(f"   ✅ {old_display} → {f['new_display']} ({f['reason']})")
            except Exception as e:
                print(f"   ❌ {old_display}: {e}")
                errors += 1

            # Rate limit
            if (updated + errors) % 50 == 0 and (updated + errors) > 0:
                print(f"   ⏳ Пауза 30с... ({updated + errors} обработано)")
                time.sleep(30)
            else:
                time.sleep(0.5)

        print(f"\n✅ Результат: {updated} обновлено, {errors} ошибок")


if __name__ == "__main__":
    main()
