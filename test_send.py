from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

RPC_URL = os.getenv("ARC_RPC_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

print("Connected:", w3.is_connected())

balance = w3.eth.get_balance(WALLET_ADDRESS)
print("Before:", w3.from_wei(balance, "ether"), "USDC")

nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

transaction = {
    "from": WALLET_ADDRESS,
    "to": WALLET_ADDRESS,
    "value": w3.to_wei(0.001, "ether"),
    "gas": 21000,
    "gasPrice": w3.eth.gas_price,
    "nonce": nonce,
    "chainId": 5042002,
}

signed_transaction = w3.eth.account.sign_transaction(
    transaction,
    PRIVATE_KEY
)

tx_hash = w3.eth.send_raw_transaction(
    signed_transaction.raw_transaction
)

print("Transaction Hash:")
print(tx_hash.hex())

print("\nWaiting for confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("Status:", receipt.status)
print("Block:", receipt.blockNumber)
print("Gas Used:", receipt.gasUsed)