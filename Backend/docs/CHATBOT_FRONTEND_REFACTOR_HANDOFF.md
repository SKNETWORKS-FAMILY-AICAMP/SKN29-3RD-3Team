# 챗봇 프론트 리팩터링 인수인계

## 목적

기존에는 청약 자가진단 메인 화면 오른쪽에 챗봇 패널이 함께 배치되어 있었습니다. 이 구조는 입력 폼이 주인공이어야 하는 화면에서 시선을 분산시키고, 챗봇 영역이 비어 있을 때 미완성 화면처럼 보이는 문제가 있었습니다.

이번 리팩터링은 메인 화면을 자가진단 폼 중심으로 정리하고, 챗봇은 별도 페이지에서 ChatGPT/Claude와 비슷한 대화 흐름으로 사용할 수 있게 분리하는 방향입니다.

## 변경 전 구조

- `diagnosis_page.py`
  - 좌측: 자가진단 입력 폼
  - 우측: `render_chatbot_panel()` 챗봇 패널
- `chatbot_panel.py`
  - 메인 화면 우측 사이드 패널로 동작
  - 추천 질문이 위쪽에 있고, 그 아래 대화 영역과 입력 폼이 배치됨
- `왜 필요한가요?`
  - 하드코딩된 간단 설명만 표시
  - 챗봇과 직접 연결되는 흐름 없음

## 변경 후 구조

- 메인 자가진단 화면은 입력 폼만 표시합니다.
- 챗봇은 `Frontend/pages/2_FAQ_챗봇.py` 별도 페이지에서 표시합니다.
- 각 단계의 `왜 필요한가요?` 설명 영역에 `더 알아보기` 버튼을 추가했습니다.
- `더 알아보기` 클릭 시 대표 질문을 `st.session_state["pending_chat_question"]`에 저장하고 챗봇 페이지로 이동합니다.
- 챗봇 페이지는 `pending_chat_question`이 있으면 자동으로 질문을 실행합니다.
- 챗봇 페이지 내부 구성은 다음 순서입니다.
  - 채팅 내용
  - 추천 질문
  - 사용자 입력 폼
- 챗봇 페이지는 전역 `청약 자가진단` 헤더를 사용하지 않고, `FAQ 챗봇` 헤더만 표시합니다.

## 파일별 변경 내용

### `Frontend/views/diagnosis_page.py`

변경 이유:

- 메인 화면에서 챗봇 패널을 제거해 자가진단 폼에 집중시키기 위함입니다.

주요 변경:

- `render_chatbot_panel` import 제거
- 좌우 분할 레이아웃 제거
- `render_diagnosis_workspace()`가 자가진단 폼만 렌더링하도록 변경

결과:

- 메인 화면은 조건 입력과 결과 흐름만 담당합니다.

### `Frontend/components/ui.py`

변경 이유:

- `왜 필요한가요?` 설명 영역에서 챗봇 페이지로 자연스럽게 연결하기 위함입니다.
- 챗봇 입력 폼이 일반 Streamlit form처럼 보이지 않도록 최소 스타일을 보강하기 위함입니다.

주요 변경:

- `CHATBOT_PAGE = "pages/2_FAQ_챗봇.py"` 추가
- `render_explanation()`에 아래 선택 인자 추가
  - `learn_more_question`
  - `learn_more_key`
- `더 알아보기` 버튼 클릭 시 `open_chatbot_with_question()` 호출
- `open_chatbot_with_question()`에서 질문을 `st.session_state["pending_chat_question"]`에 저장
- 가능하면 `st.switch_page()`로 챗봇 페이지 이동
- Streamlit 버전/환경 문제로 이동 실패 시 사이드바에서 챗봇을 선택하라는 안내 표시
- 챗봇 form/전송 버튼 스타일 보강

핵심 흐름:

```python
st.session_state["pending_chat_question"] = question
st.switch_page("pages/2_FAQ_챗봇.py")
```

### `Frontend/views/diagnosis_steps.py`

변경 이유:

- 각 단계의 설명에서 사용자가 더 알고 싶은 내용을 바로 챗봇으로 이어갈 수 있게 하기 위함입니다.

주요 변경:

- 각 `render_explanation()` 호출에 대표 질문을 연결했습니다.
- 적용된 단계:
  - 통장 정보
  - 주택/세대 조건
  - 혼인/자녀 조건
  - 선택 정보

예시:

```python
render_explanation(
    "왜 필요한가요?",
    [...],
    learn_more_question="청약통장은 왜 필요하고 가입일, 납입 횟수, 예치금은 어떻게 판단에 쓰이나요?",
    learn_more_key="learn_more_account",
)
```

### `Frontend/views/chatbot_panel.py`

변경 이유:

- 기존 패널 컴포넌트를 별도 챗봇 페이지에서도 재사용 가능하게 만들기 위함입니다.
- `st.markdown("<div>")`로 Streamlit 컴포넌트를 감싸는 방식은 실제 DOM에서 안정적으로 동작하지 않으므로 제거했습니다.
- 추천 질문이 입력창과 가까운 위치에 있어야 사용자가 다음 질문을 이어가기 쉽습니다.

주요 변경:

- `render_chatbot_page()` 추가
- `render_chatbot_panel()`은 실제 Streamlit 컨테이너인 `st.container(border=True)` 기반으로 유지
- `_consume_pending_question()` 추가
  - `pending_chat_question`을 읽고 제거
  - 챗봇 페이지 진입 시 자동 질문 실행
- 화면 구성 순서 변경
  - `_render_message_area()`: 채팅 내용 표시
  - `_render_suggested_questions()`: 추천 질문 표시
  - `_render_input_form()`: 사용자 입력 폼 표시
- 추천 질문은 항상 입력 폼 바로 위에 표시
- 입력 폼은 `st.columns([9, 1])`를 사용해 입력창 오른쪽에 전송 버튼을 배치
- 전송 버튼은 `"↑"` 텍스트를 사용해 챗봇 서비스의 전송 버튼 느낌에 가깝게 구성
- `pending_chat_question`은 API 호출 전에 먼저 사용자 메시지로 추가합니다.
  - 따라서 자가진단 화면의 `더 알아보기`에서 넘어와도 기존 채팅 내역과 새 질문이 먼저 보입니다.
  - 이후 spinner와 함께 답변을 받아오고, 응답 저장 후 rerun합니다.

핵심 흐름:

```python
pending_question = st.session_state.pop("pending_chat_question", None)
if pending_question:
    _ask(str(pending_question))
```

입력 폼 구조:

```python
with st.form("chatbot_input_form", clear_on_submit=True):
    input_col, send_col = st.columns([9, 1])
    with input_col:
        custom_question = st.text_input(...)
    with send_col:
        submitted = st.form_submit_button("↑", use_container_width=True)
```

### `Frontend/pages/2_FAQ_챗봇.py`

변경 이유:

- 챗봇을 메인 화면의 보조 패널이 아니라 독립 페이지로 제공하기 위함입니다.

주요 변경:

- 기존 안내 문구 제거
- 전역 `render_app_header()` 호출 제거
- `render_chatbot_page()`를 호출하도록 변경

결과:

- Streamlit 사이드바에서 `FAQ 챗봇` 페이지로 접근 가능
- 자가진단 화면의 `더 알아보기` 버튼에서 이동 가능
- 챗봇 페이지 상단에서 `청약 자가진단`, `FAQ 챗봇`, `챗봇` 설명이 반복 노출되지 않음

## 전달 시 설명 포인트

- 메인 페이지는 자가진단 폼 전용 화면으로 정리했습니다.
- 챗봇은 별도 페이지에서 동작하도록 분리했습니다.
- `왜 필요한가요?`의 설명은 그대로 유지하고, `더 알아보기` 버튼만 추가했습니다.
- 버튼은 설명 전문을 넘기지 않고 대표 질문 문장만 넘깁니다.
- 질문 전달은 `st.session_state`를 사용하므로 백엔드 API 구조 변경 없이 프론트에서만 처리됩니다.
- `st.switch_page()`가 동작하지 않는 환경에서는 사이드바 이동 안내로 fallback합니다.
- 챗봇 페이지는 `채팅 내용 -> 추천 질문 -> 입력 폼` 순서로 구성했습니다.
- 입력 폼은 오른쪽에 전송 버튼이 붙은 구조입니다.
- 자가진단 화면에서 넘어온 질문은 먼저 채팅 내역에 사용자 메시지로 표시한 뒤 답변을 생성합니다.

## 확인한 것

```powershell
..\..\.venv\Scripts\python.exe -m compileall -q Frontend
..\..\.venv\Scripts\python.exe -m unittest discover -s tests\Frontend
```

프론트 컴파일과 기존 프론트 테스트는 통과했습니다.
