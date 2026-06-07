"""
api.py — SmartClause FastAPI application entry point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import create_tables, settings
from auth.router import router as auth_router
from routers.contracts import router as contracts_router
from routers.extractions import router as extractions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await create_tables()
    yield


app = FastAPI(
    title="SmartClause API",
    version="1.0.0",
    description="ASC 606 Contract Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(contracts_router)
app.include_router(extractions_router)


@app.get("/")
def root():
    return {"service": "SmartClause API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
