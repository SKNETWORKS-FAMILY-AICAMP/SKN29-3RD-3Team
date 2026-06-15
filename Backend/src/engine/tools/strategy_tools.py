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
    """추첨제 특공 평가 — 조건 충족 시 동등 확률"""
    return {
        "type": supply["type"],
        "method": supply["method"],
        "ratio": None,
        "competitiveness": "동등 확률",
        "recommend_priority": 2,
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

    # 특공별 평가
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

    # 일반공급 평가
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

    # ── 전략 판정 ─────────────────────────────────────────────────
    if has_lottery and best_score_ratio < COMPETITIVENESS_THRESHOLD:
        # 추첨제 우선
        lottery_supply = next(
            (e for e in evaluations if e["method"] == "추첨제"), None
        )
        primary = {
            "type": lottery_supply["type"] if lottery_supply else "추첨제 특공",
            "reason": (
                f"점수제 특공 경쟁력({best_score_ratio:.0%})이 기준({COMPETITIVENESS_THRESHOLD:.0%}) "
                f"미만으로 낮아 추첨제가 더 유리합니다."
            ),
        }
        secondary = {
            "type": best_score_supply["type"] if best_score_supply else recommended_supply,
            "reason": "점수제 특공도 신청 가능하나 경쟁이 치열할 수 있습니다.",
        }
        strategy_summary = (
            f"현재 점수제 특공 경쟁력이 {best_score_ratio:.0%}로 기준({COMPETITIVENESS_THRESHOLD:.0%})에 "
            f"미치지 못합니다. 추첨제 특공({primary['type']})을 1순위로 신청하고, "
            f"점수제 특공은 보조 전략으로 활용하는 것을 권장합니다."
        )
    else:
        # 점수제 우선
        primary = {
            "type": best_score_supply["type"] if best_score_supply else recommended_supply,
            "reason": (
                f"점수제 특공 경쟁력({best_score_ratio:.0%})이 기준({COMPETITIVENESS_THRESHOLD:.0%}) "
                f"이상으로 높아 점수제 특공이 유리합니다."
            ),
        }
        secondary = None
        if has_lottery:
            lottery_supply = next(
                (e for e in evaluations if e["method"] == "추첨제"), None
            )
            secondary = {
                "type": lottery_supply["type"] if lottery_supply else None,
                "reason": "추첨제 특공도 동등한 기회로 함께 고려할 수 있습니다.",
            }

        strategy_summary = (
            f"현재 점수제 특공 경쟁력이 {best_score_ratio:.0%}로 충분합니다. "
            f"{primary['type']}을 1순위로 신청하는 것을 권장합니다."
            + (
                f" {secondary['type']}(추첨제)도 병행 신청을 고려하세요."
                if secondary else ""
            )
        )

    return {
        "primary": primary,
        "secondary": secondary,
        "all_evaluations": evaluations,
        "strategy_summary": strategy_summary,
    }
