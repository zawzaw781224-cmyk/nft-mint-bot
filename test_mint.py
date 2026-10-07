from services.blockchain import NFTService


service = NFTService()

result = service.mint()

print(result)