import json
import re
from pprint import pprint

# Функция для определения, входит ли сообщение в высокорисковую категорию по алгоритму pkg_sim_range
def is_high_risk(message):
    # Проверка условий высокого риска согласно алгоритму
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message
            
        # Получаем значения полей для проверки условий
        # Сопоставляем имена полей с префиксом 'g' из pkg_sim_range
        is_red_1_pl1 = row_data.get('gis_member1_od_list1', 0) != 0
        is_red_1_pl2 = row_data.get('gis_member2_od_list1', 0) != 0
        oper_idtype = row_data.get('goper_idtype')
        oper_idview = row_data.get('goper_idview')
        oper_susp_first = row_data.get('goper_susp_first')
        oper_dopinfo = row_data.get('goper_dopinfo', '').lower() if row_data.get('goper_dopinfo') else ''
        oper_difficulties = row_data.get('goper_difficulties', '').lower() if row_data.get('goper_difficulties') else ''
        oper_tenge_amount = row_data.get('goper_tenge_amount', 0)
        
        # Проверяем другие списки (в алгоритме pkg_sim_range это is_subsoil_users и is_green_1)
        is_subsoil_users_pl1 = True  # Упрощенно, в реальности нужно проверить правильное поле
        is_subsoil_users_pl2 = True  # Упрощенно
        is_green_1_pl1 = True  # Упрощенно
        is_green_1_pl2 = True  # Упрощенно
        
        # Проверка is_red_2
        is_red_2_pl1 = row_data.get('gis_member1_od_list2', 0) != 0
        is_red_2_pl2 = row_data.get('gis_member2_od_list2', 0) != 0
        
        # Проверка условий high_risk_1
        high_risk_1 = (
            (is_red_1_pl1 or is_red_1_pl2) and
            (
                (oper_idtype is not None and oper_idtype in [119, 413, 561, 661]) or
                (oper_idview is not None and oper_idview == 911) or
                (oper_susp_first is not None and oper_susp_first in [1057, 1066, 3002]) or
                (oper_susp_first is not None and oper_susp_first == 1058 and oper_idtype not in [423, 421]) or
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

        # Проверка условий high_risk_2
        high_risk_2 = (
            (is_red_2_pl1 or is_red_2_pl2 or (oper_susp_first is not None and oper_susp_first == 1113)) and
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

        # Результат проверок высокого риска
        result = high_risk_1 or high_risk_2 or is_ft_high or is_od_high or is_piramid_high
        
        # Для отладки выводим информацию о результатах проверок
        if result:
            print("\nНайдено сообщение высокого риска:")
            risk_details = {
                "high_risk_1": high_risk_1,
                "high_risk_2": high_risk_2,
                "is_ft_high": is_ft_high,
                "is_od_high": is_od_high,
                "is_piramid_high": is_piramid_high,
                "oper_tenge_amount": oper_tenge_amount,
                "oper_idtype": oper_idtype,
                "oper_idview": oper_idview,
                "oper_susp_first": oper_susp_first,
                "is_red_1_pl1": is_red_1_pl1,
                "is_red_1_pl2": is_red_1_pl2,
                "is_red_2_pl1": is_red_2_pl1,
                "is_red_2_pl2": is_red_2_pl2
            }
            pprint(risk_details)
        
        return result
    except Exception as e:
        print(f"Ошибка при определении high_risk: {e}")
        return False

# Проверка на соответствие условиям ФТ операций
def is_ft_operation(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message
            
        mess_oper_status = row_data.get('gmess_oper_status')
        mess_reason_code = row_data.get('gmess_reason_code')
        return mess_oper_status == 1 and mess_reason_code in [4, 10]
    except Exception as e:
        print(f"Ошибка при определении is_ft_operation: {e}")
        return False

# Проверка на высокий риск для ФТ операций
def is_ft_high_risk(message):
    try:
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message

        # Проверяем включение в списки DMFT или другие специальные условия
        member1_ft_list2 = row_data.get('gis_member1_ft_list2', 0) != 0
        member2_ft_list2 = row_data.get('gis_member2_ft_list2', 0) != 0
        member1_ft_list3 = row_data.get('gis_member1_ft_list3', 0) != 0
        member2_ft_list3 = row_data.get('gis_member2_ft_list3', 0) != 0
        member1_ft_list4 = row_data.get('gis_member1_ft_list4', 0) != 0
        member2_ft_list4 = row_data.get('gis_member2_ft_list4', 0) != 0

        # Проверка условий высокого риска для ФТ
        return (member1_ft_list2 or member2_ft_list2 or 
                member1_ft_list3 or member2_ft_list3 or
                member1_ft_list4 or member2_ft_list4)
    except Exception as e:
        print(f"Ошибка при определении is_ft_high_risk: {e}")
        return False

# Проверка на соответствие условиям ОД операций
def is_od_operation(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message
            
        mess_oper_status = row_data.get('gmess_oper_status')
        mess_reason_code = row_data.get('gmess_reason_code')
        return mess_oper_status == 1 and mess_reason_code in [1, 2, 8]
    except Exception as e:
        print(f"Ошибка при определении is_od_operation: {e}")
        return False

# Проверка на высокий риск для ОД операций
def is_od_high_risk(message):
    try:
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message

        # Проверяем включение в списки ОД или другие специальные условия
        member1_od_list1 = row_data.get('gis_member1_od_list1', 0) != 0
        member2_od_list1 = row_data.get('gis_member2_od_list1', 0) != 0
        member1_od_list2 = row_data.get('gis_member1_od_list2', 0) != 0
        member2_od_list2 = row_data.get('gis_member2_od_list2', 0) != 0
        
        oper_tenge_amount = row_data.get('goper_tenge_amount', 0)
        oper_susp_first = row_data.get('goper_susp_first')
        
        # Проверка условий высокого риска для ОД
        high_risk = (
            (member1_od_list1 or member2_od_list1 or member1_od_list2 or member2_od_list2) and
            (oper_tenge_amount >= 200000000 or (oper_susp_first is not None and oper_susp_first in [1057, 1066, 3002]))
        )
        
        return high_risk
    except Exception as e:
        print(f"Ошибка при определении is_od_high_risk: {e}")
        return False

# Проверка на соответствие условиям финансовой пирамиды
def is_piramid_range(message):
    try:
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message
            
        mess_oper_status = row_data.get('gmess_oper_status')
        mess_reason_code = row_data.get('gmess_reason_code')
        cfm_code = row_data.get('gcfm_code')
        
        # Проверка условий для финансовой пирамиды
        return mess_oper_status == 1 and mess_reason_code in [1, 2, 8] and cfm_code == 51
    except Exception as e:
        print(f"Ошибка при определении is_piramid_range: {e}")
        return False

# Проверка на высокий риск для финансовой пирамиды
def is_piramid_high_risk(message):
    # Упрощенная реализация, в реальности нужна более сложная логика
    return False

# Проверка на соответствие условиям ранжирования ABR
def is_abr_range(message):
    try:
        # Если в сообщении есть вложенный row_to_json, используем его
        if 'row_to_json' in message:
            row_data = message['row_to_json']
        else:
            row_data = message
            
        mess_oper_status = row_data.get('gmess_oper_status')
        mess_reason_code = row_data.get('gmess_reason_code')
        cfm_code = row_data.get('gcfm_code')
        member_id_pl1 = row_data.get('gmember_id_pl1')
        member_residence_pl1 = row_data.get('gmember_residence_pl1')
        member_id_pl2 = row_data.get('gmember_id_pl2')
        member_residence_pl2 = row_data.get('gmember_residence_pl2')
        member_id_pol1 = row_data.get('gmember_id_pol1')
        member_bank_address_pol1 = row_data.get('gmember_bank_address_pol1')
        member_id_pol2 = row_data.get('gmember_id_pol2')
        member_bank_address_pol2 = row_data.get('gmember_bank_address_pol2')
        member_bank_address_pl1 = row_data.get('gmember_bank_address_pl1')
        member_bank_address_pl2 = row_data.get('gmember_bank_address_pl2')
        receive_date = row_data.get('greceive_date')
        oper_trans_date = row_data.get('goper_trans_date')
        
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
            row_data = message['row_to_json']
        else:
            row_data = message
            
        oper_dopinfo = row_data.get('goper_dopinfo', '').lower() if row_data.get('goper_dopinfo') else ''
        
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
        row_data = message['row_to_json']
    else:
        row_data = message
    
    # Поля для извлечения (с префиксом 'g')
    keys = [
        'gmess_id', 'gmess_oper_status', 'gmess_reason_code', 'gcfm_code',
        'goper_idtype', 'goper_idview', 'goper_susp_first',
        'goper_tenge_amount', 'goper_currency_amount', 
        'gmember_residence_pl1', 'gmember_bank_address_pol1',
        'gis_member1_od_list1', 'gis_member2_od_list1',
        'gis_member1_od_list2', 'gis_member2_od_list2'
    ]
    
    result = {}
    for key in keys:
        if key in row_data:
            result[key] = row_data[key]
            
    # Добавляем текстовые поля с ограничением длины
    text_fields = ['goper_dopinfo', 'goper_difficulties', 'gmember_name_pl1', 'gmember_name_pol1']
    for field in text_fields:
        if field in row_data and row_data[field]:
            value = row_data[field]
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