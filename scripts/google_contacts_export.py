#!/usr/bin/env python3
"""
📊 Экспорт Google Contacts в таблицу для анализа ФИО.

Использование:
  python scripts/google_contacts_export.py                    # Markdown таблица
  python scripts/google_contacts_export.py --csv               # CSV
  python scripts/google_contacts_export.py --only-problems      # Только с проблемами ФИО
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
SCOPES = ["https://www.googleapis.com/auth/contacts"]


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("people", "v1", credentials=creds)


def load_all_contacts(service):
    contacts = []
    page_token = None
    page = 0
    while True:
        page += 1
        try:
            r = service.people().connections().list(
                resourceName="people/me", pageSize=500, pageToken=page_token,
                personFields="names,emailAddresses,phoneNumbers,organizations,metadata",
                sources=["READ_SOURCE_TYPE_CONTACT"],
            ).execute()
        except HttpError as e:
            if e.status_code == 429:
                time.sleep(60)
                continue
            raise
        batch = r.get("connections", [])
        contacts.extend(batch)
        page_token = r.get("nextPageToken")
        if not page_token:
            break
        if page % 3 == 0:
            print(f"   Загружено {len(contacts)} контактов...")
    return contacts


PATRONYMIC_SUFFIXES = ("овна", "евна", "ична", "ишна", "ович", "евич", "ич", "оглы", "кызы")

ABBREVIATIONS = {
    "НИИ", "ФИЦ", "ФТМ", "ННИИ", "ПТД", "ПТО", "ЦГБ", "СКЛ", "ЦНМТ",
    "МТС", "ООО", "АО", "ЗАО", "ПАО", "ИП", "ГУ", "ФГУ", "ФГБУ",
    "РЖД", "МИД", "МВД", "ФСБ", "ФСО", "МЧС", "МО", "ЦАФАП", "ГИБДД",
    "СНИЛС", "ИНН", "ОГРН", "КПП", "БИК", "ОКАТО", "ОКВЭД",
    "НСК", "МСК", "СПБ", "КРД", "ЕКБ", "НН", "ТЮМ", "ОМСУ",
}

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
    lat_to_rus = str.maketrans("ABCEHKMOPTXacehkmoptxy", "АВСЕНКМОРТХасенкмортху")
    normalized = word.translate(lat_to_rus)
    if normalized.upper() in ABBREVIATIONS:
        return False
    has_russian = any('А' <= c <= 'я' or c in 'Ёё' for c in normalized)
    if not has_russian:
        return False
    return normalized == normalized.upper()


def is_russian_name(word: str) -> bool:
    if not word:
        return False
    return word.lower().replace("ё", "е") in RU_NAMES


def detect_name_problems(info: dict) -> tuple:
    """Определяет проблемы с ФИО контакта. Возвращает (problems, solutions)."""
    problems = []
    solutions = []
    fn = info["family_name"]
    gn = info["given_name"]
    mn = info["middle_name"]
    display = info["display_name"]

    # 1. Отчество в familyName
    if fn and fn.lower().endswith(PATRONYMIC_SUFFIXES):
        problems.append("отчество в фамилии")
        parts = display.split() if display else []
        real_fn = ""
        for p in parts:
            if p.lower() != fn.lower() and not p.lower().endswith(PATRONYMIC_SUFFIXES):
                real_fn = p
                break
        if real_fn:
            solutions.append(f"fn='{real_fn}', mn='{fn}'")
        else:
            solutions.append(f"mn='{fn}', fn из displayName")

    # 2. Отчество в givenName
    if gn and gn.lower().endswith(PATRONYMIC_SUFFIXES):
        problems.append("отчество в имени")
        parts = display.split() if display else []
        real_gn = ""
        for p in parts:
            if p.lower() != gn.lower() and not p.lower().endswith(PATRONYMIC_SUFFIXES):
                real_gn = p
        if real_gn:
            solutions.append(f"gn='{real_gn}', mn='{gn}'")
        else:
            solutions.append(f"mn='{gn}', gn из displayName")

    # 3. Пустая фамилия (есть только имя)
    if not fn and gn:
        if gn.lower().endswith(PATRONYMIC_SUFFIXES):
            problems.append("пустая фамилия + отчество в имени")
            solutions.append(f"переставить: gn→mn, извлечь fn из displayName")
        else:
            problems.append("пустая фамилия")
            parts = display.split() if display else []
            if len(parts) >= 2:
                solutions.append(f"fn='{parts[-1]}' (из displayName)")
            else:
                solutions.append("нет данных для фамилии")

    # 4. Пустое имя — часто в familyName записано "Фамилия Имя" вместе
    if fn and not gn:
        # Проверяем: может быть в fn записано "Имя Фамилия" или "Фамилия Имя"
        fn_parts = fn.split()
        if len(fn_parts) >= 2:
            # В familyName два+ слова — нужно разделить
            problems.append("пустое имя (fn содержит Имя+Фамилию)")
            # Определяем что есть что: последнее слово = фамилия, первое = имя
            # Но может быть и наоборот — смотрим на displayName
            if display:
                d_parts = display.split()
                if len(d_parts) >= 2:
                    # Если первое слово displayName = первое слово fn, то fn = "Имя Фамилия"
                    if d_parts[0].lower() == fn_parts[0].lower().replace("ё", "е"):
                        solutions.append(f"fn='{fn_parts[-1]}', gn='{fn_parts[0]}'")
                    else:
                        solutions.append(f"fn='{fn_parts[0]}', gn='{' '.join(fn_parts[1:])}'")
                else:
                    solutions.append(f"fn='{fn_parts[-1]}', gn='{' '.join(fn_parts[:-1])}'")
            else:
                solutions.append(f"разделить fn: fn='{fn_parts[-1]}', gn='{' '.join(fn_parts[:-1])}'")
        elif fn.lower().endswith(PATRONYMIC_SUFFIXES):
            problems.append("пустое имя")
            solutions.append("похоже на отчество — нужна ручная проверка")
        else:
            problems.append("пустое имя")
            solutions.append("возможно организация (не контакт)")

    # 5. Перепутаны familyName/givenName — по словарю имён
    if fn and gn and not mn and "перепутаны" not in str(problems):
        fn_is_name = is_russian_name(fn)
        gn_is_name = is_russian_name(gn)
        if fn_is_name and not gn_is_name:
            problems.append("перепутаны Фамилия/Имя")
            solutions.append(f"поменять: fn='{gn}', gn='{fn}'")
        elif fn_is_name and gn_is_name:
            # Оба — имена, смотрим displayName
            if display:
                d_norm = display.lower().replace("ё", "е").strip()
                gn_fn = f"{gn} {fn}".lower().replace("ё", "е")
                fn_gn = f"{fn} {gn}".lower().replace("ё", "е")
                if d_norm == gn_fn and d_norm != fn_gn:
                    problems.append("перепутаны Фамилия/Имя")
                    solutions.append(f"поменять: fn='{gn}', gn='{fn}'")
        elif not fn_is_name and not gn_is_name:
            # Ни то ни другое — не имя. Проверяем по displayName
            if display:
                d_norm = display.lower().replace("ё", "е").strip()
                gn_fn = f"{gn} {fn}".lower().replace("ё", "е")
                fn_gn = f"{fn} {gn}".lower().replace("ё", "е")
                if d_norm == gn_fn and d_norm != fn_gn:
                    problems.append("перепутаны Фамилия/Имя")
                    solutions.append(f"поменять: fn='{gn}', gn='{fn}'")

    # 5b. middleName = имя (не отчество) → перенести в givenName
    if mn and not mn.lower().endswith(PATRONYMIC_SUFFIXES) and is_russian_name(mn):
        if not gn:
            problems.append("имя в отчестве")
            solutions.append(f"mn→gn: gn='{mn}', mn=''")
        elif not is_russian_name(gn) and is_russian_name(mn):
            problems.append("имя/фамилия перепутаны в gn/mn")
            solutions.append(f"поменять: gn='{mn}', mn='{gn}'")

    # 7. Полный КАПС в ФИО
    caps_fields = []
    caps_fixes = []
    if is_full_caps(fn):
        caps_fields.append(f"фамилия='{fn}'")
        caps_fixes.append(f"fn='{fn.capitalize()}'")
    if is_full_caps(gn):
        caps_fields.append(f"имя='{gn}'")
        caps_fixes.append(f"gn='{gn.capitalize()}'")
    if is_full_caps(mn):
        caps_fields.append(f"отчество='{mn}'")
        caps_fixes.append(f"mn='{mn.capitalize()}'")
    if caps_fields:
        problems.append("КАПС в ФИО")
        solutions.append(f"капс: {', '.join(caps_fields)} → {', '.join(caps_fixes)}")

    # 6. displayName не совпадает с Ф+И+О
    constructed = f"{fn} {gn} {mn}".strip() if fn or gn or mn else ""
    if display and constructed and display.lower().replace("ё", "е") != constructed.lower().replace("ё", "е"):
        alt = f"{gn} {fn} {mn}".strip()
        if display.lower().replace("ё", "е") != alt.lower().replace("ё", "е"):
            # Не добавляем дублирующую проблему если уже есть "перепутаны"
            if "перепутаны Фамилия/Имя" not in problems:
                problems.append("displayName ≠ ФИО")
                display_parts = display.split()
                fio_parts = [p for p in [fn, gn, mn] if p]
                if len(display_parts) > len(fio_parts):
                    extra = [p for p in display_parts if p not in fio_parts]
                    solutions.append(f"лишнее в displayName: {' '.join(extra)}")
                else:
                    solutions.append("порядок слов отличается")

    return problems, solutions


def extract_contact_info(contact: dict) -> dict:
    names = contact.get("names", [{}])
    n = names[0] if names else {}
    emails = [e.get("value", "") for e in contact.get("emailAddresses", [])]
    phones = [p.get("value", "") for p in contact.get("phoneNumbers", [])]
    orgs = [o.get("name", "") for o in contact.get("organizations", []) if o.get("name")]

    info = {
        "resource_name": contact.get("resourceName", ""),
        "display_name": n.get("displayName", ""),
        "family_name": n.get("familyName", "") or "",
        "given_name": n.get("givenName", "") or "",
        "middle_name": n.get("middleName", "") or "",
        "emails": emails,
        "phones": phones,
        "orgs": orgs,
    }
    info["problems"], info["solutions"] = detect_name_problems(info)
    return info


def export_markdown(contacts_info: list, only_problems: bool = False) -> str:
    lines = []
    lines.append("# 📊 Google Contacts — Анализ ФИО\n")
    lines.append(f"**Дата**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Всего контактов**: {len(contacts_info)}\n")

    # Статистика проблем
    problem_counts = {}
    for c in contacts_info:
        for p in c["problems"]:
            problem_counts[p] = problem_counts.get(p, 0) + 1

    if problem_counts:
        lines.append("## Статистика проблем\n")
        lines.append("| Проблема | Количество |")
        lines.append("|----------|-----------|")
        for p, cnt in sorted(problem_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {p} | {cnt} |")
        lines.append("")

    # Фильтр
    if only_problems:
        contacts_info = [c for c in contacts_info if c["problems"]]
        lines.append(f"## Контакты с проблемами ({len(contacts_info)})\n")
    else:
        lines.append(f"## Все контакты\n")

    # Таблица
    lines.append("| # | displayName | Фамилия | Имя | Отчество | Проблема | Решение | Email | Телефон | Org |")
    lines.append("|---|-------------|---------|-----|----------|----------|---------|-------|---------|-----|")

    for i, c in enumerate(contacts_info, 1):
        fn = c["family_name"] or "—"
        gn = c["given_name"] or "—"
        mn = c["middle_name"] or "—"
        problem = ", ".join(c["problems"]) or "✅"
        solution = "; ".join(c["solutions"]) or "—"
        email_str = ", ".join(c["emails"][:2]) or "—"
        if len(c["emails"]) > 2:
            email_str += f" +{len(c['emails'])-2}"
        phone_str = ", ".join(c["phones"][:2]) or "—"
        if len(c["phones"]) > 2:
            phone_str += f" +{len(c['phones'])-2}"
        org_str = ", ".join(c["orgs"][:1]) or "—"

        # Экранируем
        for ch in ("|", "\n"):
            fn = fn.replace(ch, " ")
            gn = gn.replace(ch, " ")
            mn = mn.replace(ch, " ")
            solution = solution.replace(ch, " ")
            email_str = email_str.replace(ch, " ")
            phone_str = phone_str.replace(ch, " ")
            org_str = org_str.replace(ch, " ")
            display = c["display_name"].replace(ch, " ")

        lines.append(f"| {i} | {display} | {fn} | {gn} | {mn} | {problem} | {solution} | {email_str} | {phone_str} | {org_str} |")

    return "\n".join(lines)


def export_csv(contacts_info: list, only_problems: bool, path: Path):
    rows = []
    for c in contacts_info:
        if only_problems and not c["problems"]:
            continue
        rows.append({
            "displayName": c["display_name"],
            "familyName": c["family_name"],
            "givenName": c["given_name"],
            "middleName": c["middle_name"],
            "problems": "; ".join(c["problems"]) or "ok",
            "solutions": "; ".join(c["solutions"]) or "",
            "emails": "; ".join(c["emails"]),
            "phones": "; ".join(c["phones"]),
            "organizations": "; ".join(c["orgs"]),
            "resourceName": c["resource_name"],
        })

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["displayName", "familyName", "givenName", "middleName", "problems", "solutions", "emails", "phones", "organizations", "resourceName"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"   ✅ CSV: {path} ({len(rows)} строк)")


def main():
    do_csv = "--csv" in sys.argv
    only_problems = "--only-problems" in sys.argv

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    print("📊 Анализ ФИО...")
    contacts_info = [extract_contact_info(c) for c in contacts]

    with_problems = sum(1 for c in contacts_info if c["problems"])
    print(f"   С проблемами: {with_problems}")

    if do_csv:
        path = PROJECT_ROOT / "data" / "contacts_export.csv"
        export_csv(contacts_info, only_problems, path)
    else:
        report = export_markdown(contacts_info, only_problems)
        suffix = "_problems" if only_problems else ""
        path = PROJECT_ROOT / "data" / f"contacts_export{suffix}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"   ✅ Markdown: {path}")

    # Также всегда сохраняем JSON
    json_path = PROJECT_ROOT / "data" / "contacts_info.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(contacts_info, f, ensure_ascii=False, indent=2)
    print(f"   ✅ JSON: {json_path}")


if __name__ == "__main__":
    main()
