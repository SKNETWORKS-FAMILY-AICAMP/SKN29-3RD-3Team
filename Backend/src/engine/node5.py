"""
Node 5: 전략 추론 노드 (하이브리드 ReAct Agent)

실행 순서:
1. 순서 고정 실행: 대출 계산 → 실투자금 계산 → 자금 리스크 분석
2. create_agent: 나머지 툴 자유 호출 (현재 mock)
3. 결과를 State에 저장 후 반환

사용법:
    python node5_strategy.py
"""

import os
from typing import TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from src.engine.tools.rag_tools import check_regional_priority, analyze_subscription_timing
from src.engine.tools.financial import (
    calculate_loan_amount,
    calculate_real_investment,
    analyze_financial_risk,
)
from src.engine.tools.probability_tools import calculate_winning_probability
from src.engine.tools.strategy_tools import compare_supply_strategy

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ── State 정의 ────────────────────────────────────────────────────

class Node5State(TypedDict, total=False):
    # Node 1~2에서 넘어오는 것
    available_supply_types: list[str]
    supply_analysis: dict  
    recommended_supply: str

    # 프론트에서 받은 profile
    profile: dict

    # Node 4에서 넘어오는 것
    announcement: dict

    # Node 5에서 생성되는 결과
    loan_result: dict
    investment_result: dict
    risk_result: dict
    agent_result: str

# ── Node 5 메인 함수 ──────────────────────────────────────────────

def run_node5(state: Node5State) -> Node5State:
    profile = state.get("profile", {})
    announcement = state.get("announcement", {})
    recommended_supply = state.get("recommended_supply", "")
    available_supply_types = state.get("available_supply_types", [])
    supply_analysis = state.get("supply_analysis", {})

    price = announcement.get("price", 0)
    is_regulated = announcement.get("is_regulated", False)
    total_assets = profile.get("total_assets", 0)

    # ── STEP 1: 순서 고정 실행 ────────────────────────────────────
    print("[Node 5] STEP 1: 재무 계산 시작")

    # 1) 대출 가능 금액
    loan_result = calculate_loan_amount.invoke({
        "price": price,
        "is_regulated": is_regulated,
        "recommended_supply": recommended_supply,
    })
    print(f"  대출 가능 금액: {loan_result['loan_amount']:,}원 (LTV {loan_result['ltv_rate']:.0%})")

    # 2) 실투자금
    investment_result = calculate_real_investment.invoke({
        "price": price,
        "loan_amount": loan_result["loan_amount"],
    })
    print(f"  실투자금: {investment_result['real_investment']:,}원")

    # 6) 자금 리스크
    risk_result = analyze_financial_risk.invoke({
        "real_investment": investment_result["real_investment"],
        "total_assets": total_assets,
    })
    print(f"  자금 리스크: {risk_result['risk_level']} (비율 {risk_result['ratio']:.0%})")

    # ── STEP 2: create_react_agent (나머지 툴) ────────────────────
    print("\n[Node 5] STEP 2: ReAct Agent 실행")

    mock_tools = [
        check_regional_priority,
        compare_supply_strategy,
        calculate_winning_probability,
        analyze_subscription_timing,
    ]

    agent = create_react_agent(llm, tools=mock_tools)

    # recommended_supply와 실제로 일치하는 항목을 찾아서 사용
    matched_supply = next(
        (
            s for s in supply_analysis.get("available_supplies", [])
            if s.get("type") == recommended_supply
        ),
        {},
    )

    agent_prompt = f"""
다음 정보를 바탕으로 청약 전략을 분석해주세요.
각 단계 점수의 이유(reasons)를 빠짐없이 사용자에게 설명해주세요.

[사용자 정보]
- 거주지역: {profile.get('region')}
- 무주택 기간: {profile.get('homeless_period_years')}년
- 청약통장 납입 횟수: {profile.get('bankbook_payments')}회
- 월평균 소득: {profile.get('average_monthly_income', '미입력')}원

[공고 정보]
- 건설지역: {announcement.get('region')}
- 공급유형: {announcement.get('supply_type')}
- 분양가: {price:,}원
- 희망 평형: {announcement.get('area')}
- 공급 세대수: {announcement.get('supply_count')}세대

[재무 분석 결과]
- 대출 가능 금액: {loan_result['loan_amount']:,}원 (LTV {loan_result['ltv_rate']:.0%}, {loan_result['area_type']})
- 실투자금: {investment_result['real_investment']:,}원
- 자금 리스크: {risk_result['risk_level']} ({risk_result['description']})

[추천 공급 유형]
- 추천: {recommended_supply}
- 가능 유형: {', '.join(available_supply_types)}

위 정보를 바탕으로 아래 순서대로 툴을 호출해 분석해주세요.
1. check_regional_priority 툴 호출
   - user_region: {profile.get('region')}
   - announcement_region: {announcement.get('region')}
2. compare_supply_strategy 툴 호출
   - available_supplies: {supply_analysis.get('available_supplies', [])}
   - general_supply_score: {supply_analysis.get('general_supply_score')}
   - general_max_score: {supply_analysis.get('general_max_score')}
   - recommended_supply: {recommended_supply}
3. calculate_winning_probability 툴 호출
   - supply_type: {recommended_supply}
   - score: {matched_supply.get('score')}
   - max_score: {matched_supply.get('max_score')}
   - method: {matched_supply.get('method')}
   - supply_count: {announcement.get('supply_count')}
   - region: {announcement.get('region')}
   - area: {announcement.get('area')}
   - recommended_supply: {recommended_supply}
4. analyze_subscription_timing 툴 호출
   - bankbook_type: {profile.get('bankbook_type')}
   - bankbook_payments: {profile.get('bankbook_payments')}
   - bankbook_join_date: {profile.get('bankbook_join_date')}
   - is_regulated: {announcement.get('is_regulated')}
   - supply_type: {announcement.get('supply_type')}
"""

    agent_response = agent.invoke({
        "messages": [{"role": "user", "content": agent_prompt}]
    })
    agent_result = agent_response["messages"][-1].content
    print(f"  Agent 분석 완료")

    # ── STEP 3: State 업데이트 ────────────────────────────────────
    return {
        **state,
        "loan_result": loan_result,
        "investment_result": investment_result,
        "risk_result": risk_result,
        "agent_result": agent_result,
    }


# ── 테스트 실행 ───────────────────────────────────────────────────

if __name__ == "__main__":
    test_state: Node5State = {
        "supply_analysis": {
        "available_supplies": [
            {"type": "신혼부부 특공", "score": 10, "max_score": 13, "method": "가점제"},
            {"type": "생애최초 특공", "score": None, "max_score": None, "method": "추첨제"},
        ],
        "general_supply_score": 42,
        "general_max_score": 84,
        },
        "available_supply_types": ["신혼부부 특공", "생애최초 특공"],
        "recommended_supply": "신혼부부 특공",
        "profile": {
            "region": "서울",
            "is_homeless": True,
            "homeless_period_years": 3,
            "is_household_head": True,
            "num_household_members": 3,
            "bankbook_type": "주택청약종합저축",
            "bankbook_payments": 24,
            "bankbook_balance": 10000000,
            "bankbook_join_date": "2020-01-01",
            "average_monthly_income": 5000000,
            "total_assets": 100000000,
            "birth_year": 1990,
        },
        "announcement": {
            "region": "서울 강남구",
            "is_regulated": True,
            "supply_type": "민간",
            "price": 500000000,
            "deposit": None,
            "area": "84㎡",
            "supply_count": 80,
        },
    }

    result = run_node5(test_state)

    print("\n" + "=" * 60)
    print("Node 5 최종 결과")
    print("=" * 60)
    print(f"\n[대출 결과]\n{result['loan_result']}")
    print(f"\n[실투자금 결과]\n{result['investment_result']}")
    print(f"\n[리스크 결과]\n{result['risk_result']}")
    print(f"\n[Agent 분석]\n{result['agent_result']}")
