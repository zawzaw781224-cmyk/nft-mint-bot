from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

RPC_URL = os.getenv("ARC_RPC_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

print("Connected:", w3.is_connected())
print("Wallet:", WALLET_ADDRESS)

balance = w3.eth.get_balance(WALLET_ADDRESS)

print("Balance:", w3.from_wei(balance, "ether"), "USDC")

nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

print("Nonce:", nonce)

gas_price = w3.eth.gas_price

print("Gas Price:", gas_price)
print("Gas Price:", w3.from_wei(gas_price, "ether"), "USDC")

transaction = {
    "from": WALLET_ADDRESS,
    "to": WALLET_ADDRESS,
    "value": 0,
    "nonce": nonce,
    "chainId": 5042002,
}

gas = w3.eth.estimate_gas(transaction)

print("Estimated Gas:", gas)

estimated_fee = gas * gas_price

print(
    "Estimated Fee:",
    w3.from_wei(estimated_fee, "ether"),
    "USDC"
)