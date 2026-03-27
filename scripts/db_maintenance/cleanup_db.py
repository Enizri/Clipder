import os
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Load .env file
load_dotenv()

async def cleanup():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in .env")
        return
    
    print(f"Connecting to: {database_url[:50]}...")
    
    # Create a temporary engine just for cleanup
    engine = create_async_engine(
        database_url,
        echo=False,
        connect_args={
            "ssl": "require",
            "statement_cache_size": 0,
        }
    )
    
    try:
        async with engine.begin() as conn:
            print("Dropping alembic_version...")
            await conn.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))
            print("Dropping user_clip_history...")
            await conn.execute(text('DROP TABLE IF EXISTS user_clip_history CASCADE'))
            print("Dropping vote...")
            await conn.execute(text('DROP TABLE IF EXISTS vote CASCADE'))
            print("Dropping user_streamer...")
            await conn.execute(text('DROP TABLE IF EXISTS user_streamer CASCADE'))
            print("Dropping clip...")
            await conn.execute(text('DROP TABLE IF EXISTS clip CASCADE'))
            print("Dropping users...")
            await conn.execute(text('DROP TABLE IF EXISTS users CASCADE'))
            print("Dropping user (old)...")
            await conn.execute(text('DROP TABLE IF EXISTS "user" CASCADE'))
            print('✓ Database cleaned successfully')
    except Exception as e:
        print(f'Error: {e}')
        raise
    finally:
        await engine.dispose()

asyncio.run(cleanup())
