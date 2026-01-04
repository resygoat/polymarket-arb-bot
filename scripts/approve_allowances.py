from py_clob_client.client import ClobClient
from config.config import Config

if not Config.PRIVATE_KEY:
    print("ERROR: Add your POLYMARKET_PRIVATE_KEY to config/.env first!")
    exit(1)

client = ClobClient(
    Config.HOST,
    key=Config.PRIVATE_KEY,
    chain_id=Config.CHAIN_ID,
    funder=Config.FUNDER
)

creds = client.create_or_derive_api_creds()
client.set_api_creds(creds)

print("Approving USDC spending...")
client.approve_usdc()

print("Approving conditional tokens...")
client.approve_conditional_tokens()

print("Allowances complete – you can now trade!")
