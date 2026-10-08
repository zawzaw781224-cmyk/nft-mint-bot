from web3 import Web3
from dotenv import load_dotenv
import os
import json
import logging
import config.nft_config as nft_config
import threading

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

nonce_lock = threading.Lock()
class NFTService:


    


    def preflight_mint(
        self,
        quantity: int
    ):
        if quantity < 1:
            raise ValueError(
                "Quantity must be at least 1"
            )

        import config.nft_config as nft_config

        config = nft_config.load_config()

        # Contract
        contract_address = config.get(
            "contract_address"
        )

        if not contract_address:
            raise ValueError(
                "NFT Contract is not configured"
            )

        # ABI + Contract
        self.load_contract()

        # Mint function
        function_name = config.get(
            "mint_function"
        )

        if not function_name:
            raise ValueError(
                "Mint function is not configured"
            )

        function_abi = self.find_function(
            function_name
        )

        if function_abi is None:
            raise ValueError(
                f"Mint function '{function_name}' "
                "not found in ABI"
            )

        # Build transaction
        transaction = self.build_mint_transaction(
            quantity
        )

        # Balance check
        balance_check = self.check_mint_balance(
            transaction
        )

        if not balance_check["sufficient"]:
            raise ValueError(
                "Insufficient ETH balance "
                "for mint and gas"
            )

        return {
            "ready": True,
            "contract": contract_address,
            "function": function_name,
            "quantity": quantity,
            "gas_limit": transaction.get(
                "gas",
                0
            ),
            "gas_price": transaction.get(
                "gasPrice",
                0
            ),
            "mint_value": transaction.get(
                "value",
                0
            ),
            "total_required": (
                balance_check["required"]
            ),
            "balance": balance_check["balance"],
        }


    def get_mint_readiness(
        self,
        quantity: int
    ):
        import config.nft_config as nft_config

        config = nft_config.load_config()

        checks = []

        # Default values
        rpc_ok = False
        chain_id = None
        wallet_ok = False
        contract_ok = False
        abi_ok = False
        function_ok = False
        quantity_ok = False
        gas_ok = False
        balance_ok = False

        # =================================
        # 1. RPC / Wallet / Chain Health
        # =================================

        health = self.health_check()

        rpc_ok = health.get(
            "rpc",
            False
        )

        chain_id = health.get(
            "chain_id"
        )

        wallet_ok = health.get(
            "wallet",
            False
        )

        checks.append({
            "name": "RPC",
            "ok": rpc_ok
        })

        checks.append({
            "name": "Chain ID",
            "ok": chain_id == 4663,
            "value": chain_id
        })

        checks.append({
            "name": "Wallet",
            "ok": wallet_ok
        })

        # =================================
        # 2. Contract
        # =================================

        contract_address = config.get(
            "contract_address"
        )

        if contract_address:
            try:
                contract_ok = (
                    self.w3.is_address(
                        contract_address
                    )
                )

                if contract_ok:
                    code = self.w3.eth.get_code(
                        Web3.to_checksum_address(
                            contract_address
                        )
                    )

                    contract_ok = (
                        code != b""
                        and code != b"\x00"
                    )

            except Exception:
                contract_ok = False

        checks.append({
            "name": "Contract",
            "ok": contract_ok
        })

        # =================================
        # 3. ABI
        # =================================

        if contract_ok:
            try:
                self.load_contract()
                abi_ok = True
            except Exception:
                abi_ok = False

        checks.append({
            "name": "ABI",
            "ok": abi_ok
        })

        # =================================
        # 4. Mint Function
        # =================================

        function_name = config.get(
            "mint_function"
        )

        if abi_ok and function_name:
            try:
                function_abi = self.find_function(
                    function_name
                )

                function_ok = (
                    function_abi is not None
                )

            except Exception:
                function_ok = False

        checks.append({
            "name": "Mint Function",
            "ok": function_ok
        })

        # =================================
        # 5. Quantity
        # =================================

        quantity_ok = (
            isinstance(quantity, int)
            and quantity >= 1
            and quantity <= 1000
        )

        checks.append({
            "name": "Quantity",
            "ok": quantity_ok
        })

        # =================================
        # 6. Gas + Balance
        # =================================

        if all([
            rpc_ok,
            chain_id == 4663,
            wallet_ok,
            contract_ok,
            abi_ok,
            function_ok,
            quantity_ok
        ]):
            try:
                transaction = (
                    self.build_mint_transaction(
                        quantity
                    )
                )

                gas_ok = (
                    transaction.get(
                        "gas",
                        0
                    ) > 0
                )

                balance_check = (
                    self.check_mint_balance(
                        transaction
                    )
                )

                balance_ok = (
                    balance_check[
                        "sufficient"
                    ]
                )

            except Exception:
                gas_ok = False
                balance_ok = False

        checks.append({
            "name": "Gas Estimate",
            "ok": gas_ok
        })

        checks.append({
            "name": "ETH Balance",
            "ok": balance_ok
        })

        ready = all(
            check["ok"]
            for check in checks
        )
        return {
            "ready": ready,
            "checks": checks
        }

    def preview_mint(
        self,
        quantity: int
    ):
        if quantity < 1:
            raise ValueError(
                "Quantity must be at least 1"
            )

        import config.nft_config as nft_config

        config = nft_config.load_config()

        contract_address = config.get(
            "contract_address"
        )

        mint_function = config.get(
            "mint_function"
        )

        if not contract_address:
            raise ValueError(
                "NFT Contract is not configured"
            )

        if not mint_function:
            raise ValueError(
                "Mint function is not configured"
            )

        # Build transaction without
        # failing on insufficient balance
        try:
            transaction = (
                self.build_mint_transaction(
                    quantity
                )
            )

        except ValueError as e:

            error_text = str(e)

            if (
                "Insufficient ETH balance"
                not in error_text
            ):
                raise

            # Rebuild transaction manually
            # so preview can still show costs

            contract_function = (
                self.get_mint_contract_function(
                    mint_function,
                    quantity
                )
            )

            with nonce_lock:
                nonce = (
                    self.w3.eth.get_transaction_count(
                        WALLET_ADDRESS,
                        "pending"
                    )
                )

            gas_price = (
                self.w3.eth.gas_price
            )

            from decimal import Decimal

            mint_price_eth = Decimal(
                str(
                    config.get(
                        "mint_price_eth",
                        0
                    )
                )
            )

            price_mode = config.get(
                "price_mode",
                "per_transaction"
            )

            if price_mode == "per_nft":

                total_price_eth = (
                    mint_price_eth * quantity
                )

            elif price_mode == "per_transaction":

                total_price_eth = (
                    mint_price_eth
                )

            else:
                raise ValueError(
                    f"Unsupported price mode: "
                    f"{price_mode}"
                )

            value = self.w3.to_wei(
                total_price_eth,
                "ether"
            )

            transaction = (
                contract_function.build_transaction(
                    {
                        "from": WALLET_ADDRESS,
                        "nonce": nonce,
                        "value": value,
                        "gasPrice": gas_price,
                        "chainId": 4663,
                    }
                )
            )

            gas_estimate = (
                self.estimate_mint_gas(
                    transaction
                )
            )

            transaction["gas"] = int(
                gas_estimate * 1.20
            )

        gas_limit = transaction.get(
            "gas",
            0
        )

        gas_price = transaction.get(
            "gasPrice",
            0
        )

        value = transaction.get(
            "value",
            0
        )

        gas_cost = (
            gas_limit * gas_price
        )

        total_cost = (
            value + gas_cost
        )

        balance = (
            self.w3.eth.get_balance(
                WALLET_ADDRESS
            )
        )

        return {
            "contract": contract_address,
            "function": mint_function,
            "quantity": quantity,
            "mint_value_wei": value,
            "gas_limit": gas_limit,
            "gas_price_wei": gas_price,
            "gas_cost_wei": gas_cost,
            "total_cost_wei": total_cost,
            "balance_wei": balance,
            "sufficient_balance": (
                balance >= total_cost
            ),
        }


    def execute_mint(
        self,
        quantity: int
    ):
        # ==============================
        # 1. Build Transaction
        # ==============================

        try:
            transaction = (
                self.build_mint_transaction(
                    quantity
                )
            )

        except Exception as e:
            raise ValueError(
                "Transaction Build Failed: "
                f"{str(e)}"
            )

        # ==============================
        # 2. Sign Transaction
        # ==============================

        try:
            signed_transaction = (
                self.sign_mint_transaction(
                    transaction
                )
            )

        except Exception as e:
            raise ValueError(
                "Transaction Signing Failed: "
                f"{str(e)}"
            )

        # ==============================
        # 3. Broadcast Transaction
        # ==============================

        try:
            tx_hash = (
                self.send_signed_transaction(
                    signed_transaction
                )
            )

        except Exception as e:
            raise ValueError(
                "Transaction Broadcast Failed: "
                f"{str(e)}"
            )

        # ==============================
        # 4. Wait for Receipt
        # ==============================

        try:
            receipt_result = (
                self.wait_for_transaction_receipt(
                    tx_hash
                )
            )

        except Exception as e:
            return {
                "success": False,
                "stage": "receipt",
                "tx_hash": tx_hash,
                "error": (
                    "Receipt check failed: "
                    f"{str(e)}"
                ),
                "token_ids": [],
            }

        # ==============================
        # 5. Transaction Reverted
        # ==============================

        if not receipt_result["success"]:

            if receipt_result.get("confirmed"):

                return {
                    "success": False,
                    "stage": "execution",
                    "tx_hash": tx_hash,
                    "block_number": (
                        receipt_result[
                            "block_number"
                        ]
                    ),
                    "gas_used": (
                        receipt_result[
                            "gas_used"
                        ]
                    ),
                    "error": (
                        receipt_result.get(
                            "error",
                            "Transaction reverted"
                        )
                    ),
                    "token_ids": [],
                }

            return {
                "success": False,
                "stage": "confirmation",
                "tx_hash": tx_hash,
                "block_number": None,
                "gas_used": None,
                "error": (
                    receipt_result.get(
                        "error",
                        "Transaction confirmation pending"
                    )
                ),
                "token_ids": [],
            }

        # ==============================
        # 6. Read Token IDs
        # ==============================

        try:
            receipt = (
                self.w3.eth.get_transaction_receipt(
                    tx_hash
                )
            )
            logger.info(
                "Transaction confirmation result | "
                "tx_hash=%s | success=%s | confirmed=%s | stage=%s",
                tx_hash,
                receipt_result.get("success"),
                receipt_result.get("confirmed"),
                (
                    "confirmed"
                    if receipt_result.get("confirmed")
                    else "pending"
                )
            )

            token_ids = (
                self.get_minted_token_ids(
                    receipt
                )
            )

        except Exception as e:
            return {
                "success": True,
                "stage": "token_id",
                "tx_hash": tx_hash,
                "block_number": (
                    receipt_result[
                        "block_number"
                    ]
                ),
                "gas_used": (
                    receipt_result[
                        "gas_used"
                    ]
                ),
                "error": (
                    "Mint succeeded, but "
                    "Token ID could not be read: "
                    f"{str(e)}"
                ),
                "token_ids": [],
            }

        # ==============================
        # 7. Success
        # ==============================
        logger.info(
            "Mint confirmed | "
            "tx_hash=%s | block=%s | gas_used=%s",
            tx_hash,
            receipt_result.get(
                "block_number"
            ),
            receipt_result.get(
                "gas_used"
            )
        )

        return {
            "success": True,
            "stage": "completed",
            "tx_hash": tx_hash,
            "block_number": (
                receipt_result[
                    "block_number"
                ]
            ),
            "gas_used": (
                receipt_result[
                    "gas_used"
                ]
            ),
            "token_ids": token_ids,
        }
    def get_minted_token_ids(
        self,
        receipt
    ):
        if self.contract is None:
            self.load_contract()

        token_ids = []

        try:
            transfer_event = (
                self.contract.events.Transfer()
            )

            events = (
                transfer_event.process_receipt(
                    receipt
                )
            )

            for event in events:
                args = event["args"]

                token_id = args.get(
                    "tokenId"
                )

                if token_id is not None:
                    token_ids.append(
                        int(token_id)
                    )

            return token_ids

        except Exception as e:
            raise ValueError(
                "Failed to read NFT Transfer events: "
                f"{str(e)}"
            )

    def wait_for_transaction_receipt(
        self,
        tx_hash: str,
        timeout: int = 120
    ):
        try:
            receipt = (
                self.w3.eth.wait_for_transaction_receipt(
                    tx_hash,
                    timeout=timeout
                )
            )

            block_number = receipt.get(
                "blockNumber"
            )

            gas_used = receipt.get(
                "gasUsed"
            )

            status = receipt.get(
                "status"
            )

            # Transaction succeeded
            if status == 1:
                return {
                    "success": True,
                    "confirmed": True,
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                    "gas_used": gas_used,
                    "error": None,
                }

            # Transaction reverted
            return {
                "success": False,
                "confirmed": True,
                "tx_hash": tx_hash,
                "block_number": block_number,
                "gas_used": gas_used,
                "error": "Transaction reverted",
            }

        except Exception as e:
            error_text = str(e)

            # Receipt timeout / confirmation pending
            if "timeout" in error_text.lower():
                return {
                    "success": False,
                    "confirmed": False,
                    "tx_hash": tx_hash,
                    "block_number": None,
                    "gas_used": None,
                    "error": (
                        "Transaction broadcasted, "
                        "but confirmation is still pending"
                    ),
                }

            # Other receipt/RPC error
            return {
                "success": False,
                "confirmed": False,
                "tx_hash": tx_hash,
                "block_number": None,
                "gas_used": None,
                "error": (
                    "Receipt check failed: "
                    f"{error_text}"
                ),
            }

    def send_signed_transaction(
        self,
        signed_transaction
    ):
        try:
            tx_hash = self.w3.eth.send_raw_transaction(
                signed_transaction.raw_transaction
            )

            return tx_hash.hex()

        except Exception as e:
            raise ValueError(
                f"Transaction send failed: {str(e)}"
            )

    def sign_mint_transaction(
        self,
        transaction: dict
    ):
        try:
            signed_transaction = (
                self.w3.eth.account.sign_transaction(
                    transaction,
                    private_key=PRIVATE_KEY
                )
            )

            return signed_transaction

        except Exception as e:
            raise ValueError(
                f"Transaction signing failed: {str(e)}"
            )


    def check_mint_balance(
        self,
        transaction: dict
    ):
        balance = self.w3.eth.get_balance(
            WALLET_ADDRESS
        )

        gas_limit = transaction.get(
            "gas",
            0
        )

        gas_price = transaction.get(
            "gasPrice",
            0
        )

        value = transaction.get(
            "value",
            0
        )

        gas_cost = (
            gas_limit * gas_price
        )

        total_required = (
            value + gas_cost
        )

        if balance < total_required:
            return {
                "sufficient": False,
                "balance": balance,
                "required": total_required,
                "gas_cost": gas_cost,
                "mint_value": value,
            }

        return {
            "sufficient": True,
            "balance": balance,
            "required": total_required,
            "gas_cost": gas_cost,
            "mint_value": value,
        }

    def estimate_mint_gas(
        self,
        transaction: dict
    ):
        try:
            gas_estimate = (
                self.w3.eth.estimate_gas(
                    transaction
                )
            )

            return gas_estimate

        except Exception as e:
            raise ValueError(
                "Gas estimation failed: "
                f"{str(e)}"
            )

    def build_mint_transaction(
        self,
        quantity: int
    ):
        import config.nft_config as nft_config

        config = nft_config.load_config()

        function_name = config.get(
            "mint_function"
        )

        if not function_name:
            raise ValueError(
                "Mint function is not configured"
            )

        # Get dynamic contract function
        contract_function = (
            self.get_mint_contract_function(
                function_name,
                quantity
            )
        )

        # Get wallet nonce
        with nonce_lock:
            nonce = self.w3.eth.get_transaction_count(
                WALLET_ADDRESS,
                "pending"
            )

        # Get current gas price
        gas_price = self.w3.eth.gas_price

        # Mint price → Wei
        from decimal import Decimal

        mint_price_eth = Decimal(
            str(
                config.get(
                    "mint_price_eth",
                    0
                )
            )
        )

        price_mode = config.get(
            "price_mode",
            "per_transaction"
        )

        if price_mode == "per_nft":
            total_price_eth = (
                mint_price_eth * quantity
            )

        elif price_mode == "per_transaction":
            total_price_eth = (
                mint_price_eth
            )

        else:
            raise ValueError(
                f"Unsupported price mode: "
                f"{price_mode}"
            )

        value = self.w3.to_wei(
            total_price_eth,
            "ether"
        )

        transaction = (
            contract_function.build_transaction(
                {
                    "from": WALLET_ADDRESS,
                    "nonce": nonce,
                    "value": value,
                    "gasPrice": gas_price,
                    "chainId": 4663,
                }
            )
        )

        gas_estimate = self.estimate_mint_gas(
            transaction
        )

        # Small safety margin
        gas_limit = int(
            gas_estimate * 1.20
        )

        transaction["gas"] = gas_limit
        balance_check = self.check_mint_balance(
            transaction
        )

        if not balance_check["sufficient"]:
            raise ValueError(
                "Insufficient ETH balance for mint "
                "and gas"
            )

        return transaction

    def get_mint_contract_function(
        self,
        function_name: str,
        quantity: int
    ):
        if self.contract is None:
            self.load_contract()

        function_abi = self.find_function(
            function_name
        )

        if function_abi is None:
            raise ValueError(
                f"Mint function '{function_name}' "
                "not found in ABI"
            )

        arguments = self.build_mint_arguments(
            function_abi,
            quantity
        )

        try:
            contract_function = getattr(
                self.contract.functions,
                function_name
            )

        except AttributeError:
            raise ValueError(
                f"Contract function "
                f"'{function_name}' not found"
            )

        return contract_function(
            *arguments
        )


    def build_mint_arguments(
        self,
        function_abi: dict,
        quantity: int
    ):
        inputs = function_abi.get(
            "inputs",
            []
        )

        arguments = []

        quantity_names = {
            "quantity",
            "amount",
            "count",
            "qty",
        }

        recipient_names = {
            "to",
            "recipient",
            "minter",
            "buyer",
        }

        for item in inputs:
            input_name = item.get(
                "name",
                ""
            ).strip().lower()

            input_type = item.get(
                "type",
                ""
            ).lower()

            # Quantity parameter
            if (
                input_type.startswith("uint")
                and input_name in quantity_names
            ):
                arguments.append(quantity)
                continue

            # Recipient / minter address
            if (
                input_type == "address"
                and input_name in recipient_names
            ):
                arguments.append(
                    WALLET_ADDRESS
                )
                continue

            # Unknown / unsupported argument
            raise ValueError(
                "Unsupported mint argument: "
                f"{item.get('name', '')} "
                f"({item.get('type', '')})"
            )

        return arguments

    def get_mint_function_info(
        self,
        function_name: str
    ):
        function_abi = self.find_function(
            function_name
        )

        if function_abi is None:
            raise ValueError(
                f"Function '{function_name}' "
                "not found in ABI"
            )

        inputs = function_abi.get(
            "inputs",
            []
        )

        return {
            "name": function_abi.get(
                "name"
            ),
            "inputs": inputs,
            "input_count": len(inputs),
        }

    def __init__(self):
        self.w3 = Web3(
            Web3.HTTPProvider(RPC_URL)
        )

        self.contract = None

    def set_contract(
        self,
        contract_address: str,
        abi: list
    ):
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(
                contract_address
            ),
            abi=abi
        )
    def find_function(self, function_name: str):
        if self.contract is None:
            self.load_contract()

        for item in self.contract.abi:
            if item.get("type") != "function":
                continue

            if item.get("name") == function_name:
                return item

        return None

    def detect_mint_functions(self):
        config = nft_config.load_config()

        abi_file = "config/nft_abi.json"

        with open(abi_file, "r", encoding="utf-8") as f:
            abi = json.load(f)

        if not abi:
            raise ValueError("NFT ABI is not configured")

        candidates = []

        mint_keywords = [
            "mint",
            "publicmint",
            "freemint",
            "premint",
            "claim",
            "publicsale",
            "presale"
        ]

        quantity_keywords = [
            "quantity",
            "amount",
            "count",
            "qty"
        ]

        address_keywords = [
            "to",
            "recipient",
            "minter",
            "buyer"
        ]

        for item in abi:

            if item.get("type") != "function":
                continue

            name = item.get("name", "")
            name_lower = name.lower()

            inputs = item.get("inputs", [])
            state_mutability = item.get("stateMutability", "")

            score = 0
            reasons = []

            if name_lower in mint_keywords:
                score += 5
                reasons.append("mint-like function name")

            elif "mint" in name_lower:
                score += 4
                reasons.append("contains 'mint'")

            elif "claim" in name_lower:
                score += 3
                reasons.append("claim-like function name")

            if state_mutability == "payable":
                score += 3
                reasons.append("payable")

            for input_item in inputs:

                input_name = input_item.get("name", "").lower()
                input_type = input_item.get("type", "")

                if input_name in quantity_keywords:
                    if input_type.startswith("uint"):
                        score += 3
                        reasons.append("quantity parameter")

                if input_name in address_keywords:
                    if input_type == "address":
                        score += 1
                        reasons.append("address parameter")

            if score >= 3:
                candidates.append({
                    "name": name,
                    "inputs": inputs,
                    "stateMutability": state_mutability,
                    "score": score,
                    "reasons": reasons
                })

        candidates.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return candidates
    def load_contract(self):
        config = nft_config.load_config()

        contract_address = config.get(
            "contract_address"
        )

        if not contract_address:
            raise ValueError(
                "NFT Contract Address is not configured"
            )

        abi_file = (
            "config/nft_abi.json"
        )

        with open(
            abi_file,
            "r",
            encoding="utf-8"
        ) as f:
            abi = json.load(f)

        if not abi:
            raise ValueError(
                "NFT ABI is not configured"
            )

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(
                contract_address
            ),
            abi=abi
        )

        return self.contract

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
                    "wallet": False,
                    "gas": False,
                    "chain_id": None,
                    "balance": 0,
                    "error": "RPC connection failed"
                }

            # 2. Chain ID
            chain_id = self.w3.eth.chain_id

            if chain_id != 4663:
                return {
                    "healthy": False,
                    "rpc": True,
                    "wallet": False,
                    "gas": False,
                    "chain_id": chain_id,
                    "balance": 0,
                    "error": (
                        f"Wrong network. "
                        f"Expected 4663, got {chain_id}"
                    )
                }

            # 3. Wallet check
            wallet_ok = self.w3.is_address(
                WALLET_ADDRESS
            )

            # 4. ETH balance
            balance = self.w3.eth.get_balance(
                WALLET_ADDRESS
            )

            balance_eth = self.w3.from_wei(
                balance,
                "ether"
            )

            # 5. Gas check
            gas_ok = balance > 0

            return {
                "healthy": (
                    connected
                    and chain_id == 4663
                    and wallet_ok
                    and gas_ok
                ),
                "rpc": connected,
                "wallet": wallet_ok,
                "gas": gas_ok,
                "chain_id": chain_id,
                "balance": balance_eth,
            }

        except Exception as e:

            logger.exception(
                "Health check failed"
            )

            return {
                "healthy": False,
                "rpc": False,
                "wallet": False,
                "gas": False,
                "chain_id": None,
                "balance": 0,
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

    def mint(
        self,
        quantity: int = 1
    ):
        try:
            return self.execute_mint(
                quantity
            )

        except Exception as e:

            logger.exception(
                "Mint execution failed"
            )

            return {
                "success": False,
                "stage": "mint",
                "tx_hash": None,
                "error": str(e),
                "token_ids": [],
            }