"""
Node 5 재무 계산 툴
- calculate_loan_amount: 대출 가능 금액 계산
- calculate_real_investment: 실투자금 계산
- analyze_financial_risk: 자금 리스크 분석
"""

from langchain_core.tools import tool

# ── LTV 기준표 ────────────────────────────────────────────────────

LTV_TABLE = {
    "regulation_area": {
        "first_home": 0.7,
        "general": 0.4,
    },
    "non_regulation_area": {
        "first_home": 0.8,
        "general": 0.7,
    },
}

# 생애최초로 판단하는 키워드
FIRST_HOME_KEYWORDS = ["생애최초"]


def _is_first_home(recommended_supply: str) -> bool:
    """추천 공급 유형이 생애최초인지 판단"""
    return any(kw in recommended_supply for kw in FIRST_HOME_KEYWORDS)


def _get_ltv(is_regulated: bool, is_first_home: bool) -> float:
    """규제지역 여부 + 생애최초 여부로 LTV 반환"""
    area_key = "regulation_area" if is_regulated else "non_regulation_area"
    supply_key = "first_home" if is_first_home else "general"
    return LTV_TABLE[area_key][supply_key]


# ── Tool 1: 대출 가능 금액 계산 ───────────────────────────────────

@tool
def calculate_loan_amount(
    price: int,
    is_regulated: bool,
    recommended_supply: str,
) -> dict:
    """
    분양가와 규제지역 여부, 추천 공급 유형을 바탕으로 대출 가능 금액을 계산합니다.

    Args:
        price: 분양가 (원)
        is_regulated: 규제지역 여부
        recommended_supply: 추천 공급 유형 (예: "신혼부부 특공", "생애최초 특공")

    Returns:
        dict: {
            "loan_amount": 대출 가능 금액 (원),
            "ltv_rate": 적용된 LTV 비율,
            "area_type": 지역 유형 ("규제지역" | "비규제지역"),
            "supply_type": 공급 유형 ("생애최초" | "일반"),
        }
    """
    first_home = _is_first_home(recommended_supply)
    ltv = _get_ltv(is_regulated, first_home)
    loan_amount = int(price * ltv)

    return {
        "loan_amount": loan_amount,
        "ltv_rate": ltv,
        "area_type": "규제지역" if is_regulated else "비규제지역",
        "supply_type": "생애최초" if first_home else "일반",
    }


# ── Tool 2: 실투자금 계산 ─────────────────────────────────────────

@tool
def calculate_real_investment(
    price: int,
    loan_amount: int,
) -> dict:
    """
    분양가에서 대출 가능 금액을 제외한 실제 투자 필요 금액을 계산합니다.

    Args:
        price: 분양가 (원)
        loan_amount: 대출 가능 금액 (원) — calculate_loan_amount 결과 사용

    Returns:
        dict: {
            "real_investment": 실투자금 (원),
            "price": 분양가 (원),
            "loan_amount": 대출 가능 금액 (원),
        }
    """
    real_investment = price - loan_amount

    return {
        "real_investment": real_investment,
        "price": price,
        "loan_amount": loan_amount,
    }


# ── Tool 6: 자금 리스크 분석 ──────────────────────────────────────

@tool
def analyze_financial_risk(
    real_investment: int,
    total_assets: int,
) -> dict:
    """
    실투자금과 총자산을 비교해 자금 리스크를 분석합니다.

    Args:
        real_investment: 실투자금 (원) — calculate_real_investment 결과 사용
        total_assets: 보유 총자산 (원)

    Returns:
        dict: {
            "risk_level": 리스크 수준 ("낮음" | "중간" | "높음"),
            "ratio": 실투자금 / 총자산 비율 (0~1),
            "real_investment": 실투자금 (원),
            "total_assets": 총자산 (원),
            "description": 리스크 설명,
            "action_items": 리스크 수준에 따른 구체적 행동지침 목록,
        }
    """
    if total_assets <= 0:
        return {
            "risk_level": "높음",
            "ratio": None,
            "real_investment": real_investment,
            "total_assets": total_assets,
            "description": "총자산 정보가 없어 리스크를 정확히 판단할 수 없습니다. 자금 계획을 신중히 검토하세요.",
            "action_items": [
                "보유 자산(예금, 적금, 투자금, 부동산 등)을 다시 한번 정리해 입력해보세요.",
                "총자산 파악 후 실투자금 대비 자금 부담 수준을 다시 확인하세요.",
            ],
        }

    ratio = real_investment / total_assets

    if ratio < 0.5:
        risk_level = "낮음"
        description = (
            f"실투자금({real_investment:,}원)이 총자산({total_assets:,}원)의 "
            f"{ratio:.0%}로, 자금 부담이 낮은 편입니다."
        )
        action_items = [
            "현재 자금 여력은 충분하지만, 중도금 대출 한도와 금리 조건은 미리 확인해두세요.",
            "잔금 납부 시점의 자금 일정을 미리 정리해두면 좋습니다.",
        ]
    elif ratio < 0.8:
        risk_level = "중간"
        description = (
            f"실투자금({real_investment:,}원)이 총자산({total_assets:,}원)의 "
            f"{ratio:.0%}로, 자금 여유가 제한적입니다. 비상 자금 확보를 권장합니다."
        )
        action_items = [
            "중도금 대출 가능 여부와 한도를 은행에 미리 확인하세요.",
            "잔금 조달 계획을 구체적으로 세워두세요 (예: 추가 저축, 기존 자산 매도 시점 등).",
            "예상치 못한 지출에 대비할 비상 자금을 별도로 확보해두는 것을 권장합니다.",
        ]
    else:
        risk_level = "높음"
        description = (
            f"실투자금({real_investment:,}원)이 총자산({total_assets:,}원)의 "
            f"{ratio:.0%}로, 자금 부담이 매우 높습니다. 추가 자금 조달 계획이 필요합니다."
        )
        action_items = [
            "중도금 대출 가능 여부와 최대 한도를 반드시 사전에 확인하세요.",
            "잔금 조달을 위한 추가 자기자본 확보 방안(저축, 자산 매도, 가족 지원 등)을 구체적으로 검토하세요.",
            "현재 자금 수준으로 부담이 큰 경우, 분양가가 더 낮은 단지나 소형 평형도 함께 비교해보세요.",
        ]

    return {
        "risk_level": risk_level,
        "ratio": round(ratio, 4),
        "real_investment": real_investment,
        "total_assets": total_assets,
        "description": description,
        "action_items": action_items,
    }