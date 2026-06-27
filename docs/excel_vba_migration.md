# Excel/VBA 보험료 산정 로직 Python 전환 가이드

## 1. 왜 OCR 수식을 바로 실행하면 안 되는가

OCR 수식은 인식 오류, 줄바꿈 오류, 첨자 오류, 분수 구조 오류가 발생할 수 있습니다. 따라서 OCR로 얻은 LaTeX는 공식 관리와 화면 표시에는 좋지만, 실제 보험료 산정은 검증된 Python 함수로 구현해야 합니다.

```text
LaTeX 공식 = 표시 / 감사 / 문서화
Python 함수 = 실제 계산
Excel/VBA 결과 = 검증 기준값
```

## 2. 전환 순서

```text
1. Excel 파일 구조 분석
2. 입력 셀 / 출력 셀 / 중간계산 셀 정의
3. VBA 모듈 / Function / Sub 목록 추출
4. 기초율 테이블 분리
5. Python 데이터 모델 정의
6. 보험계리 함수 구현
7. Excel 결과와 Python 결과 비교
8. Batch 검증
9. API / Web / 운영 배포
```

## 3. 분석해야 할 Excel 구성

| 항목 | 설명 |
|---|---|
| 입력 시트 | 가입나이, 성별, 보험기간, 납입기간, 가입금액 |
| 기초율 시트 | 사망률, 해지율, 예정이율, 사업비율 |
| 계산 시트 | PV, 위험보험료, 저축보험료, 준비금 |
| 출력 시트 | 보험료, 준비금, 해지환급금 |
| VBA Module | 실제 계산 순서와 보정 로직 |
| Named Range | VBA에서 참조하는 셀 이름 |
| 반올림 규칙 | 원 단위, 10원 단위, 소수점 자리 |

## 4. Python 모듈 매핑 예시

| Excel/VBA | Python |
|---|---|
| 생명표 조회 | `life_table.py` |
| D_x, N_x, M_x 계산 | `commutation.py` |
| 순보험료 계산 | `premium.py` |
| 책임준비금 계산 | `reserve.py` |
| 대량 산정 | `batch/run_premium_batch.py` |
| 공식 관리 | `formula_catalog.py` |

## 5. 검증 기준

Excel VBA 결과를 기준값으로 삼고 Python 결과와 비교합니다.

```text
보험료 차이: 1원 이하
준비금 차이: 1원 이하
비율 차이: 0.000001 이하
```

## 6. Batch 검증 방식

`policies.csv` 또는 Excel 파일에 테스트 케이스를 넣습니다.

```text
policy_id, age, term, sum_assured, interest_rate, product_type, excel_premium
```

Batch 엔진은 Python 결과를 계산하고 `excel_premium`이 있으면 차이를 계산합니다.

## 7. 개발 주의사항

보험료 산정에서 차이가 많이 발생하는 지점은 다음입니다.

```text
1. 나이 계산 방식
2. 월납/연납 변환
3. 납입기간과 보험기간 경계
4. 반올림 위치
5. 위험률 적용 시점
6. 유지율/해지율 적용 시점
7. 최고연령 예외처리
8. 특약 조합 순서
9. Excel 숨은 시트/숨은 셀
10. VBA 임의 보정 로직
```
