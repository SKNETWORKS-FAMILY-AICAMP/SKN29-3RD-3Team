from fastapi import APIRouter
from app.schemas.simulate_schema import SimulateRequest
from app.services.simulate_service import process_simulate

router = APIRouter()


@router.post("/simulate")
def simulate(request: SimulateRequest):
    result = process_simulate(request.session_id, request.simulate)
    return result