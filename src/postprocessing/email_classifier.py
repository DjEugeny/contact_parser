#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Классификация почтовых ящиков для организаций и контактов."""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Dict, Set


class MailboxType(str, Enum):
    PERSONAL_INTERNAL = "personal_internal"
    PERSONAL_EXTERNAL = "personal_external"
    SHARED_ORG = "shared_org"
    DEPARTMENT = "department"
    GROUP_ALIAS = "group_alias"
    TECHNICAL = "technical"
    UNKNOWN = "unknown"


_LOCAL_PERSONAL_PATTERN = re.compile(
    r"^(?:[a-zа-яё]{1,2}[.\-_])?[a-zа-яё]+(?:[.\-_][a-zа-яё]+)?(\d{0,2})$",
    re.IGNORECASE,
)
_INITIAL_LASTNAME_PATTERN = re.compile(r"^[a-zа-яё]\.[a-zа-яё-]{2,}$", re.IGNORECASE)
_SIMPLE_LASTNAME_PATTERN = re.compile(r"^[a-zа-яё-]{3,}$", re.IGNORECASE)
_DISPLAY_NAME_PERSON_PATTERN = re.compile(r"[а-яёa-z]+\s+[а-яёa-z]+", re.IGNORECASE)


def _normalize_local_part(local: str) -> str:
    return (local or "").strip().lower()


def _normalize_domain(domain: str) -> str:
    return (domain or "").strip().lower()


def _looks_like_personal_corporate(local: str) -> bool:
    if not local:
        return False
    if _INITIAL_LASTNAME_PATTERN.match(local):
        return True
    if any(sep in local for sep in ('.', '-', '_')):
        return bool(_LOCAL_PERSONAL_PATTERN.match(local))
    if _SIMPLE_LASTNAME_PATTERN.match(local) and len(local) <= 15:
        return True
    return False


def _looks_like_name(display_name: Optional[str]) -> bool:
    if not display_name:
        return False
    return bool(_DISPLAY_NAME_PERSON_PATTERN.search(display_name))


def _looks_like_personal_external(local: str, display_name: Optional[str]) -> bool:
    if _looks_like_name(display_name):
        return True
    if any(sep in local for sep in ('.', '-', '_')):
        return bool(_LOCAL_PERSONAL_PATTERN.match(local) or _INITIAL_LASTNAME_PATTERN.match(local))
    return False


def classify_mailbox(
    address: str,
    display_name: Optional[str],
    corp_domains: Set[str],
    cfg: Dict[str, list],
) -> MailboxType:
    """Классифицирует email на основании домена и паттернов."""
    if not address or "@" not in address:
        return MailboxType.UNKNOWN

    try:
        local_part, domain = address.split("@", 1)
    except ValueError:
        return MailboxType.UNKNOWN

    local = _normalize_local_part(local_part)
    domain_norm = _normalize_domain(domain)

    shared_prefixes = {p.lower() for p in cfg.get("shared_mailboxes_prefixes", [])}
    department_prefixes = {p.lower() for p in cfg.get("department_prefixes", [])}
    technical_prefixes = {p.lower() for p in cfg.get("technical_prefixes", [])}
    group_suffixes = {s.lower() for s in cfg.get("group_alias_suffixes", [])}

    is_corporate = domain_norm in corp_domains

    # Технические ящики
    if any(local.startswith(prefix) for prefix in technical_prefixes):
        return MailboxType.TECHNICAL

    if any(local.endswith(suffix) for suffix in group_suffixes):
        return MailboxType.GROUP_ALIAS

    if any(local.startswith(prefix) for prefix in shared_prefixes):
        return MailboxType.SHARED_ORG

    if any(local.startswith(prefix) for prefix in department_prefixes):
        return MailboxType.DEPARTMENT

    if is_corporate:
        if _looks_like_personal_corporate(local):
            return MailboxType.PERSONAL_INTERNAL
        return MailboxType.UNKNOWN

    # Внешние домены
    if _looks_like_personal_external(local, display_name):
        return MailboxType.PERSONAL_EXTERNAL

    return MailboxType.UNKNOWN


__all__ = ["MailboxType", "classify_mailbox"]
