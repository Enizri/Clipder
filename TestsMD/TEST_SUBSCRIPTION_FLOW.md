# ClipApp Subscription Flow Testing

## Test Environment Status

✅ **Database:** Connected to Supabase  
✅ **Admin User:** admin@test.com (ADMIN role)  
✅ **Pro User:** pro@test.com (PRO role)  
✅ **Frontend:** localhost:3001 with hot-reload  
✅ **Backend:** FastAPI at localhost:8000  

---

## Test Scenario 1: Free/Logged-Out User → AI Editor

### Steps
1. **Clear session:**
   - Open DevTools (F12)
   - Application → Local Storage → Clear All
   - Close browser tab and reopen `http://localhost:3001`

2. **Navigate to AI Editor:**
   - Click **"🚀 AI Editor"** tab on main page
   - ⏱️ Observe pricing section appears

### Expected Results
✅ **Pricing Hero Section Displays:**
- "🚀 AI Editor Pro" headline visible
- Demo video playing on left side
- "Get access to:" section with bullet points

✅ **Two Pricing Cards Shown:**
- **Card 1:** "Pro Monthly" ($9.99/month)
  - "Start Free Trial" button (primary CTA)
- **Card 2:** "Pro Yearly" 
  - "Get Yearly Deal" button with discount
  - "2 months free!" savings label

✅ **Alternative Payment Methods:**
- Credit card button
- PayPal button
- "Why upgrade?" link

### Code Reference
[frontend/src/App.tsx - Pricing UI](frontend/src/App.tsx#L1247-L1390)

---

## Test Scenario 2: Free User Clicks "Start Free Trial"

### Steps
1. **Continue from Scenario 1** (on pricing page)
2. Click **"Start Free Trial"** button
3. ⏱️ Observe what happens

### Expected Results
⚠️ **Current Status:** Button is wired but **full trial logic NOT implemented**

**What Should Happen (future):**
- ✅ Access granted to AI Editor for 7 days
- ✅ "Trial expires in X days" countdown timer
- ✅ Full drag-and-drop clip functionality available
- ✅ Can generate multiple shorts
- ❌ Upload to YouTube/TikTok blocked (needs Pro upgrade)

**What Actually Happens Now:**
- Frontend sets `userSubscription = 'trial'`
- Code path exists but expiration logic missing
- No countdown timer implemented
- See frontend logs in DevTools Console

---

## Test Scenario 3: Free User Clicks Payment Option

### Steps
1. **Continue from Scenario 1** (on pricing page)
2. Click **"Get Yearly Deal"** button (or credit card button)
3. ⏱️ Observe what happens

### Expected Results
❌ **Current Status:** Payment integration NOT implemented

**What Should Happen (future):**
- ✅ Stripe payment form appears (or PayPal modal)
- ✅ User enters card details
- ✅ Payment processed
- ✅ "Payment successful" confirmation
- ✅ Access granted to Pro features
- ✅ User redirected to AI Editor

**What Actually Happens Now:**
- Button is visible but non-functional
- Clicking does nothing (no handler)
- No payment processor connected (Stripe/PayPal)
- Frontend logs nothing (button not wired)

---

## Test Scenario 4: Login as PRO User

### Steps
1. **Click "Profile" tab**
2. **Click "Login" button**
3. **Enter credentials:**
   - Email: `pro@test.com`
   - Password: `ProPassword123!`
4. **Click "Login"**
5. ⏱️ Verify login succeeds
6. **Navigate to "🚀 AI Editor"**

### Expected Results
✅ **Login Succeeds:**
- JWT token stored in localStorage
- Profile tab shows "Logged In" state
- User dropdown appears with logout option

✅ **AI Editor Loads Directly:**
- **NO** pricing page shown
- Full AI Editor interface visible
- Queue panel on right side
- Can drag clips to chat

✅ **Role Badge Visible:**
- Profile shows role badge: "PRO"
- User status: pro@test.com

### Verify in DevTools
- **Application → LocalStorage:**
  - Key: `token` (contains JWT)
  - JWT payload includes `user_id`, `email`, `role: "PRO"`

---

## Test Scenario 5: Login as Admin User

### Steps
1. **Click "Profile" tab**
2. **Click "Login" button**
3. **Enter credentials:**
   - Email: `admin@test.com`
   - Password: `AdminPassword123!`
4. **Click "Login"**
5. ⏱️ Verify login succeeds
6. **Check Profile section**

### Expected Results
✅ **Login Succeeds:**
- JWT token stored in localStorage
- Profile shows "ADMIN" role badge
- Full platform access granted

✅ **Admin Tab Visible (if implemented):**
- Admin console available in menu
- Can manage users, clips, categories
- Access to admin queue

---

## Test Scenario 6: Test Leaderboard WebSocket (PRO Feature)

### Steps
1. **Login as pro@test.com** (Scenario 4)
2. **Click "🏆 Leaderboard" tab**
3. ⏱️ Observe WebSocket indicator
4. **Watch live updates** (if clips being swiped)

### Expected Results
✅ **Green WebSocket Indicator:**
- Small green dot appears next to "🏆 Leaderboard"
- Dot pulses continuously when connected
- Disappears when tab switched away

✅ **Leaderboard Data Loads:**
- Top 10 clips displayed with thumbnails
- Monthly scores updated
- View counts shown

✅ **Live Updates:**
- When other users swipe/like, scores update in real-time
- New clips appear in leaderboard
- No page refresh needed

### Code Reference
[frontend/src/App.tsx - WebSocket](frontend/src/App.tsx#L635-L657)

---

## Test Scenario 7: Drag-and-Drop in AI Editor

### Steps
1. **Login as pro@test.com** (Scenario 4)
2. **Navigate to AI Editor tab**
3. **Observe clips in queue panel (right side)**
4. **Drag a clip from queue to chat area**
5. ⏱️ Verify effects

### Expected Results
✅ **Drag Visual Feedback:**
- Clip scales up 1.1x while dragging
- Shadow appears under dragged clip
- Chat area slightly highlights (0.18 opacity background)

✅ **Drop Success:**
- Clip animates back to original size (spring-back effect)
- Clip thumbnail appears in chat
- Small undo button (✕) visible on hover

✅ **Hover-to-Play Video:**
- Hover over clip thumbnail → video plays
- Mouse leave → video stops and resets
- Background video continues playing

### Code Reference
[frontend/src/App.tsx - Drag-and-Drop](frontend/src/App.tsx#L1468-L1510)

---

## Test Scenario 8: Logout and Return to Pricing

### Steps
1. **Login as pro@test.com** (Scenario 4)
2. **Click "AI Editor" tab** (verify no pricing shown)
3. **Click "Profile" tab**
4. **Click "Logout"**
5. ⏱️ Verify logout succeeds
6. **Navigate to "AI Editor" again**

### Expected Results
✅ **Logout Succeeds:**
- JWT token removed from localStorage
- Profile shows "Login" button again
- "Logged In" state cleared

✅ **Pricing Appears After Logout:**
- Navigate to AI Editor
- Pricing page displays (same as Scenario 1)
- Free trial and payment options visible

---

## Debugging Checklist

### Browser DevTools (F12)

**Console Tab:**
```javascript
// Check JWT token
localStorage.getItem('token')

// Check current user
localStorage.getItem('user')
```

**Network Tab:**
- Watch API calls when logging in
- Should see: `POST /api/v1/auth/login`
- Response includes JWT token

**Application Tab → LocalStorage:**
- Key: `token` (JWT)
- Key: `user` (user object)
- Clear before testing scenarios

---

## Known Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| **Free Trial** | ❌ Not Implemented | No expiration timer, no date field in DB |
| **Payment Processing** | ❌ Not Implemented | No Stripe/PayPal integration |
| **Subscription Cancellation** | ❌ Not Implemented | No cancel endpoint |
| **Email Verification** | ❌ Not Implemented | No email confirmation |
| **Pro Feature Gating** | ⚠️ Partial | Roles defined, endpoints not protected |
| **Admin Panel** | ❌ Not Implemented | Admin endpoints missing |

---

## What to Build Next

### 1. Implement Free Trial (2-3 hours)
```python
# Add to User model
trial_started_at: datetime = None
trial_expires_at: datetime = None

# Create endpoint
POST /api/v1/auth/start-trial
  Response: user with trial dates set
```

**Frontend:**
- Show countdown timer: "Trial expires in X days"
- Disable trial button after started
- Show upgrade prompt as expiration nears

### 2. Implement Payment Processing (4-6 hours)
```python
# Install Stripe
uv add stripe

# Create endpoints
POST /api/v1/payments/create-intent  # Create payment intent
POST /api/v1/payments/confirm  # Confirm payment
GET /api/v1/subscriptions  # Get user subscription status
```

**Frontend:**
- Integrate Stripe.js
- Create payment form component
- Handle success/error states

### 3. Protect AI Editor with Pro Check (1-2 hours)
```python
# Use existing function in deps.py
@api_router.get("/editor")
async def get_editor(current_user: User = Depends(check_pro_access)):
    # Only PRO users can access
    ...
```

### 4. Build Admin Panel (4-8 hours)
```python
# Endpoints for admin features
GET /api/v1/admin/users  # List all users
POST /api/v1/admin/users/{id}/roles  # Change user role
GET /api/v1/admin/clips  # View all clips in queue
```

---

## Quick Test Command

```bash
# Terminal 1: Backend
cd e:\projects\ClipApp
uv run uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd e:\projects\ClipApp\frontend
npm run dev

# Browser
http://localhost:3001
```

---

## Success Criteria Checklist

- [ ] Free user can see pricing on AI Editor
- [ ] Free user can click "Start Free Trial"
- [ ] Free user cannot access AI Editor without trial/subscription
- [ ] Pro user can access AI Editor directly
- [ ] Pro user sees "PRO" role badge
- [ ] Pro user leaderboard has green WebSocket indicator
- [ ] Admin user can login
- [ ] Admin user sees "ADMIN" role badge
- [ ] Logout clears token and shows pricing again
- [ ] WebSocket updates leaderboard in real-time

