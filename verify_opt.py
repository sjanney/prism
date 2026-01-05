
import os
import sys
import numpy as np
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.database import Database
from backend.engine import LocalSearchEngine

# Mock config
import backend.config 
backend.config.config.settings['max_free_images'] = 1000

def test_optimization():
    print("Initializing test database...")
    db_path = "test_opt.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = Database(db_path)
    
    # Create dummy embeddings
    # SigLIP dims = 1152 (SO400M)
    dim = 1152
    
    print("Generating dummy data...")
    # 3 vectors
    vec1 = np.random.rand(dim).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)
    
    vec2 = np.random.rand(dim).astype(np.float32)
    vec2 /= np.linalg.norm(vec2)
    
    vec3 = np.random.rand(dim).astype(np.float32) 
    vec3 /= np.linalg.norm(vec3)
    
    vectors = [vec1, vec2, vec3]
    
    # Save to DB manually using internal methods or just by calling save
    # We need to simulate save_frame_and_embeddings behavior
    
    # Mock entries
    entries = [
        {"path": "/tmp/img1.jpg", "vec": vec1, "type": "full_image"},
        {"path": "/tmp/img2.jpg", "vec": vec2, "type": "full_image"},
        {"path": "/tmp/img3.jpg", "vec": vec3, "type": "object_crop"} # different type
    ]
    
    for i, ent in enumerate(entries):
        # We need to insert into frames first
        cursor = db.get_stats() # Just to get connection? No, direct sqlite
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT INTO frames (frame_path, width, height, indexed_at) VALUES (?, ?, ?, ?)",
                  (ent['path'], 800, 600, "2024-01-01"))
        frame_id = c.lastrowid
        
        c.execute("INSERT INTO embeddings (frame_id, embedding_type, vector) VALUES (?, ?, ?)",
                  (frame_id, ent['type'], ent['vec'].tobytes()))
        conn.commit()
        conn.close()
        
    print("Data inserted.")
    
    # Init Engine
    engine = LocalSearchEngine()
    
    # Hack: Mock compute_text_embedding to return vec1 (perfect match for img1)
    # We don't want to load the real model (heavy)
    original_compute = engine.compute_text_embedding
    engine.compute_text_embedding = lambda txt: vec1
    
    print("Running Search...")
    results = engine.search("dummy", db, limit=2)
    
    print(f"Results found: {len(results)}")
    for res in results:
        print(f" - {res['path']} ({res['confidence']:.4f})")
        
    # Validation
    if len(results) != 2:
        print("FAIL: Expected 2 results (limit=2)")
        sys.exit(1)
        
    if results[0]['path'] != "/tmp/img1.jpg":
        print("FAIL: Expected img1 to be first (exact match)")
        sys.exit(1)
        
    # Check cache
    if not hasattr(engine, '_emb_matrix') or engine._emb_matrix is None:
         print("FAIL: Cache not populated")
         sys.exit(1)
         
    if engine._emb_matrix.shape[0] != 3:
        print(f"FAIL: Cache size mismatch. Expected 3, got {engine._emb_matrix.shape[0]}")
        sys.exit(1)

    print("SUCCESS: Search optimization verification passed.")
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_optimization()
