# 📚 ClipApp Setup Guide: Local Development on Both PCs

**Date**: March 27, 2026  
**Project**: ClipApp Leaderboard System  
**Status**: Phase 4 - Integration Testing Ready

This guide walks you through setting up ClipApp on your second PC (or first PC) with PostgreSQL backend and React frontend.

---

## 🎯 Prerequisites

Before starting, ensure you have:
- **OS**: Windows 10+ / macOS / Linux
- **Git**: For cloning repository
- **Python 3.12+**: For backend
- **PostgreSQL 13+**: For database
- **Node.js 18+**: For frontend
- **uv package manager**: For Python dependency management

---

## 📋 Part 1: System Setup

### Step 1.1: Install PostgreSQL

**Windows:**
```bash
# Download from: https://www.postgresql.org/download/windows/
# Run installer, note the password you set for 'postgres' user
# Verify installation
psql --version
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
psql --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
psql --version
```

### Step 1.2: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database (in psql prompt)
CREATE DATABASE clipder;
CREATE USER clipder WITH ENCRYPTED PASSWORD 'your_secure_password';
ALTER ROLE clipder SET client_encoding TO 'utf8';
ALTER ROLE clipder SET default_transaction_isolation TO 'read committed';
ALTER ROLE clipder SET default_transaction_deferrable TO off;
ALTER ROLE clipder SET default_transaction_read_only TO off;
GRANT ALL PRIVILEGES ON DATABASE clipder TO clipder;
\q

# Test connection
psql -U clipder -d clipder -c "SELECT NOW();"
```

### Step 1.3: Install Python & uv

**Windows:**
```bash
# Download Python 3.12 from: https://www.python.org/downloads/
# Run installer, check "Add Python to PATH"
# Verify
python --version

# Install uv
pip install uv
```

**macOS:**
```bash
# Install Python 3.12
brew install python@3.12

# Install uv
pip install uv
```

**Linux:**
```bash
sudo apt-get install python3.12 python3.12-venv
pip install uv
```

### Step 1.4: Install Node.js & npm

Visit: https://nodejs.org/ (LTS version)  
Or use package manager:

```bash
# macOS
brew install node

# Linux (Ubuntu)
sudo apt-get install nodejs npm

# Windows - use official installer

# Verify
node --version
npm --version
```

---

## 🚀 Part 2: Clone & Setup Repository

### Step 2.1: Clone Repository

```bash
# Choose a directory (e.g., ~/projects or C:\projects)
cd ~/projects

# Clone (or pull if already cloned)
git clone https://github.com/yourusername/clipapp.git
cd clipapp

# Or if already exists:
git pull origin
```

### Step 2.2: Create `.env` File

```bash
# Copy template
cp .env.example .env

# Edit .env with your values
nano .env  # or use your editor
```

**Required variables for local setup:**

```env
# Database
DATABASE_URL=postgresql+asyncpg://clipder:your_secure_password@localhost:5432/clipder

# Twitch OAuth (get from Twitch Developer Console)
TWITCH_CLIENT_ID=your_client_id_here
TWITCH_CLIENT_SECRET=your_secret_here
TWITCH_REDIRECT_URI=http://localhost:8000/api/v1/auth/twitch/callback

# Twitch channels to monitor (comma-separated)
TWITCH_CHANNELS=channel1,channel2,channel3

# Twitch categories (comma-separated)
TWITCH_CATEGORIES=Just Chatting,Valorant,Minecraft

# Groq API for transcription
GROQ_API_KEY=your_groq_key_here

# JWT Secret (generate random)
SECRET_KEY=your_super_secret_key_change_this_in_production

# Algorithm for JWT
ALGORITHM=HS256

# Token expiration (minutes, 7 days = 10080)
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Optional: Opus Clip API
OPUS_CLIP_API_KEY=optional_key_if_using_opus

# Optional: Supabase
SUPABASE_URL=optional_if_using_supabase
SUPABASE_ANON_KEY=optional_if_using_supabase
```

### Step 2.3: Install Python Dependencies

```bash
# Sync dependencies using uv
uv sync

# Verify installation
python --version
pip list | grep fastapi
```

### Step 2.4: Initialize Database

```bash
# Apply migrations
alembic upgrade head

# Verify (should show 9 tables)
psql -U clipder -d clipder -c "\dt"

# You should see:
# clips, votes, users, user_streamers, user_clip_history
# leaderboard_snapshots, leaderboard_hourly_aggregates
# leaderboard_clip_performance, leaderboard_monthly_summary
```

### Step 2.5: Install Frontend Dependencies

```bash
cd frontend

# Install npm packages
npm install

# Back to root
cd ..
```

---

## 🧪 Part 3: Phase 4 Testing

### Step 3.1: Run Integration Tests

```bash
# Run pytest suite
pytest tests/integration/ -v

# Or run specific critical test (5 concurrent votes)
pytest tests/integration/test_vote_endpoint.py::test_five_concurrent_votes -v
```

### Step 3.2: Run Manual Test Workflow

```bash
# First, start the backend (in another terminal)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run manual tests
python scripts/manual_test_workflow.py
```

### Step 3.3: Verify Health Checks

```bash
# Backend must be running (see Step 3.2)

# Check health endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db
curl http://localhost:8000/api/v1/health/cache
curl http://localhost:8000/api/v1/health/workers
```

---

## 🎮 Part 4: Running the Application

### Step 4.1: Start Backend

**Terminal 1:**
```bash
# Make sure you're in project root
cd /path/to/clipapp

# Start FastAPI backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Output should show:
# ✓ Uvicorn running on http://0.0.0.0:8000
# ✓ Database initialized
# ✓ Background scheduler started
```

### Step 4.2: Start Frontend

**Terminal 2:**
```bash
cd /path/to/clipapp/frontend

# Start React dev server
npm run dev

# Output should show:
# ✓ Vite dev server running on http://localhost:5173
```

### Step 4.3: Open in Browser

**Terminal 3 or Browser:**
```
# Frontend (React UI)
http://localhost:5173

# API Documentation
http://localhost:8000/docs

# Health check
http://localhost:8000/api/v1/health
```

---

## 🔄 Part 5: Syncing Between PC-1 and PC-2

### From PC-1 to PC-2 (Initial Setup)

**On PC-2:**

```bash
# 1. Clone repository (if not already done)
git clone https://github.com/yourusername/clipapp.git
cd clipapp

# 2. Create .env file (copy values from PC-1)
cp .env.example .env
# Edit .env with same values as PC-1

# 3. Install dependencies
uv sync
cd frontend && npm install && cd ..

# 4. Apply migrations
alembic upgrade head

# 5. Run tests to verify
pytest tests/integration/ -v
python scripts/manual_test_workflow.py
```

### Daily Sync (During Development)

**Both PCs:**

```bash
# Pull latest code
git pull origin

# Sync Python dependencies (if pyproject.toml changed)
uv sync

# Apply any new migrations
alembic upgrade head

# Update frontend (if package.json changed)
cd frontend && npm install && cd ..
```

### Verify Real-Time Sync

**PC-1 (Run test):**
```bash
# Start backend
uvicorn main:app --reload

# In another terminal, run manual test
python scripts/manual_test_workflow.py
```

**PC-2 (Watch updates):**
```bash
# Start frontend
cd frontend && npm run dev

# In browser, open http://localhost:5173
# Open DevTools Network → WS tab
# Should see WebSocket connection to PC-1's backend
# Verify messages arriving every 5 seconds
```

---

## 🐛 Troubleshooting

### Database Connection Issues

**Problem**: `FATAL: password authentication failed for user "clipder"`

**Solution**:
```bash
# Verify PostgreSQL is running
psql -U postgres

# Verify user and database exist
\du   # List users
\l    # List databases

# Reset password if needed
ALTER USER clipder WITH ENCRYPTED PASSWORD 'new_password';
```

### Port Already in Use

**Problem**: `Port 8000 already in use`

**Solution**:
```bash
# macOS/Linux: Find and kill process
lsof -i :8000
kill -9 <PID>

# Windows: Find and kill process
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use different port
uvicorn main:app --port 8001
```

### WebSocket Connection Failed

**Problem**: WebSocket doesn't connect in browser console

**Solution**:
```bash
# Verify backend is running
curl http://localhost:8000/api/v1/health

# Check WebSocket endpoint exists
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/leaderboard

# Check firewall (if on network)
# May need to allow port 8000
```

### Tests Failing

**Problem**: `pytest tests/integration/ -v` shows failures

**Solution**:
```bash
# 1. Verify database migrated
alembic upgrade head

# 2. Check PostgreSQL is running
psql -U clipder -d clipder -c "SELECT NOW();"

# 3. Run specific test with verbose output
pytest tests/integration/test_vote_endpoint.py::test_vote_like_increments_counter -vv -s

# 4. Check logs for errors
# Backend logs should show in terminal running uvicorn
```

---

## 📊 Verification Checklist

Before declaring setup complete:

```
Backend Setup:
  ☑ PostgreSQL installed and running
  ☑ Database 'clipder' created
  ☑ User 'clipder' with password set
  ☑ Python 3.12 installed
  ☑ uv package manager working
  ☑ Dependencies installed (uv sync)
  ☑ Migrations applied (alembic upgrade head)

Frontend Setup:
  ☑ Node.js 18+ installed
  ☑ npm install completed
  ☑ Vite configured

Environment:
  ☑ .env file created with all required variables
  ☑ Twitch OAuth credentials set
  ☑ Groq API key set
  ☑ Database URL correct

Testing:
  ☑ Pytest suite runs (pytest tests/integration/ -v)
  ☑ Manual test workflow passes
  ☑ Health endpoints respond
  ☑ Backend starts without errors
  ☑ Frontend starts without errors

Real-Time Sync:
  ☑ WebSocket connects in browser
  ☑ Messages received every 5 seconds
  ☑ Leaderboard component renders
  ☑ Animations smooth
```

---

## 🎉 Next Steps

Once setup is complete on both PCs:

1. **Phase 4 Verification**
   - Run integration tests on both PCs
   - Run manual test workflow
   - Verify health checks
   - Compare results

2. **Frontend Testing**
   - Open leaderboard in browser
   - Submit votes and watch ranks change
   - Verify WebSocket updates every 5 seconds
   - Check animations are smooth

3. **Data Sync Testing**
   - Vote on PC-1 backend
   - Watch update on PC-2 frontend
   - Confirm real-time sync working

4. **Go/No-Go Decision**
   - All tests passing? ✅ GO
   - Issues found? Debug and fix
   - Both PCs synced? ✅ Ready for production

---

## 📞 Support

If stuck:

1. Check troubleshooting section above
2. Review backend logs (uvicorn terminal)
3. Review frontend logs (browser DevTools)
4. Check database logs
5. Review test output (pytest output)

---

## 📝 References

- **FastAPI Docs**: http://localhost:8000/docs (when backend running)
- **Redoc**: http://localhost:8000/redoc
- **Frontend**: http://localhost:5173
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Alembic**: https://alembic.sqlalchemy.org/

---

**Happy coding! 🚀**
