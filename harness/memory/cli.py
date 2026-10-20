#!/usr/bin/env python3
"""Ultron V0.6: local, user-approved SQLite memory. No external dependencies."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import uuid
from pathlib import Path

CATEGORIES = ("preference", "profile", "project", "workflow", "other")
SCOPES = ("global", "workspace")
RISK = re.compile(r"(?i)(sk-(?:proj-|svcacct-|[a-z0-9]{16})|(?:api[_ -]?key|password|passwd|access[_ -]?token|private[_ -]?key)\s*[:=])")
MAX_LENGTH = 2000


def home() -> Path:
    root = Path(os.environ.get("DSH_HOME") or Path.home() / ".ultron-dsh").expanduser().resolve()
    return root / "memory"


def database_path() -> Path:
    path = home()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path / "ultron.sqlite3"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    path = database_path()
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS memories(
        id TEXT PRIMARY KEY, body TEXT NOT NULL, category TEXT NOT NULL,
        scope TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS proposals(
        id TEXT PRIMARY KEY, action TEXT NOT NULL, target_id TEXT,
        body TEXT, category TEXT, scope TEXT, source TEXT,
        status TEXT NOT NULL, created_at TEXT NOT NULL,
        decided_at TEXT
      );
      CREATE INDEX IF NOT EXISTS proposals_status ON proposals(status);
    """)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return conn


def short_id() -> str:
    return uuid.uuid4().hex[:12]


def as_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def validate_body(text: str) -> str:
    text = text.strip()
    if not text or len(text) > MAX_LENGTH:
        raise ValueError(f"Memory text must be 1-{MAX_LENGTH} characters.")
    if RISK.search(text):
        raise ValueError("Possible credential or secret detected; memory write refused.")
    return text


def propose(args, conn):
    action = args.action
    target = args.id if action != "add" else None
    existing = None
    if target:
        existing = conn.execute("SELECT * FROM memories WHERE id=?", (target,)).fetchone()
        if existing is None:
            raise ValueError("Target approved memory does not exist.")
    body = validate_body(args.text) if action in ("add", "update") else None
    category = args.category if action == "add" else (existing["category"] if existing else None)
    scope = args.scope if action == "add" else (existing["scope"] if existing else None)
    source = args.source if action == "add" else (existing["source"] if existing else None)
    pid = short_id()
    with conn:
        conn.execute(
          "INSERT INTO proposals VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, NULL)",
          (pid, action, target, body, category, scope, source, now()),
        )
    print_json({"proposal_id": pid, "action": action, "target_id": target,
                "body": body, "status": "pending", "requires_explicit_approval": True})


def decide(args, conn, approve: bool):
    with conn:
        p = conn.execute("SELECT * FROM proposals WHERE id=?", (args.proposal_id,)).fetchone()
        if p is None or p["status"] != "pending":
            raise ValueError("Proposal does not exist or is no longer pending.")
        if approve:
            if p["action"] == "add":
                conn.execute(
                    "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (short_id(), p["body"], p["category"], p["scope"],
                     p["source"], now(), now()),
                )
            elif p["action"] == "update":
                c = conn.execute("UPDATE memories SET body=?,updated_at=? WHERE id=?",
                                 (p["body"], now(), p["target_id"]))
                if c.rowcount != 1:
                    raise ValueError("Target memory not found; cannot approve update.")
            elif p["action"] == "forget":
                c = conn.execute("DELETE FROM memories WHERE id=?", (p["target_id"],))
                if c.rowcount != 1:
                    raise ValueError("Target memory not found; cannot approve deletion.")
            else:
                raise ValueError("Unrecognized proposal action.")
        conn.execute("UPDATE proposals SET status=?, decided_at=? WHERE id=?",
                     ("approved" if approve else "rejected", now(), args.proposal_id))
    print_json({"proposal_id": args.proposal_id, "status": "approved" if approve else "rejected"})


def list_memories(args, conn):
    rows = conn.execute(
        "SELECT id,body,category,scope,source,created_at,updated_at FROM memories "
        "WHERE (? IS NULL OR scope=?) ORDER BY updated_at DESC LIMIT ?",
        (args.scope, args.scope, args.limit),
    ).fetchall()
    print_json([as_dict(r) for r in rows])


def list_proposals(args, conn):
    rows = conn.execute(
        "SELECT * FROM proposals WHERE status=? ORDER BY created_at DESC LIMIT ?",
        (args.status, args.limit),
    ).fetchall()
    print_json([as_dict(r) for r in rows])


def search(args, conn):
    terms = [s.casefold() for s in re.findall(r"[\w-]+", args.query) if s]
    if not terms:
        print_json([])
        return
    rows = conn.execute("SELECT * FROM memories WHERE (? IS NULL OR scope=?)",
                        (args.scope, args.scope)).fetchall()
    ranked = []
    for row in rows:
        body = row["body"].casefold()
        hits = sum(body.count(term) for term in terms)
        if hits:
            ranked.append((hits, row["updated_at"], as_dict(row)))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print_json([r[2] for r in ranked[:args.limit]])


def export_data(args, conn):
    rows = conn.execute(
        "SELECT id,body,category,scope,source,created_at,updated_at FROM memories "
        "ORDER BY created_at"
    ).fetchall()
    print_json({"schema": "ultron-memory-v0.6", "exported_at": now(),
                "memories": [as_dict(r) for r in rows]})


def main():
    parser = argparse.ArgumentParser(description="Ultron SQLite Memory Engine V0.6")
    sub = parser.add_subparsers(dest="command", required=True)
    pp = sub.add_parser("propose", help="Stage add/update/forget; no immediate mutation")
    pp.add_argument("--action", choices=("add", "update", "forget"), default="add")
    pp.add_argument("--id", help="Required for update/forget: approved memory ID")
    pp.add_argument("--text", help="Required for add/update")
    pp.add_argument("--category", choices=CATEGORIES, default="preference")
    pp.add_argument("--scope", choices=SCOPES, default="global")
    pp.add_argument("--source", default="explicit user statement")
    for command in ("approve", "reject"):
        p = sub.add_parser(command)
        p.add_argument("--proposal-id", required=True)
    lp = sub.add_parser("list")
    lp.add_argument("--scope", choices=SCOPES)
    lp.add_argument("--limit", type=int, default=30)
    qp = sub.add_parser("proposals")
    qp.add_argument("--status", choices=("pending", "approved", "rejected"), default="pending")
    qp.add_argument("--limit", type=int, default=30)
    sp = sub.add_parser("search")
    sp.add_argument("query")
    sp.add_argument("--scope", choices=SCOPES)
    sp.add_argument("--limit", type=int, default=10)
    sub.add_parser("export")
    args = parser.parse_args()
    try:
        if hasattr(args, "limit") and not 1 <= args.limit <= 100:
            raise ValueError("limit must be 1-100")
        if args.command == "propose":
            if args.action != "add" and not args.id:
                raise ValueError("--id required for update/forget")
            if args.action in ("add", "update") and args.text is None:
                raise ValueError("--text required for add/update")
        with connect() as conn:
            if args.command == "propose":
                propose(args, conn)
            elif args.command in ("approve", "reject"):
                decide(args, conn, args.command == "approve")
            elif args.command == "list":
                list_memories(args, conn)
            elif args.command == "proposals":
                list_proposals(args, conn)
            elif args.command == "search":
                search(args, conn)
            else:
                export_data(args, conn)
    except (ValueError, sqlite3.Error, OSError) as exc:
        print_json({"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
