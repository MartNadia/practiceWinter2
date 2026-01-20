import json
import os
from bot_config import PREDEFINED_USERS, USERS_FILE, logger

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