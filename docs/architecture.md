# Architecture

이 샘플은 보험계리 문서 OCR과 Python 보험료 산정 엔진을 분리해서 설계합니다.

```text
Frontend Web
    ↓
FastAPI Backend
    ├─ OCR Pipeline
    │   ├─ PDF text extraction
    │   ├─ Image OCR
    │   ├─ Formula candidate extraction
    │   └─ LaTeX repair
    │
    ├─ Formula Catalog DB
    │   ├─ formula_code
    │   ├─ latex
    │   ├─ python_function
    │   └─ status
    │
    ├─ Actuarial Engine
    │   ├─ life_table.py
    │   ├─ commutation.py
    │   ├─ premium.py
    │   └─ reserve.py
    │
    └─ Batch Engine
        ├─ policies.csv / xlsx
        ├─ premium calculation
        └─ Excel result comparison
```

## 핵심 원칙

OCR 수식은 실제 실행 코드가 아니라 공식 관리 데이터입니다.

```text
OCR LaTeX = 공식 원문 / 화면 표시 / 감사 / 검증
Python Function = 실제 보험료 산정 로직
```

## DB 저장 구조

```text
documents
page_content_blocks
formulas
premium_runs
```

`page_content_blocks`는 본문과 수식을 같은 페이지 순서로 저장하기 위한 테이블입니다. `formulas`는 canonical LaTeX와 Python 함수 매핑을 저장합니다.

## 운영 확장

```text
SQLite → PostgreSQL
CSV 기초율 → DB 기초율 관리
단일 상품 → 상품/특약 모델
수식 OCR 후보 → 승인/반려 워크플로우
Batch CSV → Excel/XLSX 자동 비교
```
