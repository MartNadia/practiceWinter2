import pandas as pd
from datetime import datetime
from bot_config import logger

current_report_type = None
uploaded_file_path = None
report_result = ""

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
        logger.error(f"Ошибка обработки файла: {e}")
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
    """Проверяет формат тем занятий для авторизованного пользователя"""
    result = "📚 ОТЧЕТ ПО ТЕМАМ ЗАНЯТИЙ\n"
    
    if user:
        if user.get('is_test_mode'):
            result += "🛠 ТЕСТОВЫЙ РЕЖИМ\n"
        is_admin = user.get('role') == 'admin'
        
        if is_admin:
            result += "👨‍💼 РЕЖИМ АДМИНИСТРАТОРА\n"
            result += f"Администратор: {user['full_name']}\n"
        else:
            result += f"Преподаватель: {user['full_name']}\n"
        
        if not is_admin and 'subjects' in user and user['subjects']:
            result += f"Дисциплины: {', '.join(user['subjects'])}\n\n"
        else:
            result += "\n"
    
    required_columns = ['Тема урока', 'ФИО преподавателя']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        result += f"❌ В файле отсутствуют необходимые колонки: {', '.join(missing_columns)}\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
        return result
    
    correct_format = []
    incorrect_format = []
    
    # РЕЖИМ АДМИНИСТРАТОРА
    if user and user.get('role') == 'admin':
        for idx, (_, row) in enumerate(df.iterrows(), 1):
            topic = row['Тема урока']
            teacher_name = row['ФИО преподавателя']
            
            if pd.isna(topic):
                continue
                
            if isinstance(topic, str) and topic.startswith("Урок №") and (". Тема:" in topic or ".Тема:" in topic):
                correct_format.append(f"  {idx}. [{teacher_name}] {topic}")
            else:
                incorrect_format.append(f"  {idx}. [{teacher_name}] {topic}")
        
        total_topics = len(df['Тема урока'].dropna())
        result += "📊 СТАТИСТИКА ПО ВСЕМУ ФАЙЛУ:\n"
        result += f"Всего тем в файле: {total_topics}\n"
        result += f"Корректных тем: {len(correct_format)}\n"
        result += f"Некорректных тем: {len(incorrect_format)}\n\n"
        if incorrect_format:
            result += "❌ Некорректные темы всех преподавателей:\n"
            result += "\n".join(incorrect_format[:len(incorrect_format)]) + "\n\n"
        return result
    
    # РЕЖИМ ПРЕПОДАВАТЕЛЯ
    if user:
        teacher_topics = df[df['ФИО преподавателя'] == user['full_name']]
    else:
        teacher_topics = df
    
    for idx, (_, row) in enumerate(teacher_topics.iterrows(), 1):
        topic = row['Тема урока']
        if pd.isna(topic):
            continue
            
        if isinstance(topic, str) and topic.startswith("Урок №") and (". Тема:" in topic or ".Тема:" in topic):
            correct_format.append(f"  {idx}. {topic}")
        else:
            incorrect_format.append(f"  {idx}. {topic}")
    
    total_topics = len(teacher_topics['Тема урока'].dropna())
    result += f"Преподаватель: {user['full_name'] if user else 'Не указан'}\n"
    result += f"Всего тем у преподавателя: {total_topics}\n"
    result += f"Корректных тем: {len(correct_format)}\n"
    result += f"Некорректных тем: {len(incorrect_format)}\n\n"
    
    if incorrect_format:
        result += "❌ Темы с некорректным форматом:\n"
        result += "\n".join(incorrect_format[:len(incorrect_format)]) + "\n\n"
    
    if correct_format:
        result += "✅ Пример корректной темы:\n"
        if len(correct_format) > 0:
            result += correct_format[0] + "\n"
    
    if total_topics == 0 and user:
        result += f"ℹ️ Для преподавателя '{user['full_name'] if user else ''}' не найдено тем занятий.\n"
        result += f"Проверьте, что в колонке 'ФИО преподавателя' указано имя '{user['full_name'] if user else ''}'"
    
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
        result += "Необходимы колонки: 'ФИО преподавателя', 'Средняя посещаемость'\n"
        result += f"Доступные колонки: {', '.join(df.columns)}"
    
    return result

# 5. Отчет по проверенным ДЗ
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