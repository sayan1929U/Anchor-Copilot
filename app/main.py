from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router

app = FastAPI(title="ANCHOR", description="Agentic RAG Career Sustainability Copilot")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "anchor"}

app.include_router(api_router, prefix="/api/v1")

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
