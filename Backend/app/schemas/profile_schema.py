from pydantic import BaseModel
from typing import Optional


class ProfileInput(BaseModel):
    # 통장 정보
    bankbook_type: str                          # 통장 종류
    bankbook_join_date: str                     # 가입일 (YYYY-MM-DD)
    bankbook_payments: int                      # 납입 횟수
    bankbook_balance: int                       # 예치금

    # 주택/세대 정보
    region: str                                 # 거주지역
    residence_period_years: Optional[int] = None# 거주 기간
    is_homeless: bool                           # 무주택 여부
    housing_ownership: bool                     # 주택 소유 현황
    homeless_period_years: int                  # 무주택 기간
    is_household_head: bool                     # 세대주 여부
    num_household_members: int                  # 세대원 수

    # 혼인/자녀 정보
    marital_status: str                         # 혼인 상태
    marriage_period_years: Optional[int] = None
    birth_year: int                             # 출생 연도
    child_status: str                           # 자녀 여부
    minor_child_count: Optional[int] = None     # 미성년자 자녀 수

    # 노부모 부양
    is_elderly_parent: bool = False             # 노부모 부양 여부
    elderly_parent_years: Optional[int] = None  # 부양 기간

    # 선택 → 필수로 전환
    is_dual_income: Optional[bool] = None       # 맞벌이 여부
    average_monthly_income: int                 # 가구 평균소득
    has_property_history: bool                  # 주택 구입/소유 이력
    total_assets: int                           # 총자산


class UserInput(BaseModel):
    profile: ProfileInput
