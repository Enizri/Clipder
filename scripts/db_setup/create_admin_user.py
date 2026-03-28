"""
Admin User Creation Script
Run this to create a test admin user for testing the platform features.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models import User, UserRole
from backend.core.security import get_password_hash

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")


async def create_admin_user():
    """Create a test admin user for platform testing."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("   Please set DATABASE_URL in your .env file")
        return False
    
    engine = create_async_engine(
        database_url,
        connect_args={
            "server_settings": {"statement_cache_size": "0"},
            "statement_cache_size": 0
        }
    )
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "admin@test.com"))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("✅ Admin user already exists: admin@test.com")
            print(f"   Role: {existing.role}")
            print(f"   Username: {existing.username}")
            return True
        
        admin_user = User(
            username="AdminTest",
            email="admin@test.com",
            password_hash=get_password_hash("AdminPassword123!"),
            role=UserRole.ADMIN,
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("✅ Admin user created successfully!")
        print("   Email: admin@test.com")
        print("   Password: AdminPassword123!")
        print("   Role: ADMIN")
        
        return True


async def create_pro_user():
    """Create a test PRO user for subscription testing."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False
    
    engine = create_async_engine(
        database_url,
        connect_args={
            "server_settings": {"statement_cache_size": "0"},
            "statement_cache_size": 0
        }
    )
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "pro@test.com"))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("✅ Pro user already exists: pro@test.com")
            print(f"   Role: {existing.role}")
            return True
        
        pro_user = User(
            username="ProTest",
            email="pro@test.com",
            password_hash=get_password_hash("ProPassword123!"),
            role=UserRole.PRO,
        )
        
        session.add(pro_user)
        await session.commit()
        
        print("✅ Pro user created successfully!")
        print("   Email: pro@test.com")
        print("   Password: ProPassword123!")
        print("   Role: PRO")
        
        return True


async def main():
    """Main execution."""
    print("🚀 Creating test users for ClipApp...\n")
    
    from backend.models import Base
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("   Please add DATABASE_URL to your .env file")
        print("   Example: DATABASE_URL=postgresql+asyncpg://user:pass@localhost/clipder")
        return
    
    engine = create_async_engine(
        database_url,
        connect_args={
            "server_settings": {"statement_cache_size": "0"},
            "statement_cache_size": 0
        }
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await create_admin_user()
    print()
    await create_pro_user()
    
    print("\n✅ All test users created!")
    print("\n📋 Testing Instructions:")
    print("   1. Login as admin@test.com (role: ADMIN) - Full platform access")
    print("   2. Login as pro@test.com (role: PRO) - Pro features enabled") 
    print("   3. Test as logged-out user - Should see pricing/upgrade prompt on AI Editor")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
