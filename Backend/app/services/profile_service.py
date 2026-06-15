from app.schemas.profile_schema import UserInput


def process_profile(user_input: UserInput) -> dict:
    """
    사용자 입력을 받아 파이프라인에 넘길 State로 변환합니다.
    현재는 입력값을 그대로 반환하며, 추후 Node 1~6 파이프라인과 연결합니다.
    """
    profile = user_input.profile.model_dump()

    # 추후 파이프라인 연결 시 아래 주석 해제
    # from src.pipeline import run_pipeline
    # result = run_pipeline({"profile": profile})
    # return result

    return {
        "status": "success",
        "profile": profile,
    }
