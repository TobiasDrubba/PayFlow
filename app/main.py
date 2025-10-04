from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.presentation.payments_api import router as payments_router
from app.presentation.user_api import router as auth_router

app = FastAPI(title="Payment API", version="1.0.0")

origins = ["http://localhost:3000", "http://localhost:3005"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(payments_router)
