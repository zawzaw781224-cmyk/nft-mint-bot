from services.blockchain import NFTService


service = NFTService()

tx_hash = "cefdb4c454b834c7dd5299ce8173f623210382c82b73f81072ffb6618e7ddf68"

result = service.get_transaction_status(tx_hash)

print(result)