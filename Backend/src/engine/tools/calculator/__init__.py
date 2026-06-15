"""Calculator internals used by engine tool entrypoints."""

from src.engine.tools.calculator.housing_subscription_score import (
    HousingSubscriptionScoreInput,
    HousingSubscriptionScoreOutput,
    calculate_housing_subscription_score,
)
from src.engine.tools.calculator.special_supply import (
    SpecialSupplyInput,
    SpecialSupplyResult,
    calculate_all_supply_results,
    calculate_elderly_parent_special_supply,
    calculate_general_supply_profile_score,
    calculate_multi_child_special_supply,
    calculate_newlywed_special_supply,
    check_first_home_special_supply,
    check_newborn_special_supply,
)


__all__ = [
    "HousingSubscriptionScoreInput",
    "HousingSubscriptionScoreOutput",
    "SpecialSupplyInput",
    "SpecialSupplyResult",
    "calculate_all_supply_results",
    "calculate_elderly_parent_special_supply",
    "calculate_general_supply_profile_score",
    "calculate_housing_subscription_score",
    "calculate_multi_child_special_supply",
    "calculate_newlywed_special_supply",
    "check_first_home_special_supply",
    "check_newborn_special_supply",
]
