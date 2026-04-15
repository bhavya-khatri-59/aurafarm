import os
import httpx
from typing import Dict, Optional

# --- Configuration ---
# If you are using a .env file, ensure 'from dotenv import load_dotenv; load_dotenv()' 
# is called in your main.py before importing this service.
API_KEY = os.environ.get("WEATHER_API_KEY")
BASE_URL = "http://api.weatherapi.com/v1/current.json"

async def get_weather_data(lat: float, lon: float) -> Optional[Dict]:
    """
    Fetches current weather data for a given latitude and longitude.
    """
    print(f"\n[WEATHER_SERVICE] Incoming Request -> Lat: {lat}, Lon: {lon}")

    # 1. Check API Key presence
    if not API_KEY:
        print("!!! CRITICAL ERROR: WEATHER_API_KEY environment variable is MISSING.")
        print("!!! Ensure you ran 'export WEATHER_API_KEY=...' or configured your .env file.")
        return {"error": "Server configuration error: Missing API Key"}

    # 2. Prevent 400 errors from common empty coordinate values
    if lat == 0.0 and lon == 0.0:
        print("[WEATHER_SERVICE] Warning: Coordinates are 0.0, 0.0. This usually indicates a GPS wait. Skipping API call.")
        return {"error": "Invalid coordinates (0,0)"}

    # 3. Construct Query
    query_param = f"{lat},{lon}"
    params = {"key": API_KEY, "q": query_param}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"[WEATHER_SERVICE] Calling: {BASE_URL} with q={query_param}")
            
            response = await client.get(BASE_URL, params=params)
            
            # If it's not a 200 OK, we need to know WHY.
            if response.status_code != 200:
                print(f"!!! WEATHER API REJECTED: HTTP {response.status_code}")
                print(f"!!! Response Content: {response.text}")
                return {"error": f"API returned {response.status_code}: {response.text}"}
                
            data = response.json()
            current = data.get("current")
            
            if not current:
                print(f"!!! WEATHER API ERROR: JSON structure unexpected. Received: {data}")
                return {"error": "Malformed API response"}

            print(f"[WEATHER_SERVICE] Success! Condition: {current.get('condition', {}).get('text')}")
            
            return {
                "temp_c": current.get("temp_c"),
                "humidity": current.get("humidity"),
                "description": current.get("condition", {}).get("text"),
                "wind_kph": current.get("wind_kph"),
            }

    except httpx.ConnectTimeout:
        print("!!! WEATHER_SERVICE ERROR: Connection timed out.")
        return {"error": "Connection timeout"}
    except httpx.HTTPStatusError as e:
        print(f"!!! WEATHER_SERVICE ERROR: HTTP error occurred: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"!!! WEATHER_SERVICE ERROR: Unexpected exception: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc() # This will show exactly where it failed in the terminal
        return {"error": str(e)}