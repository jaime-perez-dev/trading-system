# EdgeSignals Deployment Guide

## Quick Deploy to Vercel (5 minutes)

### Option A: Via Vercel Dashboard (Easiest)

1. **Go to [vercel.com](https://vercel.com)** and sign up/login with GitHub

2. **Import the repository:**
   - Click "Add New" → "Project"
   - Import from GitHub (connect if needed)
   - Select this repo, set root directory to `trading-system/web`

3. **Set environment variables** in Vercel dashboard:
   ```
   DATABASE_URL=<from Neon dashboard>
   NEXTAUTH_SECRET=<generate with: openssl rand -base64 32>
   NEXTAUTH_URL=https://your-app.vercel.app
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

4. **Deploy!** Vercel auto-builds and deploys.

### Option B: Via CLI (Needs Auth Link)

If Jaime starts the auth, you'll get a link like:
```
https://vercel.com/oauth/device?user_code=XXXX-XXXX
```

Click it, authorize, and the deploy proceeds automatically.

---

## Database Setup (Neon)

We already have a Neon account (jaime.a.perez93@outlook.com).

1. Login at [console.neon.tech](https://console.neon.tech)
2. Create a new project called "edgesignals"
3. Copy the connection string (it looks like):
   ```
   postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Add `&connection_limit=1` for serverless compatibility

---

## Stripe Setup

1. Go to [dashboard.stripe.com](https://dashboard.stripe.com)
2. Create/login to account
3. Get API keys from Developers → API keys
4. Create products:
   - **Pro Plan:** $49/month
   - **Enterprise Plan:** $299/month
5. Get price IDs for checkout

---

## After Deploy

1. Run database migrations:
   ```bash
   cd trading-system/web
   DATABASE_URL="..." npm run db:push
   ```

2. Test signup/login flow
3. Test Stripe checkout (use test cards)
4. 🚀 Launch!

---

## Files Ready
- ✅ Next.js app with App Router
- ✅ Auth (NextAuth v5)
- ✅ Stripe checkout routes
- ✅ Signals API
- ✅ Waitlist API
- ✅ Prisma + PostgreSQL schema

Just need: Deploy + Environment variables
