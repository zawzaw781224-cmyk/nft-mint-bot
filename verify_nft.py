from web3 import Web3
from dotenv import load_dotenv
import os
import json

load_dotenv()

RPC_URL = os.getenv("ARC_RPC_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

CONTRACT_ADDRESS = "0x0ED82B2916c31E2EeD6Ae3E18F7257326F1f7875"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open("abi.json", "r", encoding="utf-8") as f:
    ABI = json.load(f)

contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=ABI
)

token_id = 4

owner = contract.functions.ownerOf(token_id).call()

print("Token ID:", token_id)
print("Owner:", owner)
print("My Wallet:", WALLET_ADDRESS)

print("\nNFT Owner Verified:", owner.lower() == WALLET_ADDRESS.lower())