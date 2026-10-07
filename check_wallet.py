from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

rpc_url = os.getenv("ARC_RPC_URL")
wallet_address = os.getenv("WALLET_ADDRESS")

w3 = Web3(Web3.HTTPProvider(rpc_url))

print("Connected:", w3.is_connected())
print("Address:", wallet_address)

balance = w3.eth.get_balance(wallet_address)

# Arc native USDC uses 18 decimals
usdc_balance = w3.from_wei(balance, "ether")

print("Native USDC Balance:", usdc_balance, "USDC")