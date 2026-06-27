import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .actuarial.premium import calculate_from_csv
from .batch.run_premium_batch import run_batch
from .db import fetch_all, fetch_one, get_conn, init_db, insert_json_run, utc_now
from .formula_catalog import load_sample_formula_catalog
from .formula_parser import build_formula_dsl, get_formula_examples, parse_formula_candidate
from .formula_parser_examples import examples_as_dicts, find_examples
from .ocr_pipeline import process_upload

SAMPLE_DIR = Path(os.environ.get("SAMPLE_DATA_DIR", "/app/app/sample_data"))
LIFE_TABLE_PATH = SAMPLE_DIR / "life_table.csv"
POLICIES_PATH = SAMPLE_DIR / "policies.csv"
BATCH_OUTPUT = Path("/app/data/batch_result.csv")

app = FastAPI(title="OCR Life-Table Statistics API", version="0.1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PremiumRequest(BaseModel):
    age: int = Field(..., ge=0, le=120)
    term: int = Field(20, ge=1, le=120)
    sum_assured: float = Field(10000000, gt=0)
    interest_rate: float = Field(0.03, ge=0, le=0.2)
    product_type: str = Field("term_life")


class FormulaParseRequest(BaseModel):
    text: str = Field(..., min_length=1)


@app.on_event("startup")
def startup() -> None:
    init_db()
    load_sample_formula_catalog()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "OK", "service": "OCR Life-Table Statistics API"}


@app.get("/formulas")
def list_formulas() -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM formulas ORDER BY formula_code, id")


@app.get("/formula-parser/examples")
def formula_parser_examples(q: str = "") -> list[dict[str, Any]]:
    if q:
        return [item.__dict__ for item in find_examples(q)]
    return examples_as_dicts()


@app.get("/formula-parser/builtin-examples")
def formula_parser_builtin_examples() -> list[dict[str, Any]]:
    return get_formula_examples()


@app.post("/formula-parser/parse")
def formula_parser_parse(payload: FormulaParseRequest) -> dict[str, Any]:
    result = parse_formula_candidate(payload.text)
    return build_formula_dsl(result)


@app.get("/documents")
def list_documents() -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM documents ORDER BY created_at DESC")


@app.get("/documents/{document_id}/content")
def get_document_content(document_id: str) -> list[dict[str, Any]]:
    doc = fetch_one("SELECT id FROM documents WHERE id=?", (document_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return fetch_all(
        """
        SELECT page_no, block_seq, block_type, role, text_content, latex, metadata_json
        FROM page_content_blocks
        WHERE document_id=?
        ORDER BY page_no, block_seq
        """,
        (document_id,),
    )


@app.post("/ocr/upload")
async def upload_ocr(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    try:
        return process_upload(content, file.filename or "upload.bin")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/premium/calculate")
def premium_calculate(payload: PremiumRequest) -> dict[str, Any]:
    try:
        result = calculate_from_csv(LIFE_TABLE_PATH, payload.model_dump())
        run_id = insert_json_run("single", payload.model_dump(), result, "DONE")
        result["run_id"] = run_id
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch/run-sample")
def batch_run_sample() -> dict[str, Any]:
    try:
        df = run_batch(LIFE_TABLE_PATH, POLICIES_PATH, BATCH_OUTPUT)
        result = {
            "rows": len(df),
            "output": str(BATCH_OUTPUT),
            "preview": df.head(20).to_dict(orient="records"),
        }
        insert_json_run("batch_sample", {"policies": str(POLICIES_PATH)}, result, "DONE")
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/batch/runs")
def list_batch_runs() -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM premium_runs ORDER BY created_at DESC LIMIT 50")


@app.get("/admin/db/summary")
def db_summary() -> list[dict[str, Any]]:
    tables = fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    out = []
    with get_conn() as conn:
        for t in tables:
            name = t["name"]
            cnt = conn.execute(f'SELECT COUNT(*) AS cnt FROM "{name}"').fetchone()["cnt"]
            out.append({"table": name, "rows": cnt})
    return out
