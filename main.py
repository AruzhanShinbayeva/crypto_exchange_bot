from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from handlers import create_account_handler, recover_password_handler, start, get_user_info, main_menu, mnemonic_saved, \
    orders_menu, create_order_handler, my_orders, delete_order, buy_crypto_handler, buy_order_handler

from utils import TELEGRAM_TOKEN


def main():
    """Main entry point for the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(create_account_handler)
    application.add_handler(CallbackQueryHandler(get_user_info, pattern="^get_user_info$"))
    application.add_handler(recover_password_handler)
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(mnemonic_saved, pattern="^mnemonic_saved$"))

    application.add_handler(CallbackQueryHandler(orders_menu, pattern="^orders$"))
    application.add_handler(create_order_handler)
    application.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    application.add_handler(CallbackQueryHandler(delete_order, pattern="^delete_order_"))

    application.add_handler(buy_crypto_handler)
    application.add_handler(buy_order_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
