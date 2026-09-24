"""Apply backend/migrations/*.sql in order over the Neon *direct* URL."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine  # noqa: E402

MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def main() -> None:
    engine = get_engine()
    if engine is None:
        sys.exit("DATABASE_URL is not set in backend/.env")

    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.name[:4].isdigit())
    if not files:
        sys.exit(f"No migration files in {MIGRATIONS_DIR}")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename text PRIMARY KEY,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )
        applied = {
            row[0]
            for row in conn.execute(text("SELECT filename FROM schema_migrations")).all()
        }
        for path in files:
            if path.name in applied:
                print(f"skip  {path.name}")
                continue
            print(f"apply {path.name}")
            for stmt in _statements(path.read_text()):
                conn.execute(text(stmt))
            conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:name)"),
                {"name": path.name},
            )
    print("migrations complete")


def _statements(script: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";")
            if stmt:
                parts.append(stmt)
            buf = []
    rest = "\n".join(buf).strip().rstrip(";")
    if rest:
        parts.append(rest)
    return parts


if __name__ == "__main__":
    main()
