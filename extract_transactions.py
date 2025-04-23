import json
import sys

# Идентификаторы транзакций, которые мы ищем
tx_ids = [67810568, 67809113]

def format_participants(data):
    """Форматирует информацию об участниках транзакции"""
    participants = {
        "payers": [],
        "recipients": []
    }
    
    # Плательщики (pl1, pl2)
    if data.get("gmember_name_pl1") and data.get("gmember_name_pl1").strip():
        participants["payers"].append({
            "role": "pl1",
            "name": data.get("gmember_name_pl1"),
            "id": data.get("gmember_maincode_pl1"),
            "type": data.get("gmember_type_pl1")
        })
    
    if data.get("gmember_name_pl2") and data.get("gmember_name_pl2").strip():
        participants["payers"].append({
            "role": "pl2",
            "name": data.get("gmember_name_pl2"),
            "id": data.get("gmember_maincode_pl2"),
            "type": data.get("gmember_type_pl2")
        })
    
    # Получатели (pol1, pol2)
    if data.get("gmember_name_pol1") and data.get("gmember_name_pol1").strip():
        participants["recipients"].append({
            "role": "pol1",
            "name": data.get("gmember_name_pol1"),
            "id": data.get("gmember_maincode_pol1"),
            "type": data.get("gmember_type_pol1") 
        })
    
    if data.get("gmember_name_pol2") and data.get("gmember_name_pol2").strip():
        participants["recipients"].append({
            "role": "pol2",
            "name": data.get("gmember_name_pol2"),
            "id": data.get("gmember_maincode_pol2"),
            "type": data.get("gmember_type_pol2")
        })
    
    return participants

try:
    # Открываем файл и обрабатываем его построчно
    with open('json do_range.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        
        # Определяем структуру данных
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict) and 'messages' in data:
            messages = data['messages']
        else:
            messages = [data]
        
        # Ищем нужные транзакции
        for msg in messages:
            if 'row_to_json' in msg and msg['row_to_json'].get('gmess_id') in tx_ids:
                tx_data = msg['row_to_json']
                participants = format_participants(tx_data)
                
                print(f"\n{'='*80}")
                print(f"Транзакция ID: {tx_data.get('gmess_id')}")
                print(f"Дата операции: {tx_data.get('goper_trans_date')}")
                print(f"Сумма: {tx_data.get('goper_tenge_amount')} тенге")
                print(f"Назначение: {tx_data.get('goper_dopinfo')}")
                print(f"Тип операции: {tx_data.get('goper_idview')} (вид), {tx_data.get('goper_idtype')} (тип)")
                
                # Вывод плательщиков
                print("\nПлательщики:")
                if participants["payers"]:
                    for payer in participants["payers"]:
                        print(f"  Роль: {payer['role']}")
                        print(f"  Имя: {payer['name']}")
                        print(f"  ИИН/БИН: {payer['id']}")
                        print(f"  Тип: {payer['type']}")
                else:
                    print("  Не указаны")
                
                # Вывод получателей
                print("\nПолучатели:")
                if participants["recipients"]:
                    for recipient in participants["recipients"]:
                        print(f"  Роль: {recipient['role']}")
                        print(f"  Имя: {recipient['name']}")
                        print(f"  ИИН/БИН: {recipient['id']}")
                        print(f"  Тип: {recipient['type']}")
                else:
                    print("  Не указаны")
                
                # Дополнительная информация из полей gmemberX
                print("\nДополнительная информация об участниках:")
                if tx_data.get("gmember1_maincode"):
                    print("\nУчастник 1:")
                    print(f"  ИИН/БИН: {tx_data.get('gmember1_maincode')}")
                    print(f"  Тип: {tx_data.get('gmember1_member_type')}")
                    print(f"  Фамилия: {tx_data.get('gmember1_ac_secondname')}")
                    print(f"  Имя: {tx_data.get('gmember1_ac_firstname')}")
                    print(f"  Отчество: {tx_data.get('gmember1_ac_middlename')}")
                    print(f"  Наименование ЮЛ: {tx_data.get('gmember1_ur_name')}")
                
                if tx_data.get("gmember2_maincode"):
                    print("\nУчастник 2:")
                    print(f"  ИИН/БИН: {tx_data.get('gmember2_maincode')}")
                    print(f"  Тип: {tx_data.get('gmember2_member_type')}")
                    print(f"  Фамилия: {tx_data.get('gmember2_ac_secondname')}")
                    print(f"  Имя: {tx_data.get('gmember2_ac_firstname')}")
                    print(f"  Отчество: {tx_data.get('gmember2_ac_middlename')}")
                    print(f"  Наименование ЮЛ: {tx_data.get('gmember2_ur_name')}")
                
                print(f"\n{'='*80}")

except Exception as e:
    print(f"Ошибка: {e}") 