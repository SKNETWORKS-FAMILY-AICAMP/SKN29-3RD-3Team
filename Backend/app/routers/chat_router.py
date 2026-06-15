from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import get_chat_answer

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = get_chat_answer(request.question, request.session_id)
    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        session_id=result["session_id"],
    )
