# Chatbot-Frontend Integration Handoff

## 목적

현재 브랜치에서 다른 사람이 바로 이어서 맡을 작업은 "Streamlit 챗봇 패널을 실제 RAG/LangGraph 챗봇 응답과 연결"하는 것이다.

단, 바로 진단 상태 기반 전략 상담까지 확장하면 계약이 흐려진다. 먼저 FAQ/RAG 자유질문 연결을 완성하고, 그 다음 진단 상태를 포함하는 context-aware chat으로 확장한다.

## 현재 브랜치

- 작업 브랜치: `codex/frontend-mcp-score-only`
- 기준 worktree: `C:\Users\Playdata\Documents\SKN29-3rd-3team-mcp-score-only`
- 이미 반영된 브랜치:
  - `origin/준억`: Node 1 profile 진단, Node1-Node2 state adapter, source adapter
  - `origin/동윤`: `src/rag`, `src/graph`, `src/preprocessing` 구조와 RAG/Graph 초안

## 현재 연결 상태

| 영역 | 파일 | 상태 |
| --- | --- | --- |
| Streamlit 챗봇 UI | `frontend/views/chatbot_panel.py` | 구현됨. 추천 질문/직접 질문을 `client.chat(question)`으로 전송 |
| Front API client | `frontend/services/api_client.py` | `POST /api/v1/chat` 호출 구현됨 |
| Mock fallback | `frontend/services/mock_api.py` | FastAPI 연결 실패 시 mock 답변 표시 |
| FastAPI router | `backend/src/routers/chat.py` | `/api/v1/chat` endpoint 있음 |
| Chat schema | `backend/src/schemas/chat.py` | `question`, `answer`, `source_refs` 단순 계약 |
| Backend service | `backend/src/services/chat_service.py` | placeholder 응답. 실제 RAG 연결 필요 |
| RAG graph 후보 | `src/rag/chat_graph.py`, `src/rag/rag_graph.py` | 동윤 브랜치에서 반영됨. FastAPI 서비스와 직접 연결은 아직 안 됨 |
| Retriever 후보 | `src/rag/retriever.py` | 검색 함수와 `format_source()` 있음 |

## 먼저 하지 말아야 할 것

- `frontend/views/chatbot_panel.py`를 대규모로 갈아엎지 않는다. 현재 UI는 이미 API client와 mock fallback을 탄다.
- `/api/v1/chat`에 Node 2 전략 브리핑까지 한 번에 섞지 않는다.
- 일반 FAQ/RAG 응답과 진단 상태 기반 전략 상담을 같은 schema로 억지로 처리하지 않는다.
- 신혼부부/다자녀/노부모부양 점수를 일반공급 가점 계산기로 재사용하지 않는다.
- 공고문 정보 없이 당첨확률을 단정하지 않는다.

## MVP 작업 범위

### 1. Backend에서 실제 RAG 답변 연결

우선 `backend/src/services/chat_service.py` 내부만 교체한다.

현재:

```python
def answer_chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(answer="연결 테스트용 응답", source_refs=[...])
```

목표:

```python
def answer_chat(request: ChatRequest) -> ChatResponse:
    # 1. request.question 정리
    # 2. src.rag retriever 또는 chat_graph 호출
    # 3. 답변 텍스트와 출처 label 반환
    return ChatResponse(answer=answer, source_refs=source_refs)
```

MVP에서는 기존 `ChatRequest`/`ChatResponse`를 유지한다.

### 2. import 경로 정리

FastAPI는 `backend/`에서 실행한다.

```powershell
cd backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

반면 RAG 코드는 repo root의 `src/rag`에 있다. 따라서 `chat_service.py`에서 root `src.rag`를 바로 import하면 `backend/src`의 패키지명 `src`와 충돌할 수 있다.

권장 선택지는 둘 중 하나다.

| 선택지 | 설명 | 권장도 |
| --- | --- | --- |
| `backend/src/services/chatbot_rag_adapter.py` 생성 | repo root 경로를 명시적으로 추가하고 RAG 호출을 adapter에 격리 | 높음 |
| RAG 코드를 backend 내부로 이동 | import는 단순해지지만 구조 변경이 커짐 | 낮음 |

adapter 방식 예시:

```python
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.rag.retriever import search, format_source
```

이 import 충돌은 반드시 실제 실행으로 확인해야 한다.

### 3. Frontend는 응답 렌더링만 확인

`frontend/views/chatbot_panel.py`는 이미 아래 응답을 처리한다.

```json
{
  "answer": "답변 본문",
  "source_refs": ["출처1", "출처2"]
}
```

따라서 MVP에서는 프론트 변경 없이도 연결 가능해야 한다.

필요하면 추가할 수 있는 최소 개선:

- 출처를 답변 본문에 붙이는 대신 별도 caption/expander로 표시
- API 연결 실패 상태를 채팅 패널 근처에 표시
- 질문 중복 클릭 방지

## 확장 작업: 진단 상태 기반 챗봇

MVP 이후에만 진행한다.

현재 `ChatRequest`는 질문만 받는다.

```json
{
  "question": "신혼부부 특공이 유리해?"
}
```

진단 결과를 바탕으로 답하려면 새 schema가 필요하다.

권장 확장 schema:

```json
{
  "question": "내 조건이면 어떤 유형이 유리해?",
  "context": {
    "profile": {},
    "detail": {},
    "diagnosis_result": {},
    "node1_state": {},
    "node2_result": {}
  }
}
```

이 확장은 `/api/v1/chat`에 바로 섞기보다 아래 중 하나로 분리하는 편이 안전하다.

- `POST /api/v1/chat/context`
- `POST /api/v1/diagnose/strategy-briefing`
- `POST /api/v1/graph/node2/briefing`

Node 2 전략 브리핑 계약은 `docs/NODE2_DECISION_AND_MCP_TOOLING_SPEC.md`를 따른다.

## 구현 순서

1. `backend/src/services/chatbot_rag_adapter.py`를 만든다.
2. adapter에서 `src/rag/retriever.py`의 `search()`와 `format_source()`를 호출해 최소 답변을 만든다.
3. `backend/src/services/chat_service.py`의 placeholder를 adapter 호출로 교체한다.
4. RAG import 실패, Chroma DB 미존재, OpenAI key 미설정 시 `ChatResponse` 형태의 안전한 실패 응답을 반환한다.
5. `frontend/views/chatbot_panel.py`에서 실제 FastAPI 응답과 mock fallback을 수동 확인한다.
6. 테스트를 추가한다.

## 최소 테스트

Backend:

```powershell
python -m compileall -q backend\src src
```

Frontend:

```powershell
python -m unittest discover -s tests\frontend
```

수동 확인:

```powershell
cd backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

다른 터미널:

```powershell
$env:CHEONGYAK_API_MODE="auto"
$env:CHEONGYAK_API_BASE_URL="http://127.0.0.1:8000"
streamlit run frontend\streamlit_app.py
```

확인 질문:

- `신혼부부 특별공급 기준이 뭐야?`
- `청약통장 납입 횟수는 왜 중요해?`
- `생애최초 특별공급은 어떤 사람이 신청해?`

## 완료 기준

- Streamlit 챗봇 패널에서 질문을 입력하면 FastAPI `/api/v1/chat`을 호출한다.
- FastAPI가 placeholder가 아닌 RAG 기반 답변을 반환한다.
- 답변에 `source_refs`가 포함된다.
- RAG 실패 시에도 화면이 깨지지 않고 fallback/안내 응답을 보여준다.
- `python -m unittest discover -s tests\frontend`가 통과한다.
- `python -m compileall -q frontend backend\src src`가 통과한다.

## 부탁할 때 전달할 문장

아래 그대로 전달하면 된다.

```text
브랜치 `codex/frontend-mcp-score-only`에서 챗봇-프론트 연결을 맡아주세요.

현재 Streamlit 챗봇 UI와 `/api/v1/chat` 호출은 이미 연결되어 있고, 백엔드 `chat_service.py`만 placeholder입니다.
우선 MVP는 `ChatRequest(question)` / `ChatResponse(answer, source_refs)` 계약을 유지한 채 repo root의 `src/rag` 검색 로직을 backend service에 adapter로 연결하는 것입니다.

큰 구조 변경은 하지 말고 `docs/CHATBOT_FRONTEND_HANDOFF.md`의 순서대로 진행해 주세요.
진단 상태 기반 전략 상담은 이번 MVP 이후 별도 endpoint/schema로 분리해야 합니다.
```
