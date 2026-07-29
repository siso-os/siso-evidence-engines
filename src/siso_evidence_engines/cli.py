from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import ingest_knowledge, propose_idea, propose_principle, rate_idea, rate_principle
from .store import Store


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="siso-evidence-engines")
    root.add_argument("--db", type=Path, default=Path("evidence-engines.db"))
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("ingest-knowledge", "propose-principles", "rate-principles", "propose-ideas", "rate-ideas"):
        command = commands.add_parser(name)
        command.add_argument("--json", type=Path, required=True)
    commands.add_parser("export")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    args.db.parent.mkdir(parents=True, exist_ok=True)
    store = Store(args.db)
    try:
        if args.command == "ingest-knowledge":
            result = ingest_knowledge(store, _load(args.json))
        elif args.command == "propose-principles":
            result = [propose_principle(store, item) for item in _load(args.json)]
        elif args.command == "rate-principles":
            result = [rate_principle(store, item) for item in _load(args.json)]
        elif args.command == "propose-ideas":
            result = [propose_idea(store, item) for item in _load(args.json)]
        elif args.command == "rate-ideas":
            result = [rate_idea(store, item) for item in _load(args.json)]
        else:
            print(store.export_json(), end="")
            return 0
        print(json.dumps(result, indent=2))
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
