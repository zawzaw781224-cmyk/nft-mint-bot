from services.blockchain import NFTService

service = NFTService()

print("Next Token ID:", service.get_next_token_id())

result = service.mint()

if result["success"]:
    print("\n✅ Mint Successful!")
    print("Transaction Hash:", result["tx_hash"])
    print("Status:", result["status"])
    print("Block:", result["block"])
    print("Gas Used:", result["gas_used"])

else:
    print("\n❌ Mint Failed!")
    print("Error:", result["error"])