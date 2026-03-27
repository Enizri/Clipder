"""
Create an ADMIN user for ClipApp testing
"""
import asyncio
import os
import uuid
import bcrypt
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


async def create_admin_user():
    from backend.core.database import init_database
    from backend.models.user import User, UserRole
    
    print("=== Creating ADMIN User ===\n")
    
    # Initialize database
    init_database()
    print("✓ Database initialized")
    
    # Import after init
    from backend.core.database import async_session_maker
    
    if async_session_maker is None:
        print("✗ Failed to initialize database")
        return False
    
    # Generate credentials
    admin_email = "admin@clipapp.com"
    admin_password = "AdminPass123!"
    admin_username = "clipper_admin"
    
    # Hash password
    password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
    
    print(f"\nAdmin Credentials:")
    print(f"  📧 Email: {admin_email}")
    print(f"  👤 Username: {admin_username}")
    print(f"  🔑 Password: {admin_password}")
    print(f"  👑 Role: ADMIN\n")
    
    async with async_session_maker() as session:
        try:
            # Check if user already exists
            from sqlalchemy import select
            stmt = select(User).where(User.email == admin_email)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"⚠️  User already exists with ID: {existing_user.id}")
                print(f"   Email: {existing_user.email}")
                print(f"   Role: {existing_user.role.value}")
                await session.rollback()
                return True
            
            # Create admin user
            admin_user = User(
                username=admin_username,
                email=admin_email,
                password_hash=password_hash,
                role=UserRole.ADMIN,
                created_at=datetime.utcnow()
            )
            
            session.add(admin_user)
            await session.flush()
            
            admin_id = admin_user.id
            print(f"✓ ADMIN user created successfully!")
            print(f"  User ID: {admin_id}")
            
            await session.commit()
            return True
            
        except Exception as e:
            print(f"✗ Error creating admin user: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return False


if __name__ == "__main__":
    success = asyncio.run(create_admin_user())
    exit(0 if success else 1)
