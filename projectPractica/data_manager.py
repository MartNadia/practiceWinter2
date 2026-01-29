import json
import os
from bot_config import USERS_FILE, logger

def load_users():
    """Загружает пользователей из файла"""
    users = {}
    
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            for username, data in users.items():
                if 'is_predefined' not in data:
                    data['is_predefined'] = True
                    
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
            return {}
    else:
        logger.warning(f"Файл пользователей {USERS_FILE} не найден. Создайте файл users.json с пользователями.")
    
    return users

def save_users(users):
    """Сохраняет всех пользователей в файл"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        logger.info(f"Пользователи успешно сохранены в {USERS_FILE}")
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователей: {e}")

def add_user(username, user_data):
    """Добавляет нового пользователя"""
    users = load_users()
    
    if username in users:
        return False, "Пользователь с таким username уже существует"
    
    user_data['is_predefined'] = False
    users[username] = user_data
    save_users(users)
    
    return True, "Пользователь успешно добавлен"

def remove_user(username):
    """Удаляет пользователя (только не предустановленного)"""
    users = load_users()
    
    if username not in users:
        return False, "Пользователь не найден"
    
    if users[username].get('is_predefined', True):
        return False, "Нельзя удалить предустановленного пользователя"
    
    del users[username]
    save_users(users)
    
    return True, "Пользователь успешно удален"

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
    
    if user_role == "admin":
        return True
    
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