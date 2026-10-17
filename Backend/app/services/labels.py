"""Maps the classifier's PlantVillage labels to the normalized crop/disease tags used across the app.

The same `crop` and `disease` slugs tag knowledge-base chunks, so retrieval can filter on exactly
what the classifier predicted.
"""

from dataclasses import dataclass

HEALTHY = "healthy"
GENERAL = "general"


@dataclass(frozen=True)
class PlantLabel:
    label: str
    crop: str
    disease: str
    crop_name: str
    disease_name: str

    @property
    def is_healthy(self) -> bool:
        return self.disease == HEALTHY

    @property
    def display(self) -> str:
        if self.is_healthy:
            return f"Healthy {self.crop_name.lower()}"
        return f"{self.crop_name} {self.disease_name.lower()}"


_RAW: list[tuple[str, str, str, str, str]] = [
    ("Apple___Apple_scab", "apple", "apple_scab", "Apple", "Apple scab"),
    ("Apple___Black_rot", "apple", "black_rot", "Apple", "Black rot"),
    ("Apple___Cedar_apple_rust", "apple", "cedar_apple_rust", "Apple", "Cedar apple rust"),
    ("Apple___healthy", "apple", HEALTHY, "Apple", "Healthy"),
    ("Blueberry___healthy", "blueberry", HEALTHY, "Blueberry", "Healthy"),
    ("Cherry_(including_sour)___Powdery_mildew", "cherry", "powdery_mildew", "Cherry", "Powdery mildew"),
    ("Cherry_(including_sour)___healthy", "cherry", HEALTHY, "Cherry", "Healthy"),
    ("Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "corn", "gray_leaf_spot", "Corn", "Gray leaf spot"),
    ("Corn_(maize)___Common_rust_", "corn", "common_rust", "Corn", "Common rust"),
    ("Corn_(maize)___Northern_Leaf_Blight", "corn", "northern_leaf_blight", "Corn", "Northern leaf blight"),
    ("Corn_(maize)___healthy", "corn", HEALTHY, "Corn", "Healthy"),
    ("Grape___Black_rot", "grape", "black_rot", "Grape", "Black rot"),
    ("Grape___Esca_(Black_Measles)", "grape", "esca", "Grape", "Esca (black measles)"),
    ("Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "grape", "leaf_blight", "Grape", "Leaf blight (Isariopsis leaf spot)"),
    ("Grape___healthy", "grape", HEALTHY, "Grape", "Healthy"),
    ("Orange___Haunglongbing_(Citrus_greening)", "orange", "citrus_greening", "Orange", "Citrus greening (HLB)"),
    ("Peach___Bacterial_spot", "peach", "bacterial_spot", "Peach", "Bacterial spot"),
    ("Peach___healthy", "peach", HEALTHY, "Peach", "Healthy"),
    ("Pepper,_bell___Bacterial_spot", "pepper", "bacterial_spot", "Bell pepper", "Bacterial spot"),
    ("Pepper,_bell___healthy", "pepper", HEALTHY, "Bell pepper", "Healthy"),
    ("Potato___Early_blight", "potato", "early_blight", "Potato", "Early blight"),
    ("Potato___Late_blight", "potato", "late_blight", "Potato", "Late blight"),
    ("Potato___healthy", "potato", HEALTHY, "Potato", "Healthy"),
    ("Raspberry___healthy", "raspberry", HEALTHY, "Raspberry", "Healthy"),
    ("Soybean___healthy", "soybean", HEALTHY, "Soybean", "Healthy"),
    ("Squash___Powdery_mildew", "squash", "powdery_mildew", "Squash", "Powdery mildew"),
    ("Strawberry___Leaf_scorch", "strawberry", "leaf_scorch", "Strawberry", "Leaf scorch"),
    ("Strawberry___healthy", "strawberry", HEALTHY, "Strawberry", "Healthy"),
    ("Tomato___Bacterial_spot", "tomato", "bacterial_spot", "Tomato", "Bacterial spot"),
    ("Tomato___Early_blight", "tomato", "early_blight", "Tomato", "Early blight"),
    ("Tomato___Late_blight", "tomato", "late_blight", "Tomato", "Late blight"),
    ("Tomato___Leaf_Mold", "tomato", "leaf_mold", "Tomato", "Leaf mold"),
    ("Tomato___Septoria_leaf_spot", "tomato", "septoria_leaf_spot", "Tomato", "Septoria leaf spot"),
    ("Tomato___Spider_mites Two-spotted_spider_mite", "tomato", "spider_mites", "Tomato", "Two-spotted spider mites"),
    ("Tomato___Target_Spot", "tomato", "target_spot", "Tomato", "Target spot"),
    ("Tomato___Tomato_Yellow_Leaf_Curl_Virus", "tomato", "yellow_leaf_curl_virus", "Tomato", "Yellow leaf curl virus"),
    ("Tomato___Tomato_mosaic_virus", "tomato", "mosaic_virus", "Tomato", "Mosaic virus"),
    ("Tomato___healthy", "tomato", HEALTHY, "Tomato", "Healthy"),
]

# Order matters: index i is the classifier's output neuron i.
CLASS_NAMES: list[str] = [row[0] for row in _RAW]
LABELS: dict[str, PlantLabel] = {row[0]: PlantLabel(*row) for row in _RAW}
CROPS: list[str] = sorted({row[1] for row in _RAW})
DISEASES: list[str] = sorted({row[2] for row in _RAW})


def get_label(label: str) -> PlantLabel:
    return LABELS[label]
