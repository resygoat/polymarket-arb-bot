import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    HOST = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon

    PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY")
    FUNDER = os.getenv("POLYMARKET_FUNDER")

    ARB_THRESHOLD = float(os.getenv("ARB_THRESHOLD", "0.98"))
    SHARES_PER_TRADE = float(os.getenv("SHARES_PER_TRADE", "25.0"))  # Base size, will be scaled
    SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "2"))

    # Allocation percentages — must add up to 100
    ARB_PURE_PERCENT = int(os.getenv("ARB_PURE_PERCENT", "75"))   # Safe pure arb (both sides)
    ARB_LAG_PERCENT = int(os.getenv("ARB_LAG_PERCENT", "25"))      # Directional lag bets

    # Safety check
    if ARB_PURE_PERCENT + ARB_LAG_PERCENT != 100:
        raise ValueError(f"ARB_PURE_PERCENT ({ARB_PURE_PERCENT}) + ARB_LAG_PERCENT ({ARB_LAG_PERCENT}) must equal 100")

    # Target markets
    MARKET_KEYWORDS = ["15 minute", "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp"]
