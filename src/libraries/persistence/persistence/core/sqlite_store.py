from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteStore:
    def __init__(self, path: str | Path):
        db_path = Path(path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")

    def _validate_table(self, table: str) -> None:
        if not _TABLE_NAME_RE.match(table):
            raise ValueError(
                f"Invalid table name: {table!r}. Use letters, numbers, and underscore only."
            )

    def _ensure_table(self, table: str) -> None:
        self._validate_table(table)
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL
            )
            """
        )

    def insert(self, table: str, data: dict[str, Any]) -> int:
        self._ensure_table(table)
        cur = self.conn.execute(
            f"INSERT INTO {table} (data) VALUES (?)",
            (json.dumps(data, ensure_ascii=False),),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get(self, table: str, **where: Any) -> dict[str, Any] | None:
        results = self.find(table, **where)
        return results[0] if results else None

    def find(self, table: str, **where: Any) -> list[dict[str, Any]]:
        self._ensure_table(table)

        if where:
            clauses: list[str] = []
            values: list[Any] = []
            for key, value in where.items():
                if key == "id":
                    clauses.append("id = ?")
                else:
                    clauses.append(f"json_extract(data, '$.{key}') = ?")
                values.append(value)

            query = f"SELECT id, data FROM {table} WHERE " + " AND ".join(clauses)
            rows = self.conn.execute(query, values).fetchall()
        else:
            rows = self.conn.execute(f"SELECT id, data FROM {table}").fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["data"])
            if isinstance(payload, dict):
                results.append({"id": int(row["id"]), **payload})
        return results

    def update(self, table: str, where: dict[str, Any], data: dict[str, Any]) -> int:
        rows = self.find(table, **where)

        count = 0
        for row in rows:
            row_id = row["id"]
            new_data = {k: v for k, v in row.items() if k != "id"}
            new_data.update(data)

            self.conn.execute(
                f"UPDATE {table} SET data = ? WHERE id = ?",
                (json.dumps(new_data, ensure_ascii=False), row_id),
            )
            count += 1

        self.conn.commit()
        return count

    def delete(self, table: str, **where: Any) -> int:
        rows = self.find(table, **where)

        for row in rows:
            self.conn.execute(f"DELETE FROM {table} WHERE id = ?", (row["id"],))

        self.conn.commit()
        return len(rows)

    def append(self, table: str, id: int, field: str, chunk: str) -> None:
        row = self.get(table, id=id)
        if not row:
            return

        row[field] = str(row.get(field, "")) + chunk
        row_id = row["id"]
        new_data = {k: v for k, v in row.items() if k != "id"}

        self.conn.execute(
            f"UPDATE {table} SET data = ? WHERE id = ?",
            (json.dumps(new_data, ensure_ascii=False), row_id),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
