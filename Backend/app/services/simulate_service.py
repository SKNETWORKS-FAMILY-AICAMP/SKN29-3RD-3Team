from src.pipeline import resume_pipeline


def process_simulate(session_id: str, simulate: bool) -> dict:
    """
    simulate O/X 입력 후 파이프라인 재개.
    - simulate: True  → Node 4 인터럽트 (공고문 입력 대기)
    - simulate: False → Node 6 실행 (간단 리포트 반환)
    """
    result = resume_pipeline(session_id, simulate)
    return result
