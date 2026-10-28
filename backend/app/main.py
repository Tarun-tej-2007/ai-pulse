from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, CORS_ORIGIN_REGEX
from .db import Base, engine
from .routes import auth_routes, diagnostic, reports, dashboard, practice_plan

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Pulse API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth_routes.router)
app.include_router(diagnostic.router)
app.include_router(reports.router)
app.include_router(dashboard.router)
app.include_router(practice_plan.router)


@app.get("/health")
def health():
    return {"status": "ok"}
