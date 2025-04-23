import json
import argparse
from datetime import datetime
from colorama import init, Fore, Style
from tabulate import tabulate

# Инициализация colorama
init()

def format_amount(amount):
    """Форматирует сумму транзакции для удобного отображения"""
    if isinstance(amount, (int, float)):
        return f"{amount:,.2f}".replace(",", " ")
    return str(amount)

def format_person(person):
    """Форматирует информацию о человеке"""
    if not person:
        return "Не указан"
    name = person.get("name", "Не указано")
    person_id = person.get("id", "Не указан")
    return f"{name} ({person_id})"

def format_date(date_str):
    """Форматирует дату для удобного отображения"""
    if not date_str:
        return "Не указана"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except:
        return date_str

def show_transaction_groups(groups, limit=None):
    """Отображает группы транзакций"""
    group_count = 0
    
    for group_info in groups:
        group_type = group_info["type"]
        description = group_info["description"]
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.GREEN}Тип связи: {Fore.YELLOW}{description}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        if group_type == "same_amount_in_time_window":
            for i, group in enumerate(group_info.get("groups", [])):
                if limit and i >= limit:
                    print(f"\n{Fore.RED}Показано {limit} из {len(group_info.get('groups', []))} групп...{Style.RESET_ALL}")
                    break
                
                amount = group.get("amount", 0)
                transaction_count = group.get("transaction_count", 0)
                
                print(f"\n{Fore.MAGENTA}Группа {i+1}: {transaction_count} транзакций с суммой {Fore.RED}{format_amount(amount)}{Style.RESET_ALL}")
                
                headers = ["ID", "Дата", "Плательщик", "Получатель"]
                table_data = []
                
                for j, tx in enumerate(group.get("transactions", [])):
                    payers = tx.get("payers", [])
                    recipients = tx.get("recipients", [])
                    
                    payer_str = ", ".join([format_person(p) for p in payers]) if payers else "Не указан"
                    recipient_str = ", ".join([format_person(r) for r in recipients]) if recipients else "Не указан"
                    
                    table_data.append([
                        tx.get("tx_id", ""),
                        format_date(tx.get("tx_time", "")),
                        payer_str,
                        recipient_str
                    ])
                
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                group_count += 1
                
        elif group_type == "split_payments":
            for i, group in enumerate(group_info.get("groups", [])):
                if limit and i >= limit:
                    print(f"\n{Fore.RED}Показано {limit} из {len(group_info.get('groups', []))} групп...{Style.RESET_ALL}")
                    break
                
                direction = "исходящих" if group.get("type") == "outgoing" else "входящих"
                person = group.get("person", {})
                total_amount = group.get("total_amount", 0)
                transaction_count = group.get("transaction_count", 0)
                
                print(f"\n{Fore.MAGENTA}Группа {i+1}: {Fore.YELLOW}{transaction_count} {direction} транзакций")
                print(f"Лицо: {Fore.BLUE}{format_person(person)}")
                print(f"Общая сумма: {Fore.RED}{format_amount(total_amount)}{Style.RESET_ALL}")
                
                headers = ["ID", "Дата", "Сумма"]
                if group.get("type") == "outgoing":
                    headers.append("Получатель")
                else:
                    headers.append("Плательщик")
                
                table_data = []
                
                for tx in group.get("transactions", []):
                    tx_id = tx.get("tx_id", "")
                    tx_time = format_date(tx.get("tx_time", ""))
                    amount = format_amount(tx.get("amount", 0))
                    
                    if group.get("type") == "outgoing":
                        recipients = tx.get("recipients", [])
                        party = ", ".join([format_person(r) for r in recipients]) if recipients else "Не указан"
                    else:
                        payers = tx.get("payers", [])
                        party = ", ".join([format_person(p) for p in payers]) if payers else "Не указан"
                    
                    table_data.append([tx_id, tx_time, amount, party])
                
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                group_count += 1
    
    print(f"\n{Fore.GREEN}Всего отображено {group_count} групп транзакций{Style.RESET_ALL}")

def search_by_person(groups, person_id, name_part=None):
    """Поиск транзакций по ИИН/БИН или части имени человека/организации"""
    found_transactions = []
    
    for group_info in groups:
        for group in group_info.get("groups", []):
            for tx in group.get("transactions", []):
                person_match = False
                
                # Проверка плательщиков
                for payer in tx.get("payers", []):
                    if person_id and payer.get("id") == person_id:
                        person_match = True
                    elif name_part and name_part.lower() in payer.get("name", "").lower():
                        person_match = True
                
                # Проверка получателей
                for recipient in tx.get("recipients", []):
                    if person_id and recipient.get("id") == person_id:
                        person_match = True
                    elif name_part and name_part.lower() in recipient.get("name", "").lower():
                        person_match = True
                
                if person_match:
                    found_transactions.append({
                        "tx_id": tx.get("tx_id"),
                        "amount": group.get("amount"),
                        "tx_time": tx.get("tx_time"),
                        "payers": tx.get("payers", []),
                        "recipients": tx.get("recipients", []),
                        "group_type": group_info.get("type"),
                        "description": group_info.get("description")
                    })
    
    return found_transactions

def search_by_amount(groups, min_amount, max_amount=None):
    """Поиск транзакций по сумме"""
    found_groups = []
    
    for group_info in groups:
        matching_groups = []
        
        for group in group_info.get("groups", []):
            amount = group.get("amount", 0)
            total_amount = group.get("total_amount", 0)
            
            check_amount = amount if amount > 0 else total_amount
            
            if (check_amount >= min_amount and 
                (max_amount is None or check_amount <= max_amount)):
                matching_groups.append(group)
        
        if matching_groups:
            found_groups.append({
                "type": group_info.get("type"),
                "description": group_info.get("description"),
                "groups": matching_groups
            })
    
    return found_groups

def main():
    parser = argparse.ArgumentParser(description='Анализ связанных транзакций')
    parser.add_argument('--file', '-f', default='related_transactions.json', help='Путь к файлу с данными')
    parser.add_argument('--search-person', '-p', help='Поиск по ИИН/БИН человека/организации')
    parser.add_argument('--search-name', '-n', help='Поиск по части имени человека/организации')
    parser.add_argument('--min-amount', '-min', type=float, help='Минимальная сумма для поиска')
    parser.add_argument('--max-amount', '-max', type=float, help='Максимальная сумма для поиска')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Ограничение количества групп для отображения')
    
    args = parser.parse_args()
    
    try:
        with open(args.file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if args.search_person or args.search_name:
            # Поиск по человеку/организации
            results = search_by_person(data, args.search_person, args.search_name)
            
            if not results:
                print(f"{Fore.RED}Транзакции по заданным критериям не найдены{Style.RESET_ALL}")
                return
            
            print(f"\n{Fore.GREEN}Найдено {len(results)} транзакций{Style.RESET_ALL}")
            
            headers = ["ID", "Дата", "Сумма", "Плательщик", "Получатель", "Тип связи"]
            table_data = []
            
            for tx in results:
                payers = tx.get("payers", [])
                recipients = tx.get("recipients", [])
                
                payer_str = ", ".join([format_person(p) for p in payers]) if payers else "Не указан"
                recipient_str = ", ".join([format_person(r) for r in recipients]) if recipients else "Не указан"
                
                table_data.append([
                    tx.get("tx_id", ""),
                    format_date(tx.get("tx_time", "")),
                    format_amount(tx.get("amount", 0)),
                    payer_str,
                    recipient_str,
                    tx.get("description", "")
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
        elif args.min_amount:
            # Поиск по сумме
            results = search_by_amount(data, args.min_amount, args.max_amount)
            
            if not results:
                print(f"{Fore.RED}Группы транзакций по заданным критериям не найдены{Style.RESET_ALL}")
                return
            
            show_transaction_groups(results, args.limit)
        else:
            # Отображение всех групп
            show_transaction_groups(data, args.limit)
    
    except FileNotFoundError:
        print(f"{Fore.RED}Файл {args.file} не найден{Style.RESET_ALL}")
    except json.JSONDecodeError:
        print(f"{Fore.RED}Ошибка при чтении JSON-файла{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Произошла ошибка: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()