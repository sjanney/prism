"""Migration script to add sensor_type and original_path columns to existing database."""

import asyncio
import logging
from sqlalchemy import text

from backend.database import engine

logger = logging.getLogger(__name__)


async def migrate():
    """Add sensor_type and original_path columns to frames table."""
    try:
        async with engine.begin() as conn:
            # Check if columns already exist
            result = await conn.execute(text("PRAGMA table_info(frames)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "sensor_type" not in columns:
                logger.info("Adding sensor_type column...")
                await conn.execute(text("ALTER TABLE frames ADD COLUMN sensor_type VARCHAR(20) DEFAULT 'camera'"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sensor_type ON frames(sensor_type)"))
                logger.info("✓ Added sensor_type column")
            else:
                logger.info("sensor_type column already exists")
            
            if "original_path" not in columns:
                logger.info("Adding original_path column...")
                await conn.execute(text("ALTER TABLE frames ADD COLUMN original_path VARCHAR(500)"))
                logger.info("✓ Added original_path column")
            else:
                logger.info("original_path column already exists")
            
            # Update existing frames to have sensor_type = 'camera' if null
            await conn.execute(text("UPDATE frames SET sensor_type = 'camera' WHERE sensor_type IS NULL"))
            
            logger.info("Migration complete!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate())

