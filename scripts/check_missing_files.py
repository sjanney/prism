"""Check how many frame paths in database don't exist on disk."""

import asyncio
import os
from pathlib import Path

from backend.database import get_session
from backend.models import Frame
from sqlalchemy import select


async def check_missing():
    async with get_session() as session:
        result = await session.execute(select(Frame))
        frames = result.scalars().all()
        
        total = len(frames)
        missing = 0
        existing = 0
        sample_missing = []
        
        print(f"Checking {total} frames...")
        
        for frame in frames:
            path = Path(frame.frame_path)
            if path.exists():
                existing += 1
            else:
                missing += 1
                if len(sample_missing) < 10:
                    sample_missing.append(frame.frame_path)
        
        print(f"\nResults:")
        print(f"  Total frames in DB: {total}")
        print(f"  Existing files: {existing}")
        print(f"  Missing files: {missing} ({missing/total*100:.1f}%)")
        
        if sample_missing:
            print(f"\nSample missing files (first 10):")
            for path in sample_missing[:10]:
                print(f"  - {path}")


if __name__ == "__main__":
    asyncio.run(check_missing())

