"""Cheap, local guardrails that run before and after the LLM.

Blocked requests get a fixed reply and never reach the LLM API, which also saves rate limit.
"""

import re

NOT_A_PLANT_REPLY = (
    "Sorry, I couldn't identify or diagnose this image. Could you send a clearer photo of a single "
    "plant leaf, in daylight, filling most of the frame?"
)
OFF_TOPIC_REPLY = (
    "I'm AuraFarm, and I can only help with farming and plant health: diagnosing leaf photos, "
    "treating and preventing crop diseases, weather risks, and finding agricultural help nearby. "
    "What would you like to know about your crops?"
)

# Deliberately narrow: farmers say "common rust", "Java" (the island), "fungicide class",
# "select seed", "act as a protectant" and "ignore the label instructions".
_CODE_LANGUAGES = r"python|javascript|typescript|kotlin|c\+\+|c#|golang|sql|html|css|bash|regex|php"
_BLOCK_PATTERNS = [
    # Requests to produce code or software.
    re.compile(
        rf"\b(write|generate|create|give|show|make|fix|debug|build)\b.{{0,40}}"
        rf"\b(code|script|program in|website|web app|mobile app|{_CODE_LANGUAGES})\b",
        re.I,
    ),
    re.compile(rf"\b(in|using|with) ({_CODE_LANGUAGES})\b", re.I),
    # Code pasted into the message.
    re.compile(r"```|\bdef \w+\(|#include\s*<|console\.log\(|\bfunction \w+\(", re.I),
    # Attempts to override the assistant's instructions.
    re.compile(
        r"\b(ignore|disregard|forget)\b.{0,15}\b(all|any|your|previous|prior|above|earlier)\b"
        r".{0,15}\b(instructions|rules|prompts?|guidelines)\b",
        re.I,
    ),
    re.compile(r"\b(system prompt|developer mode|jailbreak|you are now|from now on you are|pretend (to be|you are))\b", re.I),
]


def check_input(text: str) -> str | None:
    """Returns a refusal to send instead of calling the LLM, or None if the message may proceed."""
    if any(pattern.search(text) for pattern in _BLOCK_PATTERNS):
        return OFF_TOPIC_REPLY
    return None


def check_output(reply: str) -> str:
    """Replaces replies that drifted out of scope (code) with the standard refusal."""
    if "```" in reply or re.search(r"^\s*(def |class |import |function |const |#include)", reply, re.M):
        return OFF_TOPIC_REPLY
    return reply
