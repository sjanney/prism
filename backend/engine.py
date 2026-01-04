import torch
from PIL import Image
from transformers import SiglipProcessor, SiglipModel
from ultralytics import YOLO
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        # Lazy Loading: Initialize to None
        self.processor = None
        self.model = None
        self.yolo = None

        # COCO classes of interest
        self.target_classes = [0, 2, 5, 7, 9] 

    def _load_siglip(self):
        """Loads SigLIP model only if not already loaded."""
        if self.model is None:
            logger.info("Loading SigLIP model (SO400M)...")
            self.processor = SiglipProcessor.from_pretrained("google/siglip-so400m-patch14-384")
            self.model = SiglipModel.from_pretrained("google/siglip-so400m-patch14-384").to(self.device)
            self.model.eval()
    
    def _load_yolo(self):
        """Loads YOLO model only if not already loaded."""
        if self.yolo is None:
            logger.info("Loading YOLOv8 model (Medium)...")
            self.yolo = YOLO("yolov8m.pt")

    def compute_embedding(self, image: Image.Image) -> np.ndarray:
        self._load_siglip() # Ensure loaded
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        with torch.no_grad():
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return image_features.cpu().numpy()[0]

    def compute_text_embedding(self, text: str) -> np.ndarray:
        self._load_siglip() # Ensure loaded
        with torch.no_grad():
            inputs = self.processor(text=[text], return_tensors="pt", padding="max_length", truncation=True).to(self.device)
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            return text_features.cpu().numpy()[0]

    def process_image(self, file_path: str):
        self._load_yolo() # Ensure loaded
        self._load_siglip() # Ensure loaded
        
        try:
            image = Image.open(file_path)
            width, height = image.size
            embeddings = []

            # 1. Global embedding
            global_emb = self.compute_embedding(image)
            embeddings.append({
                "type": "full_image",
                "class": None,
                "bbox": None,
                "embedding": global_emb
            })

            # 2. Run YOLO
            results = self.yolo(image, verbose=False) 

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id in self.target_classes:
                        # Extract crop
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(width, x2), min(height, y2)
                        
                        if x2 - x1 < 10 or y2 - y1 < 10: 
                            continue

                        crop = image.crop((x1, y1, x2, y2))
                        crop_emb = self.compute_embedding(crop)
                        
                        class_name = self.yolo.names[cls_id]
                        embeddings.append({
                            "type": "object_crop",
                            "class": class_name,
                            "bbox": [x1, y1, x2, y2],
                            "embedding": crop_emb
                        })
            
            return width, height, embeddings

        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            return 0, 0, []

    def search(self, text_query: str, db_connection):
        # 1. Text embedding
        query_emb = self.compute_text_embedding(text_query)

        # 2. Get all embeddings
        stored_items = db_connection.get_all_embeddings()

        if not stored_items:
            return []

        # Check dimension mismatch
        if stored_items and stored_items[0]['embedding'].shape != query_emb.shape:
             raise ValueError(
                 f"Model dimension mismatch! Current model uses {query_emb.shape[0]}d vectors, "
                 f"but index has {stored_items[0]['embedding'].shape[0]}d vectors. "
                 "Please delete 'prism.db' and re-index your data."
             )

        # 3. Vectorized Cosine Similarity (SPEED INCREASE)
        all_embs = np.stack([item['embedding'] for item in stored_items])
        dot_products = np.dot(all_embs, query_emb)

        scores = []
        for i, item in enumerate(stored_items):
            scores.append({
                "path": item['file_path'],
                "confidence": float(dot_products[i]),
                "reasoning": "Visual Neural Match",
                "width": item['width'],
                "height": item['height'],
                "indexed_at": item['indexed_at']
            })

        # 4. Sort and return top 20
        scores.sort(key=lambda x: x["confidence"], reverse=True)
        return scores[:20]
