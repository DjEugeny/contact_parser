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
from typing import Dict, Iterable, List, Protocol


SIG_MARKERS: Iterable[str] = (
    r"--\s*$",
    r"—\s*$",
    r"с уважением[:,]?$",
    r"best regards[:,]?$",
    r"kind regards[:,]?$",
)
DISCLAIMER_MARKERS: Iterable[str] = (
    r"confidentiality notice",
    r"настоящее сообщение",
    r"unsubscribe",
    r"privacy policy",
)
HEADER_SEPARATORS: Iterable[str] = (
    r"^-+\s*original message\s*-+$",
    r"^on .* wrote:$",
    r"^(от|дата|кому|тема|from|date|to|subject):\s",
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


def _quote_level(line: str) -> int:
    """🔽 Определяет уровень цитирования строки."""
    match = re.match(r"^(>+)", line)
    return len(match.group(1)) if match else 0


def _classify(text: str) -> str:
    """🏷️ Классифицирует блок текста."""
    lowered = text.strip().lower()

    if any(re.search(pattern, lowered, re.IGNORECASE | re.MULTILINE) for pattern in SIG_MARKERS):
        non_empty_lines = [line for line in text.splitlines() if line.strip()]
        if 1 <= len(non_empty_lines) <= 12:
            return "signature"

    if any(re.search(pattern, lowered, re.IGNORECASE | re.MULTILINE) for pattern in DISCLAIMER_MARKERS):
        return "disclaimer"

    if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in HEADER_SEPARATORS):
        return "header"

    if lowered.startswith(">") or (lowered.startswith("on ") and "wrote:" in lowered):
        return "quote"

    return "body"


def _segment(text: str) -> List[Block]:
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
        blocks.append(Block(block_text, level, _classify(block_text)))
        buffer = []
        level = 0

    for line in lines:
        new_level = _quote_level(line)
        if buffer and (new_level != level or re.match(r"^\s*-{3,}\s*$", line)):
            flush()
        level = new_level
        buffer.append(line)

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
    blocks = _segment(raw_text)
    cleaned_chunks: List[str] = []
    spans: List[Dict[str, str]] = []

    thread_cache = caches.get_thread_cache(thread_id)
    sender_cache = caches.get_sender_cache(sender_email)

    max_signature_lines = int(config.get("max_signature_lines", 5))
    fold_quote_over_chars = int(config.get("fold_quote_over_chars", 1200))

    for block in blocks:
        fingerprint = _fingerprint(block.text)

        if block.kind in ("signature", "disclaimer"):
            seen_count = thread_cache.get(fingerprint, 0) + sender_cache.get(fingerprint, 0)
            if seen_count >= 1:
                # Полностью удаляем повторяющиеся подписи/дисклеймеры
                placeholder = f"[{block.kind} elided:{sender_email}#{fingerprint}]"
                spans.append({"placeholder": placeholder, "hash": fingerprint, "kind": block.kind})
                cleaned_chunks.append(placeholder)
            else:
                # Для первого вхождения: обрезаем до max_signature_lines
                lines = block.text.splitlines()
                if len(lines) > max_signature_lines:
                    # Сохраняем только первые строки, остальное полностью удаляем
                    trimmed = "\n".join(lines[:max_signature_lines])
                    marker = f"[{block.kind} truncated #{fingerprint}]"
                    cleaned_chunks.append(trimmed)  # Убираем marker из контента!
                    spans.append({"placeholder": marker, "hash": fingerprint, "kind": block.kind})
                else:
                    # Короткие блоки сохраняем полностью
                    cleaned_chunks.append(block.text)
            thread_cache[fingerprint] = thread_cache.get(fingerprint, 0) + 1
            sender_cache[fingerprint] = sender_cache.get(fingerprint, 0) + 1
            continue

        if block.kind == "quote":
            if thread_cache.get(fingerprint, 0) >= 1 or len(block.text) > fold_quote_over_chars:
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
