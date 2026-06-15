import json
import os
from typing import Annotated, Any, Dict, List, Literal, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# =====================================================
# [Node 4] OpenAI Tool Calling 전용 공고문 스키마 정의
# =====================================================
class AnnouncementSchema(BaseModel):
    """유저의 자유 대화에서 공고문 필수 데이터를 발췌하여 지정된 데이터형으로 기계적 타입 캐스팅을 수행합니다."""
    region: str = Field(
        ..., description="단지가 위치한 지역 및 구체적인 자치구 (예: '서울 강남구', '경기 수원시')"
    )
    is_regulated: bool = Field(
        ..., description="투기과열지구, 조정대상지역 등 규제지역에 해당하면 True, 비규제지역이면 False"
    )
    supply_type: Literal["민간", "공공", "미정"] = Field(
        ..., description="민간분양/민영주택은 '민간', 공공분양/LH/SH/국민주택은 '공공'"
    )
    price: Optional[int] = Field(
        None, description="대략적인 분양가 또는 매매 금액을 원 단위의 순수 정수로 환산 (예: '5억' -> 500000000, '12억 5천' -> 1250000000). 없거나 모르면 null"
    )
    deposit: Optional[int] = Field(
        None, description="임대보증금 또는 전세보증금 금액을 원 단위의 순수 정수로 환산 (예: '보증금 3억' -> 300000000). 일반 분양이거나 없으면 null"
    )
    area: str = Field(
        ..., description="유저가 원하는 희망 평형 또는 전용면적 사이즈 (예: '84㎡', '59㎡', '34평')"
    )


# =====================================================
# [공통 규칙] 팀 사양 병합 전역 LangGraph State 정의
# =====================================================
class State(BaseModel):
    # Graph 뼈대 인프라 (대화 히스토리 및 인터럽트 추적 스택)
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Graph 공통 상태 (사용자 프로필 - 팀원 스펙 100% 동기화)
    profile: Dict[str, Any] = Field(
        default_factory=lambda: {
            "region": "서울",
            "is_homeless": True,
            "homeless_period_years": 3,
            "is_household_head": True,
            "num_household_members": 3,
            "bankbook_type": "주택청약종합저축",
            "bankbook_join_date": "2024-01-01",
            "bankbook_payments": 24,
            "bankbook_balance": 10000000,
            "average_monthly_income": 5000000,
            "total_assets": 100000000,
            "birth_year": 1990,
            "marital_status": "기혼",
            "marriage_period_years": 5,
            "num_minor_children": 1,
            "supports_elderly_parent": False,
            "has_property_history": False,
        }
    )

    # Node 1 결과 모델 스펙
    node1_available_supply_types: List[str] = Field(default_factory=list)
    node1_supply_checks: List[Any] = Field(default_factory=list)
    node1_missing_profile_keys: List[str] = Field(default_factory=list)
    node1_need_review: bool = True

    # Node 2 결과 모델 스펙
    recommended_supply: Optional[str] = None
    ranked_supply_cards: List[Any] = Field(default_factory=list)
    score_results_by_supply_type: List[Any] = Field(default_factory=list)
    briefing_message: str = ""

    # Node 3 입력 준비 및 분기 트리거 (내 도메인 연동 필드)
    wants_detailed_diagnosis: Literal["예", "아니오"] = "아니오" # 유저의 서비스 이용 선택 상태 적재
    node3_required_complex_fields: List[str] = Field(default_factory=list)

    # Node 4 결과 모델 스펙 (요청하신 정형 딕셔너리 포맷 틀 구현)
    announcement: Dict[str, Any] = Field(
        default_factory=lambda: {
            "region": None,       # str
            "is_regulated": False, # bool
            "supply_type": None,  # str ("민간"/"공공"/"미정")
            "price": None,        # int 또는 null
            "deposit": None,      # int 또는 null
            "area": None          # str
        }
    )

    # 공통 경고/검토사항
    warnings: List[str] = Field(default_factory=list)


# =====================================================
# 1. 앞단 비즈니스 로직 시뮬레이션용 Mock Nodes (1 & 2)
# =====================================================
def mock_node_1_qualify(state: State) -> Dict[str, Any]:
    print("\n📋 [팀원 Node 1] 유저 프로필 기반 청약 조건 정량 필터링 완료.")
    return {
        "node1_available_supply_types": ["GENERAL_SUPPLY", "NEWLYWED_SPECIAL"],
        "node1_need_review": False
    }

def mock_node_2_briefing(state: State) -> Dict[str, Any]:
    print("\n📢 [팀원 Node 2] 1차 최적 추천 카드 선정 및 가점 브리핑 완료.")
    return {
        "recommended_supply": "NEWLYWED_SPECIAL",
        "briefing_message": "신혼부부 특별공급 점수가 가점표 기준 고득점군에 해당하여 가장 유리합니다."
    }


# =====================================================
# 2. [내 담당] NODE 3 : 서비스 지속 여부 조건부 분기 라우터
# =====================================================
def node_3_route_decision(state: State) -> Literal["node_4_interrupt", "node_5_strategy"]:
    """
    유저가 프론트엔드 UI/CLI 화면에서 정밀 진단 서비스 제공 여부를 선택한 상태를 기준으로 분기합니다.
    - '예': 공고문 데이터 강제 정형 추출 구역인 NODE 4 인터럽트 노드로 꺾어 진입
    - '아니오': 공고문 매핑 단계를 스킵하고 즉시 자금 추론 구역인 NODE 5로 직행
    """
    if state.wants_detailed_diagnosis == "예":
        print("\n🔄 [NODE 3 라우터] 유저 정밀 진단 신청('예') 확인 ➡️ NODE 4 인터럽트 노드로 분기합니다.")
        return "node_4_interrupt"
    else:
        print("\n🔄 [NODE 3 라우터] 유저 정밀 진단 거절('아니오') 확인 ➡️ NODE 5 계산 엔진으로 직행합니다.")
        return "node_5_strategy"


# =====================================================
# 3. [내 담당] NODE 4 : 조건 수집 인터럽트 및 타입 구조화 노드
# =====================================================
def node_4_interrupt(state: State) -> Dict[str, Any]:
    """
    인터럽트 함수를 선언하여 제어를 멈추고 프론트로부터 유저 입력 회신을 수신한 뒤,
    OpenAI Native Tool Calling을 적용해 기획서 틀 유형에 맞춰 엄격한 타입 가공을 거쳐 안착시킵니다.
    """
    print("🛑 [NODE 4] 인터럽트 발동: 유저가 관심 단지 문장을 입력할 때까지 그래프 작동을 일시정지합니다.")
    
    # [1단계] LangGraph 표준 인프라 interrupt 구동을 통해 회신(resume) 대기 및 수신
    user_raw_input: str = interrupt(
        {"prompt": "관심 단지의 [지역, 규제여부, 공급유형, 분양가/보증금, 평형] 대화 문장을 수집합니다."}
    )
    
    print(f"\n🔑 [NODE 4] 인터럽트 해제 완료! 전달받은 유저 원문 텍스트:\n   \"{user_raw_input}\"")
    print("🧠 [NODE 4] OpenAI 'with_structured_output' 가동 및 데이터 타입 캐스팅 시작...")
    
    # [2단계] 미리 선언해 둔 AnnouncementSchema 구조체 기반 툴 바인딩 호출
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(AnnouncementSchema, method="function_calling")
    
    # 한글 수치("5억" -> 500000000) 및 불리언 파싱 연산 자동 수행
    extracted_obj: AnnouncementSchema = structured_llm.invoke(user_raw_input)
    announcement_json = extracted_obj.model_dump()
    
    print(f"🎯 [NODE 4 성료] 유저 문장에서 추출된 정형 데이터 규격 동기화 완료.")
    
    return {
        "announcement": announcement_json, # 수정을 요청한 단지 딕셔너리 데이터 적재 처리
        "messages": [
            HumanMessage(content=user_raw_input),
            AIMessage(content=f"선택하신 [{announcement_json['region']}] 단지 요건 검석을 종료했습니다. 후속 엔진을 재가동합니다.")
        ]
    }


# =====================================================
# 4. 뒷단 대출 및 가점 정밀 추론 시뮬레이션용 Mock Node 5
# =====================================================
def mock_node_5_strategy(state: State) -> Dict[str, Any]:
    print("\n🔮 [팀원 Node 5] 결합된 최종 전역 State 파라미터 메모리 출력 스테이지")
    print("==========================================================================")
    print(f"📥 Node 1~2 빌드 정보 추천유형: {state.recommended_supply}")
    print(f"📥 유저 실시간 서비스 요청 동의: {state.wants_detailed_diagnosis}")
    print(f"📥 [수정 통과 완료] 내 노드가 가공한 공고 정형 데이터 틀 (state['announcement']):")
    print(json.dumps(state.announcement, ensure_ascii=False, indent=2))
    print("==========================================================================")
    return {"messages": [AIMessage(content="종합 상담 리포트 산출이 최종 완료되었습니다.")]}


# =====================================================
# 5. LangGraph 파이프라인 그래프 조립 및 체크포인터 바인딩
# =====================================================
workflow = StateGraph(State)

# 노드 인프라 업로드
workflow.add_node("mock_node_1", mock_node_1_qualify)
workflow.add_node("mock_node_2", mock_node_2_briefing)
workflow.add_node("node_4_interrupt", node_4_interrupt)
workflow.add_node("mock_node_5", mock_node_5_strategy)

# 엣지 결합선 매핑
workflow.add_edge(START, "mock_node_1")
workflow.add_edge("mock_node_1", "mock_node_2")

# 💡 NODE 3 Conditional Edges 매핑 처리 구조화
workflow.add_conditional_edges(
    "mock_node_2",
    node_3_route_decision,
    {
        "node_4_interrupt": "node_4_interrupt",
        "node_5_strategy": "mock_node_5"
    }
)

workflow.add_edge("node_4_interrupt", "mock_node_5")
workflow.add_edge("mock_node_5", END)

# 메모리Saver 선언 및 컴파일
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


# =====================================================
# 🏎️ 6. 실시간 상호작용 및 PoC 검증 메인 테스트 구동 블록
# =====================================================
if __name__ == "__main__":
    # 팀원들의 데이터 구조 포맷과 동일한 테스트 원본 payload 선언
    initial_payload = {
        "node1_available_supply_types": [],
        "node1_supply_checks": [],
        "node1_missing_profile_keys": [],
        "node1_need_review": True,
        "recommended_supply": None,
        "ranked_supply_cards": [],
        "score_results_by_supply_type": [],
        "briefing_message": "",
        "node3_required_complex_fields": [],
        "warnings": [],
        "profile": {
            "region": "서울", "is_homeless": True, "homeless_period_years": 3,
            "is_household_head": True, "num_household_members": 3, "bankbook_type": "주택청약종합저축",
            "bankbook_join_date": "2024-01-01", "bankbook_payments": 24, "bankbook_balance": 10000000,
            "average_monthly_income": 5000000, "total_assets": 100000000, "birth_year": 1990,
            "marital_status": "기혼", "marriage_period_years": 5, "num_minor_children": 1,
            "supports_elderly_parent": False, "has_property_history": False
        }
    }
    
    # 세션 관리를 위한 스레드 설정
    config = {"configurable": {"thread_id": "master_poc_session_777"}}
    
    print("🚀 [시뮬레이션 시작] 1차 그래프 구동 엔진을 활성화합니다.")
    
    # 🎯 [실시간 상호작용 1] NODE 3 분기 통제를 위한 실시간 키보드 입력 스위칭 수집
    user_choice = input("\n💬 [NODE 3 선택] 1차 브리핑 확인 완료. 추가 관심 단지 정밀 진단 서비스를 연동하시겠습니까? (예/아니오): ").strip()
    initial_payload["wants_detailed_diagnosis"] = user_choice
    
    # 그래프 running 개시 (인터럽트 지점까지 순차적 런타임 진행)
    for event in app.stream(initial_payload, config, stream_mode="values"):
        pass
        
    # 상태 기록 객체 호출
    current_state = app.get_state(config)
    
    # '예'를 선택하여 그래프가 Node 4 인터럽트 상태에 진입하여 안전하게 일시정지한 경우
    if current_state.next and "node_4_interrupt" in current_state.next:
        print("\n----------------------------------------------------------------------------------")
        print("📶 [인프라 로그] 그래프가 NODE 4 인터럽트 구역 도달을 감지하고 일시정지 스탠바이에 안착했습니다.")
        
        # 🎯 [실시간 상호작용 2] 유저 대화 원문을 터미널에서 실시간 input()으로 타이핑 수신
        print("💬 [NODE 4 입력] 관심 단지의 공고문 요약 혹은 자유로운 대화 문장을 한 줄로 편하게 작성해 주세요.")
        user_chat_text = input(" 입력창 > ").strip()
        print("----------------------------------------------------------------------------------")
        
        print("\n🔄 [인터럽트 해제] Command(resume=) 패턴으로 수집 문자열을 주입하여 그래프를 재개합니다.")
        # ✅ Command(resume=...) 래핑 처리를 완료하여 InvalidUpdateError 발생 원인을 완벽 조치했습니다.
        for event in app.stream(Command(resume=user_chat_text), config, stream_mode="values"):
            pass
            
    print("\n🏁 [시뮬레이션 완료] 전체 그래프의 연동 흐름이 성공적으로 마쳤습니다.")