from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    animals,
    auth,
    breeds,
    chat,
    dashboard,
    evaluations,
    feeds,
    litters,
    scan,
    stall_pages,
    stalls,
    stats,
    weights,
)

Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Kaninchenzucht-Management API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")

app.include_router(auth.router)
app.include_router(breeds.router)
app.include_router(stall_pages.router)
app.include_router(stalls.router)
app.include_router(feeds.router)
app.include_router(animals.router)
app.include_router(weights.router)
app.include_router(evaluations.router)
app.include_router(scan.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
app.include_router(stats.router)
app.include_router(litters.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Ausgeliefertes Frontend (Produktion): `frontend/dist` nach `npm run build`.
# Im lokalen Dev-Betrieb existiert der Ordner nicht (Vite-Dev-Server läuft
# separat auf :5173) -- dann bleibt dieser Block einfach inaktiv.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
