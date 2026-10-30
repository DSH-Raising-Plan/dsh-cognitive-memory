# -*- coding: utf-8 -*-
"""运维 CLI：备份 / 恢复 / 迁移 / 健康检查。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_backup(args: argparse.Namespace) -> int:
    from mnemosyne.storage.backup import create_backup
    from mnemosyne.storage.paths import ensure_layout

    paths = ensure_layout(Path(args.data_dir).resolve() if args.data_dir else None)
    try:
        meta = create_backup(
            paths["db"],
            output_dir=Path(args.output).resolve() if args.output else None,
            label=args.label or "manual",
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(meta, ensure_ascii=False))
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    from mnemosyne.storage.backup import restore_backup
    from mnemosyne.storage.paths import ensure_layout

    paths = ensure_layout(Path(args.data_dir).resolve() if args.data_dir else None)
    try:
        result = restore_backup(
            Path(args.backup),
            db_path=paths["db"],
            force=bool(args.force),
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from mnemosyne.storage.backup import integrity_check
    from mnemosyne.storage.migrate_safe import preflight, validate_schema
    from mnemosyne.storage.paths import ensure_layout

    paths = ensure_layout(Path(args.data_dir).resolve() if args.data_dir else None)
    report = {
        "ok": True,
        "data_dir": str(paths["root"]),
        "db": str(paths["db"]),
        "preflight": preflight(paths["db"]),
        "integrity": integrity_check(paths["db"]) if paths["db"].is_file() else None,
        "validation": validate_schema(paths["db"]) if paths["db"].is_file() else None,
    }
    if report["preflight"] and not report["preflight"].get("ok"):
        report["ok"] = False
    if report["validation"] and not report["validation"].get("ok"):
        # pending on empty ok for doctor informational
        if report["validation"].get("pending_migrations"):
            report["ok"] = True
            report["note"] = "pending_migrations"
        elif report["validation"].get("missing_tables"):
            report["ok"] = False
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def cmd_health(args: argparse.Namespace) -> int:
    from mnemosyne.bootstrap import build_context

    ctx = build_context(
        data_dir=args.data_dir or None,
        token=args.token or "cli-health",
        acquire_lock=False,
        auto_backup_on_migrate=False,
    )
    print(json.dumps(ctx.service.health(), ensure_ascii=False, indent=2))
    ctx.db.close()
    return 0


def cmd_migrate_amem(args: argparse.Namespace) -> int:
    """从 A-MEM / JSONL 导入为 observations + candidate memories。"""
    from mnemosyne.bootstrap import build_context
    from mnemosyne.domain.models import (
        MemoryProposeIn,
        MemoryStatus,
        MemoryType,
        ObservationIn,
        SourceKind,
    )

    notes: list[dict] = []
    if args.jsonl:
        path = Path(args.jsonl)
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            notes.append(json.loads(line))
    else:
        try:
            root = Path(args.project_root or Path.cwd()).resolve()
            sys.path.insert(0, str(root))
            from Murasame.a_mem_bridge import get_a_mem_engine  # type: ignore
            from Murasame.utils import get_config  # type: ignore

            engine = get_a_mem_engine(get_config())
            if engine is None:
                print("A-MEM engine unavailable; pass --jsonl export", file=sys.stderr)
                return 2
            for mid, note in (engine.memories or {}).items():
                content = getattr(note, "content", None) or (note.get("content") if isinstance(note, dict) else "")
                tags = getattr(note, "tags", None) or (note.get("tags") if isinstance(note, dict) else [])
                notes.append({"id": str(mid), "content": str(content or ""), "tags": tags or []})
        except Exception as exc:
            print(f"cannot load A-MEM: {exc}", file=sys.stderr)
            return 2

    ctx = build_context(
        data_dir=args.data_dir or None,
        token=args.token or "cli-migrate",
        acquire_lock=False,
        auto_backup_on_migrate=False,
    )
    imported = 0
    skipped = 0
    for note in notes:
        content = str(note.get("content") or "").strip()
        if len(content) < 2:
            skipped += 1
            continue
        if args.dry_run:
            imported += 1
            continue
        obs = ctx.service.capture_observation(
            ObservationIn(
                source_kind=SourceKind.SYSTEM,
                content=content[:4000],
                producer="migrate.amem",
                metadata={"amem_id": note.get("id"), "tags": note.get("tags") or []},
                idempotency_key=f"amem:{note.get('id') or format(hash(content) & 0xFFFFFFFF, 'x')}",
            )
        )
        ctx.service.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.CANDIDATE,
                content=content[:2000],
                source_ids=[obs.id],
                metadata={"migrated_from": "a_mem", "tags": note.get("tags") or []},
                idempotency_key=f"amem-mem:{note.get('id') or obs.id}",
            )
        )
        imported += 1
    ctx.db.close()
    print(json.dumps({"ok": True, "imported": imported, "skipped": skipped, "dry_run": bool(args.dry_run)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mnemosyne")
    parser.add_argument("--data-dir", default="")
    parser.add_argument("--token", default="")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bak = sub.add_parser("backup", help="备份 memory.db（含 manifest）")
    p_bak.add_argument("-o", "--output", default="")
    p_bak.add_argument("--label", default="manual")
    p_bak.set_defaults(func=cmd_backup)

    p_res = sub.add_parser("restore", help="从备份恢复")
    p_res.add_argument("backup")
    p_res.add_argument("--force", action="store_true")
    p_res.set_defaults(func=cmd_restore)

    p_doc = sub.add_parser("doctor", help="预检 / 完整性 / 迁移状态（JSON）")
    p_doc.set_defaults(func=cmd_doctor)

    p_h = sub.add_parser("health", help="本地打开库并打印 health")
    p_h.set_defaults(func=cmd_health)

    p_m = sub.add_parser("migrate-amem", help="从 A-MEM 或 JSONL 导入")
    p_m.add_argument("--jsonl", default="")
    p_m.add_argument("--project-root", default="")
    p_m.add_argument("--dry-run", action="store_true")
    p_m.set_defaults(func=cmd_migrate_amem)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
