# final_front_debug 변경 추적

이 문서는 `origin/final`을 기준으로 받아온 `final_front_debug` 워크벤치에서, 우리가 추가하거나 바꾼 내용을 누적 기록하기 위한 파일이다.

## 기준 상태

- 기준 브랜치: `origin/final`
- 로컬 워크벤치: `branching/final_front_debug`
- 목적: 백엔드는 `final` 상태를 그대로 확인하고, 프론트 테스트 편의 기능만 최소 추가한다.
- 문서 위치: `Frontend/`
  - root에 새 `docs/` 폴더를 만들지 않고, 프론트 관련 문서는 `Frontend/` 아래에 둔다.

## 변경 내역

### 2026-06-17

#### 1. 디버그 입력 프리셋 추가

- 파일: `Frontend/views/diagnosis_page.py`
- 목적:
  - 동일한 테스트 입력을 매번 단계별로 다시 입력하는 시간을 줄이기 위함.
  - `origin/final`의 결과 화면을 빠르게 반복 확인하기 위함.
- 변경 내용:
  - 진단 화면 상단에 `디버그 입력 프리셋` expander 추가.
  - `테스트 입력값 채우고 결과 보기` 버튼 추가.
  - 버튼 클릭 시 Streamlit `session_state`에 대표 테스트 값을 주입.
  - 공고 기반 상세 시뮬레이션 선택값도 함께 `True`로 설정.
  - 입력 후 바로 결과 단계로 이동하도록 `diagnosis_step`을 마지막 단계로 설정.
- 주요 입력값:
  - 통장: 주택청약종합저축, 가입일 2024-01-01, 납입 24회, 예치금 1,000만 원
  - 주택/세대: 서울, 무주택, 세대주, 세대원 4명
  - 혼인/자녀: 기혼, 미성년 자녀 2명
  - 소득/자산: 외벌이, 월평균 소득 500만 원, 총자산 1억 원
  - 공고: 서울 강남구, 투기과열지구, 민간, 전용 84㎡, 분양가 5억, 공급 80세대
- 역할:
  - 실제 진단 로직을 바꾸지 않는 테스트 편의 기능.
  - 배포 전 제거 대상.
- 검증:
  - `Frontend/views/diagnosis_page.py` 컴파일 통과.

#### 2. final 응답 구조 및 결과 화면 개선 분석 문서 추가

- 파일: `Frontend/FINAL_RESPONSE_PAYLOAD_ANALYSIS.md`
- 목적:
  - `origin/final` 백엔드 응답을 프론트가 어떻게 받아 화면에 표시하는지 정리하기 위함.
  - 이후 결과 화면을 고도화할 때 백엔드 수정 없이 가능한 범위와 백엔드 협의가 필요한 범위를 구분하기 위함.
- 변경 내용:
  - `/api/profile` → `/api/simulate` → `/api/announcement` 호출 흐름 정리.
  - `pipeline.py`의 최종 응답 구조와 `api_client.py`의 정규화 구조 정리.
  - `supply_rank`, `report`, `announcement`, `finance`, `node5`, `node6`의 화면 활용 가치 분석.
  - 현재 결과 화면의 UX 문제와 개선 우선순위 정리.
- 역할:
  - final 백엔드 기준 결과 화면 개선을 위한 설계 기준 문서.
  - 개발자 공유용 payload/렌더링 매핑 문서.
- 검증:
  - 코드 동작 변경 없음.

#### 3. Node2 점수제 경쟁력 문구 보정

- 파일: `Backend/src/engine/node2.py`
- 목적:
  - 점수 비율이 45%인 다자녀 특공도 `경쟁력 있음`으로 표시되어 사용자에게 과한 신호를 주는 문제를 보정하기 위함.
  - 점수제 공급유형의 상대 경쟁력을 프론트에서 더 명확히 표시할 수 있도록 하기 위함.
- 변경 내용:
  - 파일 상단 docstring에 수정 사유, 수정 위치, 수정 내용을 간단히 기록.
  - `_score_competitiveness()` 추가:
    - 80% 이상: `매우 높음`
    - 60% 이상: `높음`
    - 40% 이상: `보통`
    - 40% 미만: `낮음`
  - `_score_reason()` 추가:
    - 점수 비율에 맞춰 사용자-facing 추천 사유 문구 생성.
  - `_scored_entry()` 반환값에 `competitiveness` 필드 추가.
  - 기존 `점수 비율 XX%로 경쟁력 있음` 일괄 문구를 구간별 문구로 변경.
- 역할:
  - 신혼부부 특공 75%는 `경쟁력 높음`으로 표시.
  - 다자녀 특공 45%는 `보통 수준`으로 표시.
  - 이후 프론트 Top3 카드에서 `competitiveness`를 badge로 사용할 수 있음.
- 검증:
  - `python -m py_compile Backend/src/engine/node2.py` 통과.

#### 4. 로컬 실행용 ChromaDB 복사

- 파일/경로: `Backend/src/preprocessing/chroma_db/`
- 목적:
  - FastAPI 실행 중 Node5 RAG 검색에서 `Collection [law_chunks] does not exist` 로그가 반복되는 문제 해결.
  - `final_front_debug`의 ChromaDB가 빈 DB 상태였기 때문에, 직전 작업환경의 정상 로컬 DB를 사용해 로컬 실행을 가능하게 하기 위함.
- 변경 내용:
  - 원본: `branching/eunjin_front_v1/Backend/src/preprocessing/chroma_db/`
  - 대상: `branching/final_front_debug/Backend/src/preprocessing/chroma_db/`
  - 기존 빈 DB는 복사 과정에서 임시 백업 후 제거.
  - `chroma_db`는 `.gitignore` 대상이므로 깃 추적 대상에는 포함하지 않음.
- 역할:
  - Node5 및 RAG retriever가 필요한 6개 collection을 로컬에서 조회할 수 있게 함.
  - 백엔드 코드 로직 변경 없이 실행 데이터만 보강.
- 검증:
  - Chroma 컬렉션 확인 완료:
    - `web_faq_chunks`: 120
    - `faq_chunks`: 480
    - `manual_chunks`: 144
    - `lh_guide_chunks`: 18
    - `guide_chunks`: 76
    - `law_chunks`: 163

#### 5. 랜딩페이지 카피 개선

- 파일: `Frontend/components/ui.py`
- 목적:
  - 첫 진입 화면에서 기능 설명보다 사용자가 얻는 결과를 먼저 이해하도록 하기 위함.
  - 개발자 관점의 내부 표현을 줄이고, 진단 시작 행동을 더 자연스럽게 유도하기 위함.
- 변경 내용:
  - 메인 카피를 `청약 조건을 먼저 정리해 보세요`에서 `내 청약 가능성을 먼저 확인해보세요`로 변경.
  - 서브 카피를 입력 절차 중심에서 결과 가치 중심으로 변경.
  - 기능 카드 3개를 `자가진단 / 공고 정보 / FAQ 챗봇`에서 `추천 공급유형 Top 3 / 가점과 자격 근거 / 공고 기준 상세 분석`으로 변경.
  - `백엔드 Node4` 같은 내부 구현 표현 제거.
  - CTA 버튼을 `자가진단하러 가기`에서 `내 청약 가능성 확인하기`로 변경.
- 역할:
  - 사용자가 “무엇을 입력해야 하는지”보다 “무엇을 알 수 있는지”를 먼저 인지하게 함.
  - 결과 화면 UX 개편 전에 첫 진입 경험을 가볍게 개선.
- 검증:
  - `python -m py_compile Frontend/components/ui.py` 통과.

#### 6. 랜딩페이지 레이아웃 적극 개선

- 파일: `Frontend/components/ui.py`
- 목적:
  - 기존 랜딩이 기능 설명 위주라 첫 화면의 매력과 행동 유도력이 약한 문제를 개선하기 위함.
  - 사용자가 진단 후 받게 될 결과를 첫 화면에서 미리 상상할 수 있도록 하기 위함.
- 변경 내용:
  - 랜딩 본문을 단일 텍스트 블록에서 2열 hero 구조로 변경.
  - 왼쪽에는 `3분 청약 진단` 키커, 핵심 헤드라인, 결과 가치 중심 설명, 주요 확인 항목 pill을 배치.
  - 오른쪽에는 `진단 결과 미리보기` 패널을 추가.
    - 1순위 추천
    - 경쟁력
    - 추가 확인 항목
    - 결과에서 확인 가능한 정보 안내
  - 기존 3개 기능 카드는 유지하되, hero 아래 보조 설명 영역으로 역할을 조정.
  - 모바일에서는 1열로 자연스럽게 쌓이도록 반응형 CSS 추가.
- 역할:
  - 첫 진입 화면을 단순 소개 페이지가 아니라 “결과를 미리 보여주는 진단 시작 화면”으로 전환.
  - 결과 화면 UX 개편 방향과 랜딩 메시지가 연결되도록 함.
- 검증:
  - `python -m py_compile Frontend/components/ui.py` 통과.

#### 7. 랜딩페이지 시선 흐름 및 헤더 안정화

- 파일: `Frontend/components/ui.py`
- 목적:
  - 상단 헤더의 `Beta` 버튼이 화면 우상단에서 잘리거나 겹쳐 보이는 문제를 해결하기 위함.
  - 메인 헤드라인의 마지막 글자가 단독 줄로 떨어지는 문제를 줄이고, CTA를 더 빠르게 발견하도록 하기 위함.
- 변경 내용:
  - 헤더 우상단 `Beta` popover 제거.
    - API 상태는 이미 사이드바에 표시되므로 랜딩 상단에서는 제외.
  - 메인 헤드라인을 `내게 유리한 청약 유형을 / 먼저 확인해보세요`로 변경해 줄바꿈 안정화.
  - CTA 버튼을 기능 카드 아래에서 hero 바로 아래로 이동.
  - primary 버튼 색상을 기본 red 계열에서 신뢰감 있는 blue 계열로 조정.
  - `Beta` 제거로 더 이상 쓰지 않는 `load_settings` import 제거.
- 역할:
  - 랜딩 첫 화면에서 제목, 결과 미리보기, 시작 버튼의 시선 흐름을 자연스럽게 정리.
  - 개발자용 상태 정보가 첫 진입 경험을 방해하지 않도록 함.
- 검증:
  - `python -m py_compile Frontend/components/ui.py` 통과.

#### 8. 서비스명 `내집각` 반영 및 상단 잘림 보정

- 파일: `Frontend/components/ui.py`
- 목적:
  - 서비스명이 `내집각`으로 정해지는 방향에 맞춰 첫 화면 브랜드를 반영하기 위함.
  - 상단 제목 영역이 Streamlit 기본 툴바/상단 영역과 가까워 잘려 보이는 문제를 완화하기 위함.
- 변경 내용:
  - `st.set_page_config()`의 `page_title`을 `내집각`으로 변경.
  - 상단 헤더 제목을 `청약 자가진단`에서 `내집각`으로 변경.
  - CSS 기반 간단 브랜드 마크 추가.
  - 사이드바 타이틀을 `청약 도우미`에서 `내집각`으로 변경.
  - 본문 상단 padding을 늘려 제목이 위쪽에서 잘려 보이는 문제를 보정.
  - Streamlit 기본 toolbar/decoration/menu를 숨겨 랜딩 상단을 안정화.
- 역할:
  - 제품명이 첫 화면의 주인공으로 보이도록 정리.
  - 별도 이미지 파일 없이 유지보수 가능한 임시 로고/브랜드 마크 제공.
- 검증:
  - `python -m py_compile Frontend/components/ui.py` 통과.

#### 9. 로고 교체 슬롯 및 결과 화면 1차 개편

- 파일:
  - `Frontend/components/ui.py`
  - `Frontend/views/diagnosis_result.py`
- 목적:
  - `내집각` 로고가 아직 확정되지 않았으므로, 임시 텍스트 로고가 고정 브랜드처럼 보이지 않게 하기 위함.
  - 결과 화면을 개발자 응답 상태 중심이 아니라 사용자 판단 순서 중심으로 재구성하기 위함.
- 변경 내용:
  - 상단 브랜드 마크를 `내` 텍스트 로고에서 교체 가능한 빈 로고 슬롯 형태로 변경.
  - 결과 화면 상단에 `내집각 진단 결과` hero 영역 추가.
    - 추천 공급유형 기반 한 줄 결론
    - 사용자용 요약 문장
    - 상태칩: 추천 유형 확인, 공고 기준 반영, 자금 부담, 진단 완료
  - `success`, `ANNOUNCEMENT_FLOW` 같은 개발자 상태 문구를 상단 결과에서 제거.
  - `지금 확인할 일` 영역 추가.
  - Top3 카드를 개선:
    - `가점제/추첨제` 방식 badge 표시
    - `competitiveness` badge 표시
    - 점수와 ratio 표시
    - 점수 근거와 확인 필요 항목을 각 카드 내부 expander로 이동
  - 상세 공고/재무/전략 분석은 `상세 근거 보기` expander로 이동.
  - 전략 분석 원문은 한 번 더 접어서 기본 화면이 길어지지 않도록 정리.
  - 금액 표기를 `500,000,000원`에서 `5억 원`처럼 읽기 쉬운 형태로 변경.
- 역할:
  - 결과 화면을 “백엔드 응답 로그”가 아니라 “사용자용 진단 결과지”에 가깝게 조정.
  - 상단에서 결론과 다음 행동을 먼저 보고, 필요한 경우 근거를 펼쳐 보도록 정보 계층 재정렬.
- 검증:
  - `python -m py_compile Frontend/components/ui.py Frontend/views/diagnosis_result.py` 통과.

#### 10. 추적 중인 Python 캐시 파일 제거

- 파일/경로:
  - `Backend/**/__pycache__/*.pyc`
  - `Frontend/**/__pycache__/*.pyc`
  - `.gitignore`
- 목적:
  - `final` 브랜치에 이미 올라간 Python 실행 캐시 파일을 PR에서 제거하기 위함.
  - 이후 같은 캐시 파일이 다시 추적되지 않도록 `.gitignore`를 보정하기 위함.
- 변경 내용:
  - Git이 추적 중이던 `*.pyc` 파일을 삭제.
  - `.gitignore`의 `__pycachec__/` 오타를 `__pycache__/`로 수정.
  - `__init__.py`는 패키지 구성에 필요할 수 있으므로 삭제 대상에서 제외.
  - `.gitignore`에서 `__init__.py` 무시 규칙 제거.
- 역할:
  - PR에 불필요한 Python 캐시 바이너리가 포함되지 않도록 정리.
  - 향후 패키지 초기화 파일은 정상적으로 추적 가능하게 함.
- 검증:
  - `git ls-files "*.pyc"` 결과 없음.

#### 11. 입력 검증 경고와 챗봇 출처 표시 개선

- 파일:
  - `Frontend/views/diagnosis_steps.py`
  - `Frontend/views/chatbot_panel.py`
  - `Frontend/components/ui.py`
- 목적:
  - 자가진단 입력 단계에서 필수값 경고가 여러 개의 빨간 박스로 쌓여 화면이 지저분해지는 문제를 줄이기 위함.
  - FAQ 챗봇 답변에서 출처가 본문 끝에 긴 문자열로 붙거나 중복되어 답변 가독성을 해치는 문제를 개선하기 위함.
  - 백엔드 RAG 흐름은 유지하고, 프론트 표시 방식 중심으로 정리하기 위함.
- 변경 내용:
  - `다음` 버튼을 눌렀을 때만 현재 단계의 필수 입력 오류를 검사하고, 여러 오류를 요약 경고 1개로 표시.
  - 오류 요약을 버튼 컬럼 내부가 아니라 버튼 행 아래 전체 폭으로 이동해 `이전`/`다음` 버튼의 수평 정렬을 유지.
  - 사용자가 입력값을 고치면 기존 경고 요약이 현재 오류 상태에 맞춰 자동 갱신/해제되도록 처리.
  - 입력 단계 중간에 즉시 표시되던 일부 빨간 오류를 안내성 caption으로 완화.
  - 세대 구성원 수의 `min_value=1` 컴포넌트 제약을 제거해 브라우저 기본 검증 말풍선 대신 프론트 요약 검증으로 안내되도록 변경.
  - 챗봇 응답의 `answer`와 `sources`를 분리해 세션에 저장.
  - 답변 본문에 섞여 들어온 `출처:`/`참고 자료:` 라인을 프론트에서 분리.
  - 출처 목록은 중복 제거 후 `참고한 자료` expander 안에 chip 형태로 표시.
  - 긴 출처명은 UI 라벨로 정리하고 과도하게 길면 말줄임 처리.
- 역할:
  - 사용자는 입력 중 빨간 경고에 계속 노출되지 않고, 다음 단계로 넘어가려는 시점에만 수정할 항목을 확인할 수 있음.
  - 검증 메시지가 버튼 자리를 밀어내지 않아 이전/다음 내비게이션 정렬이 유지됨.
  - 챗봇 답변은 본문과 출처가 분리되어 읽기 쉬워지고, 출처는 필요할 때 접어서 확인할 수 있음.
- 검증:
  - `python -m py_compile Frontend/views/diagnosis_steps.py Frontend/views/chatbot_panel.py Frontend/components/ui.py` 통과.

#### 12. 발표용 라이트/다크 테마 선택 추가

- 파일:
  - `Frontend/components/ui.py`
- 목적:
  - 발표 환경에서 브라우저/OS 설정이나 화면 밝기에 맞춰 서비스를 빠르게 전환할 수 있도록 하기 위함.
  - Streamlit 기본 `Deploy`/툴바 대신 서비스 내부에서 제어 가능한 테마 선택 경험을 제공하기 위함.
  - 기존 라이트모드의 신뢰감 있는 블루 기반 톤을 다크모드에서도 유지하기 위함.
- 변경 내용:
  - 사이드바 상단 `내집각` 아래에 `화면 테마` 선택 컨트롤 추가.
    - `라이트`
    - `다크`
  - `st.session_state["theme_mode"]`로 선택값 유지.
  - 페이지 이동 시 테마가 `라이트`로 되돌아가는 문제를 줄이기 위해 `theme` query param과 Streamlit cache 기반 테마 저장소에 선택값 동기화.
  - `set_page_style()` 내부에 `_theme_css()`를 연결해 라이트/다크 색상 토큰을 주입.
  - Streamlit 기본 테마는 런타임 변경이 불가능해, 혼선을 줄이기 위해 `시스템 설정` 옵션은 제거.
  - 주요 커스텀 UI 영역에 다크모드 override 적용:
    - 랜딩 hero/preview/feature 카드
    - 결과 hero/status chip/next action
    - 자가진단 guide/stepper/container
    - 챗봇 출처 chip
    - 입력 검증 요약 카드
    - 사이드바와 주요 입력 컴포넌트
  - 다크모드에서 흰색으로 남던 보조 버튼, disabled 버튼, number input 증감 버튼, select/input 배경을 추가 보정.
  - 실제 화면 확인 결과를 바탕으로 상단 Streamlit header, selectbox 드롭다운 listbox, label/caption 텍스트 대비를 추가 보정.
  - 추가 화면 확인 결과를 바탕으로 placeholder, expander, JSON/code payload, chat message, chat input, segmented control 색상 보정.
  - 다크모드에서 `라이트/다크` segmented control의 비선택 항목이 흰색으로 튀는 문제와 채팅 메시지 박스 대비를 추가 보정.
  - `라이트/다크` 선택 UI를 Streamlit 기본 segmented control에서 버튼형 토글로 변경해 새 탭/링크 이동 없이 현재 화면에서 즉시 전환되도록 수정.
  - 다크모드 placeholder를 더 밝게 조정하고 number input의 `-`/`+` 아이콘 대비를 추가 보정.
  - 다크모드에서 bordered container 경계가 묻히는 문제를 줄이기 위해 경계선 색과 inset shadow를 보강.
  - 결과 Top3 카드를 HTML 기반 고정 높이 카드로 변경해 라이트/다크 모두 카드 크기와 정보 구조를 통일.
  - 추천 카드의 `확인 필요` 표현을 `조건 미달 가능 항목`으로 변경해 부족 정보와 기준 미달 의미가 혼동되지 않도록 조정.
  - 다크모드 텍스트/버튼/채팅 답변의 대비를 높여 발표 화면에서 긴 답변을 읽기 쉽도록 보정.
- 역할:
  - 발표 중 라이트/다크 화면을 즉시 비교할 수 있음.
  - 완전한 Streamlit 테마 교체가 아니라, 현재 서비스 디자인 언어를 유지하는 커스텀 UI 중심 다크모드로 안정성 확보.
- 검증:
  - `python -m py_compile Frontend/components/ui.py` 통과.

#### 13. 결과 화면 재실행 버튼 위치 조정

- 파일:
  - `Frontend/views/diagnosis_result.py`
- 목적:
  - 사용자가 결과 내용을 읽기 전에 상단에서 바로 `자가진단 다시 실행`을 보게 되는 흐름을 줄이기 위함.
  - 이전 단계의 `이전`/`다음` 내비게이션과 같은 위치 감각으로 결과 화면 행동을 배치하기 위함.
- 변경 내용:
  - 결과 화면 상단의 `자가진단 다시 실행` 버튼 제거.
  - 기존 공통 하단 내비게이션의 `다음` 위치에 `자가진단 다시 시작` primary 버튼 배치.
  - 결과 단계에서는 별도 내비게이션을 새로 만들지 않고 기존 `이전` 버튼 옆에 재실행 버튼만 표시.
  - 버튼 클릭 시 입력값과 결과 캐시를 초기화하고 1단계로 이동하도록 변경.
- 역할:
  - 결과를 충분히 읽은 뒤 처음부터 다시 입력하는 사용자 흐름으로 정리.
  - 결과 단계에서도 이전 단계들과 같은 내비게이션 한 줄 구조 유지.
- 검증:
  - `python -m py_compile Frontend/views/diagnosis_result.py` 통과.

#### 14. Streamlit 버튼 ID 중복 오류 수정

- 파일:
  - `Frontend/views/diagnosis_steps.py`
  - `Frontend/views/diagnosis_result.py`
  - `Frontend/components/ui.py`
- 목적:
  - `이전`/`다음` 버튼이 여러 위치에서 같은 파라미터로 렌더링되며 `StreamlitDuplicateElementId`가 발생하는 문제를 해결하기 위함.
  - 결과 Top3 카드의 빈 상세 문구를 카드 내 짧은 라벨과 맞추기 위함.
- 변경 내용:
  - 스텝 내비게이션 `이전`, `다음` 버튼에 `diagnosis_prev_button_{step_index}`, `diagnosis_next_button_{step_index}` key 추가.
  - 결과 화면 하단 `자가진단 다시 시작` 버튼에 `result_restart_button` key 추가.
  - `reset_diagnosis_state()`를 추가해 테마/챗봇 상태는 유지하고 자가진단 입력값과 결과 캐시만 초기화.
  - 추천 카드의 빈 상세 문구를 `추가로 표시할 세부 근거가 없습니다.`에서 `세부 근거 없음`으로 축약.
- 역할:
  - Streamlit 자동 ID 충돌 방지.
  - 결과 카드의 상세 영역 문구 길이와 시각적 균형 개선.
- 검증:
  - `python -m py_compile Frontend/views/diagnosis_steps.py Frontend/views/diagnosis_result.py Frontend/components/ui.py` 통과.

#### 15. 서비스 표시명 최종 변경

- 파일:
  - `Frontend/components/ui.py`
  - `Frontend/FRONTEND_ARCHITECTURE_FINAL.md`
- 목적:
  - 발표 및 PR 기준 서비스명을 `청약 랭그래프 시스템`으로 통일하기 위함.
- 변경 내용:
  - Streamlit `page_title`을 `청약 랭그래프 시스템`으로 변경.
  - 상단 헤더, 사이드바 타이틀, 결과 화면 kicker의 서비스명을 `청약 랭그래프 시스템`으로 변경.
  - 페이지 아이콘을 `청`으로 변경.
  - 프론트 구조 설명 문서에 현재 서비스 표시명을 명시.
- 역할:
  - 화면과 공유 문서에서 서비스명을 동일하게 보여줌.
- 검증:
  - `python -m py_compile Frontend/components/ui.py Frontend/views/diagnosis_steps.py Frontend/views/diagnosis_result.py Frontend/views/chatbot_panel.py Frontend/state/diagnosis_state.py` 통과.

## 앞으로 기록할 항목

새 변경이 생기면 아래 형식으로 누적한다.

```text
#### 변경 제목

- 파일:
- 목적:
- 변경 내용:
- 역할:
- 검증:
```
