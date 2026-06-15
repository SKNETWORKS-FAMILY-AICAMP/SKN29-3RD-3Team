# Frontend

Streamlit 기반 청약 자가진단 UI입니다. 기본 실행 모드는 `auto`이며, FastAPI를 먼저 호출하고 연결 실패 시 mock 응답으로 fallback합니다.

## 구조

```text
frontend/
├─ streamlit_app.py                 # 메인 Streamlit entrypoint
├─ pages/                           # Streamlit multi-page entrypoints
│  ├─ 1_청약_자가진단.py
│  └─ 2_FAQ_챗봇.py
├─ components/
│  └─ ui.py                         # 공통 UI 렌더링 함수
├─ config/
│  └─ settings.py                   # 환경변수 기반 API 설정
├─ domain/
│  └─ constants.py                  # 화면 선택지, 추천 질문 등 도메인 상수
├─ services/
│  ├─ api_client.py                 # FastAPI/mock client 선택과 HTTP 호출
│  ├─ mock_api.py                   # 백엔드 연결 실패 시 fallback 응답
│  └─ payload.py                    # Streamlit 입력값 -> API payload 변환
├─ state/
│  └─ diagnosis_state.py            # session_state, widget key, form/detail payload
├─ views/
│  ├─ diagnosis_page.py             # 좌우 컬럼과 단계 라우팅
│  ├─ diagnosis_steps.py            # 단계별 입력 UI
│  ├─ diagnosis_result.py           # 결과/상세 진단 UI
│  └─ chatbot_panel.py              # FAQ 챗봇 패널
├─ requirements.txt
└─ README.md
```

`streamlit_app.py`와 `pages/`는 Streamlit 실행 규칙 때문에 루트에 유지하고, 기능 모듈은 역할별 폴더로 분리했습니다.

## 실행

프로젝트 루트에서 실행합니다.

```powershell
streamlit run frontend\streamlit_app.py
```

## API 모드

기본값은 `auto`입니다.

```powershell
$env:CHEONGYAK_API_MODE="auto"
$env:CHEONGYAK_API_BASE_URL="http://192.168.0.27:8000"
```

모드별 동작:

| 값 | 동작 |
| --- | --- |
| `auto` | FastAPI를 먼저 호출하고 실패하면 mock 응답 사용 |
| `http` | FastAPI 호출을 시도하며, 실패 시 화면에 fallback 상태 표시 |
| `mock` | FastAPI 호출 없이 mock 응답 사용 |

로컬 FastAPI를 사용할 때:

```powershell
$env:CHEONGYAK_API_MODE="auto"
$env:CHEONGYAK_API_BASE_URL="http://127.0.0.1:8000"
streamlit run frontend\streamlit_app.py
```

## 테스트

프로젝트 루트에서 실행합니다.

```powershell
python -m unittest discover -s tests\frontend
python -m compileall -q frontend
```

## 구현 메모

- `services/payload.py`에서 화면 입력값을 백엔드 호환 payload로 변환합니다.
- `services/api_client.py`는 `CHEONGYAK_API_MODE`에 따라 `FastApiDiagnosisClient` 또는 `MockDiagnosisClient`를 선택합니다.
- `services/api_client.py`의 진단 요청은 `/api/v1/diagnose/full-profile`로 전송하며, 혼인기간·자녀 연령·노부모 부양 여부 등 조건부 상세값은 결과 화면 이전에 `detail` payload로 함께 보냅니다.
- 챗봇 패널은 `views/chatbot_panel.py`에서 렌더링하고, `services/api_client.py`의 `chat()`이 `/api/v1/chat`을 호출합니다. 실제 RAG 연결 인수인계는 `../docs/CHATBOT_FRONTEND_HANDOFF.md`를 확인합니다.
- API 연결 실패 시 사용자는 화면에서 fallback 상태와 실패 사유를 확인할 수 있습니다.
