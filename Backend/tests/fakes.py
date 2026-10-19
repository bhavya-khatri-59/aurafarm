import hashlib
import math
import re
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


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
