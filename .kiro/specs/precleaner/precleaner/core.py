import re, hashlib, json
from dataclasses import dataclass
from typing import List, Dict

SIG_MARKERS = [r'--\s*$', r'—\s*$', r'с уважением[:,]?$', r'best regards[:,]?$', r'kind regards[:,]?$']
DISCLAIMER_MARKERS = [r'confidentiality notice', r'настоящее сообщение', r'unsubscribe', r'privacy policy']
HEADER_SEPARATORS = [r'^-+\s*original message\s*-+$', r'^on .* wrote:$', r'^(от|дата|кому|тема|from|date|to|subject):\s']

@dataclass
class Block:
    text: str
    quote_level: int
    kind: str = "unknown"  # body|signature|disclaimer|header|quote

@dataclass
class PrecleanResult:
    body_raw: str
    body_clean_llm: str
    clean_spans: dict
    attachments_index: list

def _fingerprint(text: str) -> str:
    t = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:12]

def _quote_level(line: str) -> int:
    m = re.match(r'^(>+)', line)
    return len(m.group(1)) if m else 0

def _classify(text: str) -> str:
    t = text.strip().lower()
    if any(re.search(p, t, re.I|re.M) for p in SIG_MARKERS):
        if 1 <= len([l for l in text.splitlines() if l.strip()]) <= 12:
            return "signature"
    if any(re.search(p, t, re.I|re.M) for p in DISCLAIMER_MARKERS): return "disclaimer"
    if any(re.search(p, t, re.I) for p in HEADER_SEPARATORS): return "header"
    if t.startswith('>') or (t.startswith('on ') and 'wrote:' in t): return "quote"
    return "body"

def _segment(text: str) -> List[Block]:
    lines = text.splitlines()
    blocks, buf, lvl = [], [], 0
    def flush():
        nonlocal buf, lvl, blocks
        if not buf: return
        btext = "\n".join(buf).strip("\n")
        blocks.append(Block(btext, lvl, _classify(btext)))
        buf, lvl = [], 0
    for line in lines:
        ql = _quote_level(line)
        if buf and (ql != lvl or re.match(r'^\s*-{3,}\s*$', line)): flush()
        lvl = ql; buf.append(line)
    flush(); return blocks

def preclean_email_for_llm(raw_text: str, thread_id: str, sender_email: str, config: Dict, caches) -> PrecleanResult:
    blocks = _segment(raw_text)
    out, spans = [], []
    tcache = caches.get_thread_cache(thread_id)
    scache = caches.get_sender_cache(sender_email)
    for b in blocks:
        h = _fingerprint(b.text)
        if b.kind in ("signature","disclaimer"):
            seen = tcache.get(h,0) + scache.get(h,0)
            if seen >= 1:
                ph = f"[{b.kind} elided:{sender_email}#{h}]"
                spans.append({"placeholder": ph, "hash": h, "kind": b.kind})
                out.append(ph)
            else:
                max_lines = config.get("max_signature_lines", 5)
                lines = b.text.splitlines()
                short = "\n".join(lines[:max_lines])
                if len(lines) > max_lines:
                    short += f"\n[{b.kind} truncated #{h}]"
                    spans.append({"placeholder": f"[{b.kind} truncated #{h}]", "hash": h, "kind": b.kind})
                out.append(short)
            tcache[h] = tcache.get(h,0)+1; scache[h] = scache.get(h,0)+1
            continue
        if b.kind == "quote":
            if tcache.get(h,0) >= 1 or len(b.text) > config.get("fold_quote_over_chars", 1200):
                ph = f"[quoted message elided #{h}]"
                spans.append({"placeholder": ph, "hash": h, "kind": "quote"})
                out.append(ph); tcache[h] = tcache.get(h,0)+1; continue
        out.append(b.text); tcache[h] = tcache.get(h,0)+1

    body_clean = "\n".join(out).strip()
    return PrecleanResult(body_raw=raw_text, body_clean_llm=body_clean, clean_spans={"spans": spans}, attachments_index=[])
