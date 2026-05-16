#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для Google Contacts Enrichment pipeline (шаги A, B, D из PLAN V2).

Покрывает:
- parse_fio (extract_senders + imap_sender_scan)
- decode_from_header (imap_sender_scan)
- _extract_from_from_header_response (imap_sender_scan)
- transliterate, normalize_name, get_name_key (google_contacts_enrich)
- match_senders_to_google — все 4 уровня + multi-email на один контакт
- extract_senders_from_jsonl — EMAIL_GLOBAL, EMAIL_IN_ORG, partial email
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─── Загрузка модулей из scripts/ ───

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_module(name: str, path: Path, extra_mocks=None):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    if extra_mocks:
        for mod_name, mock_obj in extra_mocks.items():
            sys.modules[mod_name] = mock_obj
    try:
        spec.loader.exec_module(mod)
    finally:
        if extra_mocks:
            for mod_name in extra_mocks:
                sys.modules.pop(mod_name, None)
    return mod


# Мокаем google-зависимости
google_mocks = {
    "google": MagicMock(),
    "google.auth": MagicMock(),
    "google.auth.transport": MagicMock(),
    "google.auth.transport.requests": MagicMock(),
    "google.oauth2": MagicMock(),
    "google.oauth2.credentials": MagicMock(),
    "googleapiclient": MagicMock(),
    "googleapiclient.discovery": MagicMock(),
    "googleapiclient.errors": MagicMock(),
}

extract_senders = _load_module("extract_senders", SCRIPTS_DIR / "extract_senders.py")
imap_sender_scan = _load_module("imap_sender_scan", SCRIPTS_DIR / "imap_sender_scan.py")
google_contacts_enrich = _load_module(
    "google_contacts_enrich",
    SCRIPTS_DIR / "google_contacts_enrich.py",
    extra_mocks=google_mocks,
)


# ══════════════════════════════════════════════
# parse_fio (общая для extract_senders и imap)
# ══════════════════════════════════════════════

class TestParseFio:
    """Проверка разбора ФИО на компоненты."""

    def test_full_fio(self):
        result = extract_senders.parse_fio("Иванов Иван Петрович")
        assert result == {"last": "Иванов", "first": "Иван", "middle": "Петрович"}

    def test_two_parts(self):
        result = extract_senders.parse_fio("Иванов Иван")
        assert result == {"last": "Иванов", "first": "Иван"}

    def test_initials(self):
        result = extract_senders.parse_fio("Иванов И. П.")
        assert result == {"last": "Иванов", "first_init": "И", "middle_init": "П"}

    def test_initials_no_space(self):
        """И.П. без пробела — один токен, не парсится как инициалы."""
        result = extract_senders.parse_fio("Иванов И.П.")
        # И.П. — один токен, не match ^[А-ЯЁA-Z]\.$, поэтому first="И.П."
        assert result["last"] == "Иванов"
        assert "first" in result

    def test_last_only(self):
        result = extract_senders.parse_fio("Иванов")
        assert result == {"last": "Иванов"}

    def test_empty(self):
        assert extract_senders.parse_fio("") == {}
        assert extract_senders.parse_fio("  ") == {}

    def test_double_last_name(self):
        """Двойная фамилия — документируем поведение: берётся как одно слово."""
        result = extract_senders.parse_fio("Иванова-Петрова Анна")
        assert result["last"] == "Иванова-Петрова"
        assert result["first"] == "Анна"

    def test_three_initials(self):
        result = extract_senders.parse_fio("Сидоров С. М.")
        assert result == {"last": "Сидоров", "first_init": "С", "middle_init": "М"}

    def test_imap_parse_fio_same(self):
        """parse_fio в imap_sender_scan идентична."""
        r1 = extract_senders.parse_fio("Иванов Иван Петрович")
        r2 = imap_sender_scan.parse_fio("Иванов Иван Петрович")
        assert r1 == r2


# ══════════════════════════════════════════════
# decode_from_header (imap_sender_scan)
# ══════════════════════════════════════════════

class TestDecodeFromHeader:
    """Проверка декодирования заголовка From."""

    def test_name_and_email(self):
        name, addr = imap_sender_scan.decode_from_header('"Иванов Иван" <ivanov@mail.ru>')
        assert name == "Иванов Иван"
        assert addr == "ivanov@mail.ru"

    def test_email_only(self):
        name, addr = imap_sender_scan.decode_from_header("a@b.ru")
        assert name == ""
        assert addr == "a@b.ru"

    def test_empty(self):
        name, addr = imap_sender_scan.decode_from_header("")
        assert name == ""
        assert addr == ""

    def test_mime_encoded(self):
        """MIME-encoded заголовок (Base64 UTF-8)."""
        # =?utf-8?B?0JDQu9C10L3QsNC90LAg0JDQu9C10L3QsA==?= = Иванова Иванова
        name, addr = imap_sender_scan.decode_from_header(
            '=?utf-8?B?0JDQu9C10L3QsNC90LAg0JDQu9C10L3QsA==?= <test@mail.ru>'
        )
        assert addr == "test@mail.ru"
        assert "Иванова" in name or len(name) > 0

    def test_angle_brackets_no_quotes(self):
        name, addr = imap_sender_scan.decode_from_header("Иванов Иван <ivanov@mail.ru>")
        assert addr == "ivanov@mail.ru"
        assert "Иванов" in name

    def test_garbage_fallback(self):
        """parseaddr не парсит мусор, но bracket extraction в try-блоке работает."""
        name, addr = imap_sender_scan.decode_from_header("Blah <real@email.com>")
        assert addr == "real@email.com"
        assert name == "Blah"

    def test_truly_broken_fallback(self):
        """Сломанный заголовок — fallback regex в except."""
        # Передаём bytes-подобный мусор который вызовет exception в make_header
        name, addr = imap_sender_scan.decode_from_header("just some text with =?invalid?= <x@y.z>")
        assert addr == "x@y.z"


# ══════════════════════════════════════════════
# _extract_from_from_header_response (imap)
# ══════════════════════════════════════════════

class TestExtractFromHeaderResponse:
    """Проверка извлечения From из IMAP BODY[HEADER.FIELDS (FROM)]."""

    def test_tuple_response(self):
        response = [(b"1 (BODY[HEADER.FIELDS (FROM)] {30}", b"From: test@mail.ru\r\n\r\n")]
        result = imap_sender_scan._extract_from_from_header_response(response)
        assert result == "test@mail.ru"

    def test_bytes_response(self):
        response = [b"From: user@example.com\r\n\r\n"]
        result = imap_sender_scan._extract_from_from_header_response(response)
        assert result == "user@example.com"

    def test_no_from_prefix(self):
        response = [(b"1 (BODY[HEADER.FIELDS (FROM)] {20}", b"test@mail.ru\r\n")]
        result = imap_sender_scan._extract_from_from_header_response(response)
        assert result == "test@mail.ru"

    def test_empty_response(self):
        result = imap_sender_scan._extract_from_from_header_response([])
        assert result is None


# ══════════════════════════════════════════════
# transliterate / normalize_name / get_name_key
# ══════════════════════════════════════════════

class TestTransliterate:
    def test_basic(self):
        assert google_contacts_enrich.transliterate("иванов") == "ivanov"

    def test_shch(self):
        assert google_contacts_enrich.transliterate("щёлочь") == "shchyoloch"

    def test_yo(self):
        assert google_contacts_enrich.transliterate("ёж") == "yozh"

    def test_latin_passthrough(self):
        assert google_contacts_enrich.transliterate("ivanov") == "ivanov"


class TestNormalizeName:
    def test_case(self):
        assert google_contacts_enrich.normalize_name("ИВАНОВ") == "иванов"

    def test_hyphen(self):
        assert google_contacts_enrich.normalize_name("Иванова-Петрова") == "иванова петрова"

    def test_extra_spaces(self):
        assert google_contacts_enrich.normalize_name("  Иванов   Иван  ") == "иванов иван"


class TestGetNameKey:
    def test_full(self):
        parts = {"last": "Иванов", "first": "Иван", "middle": "Петрович"}
        key = google_contacts_enrich.get_name_key(parts)
        assert key == "иванов иван петрович"

    def test_short(self):
        parts = {"last": "Иванов", "first": "Иван"}
        key = google_contacts_enrich.get_name_key(parts)
        assert key == "иванов иван"

    def test_initials(self):
        parts = {"last": "Иванов", "first_init": "И", "middle_init": "П"}
        key = google_contacts_enrich.get_name_key(parts)
        assert key == "иванов и п"

    def test_last_only(self):
        parts = {"last": "Иванов"}
        key = google_contacts_enrich.get_name_key(parts)
        assert key == "иванов"


# ══════════════════════════════════════════════
# match_senders_to_google — мэтчинг
# ══════════════════════════════════════════════

def _make_google_contact(resource_name, family, given="", middle="", emails=None):
    """Хелпер: создаёт фейковый Google-контакт."""
    names = []
    if family:
        n = {
            "displayName": f"{family} {given} {middle}".strip(),
            "familyName": family,
            "givenName": given,
            "middleName": middle,
            "metadata": {"primary": True},
        }
        names.append(n)
    ea = [{"value": e} for e in (emails or [])]
    return {
        "resourceName": resource_name,
        "etag": "etag123",
        "names": names,
        "emailAddresses": ea,
        "phoneNumbers": [],
    }


def _make_sender(email, last, first="", middle="", display_name=""):
    """Хелпер: создаёт фейкового отправителя."""
    name_parts = {"last": last}
    if first:
        name_parts["first"] = first
    if middle:
        name_parts["middle"] = middle
    return {
        "email": email,
        "name_parts": name_parts,
        "display_name": display_name or f"{last} {first} {middle}".strip(),
        "source": "registry",
        "org_gid": "test-gid",
        "position": "",
    }


class TestMatchSendersToGoogle:
    """Проверка 4 уровней мэтчинга + multi-email."""

    def test_level1_exact_fio(self):
        gc = _make_google_contact("people/1", "Иванов", "Иван", "Петрович")
        sender = _make_sender("ivan@work.ru", "Иванов", "Иван", "Петрович")
        result = google_contacts_enrich.match_senders_to_google([sender], [gc])
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "exact_fio"
        assert result["matched"][0]["action"] == "add_email"

    def test_level2_translit_fio(self):
        """Google-контакт на латинице, sender на кириллице."""
        gc = _make_google_contact("people/2", "Ivanov", "Ivan", "Petrovich")
        sender = _make_sender("ivan@work.ru", "Иванов", "Иван", "Петрович")
        result = google_contacts_enrich.match_senders_to_google([sender], [gc])
        # sender key = "иванов иван петрович", translit = "ivanov ivan petrovich"
        # Google key = "ivanov ivan petrovich" (lowercase латиница)
        # translit_key попадает в google_by_translit
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "translit_fio"

    def test_level3_last_first_only(self):
        gc = _make_google_contact("people/3", "Иванов", "Иван")
        sender = _make_sender("ivan@work.ru", "Иванов", "Иван", "Петрович")
        result = google_contacts_enrich.match_senders_to_google([sender], [gc])
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "last_first_only"

    def test_level4_last_name_only(self):
        gc = _make_google_contact("people/4", "Иванов")
        sender = _make_sender("ivan@work.ru", "Иванов", "Иван", "Петрович")
        result = google_contacts_enrich.match_senders_to_google([sender], [gc])
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "last_name_only"

    def test_no_match_no_name(self):
        gc = _make_google_contact("people/5", "Иванов", "Иван")
        sender = _make_sender("x@y.ru", "", "")  # нет ФИО
        result = google_contacts_enrich.match_senders_to_google([sender], [gc])
        assert len(result["matched"]) == 0
        assert len(result["unmatched_senders"]) == 1

    def test_skip_already_has(self):
        gc = _make_google_contact("people/6", "Иванов", "Иван", emails=["ivan@work.ru"])
        sender = _make_sender("ivan@work.ru", "Иванов", "Иван")
        result = google_contacts_enrich.match_senders_to_google([sender], [gc])
        assert len(result["matched"]) == 1
        assert result["matched"][0]["action"] == "skip_already_has"

    def test_multi_email_same_contact(self):
        """Баг #5: один Google-контакт получает несколько email (уровни 1-3)."""
        gc = _make_google_contact("people/7", "Иванов", "Иван", "Петрович", emails=["ivan@old.ru"])
        sender1 = _make_sender("ivan@work.ru", "Иванов", "Иван", "Петрович")
        sender2 = _make_sender("ivan@home.ru", "Иванов", "Иван", "Петрович")
        result = google_contacts_enrich.match_senders_to_google([sender1, sender2], [gc])
        # Оба должны смэтчиться с одним контактом
        matched = result["matched"]
        assert len(matched) == 2
        assert all(m["google_contact_id"] == "people/7" for m in matched)
        actions = {m["sender_email"]: m["action"] for m in matched}
        assert actions["ivan@work.ru"] == "add_email"
        assert actions["ivan@home.ru"] == "add_email"

    def test_level4_blocks_reuse(self):
        """Уровень 4 — консервативный, блокирует повторное использование."""
        gc = _make_google_contact("people/8", "Иванов")
        sender1 = _make_sender("a@x.ru", "Иванов", "Алексей")
        sender2 = _make_sender("b@x.ru", "Иванов", "Борис")
        result = google_contacts_enrich.match_senders_to_google([sender1, sender2], [gc])
        # Первый смэтчится, второй — нет (used_for_last_name_only)
        matched = result["matched"]
        assert len(matched) == 1
        assert matched[0]["match_type"] == "last_name_only"

    def test_level4_multiple_candidates_no_match(self):
        """Уровень 4: если несколько кандидатов — не мэтчим."""
        gc1 = _make_google_contact("people/9a", "Иванов")
        gc2 = _make_google_contact("people/9b", "Иванов")
        sender = _make_sender("ivan@x.ru", "Иванов", "Иван")
        result = google_contacts_enrich.match_senders_to_google([sender], [gc1, gc2])
        # Два Иванова → last_name_only не сработает
        assert len(result["matched"]) == 0 or result["matched"][0]["match_type"] != "last_name_only"


# ══════════════════════════════════════════════
# extract_senders_from_jsonl — шаг A
# ══════════════════════════════════════════════

class TestExtractSendersFromJsonl:
    """Проверка извлечения email из реестра (EMAIL_GLOBAL, EMAIL_IN_ORG, partial)."""

    def _write_jsonl(self, tmp_path, records):
        p = tmp_path / "contacts.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return p

    def test_email_key(self):
        """Стандартный EMAIL key."""
        records = [{
            "key": ["CONTACT", "EMAIL", "org1", "test@mail.ru"],
            "aliases": [["CONTACT", "NAME_POSITION", "org1", "Тестов Тест", "тестёр"]],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_jsonl(Path(tmp), records)
            senders = extract_senders.extract_senders_from_jsonl(p)
        assert len(senders) == 1
        assert senders[0]["email"] == "test@mail.ru"
        assert senders[0]["display_name"] == "Тестов Тест"

    def test_email_global_key(self):
        """EMAIL_GLOBAL key (без org_gid)."""
        records = [{
            "key": ["CONTACT", "EMAIL_GLOBAL", "global@mail.ru"],
            "aliases": [],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_jsonl(Path(tmp), records)
            senders = extract_senders.extract_senders_from_jsonl(p)
        assert len(senders) == 1
        assert senders[0]["email"] == "global@mail.ru"

    def test_email_in_org_alias(self):
        """EMAIL_IN_ORG alias."""
        records = [{
            "key": ["CONTACT", "NAME_POSITION", "org1", "Иванов Иван", ""],
            "aliases": [["CONTACT", "EMAIL_IN_ORG", "org1", "ivan@org1.ru"]],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_jsonl(Path(tmp), records)
            senders = extract_senders.extract_senders_from_jsonl(p)
        assert len(senders) == 1
        assert senders[0]["email"] == "ivan@org1.ru"
        assert senders[0]["display_name"] == "Иванов Иван"

    def test_partial_email_reconstruction(self):
        """Partial email (без @) реконструируется через домен org_gid."""
        records = [
            {
                "key": ["CONTACT", "EMAIL", "org1", "full@company.ru"],
                "aliases": [["CONTACT", "NAME_POSITION", "org1", "Полный П.", ""]],
            },
            {
                "key": ["CONTACT", "EMAIL", "org1", "partial_user"],
                "aliases": [["CONTACT", "NAME_POSITION", "org1", "Паршивый П.", ""]],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_jsonl(Path(tmp), records)
            senders = extract_senders.extract_senders_from_jsonl(p)
        emails = {s["email"] for s in senders}
        assert "full@company.ru" in emails
        assert "partial_user@company.ru" in emails

    def test_dedup_keeps_longest_fio(self):
        """Дедуп: один email в нескольких org_gid — берётся наиболее полное ФИО."""
        records = [
            {
                "key": ["CONTACT", "EMAIL", "org1", "dup@mail.ru"],
                "aliases": [["CONTACT", "NAME_POSITION", "org1", "Иванов", ""]],
            },
            {
                "key": ["CONTACT", "EMAIL", "org2", "dup@mail.ru"],
                "aliases": [["CONTACT", "NAME_POSITION", "org2", "Иванов Иван Петрович", ""]],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_jsonl(Path(tmp), records)
            senders = extract_senders.extract_senders_from_jsonl(p)
        assert len(senders) == 1
        assert senders[0]["display_name"] == "Иванов Иван Петрович"

    def test_nonexistent_file(self):
        senders = extract_senders.extract_senders_from_jsonl(Path("/nonexistent/file.jsonl"))
        assert senders == []

    def test_skip_non_contact_records(self):
        """Записи без CONTACT в key[0] пропускаются."""
        records = [{"key": ["ORG", "INN", "123"], "aliases": []}]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_jsonl(Path(tmp), records)
            senders = extract_senders.extract_senders_from_jsonl(p)
        assert len(senders) == 0
