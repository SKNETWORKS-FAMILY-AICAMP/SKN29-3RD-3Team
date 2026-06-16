from fastapi import APIRouter
from app.schemas.announcement_schema import AnnouncementRequest
from app.services.announcement_service import process_announcement

router = APIRouter()


@router.post("/announcement")
def announcement(request: AnnouncementRequest):
    result = process_announcement(request.session_id, request.announcement_text)
    return result