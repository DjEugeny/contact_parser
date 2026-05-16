#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📧 Google Contacts Enrich — сопоставление и обогащение контактов.

Читает senders_cache.json, подключается к Google People API,
сопоставляет ФИО, обогащает недостающими email-адресами.

Режимы:
  --dry-run   показать что будет сделано, без записи
  --enrich    выполнить обогащение (запись в Google Contacts)
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Импортируем parse_fio из extract_senders для fallback-парсинга displayName
import importlib.util
_extract_senders_spec = importlib.util.spec_from_file_location(
    "extract_senders", str(Path(__file__).resolve().parent / "extract_senders.py")
)
_extract_senders_mod = importlib.util.module_from_spec(_extract_senders_spec)
_extract_senders_spec.loader.exec_module(_extract_senders_mod)
parse_fio = _extract_senders_mod.parse_fio

# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENDERS_FILE = PROJECT_ROOT / "data" / "senders_cache.json"
TOKEN_FILE = PROJECT_ROOT / "config" / "google_token.json"
CREDENTIALS_FILE = PROJECT_ROOT / "config" / "google_credentials.json"
MATCH_RESULTS_FILE = PROJECT_ROOT / "data" / "match_results.json"
ENRICHMENT_REPORT_FILE = PROJECT_ROOT / "data" / "enrichment_report.json"

SCOPES = ["https://www.googleapis.com/auth/contacts"]


# ──────────────────────────────────────────────
# Транслитерация RU→EN
# ──────────────────────────────────────────────

_RU_TO_EN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

def transliterate(text: str) -> str:
    """🔄 Транслитерация кириллицы → латиница."""
    result = []
    for ch in text.lower():
        result.append(_RU_TO_EN.get(ch, ch))
    return "".join(result)


# ──────────────────────────────────────────────
# Нормализация ФИО для сравнения
# ──────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """
    🔤 Нормализация имени для сравнения.

    Приводит к нижнему регистру, убирает лишние пробелы и дефисы.
    """
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[-]', ' ', name)
    return name


def get_name_key(name_parts: Dict) -> str:
    """
    🔑 Формирует ключ для сравнения из name_parts.

    Приоритет: last+first+middle → last+first → last
    """
    parts = []
    if "last" in name_parts:
        parts.append(name_parts["last"])
    if "first" in name_parts:
        parts.append(name_parts["first"])
    elif "first_init" in name_parts:
        parts.append(name_parts["first_init"])
    if "middle" in name_parts:
        parts.append(name_parts["middle"])
    elif "middle_init" in name_parts:
        parts.append(name_parts["middle_init"])

    return normalize_name(" ".join(parts))


# ──────────────────────────────────────────────
# Чтение данных
# ──────────────────────────────────────────────

def load_senders() -> List[Dict]:
    """📂 Загружает senders_cache.json."""
    if not SENDERS_FILE.exists():
        print(f"❌ Файл отправителей не найден: {SENDERS_FILE}")
        print("   Сначала запустите: python scripts/extract_senders.py")
        sys.exit(1)

    with open(SENDERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("senders", [])


def get_credentials() -> Credentials:
    """🔑 Загружает OAuth credentials."""
    if not TOKEN_FILE.exists():
        print(f"❌ Токен не найден: {TOKEN_FILE}")
        print("   Сначала запустите: python scripts/google_auth_setup.py")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds.expired and creds.refresh_token:
        print("🔄 Обновление токена...")
        creds.refresh(Request())
        # Сохраняем обновлённый
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes),
        }
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)

    return creds


def fetch_google_contacts(service) -> List[Dict]:
    """
    📥 Загружает все Google контакты с ФИО и email.

    Returns:
        [{resource_name, names, email_addresses, phones}]
    """
    contacts = []
    page_token = None

    print("📥 Загрузка Google контактов...")

    while True:
        try:
            results = service.people().connections().list(
                resourceName="people/me",
                pageSize=500,
                pageToken=page_token,
                personFields="names,emailAddresses,phoneNumbers",
            ).execute()
        except HttpError as e:
            print(f"❌ Ошибка API: {e}")
            break

        connections = results.get("connections", [])
        contacts.extend(connections)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

        # Throttling: 300 req/min → пауза
        time.sleep(0.2)

    print(f"   ✅ Загружено контактов: {len(contacts)}")
    return contacts


def extract_google_contact_info(contact: Dict) -> Dict:
    """
    🔍 Извлекает имя и email из Google контакта.
    """
    names = contact.get("names", [])
    emails = contact.get("emailAddresses", [])
    phones = contact.get("phoneNumbers", [])

    # Берём основное имя (primary или первое)
    display_name = ""
    name_parts = {}
    alt_name_parts = {}
    if names:
        primary_name = None
        for n in names:
            if n.get("metadata", {}).get("primary", False):
                primary_name = n
                break
        if not primary_name:
            primary_name = names[0]

        display_name = primary_name.get("displayName", "")
        family_name = primary_name.get("familyName", "")
        given_name = primary_name.get("givenName", "")
        middle_name = primary_name.get("middleName", "")

        name_parts = {}
        if family_name:
            name_parts["last"] = family_name
        if given_name:
            name_parts["first"] = given_name
        if middle_name:
            name_parts["middle"] = middle_name

        # Альтернативный парсинг из displayName (fallback для familyName/givenName перепутаных)
        alt_name_parts = {}
        if display_name:
            alt_name_parts = parse_fio(display_name)

    existing_emails = [e.get("value", "").lower() for e in emails if e.get("value")]
    existing_phones = [p.get("value", "") for p in phones if p.get("value")]

    return {
        "resource_name": contact.get("resourceName", ""),
        "etag": contact.get("etag", ""),
        "display_name": display_name,
        "name_parts": name_parts,
        "alt_name_parts": alt_name_parts,
        "existing_emails": existing_emails,
        "existing_phones": existing_phones,
        "raw": contact,
    }


# ──────────────────────────────────────────────
# Мэтчинг
# ──────────────────────────────────────────────

def match_senders_to_google(
    senders: List[Dict],
    google_contacts: List[Dict],
) -> Dict:
    """
    🎯 Сопоставляет отправителей с Google контактами.

    Алгоритм:
    1. Точное совпадение ФИО (last+first+middle)
    2. Фамилия+имя (без отчества)
    3. Фамилия (если единственный кандидат)
    4. Транслитерация (Ivanov ↔ Иванов)
    """
    # Подготавливаем индексы Google контактов
    google_by_key: Dict[str, List[Dict]] = {}  # name_key → [contact_info]
    google_by_translit: Dict[str, List[Dict]] = {}

    for gc in google_contacts:
        info = extract_google_contact_info(gc)
        if not info["name_parts"]:
            continue

        # Собираем все варианты name_parts для этого контакта
        all_parts = [info["name_parts"]]
        if info.get("alt_name_parts") and info["alt_name_parts"] != info["name_parts"]:
            all_parts.append(info["alt_name_parts"])
            # Swap-вариант: если alt_name_parts имеет last+first, пробуем поменять местами
            # (displayName 'Татьяна Кошкина' → last='Татьяна', first='Кошкина' → swapped: last='Кошкина', first='Татьяна')
            alt = info["alt_name_parts"]
            if "last" in alt and "first" in alt:
                swapped = {"last": alt["first"], "first": alt["last"]}
                if "middle" in alt:
                    swapped["middle"] = alt["middle"]
                if "middle_init" in alt:
                    swapped["middle_init"] = alt["middle_init"]
                all_parts.append(swapped)

        added_keys = set()  # Чтобы не дублировать один и тот же контакт под одним ключом

        for parts in all_parts:
            # Ключ из ФИО
            key = get_name_key(parts)
            if key and key not in added_keys:
                google_by_key.setdefault(key, []).append(info)
                added_keys.add(key)

                # Транслитерированный ключ
                translit_key = transliterate(key)
                if translit_key != key:
                    google_by_translit.setdefault(translit_key, []).append(info)

            # Ключ только фамилия+имя
            short_parts = {k: v for k, v in parts.items() if k in ("last", "first")}
            if short_parts:
                short_key = get_name_key(short_parts)
                if short_key and short_key not in added_keys:
                    google_by_key.setdefault(short_key, []).append(info)
                    added_keys.add(short_key)
                    short_translit = transliterate(short_key)
                if short_translit != short_key:
                    google_by_translit.setdefault(short_translit, []).append(info)

    # Мэтчим каждого отправителя
    matched = []
    unmatched_senders = []
    # used_google_contacts — ТОЛЬКО для уровня 4 (last_name_only),
    # чтобы избежать ложных срабатываний.
    # Уровни 1-3: один Google-контакт может получить несколько email.
    used_for_last_name_only = set()

    for sender in senders:
        if not sender["name_parts"]:
            # Нет ФИО — не можем сопоставить
            unmatched_senders.append(sender)
            continue

        name_key = get_name_key(sender["name_parts"])
        translit_key = transliterate(name_key)

        # Пробуем уровни мэтчинга
        match_result = None
        match_type = None

        # Уровень 1: Точное ФИО (один контакт может получить несколько email)
        if name_key in google_by_key:
            candidates = google_by_key[name_key]
            if candidates:
                match_result = candidates[0]
                match_type = "exact_fio"

        # Уровень 2: Транслитерация точного ФИО
        # Проверяем и google_by_translit (кириллица→латиница),
        # и google_by_key (Google-контакт уже на латинице)
        if not match_result:
            candidates = []
            if translit_key in google_by_translit:
                candidates = google_by_translit[translit_key]
            if translit_key in google_by_key and translit_key != name_key:
                # translit_key может совпадать с name_key если sender уже латиница
                for c in google_by_key[translit_key]:
                    if c not in candidates:
                        candidates.append(c)
            if candidates:
                match_result = candidates[0]
                match_type = "translit_fio"

        # Уровень 3: Фамилия+имя (без отчества)
        if not match_result:
            short_parts = {k: v for k, v in sender["name_parts"].items() if k in ("last", "first")}
            if len(short_parts) >= 2:
                short_key = get_name_key(short_parts)
                if short_key in google_by_key:
                    candidates = google_by_key[short_key]
                    # Разрешаем мэтч если 1 кандидат, или все кандидаты — дубликаты (одинаковый display_name)
                    if len(candidates) == 1:
                        match_result = candidates[0]
                        match_type = "last_first_only"
                    elif len(candidates) > 1:
                        display_names = [c["display_name"] for c in candidates]
                        if len(set(display_names)) == 1:
                            # Все кандидаты — дубликаты одного контакта
                            match_result = candidates[0]
                            match_type = "last_first_only"

        # Уровень 4: Фамилия (консервативный — только неиспользованные)
        if not match_result and "last" in sender["name_parts"]:
            last_key = normalize_name(sender["name_parts"]["last"])
            last_translit = transliterate(last_key)
            candidates = []
            for key in [last_key, last_translit]:
                if key in google_by_key:
                    candidates.extend(google_by_key[key])
                if key in google_by_translit:
                    candidates.extend(google_by_translit[key])

            # Уникальные и неиспользованные (для уровня 4 — консервативно)
            seen = set()
            unique_candidates = []
            for c in candidates:
                if c["resource_name"] not in used_for_last_name_only and c["resource_name"] not in seen:
                    seen.add(c["resource_name"])
                    unique_candidates.append(c)

            if len(unique_candidates) == 1:
                match_result = unique_candidates[0]
                match_type = "last_name_only"
                used_for_last_name_only.add(match_result["resource_name"])

        if match_result:
            # Проверяем: нужен ли email?
            sender_email = sender["email"].lower()
            already_has = sender_email in match_result["existing_emails"]

            action = "skip_already_has" if already_has else "add_email"

            matched.append({
                "sender_email": sender_email,
                "sender_name": sender["display_name"],
                "google_contact_id": match_result["resource_name"],
                "google_name": match_result["display_name"],
                "match_type": match_type,
                "existing_emails": match_result["existing_emails"],
                "action": action,
                "etag": match_result["etag"],
                "raw_contact": match_result["raw"],
            })
        else:
            unmatched_senders.append(sender)

    # Google контакты без мэтча (для статистики)
    matched_google_ids = {m["google_contact_id"] for m in matched}
    unmatched_google = []
    for gc in google_contacts:
        info = extract_google_contact_info(gc)
        if info["resource_name"] not in matched_google_ids and info["name_parts"]:
            unmatched_google.append({
                "resource_name": info["resource_name"],
                "display_name": info["display_name"],
                "existing_emails": info["existing_emails"],
            })

    return {
        "matched": matched,
        "unmatched_senders": unmatched_senders,
        "unmatched_google_contacts": unmatched_google,
    }


# ──────────────────────────────────────────────
# Dry-run / Enrichment
# ──────────────────────────────────────────────

def dry_run(match_results: Dict) -> None:
    """
    👁️ Показывает что будет сделано, без записи.
    """
    matched = match_results["matched"]
    to_add = [m for m in matched if m["action"] == "add_email"]
    to_skip = [m for m in matched if m["action"] == "skip_already_has"]

    print()
    print("=" * 80)
    print("👁️ DRY RUN — предпросмотр обогащения")
    print("=" * 80)

    print(f"\n📊 Итого:")
    print(f"   Мэтчей всего: {len(matched)}")
    print(f"   Будет добавлено email: {len(to_add)}")
    print(f"   Уже есть email (пропуск): {len(to_skip)}")
    print(f"   Не сопоставлено отправителей: {len(match_results['unmatched_senders'])}")
    print(f"   Не сопоставлено Google контактов: {len(match_results['unmatched_google_contacts'])}")

    if to_add:
        print(f"\n📝 Контакты для обогащения ({len(to_add)}):")
        print(f"   {'Google контакт':<30} {'Текущие email':<35} {'Добавить':<30} {'Тип мэтча'}")
        print(f"   {'-'*30} {'-'*35} {'-'*30} {'-'*15}")
        for m in to_add:
            existing = ", ".join(m["existing_emails"][:2]) if m["existing_emails"] else "—"
            if len(m["existing_emails"]) > 2:
                existing += f" +{len(m['existing_emails'])-2}"
            print(f"   {m['google_name']:<30} {existing:<35} {m['sender_email']:<30} {m['match_type']}")

    if to_skip:
        print(f"\n✅ Пропуски (email уже есть, {len(to_skip)}):")
        for m in to_skip[:5]:
            print(f"   {m['google_name']}: {m['sender_email']} ✓")
        if len(to_skip) > 5:
            print(f"   ... и ещё {len(to_skip)-5}")


def enrich_contacts(service, match_results: Dict) -> Dict:
    """
    ✍️ Записывает email в Google контакты.
    """
    to_add = [m for m in match_results["matched"] if m["action"] == "add_email"]

    if not to_add:
        print("✅ Нечего добавлять — все email уже есть в контактах")
        return {"enriched": 0, "errors": 0, "details": []}

    print(f"\n✍️ Обогащение {len(to_add)} контактов...")

    enriched = 0
    errors = 0
    details = []

    for i, m in enumerate(to_add, 1):
        print(f"   [{i}/{len(to_add)}] {m['google_name']} ← {m['sender_email']}")

        try:
            # Получаем текущий контакт полностью
            contact = service.people().get(
                resourceName=m["google_contact_id"],
                personFields="names,emailAddresses,phoneNumbers",
            ).execute()

            # Добавляем email
            email_addresses = contact.get("emailAddresses", [])
            email_addresses.append({
                "value": m["sender_email"],
                "type": "work",
            })

            # Обновляем контакт
            update_contact = {
                "emailAddresses": email_addresses,
                "etag": contact["etag"],
            }

            # People API updateContact: передаём только поля,
            # указанные в updatePersonFields (emailAddresses).
            # names нужно передать чтобы не потерять, но phoneNumbers — нет,
            # т.к. его нет в updatePersonFields.
            if "names" in contact:
                update_contact["names"] = contact["names"]

            service.people().updateContact(
                resourceName=m["google_contact_id"],
                body=update_contact,
                updatePersonFields="emailAddresses",
            ).execute()

            enriched += 1
            details.append({
                "google_name": m["google_name"],
                "added_email": m["sender_email"],
                "status": "success",
            })

            # Throttling
            time.sleep(0.3)

        except HttpError as e:
            errors += 1
            print(f"      ❌ Ошибка: {e}")
            details.append({
                "google_name": m["google_name"],
                "added_email": m["sender_email"],
                "status": "error",
                "error": str(e),
            })

    report = {
        "enriched": enriched,
        "errors": errors,
        "total_attempted": len(to_add),
        "details": details,
    }

    # Сохраняем отчёт
    with open(ENRICHMENT_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Результат: обогащено {enriched}, ошибок {errors}")
    print(f"💾 Отчёт: {ENRICHMENT_REPORT_FILE}")

    return report


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    """🚀 Точка входа."""
    dry_run_mode = "--dry-run" in sys.argv or "--dryrun" in sys.argv
    enrich_mode = "--enrich" in sys.argv
    limit = 0
    match_types_filter = None

    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
        elif arg.startswith("--match-types="):
            match_types_filter = [t.strip() for t in arg.split("=", 1)[1].split(",")]

    if not dry_run_mode and not enrich_mode:
        print("📧 Google Contacts Enrich — сопоставление и обогащение")
        print()
        print("Использование:")
        print("  python scripts/google_contacts_enrich.py --dry-run   # предпросмотр")
        print("  python scripts/google_contacts_enrich.py --enrich    # запись в Google")
        print()
        print("Опции:")
        print("  --limit=N            ограничить число записей (для теста)")
        print("  --match-types=T1,T2  фильтр по типам мэтча")
        print("                        типы: exact_fio, translit_fio, last_first_only, last_name_only")
        print()
        print("Примеры:")
        print("  --enrich --limit=5 --match-types=exact_fio  # пилот на 5 контактах")
        print("  --dry-run --match-types=last_name_only      # ревью опасных мэтчей")
        sys.exit(0)

    # 1. Загружаем отправителей
    print("📂 Загрузка отправителей...")
    senders = load_senders()
    print(f"   ✅ Отправителей: {len(senders)}")

    # 2. Подключаемся к Google
    print("\n🔐 Подключение к Google People API...")
    creds = get_credentials()
    service = build("people", "v1", credentials=creds)

    # 3. Загружаем Google контакты
    google_contacts = fetch_google_contacts(service)

    # 4. Мэтчинг
    print("\n🎯 Сопоставление ФИО...")
    match_results = match_senders_to_google(senders, google_contacts)

    # Фильтрация по --match-types
    if match_types_filter:
        match_results["matched"] = [
            m for m in match_results["matched"]
            if m["match_type"] in match_types_filter
        ]
        print(f"   🔍 Фильтр по типам мэтча: {match_types_filter} → {len(match_results['matched'])} мэтчей")

    # Фильтрация по --limit (ограничиваем add_email действия)
    if limit > 0:
        to_add = [m for m in match_results["matched"] if m["action"] == "add_email"]
        to_skip = [m for m in match_results["matched"] if m["action"] != "add_email"]
        limited_add = to_add[:limit]
        match_results["matched"] = to_skip + limited_add
        print(f"   📊 Лимит: {limit} записей (из {len(to_add)} к добавлению)")

    # Сохраняем результаты мэтчинга
    # Убираем raw_contact (слишком большой для JSON)
    for m in match_results["matched"]:
        m.pop("raw_contact", None)

    with open(MATCH_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(match_results, f, ensure_ascii=False, indent=2)
    print(f"💾 Результаты мэтчинга: {MATCH_RESULTS_FILE}")

    # 5. Dry-run или обогащение
    if dry_run_mode:
        dry_run(match_results)
    elif enrich_mode:
        dry_run(match_results)
        print()
        confirm = input("⚠️ Подтвердите запись в Google Contacts (yes/no): ")
        if confirm.lower() == "yes":
            enrich_contacts(service, match_results)
        else:
            print("❌ Отменено")


if __name__ == "__main__":
    main()
