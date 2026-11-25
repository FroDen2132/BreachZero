"""FastAPI application entry point for BreachZero."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache.sqlite_cache import SqliteIocCache
from app.core.room_manager import RoomManager
from app.core.scenario_loader import ScenarioLoader
from app.enrichers.registry import EnricherRegistry
from app.ws.router import router

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIOS_DIR = ROOT_DIR / "scenarios"
DEFAULT_CACHE_DB = ROOT_DIR / "data" / "ioc_cache.db"


def create_app(
    scenarios_dir: Optional[Path] = None,
    cache_db_path: Optional[Path] = None,
    reconnect_grace_seconds: float = 15.0,
    tick_interval_seconds: float = 1.0,
) -> FastAPI:
    sc_dir = scenarios_dir or DEFAULT_SCENARIOS_DIR
    db_path = cache_db_path or DEFAULT_CACHE_DB

    scenario_loader = ScenarioLoader(sc_dir)
    cache = SqliteIocCache(db_path)
    enricher_registry = EnricherRegistry(cache=cache)
    room_manager = RoomManager(
        scenario_loader=scenario_loader,
        enricher_registry=enricher_registry,
        reconnect_grace_seconds=reconnect_grace_seconds,
        tick_interval_seconds=tick_interval_seconds,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        for room in list(room_manager.rooms.values()):
            if room.tick_task and not room.tick_task.done():
                room.tick_task.cancel()
            for sess in room.sessions.values():
                if sess.grace_task and not sess.grace_task.done():
                    sess.grace_task.cancel()

    app = FastAPI(title="BreachZero SOC War Room API", version="0.1.0", lifespan=lifespan)
    app.state.scenario_loader = scenario_loader
    app.state.cache = cache
    app.state.enricher_registry = enricher_registry
    app.state.room_manager = room_manager

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
