import torch
from PIL import Image
from transformers import SiglipProcessor, SiglipModel
from ultralytics import YOLO
import numpy as np
import logging

from errors import DimensionMismatchError, ModelLoadingError

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

    def compute_batch_embeddings(self, images: list[Image.Image]) -> list[np.ndarray]:
        """Compute embeddings for a batch of images in one pass."""
        self._load_siglip()
        
        # Ensure RGB
        clean_images = []
        for img in images:
            if img.mode != "RGB":
                clean_images.append(img.convert("RGB"))
            else:
                clean_images.append(img)

        if not clean_images:
            return []

        with torch.no_grad():
            inputs = self.processor(images=clean_images, return_tensors="pt", padding=True).to(self.device)
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return list(image_features.cpu().numpy())

    def process_batch(self, file_paths: list[str]):
        """Process a batch of images efficiently."""
        self._load_yolo()
        self._load_siglip()
        
        results = []
        
        # 1. Parallel Load all images (Speedup: 2x)
        # Use simple ThreadPool for I/O bound image loading
        from concurrent.futures import ThreadPoolExecutor
        
        images = [None] * len(file_paths)
        valid_paths = [None] * len(file_paths)
        
        def load_img(idx, path):
            try:
                img = Image.open(path)
                img.load() # Force load pixel data
                return idx, img, path
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                return idx, None, None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(load_img, i, p) for i, p in enumerate(file_paths)]
            for f in futures:
                idx, img, path = f.result()
                if img:
                    images[idx] = img
                    valid_paths[idx] = path
        
        # Filter failures
        images = [img for img in images if img is not None]
        valid_paths = [p for p in valid_paths if p is not None]

        if not images:
            return []

        # 2. Batch Global Embeddings (SigLIP)
        global_embs = self.compute_batch_embeddings(images)

        # 3. Batch Object Detection (YOLO)
        # YOLOv8 handles batch inference natively
        yolo_results = self.yolo(images, verbose=False, stream=False)

        # 4. Process Detections & Collect Crops
        all_crops = []
        crop_metadata = [] # (image_index, class_name, bbox)

        for i, result in enumerate(yolo_results):
            width, height = images[i].size
            
            # Start result entry
            image_result = {
                "path": valid_paths[i],
                "width": width,
                "height": height,
                "embeddings": [{
                    "type": "full_image",
                    "class": None,
                    "bbox": None,
                    "embedding": global_embs[i]
                }]
            }
            results.append(image_result)

            # Collect crops
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                if cls_id in self.target_classes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)
                    
                    if x2 - x1 < 10 or y2 - y1 < 10: 
                        continue

                    crop = images[i].crop((x1, y1, x2, y2))
                    all_crops.append(crop)
                    crop_metadata.append({
                        "img_idx": i,
                        "class": self.yolo.names[cls_id],
                        "bbox": [x1, y1, x2, y2]
                    })

        # 5. Batch Crop Embeddings (SigLIP)
        if all_crops:
            # Process crops in sub-batches if too many
            crop_embs = []
            chunk_size = 32 # Safety limit for crop batches
            for k in range(0, len(all_crops), chunk_size):
                chunk = all_crops[k:k+chunk_size]
                crop_embs.extend(self.compute_batch_embeddings(chunk))
            
            # Assign back to results
            for j, meta in enumerate(crop_metadata):
                img_idx = meta["img_idx"]
                results[img_idx]["embeddings"].append({
                    "type": "object_crop",
                    "class": meta["class"],
                    "bbox": meta["bbox"],
                    "embedding": crop_embs[j]
                })

        return results

    def search(self, text_query: str, db_connection):
        # 1. Text embedding
        query_emb = self.compute_text_embedding(text_query)
        expected_dim = query_emb.shape[0]

        # 2. Get all embeddings (with caching)
        if not hasattr(self, '_embedding_cache') or self._embedding_cache is None:
            logger.info("Loading embeddings into cache...")
            all_items = db_connection.get_all_embeddings()
            
            # Filter only embeddings with correct dimension
            self._embedding_cache = [
                item for item in all_items 
                if item['embedding'].shape[0] == expected_dim
            ]
            
            if len(self._embedding_cache) != len(all_items):
                logger.warning(f"Filtered out {len(all_items) - len(self._embedding_cache)} embeddings with wrong dimensions.")
            
            if self._embedding_cache:
                self._emb_matrix = np.stack([item['embedding'] for item in self._embedding_cache])
            else:
                self._emb_matrix = None
        
        stored_items = self._embedding_cache

        if not stored_items:
            return []

        # Check dimension mismatch
        if stored_items and stored_items[0]['embedding'].shape != query_emb.shape:
             raise DimensionMismatchError(
                 expected=query_emb.shape[0],
                 actual=stored_items[0]['embedding'].shape[0]
             )

        # 3. Vectorized Cosine Similarity (SPEED INCREASE)
        dot_products = np.dot(self._emb_matrix, query_emb)

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

    def invalidate_cache(self):
        """Call after indexing to ensure next search reloads."""
        self._embedding_cache = None
        self._emb_matrix = None
