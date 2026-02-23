import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.activity import router as activity_router
from app.api.blocks import router as blocks_router
from app.api.chat import router as chat_router
from app.api.pipelines import router as pipelines_router
from app.api.webhooks import router as webhooks_router
from app.api.sse import router as sse_router
from app.api.whatsapp import router as whatsapp_router
from app.api.websocket import router as websocket_router
from app.config import settings
from app.database import init_db
from app.engine.scheduler import rehydrate_schedules, shutdown_scheduler, start_scheduler
from app.integrations.paid_client import init_paid_tracing

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = logging.DEBUG if settings.debug else logging.INFO

# Console handler (stdout)
logging.basicConfig(level=LOG_LEVEL, format=LOG_FMT)

# File handler — rotates daily, keeps 30 days
_file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_DIR / "agentflow.log",
    when="midnight",
    backupCount=30,
    encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter(LOG_FMT))
_file_handler.setLevel(LOG_LEVEL)
logging.getLogger().addHandler(_file_handler)

logger = logging.getLogger("agentflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Paid.ai must init before any LLM client is created
    init_paid_tracing()
    logger.info("Initializing database...")
    init_db()
    start_scheduler()
    rehydrate_schedules()
    logger.info("AgentFlow started.")
    yield
    logger.info("AgentFlow shutting down.")
    shutdown_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(activity_router)
app.include_router(chat_router)
app.include_router(pipelines_router)
app.include_router(blocks_router)
app.include_router(webhooks_router)
app.include_router(sse_router)
app.include_router(websocket_router)
app.include_router(whatsapp_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
