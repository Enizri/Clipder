"""
Clean all user clip history from database
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import delete

load_dotenv()


async def clean_history():
    from backend.core.database import init_database
    from backend.models.user_clip_history import UserClipHistory
    
    print("🧹 Cleaning clip history...\n")
    
    init_database()
    from backend.core.database import async_session_maker
    
    if async_session_maker is None:
        print("✗ Failed to connect")
        return False
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(delete(UserClipHistory))
            deleted_count = result.rowcount
            await session.commit()
            print(f"✓ Deleted {deleted_count} history entries")
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            await session.rollback()
            return False


if __name__ == "__main__":
    success = asyncio.run(clean_history())
    exit(0 if success else 1)
