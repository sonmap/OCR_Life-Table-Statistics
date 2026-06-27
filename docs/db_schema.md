# DB Schema

## documents

업로드 문서 단위입니다.

| Column | 설명 |
|---|---|
| id | 문서 ID |
| filename | 원본 파일명 |
| file_type | pdf/png/jpg 등 |
| page_count | 페이지 수 |
| status | PROCESSING/DONE/ERROR |

## page_content_blocks

페이지 내 본문과 수식을 혼합 저장합니다.

| Column | 설명 |
|---|---|
| document_id | 문서 ID |
| page_no | 페이지 번호 |
| block_seq | 페이지 내 순서 |
| block_type | text/formula/table/image |
| role | paragraph/equation/caption |
| text_content | 본문 텍스트 또는 OCR 원문 |
| latex | 수식 LaTeX |
| metadata_json | OCR 후보 정보 |

## formulas

공식 카탈로그와 OCR 수식 후보를 저장합니다.

| Column | 설명 |
|---|---|
| formula_code | 공식 코드 |
| formula_name | 공식명 |
| latex | canonical LaTeX |
| python_function | 연결할 Python 함수명 |
| status | APPROVED/NEEDS_REVIEW/REJECTED |
| source_type | CATALOG/OCR |
| confidence | OCR 신뢰도 |

## premium_runs

단건/배치 보험료 산정 실행 이력입니다.

| Column | 설명 |
|---|---|
| run_type | single/batch_sample |
| input_json | 입력값 |
| result_json | 산출결과 |
| status | DONE/ERROR |
