import sqlite3
import json
import hashlib
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path="prism.db"):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Metadata table with new columns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    frame_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT,
                    source_type TEXT DEFAULT 'local',
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
            
            # Migration: Add new columns if they don't exist (MUST happen before indexes)
            try:
                cursor.execute('ALTER TABLE frames ADD COLUMN file_hash TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE frames ADD COLUMN source_type TEXT DEFAULT "local"')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Create indexes for faster queries (after migrations)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_frames_path ON frames(frame_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_frames_hash ON frames(file_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_frame ON embeddings(frame_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_type ON embeddings(embedding_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_class ON embeddings(object_class)')
            
            conn.commit()

    def compute_file_hash(self, file_path: str) -> Optional[str]:
        """Compute MD5 hash of a file for deduplication."""
        try:
            # For cloud paths, use the path itself as a pseudo-hash
            if file_path.startswith(('s3://', 'azure://')):
                return hashlib.md5(file_path.encode()).hexdigest()
            
            # For local files, compute actual hash
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None

    def file_exists_by_hash(self, file_hash: str) -> bool:
        """Check if a file with given hash already exists."""
        if not file_hash:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM frames WHERE file_hash = ? LIMIT 1", (file_hash,))
            return cursor.fetchone() is not None

    def file_exists_by_path(self, file_path: str) -> bool:
        """Check if a file with given path already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM frames WHERE frame_path = ? LIMIT 1", (file_path,))
            return cursor.fetchone() is not None

    def get_source_type(self, path: str) -> str:
        """Determine source type from path."""
        if path.startswith('s3://'):
            return 's3'
        elif path.startswith('azure://'):
            return 'azure'
        elif '::frame_' in path:  # Video frame virtual path
            return 'video'
        return 'local'

    def save_frame_and_embeddings(self, file_path: str, width: int, height: int, 
                                   embeddings_list: List[Dict], file_hash: Optional[str] = None):
        """
        Saves frame metadata and its associated embeddings.
        embeddings_list: list of dicts {type, class, bbox, embedding}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                now = datetime.now().isoformat()
                source_type = self.get_source_type(file_path)
                
                # Insert Frame with hash and source type
                cursor.execute(
                    """INSERT OR REPLACE INTO frames 
                       (frame_path, file_hash, source_type, width, height, indexed_at) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (file_path, file_hash, source_type, width, height, now)
                )
                frame_id = cursor.lastrowid
                
                # Handle REPLACE case - get the ID and clear old embeddings
                if frame_id is None or frame_id == 0:
                    cursor.execute("SELECT id FROM frames WHERE frame_path = ?", (file_path,))
                    row = cursor.fetchone()
                    if row:
                        frame_id = row[0]
                        cursor.execute("DELETE FROM embeddings WHERE frame_id = ?", (frame_id,))

                # Insert Embeddings
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
                conn.rollback()
                raise e

    def batch_save_frames(self, frames_data: List[Dict]):
        """
        Efficiently save multiple frames in a single transaction.
        frames_data: list of dicts with {path, width, height, embeddings, file_hash}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                now = datetime.now().isoformat()
                
                for frame in frames_data:
                    file_path = frame['path']
                    source_type = self.get_source_type(file_path)
                    
                    cursor.execute(
                        """INSERT OR REPLACE INTO frames 
                           (frame_path, file_hash, source_type, width, height, indexed_at) 
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (file_path, frame.get('file_hash'), source_type, 
                         frame['width'], frame['height'], now)
                    )
                    frame_id = cursor.lastrowid
                    
                    if frame_id is None or frame_id == 0:
                        cursor.execute("SELECT id FROM frames WHERE frame_path = ?", (file_path,))
                        row = cursor.fetchone()
                        if row:
                            frame_id = row[0]
                            cursor.execute("DELETE FROM embeddings WHERE frame_id = ?", (frame_id,))
                    
                    for item in frame.get('embeddings', []):
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
                conn.rollback()
                raise e

    def get_column_vectors(self):
        """Returns all embedding vectors with their IDs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, vector FROM embeddings")
            return cursor.fetchall()

    def get_metadata_by_ids(self, embedding_ids: List[int]) -> Dict[int, Dict]:
        """Returns full metadata for the specified embedding IDs."""
        if not embedding_ids:
            return {}
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Safe parameterized query for list
            placeholders = ','.join('?' * len(embedding_ids))
            query = f'''
                SELECT e.id, f.frame_path, e.embedding_type, e.object_class, e.bbox, 
                       f.width, f.height, f.indexed_at, f.source_type
                FROM embeddings e
                JOIN frames f ON e.frame_id = f.id
                WHERE e.id IN ({placeholders})
            '''
            
            cursor.execute(query, embedding_ids)
            rows = cursor.fetchall()
        
        results = {}
        for r in rows:
            results[r[0]] = {
                "id": r[0],
                "file_path": r[1],
                "type": r[2],
                "class": r[3],
                "bbox": r[4],
                "width": r[5],
                "height": r[6],
                "indexed_at": r[7],
                "source_type": r[8] if len(r) > 8 else "local"
            }
        
        return results

    def get_objects_for_frame(self, frame_path: str) -> List[str]:
        """Get all detected object classes for a frame."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT e.object_class 
                FROM embeddings e
                JOIN frames f ON e.frame_id = f.id
                WHERE f.frame_path = ? AND e.object_class IS NOT NULL
            ''', (frame_path,))
            return [row[0] for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM frames")
            total_frames = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            total_embeddings = cursor.fetchone()[0]
            
            cursor.execute("SELECT indexed_at FROM frames ORDER BY indexed_at DESC LIMIT 1")
            last = cursor.fetchone()
            last_indexed = last[0] if last else "Never"
            
            # Count by source type
            cursor.execute("SELECT source_type, COUNT(*) FROM frames GROUP BY source_type")
            source_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_frames": total_frames,
            "total_embeddings": total_embeddings,
            "last_indexed": last_indexed,
            "db_path": self.db_path,
            "source_counts": source_counts
        }

    def get_embedding_count(self) -> int:
        """Optimized count query for embeddings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            return cursor.fetchone()[0]

    def vacuum_database(self):
        """Clean up and optimize database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Remove orphaned embeddings
            cursor.execute('''
                DELETE FROM embeddings 
                WHERE frame_id NOT IN (SELECT id FROM frames)
            ''')
            conn.commit()
            # Vacuum to reclaim space
            cursor.execute('VACUUM')

    def delete_frame(self, frame_path: str) -> bool:
        """Delete a frame and its embeddings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM frames WHERE frame_path = ?", (frame_path,))
                row = cursor.fetchone()
                if row:
                    frame_id = row[0]
                    cursor.execute("DELETE FROM embeddings WHERE frame_id = ?", (frame_id,))
                    cursor.execute("DELETE FROM frames WHERE id = ?", (frame_id,))
                    conn.commit()
                    return True
                return False
            except Exception:
                conn.rollback()
                return False
