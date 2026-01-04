# Polymarket 15-Minute Arbitrage Bot – January 2026 Edition

Pure risk-free arbitrage on BTC / ETH / SOL / XRP 15-minute up/down markets.

**Core Strategy**: Buy both YES and NO shares instantly whenever the combined best ask price < $0.98.  
One side resolves to $1 → guaranteed profit (minus 2% winner fee).

This is the same mechanical edge used by top bots like distinct-baguette ($175k+ monthly profit on leaderboard) and others printing $100k+/month.

Fast polling (every 2s) with safe FOK orders and partial-fill protection.

Designed for 24/7 deployment on Oracle Cloud VM (Frankfurt region recommended for latency + geo allowance).

## Setup on the VM (do this later)
```bash
git clone https://github.com/yourusername/polymarket-arb-bot.git
cd polymarket-arb-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp config/.env.example config/.env
# Edit .env with your dedicated wallet private key

python scripts/approve_allowances.py   # One-time only
python main.py                         # Launch bot