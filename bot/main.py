from telegram import Update
import asyncio
from services.blockchain import NFTService
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv
import os


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

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        "🆔 Your Telegram ID\n\n"
        f"{user_id}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 NFT Mint Bot မှ ကြိုဆိုပါတယ်!\n\n"

        "🪙 /mint - NFT Mint\n"
        "💰 /balance - Wallet Balance\n"
        "📊 /status - Bot Status\n"
        "🏥 /health - System Health\n"
        "🔎 /tx - Transaction Status\n"
        "🆔 /myid - Get Telegram ID"
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

@admin_only
async def mint(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if mint_lock.locked():
        await update.message.reply_text(
            "⏳ NFT mint တစ်ခု လုပ်နေဆဲပါ။\n"
            "ခဏစောင့်ပြီး ပြန်စမ်းပေးပါ။"
        )
        return

    async with mint_lock:

        await update.message.reply_text(
            "⏳ NFT mint လုပ်နေပါတယ်...\n"
            "ခဏစောင့်ပေးပါ။"
        )

        service = NFTService()

        result = service.mint()

        if result["success"]:

            await update.message.reply_text(
                "🎉 NFT Minted Successfully!\n\n"
                f"🎨 Token ID: #{result['token_id']}\n"
                f"👤 Owner:\n{result['owner']}\n\n"
                f"📦 Block: {result['block']}\n"
                f"⛽ Gas Used: {result['gas_used']}\n\n"
                f"🔗 Transaction:\n{result['tx_hash']}\n\n"
                "⛓️ Network: Arc Testnet"
            )

        else:

            error_type = result.get(
                "error_type",
                "unknown"
            )

            if error_type == "insufficient_balance":

                message = (
                    "💰 Insufficient Balance\n\n"
                    "NFT mint လုပ်ဖို့ လိုအပ်တဲ့ "
                    "gas fee ပေးရန် wallet balance မလုံလောက်ပါ။"
                )

            elif error_type == "rpc_timeout":

                message = (
                    "⏱️ Blockchain Timeout\n\n"
                    "Blockchain server က response ပြန်တာ "
                    "ကြာနေပါတယ်။ ခဏနေပြီး ပြန်စမ်းပါ။"
                )

            elif error_type == "rpc_connection":

                message = (
                    "🌐 Blockchain Connection Error\n\n"
                    "Blockchain network နဲ့ connection "
                    "မရရှိသေးပါ။ ခဏနေပြီး ပြန်စမ်းပါ။"
                )

            elif error_type == "contract_reverted":

                message = (
                    "📄 Contract Rejected\n\n"
                    "NFT smart contract က transaction ကို "
                    "လက်မခံပါ။"
                )

            elif error_type == "nonce_error":

                message = (
                    "🔢 Transaction Nonce Error\n\n"
                    "Transaction sequence ပြဿနာဖြစ်နေပါတယ်။ "
                    "ခဏနေပြီး ပြန်စမ်းပါ။"
                )

            elif error_type == "gas_error":

                message = (
                    "⛽ Gas Error\n\n"
                    "Transaction အတွက် gas ပြဿနာရှိနေပါတယ်။"
                )

            else:

                message = (
                    "❌ NFT Mint Failed!\n\n"
                    "မမျှော်လင့်ထားတဲ့ ပြဿနာတစ်ခု "
                    "ဖြစ်သွားပါတယ်။"
                )

            await update.message.reply_text(
                message
            )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        service = NFTService()

        status = service.get_status()

        blockchain_status = (
            "🟢 Connected"
            if status["connected"]
            else "🔴 Disconnected"
        )

        await update.message.reply_text(
            "📊 NFT Mint Bot Status\n\n"
            "🤖 Bot: 🟢 Online\n"
            f"⛓️ Blockchain: {blockchain_status}\n"
            f"🔢 Chain ID: {status['chain_id']}\n"
            f"📦 Latest Block: {status['latest_block']}\n"
            f"🎨 Next Token ID: {status['next_token_id']}\n"
            f"💰 Balance: {status['balance']:.6f} USDC"
        )

    except Exception as e:

        await update.message.reply_text(
            "❌ Status Check Failed!\n\n"
            f"Error: {str(e)}"
        )
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    service = NFTService()

    balance = service.get_balance()

    await update.message.reply_text(
        "💰 Bot Wallet Balance\n\n"
        f"💵 {balance:.6f} USDC"
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

        contract_status = (
            "🟢 OK"
            if result["contract"]
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
            f"📄 Contract: {contract_status}\n"
            f"👛 Wallet: {wallet_status}\n"
            f"⛽ Gas: {gas_status}\n\n"
            f"🔢 Chain ID: {result.get('chain_id', 'N/A')}\n"
            f"🎨 Next Token ID: "
            f"{result.get('next_token_id', 'N/A')}\n"
            f"💰 Balance: "
            f"{result.get('balance', 0):.6f} USDC"
        )

    except Exception as e:

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
    app.add_handler(CommandHandler("mint",mint))
    app.add_handler(CommandHandler("tx",tx))
    app.add_handler(CommandHandler("health",health))
    app.add_handler(CommandHandler("myid",myid))

    print("🤖 NFT Mint Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()