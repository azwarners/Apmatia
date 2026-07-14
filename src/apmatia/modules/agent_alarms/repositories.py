from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from apmatia.lib.apmatia_core.models import utc_now

from .models import AlarmStatus, AgentAlarm


class AgentAlarmRepository(Protocol):
    def create(self, alarm: AgentAlarm) -> int:
        raise NotImplementedError

    def get(self, alarm_id: int) -> AgentAlarm | None:
        raise NotImplementedError

    def list_all(self) -> list[AgentAlarm]:
        raise NotImplementedError

    def update(self, alarm: AgentAlarm) -> None:
        raise NotImplementedError

    def delete(self, alarm_id: int) -> bool:
        raise NotImplementedError

    def list_due(self, now: datetime) -> list[AgentAlarm]:
        raise NotImplementedError

    def list_tracking(self) -> list[AgentAlarm]:
        raise NotImplementedError

    def claim_due_alarm(self, alarm_id: int, now: datetime) -> AgentAlarm | None:
        raise NotImplementedError


class SQLiteAgentAlarmRepository(AgentAlarmRepository):
    def __init__(self, path: str | Path):
        self._path = Path(path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def create(self, alarm: AgentAlarm) -> int:
        payload = self._serialize_alarm(alarm)
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO agent_alarms (data) VALUES (?)",
                (json.dumps(payload, ensure_ascii=False),),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def get(self, alarm_id: int) -> AgentAlarm | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, data FROM agent_alarms WHERE id = ?",
                (int(alarm_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_alarm(row)

    def list_all(self) -> list[AgentAlarm]:
        with self._lock:
            rows = self._conn.execute("SELECT id, data FROM agent_alarms").fetchall()
        alarms = [self._row_to_alarm(row) for row in rows]
        alarms.sort(key=lambda alarm: (alarm.scheduled_start_time, alarm.created_at, int(alarm.id or 0)))
        return alarms

    def update(self, alarm: AgentAlarm) -> None:
        if alarm.id is None:
            raise ValueError("Cannot update an alarm without an id.")
        payload = self._serialize_alarm(alarm)
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE agent_alarms SET data = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), int(alarm.id)),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Alarm not found: {alarm.id}")
            self._conn.commit()

    def delete(self, alarm_id: int) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM agent_alarms WHERE id = ?", (int(alarm_id),))
            self._conn.commit()
            return cursor.rowcount > 0

    def list_due(self, now: datetime) -> list[AgentAlarm]:
        alarms = [alarm for alarm in self.list_all() if alarm.enabled and alarm.status == AlarmStatus.SCHEDULED]
        return [alarm for alarm in alarms if alarm.scheduled_start_time <= now]

    def list_tracking(self) -> list[AgentAlarm]:
        return [alarm for alarm in self.list_all() if str(alarm.launched_loop_run_id or "").strip()]

    def claim_due_alarm(self, alarm_id: int, now: datetime) -> AgentAlarm | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, data FROM agent_alarms WHERE id = ?",
                (int(alarm_id),),
            ).fetchone()
            if row is None:
                return None
            alarm = self._row_to_alarm(row)
            if not alarm.enabled or alarm.status != AlarmStatus.SCHEDULED:
                return None
            if alarm.scheduled_start_time > now:
                return None

            claimed = replace(
                alarm,
                status=AlarmStatus.RUNNING,
                started_at=now,
                completed_at=None,
                launched_loop_run_id=None,
                last_result=None,
                last_error=None,
                updated_at=utc_now(),
            )
            self._conn.execute(
                "UPDATE agent_alarms SET data = ? WHERE id = ?",
                (json.dumps(self._serialize_alarm(claimed), ensure_ascii=False), int(alarm_id)),
            )
            self._conn.commit()
            return claimed

    @staticmethod
    def _serialize_alarm(alarm: AgentAlarm) -> dict[str, Any]:
        payload = alarm.to_dict()
        payload["status"] = alarm.status.value
        return payload

    @staticmethod
    def _row_to_alarm(row: sqlite3.Row) -> AgentAlarm:
        payload = json.loads(row["data"])
        if not isinstance(payload, dict):
            raise ValueError("Alarm payload must be a mapping.")
        payload["id"] = int(row["id"])
        return AgentAlarm.from_dict(payload)
