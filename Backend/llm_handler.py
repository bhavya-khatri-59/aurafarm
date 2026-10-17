import os
import json
import math
from typing import Dict, List, Optional
from dotenv import load_dotenv
from groq import AsyncGroq

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration ---
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("Warning: GROQ_API_KEY environment variable not set or found in .env file.")
    client = None
else:
    client = AsyncGroq(api_key=api_key)

# Default to LLaMA 3.3 70B (fast inference and strong reasoning on Groq)
MODEL_NAME = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_CONTEXT_TOKENS = 12000

SYSTEM_INSTRUCTION = """You are 'AuraFarm', a friendly and expert agricultural assistant.
- Provide helpful, clear advice for farmers.
- If diagnosis/weather/nearby data is provided, use it to give a high-precision response.
- If nearby farmers report the same disease, warn about potential local outbreaks.
- Respond strictly in English."""


def _estimate_tokens(text: str) -> int:
    """A simple heuristic for token estimation."""
    return math.ceil(len(text.split()) * 1.5)


def _extract_text(message: Dict) -> str:
    """Extracts raw text whether the message format is OpenAI/Groq or legacy Gemini."""
    if "content" in message and isinstance(message["content"], str):
        return message["content"]
    
    parts = message.get("parts", [])
    if parts:
        if isinstance(parts[0], dict):
            return parts[0].get("text", "")
        if isinstance(parts[0], str):
            return parts[0]
    return ""


def _normalize_and_truncate_history(history: List[Dict], current_user_msg: str) -> List[Dict]:
    """
    Normalizes history items to standard Groq messages ({'role': ..., 'content': ...})
    and truncates to avoid exceeding token limits.
    """
    normalized: List[Dict] = []
    
    for msg in history:
        role = msg.get("role", "user")
        # Map Gemini's 'model' role to Groq/OpenAI's 'assistant'
        if role == "model":
            role = "assistant"
            
        text = _extract_text(msg)
        if text:
            normalized.append({"role": role, "content": text})

    # Append current turn
    normalized.append({"role": "user", "content": current_user_msg})

    # Truncate oldest messages if token budget is exceeded
    current_tokens = 0
    truncated_messages: List[Dict] = []

    for msg in reversed(normalized):
        tokens = _estimate_tokens(msg["content"])
        if current_tokens + tokens > MAX_CONTEXT_TOKENS:
            break
        truncated_messages.insert(0, msg)
        current_tokens += tokens

    return truncated_messages


async def get_conversational_response(
    user_prompt: str,
    history: List[Dict],
    diagnosis: Optional[Dict] = None,
    weather: Optional[Dict] = None,
    nearby_farmers: Optional[List[Dict]] = None
) -> str:
    """
    Constructs contextual messages and retrieves a conversational response via Groq.
    """
    if not client:
        return "Error: The Groq client is not configured. Please check your GROQ_API_KEY."

    # Build contextual prompt if diagnostic info is available
    if diagnosis:
        farmer_reports_str = (
            json.dumps(nearby_farmers, indent=2) if nearby_farmers else "No data available."
        )
        current_user_text = f"""### CONTEXTUAL DATA ###
1. AI Plant Diagnosis: {json.dumps(diagnosis, indent=2)}
2. Local Weather: {json.dumps(weather, indent=2)}
3. Community Reports: {farmer_reports_str}

### FARMER'S MESSAGE ###
"{user_prompt}"

Please analyze the diagnosis and weather together. For example, if it's humid and the plant has a fungal infection, explain why that weather makes it worse."""
    else:
        current_user_text = user_prompt

    # Format messages array for Groq
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    messages.extend(_normalize_and_truncate_history(history, current_user_text))

    try:
        chat_completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.4,
            max_completion_tokens=1024,
        )
        return chat_completion.choices[0].message.content or ""

    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return f"Sorry, I encountered an error. (Error: {e})"