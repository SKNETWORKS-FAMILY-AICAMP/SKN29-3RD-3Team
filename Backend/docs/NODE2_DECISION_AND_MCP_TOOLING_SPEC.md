# NODE 2 기본 진단 및 분기 노드 / MCP Tool 합의 명세

## 1. 현재 챗봇 연결 상태

### 결론

다른 브랜치의 LangGraph/RAG 챗봇 로직을 지금 프론트에 그대로 붙이기에는 endpoint 계약이 부족하다.

현재 MCP 브랜치에는 `POST /api/v1/chat` endpoint와 Streamlit 챗봇 패널 호출이 이미 있다. 하지만 이 endpoint는 아래 수준의 단순 계약이다.

```json
{
  "question": "사용자 질문"
}
```

응답도 `answer`, `source_refs` 중심이다. 즉, 자유 질문 FAQ/RAG용 endpoint이지, 현재 자가진단 상태나 Node 1/Node 2 결과를 받아 전략 브리핑을 생성하는 endpoint는 아니다.

### 현재 가능한 것

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Streamlit 챗봇 UI | 있음 | `frontend/views/chatbot_panel.py` |
| FastAPI chat endpoint | 있음 | `POST /api/v1/chat` |
| chat request schema | 있음 | `ChatRequest.question` |
| chat response schema | 있음 | `ChatResponse.answer`, `source_refs` |
| RAG/LangGraph 챗봇 연결 | 미완 | 현재 endpoint 내부는 테스트/placeholder 응답 |
| 진단 상태를 포함한 chat 호출 | 없음 | profile, diagnosis_result, node_state를 받지 않음 |
| Node 2 전략 브리핑 endpoint | 없음 | 별도 합의 필요 |

### 추가로 필요한 로직

| 필요 로직 | 이유 |
| --- | --- |
| `ChatContext` 또는 `DiagnosisContext` schema | 챗봇이 현재 사용자 입력, 후보 공급유형, 가점 결과를 알아야 함 |
| chat endpoint 확장 또는 별도 strategy endpoint | FAQ 답변과 전략 브리핑을 분리해야 함 |
| RAG retriever 연결 방식 | 출처 문구와 근거 검색을 담당 |
| Node 1/Node 2 상태 저장 위치 | Streamlit session, backend state, LangGraph state 중 선택 필요 |
| 오류/부분 계산 정책 | 모르는 값이 있을 때 계산 제외, 확인 필요, 사용자 질문 중 어느 방식으로 처리할지 필요 |
| source priority 정책 | 법령, 청약홈, 모집공고문, 내부 JSON 중 어떤 순서로 믿을지 필요 |

### 권장 방향

`/api/v1/chat`는 FAQ/RAG 자유질문 endpoint로 유지한다. Node 2 전략 브리핑은 별도 endpoint 또는 LangGraph node API로 분리한다.

권장 endpoint 예시:

```http
POST /api/v1/diagnose/strategy-briefing
```

또는 LangGraph 도입 시:

```http
POST /api/v1/graph/node2/briefing
```

이유는 단순하다. 챗봇 endpoint에 전략 판단까지 섞으면 입력 schema가 흐려지고, 프론트가 어떤 응답을 렌더링해야 하는지 애매해진다.

---

## 2. Node 2 목표

### 이름

`NODE 2: 기본 진단 및 분기 노드`

### 기능

Node 1에서 수집/검증한 사용자 정보를 바탕으로, 사용자가 현재 검토할 만한 공급유형 중 어떤 전략이 상대적으로 유리한지 1차 브리핑한다.

### 역할

Node 2는 최종 당첨 가능성을 확정하지 않는다. 아래 역할까지만 담당한다.

1. 현재 입력값으로 검토 가능한 공급유형 후보 정리
2. 일반공급 가점제, 신혼부부, 다자녀, 생애최초, 신생아, 노부모부양 등 주요 카드의 상대적 유불리 비교
3. 계산 가능한 항목은 MCP Tool로 정량 계산
4. 계산 불가능하거나 공고문 의존적인 항목은 `확인 필요`로 분리
5. Node 3 분기 판단에 사용할 추천 카드와 남은 확인 항목 제공

---

## 3. 현재 진행된 항목

| 영역 | 진행 상태 | 파일/근거 |
| --- | --- | --- |
| 기본 프로필 기반 진단 API | 진행됨 | `POST /api/v1/diagnose/profile` |
| 초기 상세 입력 포함 진단 API | 진행됨 | `POST /api/v1/diagnose/full-profile` |
| 결과 화면 추가 질문 제거 | 진행됨 | 초기 입력 `detail` payload로 이동 |
| 일반공급 청약 가점 MCP Tool | 진행됨 | `src/engine/housing_subscription_score.py`. 단, 일반공급 전용 계산기이며 전체 전형 공통 계산기가 아님 |
| 일반공급 가점 LangChain Tool adapter | 진행됨 | `src/engine/housing_subscription_score_tool.py` |
| 부분 계산 adapter | 진행됨 | `src/engine/housing_subscription_score_partial_adapter.py` |
| 기존 DiagnoseResponse 호환 adapter | 진행됨 | `src/engine/housing_subscription_score_response_adapter.py` |
| 공식 점수표 구조화 JSON | 진행됨 | `data/processed/structured/housing_subscription_score_tables.json` |
| chat endpoint | 기본 placeholder만 있음 | `backend/src/routers/chat.py`, `backend/src/services/chat_service.py` |
| RAG/LangGraph 챗봇 연결 | 미완 | 다른 브랜치 코드 후보만 존재 |
| Node 2 전략 비교 로직 | 미완 | 합의 필요 |

---

## 4. Node 2에서 합의해야 할 내용

### 4.1 입력 계약

Node 2는 최소한 아래 입력을 받아야 한다.

```json
{
  "profile": {
    "bankbook_type": "주택청약종합저축",
    "bankbook_join_date": "2024-01-01",
    "bankbook_joined_months": 30,
    "bankbook_payments": 24,
    "bankbook_balance": 3000000,
    "region": "서울",
    "is_homeless": true,
    "homeless_period_years": 5,
    "is_household_head": true,
    "num_household_members": 3,
    "birth_year": 1993,
    "minor_children_status": "TWO_OR_MORE",
    "has_two_or_more_minor_children": true,
    "average_monthly_income": null,
    "has_property_history": false,
    "total_assets": null
  },
  "detail": {
    "marriage_period": "WITHIN_7_YEARS",
    "youngest_child_age_group": "UNDER_2",
    "child_count_group": "TWO_OR_MORE",
    "housing_history": "NO_HISTORY",
    "elderly_support": "DOES_NOT_MEET"
  },
  "diagnosis_result": {
    "candidate_supply_types": [],
    "pending_external_checks": []
  }
}
```

합의 필요:

| 항목 | 결정 필요 |
| --- | --- |
| Node 2가 `full-profile` 요청을 직접 받을지, Node 1 결과를 받을지 | API/Graph 구조 결정 |
| `detail`을 `profile` 안에 넣을지, 별도 object로 유지할지 | 현재는 별도 object 권장 |
| 소득/자산 미입력 허용 여부 | 현재는 null 허용, 확인 필요 분리 |
| 공고문 정보 입력 시점 | Node 4 인터럽트에서 받는 것으로 유지 권장 |

### 4.2 출력 계약

Node 2 출력은 프론트 카드/브리핑에 바로 쓰일 수 있어야 한다.

권장 schema:

```json
{
  "node": "NODE_2_STRATEGY_BRIEFING",
  "briefing_status": "NEEDS_REVIEW",
  "recommended_supply_type": "생애최초 특별공급",
  "recommendation_reason": "일반공급 가점은 낮고, 현재 입력값 기준으로 생애최초 추첨형 검토가 상대적으로 유리합니다.",
  "score_results_by_supply_type": [
    {
      "supply_type": "일반공급 가점제",
      "calculation_type": "POINT_BASED",
      "calculator_name": "calculate_housing_subscription_score",
      "score": 42,
      "max_score": 84,
      "score_breakdown": {
        "homeless_score": 12,
        "dependent_family_score": 20,
        "subscription_score": 10
      },
      "need_review": false,
      "warnings": [],
      "source_refs": []
    },
    {
      "supply_type": "신혼부부 특별공급",
      "calculation_type": "POINT_BASED_OR_PRIORITY_BASED",
      "calculator_name": null,
      "score": null,
      "max_score": null,
      "score_breakdown": {},
      "need_review": true,
      "warnings": ["신혼부부 특별공급 배점표와 우선순위 기준 합의 전입니다."],
      "source_refs": []
    },
    {
      "supply_type": "생애최초 특별공급",
      "calculation_type": "CONDITION_OR_LOTTERY_BASED",
      "calculator_name": null,
      "score": null,
      "max_score": null,
      "score_breakdown": {},
      "need_review": true,
      "warnings": ["추첨형/조건형 전형은 가점 점수로 비교하지 않습니다."],
      "source_refs": []
    }
  ],
  "ranked_supply_cards": [
    {
      "supply_type": "생애최초 특별공급",
      "rank": 1,
      "strategy_type": "LOTTERY_OR_CONDITION_BASED",
      "score_result_ref": "생애최초 특별공급",
      "confidence": "MEDIUM",
      "reasons": [],
      "risks": [],
      "required_checks": []
    }
  ],
  "source_refs": [],
  "warnings": [],
  "next_node": "NODE_3_CONDITIONAL_BRANCH"
}
```

중요: Node 2는 `score` 하나로 모든 전형을 비교하지 않는다. 전형마다 배점 방식과 최대점수가 다르므로 반드시 `score_results_by_supply_type`에 전형별 계산 결과를 별도로 둔다.

합의 필요:

| 항목 | 선택지 |
| --- | --- |
| `recommended_supply_type` 단일 추천 여부 | 단일 추천 / 공동 1순위 허용 |
| `confidence` 단계 | HIGH/MEDIUM/LOW 또는 숫자 점수 |
| 전형별 `score_result` 구조 | 전형별 실제 배점, 조건형 판단, 추첨형 분류를 분리 |
| `next_node` 포함 여부 | LangGraph에서만 관리할지 API 응답에도 줄지 |

### 4.3 비교 대상 공급유형

초기 Node 2 범위는 아래로 제한한다.

| 공급유형 | Node 2 처리 방식 |
| --- | --- |
| 일반공급 가점제 | 일반공급 전용 MCP 가점 계산기로 정량 계산 가능 |
| 신혼부부 특별공급 | 별도 배점/우선순위 계산 결과 필요. 일반공급 가점 계산기 재사용 금지 |
| 다자녀 특별공급 | 별도 배점표 계산 결과 필요. 일반공급 가점 계산기 재사용 금지 |
| 생애최초 특별공급 | 가점 점수 대신 조건 충족/추첨형 후보로 분류 |
| 신생아 특별공급 | 가점 점수 대신 조건/우선순위/소득·자산 확인 결과로 분류 |
| 노부모부양 특별공급 | 전용 조건/가점 기준 확인 필요. 일반공급 가점 계산기 재사용 금지 |
| 기관추천 특별공급 | Node 2 자동 비교 범위 밖, 별도 신분 확인 |

합의 필요:

| 항목 | 결정 필요 |
| --- | --- |
| 신혼부부 특공 점수표를 MCP로 만들지 | 현재 미구현 |
| 다자녀 특공 점수표를 MCP로 만들지 | 현재 미구현 |
| 추첨형 공급의 “유리함”을 어떻게 수치화할지 | 확률 데이터 없으면 정성 등급만 가능 |
| 모집공고별 비율/지역/평형 정보 없이 당첨확률을 말할지 | 말하지 않는 것이 안전 |

---

## 5. MCP Tool 설계 합의

### 5.1 이미 있는 Tool

| Tool | 상태 | 역할 |
| --- | --- | --- |
| `calculate_housing_subscription_score` | 구현됨 | 일반공급 가점제 전용 점수 계산 |
| partial score adapter | 구현됨 | 일반공급 가점제 누락값 제외 기준 참고 점수 산출 |

### 5.2 Node 2에서 추가로 필요한 Tool 후보

| Tool 후보 | 우선순위 | 설명 |
| --- | --- | --- |
| `compare_supply_strategy` | 높음 | 전형별 별도 score result를 받아 상대 유리 카드 산정 |
| `calculate_newlywed_special_score` | 높음 | 신혼부부 특공 전용 배점/우선순위 기준 확정 후 계산 |
| `calculate_multi_child_special_score` | 높음 | 다자녀 특공 전용 배점표 확정 후 계산 |
| `check_condition_based_supply` | 높음 | 생애최초/신생아/노부모 등 조건 충족 여부 분류 |
| `extract_apartment_info` | Node 4 우선 | 분양가, 지역, 평형, 모집공고 정보를 정형화 |
| `check_regional_priority` | Node 5 우선 | 지역 우선공급/거주지 제한 확인 |
| `predict_winning_probability` | 후순위 | 공고문 경쟁률/추첨·가점 비율 없으면 정확도 낮음 |

### 5.3 Node 2 MVP 추천

Node 2 MVP에서는 `compare_supply_strategy`를 만들되, 입력은 반드시 전형별 계산 결과 목록이어야 한다.

입력:

```json
{
  "diagnosis_response": {},
  "score_results_by_supply_type": [
    {
      "supply_type": "일반공급 가점제",
      "calculation_type": "POINT_BASED",
      "calculator_name": "calculate_housing_subscription_score",
      "score": 42,
      "max_score": 84,
      "score_breakdown": {},
      "need_review": false,
      "warnings": []
    },
    {
      "supply_type": "신혼부부 특별공급",
      "calculation_type": "POINT_BASED_OR_PRIORITY_BASED",
      "calculator_name": null,
      "score": null,
      "max_score": null,
      "score_breakdown": {},
      "need_review": true,
      "warnings": ["전용 계산기 미구현"]
    }
  ],
  "profile": {},
  "detail": {}
}
```

출력:

```json
{
  "recommended_supply_type": "생애최초 특별공급",
  "score_results_by_supply_type": [],
  "ranked_supply_cards": [],
  "warnings": [],
  "need_review": true
}
```

MVP에서는 다음 원칙을 둔다.

1. 일반공급 가점은 이미 구현된 일반공급 전용 MCP 결과를 사용한다.
2. 신혼부부/다자녀/노부모부양은 일반공급 가점 계산기를 재사용하지 않는다.
3. 전형별 계산기가 없는 경우 해당 전형의 `score_result.need_review=true`와 warning을 반환한다.
4. 생애최초/신생아 같은 조건형·추첨형 전형은 점수 대신 조건 충족/확인 필요 결과로 반환한다.
5. `compare_supply_strategy`는 서로 다른 전형 점수를 단순 숫자 비교하지 않고, 전형별 계산 방식과 confidence를 함께 비교한다.
6. 분양가/지역/평형/공고문 정보가 없으면 당첨확률은 말하지 않는다.
7. `need_review=true`를 적극 사용한다.

---

## 6. 브랜치별 참고 가능 항목

| 브랜치 | 참고 가능 항목 | 바로 흡수 어려운 이유 |
| --- | --- | --- |
| `origin/동윤` | LangGraph Node 흐름, RAG/chat graph 아이디어 | 현재 FastAPI endpoint 계약과 직접 연결되어 있지 않음 |
| `origin/지훈` | retriever/RAG, chunker, metadata 구조 | Node 2 전략 판단보다 근거 검색 쪽에 가까움 |
| `origin/준억` | FastAPI chat endpoint placeholder | 이미 현재 브랜치에 유사 구조 존재 |

현재 판단: 다른 브랜치의 챗봇 로직은 `answer_chat()` 내부 구현 후보로는 참고 가능하지만, 프론트에 붙이려면 먼저 context-aware chat 또는 strategy endpoint 계약이 필요하다.

---

## 7. 2인 역할 분담 추천

### 역할 A: Backend / Agent Tool 담당

담당 범위:

1. 전형별 `score_result` 공통 schema 설계
2. `calculate_housing_subscription_score` 결과를 Node 2 입력으로 연결
3. `FullProfileDiagnoseResponse`와 Node 2 출력 schema 정리
4. RAG retriever가 제공할 `source_refs` 구조 정의
5. pytest 작성

우선 작업 순서:

1. Node 2 request/response Pydantic 모델 작성
2. `compare_supply_strategy` 순수 함수 구현
3. LangChain `StructuredTool` adapter 추가
4. `/api/v1/diagnose/strategy-briefing` 또는 graph node endpoint 추가
5. 단위 테스트와 schema validation 테스트 작성

### 역할 B: Frontend / UX Integration 담당

담당 범위:

1. Node 2 브리핑 카드 UI 설계
2. 추천 공급유형 ranking 표시
3. `need_review`, `warnings`, `pending_external_checks` 표시 정책
4. Node 3 분기 버튼 UI 설계
5. API client 및 mock 응답 업데이트

우선 작업 순서:

1. Node 2 응답 mock fixture 작성
2. 전략 브리핑 카드 컴포넌트 구현
3. 기존 결과 화면에 추천 카드 영역 추가
4. “공고문 정보 입력하기” 버튼을 Node 4 인터럽트 진입점으로 설계
5. API 실패 시 mock fallback 유지

### 공동 합의 회의에서 결정할 항목

| 주제 | 결정 질문 |
| --- | --- |
| Node 2 endpoint 이름 | `/diagnose/strategy-briefing` vs `/graph/node2/briefing` |
| Node 2 출력 schema | `recommended_supply_type`, `ranked_supply_cards`, `next_node` 포함 여부 |
| 전형별 계산 범위 | 일반공급만 구현 / 신혼·다자녀·노부모 전용 계산기 추가 여부 |
| 추첨형 유리함 기준 | 정성 등급만 / 내부 비교점수 사용 |
| RAG 사용 위치 | Node 2 근거 문구 / 챗봇 답변 / 둘 다 |
| 모르는 값 처리 | 누락 제외 계산 / 사용자에게 질문 / 확인 필요만 표시 |
| 프론트 표시 방식 | 단일 추천 강조 / 후보 카드 ranking |

---

## 8. Acceptance Criteria

Node 2 구현 전 합의 완료 조건:

1. Node 2 endpoint 또는 LangGraph node 호출 방식이 정해져 있다.
2. Node 2 request/response schema가 문서화되어 있다.
3. 전형별 `score_results_by_supply_type` schema가 정해져 있다.
4. 신혼부부/다자녀 점수 계산을 MVP에 포함할지 결정되어 있다.
5. 공고문 정보 없이 당첨확률을 말하지 않는다는 원칙이 합의되어 있다.
6. 프론트가 `need_review`, `warnings`, `pending_external_checks`를 표시하는 방식이 정해져 있다.
7. 최소 테스트 케이스가 있다.

Node 2 MVP 완료 조건:

1. 입력 profile/detail/diagnosis_result로 전략 브리핑 응답을 생성한다.
2. 전형별 계산 결과가 있으면 ranking 근거에 반영한다.
3. 신혼부부/다자녀/생애최초/신생아/노부모 후보를 최소한 조건 기반으로 비교한다.
4. 불확실한 항목은 `need_review=true`와 `required_checks`로 반환한다.
5. 프론트 결과 화면에서 추천 카드와 확인 필요 항목이 구분되어 보인다.
6. `python -m pytest`가 통과한다.
