import hashlib
import json
import math
import re
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class ScriptedChatModel(BaseChatModel):
    """Returns pre-scripted AIMessages in order and records what it was sent."""

    responses: list[AIMessage]
    calls: list[list[BaseMessage]] = []
    index: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.calls.append(list(messages))
        message = self.responses[self.index]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def hashing_embedder(texts: list[str], dims: int = 256) -> list[list[float]]:
    """Deterministic bag-of-words embedding, so retrieval tests need no model download."""
    vectors = []
    for text in texts:
        vec = [0.0] * dims
        for word in re.findall(r"[a-z]+", text.lower()):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % dims] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


class StreamingScriptedChatModel(ScriptedChatModel):
    """Like ScriptedChatModel, but streams each reply word by word like a real provider."""

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        message = self._generate(messages).generations[0].message
        words = message.content.split(" ") if message.content else []
        for i, word in enumerate(words):
            text = word if i == len(words) - 1 else word + " "
            if run_manager:
                run_manager.on_llm_new_token(text)
            yield ChatGenerationChunk(message=AIMessageChunk(content=text))
        if message.tool_calls:
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[
                {"name": c["name"], "args": json.dumps(c["args"]), "id": c["id"], "index": i}
                for i, c in enumerate(message.tool_calls)
            ]))


class FailingOnceChatModel(ScriptedChatModel):
    """Raises a Groq tool-call validation error on the first call, then follows the script."""

    failed: bool = False

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if not self.failed:
            import groq
            import httpx

            self.failed = True
            raise groq.APIError(
                "Tool call validation failed: parameters for tool search_web did not match schema",
                httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
                body=None,
            )
        return super()._generate(messages, stop, run_manager, **kwargs)


class AlwaysFailingChatModel(ScriptedChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise RuntimeError("model unavailable")


def jpeg_bytes(color=(60, 140, 50), size=(320, 240), pattern: int = 0, quality: int = 90) -> bytes:
    """A real JPEG; `pattern` varies the content so different values give different photos."""
    from io import BytesIO

    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    for i in range(6):
        x = (i * 53 + pattern * 97) % size[0]
        y = (i * 37 + pattern * 61) % size[1]
        draw.ellipse([x, y, x + 40 + pattern * 7, y + 30], fill=(120 + i * 20, 80, 30 + pattern * 40 % 200))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()
