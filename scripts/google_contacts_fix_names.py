#!/usr/bin/env python3
"""
🔧 Автофикс ФИО в Google Contacts.

Исправляет:
- перепутаны Фамилия/Имя → swap fn↔gn
- КАПС в ФИО → capitalize()
- отчество в фамилии → перенести в mn
- отчество в имени → перенести в mn
- пустое имя (fn содержит Имя+Фамилию) → разделить fn

НЕ трогает:
- пустая фамилия (нет данных)
- displayName ≠ ФИО (не критично)

Использование:
  python scripts/google_contacts_fix_names.py --report     # Отчёт что будет исправлено
  python scripts/google_contacts_fix_names.py --update     # Применить исправления
  python scripts/google_contacts_fix_names.py --update --skip=N  # Пропустить N контактов
"""

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
SCOPES = ["https://www.googleapis.com/auth/contacts"]

PATRONYMIC_SUFFIXES = ("овна", "евна", "ична", "ишна", "ович", "евич", "ич", "оглы", "кызы")

ABBREVIATIONS = {
    "НИИ", "ФИЦ", "ФТМ", "ННИИ", "ПТД", "ПТО", "ЦГБ", "СКЛ", "ЦНМТ",
    "МТС", "ООО", "АО", "ЗАО", "ПАО", "ИП", "ГУ", "ФГУ", "ФГБУ",
    "РЖД", "МИД", "МВД", "ФСБ", "ФСО", "МЧС", "МО", "ЦАФАП", "ГИБДД",
    "СНИЛС", "ИНН", "ОГРН", "КПП", "БИК", "ОКАТО", "ОКВЭД",
    "НСК", "МСК", "СПБ", "КРД", "ЕКБ", "НН", "ТЮМ", "ОМСУ",
}

# Словарь русских имён — для детекции перепутанных Фамилия/Имя
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


def is_full_caps(word: str) -> bool:
    """Проверяет КАПС, включая смешанную раскладку (латинская A + русские)."""
    if not word or len(word) <= 2:
        return False
    # Нормализуем латиницу в кириллицу для проверки
    lat_to_rus = str.maketrans("ABCEHKMOPTXacehkmoptxy", "АВСЕНКМОРТХасенкмортху")
    normalized = word.translate(lat_to_rus)
    if normalized.upper() in ABBREVIATIONS:
        return False
    has_russian = any('А' <= c <= 'я' or c in 'Ёё' for c in normalized)
    if not has_russian:
        return False
    return normalized == normalized.upper()


def is_russian_name(word: str) -> bool:
    """Проверяет, похож ли слово на русское имя."""
    if not word:
        return False
    return word.lower().replace("ё", "е") in RU_NAMES


def fix_mixed_layout(word: str) -> tuple:
    """
    Исправляет смешанную раскладку (латинские буквы в русском слове).
    Применяется ТОЛЬКО если слово преимущественно русское (большинство букв — кириллица)
    и содержит единичные латинские буквы, которые выглядят как кириллица.
    Возвращает (fixed_word, was_fixed: bool).
    """
    if not word:
        return word, False
    # Латинские буквы, которые визуально совпадают с кириллицей
    mappable = set("ABCEHKMOPTXYabcehkmoptxy")
    # Считаем буквы
    russian_count = sum(1 for c in word if 'а' <= c <= 'я' or 'А' <= c <= 'Я' or c in 'Ёё')
    latin_mappable_count = sum(1 for c in word if c in mappable)
    latin_other_count = sum(1 for c in word if 'a' <= c <= 'z' or 'A' <= c <= 'Z') - latin_mappable_count
    
    # Применяем только если: русских букв много, а немаппящихся латинских мало
    if latin_mappable_count > 0 and russian_count > latin_other_count and russian_count >= 2:
        lat_to_rus = str.maketrans("ABCEHKMOPTXYabcehkmoptxy", "АВСЕНКМОРТХУавсенкмортху")
        fixed = word.translate(lat_to_rus).capitalize()
        return fixed, True
    return word, False


def compute_fixes(fn: str, gn: str, mn: str, display: str) -> tuple:
    """Вычисляет исправления. Возвращает (new_fn, new_gn, new_mn, fixes_applied)."""
    new_fn, new_gn, new_mn = fn, gn, mn
    fixes = []

    # 0. Исправить mixed layout (латиница в русском слове)
    for field_name, field_val in [("fn", new_fn), ("gn", new_gn), ("mn", new_mn)]:
        if field_val:
            fixed, was_fixed = fix_mixed_layout(field_val)
            if was_fixed:
                fixes.append(f"mixed layout {field_name}: '{field_val}'→'{fixed}'")
                if field_name == "fn":
                    new_fn = fixed
                elif field_name == "gn":
                    new_gn = fixed
                else:
                    new_mn = fixed

    # 1. Отчество в familyName
    if new_fn and new_fn.lower().endswith(PATRONYMIC_SUFFIXES):
        old_fn = new_fn
        # Извлечь настоящую фамилию из displayName
        parts = display.split() if display else []
        real_fn = ""
        for p in parts:
            if p.lower() != new_fn.lower() and not p.lower().endswith(PATRONYMIC_SUFFIXES):
                real_fn = p
                break
        if real_fn:
            new_mn = new_fn
            new_fn = real_fn
            fixes.append(f"отчество в фамилии: fn='{old_fn}'→'{new_fn}', mn='{new_mn}'")
        else:
            # Не нашли фамилию — просто переносим в mn, fn оставляем пустым
            new_mn = new_fn
            new_fn = ""
            fixes.append(f"отчество в фамилии: fn='{old_fn}'→'', mn='{new_mn}'")

    # 2. Отчество в givenName
    if new_gn and new_gn.lower().endswith(PATRONYMIC_SUFFIXES):
        old_gn = new_gn
        parts = display.split() if display else []
        real_gn = ""
        for p in parts:
            if p.lower() != new_gn.lower() and not p.lower().endswith(PATRONYMIC_SUFFIXES):
                real_gn = p
        if real_gn:
            new_mn = new_gn
            new_gn = real_gn
            fixes.append(f"отчество в имени: gn='{old_gn}'→'{new_gn}', mn='{new_mn}'")
        else:
            new_mn = new_gn
            new_gn = ""
            fixes.append(f"отчество в имени: gn='{old_gn}'→'', mn='{new_mn}'")

    # 3. Пустое имя — fn содержит "Имя Фамилия" или "Фамилия Имя"
    if new_fn and not new_gn:
        fn_parts = new_fn.split()
        if len(fn_parts) >= 2:
            if display:
                d_parts = display.split()
                if len(d_parts) >= 2:
                    if d_parts[0].lower().replace("ё", "е") == fn_parts[0].lower().replace("ё", "е"):
                        # displayName = "Имя ..." → fn начинается с имени
                        new_fn = fn_parts[-1]
                        new_gn = fn_parts[0]
                    else:
                        # displayName = "Фамилия ..." → fn начинается с фамилии
                        new_fn = fn_parts[0]
                        new_gn = " ".join(fn_parts[1:])
                else:
                    new_fn = fn_parts[-1]
                    new_gn = " ".join(fn_parts[:-1])
            else:
                new_fn = fn_parts[-1]
                new_gn = " ".join(fn_parts[:-1])
            fixes.append(f"пустое имя: fn='{' '.join(fn_parts)}'→fn='{new_fn}', gn='{new_gn}'")

    # 4. Перепутаны Фамилия/Имя — по словарю имён
    # Если familyName — это имя, а givenName — не имя → перепутаны
    if new_fn and new_gn and not new_mn and "перепутаны" not in str(fixes):
        fn_is_name = is_russian_name(new_fn)
        gn_is_name = is_russian_name(new_gn)
        if fn_is_name and not gn_is_name:
            # familyName = имя, givenName = фамилия → перепутаны
            old_fn, old_gn = new_fn, new_gn
            new_fn, new_gn = new_gn, new_fn
            fixes.append(f"перепутаны по словарю: fn='{old_fn}'→'{new_fn}', gn='{old_gn}'→'{new_gn}'")
        elif fn_is_name and gn_is_name:
            # Оба — имена. Смотрим на displayName: если "gn fn" — значит gn=фамилия
            if display:
                d_norm = display.lower().replace("ё", "е").strip()
                gn_fn = f"{new_gn} {new_fn}".lower().replace("ё", "е")
                fn_gn = f"{new_fn} {new_gn}".lower().replace("ё", "е")
                if d_norm == gn_fn and d_norm != fn_gn:
                    old_fn, old_gn = new_fn, new_gn
                    new_fn, new_gn = new_gn, new_fn
                    fixes.append(f"перепутаны по displayName: fn='{old_fn}'→'{new_fn}', gn='{old_gn}'→'{new_gn}'")

    # 5. middleName = имя (не отчество) → перенести в givenName
    if new_mn and not new_mn.lower().endswith(PATRONYMIC_SUFFIXES) and is_russian_name(new_mn):
        if not new_gn:
            # givenName пустое → mn становится gn
            old_mn = new_mn
            new_gn = new_mn
            new_mn = ""
            fixes.append(f"имя в отчестве: mn='{old_mn}'→gn='{new_gn}'")
        else:
            # givenName занято — возможно mn+gn перепутаны
            if is_russian_name(new_gn) and not is_russian_name(new_mn):
                # gn=имя, mn=не имя — ОК
                pass
            elif not is_russian_name(new_gn) and is_russian_name(new_mn):
                # gn=фамилия(?), mn=имя → swap gn↔mn
                old_gn, old_mn = new_gn, new_mn
                new_gn, new_mn = new_mn, new_gn
                fixes.append(f"имя/фам в gn/mn: gn='{old_gn}'→'{new_gn}', mn='{old_mn}'→'{new_mn}'")

    # 6. КАПС в ФИО → capitalize
    caps_fixes = []
    if is_full_caps(new_fn):
        new_fn = new_fn.capitalize()
        caps_fixes.append(f"fn→'{new_fn}'")
    if is_full_caps(new_gn):
        new_gn = new_gn.capitalize()
        caps_fixes.append(f"gn→'{new_gn}'")
    if is_full_caps(new_mn):
        new_mn = new_mn.capitalize()
        caps_fixes.append(f"mn→'{new_mn}'")
    if caps_fixes:
        fixes.append(f"КАПС: {', '.join(caps_fixes)}")

    return new_fn, new_gn, new_mn, fixes


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


def main():
    do_report = "--report" in sys.argv
    do_update = "--update" in sys.argv

    if not do_report and not do_update:
        print("Использование:")
        print("  python scripts/google_contacts_fix_names.py --report     # Отчёт")
        print("  python scripts/google_contacts_fix_names.py --update     # Применить")
        print("  python scripts/google_contacts_fix_names.py --update --skip=N  # Resume")
        return

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    # Собираем исправления
    fix_list = []
    for contact in contacts:
        names = contact.get("names", [{}])
        n = names[0] if names else {}
        fn = n.get("familyName", "") or ""
        gn = n.get("givenName", "") or ""
        mn = n.get("middleName", "") or ""
        display = n.get("displayName", "") or ""
        resource = contact.get("resourceName", "")

        new_fn, new_gn, new_mn, fixes = compute_fixes(fn, gn, mn, display)

        if fixes:
            fix_list.append({
                "resource_name": resource,
                "display_name": display,
                "old_fn": fn, "old_gn": gn, "old_mn": mn,
                "new_fn": new_fn, "new_gn": new_gn, "new_mn": new_mn,
                "fixes": fixes,
            })

    print(f"\n📊 Найдено исправлений: {len(fix_list)} контактов")

    # Статистика по типам
    fix_types = {}
    for f in fix_list:
        for fix in f["fixes"]:
            t = fix.split(":")[0]
            fix_types[t] = fix_types.get(t, 0) + 1

    print("\nПо типам:")
    for t, cnt in sorted(fix_types.items(), key=lambda x: -x[1]):
        print(f"   {t}: {cnt}")

    if do_report:
        # Генерируем отчёт
        lines = []
        lines.append("# 🔧 План автофикса ФИО\n")
        lines.append(f"**Дата**: {time.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Контактов к исправлению**: {len(fix_list)}\n")

        lines.append("## Статистика\n")
        lines.append("| Тип исправления | Количество |")
        lines.append("|----------------|-----------|")
        for t, cnt in sorted(fix_types.items(), key=lambda x: -x[1]):
            lines.append(f"| {t} | {cnt} |")
        lines.append("")

        lines.append("## Детали\n")
        lines.append("| # | Контакт | Было (Ф/И/О) | Станет (Ф/И/О) | Исправление |")
        lines.append("|---|---------|--------------|-----------------|------------|")

        for i, f in enumerate(fix_list, 1):
            old = f"{f['old_fn']}/{f['old_gn']}/{f['old_mn']}"
            new = f"{f['new_fn']}/{f['new_gn']}/{f['new_mn']}"
            fix_str = "; ".join(f["fixes"]).replace("|", " ")
            display = f["display_name"].replace("|", " ")
            lines.append(f"| {i} | {display} | {old} | {new} | {fix_str} |")

        report_path = PROJECT_ROOT / "data" / "fix_names_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n✅ Отчёт: {report_path}")

        # Также JSON
        json_path = PROJECT_ROOT / "data" / "fix_names_plan.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(fix_list, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON: {json_path}")

    if do_update:
        # Skip для resume
        skip_n = 0
        for arg in sys.argv:
            if arg.startswith("--skip="):
                skip_n = int(arg.split("=")[1])
        if skip_n > 0:
            print(f"   Пропускаем первые {skip_n} (resume)")

        updated = 0
        errors = 0
        skipped = 0

        for i, f in enumerate(fix_list):
            if i < skip_n:
                skipped += 1
                continue

            resource = f["resource_name"]
            display = f["display_name"]

            # Получаем свежий контакт
            try:
                fresh = api_call_with_retry(
                    lambda r=resource: service.people().get(
                        resourceName=r,
                        personFields="names,emailAddresses,phoneNumbers,organizations,metadata",
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

            # Обновляем имена
            name_obj = existing_names[0].copy()
            name_obj["familyName"] = f["new_fn"]
            name_obj["givenName"] = f["new_gn"]
            name_obj["middleName"] = f["new_mn"]
            # displayName пересчитается Google автоматически

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
                fix_str = ", ".join(f["fixes"])
                print(f"   ✅ {display}: {fix_str}")
            except Exception as e:
                print(f"   ❌ {display}: {e}")
                errors += 1

            # Rate limit
            if (updated + errors) % 50 == 0 and (updated + errors) > 0:
                print(f"   ⏳ Пауза 30с... ({updated + errors} обработано)")
                time.sleep(30)
            else:
                time.sleep(0.5)

        print(f"\n✅ Результат: {updated} обновлено, {errors} ошибок, {skipped} пропущено")


if __name__ == "__main__":
    main()
