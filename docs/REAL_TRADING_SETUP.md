# Real Trading Setup Guide

This guide walks through setting up real trading on Polymarket.

## Prerequisites

1. **Polygon Wallet** - An Ethereum wallet that works on Polygon network
2. **USDC** - Funds on Polygon (not Ethereum mainnet!)
3. **Python Environment** - Our trading system venv

## Step 1: Create/Use a Wallet

You need an **EOA (Externally Owned Account)** wallet. Options:
- **MetaMask** - Most common, browser extension
- **Hardware Wallet** - Ledger/Trezor (most secure)
- **New Dedicated Wallet** - Recommended for automation

### Recommended: Dedicated Trading Wallet

For automated trading, create a fresh wallet:
```bash
# Generate a new wallet (store the private key securely!)
# You can use: https://vanity-eth.tk or create in MetaMask

# IMPORTANT: Never share your private key
# Store in password manager (Bitwarden)
```

## Step 2: Fund Your Wallet with USDC

You need USDC on **Polygon network** (not Ethereum).

Options to get USDC on Polygon:
1. **Bridge from Ethereum** - Use [portal.polygon.technology](https://portal.polygon.technology/)
2. **Buy directly** - Coinbase/Binance → send USDC to Polygon address
3. **Swap on Polygon** - QuickSwap, Uniswap (if you have MATIC)

**Start small:** $50-100 for initial testing.

## Step 3: Set Token Allowances (MetaMask/EOA only)

Before trading, you must approve Polymarket's contracts to use your USDC.

1. Go to [polymarket.com](https://polymarket.com)
2. Connect your wallet
3. Try to make a small trade (~$1)
4. Approve the token spending when prompted

This only needs to be done once per wallet.

## Step 4: Configure Environment Variables

Create a `.env` file in the trading-system directory:

```bash
cd /home/rafa/clawd/trading-system

# Create .env file (don't commit this!)
cat > .env << 'EOF'
# Polymarket Trading Credentials
# NEVER commit this file to git!

# Your wallet's private key (without 0x prefix)
POLYMARKET_PRIVATE_KEY=your_private_key_here

# Optional: If using a proxy wallet (email/Magic wallet)
# POLYMARKET_FUNDER=your_funder_address_here
EOF

# Secure the file
chmod 600 .env
```

**Finding your private key:**
- MetaMask: Settings → Security & Privacy → Reveal Secret Recovery Phrase (or export individual account)
- Warning: Anyone with this key controls your funds

## Step 5: Enable Trading

```bash
cd /home/rafa/clawd/trading-system

# Check status
./venv/bin/python polymarket/real_trader.py --status

# Enable trading (still in dry-run by default)
./venv/bin/python polymarket/real_trader.py --enable
```

## Step 6: Test Dry Run

Before real money:
```bash
# This simulates orders without executing
./venv/bin/python -c "
from polymarket.real_trader import RealTrader
trader = RealTrader(dry_run=True)

# Test a dry-run order
result = trader.place_market_order(
    token_id='71321045679252212594626385532706912750332728571942532289631379312455583992563',  # Example
    side='BUY',
    amount=10.0,
    market_name='Test Market'
)
print(result)
"
```

## Step 7: First Real Trade

**Start with a tiny amount ($5-10):**

```bash
# WARNING: This uses real money!
./venv/bin/python -c "
from polymarket.real_trader import RealTrader
trader = RealTrader(dry_run=False)  # LIVE MODE

# Confirm trading is enabled
if not trader.is_trading_enabled():
    print('Trading not enabled - check config and credentials')
    exit(1)

trader.status()
# Uncomment when ready:
# result = trader.place_market_order(
#     token_id='YOUR_TOKEN_ID',
#     side='BUY',
#     amount=5.0,
#     market_name='Your Market'
# )
# print(result)
"
```

## Risk Limits

Default limits (configurable in `data/trading_config.json`):
- **Max Position Size:** $100
- **Max Daily Loss:** $50
- **Max Open Positions:** 5

To adjust:
```python
from polymarket.real_trader import RealTrader
trader = RealTrader()
trader.config.max_position_size = 200.0
trader.config.max_daily_loss = 100.0
trader.config.save()
```

## Getting Token IDs

Token IDs are required for trading. To find them:

1. **From our scanner:**
   ```bash
   ./venv/bin/python scanner.py  # Shows market info including slugs
   ```

2. **From Polymarket API:**
   ```python
   from polymarket.client import PolymarketClient
   client = PolymarketClient()
   markets = client.get_ai_markets()
   for m in markets:
       print(f"{m['question']}: {m.get('tokens', [])}")
   ```

3. **From CLOB client:**
   ```python
   from py_clob_client.client import ClobClient
   client = ClobClient("https://clob.polymarket.com")
   markets = client.get_simplified_markets()
   ```

## Security Checklist

- [ ] Private key stored in Bitwarden (not just .env)
- [ ] .env file has chmod 600 (only you can read)
- [ ] .env is in .gitignore (never commit!)
- [ ] Using a dedicated wallet (not your main holdings)
- [ ] Started with small amounts ($50-100 max)
- [ ] Tested dry-run mode first
- [ ] Risk limits configured appropriately

## Troubleshooting

**"Trading not enabled"**
- Check `POLYMARKET_PRIVATE_KEY` is set in `.env`
- Run `./venv/bin/python polymarket/real_trader.py --enable`

**"Insufficient balance"**
- Check USDC balance on Polygon (not Ethereum)
- Use [polygonscan.com](https://polygonscan.com) to verify

**"Order failed"**
- Check token allowances are set
- Verify market is still active/tradeable
- Check for minimum order sizes

**"Invalid signature"**
- Make sure private key is correct (without 0x prefix)
- Check signature_type in client config

## Next Steps

1. Complete setup above
2. Make first $5-10 test trade manually
3. Verify trade appears on Polymarket UI
4. Integrate with our scanner for automated alerts
5. Gradually increase position sizes

---

*Document created: 2026-01-28*
*For questions, ask Claude to review the setup*
