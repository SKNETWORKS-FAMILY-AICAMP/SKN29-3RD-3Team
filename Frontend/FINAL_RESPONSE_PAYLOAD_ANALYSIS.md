# final 응답 구조 및 결과 화면 개선 분석

이 문서는 `origin/final` 백엔드를 기준으로, 프론트가 어떤 응답 필드를 받아 결과 화면에 표시하는지 분석한 자료다.
목적은 백엔드 로직을 바꾸지 않고도 프론트 결과 화면을 어떤 방향으로 개선할 수 있는지 판단하기 위함이다.

## 1. 현재 결론

`final` 백엔드는 이미 결과 화면을 만들 수 있는 주요 재료를 반환하고 있다.

- 추천 순위: `supply_rank`
- 최종 추천 유형: `recommended_supply`
- 상세 리포트: `report`
- 공고 분석: `announcement`
- 재무 분석: `report.finance`, `node5.loan_result`, `node5.investment_result`, `node5.risk_result`
- 최종 전략: `report.strategy`, `node5.agent_result`

따라서 다음 개선은 백엔드 계산 로직보다 프론트 표시 구조를 먼저 다듬는 쪽이 안전하다.
특히 사용자는 결과를 “개발 로그”처럼 보는 것이 아니라, “검사지 결과지”처럼 한 페이지에서 이해해야 한다.

## 2. API 호출 흐름

```text
사용자 입력
  ↓
Frontend/services/payload.py
  - DiagnosisForm 생성
  - profile payload 변환
  ↓
POST /api/profile
  ↓
Backend/src/pipeline.py
  - Node1 실행
  - Node2 실행
  - interrupt_after=["node2"]
  ↓
프론트가 session_id, supply_rank, recommended_supply 수신
  ↓
POST /api/simulate
  - 상세 시뮬레이션 여부 전달
  ↓
상세 공고 입력 시
POST /api/announcement
  ↓
Node4 → Node5 → Node6 실행
  ↓
최종 응답 수신
  ↓
Frontend/views/diagnosis_result.py
Frontend/components/ui.py
  - 결과 화면 렌더링
```

## 3. 백엔드 최종 응답 구조

최종 응답은 `Backend/src/pipeline.py`의 `_build_resume_response()`에서 정리된다.

```python
{
    "status": status,
    "session_id": session_id,
    "report": values.get("final_report", {}),
    "profile": values.get("profile", {}),
    "announcement": values.get("announcement", {}),
    "available_supply_types": values.get("available_supply_types", []),
    "supply_analysis": values.get("supply_analysis", {}),
    "supply_rank": values.get("supply_rank", []),
    "recommended_supply": values.get("recommended_supply"),
    "node5": {
        "loan_result": values.get("loan_result", {}),
        "investment_result": values.get("investment_result", {}),
        "risk_result": values.get("risk_result", {}),
        "agent_result": values.get("agent_result", ""),
    },
    "node6": {
        "final_report": values.get("final_report", {})
    },
}
```

프론트는 이 응답을 `Frontend/services/api_client.py`의 `_normalize_resume_response()`에서 한 번 더 UI 친화 형태로 정규화한다.

## 4. 프론트 정규화 결과

`_normalize_resume_response()`가 결과 화면에 넘기는 주요 필드는 다음과 같다.

| 필드 | 의미 | 현재 활용 |
| --- | --- | --- |
| `result_mode` | 프론트 표시용 결과 모드 | `ANNOUNCEMENT_FLOW`로 표시 |
| `result_status` | 백엔드 처리 상태 | `success` 등 원문 표시 |
| `guide_message` | 상단 안내 문구 | `report.summary` 또는 백엔드 message |
| `report` | Node6 최종 리포트 | 상세 리포트/전략/재무 표시 |
| `announcement` | Node4 공고 파싱 결과 | 공고 분석 metric 표시 |
| `recommended_supply` | 최종 추천 공급유형 | 추천 요약 표시 |
| `supply_rank` | 공급유형별 추천 순위 | Top3 카드, 상세 카드 표시 |
| `supply_analysis` | Node2 분석 원본 | 현재 직접 활용은 약함 |
| `available_supply_types` | Node1 가능 공급유형 | 현재 직접 활용은 약함 |
| `node5` | Node5 재무/전략 원본 | 재무/전략 fallback으로 활용 |
| `node6` | Node6 최종 리포트 원본 | `report` fallback으로 활용 |

## 5. 핵심 필드별 화면 가치

### 5.1 `supply_rank`

가장 중요한 사용자-facing 데이터다.

예상 구조:

```python
{
    "rank": 1,
    "type": "신혼부부 특공",
    "score": 12,
    "max_score": 16,
    "ratio": "75%",
    "reason": "점수 비율 75%로 경쟁력 있음",
    "method": "가점제",
    "score_breakdown": {
        "income": 1,
        "minor_child_count": 2,
        "residence_period_years": 3,
        "bankbook_payments": 3,
        "marriage_period": 3
    },
    "matched_items": [],
    "missing_items": [],
    "source_refs": []
}
```

프론트 개선 포인트:

- Top3 카드에는 `rank`, `type`, `method`, `score/max_score`, `ratio`, `reason`만 먼저 보여준다.
- `score_breakdown`은 별도 표 하나에 몰아넣기보다 각 공급유형 카드 안에서 접이식으로 보여주는 편이 낫다.
- `method`가 `가점제`인지 `추첨제`인지 시각적으로 분리해야 한다.
- `missing_items`가 있으면 추천처럼 보이지 않도록 “확인 필요” 상태로 표현해야 한다.

### 5.2 `report`

Node6의 최종 결과다.

간단 리포트:

```python
{
    "report_type": "simple",
    "recommended_supply": "...",
    "supply_rank": [...],
    "summary": "..."
}
```

상세 리포트:

```python
{
    "report_type": "detailed",
    "recommended_supply": "...",
    "supply_rank": [...],
    "announcement": {...},
    "finance": {...},
    "strategy": "..."
}
```

프론트 개선 포인트:

- `summary`와 `strategy`가 같은 말을 반복할 수 있다.
- 사용자에게는 “요약”, “근거”, “다음 행동”으로 나누는 것이 더 자연스럽다.
- Markdown 원문을 그대로 길게 노출하면 결과지가 아니라 분석 로그처럼 보인다.

### 5.3 `announcement`

공고 입력이 있을 때 Node4가 파싱한 결과다.

주요 필드:

- `region`
- `supply_type`
- `area`
- `supply_count`

프론트 개선 포인트:

- 현재는 metric 4개로만 표시된다.
- 결과 상단의 핵심 판단과 연결되어야 한다.
- 예: “서울 강남구 민간 84㎡ / 공급 80세대 기준으로 판단했어요”

### 5.4 `finance`, `node5`

재무 분석은 사용자가 가장 민감하게 보는 영역이다.

주요 필드:

- `price`
- `loan_amount`
- `real_investment`
- `risk_level`
- `risk_ratio`
- `risk_description`

프론트 개선 포인트:

- 금액 metric이 길어지면 말줄임 처리될 수 있다.
- 원 단위 전체 숫자보다 `5억`, `2억`, `3억`처럼 읽기 쉬운 표현이 필요하다.
- `자금 리스크: 높음`은 단독으로 두기보다 “왜 높은지”를 바로 붙여야 한다.

## 6. 현재 화면의 사용자 경험 문제

### 6.1 개발자용 정보가 사용자 화면에 너무 앞에 나온다

현재 화면은 다음 문구가 상단에 보인다.

- `종합 상태: success`
- `결과 모드: ANNOUNCEMENT_FLOW`
- `백엔드 그래프 응답을 받았습니다.`

이 표현은 개발자에게는 유용하지만 사용자에게는 의미가 약하다.
사용자는 “내가 뭘 해야 하는지”를 먼저 알고 싶다.

권장:

- 개발자 상태는 하단 expander로 이동
- 상단에는 사용자 언어로 변환
  - 예: “신혼부부 특공을 먼저 검토하세요”
  - 예: “자격은 가능하지만 자금 계획 확인이 필요해요”

### 6.2 Top3 카드와 상세 결과가 중복된다

현재는 상단 Top3 카드가 있고, 아래에 다시 공급유형별 결과가 카드 형태로 반복된다.

권장:

- Top3 카드를 결과 화면의 중심으로 사용
- 각 카드 안에 “점수 근거 보기”를 접이식으로 포함
- 아래의 별도 공급유형 카드 목록은 제거하거나 “전체 비교표”로 축약

### 6.3 가점 근거가 한눈에 안 들어온다

가점 세부 항목은 사용자가 가장 궁금해할 수 있는 부분이다.
현재는 하단에 길게 나오거나 카드 밖에서 떨어져 보일 수 있다.

권장:

- 각 공급유형 카드 안에서 바로 보여준다.
- 예:

```text
신혼부부 특공
12/16점 · 75%

점수 구성
- 소득 기준: 1점
- 미성년 자녀 수: 2점
- 거주기간: 3점
- 청약통장 납입 횟수: 3점
- 혼인기간: 3점
```

### 6.4 표보다 카드가 더 적합한 영역이 있다

공급유형 비교는 표도 가능하지만, 이 서비스의 결과 화면에서는 카드가 더 적합하다.

이유:

- 사용자는 순위를 먼저 본다.
- 각 유형마다 점수제/추첨제/확인필요 상태가 다르다.
- `score_breakdown`, `missing_items`, `source_refs`처럼 유형별 부가 정보가 붙는다.

표가 적합한 영역:

- 개발자 확인용 payload
- 전체 비교를 아주 압축해서 보는 보조 영역
- 출처 목록

카드가 적합한 영역:

- 추천 Top3
- 공급유형별 가점 근거
- 자격/자금/공고 핵심 판단

## 7. 추천 결과 화면 구조

토스식 사용자 경험에 가깝게 가려면, 화면은 다음 순서가 좋다.

```text
1. 한 줄 결론
   "신혼부부 특공을 먼저 검토하세요"

2. 핵심 상태 3~4개
   자격 가능 / 1순위 충족 / 자금 부담 높음 / 공고 기준 반영

3. 지금 확인할 일
   - 공고문 세부 자격 확인
   - 중도금 대출 가능 여부 확인
   - 다자녀 특공 병행 여부 검토

4. 추천 Top3 카드
   - 신혼부부 특공
   - 다자녀 특공
   - 생애최초 특공
   각 카드 안에 점수 근거/확인 필요 항목 포함

5. 공고 및 자금 요약
   - 공고: 서울 강남구 / 민간 / 84㎡ / 80세대
   - 자금: 분양가 5억 / 대출 2억 / 실투자금 3억 / 부담 높음

6. 상세 전략
   - Node5 또는 Node6 strategy를 요약해서 표시
   - 원문은 접이식으로 제공

7. 개발자 확인용
   - payload, status, raw response는 expander로 하단 배치
```

## 8. 다음 구현 우선순위

### 1순위: 결과 상단 사용자 언어화

수정 대상:

- `Frontend/components/ui.py`
- `Frontend/views/diagnosis_result.py`

내용:

- `success`, `ANNOUNCEMENT_FLOW`를 상단에서 숨긴다.
- 대신 `recommended_supply`, 자격 상태, 자금 리스크를 조합해 한 줄 결론을 만든다.

### 2순위: Top3 카드 리디자인

수정 대상:

- `Frontend/components/ui.py`

내용:

- 카드 높이 불일치 개선
- 점수제/추첨제 badge 추가
- `score_breakdown`을 각 카드 안에 포함
- `missing_items`는 경고색 텍스트로 표시

### 3순위: 재무 metric 포맷 개선

수정 대상:

- `Frontend/views/diagnosis_result.py`

내용:

- `500,000,000원` 대신 `5억 원` 등으로 표시
- 긴 숫자 말줄임 방지
- 자금 리스크 설명을 metric 바로 아래 배치

### 4순위: 상세 전략 정리

수정 대상:

- `Frontend/views/diagnosis_result.py`

내용:

- `report.strategy`를 무조건 길게 노출하지 않는다.
- “전략 요약”은 짧게, “상세 분석 원문”은 expander로 분리한다.

## 9. 백엔드 수정 필요성 판단

현재 단계에서는 백엔드 수정 없이도 상당 부분 개선 가능하다.

백엔드를 건드리지 않아도 가능한 것:

- 결과 화면 구조 변경
- Top3 카드 개선
- 가점 세부 항목 표시 위치 변경
- 개발자 상태 하단 이동
- 금액 포맷 개선
- 상세 전략 접이식 처리

백엔드 수정이 필요할 수 있는 것:

- `summary`, `strategy`, `next_steps`를 더 안정적으로 분리해서 내려주기
- `qualification_status`, `first_rank_status`, `funding_risk` 같은 사용자-facing 상태를 명시 필드로 내려주기
- 추첨제/가점제/확인필요 상태를 더 정규화해서 내려주기

따라서 지금은 프론트 렌더링 개선을 먼저 하고, 이후 백엔드에 “있으면 좋은 정규화 필드”를 요청하는 방식이 적절하다.

