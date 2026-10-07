from web3 import Web3
from dotenv import load_dotenv
import os
import json
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

RPC_URL = os.getenv("ARC_RPC_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = "0x0ED82B2916c31E2EeD6Ae3E18F7257326F1f7875"


class NFTService:

    def __init__(self):
        self.w3 = Web3(
            Web3.HTTPProvider(RPC_URL)
        )

        with open("abi.json", "r", encoding="utf-8") as f:
            abi = json.load(f)

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=abi
        )

    def get_next_token_id(self):
        return self.contract.functions.nextTokenId().call()

    def get_balance(self):
        balance = self.w3.eth.get_balance(
            WALLET_ADDRESS
        )

        return self.w3.from_wei(
            balance,
            "ether"
        )
    def get_status(self):

        return {
            "connected": self.w3.is_connected(),
            "chain_id": self.w3.eth.chain_id,
            "latest_block": self.w3.eth.block_number,
            "next_token_id": self.get_next_token_id(),
            "balance": self.get_balance(),
        }

    def health_check(self):
        try:
            # 1. RPC connection
            connected = self.w3.is_connected()

            if not connected:
                return {
                    "healthy": False,
                    "rpc": False,
                    "contract": False,
                    "wallet": False,
                    "gas": False,
                    "error": "RPC connection failed"
                }

            # 2. Chain ID
            chain_id = self.w3.eth.chain_id

            # 3. Contract check
            next_token_id = self.contract.functions.nextTokenId().call()

            # 4. Wallet balance
            balance = self.w3.eth.get_balance(
                WALLET_ADDRESS
            )

            # 5. Gas price
            gas_price = self.w3.eth.gas_price

            # Basic gas safety check
            gas_ok = balance > 0

            return {
                "healthy": (
                    connected
                    and chain_id == 5042002
                    and next_token_id > 0
                    and balance > 0
                    and gas_ok
                ),
                "rpc": connected,
                "contract": next_token_id > 0,
                "wallet": balance > 0,
                "gas": gas_ok,
                "chain_id": chain_id,
                "balance": self.w3.from_wei(
                    balance,
                    "ether"
                ),
                "gas_price": gas_price,
                "next_token_id": next_token_id,
            }

        except Exception as e:

            logger.exception(
                "Health check failed"
            )

            return {
                "healthy": False,
                "rpc": False,
                "contract": False,
                "wallet": False,
                "gas": False,
                "error": str(e)
            }
    

    def get_owner(self, token_id):
        return self.contract.functions.ownerOf(token_id).call()

    def get_transaction_status(self, tx_hash):

        try:

            # Transaction ကို ရှာ
            tx = self.w3.eth.get_transaction(tx_hash)

            # Receipt ရှိ/မရှိ စစ်
            try:

                receipt = self.w3.eth.get_transaction_receipt(
                    tx_hash
                )

            except Exception:

                # Receipt မရှိသေးရင် Pending ဖြစ်နိုင်
                return {
                    "success": True,
                    "status": "pending",
                    "tx_hash": tx_hash,
                    "from": tx["from"],
                    "to": tx["to"],
                }

            # Receipt ရပြီ
            if receipt.status == 1:

                return {
                    "success": True,
                    "status": "confirmed",
                    "tx_hash": tx_hash,
                    "block": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "from": tx["from"],
                    "to": tx["to"],
                }

            else:

                return {
                    "success": True,
                    "status": "failed",
                    "tx_hash": tx_hash,
                    "block": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "from": tx["from"],
                    "to": tx["to"],
                }

        except Exception as e:

            return {
                "success": False,
                "status": "not_found",
                "tx_hash": tx_hash,
                "error": str(e),
            }

    def check_gas_balance(self):

        try:

            balance_wei = self.w3.eth.get_balance(
                WALLET_ADDRESS
            )

            gas_price = self.w3.eth.gas_price

            # Simple transaction gas estimate
            estimated_gas = 100000

            estimated_fee = (
                gas_price * estimated_gas
            )

            return {
                "success": True,
                "balance_wei": balance_wei,
                "gas_price": gas_price,
                "estimated_gas": estimated_gas,
                "estimated_fee": estimated_fee,
                "enough": balance_wei >= estimated_fee,
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
            }

    def mint(self):

        try:

            # =========================
            # 1. Get Token ID
            # =========================

            token_id = self.get_next_token_id()

            # =========================
            # 2. Get Nonce
            # =========================

            nonce = self.w3.eth.get_transaction_count(
                WALLET_ADDRESS
            )

            # =========================
            # 3. Get Gas Price
            # =========================

            gas_price = self.w3.eth.gas_price

            # =========================
            # 4. Build Transaction
            # =========================

            transaction = self.contract.functions.mint().build_transaction({

                "from": WALLET_ADDRESS,

                "nonce": nonce,

                "chainId": self.w3.eth.chain_id,

                "gasPrice": gas_price,

            })

            # =========================
            # 5. Estimate Real Gas
            # =========================

            estimated_gas = self.w3.eth.estimate_gas(
                transaction
            )

            # =========================
            # 6. Calculate Estimated Fee
            # =========================

            estimated_fee = (
                estimated_gas * gas_price
            )

            # =========================
            # 7. Check Wallet Balance
            # =========================

            balance = self.w3.eth.get_balance(
                WALLET_ADDRESS
            )

            if balance < estimated_fee:

                return {
                    "success": False,
                    "error": (
                        "Insufficient balance for gas fee.\n"
                        f"Balance: "
                        f"{self.w3.from_wei(balance, 'ether')} USDC\n"
                        f"Estimated Fee: "
                        f"{self.w3.from_wei(estimated_fee, 'ether')} USDC"
                    ),
                }

            # =========================
            # 8. Set Estimated Gas
            # =========================

            transaction["gas"] = estimated_gas

            # =========================
            # 9. Sign Transaction
            # =========================

            signed = self.w3.eth.account.sign_transaction(
                transaction,
                PRIVATE_KEY
            )

            # =========================
            # 10. Send Transaction
            # =========================

            tx_hash = self.w3.eth.send_raw_transaction(
                signed.raw_transaction
            )

            # =========================
            # 11. Wait Confirmation
            # =========================

            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash
            )

            # =========================
            # 12. Check Result
            # =========================

            if receipt.status != 1:

                return {
                    "success": False,
                    "error": "Transaction failed",
                    "tx_hash": tx_hash.hex(),
                }

            # =========================
            # 13. Return Result
            # =========================

            return {

                "success": True,

                "token_id": token_id,

                "owner": WALLET_ADDRESS,

                "tx_hash": tx_hash.hex(),

                "status": receipt.status,

                "block": receipt.blockNumber,

                "gas_used": receipt.gasUsed,

                "estimated_gas": estimated_gas,

                "estimated_fee": (
                    self.w3.from_wei(
                        estimated_fee,
                        "ether"
                    )
                ),

            }

        except Exception as e:

            error_message = str(e).lower()

            if "insufficient" in error_message:

                error_type = "insufficient_balance"

            elif "timeout" in error_message:

                error_type = "rpc_timeout"

            elif "connection" in error_message:

                error_type = "rpc_connection"

            elif "reverted" in error_message:

                error_type = "contract_reverted"

            elif "nonce" in error_message:

                error_type = "nonce_error"

            elif "gas" in error_message:

                error_type = "gas_error"

            else:

                error_type = "unknown"
            logger.exception("Mint failed | error_type=%s",error_type)

            return {
                "success": False,
                "error_type": error_type,
                "error": str(e),
            }