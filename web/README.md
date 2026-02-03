# EdgeSignals Web App

Next.js web application for EdgeSignals - AI-powered prediction market signals.

## Tech Stack

- **Framework:** Next.js 16 with App Router
- **Database:** PostgreSQL (Neon) with Prisma ORM
- **Auth:** NextAuth.js v5
- **Payments:** Stripe
- **Styling:** Tailwind CSS v4
- **Analytics:** Google Analytics 4 (gtag)

## Getting Started

### Prerequisites

- Node.js 20+
- A Neon PostgreSQL database (free tier available)
- Stripe account (for payments)

### 1. Clone and Install

```bash
cd trading-system/web
npm install
```

### 2. Set Up Neon Database

1. **Create a Neon account** at [neon.tech](https://neon.tech)

2. **Create a new project** (free tier is fine)

3. **Get your connection string** from the Neon dashboard:
   - Go to your project → Connection Details
   - Copy the connection string (looks like: `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`)

4. **For serverless deployments** (Vercel, etc.), add connection pooling:
   ```
   postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require&connection_limit=1
   ```
   The `connection_limit=1` prevents connection exhaustion in serverless environments.

### 3. Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local` with your actual values:
- `DATABASE_URL` — Your Neon connection string
- `NEXTAUTH_SECRET` — Generate with `openssl rand -base64 32`
- `NEXTAUTH_URL` — Your app URL (http://localhost:3000 for dev)
- Stripe keys (optional for initial setup)
- `NEXT_PUBLIC_GA_MEASUREMENT_ID` — Google Analytics Measurement ID (optional)

### 4. Initialize Database

```bash
# Generate Prisma client
npm run db:generate

# Push schema to database (creates tables)
npm run db:push
```

### 5. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app.

## Database Commands

```bash
npm run db:generate  # Generate Prisma client
npm run db:push      # Push schema changes to database
npm run db:migrate   # Create and apply migrations
npm run db:studio    # Open Prisma Studio (visual database browser)
```

## Deployment (Vercel)

1. Connect your repo to Vercel
2. Add environment variables in Vercel dashboard:
   - `DATABASE_URL` (with `&connection_limit=1`)
   - `NEXTAUTH_SECRET`
   - `NEXTAUTH_URL` (your production URL)
   - Stripe keys
3. Deploy!

Prisma client is auto-generated during build (`postinstall` script).

## Project Structure

```
web/
├── app/                 # Next.js App Router pages
├── components/          # React components
├── lib/                 # Utilities and shared code
├── prisma/
│   └── schema.prisma    # Database schema
├── public/              # Static assets
└── .env.local           # Local environment (not committed)
```

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma with Neon](https://neon.tech/docs/guides/prisma)
- [NextAuth.js](https://authjs.dev)
- [Stripe Integration](https://stripe.com/docs)

## Google Analytics Setup

EdgeSignals includes Google Analytics 4 integration for tracking user behavior and app performance.

### 1. Create Google Analytics Property

1. Go to [Google Analytics](https://analytics.google.com/)
2. Create a new property or select an existing one
3. Go to Admin → Property → Data Streams
4. Create a new web stream for your domain
5. Copy the Measurement ID (format: `G-XXXXXXXXXX`)

### 2. Configure Environment Variables

Add your Measurement ID to `.env.local`:

```bash
NEXT_PUBLIC_GA_MEASUREMENT_ID="G-XXXXXXXXXX"
```

### 3. Automatic Tracking

The integration automatically tracks:
- Page views
- Site search (via search parameters)
- File downloads
- Outbound clicks

### 4. Manual Event Tracking

You can track custom events using the `trackEvent` function:

```tsx
import { trackEvent } from '@/hooks/useAnalytics';

// Track a custom event
trackEvent({
  action: 'click',
  category: 'Button',
  label: 'CTA Button Clicked',
  value: 1
});
```

Analytics are only active when the `NEXT_PUBLIC_GA_MEASUREMENT_ID` environment variable is set.
