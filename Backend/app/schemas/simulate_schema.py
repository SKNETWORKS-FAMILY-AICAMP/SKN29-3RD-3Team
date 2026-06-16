from pydantic import BaseModel


class SimulateRequest(BaseModel):
    session_id: str
    simulate: bool  # True: 공고문 시뮬레이션 O, False: X


class SimulateResponse(BaseModel):
    status: str
    session_id: str
    message: str
