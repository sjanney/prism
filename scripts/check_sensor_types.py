"""Check sensor type distribution in database."""

import asyncio
from collections import Counter

from backend.database import get_session
from backend.models import Frame
from sqlalchemy import select, func


async def check_sensor_types():
    async with get_session() as session:
        # Get all frames with sensor types
        result = await session.execute(select(Frame.sensor_type))
        sensor_types = result.scalars().all()
        
        counts = Counter(sensor_types)
        
        print(f"Total frames: {sum(counts.values())}")
        print("\nSensor type distribution:")
        for sensor_type, count in counts.most_common():
            print(f"  {sensor_type}: {count}")
        
        # Also check if sensor_type column exists
        print(f"\nSample frames (first 10):")
        result = await session.execute(select(Frame.sensor_type, Frame.frame_path).limit(10))
        for sensor_type, path in result.all():
            print(f"  {sensor_type}: {path[:60]}...")


if __name__ == "__main__":
    asyncio.run(check_sensor_types())

