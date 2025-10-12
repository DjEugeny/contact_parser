#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧼 Ядро предочистки писем для LLM.

Реализация основана на MVP из `.kiro/specs/precleaner/`,
но адаптирована под архитектуру fetcher и строгую типизацию.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Protocol, Sequence, Set, Tuple


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?\d[\d()\s-]{6,}")
URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
INN_PATTERN = re.compile(r"\b\d{10}(?:\d{2})?\b")

DEFAULT_SIG_MARKERS: Tuple[str, ...] = (
    r"--\s*$",
    r"—\s*$",
    r"с уважением[:,]?$",
    r"best regards[:,]?$",
    r"kind regards[:,]?$",
)
DEFAULT_DISCLAIMER_MARKERS: Tuple[str, ...] = (
    r"confidentiality notice",
    r"настоящее сообщение",
    r"unsubscribe",
    r"privacy policy",
)
HEADER_SEPARATORS: Iterable[str] = (
    r"^-+\s*original message\s*-+$",
    r"^on .* wrote:$",
    r"^(от|дата|кому|тема|from|date|to|subject|sent|cc|bcc):\s",
)


class CacheProvider(Protocol):
    """🧠 Протокол для прокидывания кэшей из адаптера."""

    def get_thread_cache(self, thread_id: str) -> Dict[str, int]:
        """🔁 Возвращает кэш паттернов для заданного треда."""

    def get_sender_cache(self, sender_email: str) -> Dict[str, int]:
        """📬 Возвращает кэш паттернов для отправителя."""


@dataclass
class Block:
    """📦 Сегментированная часть письма."""

    text: str
    quote_level: int
    kind: str = "unknown"  # body|signature|disclaimer|header|quote


@dataclass
class PrecleanResult:
    """📊 Результат предочистки."""

    body_raw: str
    body_clean_llm: str
    clean_spans: Dict[str, List[Dict[str, str]]]
    attachments_index: List[Dict[str, str]]


def _fingerprint(text: str) -> str:
    """🆔 Генерирует короткий отпечаток текста."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def _contains_contact_info(text: str) -> bool:
    """📞 Проверяет наличие контактов (email/телефон/URL/ИНН) в тексте."""
    if EMAIL_PATTERN.search(text):
        return True
    if PHONE_PATTERN.search(text):
        return True
    if URL_PATTERN.search(text):
        return True
    if INN_PATTERN.search(text):
        return True
    return False


def _strip_disclaimer_tail(
    text: str, disclaimer_patterns: Sequence[str]
) -> Tuple[str, Tuple[str, str] | None]:
    """
    ✂️ Отделяет хвост с дисклеймером от текста.

    Returns:
        body_without_disclaimer: текст до начала дисклеймера (может быть пустым)
        placeholder_info: (placeholder, hash) если дисклеймер найден
    """
    lowered = text.lower()
    earliest: int | None = None

    for pattern in disclaimer_patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            start_idx = match.start()
            if earliest is None or start_idx < earliest:
                earliest = start_idx

    if earliest is None:
        return text, None

    tail = text[earliest:].strip()
    cleaned_body = text[:earliest].rstrip()
    tail_hash = _fingerprint(tail)
    placeholder = f"[disclaimer truncated #{tail_hash}]"

    return cleaned_body, (placeholder, tail_hash)


def _ensure_patterns(raw_patterns: Iterable[str] | None, fallback: Tuple[str, ...]) -> Tuple[str, ...]:
    """🧩 Подготавливает списки паттернов из конфигурации."""
    if not raw_patterns:
        return fallback

    prepared = tuple(str(pattern).strip() for pattern in raw_patterns if str(pattern).strip())
    return prepared or fallback


def _strip_quote_prefix(line: str) -> str:
    """🔧 Удаляет префикс цитирования из строки."""
    return re.sub(r"^>+\s*", "", line)


def _trim_non_empty(lines: List[str], limit: int) -> Tuple[str, bool]:
    """✂️ Обрезает блок по количеству непустых строк."""
    if limit <= 0:
        return "", bool(lines)

    trimmed_lines: List[str] = []
    non_empty_seen = 0

    for line in lines:
        trimmed_lines.append(line)
        if line.strip():
            non_empty_seen += 1
        if non_empty_seen >= limit:
            break

    is_truncated = len([line for line in lines if line.strip()]) > non_empty_seen
    return "\n".join(trimmed_lines).rstrip(), is_truncated


def _collect_non_empty_indexes(lines: Sequence[str], limit: int, from_end: bool = False) -> Set[int]:
    """📐 Возвращает индексы строк в начале/конце блока по числу непустых."""
    if limit <= 0:
        return set()

    selected: Set[int] = set()
    non_empty_seen = 0
    indices = range(len(lines) - 1, -1, -1) if from_end else range(len(lines))

    for idx in indices:
        selected.add(idx)
        if lines[idx].strip():
            non_empty_seen += 1
        if non_empty_seen >= limit:
            break

    return selected


def _expand_indexes(indexes: Set[int], total: int, radius: int) -> Set[int]:
    """🔍 Расширяет множество индексов соседними строками."""
    expanded = set(indexes)
    for idx in list(indexes):
        for offset in range(1, radius + 1):
            lower = idx - offset
            upper = idx + offset
            if lower >= 0:
                expanded.add(lower)
            if upper < total:
                expanded.add(upper)
    return expanded


def _prepare_quote_preview(
    raw_text: str,
    head_non_empty: int,
    tail_non_empty: int,
    header_markers: Sequence[str],
    sig_patterns: Sequence[str],
    context_lines: int,
    max_chars: int,
) -> str:
    """🗂️ Формирует компактный превью-блок для длинных цитат."""
    normalized_lines = [_strip_quote_prefix(line) for line in raw_text.splitlines()]
    total_lines = len(normalized_lines)
    if total_lines == 0:
        return ""

    selected_indexes: Set[int] = set()
    selected_indexes |= _collect_non_empty_indexes(normalized_lines, head_non_empty)
    selected_indexes |= _collect_non_empty_indexes(normalized_lines, tail_non_empty, from_end=True)

    header_tokens = tuple(token.lower() for token in header_markers)
    for idx, line in enumerate(normalized_lines):
        lowered = line.lower()
        if any(lowered.startswith(token) for token in header_tokens):
            selected_indexes.add(idx)

    contact_candidates: Set[int] = set()
    for idx, line in enumerate(normalized_lines):
        stripped = line.strip()
        if not stripped:
            continue
        if (
            EMAIL_PATTERN.search(stripped)
            or PHONE_PATTERN.search(stripped)
            or URL_PATTERN.search(stripped)
            or INN_PATTERN.search(stripped)
        ):
            contact_candidates.add(idx)
            continue
        if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in sig_patterns):
            contact_candidates.add(idx)

    if contact_candidates:
        selected_indexes |= _expand_indexes(contact_candidates, total_lines, radius=2)

    ordered_indexes = sorted(selected_indexes)
    header_tokens = tuple(token.lower() for token in header_markers)

    filtered_lines: List[str] = []
    context_budget = max(context_lines, 0)

    last_idx = -2
    for idx in ordered_indexes:
        line = normalized_lines[idx]
        stripped = line.strip()

        if not stripped:
            if filtered_lines and filtered_lines[-1]:
                filtered_lines.append("")
            continue

        is_header_line = any(stripped.lower().startswith(token) for token in header_tokens)
        is_contact_line = bool(
            EMAIL_PATTERN.search(stripped)
            or PHONE_PATTERN.search(stripped)
            or URL_PATTERN.search(stripped)
            or INN_PATTERN.search(stripped)
        )
        matches_signature = any(re.search(pattern, stripped, re.IGNORECASE) for pattern in sig_patterns)
        is_date_header_line = bool(re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", stripped))

        if is_header_line or is_contact_line or matches_signature or is_date_header_line:
            if idx - last_idx > 1 and filtered_lines and filtered_lines[-1]:
                filtered_lines.append("")
            filtered_lines.append(stripped)
            last_idx = idx
            continue

        if context_budget > 0:
            if idx - last_idx > 1 and filtered_lines and filtered_lines[-1]:
                filtered_lines.append("")
            filtered_lines.append(stripped)
            context_budget -= 1
            last_idx = idx

    preview_text = "\n".join(filtered_lines).strip()
    preview_text = re.sub(r"\n{3,}", "\n\n", preview_text)

    if max_chars > 0 and len(preview_text) > max_chars:
        cutoff = preview_text.rfind("\n", 0, max_chars)
        if cutoff == -1 or cutoff < max_chars * 0.4:
            cutoff = max_chars
        preview_text = preview_text[:cutoff].rstrip() + "\n[quote snippet truncated]"

    return preview_text


def _quote_level(line: str) -> int:
    """🔽 Определяет уровень цитирования строки."""
    match = re.match(r"^(>+)", line)
    return len(match.group(1)) if match else 0


def _classify(text: str, sig_patterns: Sequence[str], disclaimer_patterns: Sequence[str]) -> str:
    """🏷️ Классифицирует блок текста."""
    lowered = text.strip().lower()

    if any(
        re.search(pattern, lowered, re.IGNORECASE | re.MULTILINE)
        for pattern in sig_patterns
    ):
        non_empty_lines = [line for line in text.splitlines() if line.strip()]
        if 1 <= len(non_empty_lines) <= 12:
            return "signature"

    if any(
        re.search(pattern, lowered, re.IGNORECASE | re.MULTILINE)
        for pattern in disclaimer_patterns
    ):
        return "disclaimer"

    if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in HEADER_SEPARATORS):
        return "header"

    if lowered.startswith(">") or (lowered.startswith("on ") and "wrote:" in lowered):
        return "quote"

    if re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", lowered) and (
        "пишет" in lowered or "writes" in lowered
    ):
        return "quote"

    return "body"


def _segment(text: str, sig_patterns: Sequence[str], disclaimer_patterns: Sequence[str]) -> List[Block]:
    """✂️ Разбивает письмо на последовательность блоков."""
    lines = text.splitlines()
    blocks: List[Block] = []
    buffer: List[str] = []
    level = 0

    def flush() -> None:
        nonlocal buffer, level
        if not buffer:
            return
        block_text = "\n".join(buffer).strip("\n")
        blocks.append(Block(block_text, level, _classify(block_text, sig_patterns, disclaimer_patterns)))
        buffer = []
        level = 0

    last_line_was_header = False

    for line in lines:
        new_level = _quote_level(line)
        normalized_line = line.strip()
        lowered_line = normalized_line.lower()

        current_is_header_line = any(
            re.search(pattern, lowered_line, re.IGNORECASE) for pattern in HEADER_SEPARATORS
        )

        is_signature_boundary = bool(
            buffer
            and any(re.search(pattern, lowered_line, re.IGNORECASE) for pattern in sig_patterns)
        )
        is_header_boundary = bool(buffer and current_is_header_line)
        is_signature_divider = bool(buffer and re.match(r"^\s*-{2,}\s*$", line))
        is_date_boundary = bool(
            buffer
            and re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", normalized_line)
        )

        if buffer and last_line_was_header and not current_is_header_line:
            flush()

        if buffer and (is_signature_boundary or is_header_boundary or is_signature_divider or is_date_boundary):
            flush()

        if buffer and (new_level != level or re.match(r"^\s*-{3,}\s*$", line)):
            flush()
        level = new_level
        buffer.append(line)
        last_line_was_header = current_is_header_line

    flush()
    return blocks


def preclean_email_for_llm(
    raw_text: str,
    thread_id: str,
    sender_email: str,
    config: Dict[str, object],
    caches: CacheProvider,
) -> PrecleanResult:
    """🧼 Выполняет предочистку письма перед передачей в LLM."""
    sig_patterns = _ensure_patterns(config.get("sig_markers"), DEFAULT_SIG_MARKERS)
    disclaimer_patterns = _ensure_patterns(config.get("disclaimer_markers"), DEFAULT_DISCLAIMER_MARKERS)

    blocks = _segment(raw_text, sig_patterns, disclaimer_patterns)
    cleaned_chunks: List[str] = []
    spans: List[Dict[str, str]] = []
    kept_signatures: Dict[str, int] = {}

    thread_cache = caches.get_thread_cache(thread_id)
    sender_cache = caches.get_sender_cache(sender_email)

    max_signature_lines = int(config.get("max_signature_lines", 5))
    fold_quote_over_chars = int(config.get("fold_quote_over_chars", 1200))
    max_disclaimer_lines = int(config.get("max_disclaimer_lines", 6))
    keep_first_signature = bool(config.get("keep_first_signature_per_sender", True))
    keep_first_disclaimer = bool(config.get("keep_first_disclaimer_per_thread", True))
    fold_on_repeat = bool(config.get("fold_on_repeat", True))

    quote_preview_head = int(config.get("quote_preview_non_empty_lines", 30))
    quote_preview_tail = int(config.get("quote_preview_tail_non_empty_lines", 12))
    header_markers = tuple(
        str(marker) for marker in config.get(
            "quote_preview_header_markers",
            ("from:", "to:", "subject:", "sent:", "cc:"),
        )
    )
    quote_preview_min_lines = int(config.get("quote_preview_min_lines", 6))
    quote_preview_context_lines = int(config.get("quote_preview_context_lines", 0))
    quote_preview_max_chars = int(config.get("quote_preview_max_chars", 600))
    quote_marker_terms = tuple(
        str(term).lower()
        for term in config.get(
            "quote_preview_markers",
            (" пишет", "wrote:", "forwarded message", "original message", "ответил", "написал"),
        )
    )
    for block in blocks:
        fingerprint = _fingerprint(block.text)

        if block.kind == "signature":
            seen_count = thread_cache.get(fingerprint, 0) + sender_cache.get(fingerprint, 0)
            current_level = block.quote_level
            first_level = kept_signatures.get(fingerprint)
            contains_contact = _contains_contact_info(block.text)
            prefer_keep_full = contains_contact and current_level > 0 and (first_level is None or current_level < first_level)
            should_keep = prefer_keep_full or first_level is None or current_level < first_level

            if should_keep:
                if keep_first_signature or prefer_keep_full:
                    cleaned_chunks.append(block.text.strip("\n"))
                else:
                    trimmed, truncated = _trim_non_empty(block.text.splitlines(), max_signature_lines)
                    if trimmed:
                        cleaned_chunks.append(trimmed)
                    if truncated:
                        marker = f"[signature truncated #{fingerprint}]"
                        spans.append({"placeholder": marker, "hash": fingerprint, "kind": "signature"})
                new_level = current_level if first_level is None else min(first_level, current_level)
                kept_signatures[fingerprint] = new_level
            else:
                if seen_count >= 1:
                    placeholder = f"[signature elided:{sender_email}#{fingerprint}]"
                    spans.append({"placeholder": placeholder, "hash": fingerprint, "kind": "signature"})
                    cleaned_chunks.append(placeholder)
                else:
                    if keep_first_signature:
                        cleaned_chunks.append(block.text.strip("\n"))
                    else:
                        trimmed, truncated = _trim_non_empty(block.text.splitlines(), max_signature_lines)
                        if trimmed:
                            cleaned_chunks.append(trimmed)
                        if truncated:
                            marker = f"[signature truncated #{fingerprint}]"
                            spans.append({"placeholder": marker, "hash": fingerprint, "kind": "signature"})
                    kept_signatures[fingerprint] = current_level
            thread_cache[fingerprint] = thread_cache.get(fingerprint, 0) + 1
            sender_cache[fingerprint] = sender_cache.get(fingerprint, 0) + 1
            continue

        if block.kind == "disclaimer":
            seen_count = thread_cache.get(fingerprint, 0) + sender_cache.get(fingerprint, 0)
            body_part, tail_info = _strip_disclaimer_tail(block.text, disclaimer_patterns)

            if body_part:
                cleaned_chunks.append(body_part.strip("\n"))

            if seen_count >= 1:
                placeholder = f"[disclaimer elided:{sender_email}#{fingerprint}]"
                spans.append({"placeholder": placeholder, "hash": fingerprint, "kind": "disclaimer"})
                cleaned_chunks.append(placeholder)
            else:
                if tail_info:
                    placeholder, hash_code = tail_info
                    spans.append({"placeholder": placeholder, "hash": hash_code, "kind": "disclaimer"})
                    cleaned_chunks.append(placeholder)
                else:
                    # fallback: обрезаем по количеству строк
                    trimmed, truncated = _trim_non_empty(block.text.splitlines(), max_disclaimer_lines)
                    if keep_first_disclaimer and trimmed:
                        cleaned_chunks.append(trimmed)
                    else:
                        placeholder = f"[disclaimer truncated #{fingerprint}]"
                        spans.append({"placeholder": placeholder, "hash": fingerprint, "kind": "disclaimer"})
                        cleaned_chunks.append(placeholder)
                    if truncated and keep_first_disclaimer:
                        marker = f"[disclaimer truncated #{fingerprint}]"
                        spans.append({"placeholder": marker, "hash": fingerprint, "kind": "disclaimer"})
                        cleaned_chunks.append(marker)
            thread_cache[fingerprint] = thread_cache.get(fingerprint, 0) + 1
            sender_cache[fingerprint] = sender_cache.get(fingerprint, 0) + 1
            continue

        if block.kind == "quote":
            is_repeat = thread_cache.get(fingerprint, 0) >= 1
            is_too_long = len(block.text) > fold_quote_over_chars
            quote_lines = block.text.splitlines()
            non_empty_in_quote = sum(1 for line in quote_lines if line.strip())
            lowered_quote = block.text.lower()
            has_marker = any(marker in lowered_quote for marker in quote_marker_terms)
            is_threaded_quote = has_marker or non_empty_in_quote >= quote_preview_min_lines
            contains_contact = bool(
                EMAIL_PATTERN.search(block.text)
                or PHONE_PATTERN.search(block.text)
                or URL_PATTERN.search(block.text)
                or INN_PATTERN.search(block.text)
            )
            if contains_contact and not is_repeat:
                cleaned_quote, disclaimer_info = _strip_disclaimer_tail(block.text, disclaimer_patterns)
                if cleaned_quote:
                    cleaned_chunks.append(cleaned_quote.strip("\n"))
                if disclaimer_info:
                    placeholder, hash_code = disclaimer_info
                    spans.append({"placeholder": placeholder, "hash": hash_code, "kind": "disclaimer"})
                    cleaned_chunks.append(placeholder)
                thread_cache[fingerprint] = 1
                continue
            should_fold = (fold_on_repeat and is_repeat) or is_too_long or is_threaded_quote
            if should_fold:
                preview = _prepare_quote_preview(
                    block.text,
                    head_non_empty=quote_preview_head,
                    tail_non_empty=quote_preview_tail,
                    header_markers=header_markers,
                    sig_patterns=sig_patterns,
                    context_lines=quote_preview_context_lines,
                    max_chars=quote_preview_max_chars,
                )
                if preview:
                    cleaned_chunks.append(preview)
                # Полностью удаляем повторяющиеся или длинные цитаты
                placeholder = f"[quoted message elided #{fingerprint}]"
                spans.append({"placeholder": placeholder, "hash": fingerprint, "kind": "quote"})
                cleaned_chunks.append(placeholder)
                thread_cache[fingerprint] = thread_cache.get(fingerprint, 0) + 1
                continue
            # Для коротких цитат - сохраняем как есть
            cleaned_chunks.append(block.text)
            thread_cache[fingerprint] = thread_cache.get(fingerprint, 0) + 1
            continue

        cleaned_chunks.append(block.text)
        thread_cache[fingerprint] = thread_cache.get(fingerprint, 0) + 1

    body_clean = "\n".join(cleaned_chunks).strip()
    return PrecleanResult(
        body_raw=raw_text,
        body_clean_llm=body_clean,
        clean_spans={"spans": spans},
        attachments_index=[],
    )
