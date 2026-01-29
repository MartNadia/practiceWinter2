import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from bot_config import AUTH_CHOICE, MANUAL_AUTH_USERNAME, MANUAL_AUTH_ROLE, MENU, CHOOSE_HW_TYPE, CHOOSE_HW_CHECK_TYPE, WAITING_FILE, CHOOSE_OUTPUT, ADMIN_MENU, ADD_USER, REMOVE_USER, reply_markup, REPORT_MAPPING, logger
from data_manager import check_access, get_report_name
from report_processor import process_excel_file

current_report_type = None
uploaded_file_path = None
report_result = ""

async def handle_report_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа отчета"""
    user_choice = update.message.text
    
    current_user = context.user_data.get('current_user')
    
    if not current_user:
        await update.message.reply_text(
            "❌ Ошибка авторизации. Пожалуйста, выполните команду /start",
            reply_markup=reply_markup
        )
        return MENU
    
    if user_choice == "👥 Управление пользователями":
        if current_user['role'] != 'admin':
            await update.message.reply_text(
                "❌ Эта функция доступна только администраторам.",
                reply_markup=reply_markup
            )
            return MENU
        
        admin_keyboard = [
            ["👥 Показать всех пользователей"],
            ["➕ Добавить пользователя"],
            ["➖ Удалить пользователя"],
            ["📋 Вернуться в главное меню"]
        ]
        reply_markup_admin = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🛠 ПАНЕЛЬ АДМИНИСТРАТОРА\n\n"
            "Выберите действие:",
            reply_markup=reply_markup_admin
        )
        return ADMIN_MENU
    
    if user_choice in REPORT_MAPPING:
        report_type = REPORT_MAPPING[user_choice]
        
        if not check_access(current_user['username_key'], current_user['role'], report_type):
            if current_user['role'] == 'teacher':
                await update.message.reply_text(
                    f"❌ Этот отчет недоступен для преподавательского состава.\n\n"
                    f"📋 Доступные вам отчеты:\n"
                    f"• 📚 Отчет по темам занятия\n"
                    f"• ✅ Отчет по посещаемости студентов\n"
                    f"• 📝 Отчет по проверенным дз\n\n"
                    f"Пожалуйста, выберите другой отчет из меню:",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ У вас нет доступа к этому отчету.\n\n"
                    f"Пожалуйста, выберите другой отчет из меню:",
                    reply_markup=reply_markup
                )
            return MENU
        
        global current_report_type
        current_report_type = report_type
        
        if current_report_type == "submitted_hw":
            hw_types_keyboard = [
                ["% выполненных д/з за все время"],
                ["% выполненных д/з за 30 дней"]
            ]
            reply_markup_hw = ReplyKeyboardMarkup(hw_types_keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "📊 Вы выбрали отчет по сданным ДЗ.\n\n"
                "Пожалуйста, выберите за какой период:",
                reply_markup=reply_markup_hw
            )
            return CHOOSE_HW_TYPE
        
        elif current_report_type == "checked_hw":
            hw_check_types_keyboard = [
                ["📅 Отчет по проверенным ДЗ за месяц"],
                ["📆 Отчет по проверенным ДЗ за неделю"]
            ]
            reply_markup_hw_check = ReplyKeyboardMarkup(hw_check_types_keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "📝 Вы выбрали отчет по проверенным ДЗ.\n\n"
                "Пожалуйста, выберите за какой период:",
                reply_markup=reply_markup_hw_check
            )
            return CHOOSE_HW_CHECK_TYPE
        
        instructions = {
            "schedule": "📤 Пожалуйста, загрузите Excel-файл с расписанием группы на неделю.",
            "topics": "📤 Пожалуйста, загрузите Excel-файл с темами занятий.\n\nТемы должны быть в формате: 'Урок № _. Тема: _'",
            "students": "📤 Пожалуйста, загрузите Excel-файл с информацией по студентам.",
            "attendance": "📤 Пожалуйста, загрузите Excel-файл с посещаемостью.",
        }
        
        if current_report_type in instructions:
            await update.message.reply_text(
                f"✅ Вы выбрали: {user_choice}\n\n{instructions[current_report_type]}\n\n"
                f"Отправьте файл .xls или .xlsx как документ (скрепка 📎)."
            )
        else:
            await update.message.reply_text(
                f"✅ Вы выбрали: {user_choice}\n\n"
                f"📤 Пожалуйста, загрузите соответствующий Excel-файл.\n\n"
                f"Отправьте файл .xls или .xlsx как документ (скрепка 📎)."
            )
        
        return WAITING_FILE
    
    elif user_choice == "ℹ️ Помощь":
        return await help_command(update, context)
    
    else:
        await update.message.reply_text(
            "Неизвестная команда. Используйте меню.",
            reply_markup=reply_markup
        )
        return MENU

async def handle_hw_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа отчета по сданным ДЗ"""
    hw_type = update.message.text
    
    if hw_type in ["% выполненных д/з за все время", "% выполненных д/з за 30 дней"]:
        context.user_data['hw_period'] = "all_time" if hw_type == "% выполненных д/з за все время" else "30_days"
        
        await update.message.reply_text(
            f"Вы выбрали: {hw_type}\n\n"
            f"📤 Пожалуйста, загрузите Excel-файл со сданными ДЗ.\n\n"
            f"Отправьте файл .xls или .xlsx как документ (скрепка 📎)."
        )
        return WAITING_FILE
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из предложенных вариантов.",
            reply_markup=reply_markup
        )
        return MENU

async def handle_hw_check_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа отчета по проверенным ДЗ"""
    hw_check_type = update.message.text
    
    if hw_check_type in ["📅 Отчет по проверенным ДЗ за месяц", "📆 Отчет по проверенным ДЗ за неделю"]:
        context.user_data['hw_check_period'] = "month" if hw_check_type == "📅 Отчет по проверенным ДЗ за месяц" else "week"
        
        await update.message.reply_text(
            f"Вы выбрали: {hw_check_type}\n\n"
            f"📤 Пожалуйста, загрузите Excel-файл с проверкой ДЗ.\n\n"
            f"Отправьте файл .xls или .xlsx как документ (скрепка 📎)."
        )
        return WAITING_FILE
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из предложенных вариантов.",
            reply_markup=reply_markup
        )
        return MENU

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает загрузку Excel-файлов"""
    global current_report_type
    
    if current_report_type is None:
        await update.message.reply_text(
            "Сначала выберите тип отчета из меню.",
            reply_markup=reply_markup
        )
        return MENU
    
    document = update.message.document
    file_name = document.file_name
    
    if not file_name.endswith(('.xls', '.xlsx')):
        await update.message.reply_text(
            "Пожалуйста, загрузите файл Excel (.xls или .xlsx).",
            reply_markup=reply_markup
        )
        return WAITING_FILE
    os.makedirs("downloads", exist_ok=True)
    
    try:
        file = await document.get_file()
        uploaded_file_path = f"downloads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
        await file.download_to_drive(uploaded_file_path)
        
        await update.message.reply_text(
            f"✅ Файл '{file_name}' успешно загружен!\n\n"
            f"Обрабатываю данные...",
            reply_markup=reply_markup
        )
        current_user = context.user_data.get('current_user')
        if not current_user:
            await update.message.reply_text(
                "❌ Ошибка авторизации. Перезапустите бота командой /start",
                reply_markup=reply_markup
            )
            return MENU
        
        try:
            report_result_text = ""
            
            if current_report_type == "submitted_hw":
                hw_period = context.user_data.get('hw_period', 'all_time')
                report_result_text = process_excel_file(uploaded_file_path, current_report_type, hw_period, current_user)
            elif current_report_type == "checked_hw":
                hw_check_period = context.user_data.get('hw_check_period', 'month')
                report_result_text = process_excel_file(uploaded_file_path, current_report_type, hw_check_period, current_user)
            else:
                report_result_text = process_excel_file(uploaded_file_path, current_report_type, None, current_user)
            try:
                os.remove(uploaded_file_path)
                logger.info(f"Файл {uploaded_file_path} успешно удален")
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить файл {uploaded_file_path}: {delete_error}")

            context.user_data['report_result'] = report_result_text
            context.user_data['current_report_type'] = current_report_type
            
            keyboard = [
                [
                    InlineKeyboardButton("📝 Сообщение", callback_data="output_text"),
                    InlineKeyboardButton("📁 Файл .txt", callback_data="output_file")
                ]
            ]
            reply_markup_inline = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ Отчет готов! Как вы хотите получить результат?",
                reply_markup=reply_markup_inline
            )
            return CHOOSE_OUTPUT
            
        except Exception as e:
            try:
                os.remove(uploaded_file_path)
                logger.info(f"Файл {uploaded_file_path} удален после ошибки обработки")
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить файл после ошибки: {delete_error}")
            
            logger.error(f"Ошибка обработки файла: {e}")
            await update.message.reply_text(
                f"❌ Ошибка обработки файла: {str(e)[:200]}\n\n"
                f"Проверьте формат файла и попробуйте еще раз.",
                reply_markup=reply_markup
            )
            return MENU
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        await update.message.reply_text(
            f"❌ Ошибка загрузки файла: {str(e)[:200]}",
            reply_markup=reply_markup
        )
        return MENU


async def handle_output_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор формата вывода результата"""
    query = update.callback_query
    await query.answer()
    
    report_result = context.user_data.get('report_result', '')
    current_report_type = context.user_data.get('current_report_type', '')
    
    if not report_result:
        await query.message.reply_text(
            "❌ Ошибка: отчет не найден. Попробуйте заново.",
            reply_markup=reply_markup
        )
        return MENU
    
    if query.data == "output_text":
        if len(report_result) > 4000:
            chunks = []
            current_chunk = ""
            
            lines = report_result.split('\n')
            
            for line in lines:
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk)
            
            for i, chunk in enumerate(chunks, 1):
                if i == 1:
                    await query.message.reply_text(f"📊 Отчет (часть {i} из {len(chunks)}):\n\n{chunk}")
                else:
                    await query.message.reply_text(f"📊 Продолжение отчета (часть {i}):\n\n{chunk}")
                
                import asyncio
                await asyncio.sleep(0.5)
        else:
            try:
                await query.message.reply_text(report_result)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                clean_text = report_result.replace('`', "'").replace('*', '').replace('_', '')
                await query.message.reply_text(clean_text[:4000])
    
    elif query.data == "output_file":
        os.makedirs("reports", exist_ok=True)
        report_filename = f"reports/report_{current_report_type}_{datetime.now().strftime('%Y%m%d')}.txt"
    
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_result)
        
            with open(report_filename, 'rb') as f:
                filename_for_user = f"report_{current_report_type}_{datetime.now().strftime('%Y%m%d')}.txt"
            
                await query.message.reply_document(
                    document=f,
                    filename=filename_for_user,
                    caption="📎 Ваш отчет в файле .txt"
                )
        except Exception as e:
            logger.error(f"Ошибка создания файла: {e}")
            await query.message.reply_text(
                f"❌ Ошибка создания файла: {str(e)[:200]}",
                reply_markup=reply_markup
            )
    await query.message.reply_text(
        "Выберите следующий отчет из меню:",
        reply_markup=reply_markup
    )
    return MENU

async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает административное меню"""
    user_choice = update.message.text
    
    current_user = context.user_data.get('current_user')
    
    if not current_user or current_user['role'] != 'admin':
        await update.message.reply_text(
            "❌ Эта функция доступна только администраторам.",
            reply_markup=reply_markup
        )
        return MENU
    
    if user_choice == "👥 Показать всех пользователей":
        from data_manager import load_users
        users = load_users()
        
        if not users:
            await update.message.reply_text(
                "📋 Список пользователей пуст.",
                reply_markup=reply_markup
            )
            return MENU
        
        users_list = "📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ:\n\n"
        for username, data in users.items():
            users_list += f"👤 {username}:\n"
            users_list += f"   📝 Имя: {data['full_name']}\n"
            users_list += f"   📱 Telegram: {data.get('telegram_username', 'Не указан')}\n"
            users_list += f"   🎯 Роль: {'Администратор' if data['role'] == 'admin' else 'Преподаватель'}\n"
            if data.get('subjects'):
                users_list += f"   📚 Дисциплины: {', '.join(data['subjects'])}\n"
            users_list += f"   ⚙️ Тип: {'Предустановленный' if data.get('is_predefined', True) else 'Добавленный'}\n"
            users_list += "─" * 30 + "\n"
        
        if len(users_list) > 4000:
            chunks = [users_list[i:i+4000] for i in range(0, len(users_list), 4000)]
            for i, chunk in enumerate(chunks, 1):
                await update.message.reply_text(f"📋 Список пользователей (часть {i}):\n\n{chunk}")
                import asyncio
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(users_list)
        
        admin_keyboard = [
            ["👥 Показать всех пользователей"],
            ["➕ Добавить пользователя"],
            ["➖ Удалить пользователя"],
            ["📋 Вернуться в главное меню"]
        ]
        reply_markup_admin = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup_admin
        )
        return ADMIN_MENU
        
    elif user_choice == "➕ Добавить пользователя":
        await update.message.reply_text(
            "➕ ДОБАВЛЕНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ\n\n"
            "Введите данные в формате:\n"
            "username telegram_username full_name role [subjects]\n\n"
            "Примеры:\n"
            "1. teacher3 @ivanov Иван Иванов teacher\n"
            "2. teacher4 @petrov Петр Петров teacher Математика,Физика\n"
            "3. admin4 @admin Александр Админов admin\n\n"
            "Для отмены введите: отмена"
        )
        return ADD_USER
        
    elif user_choice == "➖ Удалить пользователя":
        from data_manager import load_users
        users = load_users()
        
        if not users:
            await update.message.reply_text(
                "📋 Список пользователей пуст.",
                reply_markup=reply_markup
            )
            return MENU
        
        removable_users = {username: data for username, data in users.items() 
                          if not data.get('is_predefined', True)}
        
        if not removable_users:
            await update.message.reply_text(
                "❌ Нет пользователей, которых можно удалить.\n"
                "Предустановленные пользователи защищены от удаления.",
                reply_markup=reply_markup
            )
            return MENU
        
        users_list = "\n".join([f"• {username} - {data['full_name']}" 
                              for username, data in removable_users.items()])
        
        await update.message.reply_text(
            "➖ УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ\n\n"
            "Введите username пользователя для удаления:\n\n"
            f"Доступные для удаления пользователи:\n{users_list}\n\n"
            "Для отмены введите: отмена"
        )
        return REMOVE_USER
        
    elif user_choice == "📋 Вернуться в главное меню":
        await update.message.reply_text(
            "Возврат в главное меню:",
            reply_markup=reply_markup
        )
        return MENU
    
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из предложенных вариантов.",
            reply_markup=reply_markup
        )
        return ADMIN_MENU

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает административные команды"""
    current_user = context.user_data.get('current_user')
    
    if not current_user or current_user['role'] != 'admin':
        await update.message.reply_text(
            "❌ Эта команда доступна только администраторам.",
            reply_markup=reply_markup
        )
        return MENU
    
    admin_text = """
    🛠 АДМИНИСТРАТИВНЫЕ КОМАНДЫ:
    
    /users - Показать всех пользователей
    /add_user - Добавить нового пользователя
    /remove_user - Удалить пользователя
    
    Для добавления пользователя используйте команду:
    /add_user username telegram_username full_name role [subjects]
    
    Пример:
    /add_user teacher3 @ivanov Иван Иванов teacher Математика,Физика
    """
    
    await update.message.reply_text(admin_text, reply_markup=reply_markup)

async def handle_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает добавление нового пользователя"""
    user_input = update.message.text.strip()
    
    if user_input.lower() == "отмена":
        await update.message.reply_text(
            "❌ Добавление пользователя отменено.",
            reply_markup=reply_markup
        )
        return MENU
    
    try:
        parts = user_input.split()
        
        if len(parts) < 4:
            raise ValueError("Недостаточно данных")
        username = parts[0]
        telegram_username = parts[1]
        role_positions = []
        for i, part in enumerate(parts):
            if part.lower() in ['admin', 'teacher']:
                role_positions.append(i)
        
        if not role_positions:
            raise ValueError("Роль не найдена. Используйте 'admin' или 'teacher'")
        
        role_position = role_positions[0]
        if role_position <= 2:
            raise ValueError("Полное имя не может быть пустым")
        
        full_name = ' '.join(parts[2:role_position])
        role = parts[role_position].lower()
        subjects = []
        if len(parts) > role_position + 1:
            subjects_str = ' '.join(parts[role_position + 1:])
            subjects = [s.strip() for s in subjects_str.split(',')]
        
        if role not in ['admin', 'teacher']:
            raise ValueError(f"Неверная роль '{role}'. Допустимые значения: admin, teacher")
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Ошибка ввода: {str(e)}\n\n"
            "Правильный формат:\n"
            "username telegram_username полное_имя role [предметы,через,запятую]\n\n"
            "Примеры:\n"
            "• teacher3 @ivanov 'Иван Иванов Петрович' teacher Математика,Физика\n"
            "• admin4 @admin 'Александр Админов' admin\n\n"
            "Попробуйте еще раз или введите 'отмена' для отмены:"
        )
        return ADD_USER
    
    user_data = {
        'telegram_username': telegram_username,
        'full_name': full_name,
        'role': role,
        'is_predefined': False
    }
    
    if subjects:
        user_data['subjects'] = subjects
    
    from data_manager import add_user
    success, message = add_user(username, user_data)
    
    if success:
        await update.message.reply_text(
            f"✅ Пользователь успешно добавлен!\n\n"
            f"👤 Username: {username}\n"
            f"📝 Имя: {full_name}\n"
            f"📱 Telegram: {telegram_username}\n"
            f"🎯 Роль: {'Администратор' if role == 'admin' else 'Преподаватель'}\n"
            f"📚 Дисциплины: {', '.join(subjects) if subjects else 'Не указаны'}",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка: {message}\n\n"
            "Попробуйте еще раз или введите 'отмена' для отмены:",
            reply_markup=reply_markup
        )
        return ADD_USER
    
    return MENU

async def handle_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает удаление пользователя"""
    username_input = update.message.text.strip().lower()
    
    if username_input == "отмена":
        await update.message.reply_text(
            "❌ Удаление пользователя отменено.",
            reply_markup=reply_markup
        )
        return MENU
    
    from data_manager import remove_user
    success, message = remove_user(username_input)
    
    if success:
        await update.message.reply_text(
            f"✅ {message}",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ {message}\n\n"
            "Попробуйте еще раз или введите 'отмена' для отмены:",
            reply_markup=reply_markup
        )
        return REMOVE_USER
    
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет справку по использованию бота"""
    current_user = context.user_data.get('current_user')
    
    help_text = """
    ℹ️ ПОМОЩЬ ПО ИСПОЛЬЗОВАНИЮ БОТА
    
    📋 Как работать с ботом:
    1. Выберите тип отчета из меню
    2. Загрузите Excel-файл по запросу
    3. Дождитесь обработки
    4. Выберите формат вывода (сообщение или файл)
    
    📁 Требования к файлам:
    • Формат: .xls или .xlsx
    • Названия колонок должны соответствовать требованиям
    """
    
    if current_user:
        role_text = "Управляющий состав" if current_user['role'] == 'admin' else "Преподавательский состав"
        test_mode = " (тестовый режим)" if current_user.get('is_test_mode') else ""
        help_text += f"\n👤 Ваш профиль{test_mode}:\n"
        help_text += f"• Имя: {current_user['full_name']}\n"
        help_text += f"• Telegram: {current_user.get('telegram_username', 'Не указан')}\n"
        help_text += f"• Роль: {role_text}\n"
        help_text += f"• Доступные отчеты:\n"
        
        if current_user['role'] == 'admin':
            help_text += "  • Все отчеты\n"
            help_text += "  • Управление пользователями\n"
        else:
            help_text += "  • 📚 Отчет по темам занятия\n"
            help_text += "  • ✅ Отчет по посещаемости студентов\n"
            help_text += "  • 📝 Отчет по проверенным дз\n"
    else:
        help_text += "\n🔐 Статус: Не авторизован\n"
        help_text += "Для начала работы выполните команду /start\n"
    
    help_text += """
    
    📊 Какие отчеты может генерировать бот:
    • 📅 Расписание - количество пар по дисциплинам
    • 📚 Темы занятий - проверка формата тем
    • 👥 Студенты - фильтрация по оценкам
    • ✅ Посещаемость - преподаватели с низкой посещаемостью
    • 📝 Проверка ДЗ - преподаватели с низким % проверки (за месяц или неделю)
    • 📊 Сдача ДЗ - студенты с низким % сдачи (за все время или 30 дней)
    
    🛠 Административные функции:
    • Просмотр всех пользователей
    • Добавление новых пользователей
    • Удаление пользователей
    
    📌 Основные команды:
    /start - Начать работу с ботом
    /help - Показать это сообщение справки
    """
    
    await update.message.reply_text(help_text, reply_markup=reply_markup)
    
    if current_user:
        return MENU
    else:
        await update.message.reply_text(
            "Для начала работы выполните команду /start",
            reply_markup=reply_markup
        )
        from bot_config import AUTH_CHOICE
        return AUTH_CHOICE