import json
import re
from pprint import pprint

# Функция для определения, входит ли сообщение в высокорисковую категорию по алгоритму pkg_sim_range
def is_high_risk(message):
    # Проверка условий высокого риска согласно алгоритму
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            message = message['row_to_json']
        
        # Проверка для is_abr_high_risk_1
        is_red_1_pl1 = message.get('IS_RED_1_PL1', 0) != 0
        is_red_1_pl2 = message.get('IS_RED_1_PL2', 0) != 0
        oper_idtype = message.get('OPER_IDTYPE')
        oper_idview = message.get('OPER_IDVIEW')
        oper_susp_first = message.get('OPER_SUSP_FIRST')
        oper_dopinfo = message.get('OPER_DOPINFO', '').lower() if message.get('OPER_DOPINFO') else ''
        oper_difficulties = message.get('OPER_DIFFICULTIES', '').lower() if message.get('OPER_DIFFICULTIES') else ''
        oper_tenge_amount = message.get('OPER_TENGE_AMOUNT', 0)
        is_subsoil_users_pl1 = message.get('IS_SUBSOIL_USERS_PL1', 0) == 0
        is_subsoil_users_pl2 = message.get('IS_SUBSOIL_USERS_PL2', 0) == 0
        is_green_1_pl1 = message.get('IS_GREEN_1_PL1', 0) == 0
        is_green_1_pl2 = message.get('IS_GREEN_1_PL2', 0) == 0

        # Проверка условий high_risk_1
        high_risk_1 = (
            (is_red_1_pl1 or is_red_1_pl2) and
            (
                oper_idtype in [119, 413, 561, 661] or
                oper_idview == 911 or
                oper_susp_first in [1057, 1066, 3002] or
                (oper_susp_first == 1058 and oper_idtype not in [423, 421]) or
                'займ' in oper_dopinfo or
                'беспроцент' in oper_dopinfo or
                'без процент' in oper_dopinfo or
                'займ' in oper_difficulties or
                'беспроцент' in oper_difficulties or
                'без процент' in oper_difficulties
            ) and
            oper_tenge_amount >= 200000000 and
            is_subsoil_users_pl1 and is_subsoil_users_pl2 and is_green_1_pl1 and is_green_1_pl2
        )

        # Проверка для is_abr_high_risk_2
        is_red_2_pl1 = message.get('IS_RED_2_PL1', 0) != 0
        is_red_2_pl2 = message.get('IS_RED_2_PL2', 0) != 0

        high_risk_2 = (
            (is_red_2_pl1 or is_red_2_pl2 or oper_susp_first == 1113) and
            oper_tenge_amount >= 200000000 and
            is_subsoil_users_pl1 and is_subsoil_users_pl2 and is_green_1_pl1 and is_green_1_pl2
        )

        # Проверка FT операции высокого риска
        ft_operation = is_ft_operation(message)
        ft_high_risk = is_ft_high_risk(message)
        is_ft_high = ft_operation and ft_high_risk

        # Проверка OD операции высокого риска
        od_operation = is_od_operation(message)
        od_high_risk = is_od_high_risk(message)
        is_od_high = od_operation and od_high_risk

        # Проверка is_piramid_high_risk
        piramid_range = is_piramid_range(message)
        piramid_high_risk = is_piramid_high_risk(message)
        is_piramid_high = piramid_range and piramid_high_risk

        # Возвращаем True, если хотя бы одно из условий высокого риска выполнено
        return high_risk_1 or high_risk_2 or is_ft_high or is_od_high or is_piramid_high
    except Exception as e:
        print(f"Ошибка при определении high_risk: {e}")
        return False

# Проверка на соответствие условиям ФТ операций
def is_ft_operation(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            message = message['row_to_json']
            
        mess_oper_status = message.get('MESS_OPER_STATUS')
        mess_reason_code = message.get('MESS_REASON_CODE')
        return mess_oper_status == 1 and mess_reason_code in [4, 10]
    except Exception as e:
        print(f"Ошибка при определении is_ft_operation: {e}")
        return False

# Проверка на высокий риск для ФТ операций
def is_ft_high_risk(message):
    # В реальном коде здесь должна быть реализация проверки 
    # на основе алгоритма pkg_sim_range
    # Для примера возвращаем False
    return False

# Проверка на соответствие условиям ОД операций
def is_od_operation(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            message = message['row_to_json']
            
        mess_oper_status = message.get('MESS_OPER_STATUS')
        mess_reason_code = message.get('MESS_REASON_CODE')
        return mess_oper_status == 1 and mess_reason_code in [1, 2, 8]
    except Exception as e:
        print(f"Ошибка при определении is_od_operation: {e}")
        return False

# Проверка на высокий риск для ОД операций
def is_od_high_risk(message):
    # В реальном коде здесь должна быть реализация проверки 
    # на основе алгоритма pkg_sim_range
    # Для примера возвращаем False
    return False

# Проверка на соответствие условиям финансовой пирамиды
def is_piramid_range(message):
    # В реальном коде здесь должна быть реализация проверки 
    # на основе алгоритма pkg_sim_range
    # Для примера возвращаем False
    return False

# Проверка на высокий риск для финансовой пирамиды
def is_piramid_high_risk(message):
    # В реальном коде здесь должна быть реализация проверки 
    # на основе алгоритма pkg_sim_range
    # Для примера возвращаем False
    return False

# Проверка на соответствие условиям ранжирования ABR
def is_abr_range(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            message = message['row_to_json']
            
        mess_oper_status = message.get('MESS_OPER_STATUS')
        mess_reason_code = message.get('MESS_REASON_CODE')
        cfm_code = message.get('CFM_CODE')
        member_id_pl1 = message.get('MEMBER_ID_PL1')
        member_residence_pl1 = message.get('MEMBER_RESIDENCE_PL1')
        member_id_pl2 = message.get('MEMBER_ID_PL2')
        member_residence_pl2 = message.get('MEMBER_RESIDENCE_PL2')
        member_id_pol1 = message.get('MEMBER_ID_POL1')
        member_bank_address_pol1 = message.get('MEMBER_BANK_ADDRESS_POL1')
        member_id_pol2 = message.get('MEMBER_ID_POL2')
        member_bank_address_pol2 = message.get('MEMBER_BANK_ADDRESS_POL2')
        member_bank_address_pl1 = message.get('MEMBER_BANK_ADDRESS_PL1')
        member_bank_address_pl2 = message.get('MEMBER_BANK_ADDRESS_PL2')
        receive_date = message.get('RECEIVE_DATE')
        oper_trans_date = message.get('OPER_TRANS_DATE')
        
        # В реальном коде нужно преобразовать даты из строк в объекты datetime
        # и вычислить разницу в днях
        # Для примера считаем, что разница меньше 15 дней
        date_diff_ok = True
        
        return (
            mess_oper_status == 1 and
            mess_reason_code in [1, 2, 8, 10] and
            cfm_code == 11 and
            ((member_id_pl1 is not None and member_residence_pl1 == 398) or 
             (member_id_pl2 is not None and member_residence_pl2 == 398)) and
            ((member_id_pol1 is not None and member_bank_address_pol1 != 398) or 
             (member_id_pol2 is not None and member_bank_address_pol2 != 398)) and
            ((member_id_pl1 is not None and member_bank_address_pl1 == 398) or 
             (member_id_pl2 is not None and member_bank_address_pl2 == 398)) and
            date_diff_ok
        )
    except Exception as e:
        print(f"Ошибка при определении is_abr_range: {e}")
        return False

# Проверка на неранжируемость ABR
def is_abr_not_range(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            message = message['row_to_json']
            
        oper_dopinfo = message.get('OPER_DOPINFO', '').lower() if message.get('OPER_DOPINFO') else ''
        
        # Упрощенная проверка на основе нескольких шаблонов
        patterns = [
            r'клиент.*подписал договор',
            r'неисполненные обязательства',
            r'не совершено',
            r'лкбк.*(задолженност|неисполнением обязательств)',
            r'принят.*репатриац.*(договор|контракт)',
            r'банком направлено уведомление о нарушен',
            r'банком были направлены уведомления о нарушен',
            r'банком направлены уведомления о нарушен',
            r'в поле 3.7 сумма в тенге указана на дату заключения договора.*(исходящ|входящ)',
            r'продление срока репатриации',
            r'увеличение срока репатриации'
        ]
        
        for pattern in patterns:
            if re.search(pattern, oper_dopinfo):
                return True
                
        return False
    except Exception as e:
        print(f"Ошибка при определении is_abr_not_range: {e}")
        return False

# Функция для извлечения ключевых полей из сообщения
def extract_key_fields(message):
    # Если в сообщении есть вложенный row_to_json, используем его
    if 'row_to_json' in message:
        message = message['row_to_json']
    
    keys = [
        'MESS_ID', 'MESS_OPER_STATUS', 'MESS_REASON_CODE', 'CFM_CODE',
        'OPER_IDTYPE', 'OPER_IDVIEW', 'OPER_SUSP_FIRST',
        'OPER_TENGE_AMOUNT', 'OPER_CURRENCY_AMOUNT', 
        'MEMBER_RESIDENCE_PL1', 'MEMBER_BANK_ADDRESS_POL1'
    ]
    
    result = {}
    for key in keys:
        if key in message:
            result[key] = message[key]
            
    # Добавляем текстовые поля с ограничением длины
    text_fields = ['OPER_DOPINFO', 'OPER_DIFFICULTIES', 'MEMBER_NAME_PL1', 'MEMBER_NAME_POL1']
    for field in text_fields:
        if field in message and message[field]:
            value = message[field]
            if len(value) > 100:
                result[field] = value[:100] + "..."
            else:
                result[field] = value
    
    return result

def process_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            # Если это массив сообщений
            if isinstance(data, list):
                messages = data
            # Если это объект с массивом внутри
            elif isinstance(data, dict) and 'messages' in data:
                messages = data['messages']
            else:
                messages = [data]  # Возможно, это одно сообщение
            
            print(f"Всего сообщений: {len(messages)}")
            
            # Анализ структуры сообщений
            print("\nАнализ структуры JSON:")
            if len(messages) > 0:
                # Проверим структуру первого сообщения
                first_msg = messages[0]
                print(f"Первое сообщение: {first_msg}")
                
                # Если в сообщении есть поле row_to_json, выведем его ключи
                if 'row_to_json' in first_msg:
                    row_json = first_msg['row_to_json']
                    if isinstance(row_json, dict):
                        print(f"Ключи в row_to_json: {', '.join(sorted(row_json.keys()))}")
                    else:
                        print(f"row_to_json не является словарем: {type(row_json)}")
                
                # Собираем все уникальные ключи в сообщениях
                keys = set()
                for message in messages[:10]:  # Анализируем только первые 10 сообщений
                    if isinstance(message, dict):
                        keys.update(message.keys())
                        # Если есть вложенный row_to_json и он является словарем, добавляем его ключи
                        if 'row_to_json' in message and isinstance(message['row_to_json'], dict):
                            keys.update([f"row_to_json.{k}" for k in message['row_to_json'].keys()])
                
                print(f"Доступные поля в сообщениях: {', '.join(sorted(keys))}")
            
            # Выводим примеры первых нескольких сообщений
            print("\nПримеры сообщений:")
            for i in range(min(3, len(messages))):
                print(f"\nСообщение {i+1}:")
                key_fields = extract_key_fields(messages[i])
                pprint(key_fields)
            
            # Интересные сообщения (высокого риска)
            interesting_messages = []
            
            # Статистика ранжирования
            stats = {
                'high_risk': 0,
                'abr_range': 0,
                'abr_not_range': 0,
                'ft_operation': 0,
                'od_operation': 0,
                'piramid_range': 0
            }
            
            for idx, message in enumerate(messages):
                # Проверка, является ли сообщение интересным (высокого риска)
                if is_high_risk(message):
                    # Сохраняем исходное сообщение без обработки
                    interesting_msg = message.copy() if isinstance(message, dict) else message
                    interesting_msg['reason'] = 'Высокий риск'
                    interesting_messages.append(interesting_msg)
                    stats['high_risk'] += 1
                
                # Подсчет статистики
                if is_abr_range(message):
                    stats['abr_range'] += 1
                
                if is_abr_not_range(message):
                    stats['abr_not_range'] += 1
                
                if is_ft_operation(message):
                    stats['ft_operation'] += 1
                
                if is_od_operation(message):
                    stats['od_operation'] += 1
                
                if is_piramid_range(message):
                    stats['piramid_range'] += 1
                
                # Выводим прогресс обработки
                if idx % 100 == 0:
                    print(f"Обработано {idx}/{len(messages)} сообщений")
            
            # Вывод статистики
            print("\nСтатистика ранжирования:")
            for key, value in stats.items():
                print(f"{key}: {value}")
            
            print(f"\nНайдено интересных сообщений (высокий риск): {len(interesting_messages)}")
            
            # Сохраняем интересные сообщения в новый файл
            if interesting_messages:
                with open('interesting_messages.json', 'w', encoding='utf-8') as out_file:
                    json.dump(interesting_messages, out_file, ensure_ascii=False, indent=2)
                print("Интересные сообщения сохранены в файл 'interesting_messages.json'")
            
            return interesting_messages
                
    except json.JSONDecodeError as e:
        print(f"Ошибка при декодировании JSON: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    
    return []

if __name__ == "__main__":
    file_path = 'json do_range.json'
    interesting_messages = process_json_file(file_path) 