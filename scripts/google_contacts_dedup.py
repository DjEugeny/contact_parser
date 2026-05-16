#!/usr/bin/env python3
"""
🧹 Дедупликация Google Contacts: отчёт + объединение.

Использование:
  python scripts/google_contacts_dedup.py --report     # Генерация отчёта
  python scripts/google_contacts_dedup.py --merge      # Объединение дублей
"""

import json
import sys
import time
from collections import defaultdict
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


def load_senders():
    with open(PROJECT_ROOT / "data" / "senders_cache.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["email"].lower().strip(): s for s in data.get("senders", []) if s.get("email")}


def load_all_contacts(service):
    """Загрузка всех контактов с прогрессом."""
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
                print(f"   ⏳ Rate limit, пауза 60с...")
                time.sleep(60)
                continue
            raise

        batch = r.get("connections", [])
        contacts.extend(batch)
        page_token = r.get("nextPageToken")
        total = r.get("totalItems", "?")
        if not page_token:
            break
        if page % 3 == 0:
            print(f"   Загружено {len(contacts)} контактов...")
    return contacts


def normalize_family(name: str) -> str:
    """Нормализация фамилии для группировки."""
    return name.lower().strip().replace("ё", "е")


def data_score(contact: dict) -> int:
    """Оценка «полноты» контакта (больше = лучше кандидат в мастер)."""
    score = 0
    emails = contact.get("emailAddresses", [])
    phones = contact.get("phoneNumbers", [])
    orgs = contact.get("organizations", [])
    names = contact.get("names", [])

    score += len(emails) * 3
    score += len(phones) * 2
    score += len(orgs) * 2

    if names:
        n = names[0]
        if n.get("familyName"):
            score += 1
        if n.get("givenName"):
            score += 1
        if n.get("middleName"):
            score += 1

    return score


def extract_contact_info(contact: dict) -> dict:
    """Извлечение ключевой информации из контакта."""
    names = contact.get("names", [{}])
    n = names[0] if names else {}
    emails = [e.get("value", "") for e in contact.get("emailAddresses", [])]
    phones = [p.get("value", "") for p in contact.get("phoneNumbers", [])]
    orgs = [o.get("name", "") for o in contact.get("organizations", []) if o.get("name")]

    return {
        "resource_name": contact.get("resourceName", ""),
        "display_name": n.get("displayName", ""),
        "family_name": n.get("familyName", ""),
        "given_name": n.get("givenName", ""),
        "middle_name": n.get("middleName", ""),
        "emails": emails,
        "phones": phones,
        "orgs": orgs,
        "score": data_score(contact),
    }


def group_by_family(contacts: list) -> dict:
    """Группировка контактов по фамилии+имени (точнее, чем только фамилия)."""
    groups = defaultdict(list)
    for c in contacts:
        info = extract_contact_info(c)
        fn = info["family_name"] or ""
        gn = info["given_name"] or ""

        # Если есть и фамилия и имя — ключ по обоим
        if fn and gn:
            key = normalize_family(fn) + " " + normalize_family(gn)
        elif fn:
            # Только фамилия — группируем по ней (будет больше дублей)
            key = normalize_family(fn)
        elif info["display_name"]:
            # Попробуем извлечь из displayName
            parts = info["display_name"].split()
            if len(parts) >= 2:
                key = normalize_family(parts[-1]) + " " + normalize_family(parts[0])
            elif len(parts) == 1:
                key = normalize_family(parts[0])
            else:
                continue
        else:
            continue

        if key and len(key) >= 3:
            groups[key].append(info)
    return groups


def is_empty(info: dict) -> bool:
    """Контакт считается «пустым» если нет email, телефона и организации."""
    return not info["emails"] and not info["phones"] and not info["orgs"]


def recommend(group: list) -> str:
    """Рекомендация для группы дублей."""
    if len(group) == 2:
        a, b = group[0], group[1]
        # Если один пустой (нет email, телефона, org) → удалить
        if is_empty(a) and not is_empty(b):
            return f"Удалить «{a['display_name']}» (пустой), оставить «{b['display_name']}»"
        if is_empty(b) and not is_empty(a):
            return f"Удалить «{b['display_name']}» (пустой), оставить «{a['display_name']}»"

        # Если один — мастер (больше данных), другой — слейв
        if a["score"] >= b["score"]:
            master, slave = a, b
        else:
            master, slave = b, a

        # Проверяем: есть ли у слейва уникальные данные
        slave_unique_emails = set(slave["emails"]) - set(master["emails"])
        slave_unique_phones = set(slave["phones"]) - set(master["phones"])

        if slave_unique_emails or slave_unique_phones:
            return f"Объединить в «{master['display_name']}» (перенести {len(slave_unique_emails)} email, {len(slave_unique_phones)} тел. из «{slave['display_name']}»)"
        else:
            return f"Удалить «{slave['display_name']}» (все данные есть в «{master['display_name']}»)"

    # 3+ дублей
    master = max(group, key=lambda x: x["score"])
    others = [g for g in group if g != master]
    empty_others = sum(1 for o in others if is_empty(o))
    if empty_others == len(others):
        return f"Удалить {empty_others} пустых дублей, оставить «{master['display_name']}»"
    return f"Объединить все в «{master['display_name']}» ({len(others)} дублей слить)"


def generate_report(groups: dict, senders: dict) -> str:
    """Генерация Markdown-отчёта."""
    lines = []
    lines.append("# 📋 Отчёт о дублях Google Contacts\n")
    lines.append(f"**Дата**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Групп дублей**: {len(groups)}\n")

    # Статистика
    total_dupes = sum(len(g) for g in groups.values())
    empty_count = sum(1 for g in groups.values() for c in g if c["score"] == 0)
    lines.append(f"**Всего контактов в группах**: {total_dupes}")
    lines.append(f"**Пустых дублей (score=0)**: {empty_count}\n")

    # Легенда
    lines.append("## Легенда")
    lines.append("| Поле | Значение |")
    lines.append("|------|----------|")
    lines.append("| Score | Полнота контакта (email×3 + тел×2 + org×2 + ФИО×3) |")
    lines.append("| Рекомендация | auto = можно объединить автоматически, manual = нужна проверка |")
    lines.append("")

    # Сортировка: сначала группы с пустыми дублями (легче чистить)
    sorted_groups = sorted(groups.items(), key=lambda x: (
        0 if any(is_empty(c) for c in x[1]) else 1,
        -max(c["score"] for c in x[1]),
        x[0],
    ))

    # Таблица дублей
    lines.append("## Группы дублей\n")

    for family_key, group in sorted_groups:
        # Заголовок группы
        display_family = max(group, key=lambda x: len(x["display_name"]))["display_name"].split()[0]
        if not display_family:
            display_family = family_key.capitalize()
        lines.append(f"### {display_family} ({len(group)} контактов)\n")

        # Таблица
        lines.append("| # | displayName | ФИО (ф/и/о) | Email | Телефон | Org | Score | Рекомендация |")
        lines.append("|---|-------------|-------------|-------|---------|-----|-------|-------------|")

        rec = recommend(group)
        for i, c in enumerate(group, 1):
            fio = f"{c['family_name']} {c['given_name']} {c['middle_name']}".strip() or "—"
            email_str = ", ".join(c["emails"]) or "—"
            phone_str = ", ".join(c["phones"]) or "—"
            org_str = ", ".join(c["orgs"]) or "—"
            # Экранируем
            for ch in ("|", "\n"):
                fio = fio.replace(ch, " ")
                email_str = email_str.replace(ch, " ")
                phone_str = phone_str.replace(ch, " ")
                org_str = org_str.replace(ch, " ")
                display = c["display_name"].replace(ch, " ")
            lines.append(f"| {i} | {display} | {fio} | {email_str} | {phone_str} | {org_str} | {c['score']} | {rec if i == 1 else ''} |")

        lines.append("")

    return "\n".join(lines)


def merge_group(service, group: list, senders: dict) -> dict:
    """Объединение одной группы дублей. Возвращает результат."""
    # Мастер = контакт с наивысшим score
    master = max(group, key=lambda x: x["score"])
    slaves = [g for g in group if g != master]

    if not slaves:
        return {"status": "skip", "reason": "no slaves"}

    # Собираем уникальные данные слейвов
    new_emails = []
    new_phones = []
    for slave in slaves:
        for e in slave["emails"]:
            if e not in master["emails"] and e not in new_emails:
                new_emails.append(e)
        for p in slave["phones"]:
            if p not in master["phones"] and p not in new_phones:
                new_phones.append(p)

    # Обновляем мастер
    if new_emails or new_phones:
        # Получаем текущие данные мастера (с retry)
        for attempt in range(3):
            try:
                fresh = service.people().get(
                    resourceName=master["resource_name"],
                    personFields="names,emailAddresses,phoneNumbers,organizations,metadata",
                ).execute()
                break
            except (HttpError, BrokenPipeError, ConnectionError) as e:
                if attempt < 2:
                    time.sleep(60)
                    continue
                return {"status": "error", "reason": f"get failed: {e}"}

        etag = fresh.get("etag", "")
        existing_emails = [e.get("value", "") for e in fresh.get("emailAddresses", [])]
        existing_phones = [p.get("value", "") for p in fresh.get("phoneNumbers", [])]

        body = {"etag": etag}
        update_fields = []

        # Добавляем email
        if new_emails:
            all_emails = [{"value": e} for e in existing_emails]
            for e in new_emails:
                if e not in existing_emails:
                    all_emails.append({"value": e})
            body["emailAddresses"] = all_emails
            update_fields.append("emailAddresses")

        # Добавляем телефоны
        if new_phones:
            all_phones = [{"value": p} for p in existing_phones]
            for p in new_phones:
                if p not in existing_phones:
                    all_phones.append({"value": p})
            body["phoneNumbers"] = all_phones
            update_fields.append("phoneNumbers")

        if update_fields:
            for attempt in range(3):
                try:
                    service.people().updateContact(
                        resourceName=master["resource_name"],
                        updatePersonFields=",".join(update_fields),
                        body=body,
                    ).execute()
                    break
                except (HttpError, BrokenPipeError, ConnectionError) as e:
                    if attempt < 2:
                        time.sleep(60)
                        # Refresh etag before retry
                        try:
                            fresh = service.people().get(
                                resourceName=master["resource_name"],
                                personFields="metadata",
                            ).execute()
                            body["etag"] = fresh.get("etag", "")
                        except Exception:
                            pass
                        continue
                    return {"status": "error", "reason": f"update failed: {e}"}

    # Удаляем слейвов
    deleted = []
    for slave in slaves:
        try:
            service.people().deleteContact(resourceName=slave["resource_name"]).execute()
            deleted.append(slave["display_name"])
        except (HttpError, BrokenPipeError) as e:
            if isinstance(e, HttpError) and e.status_code == 429 or isinstance(e, BrokenPipeError):
                time.sleep(60)
                try:
                    service.people().deleteContact(resourceName=slave["resource_name"]).execute()
                    deleted.append(slave["display_name"])
                except Exception as e2:
                    deleted.append(f"❌ {slave['display_name']}: {e2}")
            else:
                deleted.append(f"❌ {slave['display_name']}: {e}")

    return {
        "status": "ok",
        "master": master["display_name"],
        "deleted": deleted,
        "added_emails": new_emails,
        "added_phones": new_phones,
    }


def main():
    do_report = "--report" in sys.argv
    do_merge = "--merge" in sys.argv

    if not do_report and not do_merge:
        print("Использование:")
        print("  python scripts/google_contacts_dedup.py --report   # Отчёт о дублях")
        print("  python scripts/google_contacts_dedup.py --merge   # Объединить дубли")
        return

    print("🔍 Загрузка Google Contacts...")
    service = get_service()
    contacts = load_all_contacts(service)
    print(f"   Загружено: {len(contacts)} контактов")

    senders = load_senders()
    print(f"   Senders: {len(senders)}")

    print("📊 Группировка по фамилии...")
    groups = group_by_family(contacts)

    # Фильтруем: только группы ≥2
    dup_groups = {k: v for k, v in groups.items() if len(v) >= 2}

    # Фильтр: настоящие дубли (общий email/телефон или один пустой)
    real_dup_groups = {}
    for key, group in dup_groups.items():
        # Есть ли общий email/телефон между любыми двумя контактами в группе?
        has_shared = False
        has_empty = any(is_empty(c) for c in group)

        if not has_empty:
            # Проверяем общие данные
            all_emails = set()
            all_phones = set()
            for c in group:
                for e in c["emails"]:
                    if e in all_emails:
                        has_shared = True
                        break
                    all_emails.add(e)
                for p in c["phones"]:
                    if p in all_phones:
                        has_shared = True
                        break
                    all_phones.add(p)
                if has_shared:
                    break

        if has_shared or has_empty:
            real_dup_groups[key] = group

    dup_groups = real_dup_groups
    print(f"   Групп дублей (реальных): {len(dup_groups)}")
    print(f"   Контактов в дублях: {sum(len(v) for v in dup_groups.values())}")

    if do_report:
        print("📝 Генерация отчёта...")
        report = generate_report(dup_groups, senders)
        report_path = PROJECT_ROOT / "data" / "dedup_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"   ✅ Отчёт: {report_path}")

        # Также сохраняем JSON для merge
        json_path = PROJECT_ROOT / "data" / "dedup_groups.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dup_groups, f, ensure_ascii=False, indent=2)
        print(f"   ✅ Данные: {json_path}")

        # Краткая сводка
        auto_mergeable = sum(1 for g in dup_groups.values() if any(is_empty(c) for c in g))
        print(f"\n📊 Сводка:")
        print(f"   Всего групп дублей: {len(dup_groups)}")
        print(f"   Авто-объединяемые (есть пустой дубль): {auto_mergeable}")
        print(f"   Требуют ручной проверки: {len(dup_groups) - auto_mergeable}")

    if do_merge:
        # Загружаем группы из JSON если есть, иначе используем текущие
        json_path = PROJECT_ROOT / "data" / "dedup_groups.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                dup_groups = json.load(f)
            print(f"   Загружены группы из {json_path}")

        print(f"\n🧹 Объединение {len(dup_groups)} групп...")

        # Фильтр: только авто-объединяемые (есть пустой дубль) или все
        merge_all = "--all" in sys.argv
        if not merge_all:
            auto_groups = {k: v for k, v in dup_groups.items() if any(is_empty(c) for c in v)}
            print(f"   Авто-объединяемых: {len(auto_groups)} (добавь --all для всех)")
            dup_groups = auto_groups

        # --skip N: пропустить первые N групп (для resume после краша)
        skip_n = 0
        for arg in sys.argv:
            if arg.startswith("--skip="):
                skip_n = int(arg.split("=")[1])
        if skip_n > 0:
            print(f"   Пропускаем первые {skip_n} групп (resume)")

        results = {"ok": 0, "error": 0, "skip": 0}
        for i, (family_key, group_data) in enumerate(dup_groups.items()):
            if i < skip_n:
                results["skip"] += 1
                continue
            if i > skip_n and (i - skip_n) % 20 == 0:
                print(f"   ⏳ Пауза 60с... ({i - skip_n}/{len(dup_groups) - skip_n}) [total {i}]")
                time.sleep(60)

            # Восстанавливаем из JSON (dict → list of info dicts)
            group = group_data if isinstance(group_data, list) else [group_data]
            result = merge_group(service, group, senders)

            if result["status"] == "ok":
                results["ok"] += 1
                added = ""
                if result.get("added_emails"):
                    added += f" +{len(result['added_emails'])} email"
                if result.get("added_phones"):
                    added += f" +{len(result['added_phones'])} тел."
                print(f"   ✅ {result['master']}{added} ← удалено {len(result['deleted'])} дублей")
            elif result["status"] == "error":
                results["error"] += 1
                print(f"   ❌ {family_key}: {result['reason'][:80]}")
            else:
                results["skip"] += 1

        print(f"\n✅ Результат: {results['ok']} объединено, {results['error']} ошибок, {results['skip']} пропущено")


if __name__ == "__main__":
    main()
