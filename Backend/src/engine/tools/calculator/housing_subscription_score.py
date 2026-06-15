from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.engine.tools.calculator.housing_subscription_score_constants import (
    get_primary_source_ref,
    load_housing_subscription_score_table,
)


class HousingSubscriptionScoreInput(BaseModel):
    """Input for the general-supply housing subscription score calculator."""

    model_config = ConfigDict(extra="forbid")

    birth_date: date = Field(description="Applicant birth date.")
    is_married: bool = Field(default=False, description="Whether the applicant is married.")
    marriage_date: date | None = Field(
        default=None,
        description="Marriage registration date. Used if marriage happened before age 30.",
    )
    homeless_start_date: date | None = Field(
        default=None,
        description=(
            "Known date when the applicant/spouse became continuously homeless. "
            "If supplied, the later of this date and the legal age/marriage basis is used."
        ),
    )
    dependent_family_count: int = Field(
        ge=0,
        description="Number of dependent family members excluding the applicant.",
    )
    subscription_join_date: date = Field(
        description="Applicant housing subscription savings join date."
    )
    announcement_date: date = Field(
        default_factory=date.today,
        description="Tenant recruitment announcement date used as the calculation basis.",
    )
    spouse_subscription_join_date: date | None = Field(
        default=None,
        description="Spouse housing subscription savings join date for optional merge scoring.",
    )
    include_spouse_subscription_score: bool = Field(
        default=False,
        description="Whether to add the spouse subscription-account bonus under Appendix 1.",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "HousingSubscriptionScoreInput":
        if self.birth_date > self.announcement_date:
            raise ValueError("birth_date must be on or before announcement_date")
        if self.marriage_date and self.marriage_date > self.announcement_date:
            raise ValueError("marriage_date must be on or before announcement_date")
        if self.homeless_start_date and self.homeless_start_date > self.announcement_date:
            raise ValueError("homeless_start_date must be on or before announcement_date")
        if self.subscription_join_date > self.announcement_date:
            raise ValueError("subscription_join_date must be on or before announcement_date")
        if (
            self.spouse_subscription_join_date
            and self.spouse_subscription_join_date > self.announcement_date
        ):
            raise ValueError(
                "spouse_subscription_join_date must be on or before announcement_date"
            )
        return self


class HousingSubscriptionScoreOutput(BaseModel):
    """Output from the general-supply score calculator."""

    homeless_period_years: int
    homeless_score: int
    dependent_family_score: int
    subscription_period_years: int
    subscription_score: int
    spouse_subscription_score: int
    total_score: int
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    need_review: bool = False
    source_refs: list[str] = Field(default_factory=list)


def calculate_housing_subscription_score(
    input_data: HousingSubscriptionScoreInput | dict[str, Any],
) -> HousingSubscriptionScoreOutput:
    """Calculate the general-supply housing subscription score."""

    if not isinstance(input_data, HousingSubscriptionScoreInput):
        input_data = HousingSubscriptionScoreInput.model_validate(input_data)

    table = load_housing_subscription_score_table()
    warnings: list[str] = []
    assumptions: list[str] = [
        "announcement_date is used as the legal calculation basis.",
        "dependent_family_count is assumed to be pre-validated under Appendix 1 dependent-family rules.",
    ]
    need_review = False

    homeless_period_years, homeless_score = _calculate_homeless_period_score(
        input_data,
        table,
        warnings,
        assumptions,
    )

    if input_data.is_married and input_data.marriage_date is None:
        need_review = True
        warnings.append(
            "is_married is true but marriage_date is missing; age-30 basis was used unless another later homeless_start_date was supplied."
        )

    if input_data.homeless_start_date is not None:
        need_review = True
        warnings.append(
            "homeless_start_date was used as an applicant-supplied continuous homeless date; verify disposal/history basis under Articles 23 and 53."
        )

    dependent_family_score = _score_dependent_family(
        input_data.dependent_family_count,
        table,
    )
    applicant_subscription_months = _full_months_between(
        input_data.subscription_join_date,
        input_data.announcement_date,
    )
    applicant_subscription_score = _score_subscription_months(
        applicant_subscription_months,
        table,
    )

    spouse_subscription_score = 0
    subscription_score = applicant_subscription_score
    if input_data.include_spouse_subscription_score:
        if input_data.spouse_subscription_join_date is None:
            need_review = True
            warnings.append(
                "include_spouse_subscription_score is true but spouse_subscription_join_date is missing."
            )
        else:
            spouse_months = _full_months_between(
                input_data.spouse_subscription_join_date,
                input_data.announcement_date,
            )
            spouse_counted_months = spouse_months // 2
            spouse_raw_score = _score_subscription_months(
                spouse_counted_months,
                table,
            )
            max_bonus = table["score_limits"]["spouse_subscription_bonus"]
            subscription_cap = table["score_limits"]["subscription_period"]
            spouse_subscription_score = min(spouse_raw_score, max_bonus)
            subscription_score = min(
                applicant_subscription_score + spouse_subscription_score,
                subscription_cap,
            )
            assumptions.append(
                "spouse_subscription_score uses half of spouse subscription period, capped at 3 points and total subscription score capped at 17."
            )
    elif input_data.spouse_subscription_join_date is not None:
        warnings.append(
            "spouse_subscription_join_date was supplied but include_spouse_subscription_score is false; spouse score was ignored."
        )

    total_limit = table["score_limits"]["total"]
    total_score = min(
        homeless_score + dependent_family_score + subscription_score,
        total_limit,
    )

    return HousingSubscriptionScoreOutput(
        homeless_period_years=homeless_period_years,
        homeless_score=homeless_score,
        dependent_family_score=dependent_family_score,
        subscription_period_years=applicant_subscription_months // 12,
        subscription_score=subscription_score,
        spouse_subscription_score=spouse_subscription_score,
        total_score=total_score,
        warnings=warnings,
        assumptions=assumptions,
        need_review=need_review,
        source_refs=[get_primary_source_ref()],
    )


def _calculate_homeless_period_score(
    input_data: HousingSubscriptionScoreInput,
    table: dict[str, Any],
    warnings: list[str],
    assumptions: list[str],
) -> tuple[int, int]:
    age_30_date = _add_years(input_data.birth_date, 30)

    if not input_data.is_married and input_data.announcement_date < age_30_date:
        assumptions.append(
            "Applicant is unmarried and under 30 on announcement_date; homeless period score is 0."
        )
        return 0, 0

    basis_date = age_30_date
    if input_data.is_married and input_data.marriage_date:
        if input_data.marriage_date < age_30_date:
            basis_date = input_data.marriage_date
            assumptions.append(
                "Marriage registration date was used because marriage occurred before age 30."
            )
        else:
            assumptions.append("Age-30 date was used because marriage did not occur before age 30.")

    if input_data.homeless_start_date and input_data.homeless_start_date > basis_date:
        basis_date = input_data.homeless_start_date

    if basis_date > input_data.announcement_date:
        warnings.append("homeless basis date is after announcement_date; homeless period is treated as 0.")
        return 0, 0

    years = _full_years_between(basis_date, input_data.announcement_date)
    return years, _score_homeless_years(years, table)


def _score_homeless_years(years: int, table: dict[str, Any]) -> int:
    for row in table["tables"]["homeless_period"]:
        if years >= row["min_years"] and (
            row["max_years"] is None or years < row["max_years"]
        ):
            return row["score"]
    raise ValueError(f"no homeless score row for years={years}")


def _score_dependent_family(count: int, table: dict[str, Any]) -> int:
    for row in table["tables"]["dependent_family"]:
        if "count" in row and count == row["count"]:
            return row["score"]
        if "min_count" in row and count >= row["min_count"]:
            return row["score"]
    raise ValueError(f"no dependent-family score row for count={count}")


def _score_subscription_months(months: int, table: dict[str, Any]) -> int:
    for row in table["tables"]["subscription_period"]:
        if months >= row["min_months"] and (
            row["max_months"] is None or months < row["max_months"]
        ):
            return row["score"]
    raise ValueError(f"no subscription score row for months={months}")


def _full_years_between(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return max(years, 0)


def _full_months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)
