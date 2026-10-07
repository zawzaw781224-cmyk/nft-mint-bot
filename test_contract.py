from web3 import Web3
from dotenv import load_dotenv
import os
import json

load_dotenv()

RPC_URL = os.getenv("ARC_RPC_URL")
CONTRACT_ADDRESS = "0x0ED82B2916c31E2EeD6Ae3E18F7257326F1f7875"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

print("Connected:", w3.is_connected())
print("Contract:", CONTRACT_ADDRESS)

# Load ABI
with open("abi.json", "r", encoding="utf-8") as f:
    ABI = json.load(f)

# Connect to deployed contract
contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=ABI
)

print("\nContract Name:")
print(contract.functions.name().call())

print("\nSymbol:")
print(contract.functions.symbol().call())

print("\nNext Token ID:")
print(contract.functions.nextTokenId().call())