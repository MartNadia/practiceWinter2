import logging
import os
from telegram import ReplyKeyboardMarkup

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8211522202:AAH8XRQVCsQBcwk7R23t9RCzTs5_e_ukNsw"

AUTH_CHOICE, MANUAL_AUTH_USERNAME, MANUAL_AUTH_ROLE, TEST_MODE, MENU, WAITING_FILE, CHOOSE_HW_TYPE, CHOOSE_HW_CHECK_TYPE, CHOOSE_OUTPUT, ADMIN_MENU, ADD_USER, REMOVE_USER = range(12)

USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    try:
        import json
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        logger.info(f"Создан пустой файл пользователей: {USERS_FILE}")
    except Exception as e:
        logger.error(f"Ошибка создания файла пользователей: {e}")

menu_keyboard = [
    ["📅 Отчет по выставленному расписанию"],
    ["📚 Отчет по темам занятия"],
    ["👥 Отчет по студентам"],
    ["✅ Отчет по посещаемости студентов"],
    ["📝 Отчет по проверенным дз"],
    ["📊 Отчет по сданным дз"],
    ["👥 Управление пользователями"],
    ["ℹ️ Помощь"]
]

reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

REPORT_MAPPING = {
    "📅 Отчет по выставленному расписанию": "schedule",
    "📚 Отчет по темам занятия": "topics",
    "👥 Отчет по студентам": "students",
    "✅ Отчет по посещаемости студентов": "attendance",
    "📝 Отчет по проверенным дз": "checked_hw",
    "📊 Отчет по сданным дз": "submitted_hw"
}

REPORT_NAMES = {
    "schedule": "📅 Отчет по выставленному расписанию",
    "topics": "📚 Отчет по темам занятия",
    "students": "👥 Отчет по студентам",
    "attendance": "✅ Отчет по посещаемости студентов",
    "checked_hw": "📝 Отчет по проверенным дз",
    "submitted_hw": "📊 Отчет по сданным дз"
}