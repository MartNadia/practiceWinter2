# Перепроверить работу 4 пункта с авторизацией админа и преподавателя
import logging
import pandas as pd
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

AUTH_CHOICE, MANUAL_AUTH_USERNAME, MANUAL_AUTH_ROLE, TEST_MODE, MENU, WAITING_FILE, CHOOSE_HW_TYPE, CHOOSE_HW_CHECK_TYPE, CHOOSE_OUTPUT = range(9)

TOKEN = "8211522202:AAH8XRQVCsQBcwk7R23t9RCzTs5_e_ukNsw"

USERS_FILE = "users.json"

PREDEFINED_USERS = {
    "admin1": {
        "telegram_username": "@KaterinaRyabkova",
        "full_name": "Рябкова Екатерина -",
        "subjects": ["Основы философии", "ОБЖ"],
        "role": "admin",
        "is_predefined": True
    },
    "admin2": {
        "telegram_username": "@balakhnina",
        "full_name": "Балахина Ксения -",
        "subjects": ["-"],
        "role": "admin",
        "is_predefined": True
    },
    "admin3": {
        "telegram_username": "@JuliaaChernova",
        "full_name": "Чернова Юлия Андреевна",
        "subjects": ["ОГСЭ.05 Физическая культура"],
        "role": "admin",
        "is_predefined": True
    },
    "teacher_1": {
        "telegram_username": "@Mazero_T",
        "full_name": "Мазэро Тинаше -",
        "subjects": ["Иностранный язык в профессиональной деятельности РПО", "Иностранный язык в профессиональной деятельности ГД"],
        "role": "teacher",
        "is_predefined": True
    },
    "teacher_2": {
        "telegram_username": "@lekalukyanova",
        "full_name": "Лукьянова Елена -",
        "subjects": ["Интернет-маркетинг"],
        "role": "teacher",
        "is_predefined": True
    },
    "teacher_3": {
        "telegram_username": "@Alexandr_NickolaevichS",
        "full_name": "Суслов Александр -",
        "subjects": ["Основы алгоритмизации"],
        "role": "teacher",
        "is_predefined": True
    }
    # "teacher_4": {
    #     "telegram_username": "@dikuweidc",
    #     "full_name": "Мартынова Надежда Дмитриевна",
    #     "subjects": ["Тестировщик"],
    #     "role": "teacher",
    #     "is_predefined": True
    # }
}

def load_users():
    """Загружает пользователей из файла и добавляет предустановленных"""
    users = PREDEFINED_USERS.copy()
    
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                saved_users = json.load(f)
                for username, data in saved_users.items():
                    if username not in users:
                        users[username] = data
                        users[username]['is_predefined'] = False
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
    
    return users

def save_users(users):
    """Сохраняет пользователей в файл (только не предустановленных)"""
    users_to_save = {username: data for username, data in users.items() 
                    if not data.get('is_predefined', False)}
    
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователей: {e}")

def check_access(username, user_role, report_type):
    """Проверяет доступ пользователя к отчету"""
    report_mapping = {
        "schedule": "schedule",
        "topics": "topics",
        "students": "students",
        "attendance": "attendance",
        "checked_hw": "checked_hw",
        "submitted_hw": "submitted_hw"
    }
    
    if report_type in report_mapping:
        report_type = report_mapping[report_type]
    
    # Управляющий состав имеет доступ ко всему
    if user_role == "admin":
        return True
    
    # Преподавательский состав имеет доступ только к отчетам 2, 4, 5
    if user_role == "teacher":
        allowed_reports = ["topics", "attendance", "checked_hw"]
        return report_type in allowed_reports
    
    return False

def get_report_name(report_type):
    """Возвращает русское название отчета"""
    report_names = {
        "schedule": "📅 Отчет по выставленному расписанию",
        "topics": "📚 Отчет по темам занятия",
        "students": "👥 Отчет по студентам",
        "attendance": "✅ Отчет по посещаемости студентов",
        "checked_hw": "📝 Отчет по проверенным дз",
        "submitted_hw": "📊 Отчет по сданным дз"
    }
    return report_names.get(report_type, report_type)

menu_keyboard = [
    ["📅 Отчет по выставленному расписанию"],
    ["📚 Отчет по темам занятия"],
    ["👥 Отчет по студентам"],
    ["✅ Отчет по посещаемости студентов"],
    ["📝 Отчет по проверенным дз"],
    ["📊 Отчет по сданным дз"],
    ["ℹ️ Помощь"]
]

reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

current_report_type = None
uploaded_file_path = None
report_result = ""
current_user = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс авторизации"""
    user = update.effective_user
    
    users = load_users()
    
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
            welcome_text += "\n📋 У вас есть доступ ко всем отчетам.\n\n"
        
        welcome_text += "Выберите вид отчета из меню ниже:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
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
            return AUTH_CHOICE
        
        users_list = "\n".join([f"• {user_data.get('telegram_username', '@' + username)} - {user_data['full_name']}" 
                              for username, user_data in PREDEFINED_USERS.items()])
        
        await update.message.reply_text(
            f"❌ Доступ запрещен!\n\n"
            f"Пользователь @{user.username} не найден в системе.\n"
            f"Если вы должны иметь доступ к боту, обратитесь к администратору.\n\n"
            f"Разрешенные пользователи:\n{users_list}\n\n"
            f"Для тестирования выберите 'Ручная авторизация'."
        )
        return AUTH_CHOICE
        
    elif user_choice == "🛠 Ручная авторизация (тестирование)":
        await update.message.reply_text(
            "🛠 РУЧНАЯ АВТОРИЗАЦИЯ ДЛЯ ТЕСТИРОВАНИЯ\n\n"
            "Введите username для тестирования (например: admin1, teacher_1):\n\n"
            "Доступные тестовые пользователи:\n" +
            "\n".join([f"• {username} - {data['full_name']} ({'Управляющий' if data['role'] == 'admin' else 'Преподаватель'})" 
                      for username, data in PREDEFINED_USERS.items()])
        )
        return MANUAL_AUTH_USERNAME
        
    elif user_choice == "❌ Отмена":
        await update.message.reply_text("Авторизация отменена.")
        return ConversationHandler.END
        
    else:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных вариантов.")
        return AUTH_CHOICE

async def handle_manual_auth_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод username для ручной авторизации"""
    username_input = update.message.text.strip()
    
    users = load_users()
    
    if username_input in users:
        context.user_data['manual_user'] = username_input
        context.user_data['user_data'] = users[username_input]
        
        await update.message.reply_text(
            f"✅ Найден пользователь: {users[username_input]['full_name']}\n"
            f"Telegram: {users[username_input].get('telegram_username', 'Не указан')}\n"
            f"Роль: {'Управляющий состав' if users[username_input]['role'] == 'admin' else 'Преподавательский состав'}\n\n"
            f"Выберите режим тестирования:",
            reply_markup=ReplyKeyboardMarkup([
                ["✅ Тестировать как этот пользователь"],
                ["🔄 Выбрать другого пользователя"],
                ["❌ Отмена"]
            ], resize_keyboard=True)
        )
        return MANUAL_AUTH_ROLE
    else:
        await update.message.reply_text(
            f"❌ Пользователь '{username_input}' не найден.\n\n"
            f"Доступные пользователи:\n" +
            "\n".join([f"• {username} - {data['full_name']}" for username, data in PREDEFINED_USERS.items()]) +
            f"\n\nВведите username из списка выше:"
        )
        return MANUAL_AUTH_USERNAME

async def handle_manual_auth_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор режима ручной авторизации"""
    choice = update.message.text
    
    if choice == "✅ Тестировать как этот пользователь":
        username = context.user_data['manual_user']
        user_data = context.user_data['user_data']
        
        global current_user
        user_data['username_key'] = username
        user_data['is_test_mode'] = True
        current_user = user_data
        
        welcome_text = f"🛠 ТЕСТОВЫЙ РЕЖИМ АКТИВИРОВАН\n\n"
        welcome_text += f"👤 Вы вошли как: {current_user['full_name']}\n"
        welcome_text += f"📱 Telegram: {current_user.get('telegram_username', 'Не указан')}\n"
        welcome_text += f"🎯 Роль: {'Управляющий состав' if current_user['role'] == 'admin' else 'Преподавательский состав'}\n"
        
        if current_user['role'] == 'teacher':
            welcome_text += f"📚 Дисциплины: {', '.join(current_user['subjects'])}\n\n"
            welcome_text += "📋 Доступные вам отчеты:\n"
            welcome_text += "• 📚 Отчет по темам занятия\n"
            welcome_text += "• ✅ Отчет по посещаемости студентов\n"
            welcome_text += "• 📝 Отчет по проверенным дз\n\n"
        else:
            welcome_text += "\n📋 У вас есть доступ ко всем отчетам.\n\n"
        
        welcome_text += "⚠️ Внимание: Вы находитесь в тестовом режиме.\n"
        welcome_text += "Выберите вид отчета из меню ниже:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        return MENU
        
    elif choice == "🔄 Выбрать другого пользователя":
        await update.message.reply_text(
            "Введите username для тестирования:\n\n" +
            "\n".join([f"• {username} - {data['full_name']}" for username, data in PREDEFINED_USERS.items()])
        )
        return MANUAL_AUTH_USERNAME
        
    elif choice == "❌ Отмена":
        await update.message.reply_text("Ручная авторизация отменена.")
        return ConversationHandler.END
        
    else:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных вариантов.")
        return MANUAL_AUTH_ROLE

async def handle_report_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа отчета"""
    global current_report_type, current_user
    
    user_choice = update.message.text
    reports = {
        "📅 Отчет по выставленному расписанию": "schedule",
        "📚 Отчет по темам занятия": "topics",
        "👥 Отчет по студентам": "students",
        "✅ Отчет по посещаемости студентов": "attendance",
        "📝 Отчет по проверенным дз": "checked_hw",
        "📊 Отчет по сданным дз": "submitted_hw"
    }
    
    if user_choice in reports:
        report_type = reports[user_choice]
        
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
    global uploaded_file_path, report_result, current_user
    
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
    
    file = await document.get_file()
    uploaded_file_path = f"downloads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
    await file.download_to_drive(uploaded_file_path)
    
    await update.message.reply_text(
        f"✅ Файл '{file_name}' успешно загружен!\n\n"
        f"Обрабатываю данные...",
        reply_markup=reply_markup
    )
    
    try:
        if current_report_type == "submitted_hw":
            hw_period = context.user_data.get('hw_period', 'all_time')
            report_result = process_excel_file(uploaded_file_path, current_report_type, hw_period, current_user)
        elif current_report_type == "checked_hw":
            hw_check_period = context.user_data.get('hw_check_period', 'month')
            report_result = process_excel_file(uploaded_file_path, current_report_type, hw_check_period, current_user)
        else:
            report_result = process_excel_file(uploaded_file_path, current_report_type, None, current_user)
        
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
        await update.message.reply_text(
            f"❌ Ошибка обработки файла: {str(e)}\n\n"
            f"Проверьте формат файла и попробуйте еще раз.",
            reply_markup=reply_markup
        )
        return MENU

def process_excel_file(file_path, report_type, period=None, user=None):
    """Обрабатывает Excel-фильтр в зависимости от типа отчета и пользователя"""
    
    try:
        df = pd.read_excel(file_path)
        
        if user and user['role'] == 'teacher':
            df = filter_data_for_teacher(df, report_type, user)
        
        if report_type == "schedule":
            return process_schedule(df)
        elif report_type == "topics":
            return process_topics(df, user)
        elif report_type == "students":
            return process_students(df)
        elif report_type == "attendance":
            return process_attendance(df, user)
        elif report_type == "checked_hw":
            return process_checked_hw(df, period, user)
        elif report_type == "submitted_hw":
            return process_submitted_hw(df, period)
        else:
            return "Неизвестный тип отчета"
            
    except Exception as e:
        return f"Ошибка чтения файла: {str(e)}"

def filter_data_for_teacher(df, report_type, user):
    """Фильтрует данные для преподавателя по его дисциплинам или имени"""
    
    if report_type == "topics":
        if 'Предмет' in df.columns:
            df['Предмет_clean'] = df['Предмет'].astype(str).str.strip().str.lower()
            user_subjects = [s.strip().lower() for s in user['subjects']]
            df = df[df['Предмет_clean'].isin(user_subjects)]
    
    elif report_type == "attendance":
        if 'ФИО преподавателя' in df.columns:
            df = df[df['ФИО преподавателя'] == user['full_name']]
    
    elif report_type == "checked_hw":
        if 'ФИО преподавателя' in df.columns:
            df = df[df['ФИО преподавателя'] == user['full_name']]
    
    return df

# 1. Отчет по расписанию
def process_schedule(df):
    """Считает количество пар по каждой дисциплине для каждой группы"""
    result = "📅 ОТЧЕТ ПО ВЫСТАВЛЕННОМУ РАСПИСАНИЮ\n"
    
    if 'Группа' in df.columns:
        df['Группа'] = df['Группа'].ffill()
    
    groups = df['Группа'].dropna().unique()
    
    result += f"Всего групп в расписании: {len(groups)}\n\n"
    
    for group in groups:
        result += f"{'═' * 40}\n"
        result += f"ГРУППА: {group}\n"
        result += f"{'═' * 40}\n"
        
        group_data = df[df['Группа'] == group]
        discipline_counts = {}
        for col in df.columns:
            if any(day in col for day in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']):
                for cell in group_data[col]:
                    if pd.isna(cell) or cell == '' or str(cell).strip() == '':
                        continue
                    
                    cell_str = str(cell)
                    if 'Предмет:' in cell_str:
                        lines = cell_str.split('\n')
                        for line in lines:
                            if line.startswith('Предмет:'):
                                discipline = line.replace('Предмет:', '').strip()
                                if '<br>' in discipline:
                                    discipline = discipline.split('<br>')[0]
                                discipline_counts[discipline] = discipline_counts.get(discipline, 0) + 1
                                break
        
        if discipline_counts:
            total_pairs = sum(discipline_counts.values())
            
            result += f"Всего пар в неделю: {total_pairs}\n\n"
            
            result += "Количество пар по дисциплинам:\n"
            sorted_disciplines = sorted(discipline_counts.items(), key=lambda x: x[1], reverse=True)
            
            for discipline, count in sorted_disciplines:
                result += f"  • {discipline}: {count} пар\n"
        else:
            result += "Нет запланированных пар на эту неделю.\n"
        
        result += "\n"
    
    if len(groups) == 0:
        result += "Группы не найдены в файле.\n"
        result += "Попытка найти пары по всей таблице:\n"
        
        for col in df.columns:
            if any(day in col for day in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']):
                for cell in df[col]:
                    if pd.isna(cell) or cell == '':
                        continue
                    
                    cell_str = str(cell)
                    if 'Предмет:' in cell_str:
                        lines = cell_str.split('\n')
                        for line in lines:
                            if line.startswith('Предмет:'):
                                discipline = line.replace('Предмет:', '').strip()
                                discipline_counts[discipline] = discipline_counts.get(discipline, 0) + 1
                                break
        
        if discipline_counts:
            total_pairs = sum(discipline_counts.values())
            result += f"Всего пар найдено: {total_pairs}\n"
            result += f"Уникальных дисциплин: {len(discipline_counts)}\n\n"
            
            for discipline, count in sorted(discipline_counts.items(), key=lambda x: x[1], reverse=True):
                result += f"  • {discipline}: {count} пар\n"
        else:
            result += "Данные о занятиях не найдены.\n"
            result += f"Доступные колонки: {', '.join(df.columns)}\n"
            result += "Пример структуры: колонки с названиями дней недели содержат данные о занятиях"
    
    return result

# 2. Отчет по темам занятия
def process_topics(df, user=None):
    """Проверяет формат тем занятий"""
    result = "📚 ОТЧЕТ ПО ТЕМАМ ЗАНЯТИЙ\n"
    
    if user:
        if user.get('is_test_mode'):
            result += "🛠 ТЕСТОВЫЙ РЕЖИМ\n"
        result += f"Преподаватель: {user['full_name']}\n"
        result += f"Telegram: {user.get('telegram_username', 'Не указан')}\n"
        result += f"Дисциплины: {', '.join(user['subjects'])}\n\n"
    
    if 'Тема урока' in df.columns:
        correct_format = []
        incorrect_format = []
        
        for idx, topic in enumerate(df['Тема урока'].dropna(), 1):
            if isinstance(topic, str) and topic.startswith("Урок №") and ". Тема:" in topic:
                correct_format.append(f"  {idx}. {topic}")
            else:
                incorrect_format.append(f"  {idx}. {topic}")
        
        result += f"Всего тем: {len(df['Тема урока'].dropna())}\n"
        result += f"Корректных тем: {len(correct_format)}\n"
        result += f"Некорректных тем: {len(incorrect_format)}\n\n"
        
        if incorrect_format:
            result += "❌ Темы с некорректным форматом:\n"
            result += "\n".join(incorrect_format[:len(incorrect_format)])
    else:
        result += "В файле нет колонки 'Тема урока'.\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
    
    return result

# 3. Отчет по студентам
def process_students(df):
    """Находит студентов с низкими оценками"""
    result = "👥 ОТЧЕТ ПО СТУДЕНТАМ\n"
    
    required_cols = ['FIO', 'Группа', 'Homework', 'Classroom']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        result += f"Не хватает колонок: {', '.join(missing_cols)}\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
        return result
    
    df['Homework'] = pd.to_numeric(df['Homework'], errors='coerce')
    df['Classroom'] = pd.to_numeric(df['Classroom'], errors='coerce')
    
    filtered_students = df[
        (df['Homework'] <= 1) & 
        (df['Classroom'] <= 3)
    ]
    
    result += f"Всего студентов: {len(df)}\n"
    result += f"Найдено студентов по критериям: {len(filtered_students)}\n\n"
    
    if len(filtered_students) > 0:
        result += "📋 Список студентов:\n"
        for _, row in filtered_students.iterrows():
            result += f"\n👤 Студент: {row['FIO']}\n"
            result += f"   • Средняя оценка за ДЗ: {row['Homework']}\n"
            result += f"   • Оценка за классную работу: {row['Classroom']}"
    else:
        result += "✅ Нет студентов, соответствующих критериям."
    
    return result

# 4. Отчет по посещаемости
def process_attendance(df, user=None):
    """Находит преподавателей с низкой посещаемостью"""
    result = "✅ ОТЧЕТ ПО ПОСЕЩАЕМОСТИ СТУДЕНТОВ\n"
    
    if user:
        if user.get('is_test_mode'):
            result += "🛠 ТЕСТОВЫЙ РЕЖИМ\n"
        result += f"Преподаватель: {user['full_name']}\n"
        result += f"Telegram: {user.get('telegram_username', 'Не указан')}\n\n"
    
    if 'ФИО преподавателя' in df.columns and 'Средняя посещаемость' in df.columns:
        def parse_percentage(value):
            if pd.isna(value):
                return None
            if isinstance(value, str):
                cleaned = value.strip().replace('%', '').replace(',', '.')
                try:
                    return float(cleaned)
                except ValueError:
                    return None
            elif isinstance(value, (int, float)):
                return float(value)
            return None
        
        df['Посещаемость_число'] = df['Средняя посещаемость'].apply(parse_percentage)
        
        low_attendance = df[df['Посещаемость_число'] < 40]
        
        result += f"Всего преподавателей в отчете: {len(df)}\n"
        result += f"С посещаемостью ниже 40%: {len(low_attendance)}\n\n"
        
        missing_values = df['Посещаемость_число'].isna().sum()
        if missing_values > 0:
            result += f"⚠️ Некорректных значений: {missing_values}\n\n"
        
        if len(low_attendance) > 0:
            result += "📋 Преподаватели с низкой посещаемостью:\n"
            for _, row in low_attendance.iterrows():
                result += f"\n👨‍🏫 {row['ФИО преподавателя']}\n"
                orig_value = row['Средняя посещаемость']
                if isinstance(orig_value, str):
                    result += f"   • Посещаемость: {orig_value.strip()}"
                else:
                    result += f"   • Посещаемость: {orig_value}%"
        else:
            result += "✅ Все преподаватели имеют посещаемость выше 40%."
    else:
        result += "Необходимы колонки: 'ФИО преподавателя', 'Средняя посещаемость'\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
    
    return result

def process_checked_hw(df, period='month', user=None):
    """Находит преподавателей с низким процентом проверки ДЗ за выбранный период"""
    result = "📝 ОТЧЕТ ПО ПРОВЕРЕННЫМ ДЗ\n"
    
    if user:
        if user.get('is_test_mode'):
            result += "🛠 ТЕСТОВЫЙ РЕЖИМ\n"
        result += f"Преподаватель: {user['full_name']}\n"
        result += f"Telegram: {user.get('telegram_username', 'Не указан')}\n"
    
    if period == 'month':
        result += "Период: за месяц\n\n"
        target_section = 'Месяц'
    else:
        result += "Период: за неделю\n\n"
        target_section = 'Неделя'
    
    if 'ФИО преподавателя' not in df.columns:
        result += "❌ Не найдена колонка 'ФИО преподавателя'.\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
        return result
    
    df = df.rename(columns={'ФИО преподавателя': 'ФИО'})
    
    section_start_idx = None
    
    for i, col in enumerate(df.columns):
        if str(col).strip() == target_section:
            section_start_idx = i
            break
    
    if section_start_idx is None:
        result += f"❌ Не найдена секция '{target_section}' в таблице.\n"
        result += f"Доступные колонки: {', '.join(df.columns[:10])}..."
        return result
    
    received_idx = section_start_idx + 2  
    checked_idx = section_start_idx + 3   
    
    if checked_idx >= len(df.columns):
        result += f"❌ Неправильная структура таблицы для секции '{target_section}'.\n"
        result += f"Всего колонок: {len(df.columns)}, нужен индекс {checked_idx}"
        return result
    
    received_col = df.columns[received_idx]
    checked_col = df.columns[checked_idx]
    
    new_received_col = f'Получено_{period}'
    new_checked_col = f'Проверено_{period}'
    
    df = df.rename(columns={
        received_col: new_received_col,
        checked_col: new_checked_col
    })
    
    for col in [new_received_col, new_checked_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['Процент'] = 0.0
    mask = df[new_received_col] > 0
    df.loc[mask, 'Процент'] = (df[new_checked_col] / df[new_received_col]) * 100
    
    mask_low = df['Процент'] < 70
    low_checking = df[mask_low].copy()
    
    low_checking = low_checking[low_checking['ФИО'].notna() & (low_checking['ФИО'] != '')]
    
    df_valid = df[df['ФИО'].notna() & (df['ФИО'] != '')]
    
    result += f"Всего преподавателей в отчете: {len(df_valid)}\n"
    result += f"С процентом проверки ниже 70%: {len(low_checking)}\n\n"
    
    if len(low_checking) > 0:
        result += "📋 Преподаватели с низким процентом проверки:\n"
        result += "-" * 50 + "\n"
        
        for _, row in low_checking.iterrows():
            result += f"\n👨‍🏫 {row['ФИО']}\n"
            
            if pd.isna(row[new_received_col]) or row[new_received_col] == 0:
                result += f"   • Нет данных\n"
            else:
                result += f"   • Проверено: {row['Процент']:.1f}% ({row[new_checked_col]:.0f} из {row[new_received_col]:.0f})\n"
    else:
        result += "✅ Все преподаватели проверяют более 70% ДЗ.\n"
    
    return result

# 6. Отчет по сданным ДЗ
def process_submitted_hw(df, period='all_time'):
    """Находит студентов с низким процентом сданных ДЗ"""
    result = "📊 ОТЧЕТ ПО СДАННЫМ ДЗ\n"
    
    all_columns = df.columns.tolist()
    
    if period == 'all_time':
        result += "Период: за все время\n"
        percentage_columns = [col for col in all_columns if 'Percentage' in str(col) and 'Homework' in str(col)]
        
        if len(percentage_columns) >= 1:
            hw_column = percentage_columns[0]  
        else:
            hw_column = 'Percentage Homework' 
    else:  
        result += "Период: за последние 30 дней\n"
        percentage_columns = [col for col in all_columns if 'Percentage' in str(col) and 'Homework' in str(col)]
        
        if len(percentage_columns) >= 2:
            hw_column = percentage_columns[1] 
        elif len(percentage_columns) == 1:
            hw_column = percentage_columns[0]
            result += "⚠️ Внимание: найдена только одна колонка с процентами ДЗ\n"
        else:
            hw_column = 'Percentage Homework 30 Days'
    
    result += "=" * 40 + "\n\n"
    
    if hw_column not in df.columns:
        available_cols = ', '.join(df.columns)
        result += f"❌ Не найдена колонка '{hw_column}'\n"
        result += f"Доступные колонки: {available_cols}\n\n"
        
        percentage_columns = [col for col in df.columns if 'Percentage' in str(col) or 'Homework' in str(col)]
        if percentage_columns:
            result += f"Колонки, связанные с ДЗ: {', '.join(percentage_columns)}\n"
        
        result += "\nПодсказка: В файле должны быть колонки с названиями, содержащими 'Percentage' и 'Homework'"
        return result
    
    required_cols = ['FIO', hw_column]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        result += f"Не хватает колонок: {', '.join(missing_cols)}\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
        
        percentage_columns = [col for col in df.columns if 'Percentage' in str(col) or 'Homework' in str(col)]
        if percentage_columns:
            result += f"\nКолонки, связанные с ДЗ: {', '.join(percentage_columns)}"
        
        return result
    
    df[hw_column] = df[hw_column].replace(['-', '—', '–', ' ', ''], pd.NA)
    
    df[hw_column] = pd.to_numeric(df[hw_column], errors='coerce')
    
    df_with_data = df.dropna(subset=[hw_column]).copy()
    
    low_submission = df_with_data[df_with_data[hw_column] < 70]
    
    total_with_data = len(df_with_data)
    
    students_with_dash = len(df) - total_with_data
    
    result += f"Всего студентов в файле: {len(df)}\n"
    result += f"Студентов с данными: {total_with_data}\n"
    
    if students_with_dash > 0:
        result += f"Студентов с прочерком (-): {students_with_dash}\n"
    
    result += f"С процентом сдачи ниже 70%: {len(low_submission)}\n\n"
    
    if len(low_submission) > 0:
        if len(low_submission) == total_with_data and total_with_data > 0:
            result += "❌ Все студенты сдали меньше 70% ДЗ.\n"
        else:
            result += "📋 Студенты с низким процентом сдачи:\n"
            for _, row in low_submission.iterrows():
                result += f"\n👤 {row['FIO']}\n"
                result += f"   • Процент сдачи: {row[hw_column]:.1f}%"
            
            if students_with_dash > 0:
                students_with_dash_list = df[df[hw_column].isna()]
                result += f"\n\n⚠️ Студенты с прочерком (-) в данных ({students_with_dash} чел.):\n"
                for _, row in students_with_dash_list.iterrows():
                    result += f"\n👤 {row['FIO']} (нет данных)"
    else:
        if total_with_data == 0:
            result += "❌ Нет данных для анализа (все значения - прочерки или отсутствуют).\n"
        else:
            result += "✅ Все студенты сдают более 70% ДЗ.\n"
            if students_with_dash > 0:
                students_with_dash_list = df[df[hw_column].isna()]
                result += f"\n⚠️ Студенты с прочерком (-) в данных ({students_with_dash} чел.):\n"
                for _, row in students_with_dash_list.iterrows():
                    result += f"\n👤 {row['FIO']} (нет данных)"
    
    return result

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет справку по использованию бота"""
    global current_user
    
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
        else:
            help_text += "  • 📚 Отчет по темам занятия\n"
            help_text += "  • ✅ Отчет по посещаемости студентов\n"
            help_text += "  • 📝 Отчет по проверенным дз\n"
    
    help_text += """
    
    📊 Доступные отчеты:
    • 📅 Расписание - количество пар по дисциплинам
    • 📚 Темы занятий - проверка формата тем
    • 👥 Студенты - фильтрация по оценкам
    • ✅ Посещаемость - преподаватели с низкой посещаемостью
    • 📝 Проверка ДЗ - преподаватели с низким % проверки (за месяц или неделю)
    • 📊 Сдача ДЗ - студенты с низким % сдачи (за все время или 30 дней)
    
    /start - Вернуться в главное меню
    """
    
    await update.message.reply_text(help_text, reply_markup=reply_markup)
    return MENU

async def handle_output_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор формата вывода результата"""
    query = update.callback_query
    await query.answer()
    
    global report_result, uploaded_file_path
    
    if query.data == "output_text":
        if len(report_result) > 4000:
            for i in range(0, len(report_result), 4000):
                await query.message.reply_text(report_result[i:i+4000])
        else:
            await query.message.reply_text(report_result)
    
    elif query.data == "output_file":
        os.makedirs("reports", exist_ok=True)
        report_filename = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_result)
        
        with open(report_filename, 'rb') as f:
            await query.message.reply_document(
                document=f,
                filename=f"отчет_{current_report_type}.txt",
                caption="📎 Ваш отчет в файле .txt"
            )
    
    await query.message.reply_text(
        "Выберите следующий отчет из меню:",
        reply_markup=reply_markup
    )
    return MENU

def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTH_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auth_choice)],
            MANUAL_AUTH_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_auth_username)],
            MANUAL_AUTH_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_auth_role)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_selection)],
            CHOOSE_HW_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hw_type_selection)],
            CHOOSE_HW_CHECK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hw_check_type_selection)],
            WAITING_FILE: [MessageHandler(filters.Document.ALL, handle_document)],
            CHOOSE_OUTPUT: [CallbackQueryHandler(handle_output_choice)],
        },
        fallbacks=[],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    main()