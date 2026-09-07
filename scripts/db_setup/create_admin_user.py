"""
Admin User Promotion Script

Twitch-only auth: users are created automatically on first Twitch login.
Use this script to promote an existing user to ADMIN or PRO by Twitch username.

Usage:
  uv run python scripts/db_setup/create_admin_user.py --username <twitch_username> --role ADMIN
"""

import asyncio
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models import User, UserRole

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


async def promote_user(twitch_username: str, role: UserRole) -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in .env")
        return

    engine = create_async_engine(
        database_url,
        connect_args={
            "server_settings": {"statement_cache_size": "0"},
            "statement_cache_size": 0,
        },
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.twitch_username == twitch_username)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"No user found with twitch_username='{twitch_username}'.")
            print("The user must log in with Twitch at least once before being promoted.")
            return

        user.role = role
        if role == UserRole.PRO:
            user.is_pro = True
        await session.commit()
        print(f"Promoted @{twitch_username} (id={user.id}) to {role.value}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a Twitch user to ADMIN or PRO")
    parser.add_argument("--username", required=True, help="Twitch display name of the user")
    parser.add_argument(
        "--role",
        required=True,
        choices=["ADMIN", "PRO"],
        help="Role to assign",
    )
    args = parser.parse_args()
    asyncio.run(promote_user(args.username, UserRole[args.role]))


if __name__ == "__main__":
    main()
