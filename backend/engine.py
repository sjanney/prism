import torch
from PIL import Image
from transformers import SiglipProcessor, SiglipModel
from ultralytics import YOLO
import numpy as np
import logging
import time

from errors import DimensionMismatchError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COCO class names for better reasoning
COCO_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow"
}

class LocalSearchEngine:
    def __init__(self, use_fp16: bool = True):
        self.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Performance settings
        self.use_fp16 = use_fp16 and self.device in ["cuda", "mps"]
        
        # Dynamic batch size based on device (larger = faster, but more VRAM)
        if self.device == "cuda":
            self.optimal_batch_size = 32
        elif self.device == "mps":
            self.optimal_batch_size = 16
        else:
            self.optimal_batch_size = 8

        # Lazy Loading: Initialize to None
        self.processor = None
        self.model = None
        self.yolo = None

        # COCO classes of interest (person, car, bus, truck, traffic light)
        self.target_classes = [0, 2, 5, 7, 9] 
        
        # Cache for search optimization
        self._emb_matrix = None
        self._emb_ids = None
        self._cache_timestamp = None

    def _load_siglip(self):
        """Loads SigLIP model only if not already loaded."""
        if self.model is None:
            logger.info("Loading SigLIP model (SO400M)...")
            self.processor = SiglipProcessor.from_pretrained("google/siglip-so400m-patch14-384")
            self.model = SiglipModel.from_pretrained("google/siglip-so400m-patch14-384").to(self.device)
            
            # Enable FP16 for faster inference
            if self.use_fp16:
                self.model = self.model.half()
                logger.info("Using FP16 for faster inference")
            
            self.model.eval()
    
    def _load_yolo(self):
        """Loads YOLO model only if not already loaded."""
        if self.yolo is None:
            logger.info("Loading YOLOv8 model (Medium)...")
            self.yolo = YOLO("yolov8m.pt")

    def compute_embedding(self, image: Image.Image) -> np.ndarray:
        self._load_siglip()
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        with torch.no_grad():
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return image_features.cpu().numpy()[0]

    def compute_text_embedding(self, text: str) -> np.ndarray:
        self._load_siglip()
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

    def process_batch(self, file_inputs: list, db_connection=None):
        """
        Process a batch of images efficiently with deduplication support.
        
        Args:
            file_inputs: List of either:
                - str: path to image file
                - tuple: (virtual_path, PIL.Image) for video frames
            db_connection: Optional database for deduplication checks
            
        Returns:
            List of result dicts with 'skipped' flag for duplicates
        """
        self._load_yolo()
        self._load_siglip()
        
        results = []
        skipped_count = 0
        
        # 1. Load/resolve all images with deduplication
        from concurrent.futures import ThreadPoolExecutor
        
        images = [None] * len(file_inputs)
        valid_paths = [None] * len(file_inputs)
        file_hashes = [None] * len(file_inputs)
        
        def load_input(idx, input_item):
            try:
                if isinstance(input_item, tuple):
                    # Video frame: (virtual_path, PIL.Image)
                    path, img = input_item
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    return idx, img, path, None  # No hash for video frames
                
                # Check for deduplication if db available
                file_hash = None
                if db_connection and hasattr(db_connection, 'compute_file_hash'):
                    file_hash = db_connection.compute_file_hash(input_item)
                    if file_hash and db_connection.file_exists_by_hash(file_hash):
                        return idx, None, input_item, "SKIP_DUPLICATE"
                
                # Cloud Storage Support
                if input_item.startswith("s3://"):
                    try:
                        import boto3
                        import io
                        from config import config
                        
                        creds = config.aws_creds
                        if creds:
                            s3 = boto3.client(
                                's3',
                                aws_access_key_id=creds.get('access_key'),
                                aws_secret_access_key=creds.get('secret_key'),
                                region_name=creds.get('region')
                            )
                        else:
                            s3 = boto3.client('s3')
                            
                        parts = input_item.replace("s3://", "").split("/", 1)
                        bucket, key = parts[0], parts[1]
                        
                        file_stream = io.BytesIO()
                        s3.download_fileobj(bucket, key, file_stream)
                        file_stream.seek(0)
                        
                        img = Image.open(file_stream)
                        img.load()
                        return idx, img, input_item, file_hash
                    except Exception as e:
                        logger.error(f"S3 Load Error: {e}")
                        return idx, None, input_item, f"ERROR:{e}"

                elif input_item.startswith("azure://"):
                    try:
                        from azure.storage.blob import BlobServiceClient
                        import io
                        from config import config
                        
                        creds = config.azure_creds
                        conn_str = creds.get("connection_string")
                        if not conn_str:
                             raise ValueError("Azure credentials missing in config")
                             
                        client = BlobServiceClient.from_connection_string(conn_str)
                        
                        parts = input_item.replace("azure://", "").split("/", 1)
                        container, blob_name = parts[0], parts[1]
                        
                        blob_client = client.get_blob_client(container=container, blob=blob_name)
                        download_stream = blob_client.download_blob()
                        
                        file_stream = io.BytesIO()
                        download_stream.readinto(file_stream)
                        file_stream.seek(0)
                        
                        img = Image.open(file_stream)
                        img.load()
                        return idx, img, input_item, file_hash
                    except Exception as e:
                        logger.error(f"Azure Load Error: {e}")
                        return idx, None, input_item, f"ERROR:{e}"

                else:
                    # Regular image file path
                    img = Image.open(input_item)
                    img.load()
                    return idx, img, input_item, file_hash
            except Exception as e:
                logger.error(f"Error loading {input_item}: {e}")
                return idx, None, input_item, f"ERROR:{e}"


        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(load_input, i, p) for i, p in enumerate(file_inputs)]
            for f in futures:
                idx, img, path, hash_or_status = f.result()
                if hash_or_status == "SKIP_DUPLICATE":
                    skipped_count += 1
                    results.append({
                        "path": path,
                        "skipped": True,
                        "reason": "duplicate"
                    })
                elif isinstance(hash_or_status, str) and hash_or_status.startswith("ERROR:"):
                    results.append({
                        "path": path,
                        "skipped": True,
                        "reason": hash_or_status
                    })
                elif img:
                    images[idx] = img
                    valid_paths[idx] = path
                    file_hashes[idx] = hash_or_status
        
        # Filter out None entries (failed loads and duplicates)
        valid_indices = [i for i, img in enumerate(images) if img is not None]
        images = [images[i] for i in valid_indices]
        valid_paths = [valid_paths[i] for i in valid_indices]
        file_hashes = [file_hashes[i] for i in valid_indices]

        if not images:
            return results

        # 2. Batch Global Embeddings (SigLIP)
        global_embs = self.compute_batch_embeddings(images)

        # 3. Batch Object Detection (YOLO)
        yolo_results = self.yolo(images, verbose=False, stream=False)

        # 4. Process Detections & Collect Crops
        all_crops = []
        crop_metadata = []

        for i, result in enumerate(yolo_results):
            width, height = images[i].size
            
            # Collect detected objects for this frame
            detected_objects = []
            
            # Start result entry
            image_result = {
                "path": valid_paths[i],
                "width": width,
                "height": height,
                "file_hash": file_hashes[i],
                "skipped": False,
                "embeddings": [{
                    "type": "full_image",
                    "class": None,
                    "bbox": None,
                    "embedding": global_embs[i]
                }],
                "detected_objects": []
            }

            # Collect crops and detected objects
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                class_name = self.yolo.names[cls_id]
                
                # Track all detected objects
                if class_name not in detected_objects:
                    detected_objects.append(class_name)
                
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
                        "class": class_name,
                        "bbox": [x1, y1, x2, y2]
                    })
            
            image_result["detected_objects"] = detected_objects
            results.append(image_result)

        # 5. Batch Crop Embeddings (SigLIP)
        if all_crops:
            crop_embs = []
            chunk_size = 32
            for k in range(0, len(all_crops), chunk_size):
                chunk = all_crops[k:k+chunk_size]
                crop_embs.extend(self.compute_batch_embeddings(chunk))
            
            # Find the result entries (not skipped ones)
            non_skipped = [r for r in results if not r.get('skipped', False)]
            
            for j, meta in enumerate(crop_metadata):
                img_idx = meta["img_idx"]
                if img_idx < len(non_skipped):
                    non_skipped[img_idx]["embeddings"].append({
                        "type": "object_crop",
                        "class": meta["class"],
                        "bbox": meta["bbox"],
                        "embedding": crop_embs[j]
                    })

        return results

    def search(self, text_query: str, db_connection, limit: int = 100, min_confidence: float = 0.0):
        """
        Search for images matching the text query.
        
        Args:
            text_query: The search query text
            db_connection: Database connection for metadata
            limit: Maximum number of results to return
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            List of search result dicts with enhanced metadata
        """
        start_time = time.perf_counter()
        
        # 1. Text embedding
        query_emb = self.compute_text_embedding(text_query)
        expected_dim = query_emb.shape[0]

        # 2. Get vectors with caching
        if not hasattr(self, '_emb_matrix') or self._emb_matrix is None:
            logger.info("Loading vector cache (vectors only)...")
            rows = db_connection.get_column_vectors()
            
            if not rows:
                return []
            
            valid_ids = []
            valid_vectors = []
            
            for pk, blob in rows:
                vec = np.frombuffer(blob, dtype=np.float32)
                if vec.shape[0] == expected_dim:
                    valid_ids.append(pk)
                    valid_vectors.append(vec)
            
            if not valid_vectors:
                return []
                
            self._emb_ids = valid_ids
            self._emb_matrix = np.stack(valid_vectors)
            self._cache_timestamp = time.time()
            logger.info(f"Cached {len(valid_ids)} vectors in memory.")
        
        if self._emb_matrix is None or len(self._emb_matrix) == 0:
            return []

        # Check dimension mismatch
        if self._emb_matrix.shape[1] != query_emb.shape[0]:
             raise DimensionMismatchError(
                 expected=query_emb.shape[0],
                 actual=self._emb_matrix.shape[1]
             )

        # 3. Vectorized Cosine Similarity
        scores = np.dot(self._emb_matrix, query_emb)
        
        # 4. Filter by minimum confidence
        if min_confidence > 0:
            valid_mask = scores >= min_confidence
            filtered_indices = np.where(valid_mask)[0]
            filtered_scores = scores[valid_mask]
            
            # Sort filtered results
            sort_order = np.argsort(filtered_scores)[::-1][:limit]
            top_indices = filtered_indices[sort_order]
            top_scores = filtered_scores[sort_order]
        else:
            # Sort all and take top
            top_indices = np.argsort(scores)[::-1][:limit]
            top_scores = scores[top_indices]
        
        top_ids = [self._emb_ids[i] for i in top_indices]
        
        # 5. Hydrate metadata
        metadata_map = db_connection.get_metadata_by_ids(top_ids)
        
        # 6. Deduplicate by frame path (keep highest scoring embedding per frame)
        seen_paths = {}
        final_results = []
        
        for i, pk in enumerate(top_ids):
            meta = metadata_map.get(pk)
            if not meta:
                continue
            
            path = meta['file_path']
            score = float(top_scores[i])
            
            # Skip if we've seen this frame with a higher score
            if path in seen_paths:
                continue
            seen_paths[path] = True
            
            # Generate better reasoning based on match type and object class
            reasoning = self._generate_reasoning(
                meta.get('type', 'full_image'),
                meta.get('class'),
                score,
                text_query
            )
            
            # Get detected objects for this frame
            detected_objects = []
            if hasattr(db_connection, 'get_objects_for_frame'):
                detected_objects = db_connection.get_objects_for_frame(path)
            
            final_results.append({
                "path": path,
                "confidence": score,
                "reasoning": reasoning,
                "width": meta['width'],
                "height": meta['height'],
                "indexed_at": meta['indexed_at'],
                "bbox": meta.get('bbox'),
                "match_type": meta.get('type', 'full_image'),
                "object_class": meta.get('class'),
                "detected_objects": detected_objects,
                "source_type": meta.get('source_type', 'local')
            })

        search_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"Search completed in {search_time:.1f}ms, found {len(final_results)} results")
        
        return final_results

    def _generate_reasoning(self, match_type: str, object_class: str, score: float, query: str) -> str:
        """Generate human-readable reasoning for the match."""
        if match_type == "object_crop" and object_class:
            if score > 0.35:
                return f"Strong match on detected {object_class}"
            elif score > 0.25:
                return f"Moderate match on {object_class}"
            else:
                return f"Possible {object_class} match"
        else:
            if score > 0.35:
                return "Strong visual semantic match"
            elif score > 0.28:
                return "Moderate scene similarity"
            elif score > 0.20:
                return "Weak visual correlation"
            else:
                return "Potential match"

    def invalidate_cache(self):
        """Call after indexing to ensure next search reloads."""
        self._emb_matrix = None
        self._emb_ids = None
        self._cache_timestamp = None
        logger.info("Search cache invalidated.")
