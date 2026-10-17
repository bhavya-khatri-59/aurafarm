# AuraFarm: AI-Powered Plant Disease Diagnosis & Advisory System

**AuraFarm** is an integrated AI pipeline designed to provide smallholder farmers with instant, accurate, and context-aware diagnosis of plant diseases. By combining computer vision, real-time weather data, and Large Language Models (LLMs), AuraFarm transforms a simple image classification into a comprehensive, conversational agricultural advisory service.

## 👥 Contributors
* **Bhavya Prakash Khatri**
* **Piyush Priyadarsi Panda**

## 🚀 Key Features
* **Accurate Disease Classification:** Identifies 38 different plant disease classes across 14 crop species using a custom ResNet9 model.
* **Contextual Enrichment:** Integrates real-time weather data (via WeatherAPI.com) and simulated community reports to assess local risk levels.
* **Conversational AI Advisory:** Powered by **Gemini 2.5 Pro**, offering multi-turn, multilingual support for tailored treatment plans.
* **Resolution-Agnostic Inference:** Utilizes `AdaptiveMaxPool2d` to handle images of varying sizes from mobile cameras without quality loss.
* **Structured Remedies:** Provides both organic and chemical treatment options for identified diseases.

## 🛠 Technical Architecture

### 1. Vision Model: ResNet9
The core of the system is a 9-layer Residual Network (ResNet9) implemented in PyTorch, designed for high accuracy with low inference latency.

| Layer Block | Description |
| :--- | :--- |
| **conv1** | Conv2d(3→64) + BatchNorm + ReLU |
| **conv2** | Conv2d(64→128) + BatchNorm + ReLU + MaxPool2d(2) |
| **res1** | Residual block: 2× Conv(128→128) |
| **conv3** | Conv2d(128→256) + BatchNorm + ReLU + MaxPool2d(2) |
| **conv4** | Conv2d(256→512) + BatchNorm + ReLU + MaxPool2d(2) |
| **res2** | Residual block: 2× Conv(512→512) |
| **classifier** | AdaptiveMaxPool2d(1) → Flatten → Linear(512→38) |

### 2. Backend & LLM Pipeline
* **Framework:** FastAPI (Asynchronous REST API)
* **LLM:** Gemini 2.5 Pro for contextual response generation.
* **Prompt Engineering:** Dynamically injects AI diagnosis, local weather data, and community signals into the conversation context.

## 📊 Dataset: PlantVillage
The model is trained on the benchmark **PlantVillage Dataset**.

* **Total Images:** ~87,000 leaf images.
* **Crops Covered (14):** Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Bell Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato.
* **Classes:** 38 (26 disease classes + 12 healthy classes).

## 🔍 Gaps Addressed
AuraFarm was built to solve specific limitations found in existing agricultural apps:

| Gap | Impact | AuraFarm Solution |
| :--- | :--- | :--- |
| **Context Blindness** | Generic advice ignoring weather. | Integrates temperature & humidity for fungal risk assessment. |
| **No Community Signal** | Disease spreads unchecked. | Simulated community reporting to warn neighbors. |
| **Language Barrier** | English-only apps. | Multilingual support via Gemini (Hindi, Tamil, Telugu, etc.). |
| **One-shot Diagnosis** | No follow-up questions. | Multi-turn conversational history. |

## 📈 Performance & Results
* **Training Accuracy:** ~99.2%
* **Validation Accuracy:** 95–97%
* **Inference Time:** ~200–400 ms on CPU.
* **Contextuality:** Demonstrated ability to link humidity levels >85% to increased fungal disease severity in advisory text.

## 🛤 Future Scope
* **Crop Expansion:** Adding Indian staples like Rice, Wheat, and Sugarcane.
* **Offline Mode:** Developing TFLite/ONNX versions for areas with zero connectivity.
* **Geospatial Integration:** Using Firestore geohashing for real-time, privacy-preserving farmer networks.

## 📚 References
* Hughes, D.P. & Salathé, M. (2015). PlantVillage Research.
* Mohanty, S.P., et al. (2016). Deep learning for plant disease detection.
* He, K., et al. (2016). Deep Residual Learning (ResNet).
