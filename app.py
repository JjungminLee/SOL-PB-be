from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strategy_api import router as strategy_router
from calendar_api import router as calendar_router

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://sol-pb-fe.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(strategy_router)
app.include_router(calendar_router)


