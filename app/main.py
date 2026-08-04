from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.api.v1.router import api_router
from app.core.rate_limit import limiter
from app.config import settings

app = FastAPI(title="ANCHOR", description="Agentic RAG Career Sustainability Copilot")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "anchor"}

app.include_router(api_router, prefix="/api/v1")

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
