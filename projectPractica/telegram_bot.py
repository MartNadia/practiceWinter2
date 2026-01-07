import logging
import pandas as pd
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MENU, WAITING_FILE, CHOOSE_OUTPUT = range(3)

TOKEN = "8211522202:AAH8XRQVCsQBcwk7R23t9RCzTs5_e_ukNsw"

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение и меню"""
    user = update.effective_user
    welcome_text = f"Привет, {user.first_name}! \n\nЯ бот для учебной части.\nВыберите вид отчета из меню ниже:"
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return MENU

async def handle_report_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа отчета"""
    global current_report_type
    
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
        current_report_type = reports[user_choice]
        
        instructions = {
            #Сделано 2, 3, 4
            "schedule": "📤 Пожалуйста, загрузите Excel-файл с расписанием группы на неделю.",
            "topics": "📤 Пожалуйста, загрузите Excel-файл с темами занятий.\n\nТемы должны быть в формате: 'Урок № _. Тема: _'",
            "students": "📤 Пожалуйста, загрузите Excel-файл с информацией по студентам.",
            "attendance": "📤 Пожалуйста, загрузите Excel-файл с посещаемостью.",
            "checked_hw": "📤 Пожалуйста, загрузите Excel-файл с проверкой ДЗ.",
            "submitted_hw": "📤 Пожалуйста, загрузите Excel-файл со сданными ДЗ."
        }
        
        await update.message.reply_text(
            f"Вы выбрали: {user_choice}\n\n{instructions[current_report_type]}\n\n"
            f"Отправьте файл .xls или .xlsx как документ (скрепка 📎)."
        )
        return WAITING_FILE
    
    elif user_choice == "ℹ️ Помощь":
        return await help_command(update, context)
    
    else:
        await update.message.reply_text(
            f"Неизвестная команда. Используйте меню.",
            reply_markup=reply_markup
        )
        return MENU

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает загрузку Excel-файлов"""
    global uploaded_file_path, report_result
    
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
        report_result = process_excel_file(uploaded_file_path, current_report_type)
        
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

def process_excel_file(file_path, report_type):
    """Обрабатывает Excel-файл в зависимости от типа отчета"""
    
    try:
        df = pd.read_excel(file_path)
        
        if report_type == "schedule":
            return process_schedule(df)
        elif report_type == "topics":
            return process_topics(df)
        elif report_type == "students":
            return process_students(df)
        elif report_type == "attendance":
            return process_attendance(df)
        elif report_type == "checked_hw":
            return process_checked_hw(df)
        elif report_type == "submitted_hw":
            return process_submitted_hw(df)
        else:
            return "Неизвестный тип отчета"
            
    except Exception as e:
        return f"Ошибка чтения файла: {str(e)}"

# 1. Отчет по расписанию
def process_schedule(df):
    """Считает количество пар по каждой дисциплине"""
    result = "📅 ОТЧЕТ ПО РАСПИСАНИЮ\n"
    result += "=" * 40 + "\n\n"

# 2. Отчет по темам занятия
def process_topics(df):
    """Проверяет формат тем занятий"""
    result = "📚 ОТЧЕТ ПО ТЕМАМ ЗАНЯТИЙ\n"
    result += "=" * 40 + "\n\n"
    
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
        result += "В файле нет колонки 'Тема'.\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
    
    return result

# 3. Отчет по студентам
def process_students(df):
    """Находит студентов с низкими оценками"""
    result = "👥 ОТЧЕТ ПО СТУДЕНТАМ\n"
    result += "=" * 40 + "\n\n"
    
    required_cols = ['FIO', 'Группа', 'Homework', 'Classroom']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        result += f"Не хватает колонок: {', '.join(missing_cols)}\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
        return result
    
    # Конвертируем в числовые типы
    df['Homework'] = pd.to_numeric(df['Homework'], errors='coerce')
    df['Classroom'] = pd.to_numeric(df['Classroom'], errors='coerce')
    
    # Фильтруем студентов
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
def process_attendance(df):
    """Находит преподавателей с низкой посещаемостью"""
    result = "✅ ОТЧЕТ ПО ПОСЕЩАЕМОСТИ СТУДЕНТОВ\n"
    result += "=" * 40 + "\n\n"
    
    if 'ФИО преподавателя' in df.columns and 'Средняя посещаемость' in df.columns:
        # Функция для преобразования строки с % в число
        def parse_percentage(value):
            if pd.isna(value):
                return None
            # Если это строка
            if isinstance(value, str):
                # Убираем пробелы и символ %
                cleaned = value.strip().replace('%', '').replace(',', '.')
                try:
                    # Пытаемся преобразовать в число
                    return float(cleaned)
                except ValueError:
                    return None
            # Если уже число
            elif isinstance(value, (int, float)):
                return float(value)
            return None
        
        # Применяем функцию ко всей колонке
        df['Посещаемость_число'] = df['Средняя посещаемость'].apply(parse_percentage)
        
        # Фильтруем по значениям меньше 40
        low_attendance = df[df['Посещаемость_число'] < 40]
        
        result += f"Всего преподавателей: {len(df)}\n"
        result += f"С посещаемостью ниже 40%: {len(low_attendance)}\n\n"
        
        # Статистика по пропущенным значениям
        missing_values = df['Посещаемость_число'].isna().sum()
        if missing_values > 0:
            result += f"⚠️ Некорректных значений: {missing_values}\n\n"
        
        if len(low_attendance) > 0:
            result += "📋 Преподаватели с низкой посещаемостью:\n"
            for _, row in low_attendance.iterrows():
                result += f"\n👨‍🏫 {row['ФИО преподавателя']}\n"
                # Показываем оригинальное значение из колонки
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

# 5. Отчет по проверенным ДЗ
def process_checked_hw(df):
    """Находит преподавателей с низким процентом проверки ДЗ"""
    result = "📝 ОТЧЕТ ПО ПРОВЕРЕННЫМ ДЗ\n"
    result += "=" * 40 + "\n\n"

# 6. Отчет по сданным ДЗ
def process_submitted_hw(df):
    """Находит студентов с низким процентом сданных ДЗ"""
    result = "📊 ОТЧЕТ ПО СДАННЫМ ДЗ\n"
    result += "=" * 40 + "\n\n"
    

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет справку по использованию бота"""
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
    
    📊 Доступные отчеты:
    • 📅 Расписание - количество пар по дисциплинам
    • 📚 Темы занятий - проверка формата тем
    • 👥 Студенты - фильтрация по оценкам
    • ✅ Посещаемость - преподаватели с низкой посещаемостью
    • 📝 Проверка ДЗ - преподаватели с низким % проверки
    • 📊 Сдача ДЗ - студенты с низким % сдачи
    
    /start - Вернуться в главное меню
    """
    
    await update.message.reply_text(help_text, reply_markup=reply_markup)
    return MENU

def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_selection)],
            WAITING_FILE: [MessageHandler(filters.Document.ALL, handle_document)],
            CHOOSE_OUTPUT: [CallbackQueryHandler(handle_output_choice)]
        },
        fallbacks=[CommandHandler("help", help_command), CommandHandler("start", start)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':

    os.makedirs("downloads", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    
    main()