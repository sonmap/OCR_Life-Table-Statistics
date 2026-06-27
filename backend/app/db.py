import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DB_PATH = os.environ.get("DB_PATH", "/app/data/app.db")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'UPLOADED',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS page_content_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                page_no INTEGER NOT NULL,
                block_seq INTEGER NOT NULL,
                block_type TEXT NOT NULL,
                role TEXT,
                text_content TEXT,
                latex TEXT,
                bbox_json TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS formulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                page_no INTEGER,
                formula_code TEXT,
                formula_name TEXT,
                latex TEXT NOT NULL,
                python_function TEXT,
                status TEXT NOT NULL DEFAULT 'NEEDS_REVIEW',
                source_type TEXT NOT NULL DEFAULT 'OCR',
                confidence REAL DEFAULT 0,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS premium_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT NOT NULL,
                input_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_blocks_doc_page ON page_content_blocks(document_id, page_no, block_seq);
            CREATE INDEX IF NOT EXISTS idx_formulas_code ON formulas(formula_code);
            CREATE INDEX IF NOT EXISTS idx_premium_runs_created ON premium_runs(created_at);
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for key in ["metadata_json", "input_json", "result_json", "bbox_json"]:
        if key in d and d[key]:
            try:
                d[key.replace("_json", "")] = json.loads(d[key])
            except Exception:
                d[key.replace("_json", "")] = d[key]
    return d


def fetch_all(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return [row_to_dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]


def fetch_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    with get_conn() as conn:
        return row_to_dict(conn.execute(sql, tuple(params)).fetchone())


def insert_json_run(run_type: str, input_obj: dict[str, Any], result_obj: dict[str, Any], status: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO premium_runs(run_type,input_json,result_json,status,created_at) VALUES(?,?,?,?,?)",
            (run_type, json.dumps(input_obj, ensure_ascii=False), json.dumps(result_obj, ensure_ascii=False), status, utc_now()),
        )
        return int(cur.lastrowid)
