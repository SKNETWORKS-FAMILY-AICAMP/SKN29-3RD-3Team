# 청약 가점 계산기 MCP Tool API 명세

작성일: 2026-06-13

## 1. 목적

`calculate_housing_subscription_score`는 LangGraph NODE2에서 호출할 수 있는 deterministic 청약 가점 계산 도구다.

이 도구는 일반공급 가점제 점수를 계산한다. Vector DB 검색, RAG 답변 생성, FastAPI endpoint 제공은 이 문서의 범위가 아니다.

## 2. 기준 자료

1차 기준은 다음 로컬 스냅샷이다.

```text
external shared snapshot: housing_supply_rule_appendix_1_20251031.pdf
```

The PDF snapshot is not committed to Git. Use `manifest.json` and SHA256 to verify
that the external shared PDF is the same source used to derive the structured table.

관련 manifest:

```text
data/raw/official/manifest.json
```

구조화 점수표:

```text
data/processed/structured/housing_subscription_score_tables.json
```

기준 조항:

- `주택공급에 관한 규칙 [별표 1] 가점제 적용기준(제2조제8호 관련)`
- PDF SHA256: `3E0E31A3B38A5259F4750119D351699AECC12918778B3B8ECB091DC9689916DE`

## 3. Tool Summary

```text
tool name: calculate_housing_subscription_score
python function: src.engine.tools.calculator.housing_subscription_score.calculate_housing_subscription_score
tool adapter: src.engine.tools.housing_subscription_score_tool.get_housing_subscription_score_structured_tool
```

이 도구는 `StructuredTool` 어댑터를 제공하지만, LangChain이 없는 환경에서도 순수 Python 함수는 사용할 수 있다.

## 4. Request Schema

```json
{
  "birth_date": "1990-01-01",
  "is_married": true,
  "marriage_date": "2015-01-01",
  "homeless_start_date": null,
  "dependent_family_count": 3,
  "subscription_join_date": "2011-01-01",
  "announcement_date": "2026-01-01",
  "spouse_subscription_join_date": "2016-01-01",
  "include_spouse_subscription_score": true
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `birth_date` | date | yes | 신청자 생년월일 |
| `is_married` | boolean | no | 혼인 여부 |
| `marriage_date` | date/null | no | 혼인신고일 |
| `homeless_start_date` | date/null | no | 계속 무주택자가 된 것으로 확인된 날짜 |
| `dependent_family_count` | integer | yes | 신청자 본인을 제외한 부양가족 수 |
| `subscription_join_date` | date | yes | 신청자 주택청약종합저축 가입일 |
| `announcement_date` | date | no | 입주자모집공고일. 미입력 시 실행일을 사용 |
| `spouse_subscription_join_date` | date/null | no | 배우자 주택청약종합저축 가입일 |
| `include_spouse_subscription_score` | boolean | no | 배우자 가입기간 합산 여부 |

## 5. Response Schema

```json
{
  "homeless_period_years": 11,
  "homeless_score": 24,
  "dependent_family_score": 20,
  "subscription_period_years": 15,
  "subscription_score": 17,
  "spouse_subscription_score": 3,
  "total_score": 61,
  "warnings": [],
  "assumptions": [
    "announcement_date is used as the legal calculation basis.",
    "dependent_family_count is assumed to be pre-validated under Appendix 1 dependent-family rules.",
    "Marriage registration date was used because marriage occurred before age 30.",
    "spouse_subscription_score uses half of spouse subscription period, capped at 3 points and total subscription score capped at 17."
  ],
  "need_review": false,
  "source_refs": [
    "housing_supply_rule_appendix_1_20251031:[별표 1] 가점제 적용기준(제2조제8호 관련)"
  ]
}
```

| Field | Description |
| --- | --- |
| `homeless_period_years` | 산정된 만 무주택기간 |
| `homeless_score` | 무주택기간 점수, 최대 32점 |
| `dependent_family_score` | 부양가족 수 점수, 최대 35점 |
| `subscription_period_years` | 신청자 청약통장 만 가입연수 |
| `subscription_score` | 신청자 점수와 배우자 합산 점수를 반영한 청약통장 가입기간 점수, 최대 17점 |
| `spouse_subscription_score` | 배우자 가입기간 합산 점수, 최대 3점 |
| `total_score` | 총점, 최대 84점 |
| `warnings` | 계산은 했지만 주의가 필요한 항목 |
| `assumptions` | 계산에 적용한 가정 |
| `need_review` | 공고문, 처분일, 세대원 요건 등 추가 확인 필요 여부 |
| `source_refs` | 구조화 점수표의 원천 참조 |

## 6. Calculation Policy

- 기준일은 `announcement_date`다.
- 무주택기간은 기본적으로 신청자가 만 30세가 되는 날부터 계산한다.
- 만 30세 전에 혼인한 경우 혼인신고일부터 계산한다.
- `homeless_start_date`가 있으면 법령상 기산 후보보다 늦은 날짜를 사용한다.
- 미혼이고 `announcement_date` 기준 만 30세 미만이면 무주택기간 점수는 0점이다.
- 부양가족 수는 이미 별표 1의 부양가족 인정 기준을 통과한 값이라고 가정한다.
- 배우자 가입기간 합산은 배우자 가입기간의 50% 해당 점수를 더하되, 배우자 점수는 최대 3점이고 청약통장 가입기간 총점은 17점을 넘지 않는다.
- 전체 총점은 84점을 넘지 않는다.

## 7. Validation And Review Policy

Pydantic validation error:

- `birth_date`가 `announcement_date`보다 늦은 경우
- `marriage_date`, `homeless_start_date`, `subscription_join_date`, `spouse_subscription_join_date`가 `announcement_date`보다 늦은 경우
- `dependent_family_count`가 음수인 경우
- 정의되지 않은 extra field가 들어온 경우

`need_review=true`:

- `is_married=true`지만 `marriage_date`가 없는 경우
- `homeless_start_date`를 입력해 과거 주택 소유/처분 이후 무주택 기산일로 사용한 경우
- 배우자 합산을 요청했지만 `spouse_subscription_join_date`가 없는 경우

## 8. Existing DiagnoseResponse Mapping

The calculator output should not add new fields to the existing FastAPI
`DiagnoseResponse` schema. If the backend wants to expose this score through the
current diagnosis response, wrap the score result as a `SupplyDiagnosis`-shaped
payload and merge only existing response keys.

Adapter:

```python
from src.engine.tools.calculator.housing_subscription_score_response_adapter import (
    build_general_score_diagnose_response_fragment,
    build_general_score_supply_diagnosis,
)
from src.engine.tools.calculator.housing_subscription_score_partial_adapter import (
    build_partial_general_score_diagnose_response_fragment,
)
```

`build_general_score_supply_diagnosis(score)` returns exactly these existing
`SupplyDiagnosis` keys:

```text
supply_type
status
reasons
missing_checks
next_questions
source_refs
```

`build_general_score_diagnose_response_fragment(score)` returns only fields that
already exist on `DiagnoseResponse`:

```text
result_status
candidate_supply_types
missing_inputs
next_questions
warnings
```

Mapping policy:

- `need_review=false` maps to `status="가능성 있음"`.
- `need_review=true` maps to `status="추가 확인 필요"`.
- Score details are formatted into `reasons`.
- Review warnings are copied to `warnings` and, when possible, mapped to
  existing `missing_inputs` / `next_questions`.
- No FastAPI schema change is required.

### Partial Calculation Mode

If the current user payload does not contain every field needed for exact scoring,
use `build_partial_general_score_diagnose_response_fragment(input_data)`.

Partial mode policy:

- It uses the same score tables and category scoring rules as the exact calculator.
- Unknown values are not treated as `0`.
- Only categories that can be calculated from current inputs are included in the
  calculable score.
- The result must be presented as a reference score, not a final 84-point total.
- `result_status` is `추가 확인 필요`.
- Missing values are returned through existing `missing_inputs` and
  `next_questions`.
- The warning must tell the user that omitted fields were excluded and that the
  actual subscription score can differ.

Recommended user-facing wording:

```text
현재 입력값만으로 계산 가능한 항목 기준의 참고 점수입니다.
다음 항목이 누락되어 실제 청약 가점 총점과 다를 수 있습니다: {missing_inputs}.
누락된 항목은 점수에 포함하지 않았으며, 정확한 총점 계산을 위해 추가 입력이 필요합니다.
```

Examples of non-inferable fields:

- `birth_year` is not automatically converted to `birth_date`.
- `num_household_members` is not automatically converted to
  `dependent_family_count`.
- `homeless_period_years` can be used as an applicant-supplied reference value,
  but it is still not the same as verifying `birth_date`, `marriage_date`,
  `homeless_start_date`, and `announcement_date`.
- `bankbook_joined_months` can be used as a reference subscription period, but
  exact scoring should prefer `subscription_join_date` plus `announcement_date`.

## 9. NODE2 연결 예시

현재 구현은 기존 `src/graph/graph.py`를 수정하지 않는다. NODE2에서 연결할 때는 아래처럼 import해서 사용한다.

```python
from src.engine.tools.calculator.housing_subscription_score import calculate_housing_subscription_score


score = calculate_housing_subscription_score(
    {
        "birth_date": "1990-01-01",
        "is_married": True,
        "marriage_date": "2015-01-01",
        "homeless_start_date": None,
        "dependent_family_count": 3,
        "subscription_join_date": "2011-01-01",
        "announcement_date": "2026-01-01",
        "spouse_subscription_join_date": "2016-01-01",
        "include_spouse_subscription_score": True,
    }
)
```

LangChain `StructuredTool`이 필요한 경우:

```python
from src.engine.tools.housing_subscription_score_tool import (
    get_housing_subscription_score_structured_tool,
)


tool = get_housing_subscription_score_structured_tool()
```

## 10. Non-goals

- FastAPI endpoint 추가 없음
- Streamlit payload 변경 없음
- Vector DB 조회 없음
- 특별공급 자격조건, 재당첨 제한, 무주택 판정 기준, 지역 우선공급 기준 판정 없음
