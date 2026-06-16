# final 기준 프론트엔드 구조와 데이터 흐름

이 문서는 `origin/final`을 받아온 직후의 프론트엔드 구조를 공유하기 위한 설명서다. 현재 워크벤치(`final_front_debug`)에는 테스트 편의를 위한 디버그 프리셋만 추가되어 있으며, 그 외 프론트 구조와 백엔드 연동 방식은 `final` 기준으로 설명한다.

## 1. 전체 역할

프론트엔드는 Streamlit 기반 UI다. 사용자는 화면에서 청약 관련 정보를 단계별로 입력하고, 프론트는 이 값을 백엔드 FastAPI가 받는 payload로 변환한다. 백엔드는 LangGraph 기반 진단을 수행하고, 프론트는 반환된 추천 공급유형, 공고 분석, 재무 분석, 최종 전략을 결과 화면에 표시한다.

```text
사용자
  ↓ 입력
Streamlit 프론트엔드
  ↓ payload 변환
FastAPI 백엔드
  ↓ LangGraph / Node1~Node6 실행
FastAPI 응답
  ↓ 응답 정규화
Streamlit 결과 화면
```

## 2. 폴더 구조와 역할

```text
Frontend/
├─ streamlit_app.py
├─ pages/
├─ components/
├─ config/
├─ domain/
├─ services/
├─ state/
├─ views/
├─ README.md
├─ FINAL_FRONT_DEBUG_CHANGELOG.md
└─ FRONTEND_ARCHITECTURE_FINAL.md
```

### `streamlit_app.py`

Streamlit 메인 진입점이다. 홈 화면을 띄우고, 공통 스타일과 사이드바를 적용한다.

흐름:
```text
main()
  → set_page_style()
  → render_sidebar("home")
  → render_app_header()
  → render_home_screen()
```

### `pages/`

Streamlit 멀티 페이지 진입점이다. 실제 기능 구현은 `views/`에 있고, `pages/` 파일은 해당 view를 호출하는 얇은 entrypoint다.

| 파일 | 역할 |
| --- | --- |
| `1_청약_자가진단.py` | 자가진단 페이지 진입점. `views.diagnosis_page.render_diagnosis_workspace()` 호출 |
| `2_FAQ_챗봇.py` | FAQ 챗봇 페이지 진입점. `views.chatbot_panel.render_chatbot_page()` 호출 |

### `components/`

여러 화면에서 재사용하는 공통 UI 함수가 들어 있다.

| 파일 | 역할 |
| --- | --- |
| `ui.py` | 페이지 스타일, 헤더, 사이드바, 카드형 선택지, 기본 결과 카드, 챗봇 이동 helper 등을 제공 |

주요 함수:
- `set_page_style()`: 전체 CSS와 Streamlit 페이지 설정
- `render_sidebar(active_page)`: 사이드바 메뉴와 API 상태 표시
- `card_choice(...)`: O/X, 혼인 상태, 자녀 여부 같은 카드형 선택 UI
- `render_result(response)`: 상단 Top3와 기본 결과 상태 렌더링

### `config/`

런타임 환경 설정을 읽는다.

| 파일 | 역할 |
| --- | --- |
| `settings.py` | `.env` 또는 환경변수에서 API 모드, API base URL, timeout을 읽음 |

핵심 환경변수:
```text
CHEONGYAK_API_MODE=http|auto|mock
CHEONGYAK_API_BASE_URL=http://127.0.0.1:8000
CHEONGYAK_API_TIMEOUT_SECONDS=60
```

### `domain/`

화면에서 쓰는 고정 선택지와 추천 질문을 모아둔다.

| 파일 | 역할 |
| --- | --- |
| `constants.py` | 통장 종류, 지역, O/X, 혼인 상태, 자녀 여부, 상세 입력 옵션, 시뮬레이션 선택 옵션, 챗봇 추천 질문 |

예:
- `ACCOUNT_TYPE_OPTIONS`
- `REGION_OPTIONS`
- `YES_NO_OPTIONS`
- `DETAIL_FIELD_OPTIONS`
- `SIMULATE_CHOICE_OPTIONS`

### `services/`

프론트와 외부 시스템 사이의 경계 역할을 한다. 입력값을 백엔드 payload로 바꾸고, FastAPI와 통신한다.

| 파일 | 역할 |
| --- | --- |
| `api_client.py` | FastAPI HTTP 호출, mock fallback, 응답 정규화 |
| `payload.py` | Streamlit 입력값을 `DiagnosisForm`으로 묶고 백엔드 호환 payload로 변환 |
| `mock_api.py` | FastAPI 연결 실패 또는 mock 모드에서 사용할 임시 응답 |

### `state/`

Streamlit `session_state`를 다루는 보조 함수와 단계 정의가 들어 있다.

| 파일 | 역할 |
| --- | --- |
| `diagnosis_state.py` | 진단 단계 목록, 위젯 key 관리, session_state 기반 form 생성, 공고문 payload 생성 |

핵심:
- `STEPS`: 입력 단계 정의
- `build_form_from_state()`: session_state → `DiagnosisForm`
- `widget_key()`: Streamlit 위젯 key와 실제 상태 key를 연결
- `persist_widget()`: 위젯 변경값을 session_state에 저장하고 기존 결과 제거
- `build_announcement_payload()`: 공고문 text area 입력값 추출

### `views/`

실제 화면 단위 UI가 들어 있다.

| 파일 | 역할 |
| --- | --- |
| `diagnosis_page.py` | 진단 워크스페이스 전체 레이아웃, 현재 단계에 맞는 step view 호출 |
| `diagnosis_steps.py` | 1~5단계 입력 UI와 이전/다음 navigation |
| `diagnosis_result.py` | 백엔드 호출 실행, 결과 응답 렌더링, 개발자 payload 표시 |
| `chatbot_panel.py` | FAQ 챗봇 화면, 추천 질문, 직접 질문, 채팅 기록 표시 |

## 3. 자가진단 화면 흐름

자가진단은 6단계로 구성된다.

```text
1. 통장 정보
  → 통장 종류, 가입일, 납입 횟수, 예치금

2. 주택/세대 조건
  → 거주지역, 거주기간, 무주택 여부, 세대주 여부, 세대 구성원 수

3. 혼인/자녀 조건
  → 혼인 상태, 혼인기간, 출생 연도, 자녀 여부, 미성년 자녀 수

4. 소득/자산/이력 정보
  → 월평균 소득, 맞벌이 여부, 주택 구입/소유 이력, 총자산, 노부모 부양 여부

5. 공고 정보
  → 상세 시뮬레이션 여부 선택
  → 상세 진행 시 공고문 한 줄 입력

6. 결과
  → 백엔드 호출
  → 추천 순위, 공급유형별 결과, 공고 분석, 재무 분석, 최종 전략 표시
```

화면 이동은 `diagnosis_step` 값으로 관리된다.

```text
Frontend/views/diagnosis_page.py
  → st.session_state["diagnosis_step"] 확인
  → STEPS[step_index]로 현재 단계 결정
  → diagnosis_steps.py 또는 diagnosis_result.py의 렌더 함수 호출
```

## 4. 사용자 입력에서 백엔드 payload까지

### 4.1 입력 저장

각 입력 위젯은 `widget_key()`로 생성한 key를 사용한다. 입력값이 바뀌면 `persist_widget()`이 실제 상태 key에 값을 저장한다.

```text
사용자 입력
  → Streamlit widget key: _input_bankbook_type
  → persist_widget("bankbook_type")
  → st.session_state["bankbook_type"] 저장
```

### 4.2 form 생성

결과 단계에 도달하면 `build_form_from_state()`가 `session_state`를 읽어 `DiagnosisForm`을 만든다.

```text
st.session_state
  → build_form_from_state()
  → DiagnosisForm
```

### 4.3 백엔드 호환 payload 생성

`services/payload.py`에서 `DiagnosisForm`과 detail payload를 합쳐 FastAPI가 받는 형식으로 바꾼다.

```text
DiagnosisForm
  + build_detail_payload()
  → build_backend_compatible_payload()
  → {"profile": clean_profile}
```

대표 변환:
- `bankbook_join_date`: 날짜 객체 → `YYYY-MM-DD` 문자열
- `bankbook_joined_months`: 가입일 기준 개월 수 계산
- `minor_child_count`: 자녀 수 기반으로 다자녀 여부 판단
- `child_count_group`, `youngest_child_age_group`: 상세 입력을 백엔드 profile에 포함
- `is_elderly_parent`, `elderly_parent_years`: 노부모 부양 선택값으로 계산

## 5. 백엔드 호출 흐름

결과 단계에서는 `views/diagnosis_result.py`의 `run_diagnosis()`가 호출된다.

```text
run_diagnosis(form)
  → build_detail_payload()
  → build_backend_compatible_payload()
  → client.diagnose(payload)
  → session_id 수신
  → client.simulate(session_id, wants_detailed)
  → 상세 시뮬레이션이면 client.announcement(session_id, announcement_text)
  → st.session_state["last_diagnosis_response"] 저장
```

FastAPI endpoint 흐름:

```text
POST /api/profile
  → 프로필 기반 Node1~Node3 일부 실행
  → session_id, recommended_supply, supply_rank 등 반환

POST /api/simulate
  → 사용자가 상세 시뮬레이션을 원하는지 Node3 이후 흐름에 전달
  → simulate=false면 기본 리포트
  → simulate=true면 공고문 입력 대기

POST /api/announcement
  → 공고문 텍스트 전달
  → Node4 공고 파싱
  → Node5 전략/재무/당첨 경쟁력 분석
  → Node6 최종 리포트 반환
```

프론트는 백엔드 내부 Node의 세부 계산을 직접 수행하지 않는다. 프론트의 역할은 입력 수집, payload 변환, API 호출, 결과 표시다.

## 6. API client와 응답 정규화

`services/api_client.py`는 HTTP 호출 결과를 결과 화면에서 쓰기 쉬운 형태로 정규화한다.

```text
FastAPI 응답
  → _normalize_profile_response()
  또는 _normalize_resume_response()
  → result_mode, result_status, guide_message, report, node5, node6 등으로 정리
```

API 모드:

| 모드 | 동작 |
| --- | --- |
| `http` | FastAPI를 호출한다. 실패 시 오류를 표시하고 mock fallback으로 대체될 수 있다. |
| `auto` | 짧은 timeout으로 FastAPI를 먼저 시도하고 실패하면 mock 응답으로 UI 검증 가능 |
| `mock` | FastAPI 없이 mock 응답 사용 |

## 7. 결과 화면 렌더링 흐름

결과 화면은 두 층으로 렌더링된다.

```text
render_result_step()
  → run_diagnosis()
  → render_result(response)
  → render_langgraph_result(response)
  → 개발자 확인용 payload expander
```

### 7.1 `components.ui.render_result()`

상단 추천 순위 Top3와 종합 상태를 표시한다.

표시 예:
- 추천 순위 Top3
- 종합 상태
- 결과 모드
- guide_message
- candidate_supply_types

### 7.2 `views.diagnosis_result.render_langgraph_result()`

백엔드 graph 응답의 상세 결과를 표시한다.

주요 섹션:
- 추천 및 자격 요약
- 공급유형별 결과
- 공고 분석
- 재무 분석
- 최종 리포트
- 최종 전략

### 7.3 개발자 확인용 payload

화면 하단 expander에 API 상태와 payload를 노출한다.

```text
API 상태
프로필 payload
백엔드 호환 payload
초기 상세 입력 payload
최종 응답
```

이 영역은 사용자용 UI라기보다 디버깅과 백엔드 연동 확인용이다.

## 8. FAQ 챗봇 흐름

챗봇은 별도 페이지에서 동작한다.

```text
사용자 질문
  → views/chatbot_panel.py
  → get_diagnosis_client().chat(question, session_id)
  → POST /api/chat
  → answer, sources, session_id 수신
  → chat_messages에 누적 표시
```

특징:
- 추천 질문 버튼 제공
- 직접 질문 입력 가능
- 이전 `chat_session_id`가 있으면 이어서 질문
- API 실패 시 mock 응답 사용

## 9. 주요 데이터 흐름도

```text
[사용자]
  │
  │ 1. 단계별 입력
  ▼
[views/diagnosis_steps.py]
  │
  │ widget_key / persist_widget
  ▼
[state/diagnosis_state.py]
  │
  │ build_form_from_state()
  ▼
[services/payload.py]
  │
  │ build_backend_compatible_payload()
  ▼
[services/api_client.py]
  │
  │ POST /api/profile
  │ POST /api/simulate
  │ POST /api/announcement
  ▼
[Backend FastAPI]
  │
  │ Node1~Node6
  ▼
[FastAPI JSON 응답]
  │
  │ normalize response
  ▼
[views/diagnosis_result.py]
  │
  │ render_result / render_langgraph_result
  ▼
[사용자 결과 화면]
```

## 10. 프론트와 백엔드의 책임 구분

| 영역 | 프론트 책임 | 백엔드 책임 |
| --- | --- | --- |
| 입력 | 사용자가 입력하기 쉬운 단계 UI 제공 | 입력값 자체를 받음 |
| 검증 | 빈 값, 단계별 필수값, UI 상관관계 검증 | 제도/계산 기준 검증 |
| 변환 | Streamlit 상태를 FastAPI payload로 변환 | payload를 Node state로 사용 |
| 계산 | 직접 계산하지 않음. 가입 개월 같은 표시 보조 계산은 payload 생성에 사용 | 공급유형, 가점, 공고 파싱, 전략, 재무, RAG 분석 |
| 출력 | 백엔드 응답을 읽기 쉽게 렌더링 | 최종 report와 분석 결과 생성 |
| 디버깅 | payload expander, API 상태 표시 | 로그, trace, node 결과 제공 |

## 11. final_front_debug에서 추가된 임시 요소

`final_front_debug` 워크벤치에는 `origin/final` 확인 편의를 위해 아래 기능만 추가되어 있다.

- 파일: `Frontend/views/diagnosis_page.py`
- 기능: `디버그 입력 프리셋`
- 역할: 대표 테스트 값을 session_state에 채우고 결과 단계로 바로 이동
- 제거 방법:
  - `_render_debug_preset_button()` 호출 삭제
  - `_render_debug_preset_button()` 함수 삭제
  - `_apply_debug_preset()` 함수 삭제

자세한 변경 이력은 `Frontend/FINAL_FRONT_DEBUG_CHANGELOG.md`에 누적한다.
