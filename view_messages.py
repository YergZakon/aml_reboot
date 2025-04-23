import json
from pprint import pprint

def format_message(message):
    """Форматирует сообщение для удобного просмотра"""
    if 'row_to_json' in message:
        data = message['row_to_json']
    else:
        data = message
        
    # Основная информация о сообщении
    result = {
        "ID сообщения": data.get("gmess_id"),
        "Дата получения": data.get("greceive_date"),
        "Дата операции": data.get("goper_trans_date"),
        "Статус операции": data.get("gmess_oper_status"),
        "Код основания": data.get("gmess_reason_code"),
        "Сумма в тенге": data.get("goper_tenge_amount"),
        "КВО": data.get("goper_idview"),
        "ЕКНП": data.get("goper_idtype"),
        "КППО": data.get("goper_susp_first"),
        "Назначение платежа": data.get("goper_dopinfo"),
    }
    
    # Информация о Плательщике 1
    payer1 = {
        "ИИН/БИН": data.get("gmember_maincode_pl1"),
        "Резиденство": data.get("gmember_residence_pl1"),
        "Банк страны": data.get("gmember_bank_address_pl1"),
        "Имя": data.get("gmember_name_pl1"),
    }
    
    # Информация о Получателе 1
    recipient1 = {
        "ИИН/БИН": data.get("gmember_maincode_pol1"),
        "Резиденство": data.get("gmember_residence_pol1"),
        "Банк страны": data.get("gmember_bank_address_pol1"),
        "Имя": data.get("gmember_name_pol1"),
    }
    
    # Проверки списков ОД и ФТ
    lists = {
        "Плательщик в списке ОД 1": data.get("gis_member1_od_list1"),
        "Плательщик в списке ОД 2": data.get("gis_member1_od_list2"),
        "Получатель в списке ОД 1": data.get("gis_member2_od_list1"),
        "Получатель в списке ОД 2": data.get("gis_member2_od_list2"),
        "Плательщик в списке ФТ": data.get("gis_member1_ft_list2"),
        "Получатель в списке ФТ": data.get("gis_member2_ft_list2"),
        "Плательщик в DMFT": data.get("gis_member1_dmft_list4"),
        "Получатель в DMFT": data.get("gis_member2_dmft_list4"),
    }
    
    return {
        "Основная информация": result,
        "Плательщик": payer1,
        "Получатель": recipient1,
        "Списки проверок": lists,
        "Причина выбора": message.get("reason", "Не указано")
    }

def main():
    try:
        # Загружаем интересные сообщения
        with open('interesting_messages.json', 'r', encoding='utf-8') as file:
            messages = json.load(file)
            
        print(f"Найдено {len(messages)} интересных сообщений\n")
        
        # Выводим каждое сообщение в удобном формате
        for i, message in enumerate(messages):
            print(f"\n{'='*50}")
            print(f"Сообщение {i+1}")
            print(f"{'='*50}")
            
            # Обрабатываем возможность повреждения данных
            try:
                formatted = format_message(message)
                
                for section, data in formatted.items():
                    if isinstance(data, dict):
                        print(f"\n-- {section} --")
                        for key, value in data.items():
                            print(f"{key}: {value}")
                    else:
                        print(f"\n-- {section} --")
                        print(data)
            except Exception as e:
                print(f"Ошибка при форматировании сообщения: {e}")
                print("Исходное сообщение:")
                pprint(message)
            
    except FileNotFoundError:
        print("Файл interesting_messages.json не найден")
    except json.JSONDecodeError:
        print("Ошибка при чтении JSON")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main() 