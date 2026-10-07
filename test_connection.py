from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

rpc_url = os.getenv("ARC_RPC_URL")

w3 = Web3(
    Web3.HTTPProvider(
        rpc_url,
        request_kwargs={"timeout": 15}
    )
)

print("RPC:", rpc_url)
print("Connected:", w3.is_connected())

if w3.is_connected():
    print("Chain ID:", w3.eth.chain_id)
    print("Latest Block:", w3.eth.block_number)