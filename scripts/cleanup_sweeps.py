"""Clean up database entries that point to sweeps/ directory.

Sweeps are intermediate frames that should not be indexed.
Only key frames from samples/ should be in the database.
"""

import asyncio
from pathlib import Path

from backend.database import get_session
from backend.models import Frame
from sqlalchemy import select, delete


async def cleanup_sweeps():
    """Remove all frames that point to files in the sweeps/ directory."""
    async with get_session() as session:
        # Count sweeps before deletion
        result = await session.execute(select(Frame))
        all_frames = result.scalars().all()
        
        sweeps_count = 0
        samples_count = 0
        
        for frame in all_frames:
            if "/sweeps/" in frame.frame_path:
                sweeps_count += 1
            elif "/samples/" in frame.frame_path:
                samples_count += 1
        
        print(f"Database status:")
        print(f"  Total frames: {len(all_frames)}")
        print(f"  Frames in sweeps/: {sweeps_count}")
        print(f"  Frames in samples/: {samples_count}")
        print(f"  Other: {len(all_frames) - sweeps_count - samples_count}")
        
        if sweeps_count == 0:
            print("\n✓ No sweeps found in database. Database is clean!")
            return
        
        # Delete frames in sweeps/
        print(f"\nDeleting {sweeps_count} frames from sweeps/ directory...")
        delete_stmt = delete(Frame).where(Frame.frame_path.like("%/sweeps/%"))
        result = await session.execute(delete_stmt)
        await session.commit()
        
        print(f"✓ Successfully deleted {sweeps_count} sweep frames")
        print(f"✓ Database now contains only key frames from samples/")


if __name__ == "__main__":
    asyncio.run(cleanup_sweeps())

