from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import List, Optional

# Import your handler functions
from disease_detector import get_disease_prediction 
from llm_handler import get_conversational_response
from weather_service import get_weather_data as get_weather
from farmer_network_service import get_nearby_farmer_data

# --- FastAPI App Initialization ---
app = FastAPI(title="AuraFarm AI Backend")

# --- FIX: CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- Helper Function to Load Remedies ---
def load_remedies():
    try:
        with open("remedies.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("ERROR: remedies.json not found. Please create it.")
        return {}

remedies_db = load_remedies()

# --- API Endpoint ---
@app.post("/diagnose")
async def diagnose_plant(
    prompt: str = Form(...),
    image: Optional[UploadFile] = File(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    history: str = Form("[]")
):
    try:
        conversation_history = json.loads(history)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid history format. Must be a valid JSON string.")

    if image:
        # --- Diagnosis Mode ---
        if lat is None or lon is None:
            raise HTTPException(
                status_code=400, 
                detail="Latitude and longitude are required for image-based plant diagnosis."
            )

        try:
            image_bytes = await image.read()
            
            # 1. Neural Network Prediction
            disease_name, confidence = await get_disease_prediction(image_bytes)
            
            # 2. Gather Contextual Data (Weather & Remedies)
            # IMPROVED: Check for 0,0 coordinates which often cause 400 errors from APIs
            weather_data = None
            if lat == 0.0 and lon == 0.0:
                weather_data = {"error": "GPS lock not yet established. Weather context unavailable."}
            else:
                try:
                    weather_data = await get_weather(lat, lon)
                    if not weather_data:
                        weather_data = {"error": "Location not supported by weather service"}
                except Exception as e:
                    print(f"Weather API Error: {e}")
                    weather_data = {"error": "Weather data currently unavailable"}

            remedy_data = remedies_db.get(disease_name, {})
            farmer_data = get_nearby_farmer_data(lat, lon, disease_name)
            
            diagnosis_result = {
                "name": disease_name,
                "confidence": f"{confidence * 100:.2f}%",
                "remedies": remedy_data
            }

            # 3. LLM Final Conversation
            final_response = await get_conversational_response(
                user_prompt=prompt,
                history=conversation_history,
                diagnosis=diagnosis_result,
                weather=weather_data,
                nearby_farmers=farmer_data
            )
        except Exception as e:
            print(f"Internal Server Error during diagnosis: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # --- Conversational Mode ---
        final_response = await get_conversational_response(
            user_prompt=prompt,
            history=conversation_history
        )

    return JSONResponse(content={"response": final_response})