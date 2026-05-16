#!/usr/bin/env python3
"""
🔧 Исправление дублей fn==gn в Google Contacts.

Проблема: предыдущий автофикс создал дубли — familyName скопирован в givenName.
Например: fn='Надежда', gn='Надежда', mn='Мергеноловна'
Правильно: fn='', gn='Надежда', mn='Мергеноловна'  (нет фамилии)
Или: fn='Селюнина', gn='Селюнина', mn='Юлия Васильевна'
Правильно: fn='Селюнина', gn='Юлия', mn='Васильевна'

Логика исправления:
1. Если fn==gn и mn содержит "Имя Отчество" → извлечь имя из mn, fn оставить
2. Если fn==gn и mn = отчество → gn='', fn оставить (нет фамилии, только имя+отчество)
3. Если fn==gn и mn содержит имя → извлечь имя из mn
4. Если fn==gn и нет mn → gn='' (организация или только имя)

Использование:
  python scripts/google_contacts_fix_fn_gn_dup.py --report
  python scripts/google_contacts_fix_fn_gn_dup.py --update
"""

import csv
import json
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "config" / "google_token.json"
CSV_FILE = PROJECT_ROOT / "data" / "contacts_export.csv"
SCOPES = ["https://www.googleapis.com/auth/contacts"]

PATRONYMIC_SUFFIXES = ("овна", "евна", "ична", "ишна", "ович", "евич", "ич", "оглы", "кызы")

RU_NAMES = {
    "александр", "александра", "алексей", "анатолий", "андрей", "анна", "антон",
    "артем", "артём", "арина", "алина", "алла", "адам", "афанасий",
    "борис", "богдан", "валентин", "валентина", "валерий", "валерия", "ваня",
    "василий", "василиса", "вера", "вероника", "вика", "виктор", "виктория",
    "виталий", "виталия", "влад", "владимир", "владислав", "влада", "вова",
    "вячеслав", "галина", "геннадий", "георгий", "глеб", "григорий",
    "данил", "данила", "дарья", "дима", "дмитрий", "евгений", "евгения",
    "екатерина", "елена", "елизавета", "илья", "инна", "игорь", "ира",
    "ирина", "клавдия", "карина", "кирилл", "кристина", "ксения", "костя",
    "константин", "лариса", "лена", "леонид", "лидия", "любовь", "людмила",
    "макар", "маргарита", "марина", "мария", "маша", "максим", "мила",
    "мирон", "михаил", "надежда", "наташа", "наталья", "нина", "никита",
    "николай", "оксана", "ольга", "оля", "осип", "павел", "петр", "пётр",
    "полина", "раиса", "ренат", "римма", "роман", "ростислав", "руслан",
    "савелий", "светлана", "сева", "семён", "сергей", "снежана",
    "станислав", "степан", "тамара", "таня", "татьяна", "тимур",
    "ульяна", "фаина", "федор", "фёдор", "эдуард", "эльвира", "юлия",
    "юрий", "яна", "ярослав",
}


def is_russian_name(word: str) -> bool:
    if not word:
        return False
    return word.lower().replace("ё", "е") in RU_NAMES


def is_patronymic(word: str) -> bool:
    if not word:
        return False
    return word.lower().replace("ё", "е").endswith(PATRONYMIC_SUFFIXES)


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


def compute_fn_gn_fix(fn: str, gn: str, mn: str, display: str) -> tuple:
    """
    Вычисляет исправление для fn==gn.
    Возвращает (new_fn, new_gn, new_mn, reason) или None если исправление не нужно.
    """
    if not fn or not gn:
        return None
    if fn.lower().replace("ё", "е") != gn.lower().replace("ё", "е"):
        return None

    # Случай 1: mn содержит "Имя Отчество" (2+ слова, первое — имя)
    if mn:
        mn_parts = mn.split()
        if len(mn_parts) >= 2:
            first = mn_parts[0]
            rest = " ".join(mn_parts[1:])
            if is_russian_name(first):
                # mn = "Юлия Васильевна", fn = "Селюнина"
                # Правильно: gn = "Юлия", mn = "Васильевна", fn = "Селюнина"
                new_mn = rest
                # Проверяем что rest — отчество
                if is_patronymic(rest):
                    return (fn, first, new_mn, f"gn='{gn}'→'{first}', mn='{mn}'→'{new_mn}'")
                else:
                    # rest не отчество — возможно "Васильевна Селюнина" 
                    # Проверяем последнее слово rest
                    rest_parts = rest.split()
                    if len(rest_parts) >= 2 and is_patronymic(rest_parts[0]):
                        # "Васильевна Селюнина" → mn="Васильевна", fn уже правильный
                        return (fn, first, rest_parts[0], f"gn='{gn}'→'{first}', mn='{mn}'→'{rest_parts[0]}'")
                    # Иначе — просто переносим имя в gn
                    return (fn, first, rest, f"gn='{gn}'→'{first}', mn='{mn}'→'{rest}'")

        # Случай 2: mn = отчество (одно слово)
        if is_patronymic(mn):
            # fn = "Надежда", gn = "Надежда", mn = "Мергеноловна"
            # Правильно: fn = "", gn = "Надежда", mn = "Мергеноловна"
            # Но если fn — это реальная фамилия (не имя), то оставляем fn
            if is_russian_name(fn):
                # fn — имя, не фамилия. Убираем дубликат
                return ("", gn, mn, f"fn='{fn}'→'', gn оставить (имя+отчество, нет фамилии)")
            else:
                # fn — фамилия (не имя). Значит gn неправильно = фамилии
                # Ищем имя в displayName
                if display:
                    d_parts = display.split()
                    for p in d_parts:
                        if is_russian_name(p) and p.lower().replace("ё","е") != fn.lower().replace("ё","е"):
                            return (fn, p, mn, f"gn='{gn}'→'{p}' (из displayName)")
                # Не нашли имя — очистить gn, но попробовать mn как имя
                # Это случай когда mn — отчество, но без имени
                return (fn, "", mn, f"gn='{gn}'→'' (фамилия дублируется, имя неизвестно)")

        # Случай 3: mn = имя (не отчество)
        if is_russian_name(mn) and not is_patronymic(mn):
            # fn = "Светлана", gn = "Светлана", mn = "Мунировна" — нет, это отчество
            # fn = "Виталя", gn = "Виталя", mn = "Карлинский" — фамилия в mn
            if not is_patronymic(mn):
                # Возможно фамилия в mn
                return (mn, "", "", f"fn='{fn}'→'{mn}', gn='{gn}'→'', mn='{mn}'→'' (фамилия в mn)")

    # Случай 4: нет mn
    if not mn:
        if is_russian_name(fn):
            # fn = "Надежда", gn = "Надежда" — просто имя без фамилии
            return ("", gn, "", f"fn='{fn}'→'' (имя без фамилии)")
        else:
            # fn = "Менеджер", gn = "Менеджер" — организация
            return (fn, "", "", f"gn='{gn}'→'' (организация/не имя)")

    return None


def main():
    do_report = "--report" in sys.argv
    do_update = "--update" in sys.argv

    if not do_report and not do_update:
        print("Использование:")
        print("  python scripts/google_contacts_fix_fn_gn_dup.py --report")
        print("  python scripts/google_contacts_fix_fn_gn_dup.py --update")
        return

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    fix_list = []
    for contact in contacts:
        names = contact.get("names", [{}])
        if not names:
            continue
        n = names[0]
        fn = (n.get("familyName") or "").strip()
        gn = (n.get("givenName") or "").strip()
        mn = (n.get("middleName") or "").strip()
        display = (n.get("displayName") or "").strip()

        result = compute_fn_gn_fix(fn, gn, mn, display)
        if result:
            new_fn, new_gn, new_mn, reason = result
            fix_list.append({
                "resource_name": contact.get("resourceName", ""),
                "display_name": display,
                "old_fn": fn, "old_gn": gn, "old_mn": mn,
                "new_fn": new_fn, "new_gn": new_gn, "new_mn": new_mn,
                "reason": reason,
            })

    print(f"\n📊 Найдено: {len(fix_list)} контактов с fn==gn")

    # Статистика по типам
    reasons = {}
    for f in fix_list:
        key = f["reason"].split("(")[-1].rstrip(")") if "(" in f["reason"] else f["reason"]
        reasons[key] = reasons.get(key, 0) + 1
    print("\nПо типам:")
    for t, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"   {t}: {cnt}")

    if do_report:
        # Сохраняем отчёт
        report_lines = [f"# 🔧 План исправления fn==gn\n\n**Контактов**: {len(fix_list)}\n"]
        report_lines.append("| # | Контакт | Было (Ф/И/О) | Станет (Ф/И/О) | Причина |")
        report_lines.append("|---|---------|--------------|-----------------|---------|")
        for i, f in enumerate(fix_list, 1):
            old = f"{f['old_fn']}/{f['old_gn']}/{f['old_mn']}"
            new = f"{f['new_fn']}/{f['new_gn']}/{f['new_mn']}"
            report_lines.append(f"| {i} | {f['display_name']} | {old} | {new} | {f['reason']} |")

        report_file = PROJECT_ROOT / "data" / "fix_fn_gn_dup_report.md"
        report_file.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\n✅ Отчёт: {report_file}")

        print("\nПервые 30:")
        for f in fix_list[:30]:
            old = f"{f['old_fn']}/{f['old_gn']}/{f['old_mn']}"
            new = f"{f['new_fn']}/{f['new_gn']}/{f['new_mn']}"
            print(f"   {f['display_name']}: {old} → {new} ({f['reason']})")
        return

    if do_update:
        updated = 0
        errors = 0
        for f in fix_list:
            resource = f["resource_name"]
            display = f["display_name"]

            try:
                fresh = api_call_with_retry(
                    lambda r=resource: service.people().get(
                        resourceName=r,
                        personFields="names,metadata",
                    )
                )
            except Exception as e:
                print(f"   ❌ {display}: get failed {e}")
                errors += 1
                continue

            etag = fresh.get("etag", "")
            existing_names = fresh.get("names", [{}])
            if not existing_names:
                errors += 1
                continue

            name_obj = existing_names[0].copy()
            name_obj["familyName"] = f["new_fn"]
            name_obj["givenName"] = f["new_gn"]
            name_obj["middleName"] = f["new_mn"]

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
                old = f"{f['old_fn']}/{f['old_gn']}/{f['old_mn']}"
                new = f"{f['new_fn']}/{f['new_gn']}/{f['new_mn']}"
                print(f"   ✅ {display}: {old} → {new}")
            except Exception as e:
                print(f"   ❌ {display}: {e}")
                errors += 1

            if (updated + errors) % 50 == 0 and (updated + errors) > 0:
                print(f"   ⏳ Пауза 30с... ({updated + errors} обработано)")
                time.sleep(30)
            else:
                time.sleep(0.5)

        print(f"\n✅ Результат: {updated} обновлено, {errors} ошибок")


if __name__ == "__main__":
    main()
