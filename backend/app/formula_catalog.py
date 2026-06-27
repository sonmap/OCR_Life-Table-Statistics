import json
import os
from pathlib import Path

from .db import get_conn, utc_now

SAMPLE_DIR = Path(os.environ.get("SAMPLE_DATA_DIR", "/app/app/sample_data"))


def load_sample_formula_catalog() -> None:
    path = SAMPLE_DIR / "formula_catalog.json"
    if not path.exists():
        return
    formulas = json.loads(path.read_text(encoding="utf-8"))
    with get_conn() as conn:
        for item in formulas:
            exists = conn.execute(
                "SELECT id FROM formulas WHERE formula_code=? AND source_type='CATALOG'",
                (item["formula_code"],),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO formulas(formula_code,formula_name,latex,python_function,status,source_type,confidence,metadata_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    item["formula_code"],
                    item["formula_name"],
                    item["latex"],
                    item.get("python_function"),
                    item.get("status", "APPROVED"),
                    "CATALOG",
                    1.0,
                    json.dumps(item, ensure_ascii=False),
                    utc_now(),
                    utc_now(),
                ),
            )
