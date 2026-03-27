#!/usr/bin/env bash
# Quick verification script to test the bug fixes

echo "=== ClipApp Bug Fixes - Verification Script ==="
echo ""
echo "Testing 1: Server Startup"
timeout 5 python -m uvicorn main:app --port 8001 2>&1 | grep -E "Application startup|error" || true
echo ""
echo "Testing 2: Database Connection"
python -c "
from backend.core.database import AsyncSessionLocal
import asyncio
async def test():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        result = await session.execute(text('SELECT 1'))
        print('✅ Database connected')
asyncio.run(test())
" 2>&1 || echo "❌ Database connection failed"
echo ""
echo "Testing 3: API Routes"
python -c "
from main import app
routes = [route.path for route in app.routes]
print('Available routes:')
vote_routes = [r for r in routes if 'vote' in r or 'clips' in r]
for route in vote_routes:
    print(f'  ✅ {route}')
" 2>&1 || echo "❌ Route inspection failed"
echo ""
echo "=== Verification Complete ==="
