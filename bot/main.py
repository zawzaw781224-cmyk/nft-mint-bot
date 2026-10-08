from telegram import Update
from decimal import Decimal, InvalidOperation
import asyncio
from services.blockchain import NFTService
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from dotenv import load_dotenv
import os
import config.nft_config as nft_config
from web3 import Web3
import json


load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = {
    int(user_id.strip())
    for user_id in os.getenv(
        "TELEGRAM_ADMIN_IDS",
        ""
    ).split(",")
    if user_id.strip()
}
mint_lock = asyncio.Lock()
auto_mint_stop_event = asyncio.Event()
auto_mint_task = None




async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        "🆔 Your Telegram ID\n\n"
        f"{user_id}"
    )

async def stop(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):
        await update.message.reply_text(
            "⛔️ Access Denied!\n\n"
            "ဒီ Bot ကို အသုံးပြုခွင့် မရှိပါ။"
        )
        return

    if not auto_mint_stop_event.is_set():

        auto_mint_stop_event.set()

        await update.message.reply_text(
            "🛑 Auto Mint Stop Request ပို့ပြီးပါပြီ။\n\n"
            "လက်ရှိ NFT transaction ပြီးသွားရင် "
            "Auto Mint ရပ်ပါမယ်။"
        )

    else:

        await update.message.reply_text(
            "ℹ️ Auto Mint Stop Request ရှိပြီးသားပါ။"
        )
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 NFT Mint Bot မှ ကြိုဆိုပါတယ်!\n\n"

        "🚀 Mint\n"
        "🪙 /auto_mint <quantity> - NFT Mint စတင်ရန်\n"
        "🛑 /stop - Auto Mint ရပ်ရန်\n\n"

        "📊 Bot Status\n"
        "📊 /status - NFT Bot Status စစ်ရန်\n"
        "🏥 /health - RPC / Wallet / Gas စစ်ရန်\n"
        "💰 /balance - Wallet Balance စစ်ရန်\n"
        "🔎 /tx - Transaction Status စစ်ရန်\n"
        "🆔 /myid - Telegram ID ကြည့်ရန်\n\n"

        "⚙️ NFT Configuration\n"
        "📄 /config - လက်ရှိ NFT Configuration ကြည့်ရန်\n"
        "📄 /set_contract <address> - NFT Contract သတ်မှတ်ရန်\n"
        "📤 ABI JSON File - ဒီ Chat ထဲ Upload လုပ်ရန်\n"
        "🔧 /set_mint_function <name> - Mint Function သတ်မှတ်ရန်\n"
        "💰 /set_price <price> <mode> - Mint Price သတ်မှတ်ရန်\n"
        "📦 /set_quantity <number> - Mint Quantity သတ်မှတ်ရန်\n\n"

        "🔍 Mint Preparation\n"
        "📋 /preview_mint <quantity> - Mint မလုပ်ခင် စစ်ဆေးရန်\n"
        "🚀 /ready - Mint လုပ်ရန် အဆင်သင့်ဖြစ်/မဖြစ် စစ်ရန်\n"
        
    )
def is_admin(update: Update) -> bool:
    return update.effective_user.id in ADMIN_IDS
from functools import wraps


def admin_only(func):

    @wraps(func)
    async def wrapper(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        if not is_admin(update):
            await update.message.reply_text(
                "⛔️ Access Denied!\n\n"
                "ဒီ Bot ကို အသုံးပြုခွင့် မရှိပါ။"
            )
            return

        return await func(update, context)

    return wrapper

async def run_auto_mint(
    update: Update,
    quantity: int
):
    async with mint_lock:
        service = NFTService()

        readiness = service.get_mint_readiness(
            quantity
        )

        if not readiness["ready"]:

            failed_checks = []

            for check in readiness["checks"]:

                if not check["ok"]:
                    failed_checks.append(
                        f"🔴 {check['name']}"
                    )

            failed_text = "\n".join(
                failed_checks
            )

            await update.message.reply_text(
                "🔴 Mint NOT READY\n\n"
                "Auto Mint မစတင်ပါ။\n\n"
                "Failed Checks:\n"
                f"{failed_text}\n\n"
                "/ready နဲ့ ပြန်စစ်ပါ။"
            )

            return
        actual_quantity = quantity
        success_count = 0
        failed_count = 0
        minted_tokens = []

        await update.message.reply_text(
            "🚀 Auto Mint Engine Started!\n\n"
            f"🎯 Target: {actual_quantity} NFTs\n"
            "⏳ တစ်ခုချင်းစီ mint လုပ်နေပါတယ်..."
        )

        # Auto Mint Loop
        for i in range(actual_quantity):

            # Stop Request စစ်မယ်
            if auto_mint_stop_event.is_set():

                await update.message.reply_text(
                    "🛑 Auto Mint ရပ်လိုက်ပါပြီ။\n\n"
                    f"🎯 Target: {actual_quantity}\n"
                    f"✅ Success: {success_count}\n"
                    f"❌ Failed: {failed_count}"
                )

                return

            # Mint One NFT
            result = await asyncio.to_thread(
                service.mint,
                1
            )

            if result["success"]:

                success_count += 1

                token_ids = result.get(
                    "token_ids",
                    []
                )

                if token_ids:

                    minted_tokens.extend(
                        token_ids
                    )

                    token_text = ", ".join(
                        f"#{token_id}"
                        for token_id in token_ids
                    )

                else:

                    token_text = (
                        "Token ID မဖတ်နိုင်ပါ"
                    )

                await update.message.reply_text(
                    "✅ NFT Mint Success!\n\n"
                    f"📦 Progress: "
                    f"{success_count}/{actual_quantity}\n"
                    f"🎨 Token ID: {token_text}\n"
                    f"⛽️ Gas Used: {result['gas_used']}\n"
                    f"🔗 TX:\n{result['tx_hash']}"
                )

            else:

                failed_count += 1

                stage = result.get(
                    "stage",
                    "unknown"
                )

                tx_hash = result.get(
                    "tx_hash"
                )

                error = result.get(
                    "error",
                    "Unknown error"
                )

                if stage == "confirmation":

                    tx_text = (
                        tx_hash
                        if tx_hash
                        else "TX Hash မရရှိသေးပါ"
                    )

                    await update.message.reply_text(
                        "🟡 Mint Confirmation Pending!\n\n"
                        f"📦 Progress: "
                        f"{success_count}/{actual_quantity}\n"
                        f"❌ Failed: {failed_count}\n\n"
                        f"🔗 TX:\n{tx_text}\n\n"
                        f"ℹ️ {error}\n\n"
                        "⚠️ Transaction ကို "
                        "ပြန်မပို့ဘဲ Auto Mint ရပ်လိုက်ပါပြီ။"
                    )

                else:

                    tx_text = (
                        tx_hash
                        if tx_hash
                        else "TX Hash မရှိပါ"
                    )

                    await update.message.reply_text(
                        "❌ NFT Mint Failed!\n\n"
                        f"📦 Progress: "
                        f"{success_count}/{actual_quantity}\n"
                        f"❌ Failed: {failed_count}\n\n"
                        f"📍 Stage: {stage}\n"
                        f"❌ Error: {error}\n\n"
                        f"🔗 TX:\n{tx_text}\n\n"
                        "🛑 Auto Mint ရပ်လိုက်ပါပြီ။"
                    )

                return

        await update.message.reply_text(
            "🏁 Auto Mint Completed!\n\n"
            f"🎯 Target: {actual_quantity}\n"
            f"✅ Success: {success_count}\n"
            f"❌ Failed: {failed_count}\n\n"
            f"🎨 Minted Token IDs: "
            f"{', '.join(f'#{token_id}' for token_id in minted_tokens) if minted_tokens else 'None'}"
        )


@admin_only
async def auto_mint_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:
        await update.message.reply_text(
            "❌ Quantity ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/auto_mint 10"
        )
        return

    try:
        quantity = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Quantity က number ဖြစ်ရပါမယ်။\n\n"
            "ဥပမာ:\n"
            "/auto_mint 10"
        )
        return

    if quantity < 1:
        await update.message.reply_text(
            "❌ Quantity က 1 ထက်ငယ်လို့မရပါ။"
        )
        return

    if quantity > 1000:
        await update.message.reply_text(
            "❌ တစ်ကြိမ်မှာ အများဆုံး 1000 NFTs ပဲ mint လုပ်နိုင်ပါတယ်။"
        )
        return

    # =================================
    # Preflight Check
    # =================================

    try:
        service = NFTService()

        readiness = service.get_mint_readiness(
            quantity
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Mint Preflight Failed!\n\n"
            f"Error: {str(e)}"
        )
        return

    if not readiness["ready"]:
        failed_checks = []

        for check in readiness["checks"]:
            if not check["ok"]:
                failed_checks.append(
                    f"🔴 {check['name']}"
                )

        failed_text = "\n".join(
            failed_checks
        )

        await update.message.reply_text(
            "🔴 Mint NOT READY\n\n"
            "Auto Mint မစတင်ပါ။\n\n"
            "Failed Checks:\n"
            f"{failed_text}\n\n"
            "အရင် configuration / "
            "wallet / contract / gas ကို ပြင်ပြီး\n"
            "/ready နဲ့ ပြန်စစ်ပါ။"
        )

        return

    global auto_mint_task

    if auto_mint_task is not None and not auto_mint_task.done():
        await update.message.reply_text(
            "⏳ Auto Mint တစ်ခု လုပ်နေဆဲပါ။\n\n"
            "လက်ရှိ Auto Mint ပြီးမှ ပြန်စမ်းပါ။"
        )
        return

    auto_mint_stop_event.clear()

    auto_mint_task = asyncio.create_task(
        run_auto_mint(update, quantity)
    )

    await update.message.reply_text(
        "🚀 Auto Mint ကို Background မှာ စတင်လိုက်ပါပြီ။\n\n"
        f"🎯 Requested: {quantity} NFTs"
    )

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        import config.nft_config as nft_config

        config = nft_config.load_config()

        contract_address = config.get(
            "contract_address"
        )

        mint_function = config.get(
            "mint_function"
        )

        if contract_address:
            contract_text = (
                "🟢 Configured\n"
                f"{contract_address}"
            )
        else:
            contract_text = (
                "🔴 Not configured"
            )

        if mint_function:
            function_text = (
                f"🟢 {mint_function}"
            )
        else:
            function_text = (
                "🔴 Not configured"
            )

        if (
            contract_address
            and mint_function
        ):
            nft_status = "🟡 CONFIGURED"
        else:
            nft_status = "🔴 NOT READY"

        await update.message.reply_text(
            "📊 NFT Mint Bot Status\n\n"
            f"📊 NFT Status: {nft_status}\n\n"
            f"📄 Contract:\n"
            f"{contract_text}\n\n"
            f"🔧 Mint Function:\n"
            f"{function_text}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Status Check Failed!\n\n"
            f"Error: {str(e)}"
        )
@admin_only
async def ready_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        import config.nft_config as nft_config

        config = nft_config.load_config()

        quantity = int(
            config.get(
                "mint_quantity",
                1
            )
        )

        service = NFTService()

        result = service.get_mint_readiness(
            quantity
        )

        lines = [
            "🚀 NFT Mint Readiness",
            ""
        ]

        for check in result["checks"]:
            status = (
                "🟢"
                if check["ok"]
                else "🔴"
            )

            name = check["name"]

            value = check.get(
                "value"
            )

            if value is not None:
                lines.append(
                    f"{status} {name}: {value}"
                )
            else:
                lines.append(
                    f"{status} {name}"
                )

        lines.append("")

        if result["ready"]:
            lines.append(
                "🟢 READY TO MINT"
            )
        else:
            lines.append(
                "🔴 NOT READY"
            )

        await update.message.reply_text(
            "\n".join(lines)
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Readiness Check Failed!\n\n"
            f"Error: {str(e)}"
        )
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    service = NFTService()

    balance = service.get_balance()

    await update.message.reply_text(
        "💰 Bot Wallet Balance\n\n"
        f"💵 {balance:.6f} ETH"
    )

@admin_only
async def config(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    import config.nft_config as nft_config
    import json
    import os

    nft = nft_config.load_config()

    contract = nft.get(
        "contract_address"
    )

    mint_function = nft.get(
        "mint_function"
    )

    mint_price = nft.get(
        "mint_price_eth",
        0
    )

    quantity = nft.get(
        "mint_quantity",
        1
    )

    # ABI status
    abi_ready = False
    abi_entries = 0

    abi_path = "config/nft_abi.json"

    if os.path.exists(abi_path):
        try:
            with open(
                abi_path,
                "r",
                encoding="utf-8"
            ) as f:
                abi = json.load(f)

            if isinstance(abi, list) and abi:
                abi_ready = True
                abi_entries = len(abi)

        except Exception:
            abi_ready = False

    # Status
    contract_ready = bool(contract)
    function_ready = bool(mint_function)

    price_ready = (
        isinstance(mint_price, (int, float))
        and mint_price >= 0
    )

    quantity_ready = (
        isinstance(quantity, int)
        and quantity >= 1
    )

    ready = (
        contract_ready
        and abi_ready
        and function_ready
        and price_ready
        and quantity_ready
    )

    status = (
        "🟢 READY"
        if ready
        else "🟡 NOT READY"
    )
    price_status = (
        "🟢 OK"
        if price_ready
        else "🔴 INVALID"
    )

    quantity_status = (
        "🟢 OK"
        if quantity_ready
        else "🔴 INVALID"
    )

    contract_text = (
        contract
        if contract
        else "❌ Not configured"
    )

    function_text = (
        mint_function
        if mint_function
        else "❌ Not configured"
    )

    abi_text = (
        f"🟢 Configured ({abi_entries} entries)"
        if abi_ready
        else "❌ Not configured"
    )

    await update.message.reply_text(
        "⚙️ NFT Mint Configuration\n\n"
        f"📊 Status: {status}\n\n"
        f"📄 Contract:\n"
        f"{contract_text}\n\n"
        f"🔧 Mint Function:\n"
        f"{function_text}\n\n"
        f"📚 ABI:\n"
        f"{abi_text}\n\n"
        f"💰 Mint Price:\n"
        f"{mint_price} ETH\n\n"
        f"📊 Price Mode:\n"
        f"{nft.get('price_mode', 'per_transaction')}\n\n"
        f"📦 Quantity:\n"
        f"{quantity} ({quantity_status})"
    )

@admin_only
async def set_contract(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "❌ Contract Address ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/set_contract 0x..."
        )
        return

    contract_address = context.args[0].strip()

    service = NFTService()

    # 1. Address format check
    if not service.w3.is_address(contract_address):
        await update.message.reply_text(
            "❌ Invalid Contract Address!\n\n"
            "Ethereum-style address မှန်ကန်တဲ့ format ဖြစ်ရပါမယ်။"
        )
        return

    # 2. Checksum address
    contract_address = Web3.to_checksum_address(
        contract_address
    )

    try:
        # 3. Check Robinhood Chain
        chain_id = service.w3.eth.chain_id

        if chain_id != 4663:
            await update.message.reply_text(
                "❌ Wrong Network!\n\n"
                f"Current Chain ID: {chain_id}\n"
                "Expected Chain ID: 4663"
            )
            return

        # 4. Check contract code
        code = service.w3.eth.get_code(
            contract_address
        )

        if code == b"" or code == b"\x00":
            await update.message.reply_text(
                "❌ Contract မတွေ့ပါ။\n\n"
                "ဒီ Address မှာ Smart Contract code "
                "မရှိပါ။"
            )
            return

        # 5. Save persistent config
        config = nft_config.load_config()

        config["contract_address"] = contract_address

        nft_config.save_config(config)

        await update.message.reply_text(
            "✅ NFT Contract Set Successfully!\n\n"
            f"📄 Contract:\n{contract_address}\n\n"
            f"⛓️ Chain ID: {chain_id}\n"
            "🟢 Smart Contract detected"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Contract Check Failed!\n\n"
            f"Error: {str(e)}"
        )

@admin_only
async def set_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Price နဲ့ Price Mode ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/set_price 0.001 per_nft\n\n"
            "သို့မဟုတ်\n"
            "/set_price 0.001 per_transaction"
        )
        return

    try:
        price = Decimal(
            context.args[0].strip()
        )

    except InvalidOperation:
        await update.message.reply_text(
            "❌ Price က valid number ဖြစ်ရပါမယ်။\n\n"
            "ဥပမာ:\n"
            "0.001"
        )
        return

    if price < 0:
        await update.message.reply_text(
            "❌ Price က 0 ထက်ငယ်လို့ မရပါ။"
        )
        return

    price_mode = (
        context.args[1]
        .strip()
        .lower()
    )

    allowed_modes = {
        "per_nft",
        "per_transaction"
    }

    if price_mode not in allowed_modes:
        await update.message.reply_text(
            "❌ Invalid Price Mode!\n\n"
            "အသုံးပြုနိုင်တာ:\n"
            "• per_nft\n"
            "• per_transaction"
        )
        return

    try:
        import config.nft_config as nft_config

        config = nft_config.load_config()

        config["mint_price_eth"] = str(price)
        config["price_mode"] = price_mode

        nft_config.save_config(
            config
        )

        await update.message.reply_text(
            "✅ Mint Price Updated!\n\n"
            f"💰 Price: {price} ETH\n"
            f"📊 Mode: {price_mode}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Price Update Failed!\n\n"
            f"Error: {str(e)}"
        )

@admin_only
async def handle_abi_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    document = update.message.document

    if not document:
        return

    file_name = document.file_name or ""

    if not file_name.lower().endswith(".json"):
        await update.message.reply_text(
            "❌ ABI JSON file ပဲ လက်ခံပါတယ်။"
        )
        return

    temp_path = "config/nft_abi_temp.json"

    try:
        file = await document.get_file()

        await file.download_to_drive(
            temp_path
        )

        # Validate JSON
        with open(
            temp_path,
            "r",
            encoding="utf-8"
        ) as f:
            abi = json.load(f)

        if not isinstance(abi, list):
            raise ValueError(
                "ABI must be a JSON array"
            )

        if not abi:
            raise ValueError(
                "ABI is empty"
            )

        # Validate ABI entries
        valid_entries = []

        for item in abi:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")

            if item_type in {
                "function",
                "event",
                "constructor",
                "fallback",
                "receive"
            }:
                valid_entries.append(item)

        if not valid_entries:
            raise ValueError(
                "ABI does not contain valid entries"
            )

        # Count functions and events
        function_count = sum(
            1
            for item in valid_entries
            if item.get("type") == "function"
        )

        event_count = sum(
            1
            for item in valid_entries
            if item.get("type") == "event"
        )

        # Save validated ABI
        with open(
            "config/nft_abi.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                valid_entries,
                f,
                indent=4
            )

        await update.message.reply_text(
            "✅ NFT ABI Uploaded Successfully!\n\n"
            f"📄 File: {file_name}\n"
            f"🔧 Functions: {function_count}\n"
            f"📡 Events: {event_count}\n"
            f"📚 Total Entries: "
            f"{len(valid_entries)}"
        )

    except json.JSONDecodeError:
        await update.message.reply_text(
            "❌ Invalid JSON file!\n\n"
            "ABI file က valid JSON "
            "မဟုတ်ပါ။"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ ABI Upload Failed!\n\n"
            f"Error: {str(e)}"
        )

    finally:
        # Always remove temporary file
        import os

        if os.path.exists(temp_path):
            os.remove(temp_path)


@admin_only
async def handle_abi_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    text = text.strip()

    # JSON ABI must start with [
    # and end with ]
    if not (
        text.startswith("[")
        and text.endswith("]")
    ):
        return

    try:
        abi = json.loads(text)

        if not isinstance(abi, list):
            raise ValueError(
                "ABI must be a JSON array"
            )

        if not abi:
            raise ValueError(
                "ABI is empty"
            )

        valid_entries = []

        for item in abi:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")

            if item_type in {
                "function",
                "event",
                "constructor",
                "fallback",
                "receive"
            }:
                valid_entries.append(item)

        if not valid_entries:
            raise ValueError(
                "ABI does not contain valid entries"
            )

        function_count = sum(
            1
            for item in valid_entries
            if item.get("type") == "function"
        )

        event_count = sum(
            1
            for item in valid_entries
            if item.get("type") == "event"
        )

        with open(
            "config/nft_abi.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                valid_entries,
                f,
                indent=4
            )

        await update.message.reply_text(
            "✅ NFT ABI Updated Successfully!\n\n"
            f"🔧 Functions: {function_count}\n"
            f"📡 Events: {event_count}\n"
            f"📚 Total Entries: "
            f"{len(valid_entries)}"
        )

    except json.JSONDecodeError:
        await update.message.reply_text(
            "❌ Invalid JSON!\n\n"
            "ABI JSON format မှားနေပါတယ်။"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ ABI Update Failed!\n\n"
            f"Error: {str(e)}"
        )
@admin_only
async def set_mint_function(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "❌ Mint Function ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/set_mint_function mint\n\n"
            "သို့မဟုတ်\n"
            "/set_mint_function publicMint"
        )
        return

    mint_function = context.args[0].strip()

    if not mint_function:
        await update.message.reply_text(
            "❌ Mint Function မဖြစ်မနေ ထည့်ရပါမယ်။"
        )
        return

    # Basic validation
    if not mint_function.replace("_", "").isalnum():
        await update.message.reply_text(
            "❌ Invalid function name!"
        )
        return

    try:
        import config.nft_config as nft_config

        # Load saved NFT configuration
        config = nft_config.load_config()

        # Create blockchain service
        service = NFTService()

        # Load configured NFT contract
        contract_address = config.get(
            "contract_address"
        )

        if not contract_address:
            await update.message.reply_text(
                "❌ NFT Contract မသတ်မှတ်ရသေးပါ။\n\n"
                "အရင်ဆုံး:\n"
                "/set_contract <address>\n\n"
                "လုပ်ပေးပါ။"
            )
            return

        if not service.w3.is_address(
            contract_address
        ):
            await update.message.reply_text(
                "❌ Configured Contract Address "
                "မမှန်ပါ။"
            )
            return

        service.load_contract()

        # Find function inside ABI
        function_abi = service.find_function(
            mint_function
        )

        if function_abi is None:
            await update.message.reply_text(
                "❌ Mint Function မတွေ့ပါ။\n\n"
                f"🔧 Function: {mint_function}\n\n"
                "ဒီ function name က NFT ABI ထဲမှာ "
                "မရှိပါ။"
            )
            return

        # Get function inputs
        inputs = function_abi.get(
            "inputs",
            []
        )

        if inputs:
            input_lines = []

            for item in inputs:
                name = item.get(
                    "name",
                    ""
                )

                input_type = item.get(
                    "type",
                    ""
                )

                input_lines.append(
                    f"• {name}: {input_type}"
                )

            input_text = "\n".join(
                input_lines
            )

        else:
            input_text = "None"

        # Save only after ABI validation
        config["mint_function"] = (
            mint_function
        )

        nft_config.save_config(
            config
        )

        await update.message.reply_text(
            "✅ Mint Function Validated!\n\n"
            f"🔧 Function:\n"
            f"{mint_function}\n\n"
            f"📥 Inputs:\n"
            f"{input_text}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Function Validation Failed!\n\n"
            f"Error: {str(e)}"
        )

@admin_only
async def set_mint_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "❌ Mint Price ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/set_mint_price 0.001"
        )
        return

    try:
        price = float(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Mint Price က number ဖြစ်ရပါမယ်။\n\n"
            "ဥပမာ:\n"
            "/set_mint_price 0.001"
        )
        return

    if price < 0:
        await update.message.reply_text(
            "❌ Mint Price က 0 ထက်ငယ်လို့ မရပါ။"
        )
        return

    try:
        import config.nft_config as nft_config

        config = nft_config.load_config()

        config["mint_price_eth"] = price

        nft_config.save_config(config)

        await update.message.reply_text(
            "✅ Mint Price Set Successfully!\n\n"
            f"💵 Price: {price} ETH"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Failed to save Mint Price!\n\n"
            f"Error: {str(e)}"
        )



@admin_only
async def preview_mint_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "❌ Quantity ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/preview_mint 1"
        )
        return

    try:
        quantity = int(
            context.args[0]
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Quantity က number ဖြစ်ရပါမယ်။\n\n"
            "ဥပမာ:\n"
            "/preview_mint 1"
        )
        return

    if quantity < 1:
        await update.message.reply_text(
            "❌ Quantity က 1 ထက်ငယ်လို့ မရပါ။"
        )
        return

    if quantity > 1000:
        await update.message.reply_text(
            "❌ Quantity အများဆုံး 1000 ပါ။"
        )
        return

    try:
        service = NFTService()

        result = service.preview_mint(
            quantity
        )

        mint_value = (
            service.w3.from_wei(
                result["mint_value_wei"],
                "ether"
            )
        )

        gas_cost = (
            service.w3.from_wei(
                result["gas_cost_wei"],
                "ether"
            )
        )

        total_cost = (
            service.w3.from_wei(
                result["total_cost_wei"],
                "ether"
            )
        )

        balance = (
            service.w3.from_wei(
                result["balance_wei"],
                "ether"
            )
        )

        balance_status = (
            "🟢 SUFFICIENT"
            if result["sufficient_balance"]
            else "🔴 INSUFFICIENT"
        )

        await update.message.reply_text(
            "📋 Mint Preview\n\n"
            f"📄 Contract:\n"
            f"{result['contract']}\n\n"
            f"🔧 Function:\n"
            f"{result['function']}\n\n"
            f"📦 Quantity:\n"
            f"{result['quantity']}\n\n"
            f"💰 Mint Value:\n"
            f"{mint_value} ETH\n\n"
            f"⛽ Gas Limit:\n"
            f"{result['gas_limit']}\n\n"
            f"⛽ Estimated Gas Cost:\n"
            f"{gas_cost} ETH\n\n"
            f"💵 Total Required:\n"
            f"{total_cost} ETH\n\n"
            f"👛 Wallet Balance:\n"
            f"{balance} ETH\n\n"
            f"Balance: {balance_status}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Mint Preview Failed!\n\n"
            f"Error: {str(e)}"
        )

@admin_only
async def set_quantity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ Quantity ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "/set_quantity 5"
        )
        return

    try:
        quantity = int(
            context.args[0]
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Quantity က integer number ဖြစ်ရပါမယ်။"
        )
        return

    if quantity < 1:
        await update.message.reply_text(
            "❌ Quantity က 1 ထက်ငယ်လို့ မရပါ။"
        )
        return

    if quantity > 1000:
        await update.message.reply_text(
            "❌ Quantity အများဆုံး 1000 ပါ။"
        )
        return

    try:
        import config.nft_config as nft_config

        config = nft_config.load_config()

        config["mint_quantity"] = quantity

        nft_config.save_config(
            config
        )

        await update.message.reply_text(
            "✅ Mint Quantity Updated!\n\n"
            f"📦 Quantity: {quantity}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Quantity Update Failed!\n\n"
            f"Error: {str(e)}"
        )


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        service = NFTService()

        result = service.health_check()

        if result["healthy"]:
            overall = "🟢 HEALTHY"
        else:
            overall = "🔴 UNHEALTHY"

        rpc_status = (
            "🟢 OK"
            if result["rpc"]
            else "🔴 FAIL"
        )

        wallet_status = (
            "🟢 OK"
            if result["wallet"]
            else "🔴 FAIL"
        )

        gas_status = (
            "🟢 OK"
            if result["gas"]
            else "🔴 FAIL"
        )

        await update.message.reply_text(
            "🏥 NFT Mint Bot Health\n\n"
            f"Overall: {overall}\n\n"
            f"⛓️ RPC: {rpc_status}\n"
            f"👛 Wallet: {wallet_status}\n"
            f"⛽️ Gas: {gas_status}\n\n"
            f"🔢 Chain ID: "
            f"{result.get('chain_id', 'N/A')}\n"
            f"💰 Balance: "
            f"{result.get('balance', 0):.6f} ETH"
        )

    except Exception:
        await update.message.reply_text(
            "🔴 Health Check Failed!\n\n"
            "System health စစ်လို့မရပါ။"
        )

async def tx(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "❌ Transaction Hash မထည့်ထားပါ။\n\n"
            "အသုံးပြုပုံ:\n"
            "/tx <transaction_hash>"
        )

        return

    tx_hash = context.args[0]

    await update.message.reply_text(
        "🔎 Transaction စစ်နေပါတယ်..."
    )

    try:

        service = NFTService()

        result = service.get_transaction_status(
            tx_hash
        )

        if not result["success"]:

            await update.message.reply_text(
                "❓ Transaction Not Found\n\n"
                f"TX:\n{tx_hash}"
            )

            return

        status = result["status"]

        # =========================
        # PENDING
        # =========================

        if status == "pending":

            await update.message.reply_text(

                "⏳ Transaction Pending\n\n"

                "⛓️ Network: Arc Testnet\n\n"

                "Blockchain confirmation စောင့်နေပါတယ်။\n\n"

                f"🔗 TX:\n{tx_hash}"
            )

            return

        # =========================
        # FAILED
        # =========================

        if status == "failed":

            await update.message.reply_text(

                "❌ Transaction Failed\n\n"

                "⛓️ Network: Arc Testnet\n\n"

                f"📦 Block: {result['block']}\n"
                f"⛽ Gas Used: {result['gas_used']}\n\n"

                f"🔗 TX:\n{tx_hash}"
            )

            return

        # =========================
        # CONFIRMED
        # =========================

        if status == "confirmed":

            await update.message.reply_text(

                "✅ Transaction Confirmed\n\n"

                "⛓️ Network: Arc Testnet\n\n"

                f"📦 Block: {result['block']}\n"
                f"⛽ Gas Used: {result['gas_used']}\n\n"

                f"👤 From:\n"
                f"{result['from']}\n\n"

                f"📄 Contract:\n"
                f"{result['to']}\n\n"

                f"🔗 TX:\n"
                f"{result['tx_hash']}"
            )

            return

    except Exception as e:

        await update.message.reply_text(

            "❌ Transaction Check Failed!\n\n"
            f"Error: {str(e)}"
        )

def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    
    app.add_handler(CommandHandler("balance",balance))
    app.add_handler(CommandHandler("tx",tx))
    app.add_handler(CommandHandler("health",health))
    app.add_handler(CommandHandler("myid",myid))
    app.add_handler(CommandHandler("auto_mint",auto_mint_command))
    app.add_handler(CommandHandler("stop",stop))
    app.add_handler(CommandHandler("config",config))
    app.add_handler(CommandHandler("set_contract",set_contract))
    app.add_handler(CommandHandler("set_mint_function",set_mint_function))
    app.add_handler(CommandHandler("preview_mint",preview_mint_command))
    app.add_handler(CommandHandler("set_price",set_price))
    app.add_handler(CommandHandler("set_quantity",set_quantity))
    app.add_handler(CommandHandler("ready",ready_command))
    
    
    app.add_handler(
    MessageHandler(
        filters.Document.ALL,
        handle_abi_upload
    )
)
    app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_abi_text
    )
)
    
    print("🤖 NFT Mint Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()