"""Frontend constants and option values."""

ACCOUNT_TYPE_OPTIONS = [
    "주택청약종합저축",
    "청약저축",
    "청약예금",
    "청약부금",
]

REGION_OPTIONS = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]

YES_NO_OPTIONS = [
    {"value": True, "label": "O", "description": "해당합니다"},
    {"value": False, "label": "X", "description": "해당하지 않습니다"},
]

MARITAL_STATUS_OPTIONS = [
    {"value": "MARRIED", "label": "기혼", "description": "혼인 상태입니다"},
    {"value": "ENGAGED", "label": "예비 신혼부부", "description": "결혼 예정 상태입니다"},
    {"value": "NOT_MARRIED", "label": "미혼", "description": "혼인 상태가 아닙니다"},
]

CHILD_STATUS_OPTIONS = [
    {"value": "HAS_CHILD", "label": "있음", "description": "미성년 자녀, 태아 또는 입양 예정 자녀가 있습니다"},
    {"value": "NO_CHILD", "label": "없음", "description": "해당 자녀가 없습니다"},
]

HOMELESS_PERIOD_OPTIONS = [
    {"value": 0, "label": "1년 미만"},
    {"value": 2, "label": "1년 이상 3년 미만"},
    {"value": 4, "label": "3년 이상 5년 미만"},
    {"value": 5, "label": "5년 이상"},
]

MINOR_CHILDREN_OPTIONS = [
    {"value": "UNDER_TWO", "label": "2명 미만", "description": "0명 또는 1명"},
    {"value": "TWO_OR_MORE", "label": "2명 이상", "description": "만 19세 미만 자녀 2명 이상"},
]

PROPERTY_HISTORY_OPTIONS = [
    {"value": True, "label": "O", "description": "주택 구입/소유 이력이 있습니다"},
    {"value": False, "label": "X", "description": "주택 구입/소유 이력이 없습니다"},
]

DETAIL_FIELD_OPTIONS = {
    "youngest_child_age_group": {
        "label": "가장 어린 자녀 연령",
        "options": [
            {"value": "UNDER_2", "label": "2세 미만", "description": "신생아 특별공급 후보 확인"},
            {"value": "AGE_2_TO_6", "label": "2세 이상 7세 미만", "description": "자녀 관련 특별공급 보조 판단"},
            {"value": "AGE_7_PLUS_MINOR", "label": "7세 이상 미성년", "description": "미성년 자녀 조건 보조 판단"},
            {"value": "UNKNOWN", "label": "모름", "description": "자녀 생년월일 확인 필요"},
        ],
    },
    "child_count_group": {
        "label": "미성년 자녀 수",
        "options": [
            {"value": "ONE", "label": "1명"},
            {"value": "TWO_OR_MORE", "label": "2명 이상"},
            {"value": "UNKNOWN", "label": "모름"},
        ],
    },
    "housing_history": {
        "label": "과거 주택 소유 이력",
        "options": [
            {"value": "NO_HISTORY", "label": "없음"},
            {"value": "SPOUSE_PREMARRIAGE_DISPOSED", "label": "배우자 혼인 전 처분"},
            {"value": "OTHER_HISTORY", "label": "기타 이력 있음"},
            {"value": "UNKNOWN", "label": "모름"},
        ],
    },
    "elderly_support": {
        "label": "노부모 부양 여부",
        "options": [
            {"value": "MEETS_65_AND_3Y", "label": "65세 이상 3년 이상 부양", "description": "노부모부양 특별공급 후보 확인"},
            {"value": "DOES_NOT_MEET", "label": "해당 없음", "description": "노부모부양 특별공급 가능성 낮음"},
            {"value": "UNKNOWN", "label": "모름", "description": "주민등록상 부양기간 확인 필요"},
        ],
    },
}

SIMULATE_CHOICE_OPTIONS = [
    {"value": True, "label": "예, 공고 기반 상세 시뮬레이션을 원해요", "description": "공고문 정보를 입력해 상세 리포트를 받습니다"},
    {"value": False, "label": "아니요, 기본 리포트만 볼게요", "description": "입력한 프로필 기준의 기본 리포트만 받습니다"},
]

RECOMMENDED_QUESTIONS = [
    "청약통장 가입일은 왜 필요한가요?",
    "무주택 기간은 어떻게 계산하나요?",
    "세대주가 아니면 청약이 불가능한가요?",
    "자녀 2명 이상 기준은 어디에 쓰이나요?",
]
