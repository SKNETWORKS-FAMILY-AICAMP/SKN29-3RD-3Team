from src.pipeline import resume_with_announcement


def process_announcement(session_id: str, announcement_text: str) -> dict:
    """
    공고문 텍스트를 받아 Node 4 재개 후 Node 5~6 실행.
    상세 리포트 반환.
    """
    result = resume_with_announcement(session_id, announcement_text)
    return result
