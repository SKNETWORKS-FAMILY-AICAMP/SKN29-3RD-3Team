"""
Node 5 당첨확률 계산 툴 (5번)
- calculate_winning_probability: 6단계 점수 기반 당첨확률 계산
"""

from langchain_core.tools import tool

# ── 지역 경쟁도 룰 테이블 ─────────────────────────────────────────

REGION_COMPETITION = {
    "high": {
        "keywords": ["강남", "서초", "송파", "용산", "과천", "성수", "분당", "광교"],
        "penalty": 0,
        "label": "고경쟁 지역",
    },
    "medium": {
        "keywords": ["동탄", "수원", "인천", "부산", "대구", "광주"],
        "penalty": 10,
        "label": "중경쟁 지역",
    },
    "low": {
        "keywords": [],  # 위에 해당 없으면 일반 지역
        "penalty": 20,
        "label": "일반 지역",
    },
}

# ── 평형 보정 테이블 ──────────────────────────────────────────────

AREA_BONUS = {
    "59": +10,
    "84": 0,
}


def _get_region_penalty(region: str) -> tuple[int, str]:
    """지역명에서 경쟁도 점수 반환"""
    for level, info in REGION_COMPETITION.items():
        if level == "low":
            continue
        if any(kw in region for kw in info["keywords"]):
            return info["penalty"], info["label"]
    return 20, "일반 지역"  # low 기본값


def _get_area_bonus(area: str) -> tuple[int, str]:
    """평형에서 보정값 반환 (예: '84㎡' → 0)"""
    area_num = area.replace("㎡", "").replace(" ", "").strip()
    try:
        area_int = int(area_num)
        if area_int <= 59:
            return +10, "59㎡ 이하 (공급 많음)"
        elif area_int <= 84:
            return 0, "84㎡ (경쟁 보통)"
        else:
            return -10, "84㎡ 초과 (공급 적음)"
    except ValueError:
        return 0, "평형 정보 없음"


def _get_user_competitiveness(score: int | None, max_score: int | None, method: str) -> tuple[int, str]:
    if method == "추첨제":
        return 0, "추첨제 (경쟁력 무관)"

    if score is None or max_score is None:
        return 15, "Node2 점수 미연결 (기본값 적용)"

    ratio = score / max_score
    if ratio >= 0.8:
        return 30, f"점수 {score}/{max_score} (매우 우수)"
    elif ratio >= 0.6:
        return 20, f"점수 {score}/{max_score} (우수)"
    elif ratio >= 0.4:
        return 10, f"점수 {score}/{max_score} (보통)"
    else:
        return 0, f"점수 {score}/{max_score} (낮음)"


def _get_supply_count_bonus(supply_count: int) -> tuple[int, str]:
    """공급 물량 보너스"""
    if supply_count >= 100:
        return 30, f"공급 {supply_count}세대 (많음)"
    elif supply_count >= 50:
        return 20, f"공급 {supply_count}세대 (보통)"
    elif supply_count >= 20:
        return 10, f"공급 {supply_count}세대 (적음)"
    else:
        return 0, f"공급 {supply_count}세대 (매우 적음)"


def _normalize_score(raw_score: int) -> int:
    """
    최대 가능 점수 기준으로 정규화 (0~100)
    추첨제 최대: 40 + 0 + 30 + 0 + 10 + 20 = 100
    가점제 최대: 10 + 30 + 30 + 0 + 10 + 20 = 100
    패널티(-20, -10) 반영 시 음수 가능 → 최소 0으로 클램핑
    """
    return max(0, min(100, raw_score))


def _get_residency_priority_penalty(is_same_region: bool | None) -> tuple[int, str]:
    """거주지역과 건설지역 일치 여부에 따른 우선공급 보정"""
    if is_same_region is None:
        return 0, "거주지역 우선공급 여부 확인 불가"
    if is_same_region:
        return 0, "해당지역 거주자로 우선공급 대상에 해당"
    return -15, "해당지역 거주자가 아니므로 우선공급 대상에서 제외, 기타지역 자격으로 경쟁"

# ── Tool 5: 평형별 당첨확률 계산 ──────────────────────────────────

@tool
def calculate_winning_probability(
    supply_type: str,
    score: int | None,
    max_score: int | None,
    method: str,
    supply_count: int,
    region: str,
    area: str,
    recommended_supply: str,
    is_same_region: bool | None = None,
) -> dict:
    """
    6단계 점수와 거주지역 우선공급 여부를 바탕으로 특공/일반공급의 당첨확률을 계산합니다.

    Args:
        supply_type: 공급 유형 (예: "신혼부부 특공", "생애최초 특공", "일반공급")
        score: Node 2에서 계산된 점수 (추첨제는 None)
        method: 공급 방식 ("추첨제" | "가점제")
        supply_count: 공급 세대수
        region: 청약 대상 건설지역
        area: 희망 평형 (예: "84㎡")
        recommended_supply: Node 2 추천 공급 유형
        is_same_region: 사용자 거주지역과 건설지역의 일치 여부 (check_regional_priority 결과)

    Returns:
        dict: {
            "supply_type": 공급 유형,
            "winning_score": 최종 점수 (0~100),
            "probability": 경쟁력 지표 ("상" | "중" | "하"),
            "breakdown": 단계별 점수 상세,
            "reasons": 판정 이유 목록,
            "methodology_notice": 추정 방식과 한계에 대한 안내문,
        }
    """
    reasons = []
    breakdown = {}

    # 1단계: 공급 방식
    if method == "추첨제":
        method_score = 40
        reasons.append("추첨제 — 가점 낮아도 동등한 기회")
    else:
        method_score = 10
        reasons.append("가점제 — 고가점자에게 불리")
    breakdown["공급방식"] = method_score

    # 2단계: 사용자 경쟁력
    comp_score, comp_reason = _get_user_competitiveness(score, max_score, method)
    breakdown["사용자경쟁력"] = comp_score
    reasons.append(comp_reason)

    # 3단계: 공급 물량
    count_score, count_reason = _get_supply_count_bonus(supply_count)
    breakdown["공급물량"] = count_score
    reasons.append(count_reason)

    # 4단계: 지역 경쟁도
    region_penalty, region_reason = _get_region_penalty(region)
    breakdown["지역경쟁도"] = region_penalty
    if region_penalty < 0:
        reasons.append(f"{region_reason} — 경쟁 치열")

    # 5단계: 평형 보정
    area_bonus, area_reason = _get_area_bonus(area)
    breakdown["평형보정"] = area_bonus
    reasons.append(area_reason)

    # 6단계: 추천 카드 보정
    if supply_type == recommended_supply:
        rec_bonus = 20
        reasons.append(f"추천 공급 유형과 일치 (+20)")
    else:
        rec_bonus = 0
    breakdown["추천카드"] = rec_bonus

    # 7단계: 거주지역 우선공급 보정
    residency_penalty, residency_reason = _get_residency_priority_penalty(is_same_region)
    breakdown["거주지역우선순위"] = residency_penalty
    reasons.append(residency_reason)

    # 최종 점수 계산 및 정규화
    raw_score = (
        method_score
        + comp_score
        + count_score
        + region_penalty
        + area_bonus
        + rec_bonus
        + residency_penalty
    )
    winning_score = _normalize_score(raw_score)

    # 상/중/하 판정
    if winning_score >= 80:
        probability = "상"
    elif winning_score >= 50:
        probability = "중"
    else:
        probability = "하"

    methodology_notice = (
        "이 지표는 공급 세대수, 지역 경쟁도, 보유 점수, 추천 유형 일치 여부, 거주지역 우선공급 여부를 "
        "기반으로 계산한 참고용 경쟁력 추정치입니다. 실제 신청자 수(경쟁률)는 반영되지 않았으며, "
        "실제 당첨 확률은 신청자 수에 따라 이 추정과 크게 다를 수 있습니다."
    )

    return {
        "supply_type": supply_type,
        "winning_score": winning_score,
        "probability": probability,
        "breakdown": breakdown,
        "reasons": reasons,
        "methodology_notice": methodology_notice,
    }