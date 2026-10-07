from services.blockchain import NFTService


service = NFTService()

result = service.check_gas_balance()

print(result)