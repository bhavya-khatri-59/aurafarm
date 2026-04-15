import os
import torch
import torchvision.transforms as transforms
import torch.nn.functional as F
import torch.nn as nn
from PIL import Image
from typing import Tuple
from io import BytesIO
import asyncio

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(_BASE_DIR, 'Model', 'plant-disease-model.pth')

CLASS_NAMES_CORRECT = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy', 
    'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy', 
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_', 
    'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy', 'Grape___Black_rot', 
    'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy', 
    'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot', 'Peach___healthy', 
    'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy', 'Potato___Early_blight', 
    'Potato___Late_blight', 'Potato___healthy', 'Raspberry___healthy', 'Soybean___healthy', 
    'Squash___Powdery_mildew', 'Strawberry___Leaf_scorch', 'Strawberry___healthy', 
    'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight', 'Tomato___Leaf_Mold', 
    'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot', 
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus', 'Tomato___healthy'
]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def ConvBlock(in_channels, out_channels, pool=False):
    layers = [nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1), 
              nn.BatchNorm2d(out_channels), 
              nn.ReLU(inplace=True)]
    if pool: layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)

# ==============================================================
# FULLY WRITTEN RESNET9 CLASS (With Adaptive Pooling Upgrade)
# ==============================================================
class ResNet9(nn.Module):
    def __init__(self, in_channels, num_classes):
        super().__init__()
        
        self.conv1 = ConvBlock(in_channels, 64)
        self.conv2 = ConvBlock(64, 128, pool=True)
        self.res1 = nn.Sequential(ConvBlock(128, 128), ConvBlock(128, 128))
        
        self.conv3 = ConvBlock(128, 256, pool=True)
        self.conv4 = ConvBlock(256, 512, pool=True)
        self.res2 = nn.Sequential(ConvBlock(512, 512), ConvBlock(512, 512))
        
        self.classifier = nn.Sequential(
            nn.AdaptiveMaxPool2d(1), # Index 0: The magic funnel
            nn.Flatten(),            # Index 1: Flatten the output
            nn.Linear(512, num_classes) # Index 2: Matches the saved state_dict!
        )
        
    def forward(self, xb):
        out = self.conv1(xb)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        out = self.classifier(out)
        return out
# ==============================================================

model = None
model_load_lock = asyncio.Lock()

def _load_model_sync():
    try:
        if not os.path.exists(MODEL_PATH):
            print(f"FATAL: Model file not found at: {MODEL_PATH}")
            return None
            
        print(f"Loading PyTorch model from: {MODEL_PATH} onto {device}")
        
        # 1. Load the file and bypass the PyTorch 2.6 weights_only security block
        checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
        
        # 2. Bulletproof loading: Check if it's a full model or just weights
        if isinstance(checkpoint, nn.Module):
            print("Detected a complete model file.")
            loaded_model = checkpoint
        else:
            print("Detected a state_dict weights file.")
            loaded_model = ResNet9(3, len(CLASS_NAMES_CORRECT)) 
            loaded_model.load_state_dict(checkpoint)
        
        # Set to evaluation mode
        loaded_model.to(device)
        loaded_model.eval()
        
        print("PyTorch model loaded successfully.")
        return loaded_model
    except Exception as e:
        print(f"FATAL: An error occurred during model loading: {e}")
        return None

async def get_disease_prediction(image_bytes: bytes) -> Tuple[str, float]:
    global model
    
    if model is None:
        async with model_load_lock:
            if model is None:
                print("Model is not loaded yet. Attempting to load...")
                loop = asyncio.get_event_loop()
                model = await loop.run_in_executor(None, _load_model_sync)

    if model is None:
        raise RuntimeError("Model could not be loaded. Please check the server logs.")

    try:
        # Standard Resize for Plant Disease (The funnel handles the rest!)
        transform = transforms.Compose([
            transforms.Resize((256, 256)), 
            transforms.ToTensor()
        ])
        
        img = Image.open(BytesIO(image_bytes)).convert('RGB')
        tensor = transform(img).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(tensor)
            probabilities = F.softmax(outputs, dim=1)
            confidence, preds = torch.max(probabilities, dim=1)
            
            top_index = preds.item()
            conf_val = confidence.item()

        if top_index >= len(CLASS_NAMES_CORRECT):
             print(f"Error: Model predicted index {top_index}, out of bounds.")
             return "Model/Class Mismatch", 0.0

        disease_name = CLASS_NAMES_CORRECT[top_index]
        return disease_name, conf_val

    except Exception as e:
        print(f"Error during prediction: {e}")
        raise e