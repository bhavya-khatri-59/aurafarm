from dotenv import load_dotenv
import os
import google.generativeai as genai
from typing import Dict, List, Optional
import math
import json

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration ---
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set or found in .env file.")
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    model = None

MAX_CONTEXT_TOKENS = 12000

def _estimate_tokens(text: str) -> int:
    """A simple heuristic for token estimation."""
    return math.ceil(len(text.split()) * 1.5)

def _truncate_history_by_tokens(history: List[Dict]) -> List[Dict]:
    """Ensures the conversation history does not exceed the token limit."""
    if not history:
        return []
    
    current_token_count = 0
    truncated_conversation = []

    for message in reversed(history):
        message_text = ""
        parts = message.get('parts', [])
        if parts and isinstance(parts[0], dict):
            message_text = parts[0].get('text', "")
        elif parts and isinstance(parts[0], str):
            message_text = parts[0]
        
        message_tokens = _estimate_tokens(message_text)
        
        if current_token_count + message_tokens > MAX_CONTEXT_TOKENS:
            break
        
        truncated_conversation.insert(0, message)
        current_token_count += message_tokens
    
    return truncated_conversation

async def get_conversational_response(
    user_prompt: str,
    history: List[Dict],
    diagnosis: Optional[Dict] = None,
    weather: Optional[Dict] = None,
    nearby_farmers: Optional[List[Dict]] = None
) -> str:
    """
    Constructs a prompt and gets a response from Gemini.
    """
    if not model:
        return "Error: The AI model is not configured. Please check the API key."

    # --- System Instructions ---
    system_instruction = """
    You are 'AuraFarm', a friendly and expert agricultural assistant.
    - Provide helpful, clear advice for farmers.
    - If diagnosis/weather/nearby data is provided, use it to give a high-precision response.
    - If nearby farmers report the same disease, warn about potential local outbreaks.
    - Respond strictly in english.
    """

    # --- Context Injection Logic ---
    # We inject context whenever a diagnosis is present, OR if it's the very first message.
    if diagnosis:
        farmer_reports_str = json.dumps(nearby_farmers, indent=2) if nearby_farmers else "No data available."
        
        # We wrap the user's specific prompt with all the data we've gathered
        enriched_prompt = f"""
        {system_instruction}

        ### CONTEXTUAL DATA ###
        1. AI Plant Diagnosis: {json.dumps(diagnosis, indent=2)}
        2. Local Weather: {json.dumps(weather, indent=2)}
        3. Community Reports: {farmer_reports_str}

        ### FARMER'S MESSAGE ###
        "{user_prompt}"

        Please analyze the diagnosis and weather together. For example, if it's humid and the plant has a fungal infection, explain why that weather makes it worse.
        """
        current_message = {'role': 'user', 'parts': [{'text': enriched_prompt}]}
    else:
        # Standard conversation mode
        if not history:
            current_message = {'role': 'user', 'parts': [{'text': system_instruction + "\n\n" + user_prompt}]}
        else:
            current_message = {'role': 'user', 'parts': [{'text': user_prompt}]}

    # Combine history with the current turn
    api_history = history + [current_message]
    
    try:
        safe_history = _truncate_history_by_tokens(api_history)
        
        # Start chat with everything EXCEPT the last message
        chat_session_history = safe_history[:-1]
        # Send the last message as the new prompt
        last_message_text = safe_history[-1]['parts'][0]['text']

        chat = model.start_chat(history=chat_session_history)
        response = await chat.send_message_async(last_message_text)
        
        return response.text
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return f"Sorry, I encountered an error. (Error: {e})"