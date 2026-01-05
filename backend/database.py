import sqlite3
import json
import os
import numpy as np
from datetime import datetime

class Database:
    def __init__(self, db_path="prism.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_path TEXT UNIQUE NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                width INTEGER,
                height INTEGER,
                indexed_at DATETIME
            )
        ''')

        # Vector storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER,
                embedding_type TEXT,    -- 'full_image' or 'object_crop'
                object_class TEXT,      -- NULL for full_image
                bbox TEXT,              -- JSON: "[x1,y1,x2,y2]"
                vector BLOB,            -- Serialized numpy array
                FOREIGN KEY (frame_id) REFERENCES frames(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save_frame_and_embeddings(self, file_path, width, height, embeddings_list):
        """
        Saves frame metadata and its associated embeddings.
        embeddings_list: list of dicts {type, class, bbox, embedding}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Insert Frame
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO frames (frame_path, width, height, indexed_at) VALUES (?, ?, ?, ?)",
                (file_path, width, height, now)
            )
            frame_id = cursor.lastrowid
            
            # If it was a REPLACE, we might want to clear old embeddings for this frame to avoid duplicates
            if frame_id is None: 
                # REPLACE might not return lastrowid if it didn't strictly insert a new row ID in some sqlite versions/cases? 
                # Actually INSERT OR REPLACE usually works. 
                # Let's fetch the ID to be safe if it's an update
                cursor.execute("SELECT id FROM frames WHERE frame_path = ?", (file_path,))
                frame_id = cursor.fetchone()[0]
                # clear old embeddings
                cursor.execute("DELETE FROM embeddings WHERE frame_id = ?", (frame_id,))

            # 2. Insert Embeddings
            for item in embeddings_list:
                vector_blob = item['embedding'].tobytes()
                bbox_json = json.dumps(item.get('bbox')) if item.get('bbox') else None
                
                cursor.execute(
                    '''INSERT INTO embeddings 
                       (frame_id, embedding_type, object_class, bbox, vector) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (frame_id, item['type'], item.get('class'), bbox_json, vector_blob)
                )
                
            conn.commit()
        except Exception as e:
            print(f"DB Error: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_column_vectors(self):
        """Returns all embedding vectors with their IDs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, vector FROM embeddings")
        rows = cursor.fetchall()
        
        conn.close()
        return rows

    def get_metadata_by_ids(self, embedding_ids):
        """Returns full metadata for the specified embedding IDs."""
        if not embedding_ids:
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Safe parameterized query for list
        placeholders = ','.join('?' * len(embedding_ids))
        query = f'''
            SELECT e.id, f.frame_path, e.embedding_type, e.object_class, e.bbox, f.width, f.height, f.indexed_at
            FROM embeddings e
            JOIN frames f ON e.frame_id = f.id
            WHERE e.id IN ({placeholders})
        '''
        
        cursor.execute(query, embedding_ids)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            pk, path, emb_type, obj_class, bbox, w, h, idx_at = r
            results.append({
                "id": pk,
                "file_path": path,
                "type": emb_type,
                "class": obj_class,
                "bbox": bbox,
                "width": w,
                "height": h,
                "indexed_at": idx_at
            })
        
        # Sort results to match input order if necessary, but caller (search) usually re-sorts or attaches scores
        # We'll return a dict for O(1) lookup
        return {res['id']: res for res in results}

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM frames")
        total_frames = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        total_embeddings = cursor.fetchone()[0]
        
        cursor.execute("SELECT indexed_at FROM frames ORDER BY indexed_at DESC LIMIT 1")
        last = cursor.fetchone()
        last_indexed = last[0] if last else "Never"
        
        conn.close()
        
        return {
            "total_frames": total_frames,
            "total_embeddings": total_embeddings,
            "last_indexed": last_indexed,
            "db_path": self.db_path
        }

