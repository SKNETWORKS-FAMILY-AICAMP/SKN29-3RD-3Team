# Streamlit Frontend API Integration Spec

작성일: 2026-06-12

이 문서는 현재 `은진` 브랜치의 Streamlit 프론트 구현 상태와,
원격 FastAPI 서버(`http://192.168.0.27:8000`) 기준 API 요구사항을 함께 정리한 명세입니다.

기존 `docs/API_SPEC.md`는 초기 계약 문서로 유지하고, 이 문서는 현재 프론트 연동 기준의 실행 명세로 사용합니다.

## 1. 현재 구현 상태

| 영역 | 상태 | 구현 위치 |
| --- | --- | --- |
| Streamlit 진입점 | 구현 완료 | `frontend/streamlit_app.py` |
| 자가진단 단계형 입력 UI | 구현 완료 | `frontend/views/diagnosis_steps.py`, `frontend/views/diagnosis_page.py` |
| 사용자 입력 -> profile API payload 변환 | 구현 완료 | `frontend/services/payload.py` |
| FastAPI profile 호출 | 구현 완료 | `frontend/services/api_client.py` |
| FastAPI detail 호출 | 구현 완료 | `frontend/services/api_client.py` |
| API auto 연결 및 mock fallback | 구현 완료 | `frontend/config/settings.py`, `frontend/views/diagnosis_result.py`, `frontend/views/chatbot_panel.py` |
| 결과 렌더링 | 구현 완료 | `frontend/components/ui.py`, `frontend/views/diagnosis_result.py` |
| `next_questions` 기반 추가 질문 UI | 일부 구현 | 지원 가능한 detail 필드만 UI 제공 |
| mock 응답 확장 | 구현 완료 | `frontend/services/mock_api.py` |
| 챗봇 API 호출 | 기존 구현 유지 | `frontend/services/api_client.py`, `frontend/views/chatbot_panel.py` |
| 백엔드 코드 병합 | 구현 완료 | `backend/` |

## 2. 실행 모드 요구사항

프론트는 `CHEONGYAK_API_MODE`에 따라 API client를 선택합니다.

| 값 | 동작 |
| --- | --- |
| `auto` | 기본값. FastAPI를 먼저 호출하고 실패하면 mock 응답으로 대체 |
| `http` | FastAPI를 호출. 실패 시 화면에서는 mock fallback 표시 |
| `mock` | FastAPI 호출 없이 mock 응답 사용 |

기본 설정:

```powershell
$env:CHEONGYAK_API_MODE="auto"
$env:CHEONGYAK_API_BASE_URL="http://192.168.0.27:8000"
```

로컬 실행:

```powershell
streamlit run frontend\streamlit_app.py
```

## 3. 연동 대상 API

원격 Swagger 문서 기준:

```text
http://192.168.0.27:8000/docs
```

현재 프론트가 직접 사용하는 endpoint:

| Method | Path | 용도 |
| --- | --- | --- |
| `POST` | `/api/v1/diagnose/profile` | 사용자 상세 프로필 기반 1차 청약 진단 |
| `POST` | `/api/v1/diagnose/detail` | 1차 진단 후 추가 질문 기반 상세 진단 |
| `POST` | `/api/v1/chat` | 청약 FAQ/챗봇 질문 답변 |

참고 endpoint:

| Method | Path | 용도 |
| --- | --- | --- |
| `GET` | `/health` | 백엔드 상태 확인 |
| `POST` | `/api/v1/diagnose/initial` | 초보자용 초기 진단 |
| `POST` | `/api/v1/diagnose` | initial 호환 endpoint |
| `GET` | `/api/v1/sources` | 근거 문서 목록 |

## 4. 사용자 입력 항목

현재 Streamlit UI는 다음 값을 수집합니다.

### 필수 입력

| 화면 단계 | 입력값 | payload 필드 |
| --- | --- | --- |
| 통장 | 통장 종류 | `profile.bankbook_type`, `subscription_account_detail.account_type` |
| 통장 | 가입일 | `profile.bankbook_join_date` |
| 통장 | 납입 횟수 | `profile.bankbook_payments`, `subscription_account_detail.payment_count` |
| 통장 | 예치금 | `profile.bankbook_balance`, `subscription_account_detail.deposit_amount` |
| 주택/세대 | 거주지역 | `profile.region` |
| 주택/세대 | 무주택 여부 | `profile.is_homeless`, `housing_ownership` |
| 주택/세대 | 무주택 기간 | `profile.homeless_period_years` |
| 주택/세대 | 세대주 여부 | `profile.is_household_head` |
| 주택/세대 | 세대원 수 | `profile.num_household_members` |
| 혼인/자녀 | 혼인 상태 | `marital_status` |
| 혼인/자녀 | 출생 연도 | `profile.birth_year` |
| 혼인/자녀 | 자녀 여부 | `child_status` |
| 혼인/자녀 | 미성년 자녀 수 범주 | `profile.minor_children_status` |

### 선택 입력

| 화면 단계 | 입력값 | payload 필드 |
| --- | --- | --- |
| 선택 정보 | 가구 평균소득 | `profile.average_monthly_income` |
| 선택 정보 | 주택 구입/소유 이력 | `profile.has_property_history` |
| 선택 정보 | 총자산 | `profile.total_assets` |

선택 입력은 사용자가 입력하지 않으면 `null`로 전송합니다.

## 5. Profile 진단 요청 명세

Endpoint:

```http
POST /api/v1/diagnose/profile
Content-Type: application/json
```

Request body:

```json
{
  "housing_ownership": "HOUSELESS",
  "marital_status": "MARRIED",
  "child_status": "HAS_CHILD",
  "subscription_account_status": "HAS_ACCOUNT",
  "subscription_account_detail": {
    "account_type": "주택청약종합저축",
    "joined_months": 36,
    "payment_count": 24,
    "deposit_amount": 3000000
  },
  "profile": {
    "bankbook_type": "주택청약종합저축",
    "bankbook_join_date": "2023-01-15",
    "bankbook_joined_months": 36,
    "bankbook_payments": 24,
    "bankbook_balance": 3000000,
    "region": "경기",
    "is_homeless": true,
    "homeless_period_years": 5,
    "is_household_head": true,
    "num_household_members": 3,
    "birth_year": 1993,
    "minor_children_status": "TWO_OR_MORE",
    "has_two_or_more_minor_children": true,
    "average_monthly_income": null,
    "has_property_history": null,
    "total_assets": null
  }
}
```

### enum 값

| 필드 | 허용값 |
| --- | --- |
| `housing_ownership` | `HOUSELESS`, `OWNS_HOME`, `UNKNOWN` |
| `marital_status` | `MARRIED`, `ENGAGED`, `NOT_MARRIED` |
| `child_status` | `NO_CHILD`, `HAS_CHILD`, `UNKNOWN` |
| `subscription_account_status` | `HAS_ACCOUNT`, `NO_ACCOUNT`, `UNKNOWN` |
| `profile.minor_children_status` | `UNDER_TWO`, `TWO_OR_MORE` |

현재 profile UI는 청약통장 정보를 필수로 받으므로 `subscription_account_status`는 `HAS_ACCOUNT`로 전송합니다.

자녀 여부가 `NO_CHILD`이면 프론트는 `profile.minor_children_status`를 `UNDER_TWO`로 보정합니다.

## 6. Profile 진단 응답 명세

Response body:

```json
{
  "result_mode": "NEEDS_DETAIL",
  "result_status": "추가 확인 필요",
  "candidate_supply_types": [
    {
      "supply_type": "일반공급",
      "status": "추가 확인 필요",
      "reasons": ["청약통장을 보유한 것으로 입력되었습니다."],
      "missing_checks": ["지역별 예치금 기준"],
      "next_questions": ["notice_region", "housing_area"],
      "source_refs": ["청약홈 순위별 청약자격"]
    }
  ],
  "blocked_reasons": [],
  "missing_inputs": ["가구 월평균 소득", "총자산"],
  "next_questions": ["marriage_period", "average_monthly_income"],
  "next_actions": ["추가 질문에 답하면 특별공급 후보를 더 구체화할 수 있습니다."],
  "guide_message": "프로필 입력값 기준으로 검토 가능한 청약 공급유형 후보를 안내합니다.",
  "warnings": ["최종 자격은 청약홈 및 입주자모집공고문 기준으로 확인해야 합니다."]
}
```

### 프론트 렌더링 요구사항

프론트는 다음 응답 필드를 화면에 표시해야 합니다.

| 응답 필드 | 현재 처리 |
| --- | --- |
| `result_mode` | 결과 모드 caption 표시 |
| `result_status` | 종합 상태로 표시 |
| `candidate_supply_types` | 공급유형 카드로 표시 |
| `candidate_supply_types[].reasons` | 근거 목록으로 표시 |
| `candidate_supply_types[].missing_checks` | 추가 확인 목록으로 표시 |
| `candidate_supply_types[].next_questions` | 후속 질문 키로 표시 |
| `candidate_supply_types[].source_refs` | 출처 caption 표시 |
| `blocked_reasons` | 제한 사유로 표시 |
| `missing_inputs` | 부족한 입력값으로 표시 |
| `next_questions` | 필요한 후속 질문으로 표시 |
| `next_actions` | 다음 확인 항목으로 표시 |
| `guide_message` | 안내 메시지로 표시 |
| `warnings` | warning 메시지로 표시 |

## 7. Detail 진단 요청 명세

Endpoint:

```http
POST /api/v1/diagnose/detail
Content-Type: application/json
```

Request body:

```json
{
  "marriage_period": "WITHIN_7_YEARS",
  "youngest_child_age_group": "UNDER_2",
  "child_count_group": "TWO_OR_MORE",
  "housing_history": "NO_HISTORY",
  "elderly_support": "DOES_NOT_MEET"
}
```

모든 필드는 선택값입니다. 프론트는 profile 응답의 `next_questions`를 보고 지원 가능한 필드만 사용자에게 보여줍니다.

### 현재 지원하는 detail 질문

| `next_questions` 키 | UI 라벨 | 전송 필드 |
| --- | --- | --- |
| `marriage_period` | 혼인기간 | `marriage_period` |
| `youngest_child_age_group` | 가장 어린 자녀 연령 | `youngest_child_age_group` |
| `child_count_group` | 미성년 자녀 수 | `child_count_group` |
| `housing_history` | 과거 주택 소유 이력 | `housing_history` |
| `elderly_support` | 노부모 부양 여부 | `elderly_support` |

### 현재 UI에서 별도 안내만 하는 질문

아래 키는 원격 API 응답에는 포함될 수 있지만, 현재 detail endpoint 입력 스키마에는 없으므로 선택 UI를 만들지 않고 별도 확인 항목으로 표시합니다.

| 키 | 현재 처리 |
| --- | --- |
| `notice_region` | 별도 확인 항목으로 표시 |
| `housing_area` | 별도 확인 항목으로 표시 |
| `average_monthly_income` | 선택 정보 단계에서 입력 가능. 후속 질문에서는 별도 확인 항목으로 표시 |
| `total_assets` | 선택 정보 단계에서 입력 가능. 후속 질문에서는 별도 확인 항목으로 표시 |
| `has_property_history` | 선택 정보 단계에서 입력 가능. 후속 질문에서는 별도 확인 항목으로 표시 |
| `special_identity_types` | 별도 확인 항목으로 표시 |

## 8. Chat API 명세

Endpoint:

```http
POST /api/v1/chat
Content-Type: application/json
```

Request body:

```json
{
  "question": "무주택 기간은 어떻게 계산하나요?"
}
```

Response body:

```json
{
  "answer": "답변 본문",
  "question": "무주택 기간은 어떻게 계산하나요?",
  "source_refs": ["청약홈", "주택공급에 관한 규칙"]
}
```

프론트는 `answer`를 챗봇 메시지로 표시하고, `source_refs`가 있으면 답변 하단에 출처를 붙입니다.

## 9. Mock fallback 요구사항

FastAPI 연결 실패 시 mock 응답은 실제 API 응답 구조와 최대한 같은 형태를 유지해야 합니다.

현재 mock은 다음 공급유형 후보를 반환합니다.

| 공급유형 |
| --- |
| 일반공급 |
| 신혼부부 특별공급 |
| 다자녀 특별공급 |
| 생애최초 특별공급 |
| 신생아 특별공급 |
| 노부모부양 특별공급 |
| 기관추천 특별공급 |

mock 응답도 다음 필드를 포함해야 합니다.

```json
{
  "result_mode": "NEEDS_DETAIL",
  "result_status": "추가 확인 필요",
  "candidate_supply_types": [],
  "blocked_reasons": [],
  "missing_inputs": [],
  "next_questions": [],
  "next_actions": [],
  "guide_message": "mock 응답입니다.",
  "warnings": []
}
```

## 10. 검증 기록

현재 구현 기준으로 확인한 항목:

| 검증 | 결과 |
| --- | --- |
| 프론트 단위 테스트 | `9 passed` |
| 프론트 Python 문법 검사 | 통과 |
| 원격 `/api/v1/diagnose/profile` smoke test | 성공 |
| 원격 `/api/v1/diagnose/detail` smoke test | 성공 |
| Streamlit 브라우저 실행 확인 | 성공 |

원격 profile smoke test 결과:

```text
result_mode: NEEDS_DETAIL
result_status: 추가 확인 필요
candidate_supply_types: 7개
next_questions: notice_region,housing_area,marriage_period,average_monthly_income,total_assets,has_property_history,youngest_child_age_group,elderly_support,special_identity_types
```

원격 detail smoke test 결과:

```text
result_mode: INITIAL_RESULT
result_status: 가능성 있음
candidate_supply_types: 1개
```

## 11. 남은 보완 요구사항

우선순위가 높은 항목:

1. `average_monthly_income`, `total_assets`, `has_property_history`가 후속 질문으로 내려올 때 결과 화면에서 바로 선택 정보 단계로 돌아가게 하는 UX.
2. `notice_region`, `housing_area`를 모집공고/면적 선택 UI로 확장.
3. `special_identity_types`를 기관추천 특별공급용 선택 UI로 확장.
4. 원격 백엔드 브랜치(`origin/준억`)를 병합할지, 별도 `backend/` 구조로 유지할지 팀 단위 결정.
5. 줄바꿈 정책 통일을 위한 `.gitattributes` 추가 검토.

아직 하지 않는 것이 나은 항목:

1. 현재 시점의 대규모 폴더 구조 재정립.
2. 백엔드 브랜치 무조건 merge.
3. FastAPI만 강제하는 기본 설정. 팀원 환경에서 LAN 서버가 꺼져 있으면 프론트 확인이 막힐 수 있습니다.
