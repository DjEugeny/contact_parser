"""
discover_patterns.py — модуль для пакетного анализа e-mail за период (поиск паттернов сигнатур, дисклеймеров, цитат).
"""
import re
import csv
import json
import hashlib
from collections import defaultdict, Counter
from pathlib import Path

SIG_MARKERS = [r'--\s*$', r'—\s*$', r'с уважением[:,]?$', r'best regards[:,]?$', r'kind regards[:,]?$']
DISCLAIMER_MARKERS = [r'confidentiality notice', r'настоящее сообщение', r'unsubscribe', r'privacy policy']
HEADER_SEPARATORS = [r'^-+\s*original message\s*-+$', r'^on .* wrote:$', r'^(от|дата|кому|тема|from|date|to|subject):\s']

def fingerprint(text: str) -> str:
    t = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:12]

def classify(text: str) -> str:
    t = text.strip().lower()
    if any(re.search(p, t, re.I | re.M) for p in SIG_MARKERS):
        if 1 <= len([l for l in text.splitlines() if l.strip()]) <= 12:
            return "signature"
    if any(re.search(p, t, re.I | re.M) for p in DISCLAIMER_MARKERS):
        return "disclaimer"
    if any(re.search(p, t, re.I) for p in HEADER_SEPARATORS):
        return "header"
    if t.startswith('>') or (t.startswith('on ') and 'wrote:' in t):
        return "quote"
    return "body"

def segment(text: str):
    lines = text.splitlines()
    blocks, buf = [], []
    for line in lines:
        if re.match(r'^\s*-{3,}\s*$', line):
            if buf:
                blocks.append("\n".join(buf).strip())
                buf = []
            continue
        buf.append(line)
    if buf:
        blocks.append("\n".join(buf).strip())
    return blocks

def discover_patterns(input_path: Path, out_dir: Path, limit: int = 0):
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = defaultdict(lambda: defaultdict(int))
    samples = defaultdict(dict)

    with open(input_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            if limit and i >= limit:
                break
            email = json.loads(line)
            txt = email.get("body_text") or ""
            sender = (email.get("from") or "unknown").lower()
            thread = email.get("thread_id") or "unknown"
            domain = sender.split("@")[-1] if "@" in sender else "unknown"

            for b in segment(txt):
                kind = classify(b)
                h = fingerprint(b)
                stats[(domain, kind, h)]["count"] += 1
                if h not in samples[kind]:
                    samples[kind][h] = {"sample": b[:500], "domain": domain, "sender": sender}

    import csv as _csv
    for kind in ("signature","disclaimer","quote"):
        file_csv = out_dir / f"top_{kind}_patterns.csv"
        with open(file_csv, "w", newline="", encoding="utf-8") as cf:
            writer = _csv.writer(cf)
            writer.writerow(["hash","domain","count","sample"])
            agg = defaultdict(int)
            for (domain,k,h), cnt in stats.items():
                if k != kind: continue
                agg[(h,domain)] += cnt["count"]
            top = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:1000]
            for (h,domain), c in top:
                sample = samples[kind].get(h,{}).get("sample","").replace("\n"," ")[:250]
                writer.writerow([h, domain, c, sample])

    md_path = out_dir / "REPORT_PATTERNS.md"
    with open(md_path, "w", encoding="utf-8") as mf:
        mf.write("# Report: Frequent Patterns in Email Threads\n\n")
        for kind in ("signature","disclaimer","quote"):
            mf.write(f"## {kind.capitalize()}s\n\n")
            mf.write("| Hash | Domain | Count | Sample |\n|------|--------|-------|--------|\n")
            file_csv = out_dir / f"top_{kind}_patterns.csv"
            if file_csv.exists():
                with open(file_csv, encoding="utf-8") as cf:
                    next(cf, None)
                    for j, row in enumerate(_csv.reader(cf)):
                        if j > 20: break
                        h, domain, c, sample = row
                        mf.write(f"| `{h}` | {domain} | {c} | {sample[:80]}... |\n")
            mf.write("\n")
    print(f"✅ Patterns extracted → {out_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Discover repeated patterns in email dataset (NDJSON).")
    parser.add_argument("--infile", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    discover_patterns(Path(args.infile), Path(args.out), args.limit)
