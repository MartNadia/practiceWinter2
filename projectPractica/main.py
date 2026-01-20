import os
from telegram import Update
from telegram.ext import Application, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot_config import TOKEN, AUTH_CHOICE, MANUAL_AUTH_USERNAME, MENU, CHOOSE_HW_TYPE, CHOOSE_HW_CHECK_TYPE, WAITING_FILE, CHOOSE_OUTPUT, logger
from auth import start, handle_auth_choice, handle_manual_auth_username
from handlers import handle_report_selection, handle_hw_type_selection, handle_hw_check_type_selection, handle_document, handle_output_choice, help_command

def main():
    """Запуск бота"""
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTH_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auth_choice)],
            MANUAL_AUTH_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_auth_username)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_selection)],
            CHOOSE_HW_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hw_type_selection)],
            CHOOSE_HW_CHECK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hw_check_type_selection)],
            WAITING_FILE: [MessageHandler(filters.Document.ALL, handle_document)],
            CHOOSE_OUTPUT: [CallbackQueryHandler(handle_output_choice)],
        },
        fallbacks=[CommandHandler('start', start)],
        name="main_conversation",
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()