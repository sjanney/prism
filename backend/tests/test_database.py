"""
Tests for database.py - Database operations and schema.
"""
import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseBasics:
    """Test basic database functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        from database import Database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_database_creates(self, temp_db):
        """Database should initialize without errors."""
        assert temp_db is not None
    
    def test_database_has_schema(self, temp_db):
        """Database should have frames and embeddings tables."""
        stats = temp_db.get_stats()
        assert 'total_frames' in stats
        assert 'total_embeddings' in stats
    
    def test_initial_stats_zero(self, temp_db):
        """New database should have zero counts."""
        stats = temp_db.get_stats()
        assert stats['total_frames'] == 0
        assert stats['total_embeddings'] == 0


class TestFileHashDeduplication:
    """Test file hash and deduplication functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        from database import Database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_compute_file_hash_consistent(self, temp_db):
        """Same file should produce same hash."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_file = f.name
        
        try:
            hash1 = temp_db.compute_file_hash(temp_file)
            hash2 = temp_db.compute_file_hash(temp_file)
            assert hash1 == hash2
            assert len(hash1) == 32  # MD5 hex length
        finally:
            os.unlink(temp_file)
    
    def test_compute_file_hash_different_files(self, temp_db):
        """Different files should produce different hashes."""
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"content 1")
            file1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"content 2")
            file2 = f2.name
        
        try:
            hash1 = temp_db.compute_file_hash(file1)
            hash2 = temp_db.compute_file_hash(file2)
            assert hash1 != hash2
        finally:
            os.unlink(file1)
            os.unlink(file2)
    
    def test_file_exists_by_hash_false(self, temp_db):
        """Non-existent hash should return False."""
        result = temp_db.file_exists_by_hash("nonexistenthash12345678901234567890")
        assert result is False
    
    def test_file_exists_by_path_false(self, temp_db):
        """Non-existent path should return False."""
        result = temp_db.file_exists_by_path("/nonexistent/path/file.jpg")
        assert result is False


class TestSourceTypeDetection:
    """Test source type detection from paths."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        from database import Database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_local_source_type(self, temp_db):
        """Local paths should be detected as 'local'."""
        result = temp_db.get_source_type("/path/to/image.jpg")
        assert result == "local"
    
    def test_s3_source_type(self, temp_db):
        """S3 paths should be detected as 's3'."""
        result = temp_db.get_source_type("s3://bucket/key/image.jpg")
        assert result == "s3"
    
    def test_azure_source_type(self, temp_db):
        """Azure paths should be detected as 'azure'."""
        result = temp_db.get_source_type("azure://container/blob.jpg")
        assert result == "azure"
    
    def test_video_path_source_type(self, temp_db):
        """Video paths (with video:// prefix if used) should be detected appropriately."""
        # Note: The current implementation treats non-prefixed paths as local
        # This is expected behavior - video frames use local file paths
        result = temp_db.get_source_type("/path/to/video_frame.jpg")
        assert result == "local"


class TestColumnVectors:
    """Test vector retrieval functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        from database import Database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_get_column_vectors_empty(self, temp_db):
        """Empty database should return empty list or appropriate type."""
        result = temp_db.get_column_vectors()
        # get_column_vectors may return list of tuples or empty list
        assert len(result) == 0 or (hasattr(result, '__len__') and len(result) == 0)
