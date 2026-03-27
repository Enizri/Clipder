# 🧪 ClipApp Quick Test Reference

## 📋 Test Users Ready

| Role | Email | Password |
|------|-------|----------|
| 👤 FREE | (logged out) | N/A |
| 👑 PRO | pro@test.com | ProPassword123! |
| 🔑 ADMIN | admin@test.com | AdminPassword123! |

---

## 🚀 Start Testing (3 Terminals)

```bash
# Terminal 1: Backend FastAPI
uv run uvicorn main:app --reload

# Terminal 2: Frontend React
cd frontend && npm run dev

# Terminal 3: Open browser
http://localhost:3001
```

---

## ✅ Test Checklist (5 minutes)

### 1️⃣ Free User Flow
```
[ ] Go to http://localhost:3001
[ ] Click "🚀 AI Editor" tab
[ ] Verify pricing page appears
[ ] See "Start Free Trial" button
```

### 2️⃣ Pro User Flow  
```
[ ] Click "Profile" → "Login"
[ ] Email: pro@test.com
[ ] Password: ProPassword123!
[ ] Click "🚀 AI Editor"
[ ] Editor loads (NO pricing page)
[ ] Verify "PRO" badge in profile
```

### 3️⃣ Leaderboard WebSocket
```
[ ] Stay logged in as pro user
[ ] Click "🏆 Leaderboard"
[ ] Green dot appears next to tab
[ ] Dot pulses continuously
[ ] See top 10 clips with scores
```

### 4️⃣ Drag-and-Drop
```
[ ] In AI Editor, find clip in queue (right panel)
[ ] Drag clip to chat area (left side)
[ ] See clip thumbnail appear
[ ] Hover clip to play video
[ ] Mouse leave to stop video
[ ] Small ✕ button to undo
```

### 5️⃣ Logout & Reprice
```
[ ] Click "Profile" → "Logout"
[ ] Verify token cleared (DevTools)
[ ] Click "🚀 AI Editor"
[ ] Pricing appears again
[ ] ✅ Full loop complete!
```

---

## 🔍 DevTools Quick Commands

```javascript
// Check JWT token
localStorage.getItem('token')

// Check current user
localStorage.getItem('user')

// Clear all session data
localStorage.clear()
```

---

## ⚠️ Known Limitations

| Feature | Status |
|---------|--------|
| Payment processing | ❌ Not yet |
| Trial expiration | ❌ Not yet |
| Admin panel | ❌ Not yet |
| Send feedback | ✅ Works |
| WebSocket leaderboard | ✅ Works |
| Drag-and-drop UI | ✅ Works |

---

## 📊 What Works NOW

✅ User login/logout  
✅ Role-based access (USER/PRO/ADMIN)  
✅ Pricing page for free users  
✅ WebSocket real-time leaderboard  
✅ Drag-and-drop clip management  
✅ Hover-to-play video in chat  
✅ Beautiful TikTok-style UI  

---

## 🔧 If Something Breaks

**Backend error?**
```bash
# Terminal 1: Check logs, Ctrl+C to stop
# Then restart:
uv run uvicorn main:app --reload
```

**Frontend error?**
```bash
# Terminal 2: Check DevTools Console (F12)
# Ctrl+C to stop, then:
cd frontend && npm run dev
```

**Database error?**
```bash
# Verify .env has DATABASE_URL set
echo $DATABASE_URL
# If empty, add to .env file
```

**Session stuck?**
```javascript
// In DevTools Console:
localStorage.clear()
location.reload()
```

---

## 📝 Test Notes

**Free User Signup NOT Implemented Yet**
- Current: Can only test with our created PRO account
- Future: Add registration endpoint (TODO)

**Payment Buttons Not Wired**
- Current: Click "Get Yearly Deal" → nothing happens
- Future: Integrate Stripe payment processor (TODO)

**Trial Expiration NOT Tracked**
- Current: "Start Trial" works but no countdown
- Future: Add trial_expires_at to User model (TODO)

**Pro Feature Enforcement NOT Applied**
- Current: AI Editor accessible to all logged users
- Future: Apply check_pro_access() dependency (TODO)

---

## 🎯 Success = All 5 Checkboxes Done

```
[ ] Free user sees pricing       ← Test #1
[ ] Pro user skips pricing       ← Test #2
[ ] WebSocket green dot works    ← Test #3
[ ] Drag-drop works smoothly     ← Test #4
[ ] Logout clears everything     ← Test #5

✅ ALL TESTS PASS = READY FOR NEXT PHASE
```

