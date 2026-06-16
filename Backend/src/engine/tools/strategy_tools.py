"""
Node 5 특공/일반공급 전략 비교 툴 (4번)
- compare_supply_strategy: 가능한 특공들을 점수/방식 기준으로 비교해 전략 추천
"""

from langchain_core.tools import tool

# ── 점수제 경쟁력 기준 ────────────────────────────────────────────
COMPETITIVENESS_THRESHOLD = 0.6  # 60% 미만이면 추첨제 우선 추천


def _evaluate_score_supply(supply: dict) -> dict:
    """점수제 특공의 경쟁력 평가"""
    score = supply.get("score")
    max_score = supply.get("max_score")

    if score is None or max_score is None or max_score == 0:
        return {
            "type": supply["type"],
            "method": supply["method"],
            "ratio": None,
            "competitiveness": "알 수 없음",
            "recommend_priority": 99,
        }

    ratio = score / max_score

    if ratio >= 0.8:
        competitiveness = "매우 높음"
        priority = 1
    elif ratio >= 0.6:
        competitiveness = "높음"
        priority = 2
    elif ratio >= 0.4:
        competitiveness = "보통"
        priority = 3
    else:
        competitiveness = "낮음"
        priority = 4

    return {
        "type": supply["type"],
        "method": supply["method"],
        "score": score,
        "max_score": max_score,
        "ratio": round(ratio, 2),
        "competitiveness": competitiveness,
        "recommend_priority": priority,
    }


def _evaluate_lottery_supply(supply: dict) -> dict:
    """추첨제 특공 평가 — 자격 충족 여부를 반영"""
    missing_items = supply.get("missing_items") or []
    status = supply.get("status")

    if status == "가능성 낮음":
        return {
            "type": supply["type"],
            "method": supply["method"],
            "ratio": None,
            "competitiveness": "가능성 낮음",
            "recommend_priority": 9,
            "missing_items": missing_items,
        }

    if missing_items or status == "추가 확인 필요":
        return {
            "type": supply["type"],
            "method": supply["method"],
            "ratio": None,
            "competitiveness": "자격 확인 필요",
            "recommend_priority": 5,
            "missing_items": missing_items,
        }

    return {
        "type": supply["type"],
        "method": supply["method"],
        "ratio": None,
        "competitiveness": "동등 확률",
        "recommend_priority": 2,
        "missing_items": [],
    }


# ── Tool 4: 특공/일반공급 전략 비교 ──────────────────────────────

@tool
def compare_supply_strategy(
    available_supplies: list,
    general_supply_score: int,
    general_max_score: int,
    recommended_supply: str,
) -> dict:
    """
    가능한 특공들과 일반공급을 점수/방식 기준으로 비교해 전략을 추천합니다.

    Args:
        available_supplies: Node 2에서 넘어온 가능한 특공 목록
            [{"type": "신혼부부 특공", "score": 10, "max_score": 13, "method": "가점제"}, ...]
        general_supply_score: 일반공급 가점
        general_max_score: 일반공급 만점
        recommended_supply: Node 2 추천 공급 유형

    Returns:
        dict: {
            "primary": 1순위 추천 공급 유형 및 이유,
            "secondary": 2순위 추천 (있을 경우),
            "all_evaluations": 전체 평가 결과,
            "strategy_summary": 전략 요약 텍스트,
        }
    """
    evaluations = []
    has_lottery = False
    best_score_ratio = 0.0
    best_score_supply = None

    for supply in available_supplies:
        if supply["method"] == "추첨제":
            has_lottery = True
            eval_result = _evaluate_lottery_supply(supply)
        else:
            eval_result = _evaluate_score_supply(supply)
            ratio = eval_result.get("ratio") or 0.0
            if ratio > best_score_ratio:
                best_score_ratio = ratio
                best_score_supply = eval_result

        evaluations.append(eval_result)

    general_ratio = general_supply_score / general_max_score if general_max_score > 0 else 0
    general_eval = {
        "type": "일반공급",
        "method": "가점제",
        "score": general_supply_score,
        "max_score": general_max_score,
        "ratio": round(general_ratio, 2),
        "competitiveness": (
            "매우 높음" if general_ratio >= 0.8
            else "높음" if general_ratio >= 0.6
            else "보통" if general_ratio >= 0.4
            else "낮음"
        ),
        "recommend_priority": (
            1 if general_ratio >= 0.8
            else 2 if general_ratio >= 0.6
            else 3 if general_ratio >= 0.4
            else 4
        ),
    }
    evaluations.append(general_eval)

    eligible_lottery = [
        e for e in evaluations
        if e["method"] == "추첨제" and e.get("recommend_priority", 2) < 5
    ]
    unresolved_lottery = [
        e for e in evaluations
        if e["method"] == "추첨제" and e.get("recommend_priority", 2) >= 5
    ]
    has_eligible_lottery = bool(eligible_lottery)

    if has_eligible_lottery and best_score_ratio < COMPETITIVENESS_THRESHOLD:
        lottery_supply = min(eligible_lottery, key=lambda e: e.get("recommend_priority", 2))
        primary = {
            "type": lottery_supply["type"],
            "reason": (
                f"점수제 특공 경쟁력({best_score_ratio:.0%})이 기준({COMPETITIVENESS_THRESHOLD:.0%}) "
                f"미만으로 낮아 추첨제가 더 유리합니다."
            ),
        }
    elif best_score_supply:
        primary = {
            "type": best_score_supply["type"],
            "reason": (
                f"점수제 특공 경쟁력({best_score_ratio:.0%})이 기준({COMPETITIVENESS_THRESHOLD:.0%}) "
                f"이상으로 높아 점수제 특공이 유리합니다."
            ),
        }
    else:
        excluded_notes = [
            f"{e['type']}은 {', '.join(e['missing_items'])} 미충족으로 제외"
            for e in unresolved_lottery
            if e.get("missing_items")
        ]
        reason = f"현재 즉시 신청 가능한 유형 중 {recommended_supply}이 가장 현실적인 선택입니다."
        if excluded_notes:
            reason += " (" + ", ".join(excluded_notes) + ")"
        primary = {
            "type": recommended_supply,
            "reason": reason,
        }

    secondary_candidates = [
        e for e in evaluations
        if e["type"] != primary["type"] and e.get("recommend_priority", 2) < 9
    ]
    secondary_candidates.sort(
        key=lambda e: (e.get("recommend_priority", 2), -(e.get("ratio") or 0.0))
    )
    secondary_eval = secondary_candidates[0] if secondary_candidates else None
    secondary = (
        {
            "type": secondary_eval["type"],
            "reason": (
                "자격 확인이 더 필요하지만 함께 검토할 수 있습니다."
                if secondary_eval.get("recommend_priority", 2) == 5
                else "추첨제 특공도 동등한 기회로 함께 고려할 수 있습니다."
                if secondary_eval["method"] == "추첨제"
                else "보조 전략으로 함께 신청을 고려할 수 있습니다."
            ),
        }
        if secondary_eval
        else None
    )

    unresolved_notes = [
        f"{e['type']}: {', '.join(e['missing_items'])} 확인 필요"
        for e in evaluations
        if e["method"] == "추첨제" and e.get("missing_items")
    ]

    strategy_summary = (
        f"{primary['type']}을 1순위로 신청하는 것을 권장합니다. {primary['reason']}"
        + (f" {secondary['type']}도 함께 고려하세요." if secondary else "")
        + (" " + " / ".join(unresolved_notes) if unresolved_notes else "")
    )

    return {
        "primary": primary,
        "secondary": secondary,
        "all_evaluations": evaluations,
        "strategy_summary": strategy_summary,
    }