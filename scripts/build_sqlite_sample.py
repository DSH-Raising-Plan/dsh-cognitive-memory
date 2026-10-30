"""Build samples/providers/sqlite/sample.sqlite for MIM mapping demos."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "samples" / "providers" / "sqlite" / "sample.sqlite"


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(
        """
        CREATE TABLE memories (
          id INTEGER PRIMARY KEY,
          body TEXT NOT NULL,
          created_at TEXT NOT NULL,
          kind TEXT
        );
        CREATE TABLE links (
          from_id INTEGER NOT NULL,
          to_id INTEGER NOT NULL,
          rel TEXT NOT NULL
        );
        INSERT INTO memories VALUES
          (1, 'Prefers dark theme in admin UI.', '2026-03-05T10:00:00Z', 'fact'),
          (2, 'Finished Foundation 1.0 local smoke test.', '2026-03-11T16:20:00Z', 'episode');
        INSERT INTO links VALUES (2, 1, 'related_to');
        """
    )
    con.commit()
    con.close()
    print(f"wrote {DB}")


if __name__ == "__main__":
    main()
