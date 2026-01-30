# Task Queue - Trading System

## How This Works
1. Cron runs every 15 min
2. Picks the top `🔴 ACTIVE` task
3. Spawns sub-agent to work on it
4. Sub-agent completes → marks task done → promotes next task
5. Repeat forever

## Status Legend
- 🔴 ACTIVE — Currently being worked on (only 1 at a time)
- 🟡 NEXT — Ready to start when current completes
- ⚪ BACKLOG — Prioritized but not started
- ✅ DONE — Completed (move to bottom)
- ⏸️ BLOCKED — Waiting on external action

---

## Queue

### ⏸️ BLOCKED
1. **Deploy EdgeSignals to Vercel**
   - ⏸️ **BLOCKED:** Needs fresh auth link (old one expired after ~10 min)
   - ⚠️ Old code JRJZ-RZXP expired (device codes last ~10 min, not 17 hours)
   - **Action needed:** When Rafa is ready, run `cd web && npx vercel login` to get new link
   - Once auth completes: configure env vars, deploy
   - Success: Site accessible at production URL

### ✅ DONE (pending deploy)
2. **Prepare Marketing Launch** — ✅ Completed 2026-01-28
   - [x] Marketing materials created (MARKETING.md)
   - [x] Twitter thread finalized (LAUNCH_READY.md)
   - [x] Reddit post for r/Polymarket (LAUNCH_READY.md)
   - [x] Product Hunt, Discord, Email templates (LAUNCH_READY.md)
   - [ ] Screenshots — requires live site (blocked on Vercel)

### ⏸️ BLOCKED (Need Rafa)
3. **Set up Dodo Payments Products** ← REPLACED Lemon Squeezy
   - ⏸️ BLOCKED: Needs account setup at dodopayments.com
   - Create products: Pro ($49/mo), Enterprise ($299/mo)
   - Get API key and Product IDs
   - Create webhook endpoint pointing to `/api/dodo/webhook`
   - Update web/.env with real keys (see .env.example)
   - **Why Dodo?** Better MOR, no business entity needed, AI-focused, MCP integration

4. **Set up Neon Database**
   - ⏸️ BLOCKED: Needs account creation at console.neon.tech
   - Create "edgesignals" project, get connection string
   - Then run `npm run db:push`

### ✅ DONE
6. **Add Real-time Signal Updates** — ✅ Completed 2026-01-28
   - [x] Created `useRealTimeSignals` hook (10s polling for pro, 60s for free)
   - [x] Visual indicators for new signals (pulse animation, badge)
   - [x] Push notification system (Web Push API)
   - [x] Service worker for push (`public/sw.js`)
   - [x] API routes: `/api/notifications/subscribe`, `/unsubscribe`, `/send`
   - [x] NotificationToggle component for Pro users
   - [x] Live connection indicator in dashboard header
   - [x] Browser notifications on new signals

### ✅ DONE  
9. **Add More Position Tracking** — ✅ Completed 2026-01-28
   - [x] Created `alerts/exit_tracker.py` with full exit management
   - [x] Take-profit, stop-loss, and trailing stop targets
   - [x] Real-time P&L tracking per position
   - [x] Telegram alerts when exit targets hit
   - [x] CLI: `--check`, `--summary`, `--set` commands
   - [x] Tested with position #2 (TP: 99%, SL: 90%, TS: 3pp)

### ✅ DONE
8. **Build Track Record Page** — ✅ Completed 2026-01-28
   - [x] Created `/track-record` route with stats cards
   - [x] Display all trades with timestamps, entry/exit, P&L
   - [x] Win/loss badges, verification notice
   - [x] API route `/api/track-record` reads paper_trades.json
   - [x] Added nav link from landing page
   - [x] Build passes ✅

### ✅ DONE
7. **Expand to More Markets** — ✅ Completed 2026-01-28
   - [x] Researched Kalshi API — kalshi-python SDK integrated
   - [x] Researched Metaculus API — REST API client built
   - [x] Created `kalshi/client.py` — full trading client
   - [x] Created `metaculus/client.py` — forecasting data client
   - [x] Created `multi_scanner.py` — scans all 3 platforms (Polymarket + Kalshi + Metaculus)
   - [x] Cross-platform comparison for arbitrage detection
   - Result: Scanner now works on 3 platforms!

---

## Completed
<!-- Move finished tasks here with completion date -->
- [2026-01-30] **Migrated payments: Lemon Squeezy → Dodo Payments** — Better MOR, MCP tools, AI-focused
- [2026-01-28] **Exit tracker with targets** — TP, SL, trailing stops for positions
- [2026-01-28] **Built Track Record page** — public performance history with verified trades
- [2026-01-28] **Expanded to 3 platforms** — Kalshi + Metaculus + Polymarket integration
- [2026-01-28] Improved news sources — now scraping 9 sources, 73 articles (RSS + web scraping)
- [2026-01-28] Migrated payments from Stripe → Lemon Squeezy → [2026-01-30] Dodo Payments
- [2026-01-28] Built EdgeSignals web app (Next.js + Auth + Dodo Payments checkout)
- [2026-01-28] Created marketing materials (MARKETING.md, LAUNCH_READY.md)
- [2026-01-28] Created position #1 (+$78.65 closed profit)
- [2026-01-28] Built backtesting module (backtester.py) — 100% win rate, 11.2% ROI

---

## Rules for Sub-Agent
1. Work ONLY on the 🔴 ACTIVE task
2. When done: mark it ✅ DONE, move to Completed section
3. Promote the top 🟡 NEXT task to 🔴 ACTIVE
4. Update `memory/YYYY-MM-DD.md` with what you did
5. Update `logs/audit.md` with decisions
6. If blocked: note the blocker, skip to next task, mark blocked task with ⏸️ BLOCKED

## Blockers Log
- [2026-01-28 18:16] Vercel deploy needs auth - link sent to Rafa
- Neon DB setup needs human (account creation)
- [2026-01-30] Dodo Payments setup needs human (account + products at dodopayments.com)
