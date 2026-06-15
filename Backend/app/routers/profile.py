from fastapi import APIRouter
from app.schemas.profile_schema import UserInput
from app.services.profile_service import process_profile

router = APIRouter()


@router.post("/profile")
def submit_profile(user_input: UserInput):
    return process_profile(user_input)
