#!/usr/bin/env python3
"""
precleaner.cli — простой CLI для запуска:
- precleaner discover — вызвать discover_patterns.py
- precleaner run — применить пред-очистку к NDJSON
- precleaner eval — заглушка для сравнения метрик (вставьте свою логику)
"""
import argparse, json, sys
from pathlib import Path

from .core import preclean_email_for_llm, PrecleanResult
from . import core
# динамический импорт discover
def _discover_main(infile: str, outdir: str, limit: int):
    from importlib import import_module
    mod = import_module("discover_patterns")
    from pathlib import Path
    mod.discover_patterns(Path(infile), Path(outdir), limit)

class _MemCaches:
    def __init__(self): self.t = {}; self.s = {}
    def get_thread_cache(self, tid): return self.t.setdefault(tid, {})
    def get_sender_cache(self, em): return self.s.setdefault(em, {})

def cmd_run(args):
    cfg = {"max_signature_lines": 5, "fold_quote_over_chars": 1200}
    caches = _MemCaches()
    infile = Path(args.infile); outfile = Path(args.out)
    with infile.open(encoding="utf-8") as fin, outfile.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            res: PrecleanResult = preclean_email_for_llm(
                rec.get("body_text",""), rec.get("thread_id","unknown"), (rec.get("from") or "unknown").lower(), cfg, caches
            )
            rec["body_clean_llm"] = res.body_clean_llm
            rec["clean_spans"] = res.clean_spans
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"✅ precleaner run → {outfile}")

def cmd_discover(args):
    _discover_main(args.infile, args.out, args.limit)
    print("✅ discover done")

def cmd_eval(args):
    print("⚠ eval: заглушка. Подключите сравнение с эталоном (precision/recall/F1).")

def main():
    p = argparse.ArgumentParser(prog="precleaner")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Применить пред-очистку к NDJSON")
    p_run.add_argument("--infile", required=True)
    p_run.add_argument("--out", required=True)
    p_run.set_defaults(func=cmd_run)

    p_disc = sub.add_parser("discover", help="Выявить паттерны (частоты)")
    p_disc.add_argument("--infile", required=True)
    p_disc.add_argument("--out", required=True)
    p_disc.add_argument("--limit", type=int, default=0)
    p_disc.set_defaults(func=cmd_discover)

    p_eval = sub.add_parser("eval", help="Сравнить метрики (заглушка)")
    p_eval.add_argument("--gold", required=False)
    p_eval.add_argument("--pred", required=False)
    p_eval.set_defaults(func=cmd_eval)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
