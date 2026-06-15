from fastapi import FastAPI
from app.routers.app_routers import router

app = FastAPI(title="청약 전략 서비스")

app.include_router(router)