import requests

url = "https://arc-testnet.drpc.org/"

payload = {
    "jsonrpc": "2.0",
    "method": "eth_chainId",
    "params": [],
    "id": 1
}

response = requests.post(url, json=payload, timeout=15)

print("HTTP Status:", response.status_code)
print("Response:", response.text)