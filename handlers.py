from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import requests
from utils import API_URL

# Conversation states
ASK_PASSWORD, ASK_MNEMONIC = range(2)
ASK_NEW_PASSWORD, _ = range(2)
ASK_FROM_CURRENCY, ASK_TO_CURRENCY, ASK_VALUE, ASK_EXCHANGE_RATE = range(4)
ASK_BUY_CURRENCY, ASK_SELL_CURRENCY = range(2)
AMOUNT_TO_BUY, _ = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command to check if the user exists and display the main menu."""
    telegram_id = update.effective_user.id
    response = requests.get(f"{API_URL}/user/exist?user_id={telegram_id}")

    if response.status_code == 200 and response.json().get("exists"):
        keyboard = [
            [InlineKeyboardButton("Get User Info", callback_data="get_user_info")],
            [InlineKeyboardButton("Recover Password", callback_data="recover_password")],
            [InlineKeyboardButton("Orders", callback_data="orders")],
        ]
        message_text = "Welcome back! What would you like to do?"
    else:
        keyboard = [[InlineKeyboardButton("Create Account", callback_data="create_account")]]
        message_text = "Hello! Please create an account to get started."

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle navigation back to the main menu."""
    query = update.callback_query
    await query.answer()
    await start(update, context)


async def orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the 'Create Order' and 'My Orders' buttons."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Create Order", callback_data="create_order")],
        [InlineKeyboardButton("My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("Buy Crypto", callback_data="buy_crypto")],
    ]
    message_text = "What would you like to do with your orders?"
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message_text, reply_markup=reply_markup)


async def create_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the account creation process by asking for a password."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Please enter a password to create your account:")
    return ASK_PASSWORD


async def create_account_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user-provided password and create the account."""
    password = update.message.text
    telegram_id = update.effective_user.id

    try:
        await update.message.delete()
    except Exception as e:
        print(f"Failed to delete password message: {e}")

    response = requests.post(f"{API_URL}/user/createAccount/", json={"user_id": telegram_id, "password": password})

    if response.status_code == 200:
        data = response.json()
        mnemonic_phrase = " ".join(data["mnemonic_phrase"])
        user_address = data["user_address"]

        context.user_data["mnemonic_phrase"] = mnemonic_phrase
        context.user_data["user_address"] = user_address

        message_text = (
            f"Your account has been created successfully!\n\n"
            f"🔑 **Password**: `{password}`\n"
            f"🏠 **Address**: `{user_address}`\n"
            f"📜 **Mnemonic Phrase**: `{mnemonic_phrase}`\n\n"
            f"**Please remember the mnemonic phrase carefully. You will need it to recover your password.**\n"
            f"Click the button below once you've saved your mnemonic phrase securely."
        )
        keyboard = [[InlineKeyboardButton("I have saved it", callback_data="mnemonic_saved")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Failed to create an account. Please try again later or contact support."
        )
        return ConversationHandler.END


async def mnemonic_saved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user confirmation of saving the mnemonic phrase."""
    query = update.callback_query
    await query.answer()

    await start(update, context)


async def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Get User Info' button."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    response = requests.get(f"{API_URL}/user/info?user_id={telegram_id}")

    if response.status_code == 200:
        user_info = response.json()
        user_address = user_info["user_address"]
        wallets = user_info["wallets"]

        wallet_details = "\n".join([f"{w['currency']}: {w['value']}" for w in wallets])

        message_text = (
            f"🏠 **User Address**: `{user_address}`\n\n"
            f"💼 **Wallets**:\n{wallet_details}"
        )
        keyboard = [[InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await query.edit_message_text("Failed to fetch user info. Please try again later.")


async def recover_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the password recovery process by asking for the mnemonic phrase."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Please enter your mnemonic phrase:")
    return ASK_MNEMONIC


async def recover_password_mnemonic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the mnemonic phrase provided by the user."""
    mnemonic_phrase = update.message.text
    telegram_id = update.effective_user.id

    # Save the mnemonic phrase for later use
    context.user_data["mnemonic_phrase"] = mnemonic_phrase

    # Ask for the new password
    await update.message.reply_text("Now, please enter your new password:")
    return ASK_NEW_PASSWORD


async def recover_password_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the new password and call the API to recover the password."""
    new_password = update.message.text
    telegram_id = update.effective_user.id
    mnemonic_phrase = context.user_data.get("mnemonic_phrase")

    if not mnemonic_phrase:
        await update.message.reply_text("❌ Mnemonic phrase is missing. Please start the process again.")
        return ConversationHandler.END

    # Call the recoverPassword API with mnemonic and new password
    response = requests.post(
        f"{API_URL}/user/recoverPassword/",
        json={"user_id": telegram_id, "mnemonic_phrase": mnemonic_phrase, "new_password": new_password},
    )

    if response.status_code == 200:
        # Password updated successfully
        await update.message.reply_text(
            f"✅ Your password has been successfully updated.",
            parse_mode="Markdown",
        )
        # Return to main menu
        await start(update, context)
        return ConversationHandler.END
    else:
        # Failed to update password
        await update.message.reply_text(
            "❌ Failed to recover password. Please check your mnemonic phrase and try again."
        )
        return ConversationHandler.END


async def create_order_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the order creation process by asking for the 'from_currency'."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Please enter the 'from_currency' (e.g., BTC):")
    return ASK_FROM_CURRENCY


async def create_order_from_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'from_currency' input."""
    context.user_data["from_currency"] = update.message.text
    await update.message.delete()

    await update.message.reply_text("Please enter the 'to_currency' (e.g., ETH):")
    return ASK_TO_CURRENCY


async def create_order_to_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'to_currency' input."""
    context.user_data["to_currency"] = update.message.text
    await update.message.delete()

    await update.message.reply_text("Please enter the amount to sell (value):")
    return ASK_VALUE


async def create_order_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'value' input."""
    context.user_data["value"] = float(update.message.text)
    await update.message.delete()

    await update.message.reply_text("Please enter the exchange rate:")
    return ASK_EXCHANGE_RATE


async def create_order_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the exchange rate and create the order."""
    context.user_data["exchange_rate"] = float(update.message.text)
    await update.message.delete()

    # Send the order data to the API
    order_data = {
        "user_id": update.effective_user.id,
        "from_currency": context.user_data["from_currency"],
        "to_currency": context.user_data["to_currency"],
        "value": context.user_data["value"],
        "exchange_rate": context.user_data["exchange_rate"],
    }

    response = requests.post(f"{API_URL}/order/create", json=order_data)

    if response.status_code == 200:
        order_response = response.json()
        message_text = f"Order created successfully: {order_response['msg']}"
    else:
        message_text = "Failed to create order. Please try again later."

    await update.message.reply_text(message_text)

    # Return to main menu
    await start(update, context)
    return ConversationHandler.END


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's orders, with a 'Delete' button under each order."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    response = requests.get(f"{API_URL}/user/orders?user_id={telegram_id}")

    if response.status_code == 200:
        orders = response.json()
        if orders:
            for order in orders:
                message_text = (
                    f"Order ID: {order['order_id']}\n"
                    f"From: {order['from_currency']} → To: {order['to_currency']}\n"
                    f"Amount Sold: {order['amount_sold']} | Amount to Receive: {order['amount_to_receive']}\n"
                    f"Status: {order['status']}\n\n"
                )
                keyboard = [
                    [InlineKeyboardButton("Delete", callback_data=f"delete_order_{order['order_id']}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(message_text, reply_markup=reply_markup)

            keyboard = [[InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Here are your orders:", reply_markup=reply_markup)
        else:
            await query.edit_message_text("You have no orders yet.")
            await orders_menu(update, context)
    else:
        await query.edit_message_text("Failed to fetch your orders. Please try again later.")


async def delete_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Delete' button press to delete an order."""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    order_id = int(callback_data.split("_")[-1])

    telegram_id = update.effective_user.id

    response = requests.delete(f"{API_URL}/order/delete?order_id={order_id}&user_id={telegram_id}")

    if response.status_code == 200:
        await query.edit_message_text(f"Order {order_id} has been deleted successfully.")

    else:
        await query.edit_message_text(f"Failed to delete Order {order_id}. Please try again later.")


async def buy_crypto_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask user what currency they want to buy and sell."""
    query = update.callback_query
    await query.answer()

    # Ask for the currency to buy
    await query.edit_message_text("Which currency would you like to buy?")

    return ASK_BUY_CURRENCY


async def buy_crypto_buy_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for the currency to sell."""
    buy_currency = update.message.text
    context.user_data["buy_currency"] = buy_currency

    # Ask for the currency to sell
    await update.message.reply_text("Which currency would you like to sell?")

    return ASK_SELL_CURRENCY


async def buy_crypto_sell_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available orders as separate messages based on the selected currencies and display a main menu button at the end."""
    sell_currency = update.message.text
    buy_currency = context.user_data["buy_currency"]
    context.user_data["sell_currency"] = sell_currency
    user_id = update.effective_user.id

    response = requests.get(f"{API_URL}/orders/list?user_id={user_id}&currency_to_buy={buy_currency}&currency_to_sell={sell_currency}")

    if response.status_code == 200:
        orders = response.json()
        if orders:
            await update.message.reply_text("Here are the orders that you can buy:")

            for order in orders:
                order_message = (
                    f"Order ID: {order['order_id']}\n"
                    f"From: {order['from_currency']} → To: {order['to_currency']}\n"
                    f"Amount Sold: {order['amount_sold']} | Amount to Receive: {order['amount_to_receive']}\n"
                    f"Status: {order['status']}\n"
                )
                keyboard = [
                    [InlineKeyboardButton("Buy", callback_data=f"buy_order_{order['order_id']}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(order_message, reply_markup=reply_markup)
            keyboard = [[InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Click the button below to go back to the main menu.", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"No available orders to buy {buy_currency} with {sell_currency}.")
            await orders_menu(update, context)
    else:
        await update.message.reply_text("Failed to fetch orders. Please try again later.")
    return ConversationHandler.END


async def buy_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Buy' button press to ask the user for the amount to buy."""
    query = update.callback_query
    await query.answer()

    # Extract the order ID from the callback data
    order_id = int(query.data.split("_")[2])  # "buy_order_1" -> 1
    context.user_data["order_id"] = order_id  # Store the selected order ID

    # Ask the user to enter the amount to buy
    await query.message.reply_text("Please enter the amount you'd like to buy:")

    return AMOUNT_TO_BUY


async def process_amount_to_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the amount entered by the user and make the buy request."""
    amount_to_buy = update.message.text
    try:
        amount_to_buy = float(amount_to_buy)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for the amount to buy.")
        return AMOUNT_TO_BUY

    order_id = context.user_data["order_id"]
    user_id = update.effective_user.id
    buy_currency = context.user_data["buy_currency"]
    sell_currency = context.user_data["sell_currency"]

    buy_data = {
        "user_id": user_id,
        "order_id": order_id,
        "amount_to_buy": amount_to_buy
    }

    response = requests.post(f"{API_URL}/orders/buy", json=buy_data)

    if response.status_code == 200:
        buy_response = response.json()
        amount_received = buy_response["amount_to_receive"]
        amount_paid = buy_response["amount_paid"]

        message_text = (
            f"✅ Your purchase was successful!\n\n"
            f"You bought {amount_received} {buy_currency} for {amount_paid} {sell_currency}."
        )
    else:
        message_text = "❌ Failed to process your purchase. Please try again later."

    await update.message.reply_text(message_text)

    keyboard = [[InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click the button below to go back to the main menu.", reply_markup=reply_markup)

    return ConversationHandler.END


# Conversation handler for creating account
create_account_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_account_start, pattern="^create_account$")],
    states={
        ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_password)],
    },
    fallbacks=[],
)

# Conversation handler for recovering password
recover_password_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(recover_password_start, pattern="^recover_password$")],
    states={
        ASK_MNEMONIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, recover_password_mnemonic)],
        ASK_NEW_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recover_password_new_password)],
    },
    fallbacks=[],
)

create_order_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_order_start, pattern="^create_order$")],
    states={
        ASK_FROM_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_order_from_currency)],
        ASK_TO_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_order_to_currency)],
        ASK_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_order_value)],
        ASK_EXCHANGE_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_order_exchange_rate)],
    },
    fallbacks=[],
)

buy_crypto_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(buy_crypto_start, pattern="^buy_crypto$")],
    states={
        ASK_BUY_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_crypto_buy_currency)],
        ASK_SELL_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_crypto_sell_currency)],
    },
    fallbacks=[],
)

buy_order_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(buy_order, pattern=r"^buy_order_\d+$")],
    states={
        AMOUNT_TO_BUY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount_to_buy)],
    },
    fallbacks=[],
)
