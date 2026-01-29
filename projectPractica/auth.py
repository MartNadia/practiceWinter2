from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from data_manager import load_users, add_user, remove_user
from bot_config import reply_markup, logger

current_user = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс авторизации"""
    user = update.effective_user
 
    users = load_users()
    
    if not users:
        await update.message.reply_text(
            "❌ Ошибка: база пользователей пуста.\n"
            "Обратитесь к администратору для настройки системы.",
            reply_markup=reply_markup
        )
        from bot_config import AUTH_CHOICE
        return AUTH_CHOICE
    
    found_user = None
    found_username = None
    
    for username_key, user_data in users.items():
        telegram_username = user_data.get('telegram_username', '').lstrip('@')
        if telegram_username and telegram_username.lower() == user.username.lower():
            found_user = user_data
            found_username = username_key
            break
    
    if found_user:
        global current_user
        found_user['username_key'] = found_username
        current_user = found_user
        
        welcome_text = f"✅ Авторизация успешна!\n\n"
        welcome_text += f"👤 Добро пожаловать, {current_user['full_name']}!\n"
        welcome_text += f"📱 Telegram: {current_user.get('telegram_username', '@' + user.username)}\n"
        welcome_text += f"🎯 Роль: {'Управляющий состав' if current_user['role'] == 'admin' else 'Преподавательский состав'}\n"
        
        if current_user['role'] == 'teacher':
            welcome_text += f"📚 Дисциплины: {', '.join(current_user['subjects'])}\n\n"
            welcome_text += "📋 Доступные вам отчеты:\n"
            welcome_text += "• 📚 Отчет по темам занятия\n"
            welcome_text += "• ✅ Отчет по посещаемости студентов\n"
            welcome_text += "• 📝 Отчет по проверенным дз\n\n"
        else:
            welcome_text += "\n📋 У вас есть доступ ко всем отчеты.\n\n"
        
        welcome_text += "Выберите вид отчета из меню ниже:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        from bot_config import MENU
        return MENU
    else:
        auth_keyboard = [
            ["🔐 Автоматическая авторизация"],
            ["🛠 Ручная авторизация (тестирование)"],
            ["❌ Отмена"]
        ]
        reply_markup_auth = ReplyKeyboardMarkup(auth_keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"🔐 Требуется авторизация\n\n"
            f"Ваш Telegram username: @{user.username if user.username else 'не установлен'}\n\n"
            f"Выберите тип авторизации:",
            reply_markup=reply_markup_auth
        )
        from bot_config import AUTH_CHOICE
        return AUTH_CHOICE

async def handle_auth_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа авторизации"""
    user_choice = update.message.text
    
    if user_choice == "🔐 Автоматическая авторизация":
        user = update.effective_user
        
        if not user.username:
            await update.message.reply_text(
                "❌ У вас не установлен username в Telegram.\n\n"
                "Для автоматической авторизации необходимо установить username в настройках Telegram:\n"
                "Настройки → Имя пользователя → Установить username\n\n"
                "После установки username перезапустите бота командой /start\n\n"
                "Или выберите ручную авторизацию для тестирования."
            )
            from bot_config import AUTH_CHOICE
            return AUTH_CHOICE
        
        users = load_users()
        users_list = "\n".join([f"• {user_data.get('telegram_username', '@' + username)} - {user_data['full_name']}" 
                              for username, user_data in users.items()])
        
        await update.message.reply_text(
            f"❌ Доступ запрещен!\n\n"
            f"Пользователь @{user.username} не найден в системе.\n"
            f"Если вы должны иметь доступ к боту, обратитесь к администратору.\n\n"
            f"Зарегистрированные пользователи:\n{users_list}\n\n"
            f"Для тестирования выберите 'Ручная авторизация'."
        )
        from bot_config import AUTH_CHOICE
        return AUTH_CHOICE
        
    elif user_choice == "🛠 Ручная авторизация (тестирование)":
        users = load_users()
        
        if not users:
            await update.message.reply_text(
                "❌ Ошибка: база пользователей пуста.\n"
                "Нет доступных пользователей для тестирования.",
                reply_markup=reply_markup
            )
            from bot_config import AUTH_CHOICE
            return AUTH_CHOICE
        
        await update.message.reply_text(
            "🛠 РУЧНАЯ АВТОРИЗАЦИЯ ДЛЯ ТЕСТИРОВАНИЯ\n\n"
            "Введите username для тестирования (например: admin1, teacher_1):\n\n"
            "Доступные тестовые пользователи:\n" +
            "\n".join([f"• {username} - {data['full_name']} ({'Управляющий' if data['role'] == 'admin' else 'Преподаватель'})" 
                      for username, data in users.items()])
        )
        from bot_config import MANUAL_AUTH_USERNAME
        return MANUAL_AUTH_USERNAME
        
    elif user_choice == "❌ Отмена":
        await update.message.reply_text("Авторизация отменена.")
        return ConversationHandler.END
        
    else:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных вариантов.")
        from bot_config import AUTH_CHOICE
        return AUTH_CHOICE

async def handle_manual_auth_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод username для ручной авторизации"""
    username_input = update.message.text.strip()
    
    users = load_users()
    
    if username_input in users:
        context.user_data['manual_user'] = username_input
        user_data = users[username_input]
        
        user_data['username_key'] = username_input
        user_data['is_test_mode'] = True
        
        context.user_data['current_user'] = user_data
        
        welcome_text = f"🛠 ТЕСТОВЫЙ РЕЖИМ АКТИВИРОВАН\n\n"
        welcome_text += f"👤 Вы вошли как: {user_data['full_name']}\n"
        welcome_text += f"📱 Telegram: {user_data.get('telegram_username', 'Не указан')}\n"
        welcome_text += f"🎯 Роль: {'Управляющий состав' if user_data['role'] == 'admin' else 'Преподавательский состав'}\n"
        
        if user_data['role'] == 'teacher':
            welcome_text += f"📚 Дисциплины: {', '.join(user_data['subjects'])}\n\n"
            welcome_text += "📋 Доступные вам отчеты:\n"
            welcome_text += "• 📚 Отчет по темам занятия\n"
            welcome_text += "• ✅ Отчет по посещаемости студентов\n"
            welcome_text += "• 📝 Отчет по проверенным дз\n\n"
        else:
            welcome_text += "\n📋 У вас есть доступ ко всем отчеты.\n\n"
        
        welcome_text += "⚠️ Внимание: Вы находитесь в тестовом режиме.\n"
        welcome_text += "Выберите вид отчета из меню ниже:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        from bot_config import MENU
        return MENU
    else:
        users = load_users()
        await update.message.reply_text(
            f"❌ Пользователь '{username_input}' не найден.\n\n"
            f"Доступные пользователи:\n" +
            "\n".join([f"• {username} - {data['full_name']}" for username, data in users.items()]) +
            f"\n\nВведите username из списка выше:"
        )
        from bot_config import MANUAL_AUTH_USERNAME
        return MANUAL_AUTH_USERNAME