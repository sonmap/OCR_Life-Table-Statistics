import json
import os
from pathlib import Path
from typing import Any

from .db import get_conn, utc_now
from .formula_parser import get_formula_examples

SAMPLE_DIR = Path(os.environ.get("SAMPLE_DATA_DIR", "/app/app/sample_data"))


def load_sample_formula_catalog() -> None:
    """Load both static JSON formulas and parser example formulas into DB."""
    formulas: list[dict[str, Any]] = []
    path = SAMPLE_DIR / "formula_catalog.json"
    if path.exists():
        formulas.extend(json.loads(path.read_text(encoding="utf-8")))

    # The parser contains a richer actuarial example library used for OCR classification.
    # Loading it into DB makes the Web formula catalog more useful.
    formulas.extend(get_formula_examples())

    with get_conn() as conn:
        for item in formulas:
            formula_code = item["formula_code"]
            exists = conn.execute(
                "SELECT id FROM formulas WHERE formula_code=? AND source_type='CATALOG'",
                (formula_code,),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO formulas(formula_code,formula_name,latex,python_function,status,source_type,confidence,metadata_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    formula_code,
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
