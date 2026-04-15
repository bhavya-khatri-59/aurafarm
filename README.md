This documentation covers your entire AI-driven agricultural system, from the deep learning model architecture used for training to the full-stack deployment of the AuraFarm application.

---

## 1. Project Overview: AuraFarm AI
[cite_start]**AuraFarm** is an end-to-end plant pathology system that allows farmers to upload leaf images and receive immediate diagnoses, organic/chemical treatment plans, local weather context, and community outbreak alerts[cite: 32, 590, 596]. 

[cite_start]The core of the system is a **ResNet9** deep learning model trained on a dataset of over **70,000 images** to recognize **38 different classes** of plant health[cite: 33, 94].

---

## 2. Model Architecture: ResNet9
[cite_start]The model follows a "Residual Network" design, which uses "shortcuts" to ensure that as the network gets deeper, it doesn't lose the original features of the leaf image[cite: 278, 293].



### Stage-by-Stage Breakdown
* [cite_start]**Input Block (`conv1`)**: Performs initial feature extraction using 64 filters to identify basic edges and colors[cite: 280, 387].
* **Stage 1 (`conv2` + `res1`)**: Learns basic textures like leaf smoothness or roughness. [cite_start]It uses 128 filters and includes the first **Residual Block**, which adds the input back to the output to prevent data degradation[cite: 280, 293, 387].
* [cite_start]**Stage 2 (`conv3` + `conv4`)**: Scales up to 256 and then 512 filters to identify complex disease patterns, such as specific spot shapes or fungal growth[cite: 281, 282, 387].
* [cite_start]**Stage 3 (`res2`)**: Performs final high-level feature extraction with another residual connection at the 512-filter level[cite: 281, 297, 387].
* **Output Layer**:
    * [cite_start]**MaxPool**: Reduces spatial dimensions to focus on the strongest disease signals[cite: 283, 375, 387].
    * [cite_start]**Flatten**: Converts the 2D feature maps into a 1D vector of 512 numbers[cite: 285, 376, 387].
    * [cite_start]**Linear**: A fully connected layer that maps those 512 features to one of the 38 disease classes[cite: 286, 377, 387].

---

## 3. Training & Performance
[cite_start]The model was trained using the **One-Cycle Learning Rate Policy** and **Stochastic Gradient Descent (SGD)**[cite: 410, 449].



### Training Highlights
* [cite_start]**Dataset**: 70,295 training images and a separate validation set[cite: 94, 97].
* [cite_start]**Epochs**: 2 (The model achieved high accuracy extremely quickly)[cite: 444, 455, 456].
* [cite_start]**Optimization**: Used Weight Decay (L2 regularization) to prevent the model from simply memorizing images[cite: 447, 450].

### [cite_start]Final Metrics [cite: 820]
| Metric | Result |
| :--- | :--- |
| **Accuracy** | 98.02% |
| **Precision** | 98.03% |
| **Recall** | 98.02% |
| **F1-Score** | 98.01% |

---

## 4. Full-Stack Implementation
The project is deployed as a modern web application with a decoupled architecture.

### Backend (Python/FastAPI)
* [cite_start]**Model Inference**: Loads the trained PyTorch `state_dict` and processes uploaded images through the ResNet9 architecture[cite: 633, 642].
* **Service Integration**:
    * **Weather Service**: Fetches real-time temperature and humidity via WeatherAPI.com based on the user's GPS coordinates.
    * [cite_start]**Farmer Network**: Queries a database (remedies.json) for treatment protocols and mocks nearby outbreak data[cite: 724, 775].
* **LLM Handler**: Uses **Google Gemini 1.5 Flash** to combine the diagnosis, weather, and community data into a conversational response for the farmer.

### Frontend (React/TypeScript)
* **Chat Interface**: A responsive UI utilizing Tailwind CSS and Lucide icons for image uploads and real-time chat.
* **Geolocation**: Automatically requests the user's latitude and longitude to provide localized agricultural advice.
* **State Management**: Tracks conversation history in a format compatible with Gemini's strict "Role/Parts" schema.

---

## 5. Disease Coverage
[cite_start]The system provides recommendations for **38 categories**[cite: 33, 775], including:
* [cite_start]**Apple**: Scab, Black Rot, Cedar Rust[cite: 726].
* [cite_start]**Corn**: Common Rust, Northern Leaf Blight, Gray Leaf Spot[cite: 734, 737, 738].
* [cite_start]**Potato**: Early Blight, Late Blight[cite: 759, 761].
* [cite_start]**Tomato**: 10 distinct classes including Bacterial Spot, Leaf Mold, and Yellow Leaf Curl Virus[cite: 765, 766, 768, 771, 772].