# PROJECT.md - AI News → Prediction Market Trading System

## Vision
Build the **best prediction market tooling ecosystem** — tools we use ourselves AND sell to others.

1. **Trade profitably** using our own edge detection
2. **Productize the tools** as services others pay for
3. **Multiple revenue streams:** trading profits + SaaS subscriptions + signals

## Goal
**$10k/month**

## ⚠️ TRADING MODE: PAPER ONLY
We are paper trading until edge is validated. Do NOT execute real trades yet. from:
- Our own trading profits
- Subscription services (alerts, signals, analytics)
- API access for other traders/builders

---

## Current Phase: MVP Validation

### Status: 🟢 Paper Trading Active - First Profitable Trade!

### What Exists (Verified Working)
- [x] Edge tracker (`edge_tracker.py`) — manual event logging
- [x] Auto monitor (`auto_monitor.py`) — news + price scanning
- [x] Paper trader (`paper_trader.py`) — simulated trading
- [x] Scanner (`scanner.py`) — opportunity detection with --notify flag
- [x] Polymarket client (`polymarket/client.py`) — API integration
- [x] **Kalshi client** (`kalshi/client.py`) — regulated US exchange, 4 AI markets
- [x] **Metaculus client** (`metaculus/client.py`) — forecasting aggregation, 1k+ AI questions
- [x] **Multi-platform scanner** (`multi_scanner.py`) — Polymarket + Kalshi + Metaculus
- [x] News monitor (`monitors/news_monitor.py`) — RSS feed parsing
- [x] Dashboard (`dashboard.py`) — portfolio view with live P&L
- [x] **Telegram notifier** (`alerts/telegram_notifier.py`)
- [x] **Position monitor** (`alerts/position_monitor.py`)
- [x] **Real trader** (`polymarket/real_trader.py`) — CLOB API integration, risk limits

### 🆕 WEB PRODUCT: EdgeSignals (Built 2026-01-28)
Location: `/home/rafa/clawd/trading-system/web/`
Stack: Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui

**Features Built:**
- [x] Landing page with value proposition
- [x] Waitlist signup (`/api/waitlist`)
- [x] Signals dashboard (`/dashboard`)
- [x] Signals API (`/api/signals`) — reads from paper_trades.json
- [x] Stripe checkout integration (`/api/stripe/checkout`)
- [x] User authentication (NextAuth v5)
- [x] Pricing tiers: Free ($0), Pro ($49/mo), Enterprise ($299/mo)
- [x] **Marketing materials** (MARKETING.md) — launch thread, Reddit post, Product Hunt

**Revenue Target:** 200 Pro subs × $49/mo = $9,800/mo ≈ $10k goal

**To Deploy:**
1. Set up Vercel project
2. Configure environment variables (see `.env.example`)
3. Create Stripe products/prices
4. Launch with prepared marketing content!

### Bugs Fixed
- [x] Price parsing bug — outcomes was JSON string, now parsed correctly
- [x] AI market filter too weak — rewrote to use events API, now finds 23 markets
- [x] Position monitor price fetch — was using search (wrong results), now uses slug API

### Active Issues
- [ ] No scheduled execution (cron/heartbeat)
- [x] ~~No real trading integration~~ — ✅ CLOB client integrated (`polymarket/real_trader.py`)
- [ ] Web search unavailable (no Brave API key)
- [ ] Wallet setup needed — See `docs/REAL_TRADING_SETUP.md`

---

## 2-Week Action Plan

### Week 1: Foundation (Days 1-7)

#### Day 1-2: Core Fixes ✅ COMPLETE
- [x] **Fix AI market filter** — ✅ Rewrote using events API, now 23 markets
- [x] **Add requirements.txt** — ✅ Created
- [x] **Update TRACKED_MARKETS** — ✅ Using dynamic event discovery
- [x] **Resolve paper position #1** — ✅ CLOSED with +$78.65 profit!

#### Day 3-4: Notifications ✅ COMPLETE
- [x] **Build alert system** — ✅ `alerts/telegram_notifier.py`
- [x] **Hook scanner to alerts** — ✅ `scanner.py --notify` flag
- [x] **Add position alerts** — ✅ `alerts/position_monitor.py`

#### Day 5-6: Monitoring (PRIORITY: MEDIUM)
- [x] **Add live P&L to status** — ✅ dashboard.py shows live prices and P&L
- [x] **Create dashboard script** — ✅ dashboard.py created
- [ ] **Improve news sources** — add Twitter/X, official blogs

#### Day 7: Automation (PRIORITY: MEDIUM)
- [ ] **Add cron scheduling** — run scanner every 15-30 mins
- [ ] **Heartbeat integration** — periodic checks via main agent
- [ ] **Error handling/logging** — robust operation

### Week 2: Trading Ready (Days 8-14)

#### Day 8-9: Backtesting (PRIORITY: HIGH)
- [ ] **Historical edge analysis** — analyze past opportunities
- [ ] **Win rate calculation** — how often were signals correct?
- [ ] **Timing analysis** — how fast do prices move after news?

#### Day 10-11: Risk Framework (PRIORITY: HIGH)
- [ ] **Position sizing rules** — max per trade, per market
- [ ] **Daily loss limits** — stop trading if down X%
- [ ] **Correlation limits** — don't overexpose to one narrative

#### Day 12-13: Real Trading Prep (PRIORITY: MEDIUM)
- [x] **Research Polymarket CLOB API** — ✅ py-clob-client installed & integrated
- [x] **Build real trader module** — ✅ `polymarket/real_trader.py` with risk limits
- [x] **Create setup guide** — ✅ `docs/REAL_TRADING_SETUP.md`
- [ ] **Set up Polygon wallet** — for USDC trades (RAFA ACTION NEEDED)
- [ ] **Small test trade** — $10-50 manual verification

#### Day 14: Launch Small
- [ ] **First real trade** — $50-100 on high-confidence signal
- [ ] **Document learnings** — what worked, what didn't

---

## Metrics

### Paper Trading (Current)
- Total positions: 1 open
- Closed trades: 1
- **Realized P&L: +$78.65** ✅
- Unrealized P&L: -$0.21
- **Total P&L: +$78.44**
- Win rate: 100% (1/1)

### Open Positions
| # | Market | Side | Entry | Current | Amount | P&L | Status |
|---|--------|------|-------|---------|--------|-----|--------|
| 2 | GPT ads by Mar 31 | Yes | 95.9% | 95.8% | $200 | -$0.21 | ✅ Holding |

### Closed Positions
| # | Market | Side | Entry | Exit | Amount | P&L | Result |
|---|--------|------|-------|------|--------|-----|--------|
| 1 | GPT ads by Jan 31 | Yes | 4.45% | 5.15% | $500 | +$78.65 | ✅ WIN |

### System Health
- Last scan: 2026-01-28 17:33
- News feeds active: 6
- AI markets tracked: 23 ✅
- Telegram alerts: Working ✅

---

## Blockers

### 🔴 Critical
*None*

### 🟡 Important  
1. **Polymarket API Access** — Research needed for real trading
   - May need: Polygon wallet, USDC, API credentials

2. **Web Search** — Brave API key not configured
   - Limits news research capabilities

### 🟢 Minor
3. **Better news sources** — Could add Twitter, official blogs
4. **Cron scheduling** — Need automated runs

---

## Technical Notes

### Polymarket
- Uses USDC on Polygon network
- Gamma API for read-only market data (working ✅)
- CLOB API for trading (requires auth)
- Fees: ~1-2% spread + gas

### Architecture
```
news_monitor.py    --> scanner.py --> alerts/telegram_notifier.py
                        |
                        v
polymarket/client.py --> paper_trader.py --> real_trader (TODO)
                        |
                        v
                   edge_tracker.py
                   
alerts/position_monitor.py --> tracks open positions, alerts on moves
```

### Key Files
- `data/paper_trades.json` — trade history
- `data/seen_articles.json` — processed news
- `data/edge_events.json` — tracked events
- `alerts/telegram_notifier.py` — notification system
- `alerts/position_monitor.py` — position tracking & alerts

### Running
```bash
# Activate venv first
cd /home/rafa/clawd/trading-system
./venv/bin/python dashboard.py        # Portfolio view
./venv/bin/python scanner.py --notify # Scan + alert
./venv/bin/python alerts/position_monitor.py  # Check positions
./venv/bin/python auto_monitor.py     # Full monitor run
```

---

## Roadmap

### Phase 1: Validate Edge ← CURRENT
- [x] First profitable trade! (+$78.65)
- [x] Notification system built
- [ ] Run paper trading for 2 weeks
- [ ] Document win rate and returns
- [ ] Identify patterns

### Phase 2: Real Trading (Small)
- $100-500 per trade
- Manual confirmation initially
- Build confidence

### Phase 3: Scale
- Increase position sizes
- Automate execution
- Expand markets (Kalshi, Metaculus)

### Phase 4: Productize (CORE — Not Optional)
**This is how we hit $10k/month:**
- **Alerts Service** — Real-time AI news → market edge notifications ($20-50/mo)
- **Signals API** — Programmatic access for other traders ($100-500/mo)
- **Analytics Dashboard** — Market intelligence for prediction market traders
- **Edge Scanner** — Self-hosted or SaaS tool for finding mispricings
- **Educational content** — Courses/guides on prediction market trading

---

*Last updated: 2026-01-28 15:45 AST*

## ⚠️ TECH STACK REQUIREMENT
**All products must use Next.js (frontend + backend API routes)**
- NO Python web services
- Python OK for scripts/analysis only
- Use TypeScript, Tailwind, shadcn/ui
