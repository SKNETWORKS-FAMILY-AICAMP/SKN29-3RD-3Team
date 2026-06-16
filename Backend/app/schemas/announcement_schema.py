from pydantic import BaseModel


class AnnouncementRequest(BaseModel):
    session_id: str
    announcement_text: str  # 사용자가 자유 형식으로 입력한 공고문 텍스트


class AnnouncementResponse(BaseModel):
    status: str
    session_id: str
    report: dict
