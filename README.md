# AuraFarm: AI-Powered Plant Disease Diagnosis & Advisory System

**AuraFarm** gives smallholder farmers instant, context-aware diagnosis of plant diseases. A farmer photographs a leaf in the mobile app. A ResNet9 model identifies the disease, and a team of agents adds local weather, outbreak reports from nearby farmers, places to get help, and treatment advice grounded in extension-service guides.

## 👥 Contributors
* **Bhavya Prakash Khatri**
* **Piyush Priyadarsi Panda**

## 🚀 Key Features
* **Accurate disease classification:** 38 classes across 14 crops with a custom ResNet9 model. Low-confidence results are flagged, and the assistant asks for a clearer photo.
* **Agentic backend:** a LangGraph graph with an orchestrator agent, a deterministic diagnosis node and a remedy-recommendation agent.
* **Grounded remedies (RAG):** the remedy agent searches a ChromaDB knowledge base of extension guides. Every chunk is tagged with crop and disease, so retrieval is filtered to the diagnosed problem. It falls back to web search when the knowledge base is thin.
* **Real local context:** current weather and a 3-day forecast (WeatherAPI.com), outbreak alerts built from other users' diagnoses within 10 km, and nearby agri-input shops and agricultural offices (OpenStreetMap).
* **Stateful, multi-conversation chat:** accounts with email and JWT, server-side conversation history, and switching between conversations in the app.
* **Streaming:** replies stream token by token, with live status ("Analyzing the leaf image…", "Researching treatments…").

## 🛠 Architecture

```
mobile/ (Expo React Native)  ──HTTP + SSE──>  Backend/ (FastAPI)
                                                │
                                   ┌────────────┴─────────────┐
                                   │       LangGraph graph     │
   START ─┬─(photo)─> diagnose ─> orchestrator <──> tools ─> END
          └─────────────────────> orchestrator
```

| Component | Role |
| :--- | :--- |
| **diagnose** (deterministic node) | Runs ResNet9 (top 3), then fetches weather, nearby outbreak reports and nearby places in parallel. Records confident diagnoses, at roughly 1 km resolution, for the community signal. |
| **orchestrator** (Groq LLM) | Talks to the farmer, interprets the diagnosis and context, and decides when to call tools. |
| `consult_remedy_specialist` | Runs the **remedy agent**, a tool-calling loop over `search_knowledge_base` (Chroma, filtered by crop/disease) and `search_web` (DuckDuckGo, or Tavily if configured). Returns cited advice. |
| `find_nearby_help` | Finds agri-input shops, Krishi Vigyan Kendras and agriculture offices via the Overpass API. |

**Storage** (all local, under `Backend/data/`):
- `aurafarm.db` (SQLite): users, conversations, displayed messages, uploads, disease reports.
- `checkpoints.db` (SQLite): LangGraph checkpointer, holding each conversation's agent state (`thread_id` = conversation id).
- `chroma/`: the remedy knowledge base.
- `uploads/`: leaf photos.

**Knowledge-base retrieval** filters from narrow to broad: first `crop AND disease`, then `crop` (plus general material for that crop), then the whole collection, stopping once enough chunks are found. Crop/disease slugs come from one table (`Backend/app/services/labels.py`) shared by the classifier, the ingestion script and the retriever.

## ▶️ Getting Started

### Backend

```bash
cd Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # add GROQ_API_KEY, WEATHER_API_KEY and a JWT_SECRET

# Build the remedy knowledge base (downloads ~60 extension guides, then embeds them)
python -m scripts.fetch_kb
python -m scripts.ingest_kb

# Optional: demo outbreak reports around a location (clearly labelled as demo data in the app)
python -m scripts.seed_demo_reports --lat 12.97 --lon 77.59

uvicorn app.main:app --host 0.0.0.0 --port 8000
pytest                        # run the tests
```

The guide text itself is not committed, because it belongs to its publishers. `kb/sources.yaml` lists each source with its crop/disease tags, and `kb/remedies_seed.json` (AuraFarm's own notes) is always ingested. To add material, add an entry to `sources.yaml` and rerun both scripts.

### Mobile app

```bash
cd mobile
npm install
cp .env.example .env          # EXPO_PUBLIC_API_URL: where the phone/emulator can reach the backend
npx expo start
```

The app uses native modules (secure storage, camera, location), so run it in a development build (`npx expo run:android`) or in Expo Go if your Expo Go version matches SDK 58.

### API overview

| Method & path | Purpose |
| :--- | :--- |
| `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Email/password accounts, JWT bearer tokens |
| `GET/POST /conversations`, `GET/PATCH/DELETE /conversations/{id}` | List, create, load, rename, delete conversations |
| `POST /uploads`, `GET /uploads/{id}` | Upload a leaf photo, fetch it back (owner only) |
| `POST /conversations/{id}/messages` | Run an agent turn. Body: `{text, image_id?, lat?, lon?}`. Response: server-sent events `user_message`, `status`, `diagnosis`, `token`, `message`, `done` / `error` |

> The legacy Flutter app (`Frontend/`) and web app (`frontend-web/`) call the old `/diagnose` endpoint, which no longer exists.

## 🧠 Vision Model: ResNet9

| Layer Block | Description |
| :--- | :--- |
| **conv1** | Conv2d(3→64) + BatchNorm + ReLU |
| **conv2** | Conv2d(64→128) + BatchNorm + ReLU + MaxPool2d(2) |
| **res1** | Residual block: 2× Conv(128→128) |
| **conv3** | Conv2d(128→256) + BatchNorm + ReLU + MaxPool2d(2) |
| **conv4** | Conv2d(256→512) + BatchNorm + ReLU + MaxPool2d(2) |
| **res2** | Residual block: 2× Conv(512→512) |
| **classifier** | AdaptiveMaxPool2d(1) → Flatten → Linear(512→38) |

`AdaptiveMaxPool2d` makes inference resolution-agnostic for photos from mobile cameras.

## 📊 Dataset: PlantVillage
* **Total images:** ~87,000 leaf images.
* **Crops covered (14):** Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Bell Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato.
* **Classes:** 38 (26 disease classes + 12 healthy classes).

PlantVillage photos are single leaves on plain backgrounds, so field photos score lower. The model also always picks one of its 38 classes, even for photos of something else. AuraFarm treats predictions below `CONFIDENCE_THRESHOLD` (default 0.6) as uncertain and asks for a clearer photo.

## 📈 Performance & Results
* **Training accuracy:** ~99.2%
* **Validation accuracy:** 95–97%
* **Inference time:** ~200–400 ms on CPU.

## 🛤 Future Scope
* **Crop expansion:** Indian staples like rice, wheat and sugarcane.
* **Out-of-distribution detection:** reject non-plant photos before classification.
* **Offline mode:** TFLite/ONNX versions for areas with no connectivity.
* **Multilingual answers:** Hindi, Tamil, Telugu and more.

## 📚 References
* Hughes, D.P. & Salathé, M. (2015). PlantVillage Research.
* Mohanty, S.P., et al. (2016). Deep learning for plant disease detection.
* He, K., et al. (2016). Deep Residual Learning (ResNet).
