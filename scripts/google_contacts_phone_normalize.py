#!/usr/bin/env python3
"""
📞 Нормализация телефонов в Google Contacts.

Использование:
  python scripts/google_contacts_phone_normalize.py --report     # Отчёт о телефонах
  python scripts/google_contacts_phone_normalize.py --update     # Обновить телефоны
  python scripts/google_contacts_phone_normalize.py --update --dedup-phones  # + удалить дубли телефонов
"""

import json
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Прямой импорт PhoneNormalizer (без цепочки постпроцессинга)
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "phone_normalizer",
    str(Path(__file__).resolve().parent.parent / "src" / "postprocessing" / "phone_normalizer.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
PhoneNormalizer = _mod.PhoneNormalizer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "config" / "google_token.json"
SCOPES = ["https://www.googleapis.com/auth/contacts"]

# Google phone type mapping
GOOGLE_PHONE_TYPES = {
    "mobile": "mobile",
    "office": "work",
    "home": "home",
    "main": "work",
    "other": "other",
    "incomplete": "other",
}


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("people", "v1", credentials=creds)


def api_call_with_retry(request_fn, max_retries=3):
    """Вызов Google API с retry на 429/BrokenPipe/ConnectionError.
    request_fn: callable, возвращающий HttpRequest (нужно .execute())
    """
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
    """Загрузка всех контактов с прогрессом."""
    contacts = []
    page_token = None
    page = 0
    while True:
        page += 1
        r = api_call_with_retry(
            lambda: service.people().connections().list(
                resourceName="people/me",
                pageSize=500,
                pageToken=page_token,
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


def normalize_phones_for_contact(contact: dict, normalizer: PhoneNormalizer) -> list:
    """
    Нормализует все телефоны контакта.
    Возвращает список dicts: {original, normalized, formatted, type, extension, changed, google_type}
    """
    results = []
    phones = contact.get("phoneNumbers", [])

    for phone_entry in phones:
        original = phone_entry.get("value", "")
        if not original:
            continue

        # Нормализуем через PhoneNormalizer
        norm = normalizer.normalize_contact_phone(original)

        # Определяем тип для Google
        internal_type = norm.get("phone_type", "неизвестно")
        google_type = GOOGLE_PHONE_TYPES.get(internal_type, "work")

        # Формат отображения
        formatted = norm.get("formatted_phone", original)
        normalized_digits = norm.get("normalized_phone", "")
        extension = norm.get("phone_extension", "")

        # Определяем, изменился ли номер
        changed = formatted != original
        # Также считаем изменением если тип отличается
        current_type = ""
        if phone_entry.get("type"):
            current_type = phone_entry.get("type", "").lower()

        results.append({
            "original": original,
            "normalized": normalized_digits,
            "formatted": formatted,
            "type": internal_type,
            "google_type": google_type,
            "extension": extension,
            "confidence": norm.get("confidence", 0),
            "changed": changed,
            "resource_tag": phone_entry.get("metadata", {}).get("primary", False),
        })

    return results


def generate_report(contacts: list, normalizer: PhoneNormalizer) -> str:
    """Генерация Markdown-отчёта по телефонам."""
    lines = []
    lines.append("# 📞 Отчёт о телефонах Google Contacts\n")
    lines.append(f"**Дата**: {time.strftime('%Y-%m-%d %H:%M')}\n")

    # Статистика
    total_contacts = len(contacts)
    with_phones = sum(1 for c in contacts if c.get("phoneNumbers"))
    total_phones = sum(len(c.get("phoneNumbers", [])) for c in contacts)

    # Нормализуем все
    all_results = []
    type_stats = {}
    changed_count = 0
    incomplete_count = 0
    extension_count = 0

    for contact in contacts:
        if not contact.get("phoneNumbers"):
            continue
        names = contact.get("names", [{}])
        display = names[0].get("displayName", "???") if names else "???"
        resource = contact.get("resourceName", "")

        phone_results = normalize_phones_for_contact(contact, normalizer)
        for pr in phone_results:
            pr["contact_name"] = display
            pr["resource_name"] = resource
            all_results.append(pr)

            t = pr["type"]
            type_stats[t] = type_stats.get(t, 0) + 1
            if pr["changed"]:
                changed_count += 1
            if pr["type"] == "incomplete":
                incomplete_count += 1
            if pr["extension"]:
                extension_count += 1

    lines.append(f"## Статистика\n")
    lines.append(f"| Метрика | Значение |")
    lines.append(f"|---------|----------|")
    lines.append(f"| Всего контактов | {total_contacts} |")
    lines.append(f"| С телефонами | {with_phones} |")
    lines.append(f"| Всего номеров | {total_phones} |")
    lines.append(f"| Требуют изменения | {changed_count} |")
    lines.append(f"| Неполные номера | {incomplete_count} |")
    lines.append(f"| С добавочным | {extension_count} |")
    lines.append("")

    lines.append("### По типам\n")
    lines.append("| Тип | Количество |")
    lines.append("|-----|-----------|")
    for t, cnt in sorted(type_stats.items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {cnt} |")
    lines.append("")

    # Таблица изменений (только изменённые)
    changed_results = [r for r in all_results if r["changed"]]
    if changed_results:
        lines.append(f"## Изменения ({len(changed_results)} номеров)\n")
        lines.append("| Контакт | Было | Стало | Тип | Доб. |")
        lines.append("|---------|------|-------|-----|------|")
        # Сортируем по имени контакта
        for r in sorted(changed_results, key=lambda x: x["contact_name"]):
            ext = r["extension"] or "—"
            lines.append(f"| {r['contact_name']} | {r['original']} | {r['formatted']} | {r['type']} | {ext} |")
        lines.append("")

    # Неполные номера
    incomplete_results = [r for r in all_results if r["type"] == "incomplete"]
    if incomplete_results:
        lines.append(f"## Неполные номера ({len(incomplete_results)}) ⚠️\n")
        lines.append("| Контакт | Номер | Причина |")
        lines.append("|---------|-------|---------|")
        for r in sorted(incomplete_results, key=lambda x: x["contact_name"]):
            reason = "мало цифр" if len(r["original"]) < 7 else "не распознан"
            lines.append(f"| {r['contact_name']} | {r['original']} | {reason} |")
        lines.append("")

    return "\n".join(lines)


def update_phones(service, contacts: list, normalizer: PhoneNormalizer, dedup_phones: bool = False):
    """Обновление телефонов в Google Contacts."""
    updated = 0
    errors = 0
    skipped = 0

    for i, contact in enumerate(contacts):
        if not contact.get("phoneNumbers"):
            continue

        names = contact.get("names", [{}])
        display = names[0].get("displayName", "???") if names else "???"
        resource = contact.get("resourceName", "")

        phone_results = normalize_phones_for_contact(contact, normalizer)

        # Есть ли что менять?
        has_changes = any(r["changed"] for r in phone_results)
        has_type_changes = False

        # Проверяем типы
        current_phones = contact.get("phoneNumbers", [])
        for j, pr in enumerate(phone_results):
            if j < len(current_phones):
                current_type = current_phones[j].get("type", "").lower()
                if current_type != pr["google_type"]:
                    has_type_changes = True

        if not has_changes and not has_type_changes and not dedup_phones:
            skipped += 1
            continue

        # Получаем свежий контакт
        try:
            fresh = api_call_with_retry(
                lambda: service.people().get(
                    resourceName=resource,
                    personFields="names,emailAddresses,phoneNumbers,organizations,metadata",
                )
            )
        except Exception as e:
            print(f"   ❌ {display}: get failed {e}")
            errors += 1
            continue

        etag = fresh.get("etag", "")
        existing_phones = fresh.get("phoneNumbers", [])

        # Строим обновлённый список телефонов
        new_phones = []
        seen_normalized = set()  # для дедупа

        for phone_entry in existing_phones:
            original = phone_entry.get("value", "")
            norm = normalizer.normalize_contact_phone(original)

            formatted = norm.get("formatted_phone", original)
            normalized_digits = norm.get("normalized_phone", "")
            internal_type = norm.get("phone_type", "неизвестно")
            google_type = GOOGLE_PHONE_TYPES.get(internal_type, "work")
            extension = norm.get("phone_extension", "")

            # Дедуп: пропускаем если нормализованный номер уже есть
            if dedup_phones and normalized_digits:
                if normalized_digits in seen_normalized:
                    print(f"      🗑️ Дубль телефона: {original} → {normalized_digits} (уже есть)")
                    continue
                seen_normalized.add(normalized_digits)

            phone_obj = {
                "value": formatted,
                "type": google_type,
            }

            # Сохраняем primary если был
            if phone_entry.get("metadata", {}).get("primary"):
                phone_obj["metadata"] = {"primary": True}

            # Добавочный в formatted (Google не имеет отдельного поля для extension)
            if extension:
                phone_obj["value"] = f"{formatted} доб.{extension}"

            new_phones.append(phone_obj)

        # Обновляем контакт
        body = {
            "etag": etag,
            "phoneNumbers": new_phones,
        }

        try:
            api_call_with_retry(
                lambda: service.people().updateContact(
                    resourceName=resource,
                    updatePersonFields="phoneNumbers",
                    body=body,
                )
            )
            updated += 1
            change_desc = []
            if has_changes:
                change_desc.append("формат")
            if has_type_changes:
                change_desc.append("тип")
            if dedup_phones:
                removed = len(existing_phones) - len(new_phones)
                if removed > 0:
                    change_desc.append(f"-{removed} дублей")
            print(f"   ✅ {display}: {', '.join(change_desc) or 'ok'}")
        except Exception as e:
            print(f"   ❌ {display}: {e}")
            errors += 1

        # Rate limit: Google API ~90 req/min, мы делаем ~1 req/s — в пределах лимита
        # Пауза 30с каждые 50 контактов для стабильности
        if (updated + errors) % 50 == 0 and (updated + errors) > 0:
            print(f"   ⏳ Пауза 30с... ({updated + errors} обработано)")
            time.sleep(30)
        else:
            time.sleep(0.5)

    return {"updated": updated, "errors": errors, "skipped": skipped}


def main():
    do_report = "--report" in sys.argv
    do_update = "--update" in sys.argv
    dedup_phones = "--dedup-phones" in sys.argv

    if not do_report and not do_update:
        print("Использование:")
        print("  python scripts/google_contacts_phone_normalize.py --report          # Отчёт")
        print("  python scripts/google_contacts_phone_normalize.py --update          # Обновить")
        print("  python scripts/google_contacts_phone_normalize.py --update --dedup-phones  # + дедуп")
        return

    print("📞 Инициализация PhoneNormalizer...")
    normalizer = PhoneNormalizer()

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    with_phones = sum(1 for c in contacts if c.get("phoneNumbers"))
    total_phones = sum(len(c.get("phoneNumbers", [])) for c in contacts)
    print(f"   С телефонами: {with_phones} контактов ({total_phones} номеров)")

    if do_report:
        print("📝 Генерация отчёта...")
        report = generate_report(contacts, normalizer)
        report_path = PROJECT_ROOT / "data" / "phone_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"   ✅ Отчёт: {report_path}")

    if do_update:
        print(f"\n📞 Обновление телефонов{' (+ дедуп)' if dedup_phones else ''}...")
        result = update_phones(service, contacts, normalizer, dedup_phones)
        print(f"\n✅ Результат: {result['updated']} обновлено, {result['errors']} ошибок, {result['skipped']} без изменений")


if __name__ == "__main__":
    main()
