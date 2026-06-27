import json
import re
import uuid
from pathlib import Path
from typing import Any

import fitz
import pytesseract
from PIL import Image

from .db import get_conn, utc_now
from .formula_parser import build_formula_dsl, extract_formula_candidates, parse_formula_candidate

DATA_DIR = Path("/app/data")
UPLOAD_DIR = DATA_DIR / "uploads"
ASSET_DIR = DATA_DIR / "assets"


def process_upload(file_bytes: bytes, filename: str) -> dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    suffix = Path(filename).suffix.lower() or ".bin"
    saved_path = UPLOAD_DIR / f"{doc_id}{suffix}"
    saved_path.write_bytes(file_bytes)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents(id,filename,file_type,page_count,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (doc_id, filename, suffix.lstrip("."), 0, "PROCESSING", utc_now(), utc_now()),
        )

    if suffix == ".pdf":
        page_count = _process_pdf(doc_id, saved_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        page_count = _process_image(doc_id, saved_path, 1)
    else:
        raise ValueError(f"unsupported file type: {suffix}")

    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET page_count=?, status='DONE', updated_at=? WHERE id=?",
            (page_count, utc_now(), doc_id),
        )
    return {"document_id": doc_id, "filename": filename, "page_count": page_count, "status": "DONE"}


def _process_pdf(doc_id: str, path: Path) -> int:
    pdf = fitz.open(str(path))
    with get_conn() as conn:
        for page_no, page in enumerate(pdf, start=1):
            text = page.get_text("text") or ""
            pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8))
            image_path = ASSET_DIR / f"{doc_id}_page_{page_no}.png"
            pix.save(str(image_path))
            if len(text.strip()) < 30:
                text = _ocr_image_text(image_path)
            _store_page_blocks(conn, doc_id, page_no, text)
            _extract_and_store_formulas(conn, doc_id, page_no, text, source_type="pdf_text")
    return len(pdf)


def _process_image(doc_id: str, path: Path, page_no: int) -> int:
    text = _ocr_image_text(path)
    with get_conn() as conn:
        _store_page_blocks(conn, doc_id, page_no, text)
        _extract_and_store_formulas(conn, doc_id, page_no, text, source_type="image_text_ocr")
    return 1


def _ocr_image_text(path: Path) -> str:
    try:
        img = Image.open(path).convert("RGB")
        return pytesseract.image_to_string(img, lang="eng+kor", config="--oem 3 --psm 6")
    except Exception as exc:
        return f"OCR_ERROR: {exc}"


def _store_page_blocks(conn, doc_id: str, page_no: int, text: str) -> None:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    seq = 1
    for para in paragraphs:
        conn.execute(
            """
            INSERT INTO page_content_blocks(document_id,page_no,block_seq,block_type,role,text_content,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (doc_id, page_no, seq, "text", "paragraph", _clean_text(para), utc_now()),
        )
        seq += 1


def _extract_and_store_formulas(conn, doc_id: str, page_no: int, text: str, source_type: str) -> None:
    candidates = extract_formula_candidates(text)
    base_seq = _next_block_seq(conn, doc_id, page_no)
    for idx, raw in enumerate(candidates, start=1):
        parsed = parse_formula_candidate(raw)
        dsl = build_formula_dsl(parsed)
        cur = conn.execute(
            """
            INSERT INTO formulas(document_id,page_no,formula_code,formula_name,latex,python_function,status,source_type,confidence,metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                doc_id,
                page_no,
                parsed.formula_code,
                parsed.formula_name,
                parsed.latex,
                parsed.python_function,
                parsed.status,
                source_type,
                parsed.confidence,
                json.dumps(dsl, ensure_ascii=False),
                utc_now(),
                utc_now(),
            ),
        )
        formula_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO page_content_blocks(document_id,page_no,block_seq,block_type,role,text_content,latex,metadata_json,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                doc_id,
                page_no,
                base_seq + idx - 1,
                "formula",
                "equation",
                raw,
                parsed.latex,
                json.dumps({"formula_id": formula_id, "formula_code": parsed.formula_code, "category": parsed.category, "confidence": parsed.confidence, "status": parsed.status}, ensure_ascii=False),
                utc_now(),
            ),
        )


def _next_block_seq(conn, doc_id: str, page_no: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(block_seq),0) + 1 AS next_seq FROM page_content_blocks WHERE document_id=? AND page_no=?",
        (doc_id, page_no),
    ).fetchone()
    return int(row["next_seq"])


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
