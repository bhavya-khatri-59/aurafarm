import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import ORCHESTRATOR_NODE
from app.db import get_session, session_factory
from app.models import Conversation, Message, Upload, User
from app.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    SendMessageRequest,
)
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])

DEFAULT_TITLE = "New conversation"
PHOTO_TITLE = "Plant diagnosis"


async def _get_owned(session: AsyncSession, conversation_id: str, user: User) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    result = await session.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.all()


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation = Conversation(user_id=user.id, title=body.title or DEFAULT_TITLE)
    session.add(conversation)
    await session.commit()
    return conversation


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation = await _get_owned(session, conversation_id, user)
    await session.refresh(conversation, ["messages"])
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation = await _get_owned(session, conversation_id, user)
    conversation.title = body.title.strip()
    await session.commit()
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation = await _get_owned(session, conversation_id, user)
    await session.delete(conversation)
    await session.commit()
    graph = request.app.state.graph
    if graph is not None and graph.checkpointer is not None:
        await graph.checkpointer.adelete_thread(conversation_id)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Runs one agent turn and streams it as server-sent events:
    `user_message`, then any of `status` / `diagnosis` / `token`, then `message` and `done`
    (or `error`)."""
    graph = request.app.state.graph
    if graph is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The assistant is not configured (missing GROQ_API_KEY)")
    text = body.text.strip()
    if not text and not body.image_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Send some text or a photo")

    conversation = await _get_owned(session, conversation_id, user)
    if body.image_id:
        upload = await session.get(Upload, body.image_id)
        if upload is None or upload.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")

    user_message = Message(conversation_id=conversation.id, role="user", content=text, image_id=body.image_id)
    session.add(user_message)
    if conversation.title == DEFAULT_TITLE:
        conversation.title = text[:60] if text else PHOTO_TITLE
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    user_message_out = MessageOut.model_validate(user_message).model_dump(mode="json")

    llm_text = text
    if body.image_id:
        llm_text = f"[Attached a photo of a plant]\n{text}" if text else "[Attached a photo of a plant] Please diagnose this plant."
    graph_input: dict = {
        "messages": [HumanMessage(llm_text)],
        "user_id": user.id,
        "image_id": body.image_id,
        "new_diagnosis": False,
    }
    if body.lat is not None and body.lon is not None:
        graph_input["location"] = {"lat": body.lat, "lon": body.lon}
    config = {"configurable": {"thread_id": conversation.id}, "recursion_limit": 25}

    async def stream() -> AsyncIterator[str]:
        yield _sse("user_message", user_message_out)
        diagnosis = None
        try:
            async for mode, payload in graph.astream(
                graph_input, config, stream_mode=["messages", "custom"]
            ):
                if mode == "custom":
                    if payload.get("type") == "diagnosis":
                        diagnosis = payload["diagnosis"]
                        yield _sse("diagnosis", diagnosis)
                    elif payload.get("type") == "status":
                        yield _sse("status", {"text": payload["text"]})
                elif mode == "messages":
                    chunk, metadata = payload
                    if (
                        metadata.get("langgraph_node") == ORCHESTRATOR_NODE
                        and isinstance(chunk, AIMessageChunk)
                        and isinstance(chunk.content, str)
                        and chunk.content
                    ):
                        yield _sse("token", {"text": chunk.content})

            final_state = await graph.aget_state(config)
            last = final_state.values["messages"][-1]
            reply = last.content if isinstance(last, AIMessage) and isinstance(last.content, str) else ""
        except Exception:
            logger.exception("Agent turn failed for conversation %s", conversation_id)
            yield _sse("error", {"detail": "Something went wrong while generating a reply. Please try again."})
            return

        async with session_factory()() as write_session:
            stored = await write_session.get(Conversation, conversation_id)
            if stored is None:  # deleted while the reply was being generated
                return
            assistant_message = Message(
                conversation_id=conversation_id, role="assistant", content=reply, diagnosis=diagnosis
            )
            write_session.add(assistant_message)
            if diagnosis and diagnosis["status"] == "confident" and stored.title == PHOTO_TITLE:
                stored.title = diagnosis["name"]
            stored.updated_at = datetime.now(timezone.utc)
            await write_session.commit()
            yield _sse("message", MessageOut.model_validate(assistant_message).model_dump(mode="json"))
            yield _sse("done", {"conversation_title": stored.title})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
