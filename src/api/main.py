from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.api.routers import auth, accounts, projects, chat, integrations
from src.storage.postgres import init_db

app = FastAPI(
    title="Fulcrum Project Manager API",
    description="Multi-tenant AI-native project orchestration system",
    version="0.1.0"
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(static_dir, "icons", "favicon.png")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return None

@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(integrations.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/sw.js", include_in_schema=False)
async def sw():
    sw_path = os.path.join(static_dir, "sw.js")
    return FileResponse(sw_path)

@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    manifest_path = os.path.join(static_dir, "manifest.json")
    return FileResponse(manifest_path)

@app.get("/", include_in_schema=False)
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "title": "Fulcrum Project Manager",
        "status": "online",
        "documentation": "/docs",
        "message": "Welcome to the Fulcrum AI-native project orchestration system."
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
