import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import get_settings
from app.db import create_tables, dispose_engine, init_engine, session_factory
from app.routers import auth, conversations, uploads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aurafarm")


async def load_image(image_id: str) -> bytes:
    from app.models import Upload

    async with session_factory()() as session:
        upload = await session.get(Upload, image_id)
    if upload is None:
        raise FileNotFoundError(image_id)
    return uploads.upload_path(upload).read_bytes()


async def build_app_graph(stack: AsyncExitStack):
    from app.agents.graph import build_graph
    from app.agents.llm import make_llm
    from app.services.knowledge_base import get_knowledge_base

    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY is not set; chat endpoints will return 503.")
        return None
    checkpointer = await stack.enter_async_context(
        AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_db_path))
    )
    return build_graph(
        orchestrator_llm=make_llm(settings.orchestrator_model),
        remedy_llm=make_llm(settings.remedy_model, temperature=0.2),
        get_kb=get_knowledge_base,
        sessions=session_factory(),
        load_image=load_image,
        checkpointer=checkpointer,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    init_engine()
    await create_tables()
    async with AsyncExitStack() as stack:
        app.state.graph = await build_app_graph(stack)
        yield
    await dispose_engine()


app = FastAPI(title="AuraFarm API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(uploads.router)


@app.get("/health")
async def health():
    return {"status": "ok", "assistant_configured": app.state.graph is not None}
