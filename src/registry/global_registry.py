#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global registry for deterministic organization/contact identifiers."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import yaml

from ..utils.city_registry import CityRegistry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = PROJECT_ROOT / "registry"
OVERRIDES_FILENAME = "overrides.yml"

# UUID namespaces (фиксированные значения — не изменять после публикации)
ORG_NS = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
CONTACT_NS = uuid.UUID("11111111-2222-3333-4444-555555555555")

_CITY_REGISTRY = CityRegistry()

LEGAL_SUFFIXES = (
    "ооо",
    "зао",
    "оао",
    "пао",
    "ип",
    "фбуз",
    "фгбу",
    "гбуз",
    "нп",
    "ао",
    "ao",
    "ooo",
    "zao",
    "oao",
    "pao",
)

PUBLIC_TWO_LEVEL_TLDS = {
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "co.jp",
    "co.kr",
    "com.sg",
    "com.tr",
}

EMAIL_SPLIT_RE = re.compile(r"@")
NON_DIGIT_RE = re.compile(r"\D+")
SPACE_RE = re.compile(r"\s+")


@dataclass
class ResolutionResult:
    gid: str
    match_rule: str
    key_tuple: Tuple[str, ...]
    alias_added: bool = False
    source: str = "registry"
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    overrides_applied: bool = False


class FileLock:
    """Cross-platform file lock based on flock/msvcrt."""

    def __init__(self, path: Path):
        self.path = path
        self._handle: Optional[Any] = None

    def __enter__(self) -> Any:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+")
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        return self._handle

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._handle:
            return
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _normalize_space(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()


def norm_inn(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = NON_DIGIT_RE.sub("", str(value))
    if len(digits) in (10, 12):
        return digits
    return None


def norm_domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip().lower()
    if not value:
        return None
    if "@" in value:
        parts = EMAIL_SPLIT_RE.split(value, maxsplit=1)
        value = parts[1] if len(parts) > 1 else parts[0]
    if "://" in value:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        value = parsed.hostname or ""
    value = value.split("/")[0]
    value = value.split(":")[0]
    value = value.strip(".")
    if not value:
        return None
    try:
        ascii_domain = value.encode("idna").decode("ascii")
    except UnicodeError:
        ascii_domain = value
    labels = [label for label in ascii_domain.split(".") if label]
    if not labels:
        return None
    if len(labels) <= 2:
        root = ".".join(labels)
    else:
        last_two = ".".join(labels[-2:])
        last_three = ".".join(labels[-3:])
        if last_two in PUBLIC_TWO_LEVEL_TLDS and len(labels) >= 3:
            root = last_three
        else:
            root = last_two
    return root


def _strip_legal_suffix(name: str) -> str:
    tokens = [token for token in SPACE_RE.split(name.lower()) if token]
    filtered = [token for token in tokens if token not in LEGAL_SUFFIXES]
    return " ".join(filtered)


def norm_org_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name = _normalize_space(name)
    if not name:
        return None
    name = name.replace("\"", "").replace("'", "")
    name = name.replace("«", "").replace("»", "")
    name = name.replace("“", "").replace("”", "")
    name = name.lower()
    name = _strip_legal_suffix(name)
    name = SPACE_RE.sub(" ", name)
    return name.strip() or None


def norm_city(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    record = _CITY_REGISTRY.resolve_city(value)
    if record:
        normalized = record.city
    else:
        normalized = value
    normalized = _normalize_space(normalized)
    normalized = normalized.replace("ё", "е").lower()
    return normalized or None


def norm_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    email = str(value).strip().lower()
    return email or None


def norm_e164(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = NON_DIGIT_RE.sub("", str(value))
    if not digits:
        return None
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("7") and len(digits) == 11:
        digits = "+" + digits
    elif digits.startswith("+"):
        digits = "+" + digits.lstrip("+")
    elif digits.startswith("9") and len(digits) == 10:
        digits = "+7" + digits
    elif not digits.startswith("+"):
        digits = "+" + digits
    return digits


def norm_contact_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    name = _normalize_space(value)
    name = name.replace(".", " ")
    name = SPACE_RE.sub(" ", name)
    return name.lower() or None


def norm_contact_position(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    position = _normalize_space(value)
    return position.lower() or None


def _hash_fallback(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------


def iter_org_keys(org: Dict[str, Any]) -> Iterable[Tuple[str, ...]]:
    seen: Set[Tuple[str, ...]] = set()

    inn = norm_inn(org.get("inn"))
    if inn:
        key = ("ORG", "INN", inn)
        seen.add(key)
        yield key

    domain_candidates: List[str] = []
    if org.get("website"):
        domain_candidates.append(org["website"])
    if org.get("website_domain"):
        domain_candidates.append(org["website_domain"])
    for email in org.get("emails", []) or []:
        if isinstance(email, str) and "@" in email:
            domain_candidates.append(email.split("@", 1)[1])
    for raw_domain in domain_candidates:
        domain = norm_domain(raw_domain)
        if not domain:
            continue
        key = ("ORG", "DOMAIN", domain)
        if key not in seen:
            seen.add(key)
            yield key

    name_norm = norm_org_name(org.get("name"))
    city_norm = norm_city(org.get("city"))
    if name_norm and city_norm:
        key = ("ORG", "NAME_CITY", name_norm, city_norm)
        if key not in seen:
            seen.add(key)
            yield key

    email_domains = {
        norm_domain(email.split("@", 1)[1])
        for email in org.get("emails", []) or []
        if isinstance(email, str) and "@" in email
    }
    for domain in sorted(filter(None, email_domains)):
        key = ("ORG", "EMAIL_DOMAIN", domain)
        if key not in seen:
            seen.add(key)
            yield key

    fallback_basis = name_norm or org.get("name", "")
    city_component = city_norm or (org.get("city") or "")
    hashed = _hash_fallback(f"{fallback_basis}|{city_component}")
    fallback_key = ("ORG", "FALLBACK", hashed)
    if fallback_key not in seen:
        yield fallback_key


def iter_contact_keys(contact: Dict[str, Any], org_gid: Optional[str]) -> Iterable[Tuple[str, ...]]:
    seen: Set[Tuple[str, ...]] = set()
    
    # Для контактов без организации используем специальный маркер
    org_key = org_gid if org_gid is not None else "PERSONAL"

    email = norm_email(contact.get("email"))
    if email:
        key = ("CONTACT", "EMAIL", org_key, email)
        seen.add(key)
        yield key

    for phone in contact.get("phones", []) or []:
        if isinstance(phone, dict):
            phone_number = phone.get("number")
        else:
            phone_number = phone
        e164 = norm_e164(phone_number)
        if not e164:
            continue
        key = ("CONTACT", "PHONE", org_key, e164)
        if key not in seen:
            seen.add(key)
            yield key

    name_norm = norm_contact_name(contact.get("name"))
    position_norm = norm_contact_position(contact.get("position")) or ""
    key = ("CONTACT", "NAME_POSITION", org_key, name_norm or "", position_norm)
    if key not in seen:
        seen.add(key)
        yield key


# ---------------------------------------------------------------------------
# Registry implementation
# ---------------------------------------------------------------------------


class GlobalIDRegistry:
    """Persisted registry that maps canonical keys to deterministic GIDs."""

    def __init__(
        self,
        registry_dir: Optional[Path] = None,
        overrides_path: Optional[Path] = None,
    ) -> None:
        self.registry_dir = Path(registry_dir or REGISTRY_DIR)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        self.org_file = self.registry_dir / "organizations.jsonl"
        self.contact_file = self.registry_dir / "contacts.jsonl"
        self.org_lock = self.registry_dir / "organizations.lock"
        self.contact_lock = self.registry_dir / "contacts.lock"

        self.overrides_path = (
            Path(overrides_path)
            if overrides_path is not None
            else self.registry_dir / OVERRIDES_FILENAME
        )

        self.key_index: Dict[Tuple[str, ...], str] = {}
        self.gid_index: Dict[str, Dict[str, Any]] = {}
        self.alias_index: Dict[str, Set[Tuple[str, ...]]] = {}
        self._gid_keys: Dict[str, Set[Tuple[str, ...]]] = {}
        self._line_counters = {"organizations": 0, "contacts": 0}
        self._lock = threading.RLock()

        self.org_overrides: Dict[Tuple[str, ...], str] = {}
        self.contact_overrides: Dict[Tuple[str, ...], str] = {}

        self._load_overrides()
        self._load_file(self.org_file, "organizations")
        self._load_file(self.contact_file, "contacts")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_organization(self, org: Dict[str, Any]) -> ResolutionResult:
        with self._lock:
            keys = list(iter_org_keys(org))
            if not keys:
                raise ValueError("Organization object does not contain identification data")

            override_result = self._resolve_with_overrides(keys, entity="organization")
            if override_result:
                return override_result

            for key in keys:
                gid = self.key_index.get(key)
                if gid:
                    alias_added, conflicts = self._ensure_aliases(
                        gid, keys, bucket="organizations"
                    )
                    return ResolutionResult(
                        gid=gid,
                        match_rule=key[1],
                        key_tuple=key,
                        alias_added=alias_added,
                        source="registry",
                        conflicts=conflicts,
                    )

            # Create new record
            primary = keys[0]
            gid = self._generate_gid(primary, namespace=ORG_NS)
            aliases = [alias for alias in keys[1:] if alias != primary]
            self._create_record(
                bucket="organizations",
                gid=gid,
                primary_key=primary,
                aliases=aliases,
                source="new",
            )
            return ResolutionResult(
                gid=gid,
                match_rule=primary[1],
                key_tuple=primary,
                alias_added=bool(aliases),
                source="new",
            )

    def resolve_contact(self, contact: Dict[str, Any], org_gid: Optional[str]) -> ResolutionResult:
        with self._lock:
            keys = list(iter_contact_keys(contact, org_gid))
            if not keys:
                raise ValueError("Contact object does not contain identification data")

            override_result = self._resolve_with_overrides(keys, entity="contact")
            if override_result:
                return override_result

            for key in keys:
                gid = self.key_index.get(key)
                if gid:
                    alias_added, conflicts = self._ensure_aliases(
                        gid, keys, bucket="contacts"
                    )
                    return ResolutionResult(
                        gid=gid,
                        match_rule=key[1],
                        key_tuple=key,
                        alias_added=alias_added,
                        source="registry",
                        conflicts=conflicts,
                    )

            primary = keys[0]
            gid = self._generate_gid(primary, namespace=CONTACT_NS)
            aliases = [alias for alias in keys[1:] if alias != primary]
            self._create_record(
                bucket="contacts",
                gid=gid,
                primary_key=primary,
                aliases=aliases,
                source="new",
            )
            return ResolutionResult(
                gid=gid,
                match_rule=primary[1],
                key_tuple=primary,
                alias_added=bool(aliases),
                source="new",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_with_overrides(
        self,
        keys: Sequence[Tuple[str, ...]],
        entity: str,
    ) -> Optional[ResolutionResult]:
        overrides = (
            self.org_overrides if entity == "organization" else self.contact_overrides
        )
        bucket = "organizations" if entity == "organization" else "contacts"
        for key in keys:
            override_gid = overrides.get(key)
            if not override_gid:
                continue
            conflict = None
            existing_gid = self.key_index.get(key)
            if existing_gid and existing_gid != override_gid:
                conflict = {
                    "entity": entity,
                    "key": list(key),
                    "existing_gid": existing_gid,
                    "override_gid": override_gid,
                }
            self._ensure_override_record(override_gid, key, bucket)
            alias_added, alias_conflicts = self._ensure_aliases(
                override_gid, keys, bucket=bucket
            )
            all_conflicts = []
            if conflict:
                all_conflicts.append(conflict)
            all_conflicts.extend(alias_conflicts)
            return ResolutionResult(
                gid=override_gid,
                match_rule=key[1],
                key_tuple=key,
                alias_added=alias_added,
                source="override",
                conflicts=all_conflicts,
                overrides_applied=True,
            )
        return None

    def _ensure_override_record(
        self,
        override_gid: str,
        key: Tuple[str, ...],
        bucket: str,
    ) -> None:
        if override_gid not in self.gid_index:
            self._create_record(
                bucket=bucket,
                gid=override_gid,
                primary_key=key,
                aliases=[],
                source="override",
            )
        else:
            # Ensure key is registered for override gid
            self._ensure_aliases(override_gid, [key], bucket=bucket)

    def _generate_gid(self, primary_key: Tuple[str, ...], namespace: uuid.UUID) -> str:
        return str(uuid.uuid5(namespace, repr(primary_key)))

    def _create_record(
        self,
        bucket: str,
        gid: str,
        primary_key: Tuple[str, ...],
        aliases: Sequence[Tuple[str, ...]],
        source: str,
    ) -> None:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record = {
            "event": "create",
            "gid": gid,
            "key": list(primary_key),
            "aliases": [list(alias) for alias in aliases],
            "created_at": timestamp,
            "source": source,
        }
        self._append_event(bucket, record)

    def _ensure_aliases(
        self,
        gid: str,
        keys: Sequence[Tuple[str, ...]],
        bucket: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        alias_added = False
        conflicts: List[Dict[str, Any]] = []
        for key in keys:
            if key in self.key_index and self.key_index[key] == gid:
                continue
            if key in self.key_index and self.key_index[key] != gid:
                conflicts.append(
                    {
                        "entity": "organization" if bucket == "organizations" else "contact",
                        "key": list(key),
                        "existing_gid": self.key_index[key],
                        "target_gid": gid,
                    }
                )
                continue
            gid_keys = self._gid_keys.setdefault(gid, set())
            if key in gid_keys:
                self.key_index[key] = gid
                continue
            self.key_index[key] = gid
            gid_keys.add(key)
            record = self.gid_index.setdefault(gid, {"gid": gid, "aliases": []})
            record.setdefault("aliases", [])
            if list(key) not in record["aliases"]:
                record["aliases"].append(list(key))
            alias_event = {
                "event": "alias",
                "gid": gid,
                "alias": list(key),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._append_event(bucket, alias_event)
            alias_added = True
        return alias_added, conflicts

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _append_event(self, bucket: str, record: Dict[str, Any]) -> None:
        file_path = self.org_file if bucket == "organizations" else self.contact_file
        lock_path = self.org_lock if bucket == "organizations" else self.contact_lock

        with FileLock(lock_path):
            self._refresh_file(bucket)
            with file_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._line_counters[bucket] += 1
            self._apply_event(record, bucket)

    def _load_overrides(self) -> None:
        if not self.overrides_path.exists():
            return
        with self.overrides_path.open("r", encoding="utf-8") as handle:
            overrides_data = yaml.safe_load(handle) or {}
        for item in overrides_data.get("org_overrides", []) or []:
            key_tuple = tuple(item.get("key", []))
            gid_value = item.get("gid")
            if key_tuple and gid_value:
                self.org_overrides[key_tuple] = gid_value
        for item in overrides_data.get("contact_overrides", []) or []:
            key_tuple = tuple(item.get("key", []))
            gid_value = item.get("gid")
            if key_tuple and gid_value:
                self.contact_overrides[key_tuple] = gid_value

    def _load_file(self, path: Path, bucket: str) -> None:
        if not path.exists():
            path.touch()
            self._line_counters[bucket] = 0
            return
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._apply_event(record, bucket)
                count += 1
        self._line_counters[bucket] = count

    def _refresh_file(self, bucket: str) -> None:
        file_path = self.org_file if bucket == "organizations" else self.contact_file
        if not file_path.exists():
            return
        start = self._line_counters[bucket]
        if start < 0:
            start = 0
        with file_path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle):
                if idx < start:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._apply_event(record, bucket)
                self._line_counters[bucket] = idx + 1

    def _apply_event(self, record: Dict[str, Any], bucket: str) -> None:
        event_type = record.get("event", "create")
        gid = record.get("gid")
        if not gid:
            return

        if event_type == "create":
            primary_key = tuple(record.get("key", []))
            aliases = [tuple(alias) for alias in record.get("aliases", [])]

            # Проверяем, существует ли уже такая запись
            if gid in self.gid_index:
                # Запись уже существует, добавляем только новые ключи как aliases
                existing_entry = self.gid_index[gid]
                existing_keys = self._gid_keys.get(gid, set())

                # Добавляем primary key если его нет
                if primary_key not in existing_keys:
                    self.key_index[primary_key] = gid
                    self._gid_keys.setdefault(gid, set()).add(primary_key)
                    if list(primary_key) not in existing_entry["aliases"]:
                        existing_entry["aliases"].append(list(primary_key))

                # Добавляем aliases если их нет
                for alias in aliases:
                    if alias not in existing_keys:
                        self.key_index[alias] = gid
                        self._gid_keys[gid].add(alias)
                        if list(alias) not in existing_entry["aliases"]:
                            existing_entry["aliases"].append(list(alias))
            else:
                # Новая запись - создаём её
                self.key_index[primary_key] = gid
                gid_entry = self.gid_index.setdefault(
                    gid,
                    {
                        "gid": gid,
                        "key": list(primary_key),
                        "aliases": [],
                        "created_at": record.get("created_at"),
                        "source": record.get("source", "registry"),
                    },
                )
                gid_entry["key"] = list(primary_key)
                gid_entry.setdefault("aliases", [])
                self._gid_keys.setdefault(gid, set()).add(primary_key)
                for alias in aliases:
                    self.key_index[alias] = gid
                    if list(alias) not in gid_entry["aliases"]:
                        gid_entry["aliases"].append(list(alias))
                    self._gid_keys[gid].add(alias)

        elif event_type == "alias":
            alias = tuple(record.get("alias", []))
            if alias:
                self.key_index[alias] = gid
                gid_entry = self.gid_index.setdefault(gid, {"gid": gid, "aliases": []})
                gid_entry.setdefault("aliases", [])
                if list(alias) not in gid_entry["aliases"]:
                    gid_entry["aliases"].append(list(alias))
                self._gid_keys.setdefault(gid, set()).add(alias)

    # ------------------------------------------------------------------
    # Utility accessors
    # ------------------------------------------------------------------

    def get_all_keys_for_gid(self, gid: str) -> Set[Tuple[str, ...]]:
        return self._gid_keys.get(gid, set())
