# AI News → Prediction Market Trading System

Trade prediction markets by exploiting the lag between AI news and price repricing.

## Quick Start

```bash
cd /home/rafa/clawd/trading-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run scanner (paper mode)
python scanner.py --notify
```

## Architecture

```
trading-system/
├── scanner.py           # Main opportunity scanner
├── multi_scanner.py     # Polymarket + Kalshi + Metaculus
├── paper_trader.py      # Simulated trading
├── backtester.py        # Historical analysis
├── dashboard.py         # Portfolio view + P&L
├── edge_tracker.py      # Manual edge logging
├── auto_monitor.py      # News + price automation
├── polymarket/          # Polymarket CLOB client
├── kalshi/              # Kalshi API client
├── metaculus/           # Metaculus forecasts
├── monitors/            # RSS news monitors
├── alerts/              # Telegram notifier + position monitor
└── web/                 # EdgeSignals product (Next.js)
```

## Key Commands

```bash
# Find opportunities
python scanner.py --notify

# Multi-platform scan
python multi_scanner.py

# View portfolio
python dashboard.py

# Run news monitor
python -m monitors.news_monitor
```

## Environment

```bash
# Required for real trading
export POLYMARKET_API_KEY="..."
export POLYMARKET_API_SECRET="..."
export POLYMARKET_PASSPHRASE="..."

# Optional notifications
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
```

## Testing

```bash
# Run Python tests
source venv/bin/activate
pytest tests/ -v

# Run EdgeSignals API tests
cd web && bun test
```

Test coverage:
- `tests/test_paper_trader.py` — PaperTrader class, share calculations, P&L math
- `tests/test_scanner.py` — Filtering, scoring, risk limits, Kelly criterion
- `web/tests/api.test.ts` — EdgeSignals API endpoints

## Status

- **Mode:** Paper trading (validation phase)
- **Goal:** $10k/month
- **EdgeSignals:** Web product at `web/`
- **Tests:** 29 Python + API tests passing

See `PROJECT.md` for full roadmap.
