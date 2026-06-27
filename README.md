# OCR Life-Table Statistics

보험계리 문서 OCR, 수식 저장, Excel/VBA 보험료 산정 로직의 Python 전환을 위한 샘플 플랫폼입니다.

이 저장소는 다음 목표를 가집니다.

```text
보험계리 문서 PDF/Image OCR
        ↓
본문 + 수식 LaTeX + 공식 카탈로그 DB 저장
        ↓
Excel/VBA 보험료 산정 로직을 Python 계산엔진으로 재구현
        ↓
Batch Engine으로 Excel/CSV 테스트케이스 대량 검증
        ↓
Web Frontend에서 OCR/공식/보험료 산출 결과 확인
```

---

## 1. 전체 구성

```text
.
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                      # FastAPI API 서버
│   │   ├── db.py                        # SQLite DB 초기화/조회
│   │   ├── ocr_pipeline.py              # PDF/Image OCR + 수식 후보 추출
│   │   ├── formula_repair.py            # 계리식 LaTeX 후처리
│   │   ├── formula_catalog.py           # LaTeX 공식과 Python 함수 매핑
│   │   ├── actuarial/
│   │   │   ├── life_table.py            # 생명표 로더
│   │   │   ├── commutation.py           # D_x, N_x, M_x 계산
│   │   │   ├── premium.py               # 보험료 계산
│   │   │   └── reserve.py               # 준비금 샘플 계산
│   │   ├── batch/
│   │   │   └── run_premium_batch.py     # Batch 산정/Excel 비교 엔진
│   │   └── sample_data/
│   │       ├── life_table.csv
│   │       ├── policies.csv
│   │       └── formula_catalog.json
│   │
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   └── app.js
│
├── docs/
│   ├── architecture.md
│   ├── excel_vba_migration.md
│   └── db_schema.md
│
├── scripts/
│   ├── run-local.sh
│   └── run-batch.sh
│
├── docker-compose.yml
└── .gitignore
```

---

## 2. 실행 방법

### Docker Compose 실행

```bash
cd OCR_Life-Table-Statistics

docker compose build
docker compose up -d
```

접속:

```text
Frontend: http://localhost:8080
Backend : http://localhost:8000/health
API Docs: http://localhost:8000/docs
```

---

## 3. 로컬 Python 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Batch 보험료 산정 실행

```bash
cd backend
python -m app.batch.run_premium_batch \
  --life-table app/sample_data/life_table.csv \
  --policies app/sample_data/policies.csv \
  --output /tmp/premium_result.csv
```

또는:

```bash
./scripts/run-batch.sh
```

---

## 5. 핵심 개념

### OCR 수식은 직접 실행하지 않는다

OCR로 얻은 LaTeX는 아래 용도로 사용합니다.

```text
1. 공식 원문 보관
2. 화면 수식 렌더링
3. 공식명 / 변수명 / 설명 관리
4. Python 함수와 매핑
5. 검증/승인 워크플로우
```

실제 보험료 산정은 Python 함수로 구현합니다.

```text
LaTeX = 표시 / 감사 / 공식 관리
Python function = 실제 계산 엔진
```

---

## 6. 샘플 공식 매핑

```json
{
  "formula_code": "WHOLE_LIFE_INSURANCE",
  "formula_name": "Whole life insurance net single premium",
  "latex": "A_x = M_x / D_x",
  "python_function": "whole_life_insurance",
  "status": "APPROVED"
}
```

---

## 7. 샘플 API

### Health Check

```bash
curl http://localhost:8000/health
```

### 공식 목록

```bash
curl http://localhost:8000/formulas
```

### 보험료 단건 산정

```bash
curl -X POST http://localhost:8000/premium/calculate \
  -H 'Content-Type: application/json' \
  -d '{
    "age": 40,
    "term": 20,
    "sum_assured": 10000000,
    "interest_rate": 0.03,
    "product_type": "term_life"
  }'
```

### 문서 OCR 업로드

```bash
curl -F "file=@sample.pdf" http://localhost:8000/ocr/upload
```

### Batch 실행

```bash
curl -X POST http://localhost:8000/batch/run-sample
```

---

## 8. Excel/VBA 전환 전략

```text
Excel/VBA 산정기
        ↓
입력/출력/중간계산값/기초율 분석
        ↓
Python actuarial engine 구현
        ↓
Excel 결과와 Python 결과 비교
        ↓
오차 기준 승인
        ↓
API / Batch / Web 화면 제공
```

자세한 내용은 `docs/excel_vba_migration.md`를 참고하세요.

---

## 9. 현재 샘플 범위

| 영역 | 포함 여부 |
|---|---|
| Frontend Web | 포함 |
| Backend FastAPI | 포함 |
| SQLite DB | 포함 |
| PDF/Image OCR 샘플 | 포함 |
| 수식 LaTeX 후처리 | 포함 |
| 공식 카탈로그 | 포함 |
| 생명표 CSV 로더 | 포함 |
| 통근함수 D/N/M 계산 | 포함 |
| 순보험료 샘플 계산 | 포함 |
| Batch 산정 엔진 | 포함 |
| Excel/VBA 전환 가이드 | 포함 |

---

## 10. 운영 확장 방향

```text
SQLite → PostgreSQL
CSV 생명표 → DB 기초율 관리
OCR 후보 → 승인 워크플로우
단일 상품 → 상품/특약 모델
Batch CSV → Excel/XLSX 대량 검증
로컬 Docker → Kubernetes / AKS
```
