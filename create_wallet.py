from web3 import Web3

w3 = Web3()

account = w3.eth.account.create()

print("Address:")
print(account.address)

print("\nPrivate Key:")
print(account.key.hex())