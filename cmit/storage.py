from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DB_PATH, SOURCE_DIR, ensure_runtime_dirs
from .importer import DATA_COLUMNS
from .shift import ShiftSpec, make_shift


def get_connection() -> sqlite3.Connection:
    ensure_runtime_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_date TEXT NOT NULL,
                shift_code TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(work_date, shift_code)
            );

            CREATE TABLE IF NOT EXISTS source_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );

            CREATE TABLE IF NOT EXISTS moves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                unit_nbr TEXT,
                move_kind TEXT,
                carrier_visit TEXT,
                ca TEXT,
                loai_ptvt TEXT,
                loai_cau_ben TEXT,
                sts_quay TEXT,
                time_sts_quay TEXT,
                gap_delay TEXT,
                reason TEXT,
                time_completed TEXT,
                put_che_name TEXT,
                time_of_fetch TEXT,
                fetch_che_name TEXT,
                carry_che_name TEXT,
                from_position TEXT,
                to_position TEXT,
                unit_type_iso TEXT,
                unit_vgm_verified TEXT,
                line_op TEXT,
                sts_yard TEXT,
                sts_yard_time TEXT,
                sts_carry TEXT,
                sts_carry_start_time TEXT,
                sts_carry_end_time TEXT,
                restow_reason TEXT,
                teu INTEGER,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );

            CREATE TABLE IF NOT EXISTS manual_inputs (
                shift_id INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );

            CREATE TABLE IF NOT EXISTS generated_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                email_subject TEXT NOT NULL,
                email_body TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            );

            CREATE TABLE IF NOT EXISTS personnel_names (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                UNIQUE(role, name)
            );
            """
        )


def upsert_shift(work_date: date, shift_code: str) -> int:
    shift = make_shift(work_date, shift_code)
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO shifts(work_date, shift_code, start_at, end_at, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'draft', ?, ?)
            ON CONFLICT(work_date, shift_code) DO UPDATE SET
                start_at=excluded.start_at,
                end_at=excluded.end_at,
                updated_at=excluded.updated_at
            """,
            (work_date.isoformat(), shift.code, shift.start.isoformat(), shift.end.isoformat(), now, now),
        )
        return int(conn.execute("SELECT id FROM shifts WHERE work_date=? AND shift_code=?", (work_date.isoformat(), shift.code)).fetchone()["id"])


def list_shifts() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM shifts ORDER BY work_date DESC, shift_code DESC").fetchall()
    return [dict(row) for row in rows]


def list_shift_summaries() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.*, COUNT(m.id) AS move_count
            FROM shifts s
            LEFT JOIN moves m ON m.shift_id = s.id
            GROUP BY s.id
            ORDER BY s.work_date DESC, s.shift_code DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_shift(shift_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM shifts WHERE id=?", (shift_id,)).fetchone()
    if row is None:
        raise ValueError(f"Shift not found: {shift_id}")
    return dict(row)


def get_shift_spec(shift_id: int) -> ShiftSpec:
    row = get_shift(shift_id)
    return make_shift(date.fromisoformat(row["work_date"]), row["shift_code"])


def save_source_file(shift_id: int, file_name: str, content: bytes) -> Path:
    shift = get_shift_spec(shift_id)
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in file_name)
    target = SOURCE_DIR / f"{shift.file_label}_{safe_name}"
    target.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO source_files(shift_id, file_name, file_path, checksum, imported_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (shift_id, file_name, str(target), checksum, now),
        )
    return target


def replace_moves(shift_id: int, moves: pd.DataFrame) -> None:
    db_df = _moves_to_db(moves)
    db_df.insert(0, "shift_id", shift_id)
    with get_connection() as conn:
        conn.execute("DELETE FROM moves WHERE shift_id=?", (shift_id,))
        db_df.to_sql("moves", conn, if_exists="append", index=False)


def load_moves(shift_id: int) -> pd.DataFrame:
    with get_connection() as conn:
        db_df = pd.read_sql_query("SELECT * FROM moves WHERE shift_id=? ORDER BY time_sts_quay", conn, params=(shift_id,))
    if db_df.empty:
        return pd.DataFrame(columns=DATA_COLUMNS)
    df = _db_to_moves(db_df)
    return df[DATA_COLUMNS]


def update_carrier_classifications(shift_id: int, rows: list[dict[str, Any]]) -> None:
    with get_connection() as conn:
        for row in rows:
            carrier = str(row.get("carrier_visit", "")).strip()
            if not carrier:
                continue
            conn.execute(
                """
                UPDATE moves
                SET loai_ptvt=?, loai_cau_ben=?
                WHERE shift_id=? AND carrier_visit=?
                """,
                (row.get("loai_ptvt", ""), row.get("loai_cau_ben", ""), shift_id, carrier),
            )


def get_manual_inputs(shift_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT payload_json FROM manual_inputs WHERE shift_id=?", (shift_id,)).fetchone()
    return default_manual_inputs() if row is None else _merge_defaults(json.loads(row["payload_json"]))


def save_manual_inputs(shift_id: int, payload: dict[str, Any]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO manual_inputs(shift_id, payload_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(shift_id) DO UPDATE SET
                payload_json=excluded.payload_json,
                updated_at=excluded.updated_at
            """,
            (shift_id, json.dumps(payload, ensure_ascii=False), now),
        )
    save_personnel_names_from_payload(payload)


def list_personnel_names(role: str | None = None) -> list[str]:
    query = "SELECT name FROM personnel_names"
    params: tuple[Any, ...] = ()
    if role:
        query += " WHERE role=?"
        params = (role,)
    query += " ORDER BY last_used_at DESC, name"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [str(row["name"]) for row in rows]


def save_personnel_names_from_payload(payload: dict[str, Any]) -> None:
    personnel = payload.get("personnel", {})
    role_map = {
        "shift_manager": "SHIFT MANAGER (SM)",
        "vessel_supervisors": "VESSEL SUPERVISORS",
        "yard_supervisors": "YARD SUPERVISORS",
    }
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        for field, role in role_map.items():
            for name in _split_names(personnel.get(field, "")):
                conn.execute(
                    """
                    INSERT INTO personnel_names(role, name, last_used_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(role, name) DO UPDATE SET last_used_at=excluded.last_used_at
                    """,
                    (role, name, now),
                )


def save_generated_report(shift_id: int, file_path: Path, email_subject: str, email_body: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generated_reports(shift_id, file_path, email_subject, email_body, generated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (shift_id, str(file_path), email_subject, email_body, now),
        )


def latest_generated_report(shift_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM generated_reports
            WHERE shift_id=?
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            (shift_id,),
        ).fetchone()
    return None if row is None else dict(row)


def default_manual_inputs() -> dict[str, Any]:
    return {
        "personnel": {
            "shift_manager": "",
            "vessel_supervisors": "",
            "yard_supervisors": "",
        },
        "gate": {
            "gate_in": 0,
            "gate_out": 0,
            "total": 0,
            "ttt": "",
            "single": "",
            "multiple": "",
            "queue_time": "",
            "in_gate_complete": "",
            "complete_outgate": "",
            "truck_turn_time": "",
        },
        "other": {
            "hk_moves": None,
            "vessel_sequence": "",
            "boe": "--",
            "incident": "NONE",
            "operation_notes": "Safe operation",
        },
        "che": {
            "demand": {"QC": 0, "RTG": 0, "UNI": 0, "EH": 0, "RS": 0, "TT": 0},
            "bd_time": {"QC": 0, "RTG": 0, "UNI": 0, "EH": 0, "RS": 0, "TT": 0},
            "notes": "",
        },
        "vessel_calls": [],
        "delays": [],
        "equipment_breakdowns": [],
    }


def _split_names(value: object) -> list[str]:
    text = str(value or "")
    names = []
    for chunk in text.replace(";", ",").split(","):
        name = " ".join(chunk.strip().split())
        if name:
            names.append(name)
    return names


def _merge_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    defaults = default_manual_inputs()
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            defaults[key].update(value)
        else:
            defaults[key] = value
    return defaults


def _moves_to_db(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    mapping = {
        "UNIT NBR": "unit_nbr",
        "MOVE KIND": "move_kind",
        "CARRIER VISIT": "carrier_visit",
        "CA": "ca",
        "LOAI PTVT": "loai_ptvt",
        "LOAI CAU BEN": "loai_cau_ben",
        "STS QUAY": "sts_quay",
        "TIME STS QUAY": "time_sts_quay",
        "GAP DELAY": "gap_delay",
        "REASON": "reason",
        "TIME COMPLETED": "time_completed",
        "PUT CHE NAME": "put_che_name",
        "TIME OF FETCH": "time_of_fetch",
        "FETCH CHE NAME": "fetch_che_name",
        "CARRY CHE NAME": "carry_che_name",
        "FROM POSITION": "from_position",
        "TO POSITION": "to_position",
        "UNIT TYPE ISO": "unit_type_iso",
        "UNIT VGM VERIFIED": "unit_vgm_verified",
        "LINE OP": "line_op",
        "STS YARD": "sts_yard",
        "STS YARD TIME": "sts_yard_time",
        "STS CARRY": "sts_carry",
        "STS CARRY START TIME": "sts_carry_start_time",
        "STS CARRY END TIME": "sts_carry_end_time",
        "RESTOW REASON": "restow_reason",
        "TEU": "teu",
    }
    for src, dst in mapping.items():
        out[dst] = df[src] if src in df.columns else None
    for col in ["time_sts_quay", "time_completed", "time_of_fetch", "sts_yard_time", "sts_carry_start_time", "sts_carry_end_time"]:
        out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
    out = out.where(pd.notna(out), None)
    return out


def _db_to_moves(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "unit_nbr": "UNIT NBR",
        "move_kind": "MOVE KIND",
        "carrier_visit": "CARRIER VISIT",
        "ca": "CA",
        "loai_ptvt": "LOAI PTVT",
        "loai_cau_ben": "LOAI CAU BEN",
        "sts_quay": "STS QUAY",
        "time_sts_quay": "TIME STS QUAY",
        "gap_delay": "GAP DELAY",
        "reason": "REASON",
        "time_completed": "TIME COMPLETED",
        "put_che_name": "PUT CHE NAME",
        "time_of_fetch": "TIME OF FETCH",
        "fetch_che_name": "FETCH CHE NAME",
        "carry_che_name": "CARRY CHE NAME",
        "from_position": "FROM POSITION",
        "to_position": "TO POSITION",
        "unit_type_iso": "UNIT TYPE ISO",
        "unit_vgm_verified": "UNIT VGM VERIFIED",
        "line_op": "LINE OP",
        "sts_yard": "STS YARD",
        "sts_yard_time": "STS YARD TIME",
        "sts_carry": "STS CARRY",
        "sts_carry_start_time": "STS CARRY START TIME",
        "sts_carry_end_time": "STS CARRY END TIME",
        "restow_reason": "RESTOW REASON",
        "teu": "TEU",
    }
    out = pd.DataFrame({dst: df[src] if src in df.columns else None for src, dst in mapping.items()})
    for col in ["TIME STS QUAY", "TIME COMPLETED", "TIME OF FETCH", "STS YARD TIME", "STS CARRY START TIME", "STS CARRY END TIME"]:
        out[col] = pd.to_datetime(out[col], errors="coerce")
    return out
