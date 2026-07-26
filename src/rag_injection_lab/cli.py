"""CLI — UI launcher and headless ingest / ask / list (v0.1)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from rag_injection_lab import __version__
from rag_injection_lab.config import APP_HOST, APP_PORT, PROJECT_ROOT, ensure_runtime_dirs

_EPILOG = """
examples:
  rag-injection-lab ui
  rag-injection-lab ingest --name acme-clean
  rag-injection-lab ingest --name acme-poisoned --include-poisoned
  rag-injection-lab ask --corpus-id <id> -q "How many vacation days do I get?"
  rag-injection-lab list-corpora
  rag-injection-lab list-queries
  rag-injection-lab list-rules

security:
  Binds to 127.0.0.1 by default. No authentication.
  Poisoned docs are for lab demos only — do not deploy as production KB.
  See README.md and docs/design.md.
"""


def _cmd_ui(_: argparse.Namespace) -> int:
    ensure_runtime_dirs()
    home = PROJECT_ROOT / "app" / "Home.py"
    if not home.is_file():
        print(f"Streamlit entry not found: {home}", file=sys.stderr)
        return 1
    print(f"RAG Injection Lab v{__version__}")
    print(f"Starting UI at http://{APP_HOST}:{APP_PORT}")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(home),
        "--server.address",
        APP_HOST,
        "--server.port",
        str(APP_PORT),
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.call(cmd)


def _cmd_ingest(args: argparse.Namespace) -> int:
    ensure_runtime_dirs()
    from rag_injection_lab.services.ingest_service import build_corpus

    extra = [Path(p) for p in (args.path or [])]
    try:
        report = build_corpus(
            name=args.name,
            include_clean=not args.no_clean,
            include_poisoned=args.include_poisoned,
            extra_paths=extra or None,
            provider=args.provider,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"corpus_id:  {report.corpus_id}")
        print(f"docs:       {report.n_docs}")
        print(f"chunks:     {report.n_chunks}")
        print(f"embed:      {report.embed_model} ({report.provider})")
        for w in report.warnings:
            print(f"warning:    {w}", file=sys.stderr)
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    ensure_runtime_dirs()
    from rag_injection_lab.core.models import MitigationMode
    from rag_injection_lab.services.query_service import ask

    try:
        log = ask(
            args.corpus_id,
            args.question,
            top_k=args.top_k,
            provider=args.provider,
            run_detection=not args.no_detect,
            mitigation=MitigationMode(args.mitigation),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(log.to_dict(), indent=2))
    else:
        print(f"query_id:  {log.query_id}")
        print(f"verdict:   {log.overall_verdict}")
        print(f"provider:  {log.provider} / {log.chat_model}")
        print(f"latency:   {log.latency_ms} ms")
        if log.detection_hits:
            print("detections:")
            for h in log.detection_hits:
                print(f"  - [{h.get('severity')}] {h.get('rule_id')}: {h.get('message')}")
        print("--- answer ---")
        print(log.answer or log.error or "(empty)")
        if log.error:
            return 1
    return 0


def _cmd_list_corpora(args: argparse.Namespace) -> int:
    ensure_runtime_dirs()
    from rag_injection_lab.services.corpus_service import get_corpora

    rows = get_corpora()
    if args.json:
        print(json.dumps([c.to_dict() for c in rows], indent=2))
        return 0
    if not rows:
        print("(no corpora)")
        return 0
    for c in rows:
        poison = " +poisoned" if c.include_poisoned else ""
        print(
            f"{c.corpus_id}  docs={c.n_docs} chunks={c.n_chunks} "
            f"embed={c.embed_model}{poison}  {c.created_at}"
        )
    return 0


def _cmd_list_queries(args: argparse.Namespace) -> int:
    ensure_runtime_dirs()
    from rag_injection_lab.services.query_service import list_query_logs

    rows = list_query_logs(limit=args.limit)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("(no queries)")
        return 0
    for r in rows:
        print(
            f"{r.get('query_id')}  [{r.get('overall_verdict')}]  "
            f"{(r.get('question') or '')[:60]!r}  mit={r.get('mitigation_mode')}"
        )
    return 0


def _cmd_list_rules(_: argparse.Namespace) -> int:
    from rag_injection_lab.detect.registry import list_rules

    for r in list_rules():
        print(f"{r.rule_id:28}  {r.severity:8}  {r.title}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rag-injection-lab",
        description="RAG Injection Lab — baseline RAG + prompt-injection demos",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    ui = sub.add_parser("ui", help="Launch Streamlit UI")
    ui.set_defaults(func=_cmd_ui)

    ing = sub.add_parser("ingest", help="Build a corpus from data/kb (+ optional uploads)")
    ing.add_argument("--name", default="default", help="Corpus display name")
    ing.add_argument("--include-poisoned", action="store_true", help="Include data/kb/poisoned")
    ing.add_argument("--no-clean", action="store_true", help="Skip data/kb/clean")
    ing.add_argument("--path", action="append", help="Extra document path (repeatable)")
    ing.add_argument("--provider", default=None, help="openai|anthropic|mock")
    ing.add_argument("--json", action="store_true")
    ing.set_defaults(func=_cmd_ingest)

    ask_p = sub.add_parser("ask", help="Query a corpus")
    ask_p.add_argument("--corpus-id", required=True)
    ask_p.add_argument("-q", "--question", required=True)
    ask_p.add_argument("--top-k", type=int, default=None)
    ask_p.add_argument("--provider", default=None)
    ask_p.add_argument("--mitigation", default="none", choices=["none", "delimit", "sanitize", "quarantine"])
    ask_p.add_argument("--no-detect", action="store_true")
    ask_p.add_argument("--json", action="store_true")
    ask_p.set_defaults(func=_cmd_ask)

    lc = sub.add_parser("list-corpora", help="List built corpora")
    lc.add_argument("--json", action="store_true")
    lc.set_defaults(func=_cmd_list_corpora)

    lq = sub.add_parser("list-queries", help="List recent query logs")
    lq.add_argument("--limit", type=int, default=20)
    lq.add_argument("--json", action="store_true")
    lq.set_defaults(func=_cmd_list_queries)

    lr = sub.add_parser("list-rules", help="List detection rules")
    lr.set_defaults(func=_cmd_list_rules)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
