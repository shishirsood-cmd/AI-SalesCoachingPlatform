from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, auth, knowledge, organizations, scenarios, sessions, users
from app.core.config import settings

app = FastAPI(title="Sales Coaching Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(scenarios.router)
app.include_router(knowledge.router)
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(organizations.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
