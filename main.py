import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import BUY
from py_clob_client.order_builder.constants import OrderType

from config.config import Config

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)

class ArbitrageBot:
    def __init__(self):
        if not Config.PRIVATE_KEY:
            logging.error("PRIVATE_KEY missing in .env – add it and restart.")
            exit(1)

        self.client = ClobClient(
            Config.HOST,
            key=Config.PRIVATE_KEY,
            chain_id=Config.CHAIN_ID,
            funder=Config.FUNDER
        )
        creds = self.client.create_or_derive_api_creds()
        self.client.set_api_creds(creds)

        self.pairs: Dict[str, dict] = {}
        
        # Stats
        self.stats = {
            "scans": 0,
            "opps": 0,
            "successful_trades": 0,
            "daily_profit": 0.0,      # Resets daily
            "total_profit": 0.0,       # Cumulative
            "invested": 0.0
        }
        
        # For daily reset
        self.current_date = datetime.utcnow().date()
        self.last_report_sent = False

    def send_discord_report(self):
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            logging.info("No Discord webhook set – skipping report")
            return

        embed = {
            "title": "🚀 Daily Polymarket Arb Bot Report",
            "description": f"Report for {self.current_date}",
            "color": 0x00ff00 if self.stats["daily_profit"] >= 0 else 0xff0000,
            "fields": [
                {"name": "Daily Profit", "value": f"${self.stats['daily_profit']:.2f}", "inline": True},
                {"name": "Total Compounded Profit", "value": f"${self.stats['total_profit']:.2f}", "inline": True},
                {"name": "Opportunities Found (Day)", "value": str(self.stats["opps"]), "inline": True},
                {"name": "Successful Trades (Day)", "value": str(self.stats["successful_trades"]), "inline": True},
                {"name": "Total Invested (Cumulative)", "value": f"${self.stats['invested']:.2f}", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Pure arb strategy – compounding in progress"}
        }

        payload = {
            "username": "Arb Bot",
            "embeds": [embed]
        }

        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 204:
                logging.info("Daily Discord report sent successfully")
            else:
                logging.warning(f"Discord webhook failed: {response.status_code} {response.text}")
        except Exception as e:
            logging.error(f"Discord send error: {e}")

    def check_daily_reset(self):
        today = datetime.utcnow().date()
        if today != self.current_date:
            # Send yesterday's report
            self.send_discord_report()
            
            # Reset daily stats
            self.stats["opps"] = 0
            self.stats["successful_trades"] = 0
            self.stats["daily_profit"] = 0.0
            
            self.current_date = today
            self.last_report_sent = False

    def load_markets(self):
        try:
            markets = self.client.get_simplified_markets()["data"]
            new_pairs = {}
            for m in markets:
                q_lower = m["question"].lower()
                if all(k in q_lower for k in Config.MARKET_KEYWORDS) and m.get("active"):
                    tokens = json.loads(m["clobTokenIds"])
                    if len(tokens) == 2:
                        new_pairs[m["question"]] = {
                            "yes_id": tokens[1],
                            "no_id": tokens[0],
                            "question": m["question"]
                        }
            self.pairs = new_pairs
            logging.info(f"Refreshed markets – found {len(self.pairs)} active 15-min targets")
        except Exception as e:
            logging.error(f"Market load failed: {e}")

    def execute_arbitrage(self, yes_id: str, no_id: str, yes_price: float, no_price: float) -> bool:
        orders = [(yes_id, yes_price), (no_id, no_price)]
        executed_id = None

        try:
            for token_id, price in orders:
                args = OrderArgs(
                    token_id=token_id,
                    price=price,
                    size=Config.SHARES_PER_TRADE,
                    side=BUY
                )
                signed = self.client.create_order(args)
                resp = self.client.post_order(signed, OrderType.FOK)

                if "error" in resp or not resp.get("success"):
                    logging.warning(f"Order failed: {resp.get('error', resp)}")
                    if executed_id:
                        self.client.cancel(executed_id)
                    return False

                executed_id = resp.get("id")
                logging.info(f"Bought {Config.SHARES_PER_TRADE} shares @ ${price:.4f}")

            combined = yes_price + no_price
            edge_per_share = 1.0 - combined - 0.02  # Conservative: subtract 2% winner fee
            profit = Config.SHARES_PER_TRADE * edge_per_share

            self.stats["daily_profit"] += profit
            self.stats["total_profit"] += profit
            cost = Config.SHARES_PER_TRADE * combined
            self.stats["invested"] += cost
            self.stats["successful_trades"] += 1

            logging.info(f"LOCKED PROFIT ${profit:.2f} | Daily: ${self.stats['daily_profit']:.2f} | Total: ${self.stats['total_profit']:.2f}")
            return True

        except Exception as e:
            logging.error(f"Execution error: {e}")
            if executed_id:
                try:
                    self.client.cancel(executed_id)
                except:
                    pass
            return False

    def run(self):
        logging.info("=== POLYMARKET ARB BOT LIVE – JAN 2026 | DAILY DISCORD ALERTS ENABLED ===")
        self.load_markets()

        while True:
            try:
                self.check_daily_reset()
                
                self.stats["scans"] += 1

                for question, info in list(self.pairs.items()):
                    yes_price = self.client.get_price(info["yes_id"], BUY)
                    no_price = self.client.get_price(info["no_id"], BUY)
                    combined = yes_price + no_price

                    if combined < Config.ARB_THRESHOLD:
                        edge = 1.0 - combined
                        self.stats["opps"] += 1
                        logging.info(f"OPPORTUNITY | {question[:60]}... | Combined ${combined:.4f} | Edge {edge:.4%}")

                        if self.execute_arbitrage(info["yes_id"], info["no_id"], yes_price, no_price):
                            logging.info(f"SUCCESS | Daily Opps: {self.stats['opps']} | Trades: {self.stats['successful_trades']} | Profit: ${self.stats['daily_profit']:.2f}")

                if self.stats["scans"] % 50 == 0:
                    self.load_markets()

                time.sleep(Config.SCAN_INTERVAL)

            except KeyboardInterrupt:
                logging.info("Bot stopped manually – sending final report")
                self.send_discord_report()
                break
            except Exception as e:
                logging.error(f"Main loop error: {e}")
                time.sleep(5)

        logging.info(f"Final Stats: {self.stats}")

if __name__ == "__main__":
    import os  # For webhook env
    bot = ArbitrageBot()
    bot.run()
