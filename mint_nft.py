from web3 import Web3
from dotenv import load_dotenv
import os
import json

load_dotenv()

RPC_URL = os.getenv("ARC_RPC_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = "0x0ED82B2916c31E2EeD6Ae3E18F7257326F1f7875"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

print("Connected:", w3.is_connected())

# Load ABI
with open("abi.json", "r", encoding="utf-8") as f:
    ABI = json.load(f)

# Connect contract
contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=ABI
)

# Current token ID
next_token_id = contract.functions.nextTokenId().call()

print("Next Token ID:", next_token_id)

# Nonce
nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

# Build mint transaction
transaction = contract.functions.mint().build_transaction({
    "from": WALLET_ADDRESS,
    "nonce": nonce,
    "chainId": w3.eth.chain_id,
    "gasPrice": w3.eth.gas_price,
})

# Estimate gas
gas = w3.eth.estimate_gas(transaction)

print("Estimated Gas:", gas)

transaction["gas"] = gas

# Sign
signed = w3.eth.account.sign_transaction(
    transaction,
    PRIVATE_KEY
)

print("Minting NFT...")

# Send
tx_hash = w3.eth.send_raw_transaction(
    signed.raw_transaction
)

print("Transaction Hash:")
print(tx_hash.hex())

print("Waiting for confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("\nMint Successful!")
print("Status:", receipt.status)
print("Block:", receipt.blockNumber)
print("Gas Used:", receipt.gasUsed)