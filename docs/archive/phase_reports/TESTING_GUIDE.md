# ClipApp Admin & Subscription Testing Guide

## Setup Instructions

### 1. Create Test Users

Run the admin user creation script (**after setting DATABASE_URL**):

```bash
cd e:\projects\ClipApp
uv run python create_admin_user.py
```

**Required:** Your `.env` file must have `DATABASE_URL` set!

Example `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/clipder
```

### 2. Test User Credentials Created

After running the script, you'll have:

| User Type | Email | Password | Role | Purpose |
|-----------|-------|----------|------|---------|
| **Admin** | admin@test.com | AdminPassword123! | ADMIN | Full platform access, admin features |
| **Pro** | pro@test.com | ProPassword123! | PRO | Pro AI Editor features |
| **Free** | (any) | (any) | USER | Default user (test upgrade flow) |

---

## Testing Flows

### Flow 1: Free User → AI Editor (Shows Pricing)

**Steps:**
1. **Logout** or use an incognito window
2. **Do NOT login**
3. Click **"🚀 AI Editor"** tab
4. **Expected:** Should see pricing hero with benefits

**Verify UI shows:**
- ✅ "🚀 AI Editor Pro" headline
- ✅ Demo video on left side
- ✅ Two pricing cards: "Pro Monthly" and "Pro Yearly"
- ✅ "Start Free Trial" button (main CTA)
- ✅ Alternative payment options (credit card, PayPal buttons)

---

### Flow 2: Free Trial (7 Days)

**Steps:**
1. On the pricing page, click **"Start Free Trial"**
2. You should be permitted to use the AI Editor
3. **Expected:** Access granted to all Pro features for trial period

**Current Status:** ⚠️ Button is wired to `setUserSubscription('trial')` but trial expiration logic is NOT yet implemented

---

### Flow 3: Pro Subscription (Yearly Deal)

**Steps:**
1. Click **"Get Yearly Deal"** button
2. **Expected:** Payment form should appear

**Current Status:** ⚠️ UI button is present but payment processing (Stripe/PayPal) is **NOT implemented yet**

---

### Flow 4: Login as Pro User

**Steps:**
1. Click **"Profile"** tab
2. Click **"Login"**
3. Enter: `pro@test.com` / `ProPassword123!`
4. Navigate to **"🚀 AI Editor"** tab
5. **Expected:** AI Editor loads directly (no pricing page)

**Verify:**
- ✅ No pricing/paywall shown
- ✅ Full AI Editor interface visible
- ✅ Role badge shows "PRO" in profile

---

### Flow 5: Admin User

**Steps:**
1. Login as `admin@test.com` / `AdminPassword123!`
2. Click **"Profile"** tab
3. **Expected:** Role badge shows "ADMIN"
4. Admin features should be available (if implemented)

---

## What's Implemented ✅

- ✅ User roles (USER, PRO, ADMIN) in database
- ✅ Role-based access checks in backend
- ✅ Pricing UI showing free vs pro
- ✅ "Start Free Trial" button
- ✅ "Get Yearly Deal" button
- ✅ Role display in profile section
- ✅ WebSocket for live leaderboard (PRO feature)

---

## What's NOT Yet Implemented ❌

- ❌ **Payment Processing:** No Stripe/PayPal integration
- ❌ **Trial Expiration:** No `trial_expires_at` field or countdown logic
- ❌ **Subscription Management:** No cancel subscription option
- ❌ **Payment Forms:** No credit card or PayPal checkout UI
- ❌ **Email Verification:** No email confirmation on signup
- ❌ **Pro Feature Gating:** Features not yet tied to role checks

---

## Frontend Code References

**Pricing UI Page:**
- File: [frontend/src/App.tsx](frontend/src/App.tsx#L1247-L1390)
- Lines: 1247-1390
- Shows pricing for free users in AI Editor section

**User Role in Profile:**
- File: [frontend/src/App.tsx](frontend/src/App.tsx#L1795)
- Displays current user role as badge

---

## Backend Code References

**Role Definitions:**
- File: [backend/models/user.py](backend/models/user.py)
- Enum: `UserRole` (USER, PRO, ADMIN)

**Pro Access Check:**
- File: [backend/api/v1/deps.py](backend/api/v1/deps.py)
- Function: `check_pro_access()`
- **Note:** Function exists but is NOT used in any endpoint yet

**Admin User Creation:**
- File: [create_admin_user.py](create_admin_user.py)
- Script to create test users

---

## Testing Checklist

### Pre-Launch

- [ ] DATABASE_URL configured in .env
- [ ] Admin users created via `uv run python create_admin_user.py`
- [ ] Can login with all three user types
- [ ] Free users see pricing on AI Editor tab
- [ ] Pro users skip pricing and go to editor
- [ ] Role badges display correctly in profile

### Payment Features (When Ready)

- [ ] Implement Stripe integration (`uv add stripe`)
- [ ] Add trial_expires_at field to User model
- [ ] Create payment processing endpoints
- [ ] Add subscription cancellation logic
- [ ] Wire "Get Yearly Deal" to payment processor
- [ ] Add trial countdown timer UI

---

## Tips

1. **Clear localStorage between tests:**  
   - Open DevTools → Application → LocalStorage → Clear All

2. **Use browser DevTools to monitor:**
   - Network tab: Watch API calls
   - Console: Check for errors
   - Storage: See JWT tokens & session data

3. **Test in incognito/private window:**
   - Faster to clear session and cookies
   - No auth token pollution

---

## Quick Start

```bash
# 1. Ensure DATABASE_URL is in .env
# 2. Create test users
uv run python create_admin_user.py

# 3. Start backend
uv run uvicorn main:app --reload --port 8000

# 4. In another terminal, start frontend
cd frontend
npm run dev

# 5. Visit http://localhost:3001
# 6. Test flows from the checklist above
```

