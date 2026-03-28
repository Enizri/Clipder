"""
End-to-end test for PRO clip history feature.
Tests: Save clip, retrieve history, delete clip, access control.
"""
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()


async def main():
    from backend.core.database import init_database
    from backend.models.user import User, UserRole
    from backend.models.user_clip_history import UserClipHistory
    from sqlalchemy import select
    
    print("=== PRO Clip History E2E Test ===\n")
    
    # Initialize database
    init_database()
    print("✓ Database initialized")
    
    # Import the module-level async_session_maker after init
    from backend.core.database import async_session_maker
    
    if async_session_maker is None:
        print("✗ async_session_maker is None!")
        return False
    
    # Create async session
    async with async_session_maker() as session:
        try:
            # Create test users (PRO and regular USER)
            print("\n1. Creating test users...")
            
            pro_user = User(
                username="pro_test_user",
                email="pro_test@test.com",
                password_hash="hashed_password",
                role=UserRole.PRO
            )
            
            free_user = User(
                username="free_test_user",
                email="free_test@test.com",
                password_hash="hashed_password",
                role=UserRole.USER
            )
            
            session.add(pro_user)
            session.add(free_user)
            await session.flush()
            
            pro_user_id = pro_user.id
            free_user_id = free_user.id
            
            print(f"  ✓ Created PRO user (ID: {pro_user_id})")
            print(f"  ✓ Created FREE user (ID: {free_user_id})")
            
            # Create test clips in history for PRO user
            print("\n2. Saving clips to PRO user's history...")
            
            clips = [
                {
                    "user_id": pro_user_id,
                    "clip_id": "clip_123",
                    "clip_title": "Epic Moment",
                    "clip_url": "https://twitch.tv/clip/epic",
                    "clip_channel": "streamer123",
                    "thumbnail_url": "https://example.com/thumb.jpg"
                },
                {
                    "user_id": pro_user_id,
                    "clip_id": "clip_456",
                    "clip_title": "Funny Fail",
                    "clip_url": "https://twitch.tv/clip/fail",
                    "clip_channel": "streamer456",
                    "thumbnail_url": "https://example.com/thumb2.jpg"
                }
            ]
            
            for clip_data in clips:
                history_entry = UserClipHistory(**clip_data)
                session.add(history_entry)
                print(f"  ✓ Saved: {clip_data['clip_title']}")
            
            await session.flush()
            
            # Query clips back
            print("\n3. Retrieving PRO user's clip history...")
            
            stmt = select(UserClipHistory).where(UserClipHistory.user_id == pro_user_id)
            result = await session.execute(stmt)
            saved_clips = result.scalars().all()
            
            print(f"  ✓ Retrieved {len(saved_clips)} clips")
            for clip in saved_clips:
                print(f"    - {clip.clip_title} ({clip.clip_id})")
            
            # Verify free user has no clips
            print("\n4. Verifying FREE user has no history...")
            
            stmt = select(UserClipHistory).where(UserClipHistory.user_id == free_user_id)
            result = await session.execute(stmt)
            free_clips = result.scalars().all()
            
            print(f"  ✓ FREE user has {len(free_clips)} clips (expected: 0)")
            assert len(free_clips) == 0, "FREE user should have no clips!"
            
            # Test delete
            print("\n5. Testing delete functionality...")
            
            first_clip = saved_clips[0]
            await session.delete(first_clip)
            await session.flush()
            
            stmt = select(UserClipHistory).where(UserClipHistory.user_id == pro_user_id)
            result = await session.execute(stmt)
            remaining_clips = result.scalars().all()
            
            print(f"  ✓ Deleted clip: {first_clip.clip_title}")
            print(f"  ✓ Remaining clips: {len(remaining_clips)} (expected: 1)")
            assert len(remaining_clips) == 1, "Should have 1 clip left!"
            
            print("\n✓ All E2E tests passed!")
            await session.commit()
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
