import logging
from telegram import ReplyKeyboardMarkup

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8211522202:AAH8XRQVCsQBcwk7R23t9RCzTs5_e_ukNsw"

USERS_FILE = "users.json"

AUTH_CHOICE, MANUAL_AUTH_USERNAME, MANUAL_AUTH_ROLE, TEST_MODE, MENU, WAITING_FILE, CHOOSE_HW_TYPE, CHOOSE_HW_CHECK_TYPE, CHOOSE_OUTPUT = range(9)

PREDEFINED_USERS = {
    "admin1": {
        "telegram_username": "@KaterinaRyabkova",
        "full_name": "Рябкова Екатерина -",
        "role": "admin",
        "is_predefined": True
    },
    "admin2": {
        "telegram_username": "@balakhnina",
        "full_name": "Балахина Ксения -",
        "role": "admin",
        "is_predefined": True
    },
    "admin3": {
        "telegram_username": "@JuliaaChernova",
        "full_name": "Чернова Юлия Андреевна",
        "role": "admin",
        "is_predefined": True
    },
    
    "teacher_1": {
        "telegram_username": "@Mazero_T",
        "full_name": "Мазеро Тинаше",
        "subjects": ["Иностранный язык в профессиональной деятельности РПО", "Иностранный язык в профессиональной деятельности ГД"],
        "role": "teacher",
        "is_predefined": True
    },
    "teacher_2": {
        "telegram_username": "@lekalukyanova",
        "full_name": "Лукьянова Елена Сергеевна",
        "subjects": ["Менеджмент и экономические основы рекламной деятельности ИМ","Правовое обеспечение рекламной деятельности ИМ","Маркетинг в рекламе ИМ","Рекламная деятельность ИМ","Правовое обеспечение профессиональной деятельности ИМ"],
        "role": "teacher",
        "is_predefined": True
    }
}

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