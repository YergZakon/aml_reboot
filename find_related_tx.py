import json
from datetime import datetime, timedelta
from pprint import pprint

def format_transaction(message):
    """Форматирует транзакцию для удобного отображения"""
    if 'row_to_json' in message:
        data = message['row_to_json']
    else:
        data = message
        
    # Собираем информацию обо всех участниках
    payers = []
    recipients = []
    
    # Плательщики (pl1, pl2)
    if data.get("gmember_name_pl1") and data.get("gmember_name_pl1").strip() != "":
        payers.append({
            "name": data.get("gmember_name_pl1"),
            "id": data.get("gmember_maincode_pl1")
        })
    if data.get("gmember_name_pl2") and data.get("gmember_name_pl2").strip() != "":
        payers.append({
            "name": data.get("gmember_name_pl2"),
            "id": data.get("gmember_maincode_pl2")
        })
    
    # Получатели (pol1, pol2)
    if data.get("gmember_name_pol1") and data.get("gmember_name_pol1").strip() != "":
        recipients.append({
            "name": data.get("gmember_name_pol1"),
            "id": data.get("gmember_maincode_pol1")
        })
    if data.get("gmember_name_pol2") and data.get("gmember_name_pol2").strip() != "":
        recipients.append({
            "name": data.get("gmember_name_pol2"),
            "id": data.get("gmember_maincode_pol2")
        })
    
    return {
        "ID": data.get("gmess_id"),
        "Дата": data.get("goper_trans_date"),
        "Сумма": data.get("goper_tenge_amount"),
        "Плательщики": payers,
        "Получатели": recipients,
        "Назначение": data.get("goper_dopinfo")[:100] if data.get("goper_dopinfo") else None
    }

def parse_datetime(dt_str):
    """Парсит строку даты в объект datetime"""
    if not dt_str:
        return None
    try:
        # Пробуем разные форматы даты
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        # Если не удалось распарсить, возвращаем None
        return None
    except Exception as e:
        print(f"Ошибка при парсинге даты {dt_str}: {e}")
        return None

def find_related_transactions(messages, max_time_diff_hours=24):
    """Находит взаимосвязанные транзакции по участникам, суммам и времени"""
    print(f"Анализируем {len(messages)} сообщений...")
    
    # Словари для индексации транзакций
    by_person = {}  # по участникам
    by_amount = {}  # по суммам
    by_time_window = {}  # по временным окнам
    tx_data = {}  # данные о транзакциях для быстрого доступа
    
    # Первый проход: индексация всех транзакций
    for idx, msg in enumerate(messages):
        if 'row_to_json' in msg:
            data = msg['row_to_json']
        else:
            data = msg
        
        # Извлекаем ключевые данные
        tx_id = data.get('gmess_id')
        if not tx_id:
            continue  # Пропускаем транзакции без ID
        
        # Собираем информацию обо всех участниках
        payers = []
        recipients = []
        all_participants = []
        
        # Плательщики (pl1, pl2)
        if data.get("gmember_name_pl1") and data.get("gmember_name_pl1").strip() != "":
            payer_pl1 = {
                "name": data.get("gmember_name_pl1"),
                "id": data.get("gmember_maincode_pl1")
            }
            payers.append(payer_pl1)
            all_participants.append(payer_pl1)
            
        if data.get("gmember_name_pl2") and data.get("gmember_name_pl2").strip() != "":
            payer_pl2 = {
                "name": data.get("gmember_name_pl2"),
                "id": data.get("gmember_maincode_pl2")
            }
            payers.append(payer_pl2)
            all_participants.append(payer_pl2)
        
        # Получатели (pol1, pol2)
        if data.get("gmember_name_pol1") and data.get("gmember_name_pol1").strip() != "":
            recipient_pol1 = {
                "name": data.get("gmember_name_pol1"),
                "id": data.get("gmember_maincode_pol1")
            }
            recipients.append(recipient_pol1)
            all_participants.append(recipient_pol1)
            
        if data.get("gmember_name_pol2") and data.get("gmember_name_pol2").strip() != "":
            recipient_pol2 = {
                "name": data.get("gmember_name_pol2"),
                "id": data.get("gmember_maincode_pol2")
            }
            recipients.append(recipient_pol2)
            all_participants.append(recipient_pol2)
            
        # Сохраняем данные о транзакции
        tx_data[tx_id] = {
            'amount': data.get('goper_tenge_amount'),
            'tx_time_str': data.get('goper_trans_date'),
            'payers': payers,
            'recipients': recipients,
            'all_participants': all_participants,
            'msg_idx': idx  # Индекс сообщения в исходном массиве
        }
        
        # Парсим время транзакции
        tx_time = parse_datetime(data.get('goper_trans_date'))
        if tx_time:
            tx_data[tx_id]['tx_time'] = tx_time
            
            # Индексация по временным окнам (каждый час)
            time_key = tx_time.strftime("%Y-%m-%d %H")
            if time_key not in by_time_window:
                by_time_window[time_key] = set()
            by_time_window[time_key].add(tx_id)
        
        # Индексация по участникам
        for participant in all_participants:
            person_id = participant["id"]
            if person_id:
                if person_id not in by_person:
                    by_person[person_id] = set()
                by_person[person_id].add(tx_id)
        
        # Индексация по суммам
        amount = data.get('goper_tenge_amount')
        if amount:
            if amount not in by_amount:
                by_amount[amount] = set()
            by_amount[amount].add(tx_id)
    
    print(f"Проиндексировано {len(tx_data)} транзакций")
    
    # Второй проход: поиск связанных транзакций
    related_groups = []
    
    # 1. Поиск связанных по участникам транзакций (цепочки переводов)
    person_chains = find_transaction_chains(tx_data, by_person)
    if person_chains:
        related_groups.append({
            'type': 'chain_by_person',
            'description': 'Цепочки транзакций, где получатель становится плательщиком',
            'chains': person_chains
        })
    
    # 2. Поиск множественных транзакций между одними и теми же лицами
    person_multitx = find_multiple_transactions_between_same_persons(tx_data, by_person)
    if person_multitx:
        related_groups.append({
            'type': 'multiple_tx_between_same_persons',
            'description': 'Множественные транзакции между одними и теми же лицами',
            'groups': person_multitx
        })
    
    # 3. Поиск дробления платежей (несколько платежей близких по времени с одинаковым плательщиком или получателем)
    split_payments = find_split_payments(tx_data, by_person, by_time_window, max_time_diff_hours)
    if split_payments:
        related_groups.append({
            'type': 'split_payments',
            'description': 'Возможное дробление платежей',
            'groups': split_payments
        })
    
    # 4. Поиск транзакций с одинаковыми суммами в ограниченном временном окне
    same_amount_groups = find_same_amount_transactions(tx_data, by_amount, by_time_window, max_time_diff_hours)
    if same_amount_groups:
        related_groups.append({
            'type': 'same_amount_in_time_window',
            'description': f'Транзакции с одинаковыми суммами в течение {max_time_diff_hours} часов',
            'groups': same_amount_groups
        })
    
    return related_groups

def find_transaction_chains(tx_data, by_person, min_chain_length=2):
    """Находит цепочки транзакций, где получатель становится плательщиком"""
    chains = []
    visited = set()
    
    for tx_id, tx_info in tx_data.items():
        if tx_id in visited:
            continue
            
        # Начинаем новую цепочку с текущей транзакции
        recipients = tx_info.get('recipients', [])
        if not recipients:
            continue
            
        # Проверяем, являются ли получатели плательщиками в других транзакциях
        current_chain = [tx_id]
        visited.add(tx_id)
        
        # Перебираем всех получателей
        for recipient in recipients:
            recipient_id = recipient.get('id')
            if not recipient_id or recipient_id not in by_person:
                continue
                
            # Ищем следующие звенья цепочки
            for next_tx_id in by_person[recipient_id]:
                if next_tx_id in visited:
                    continue
                    
                # Проверяем, является ли получатель плательщиком в следующей транзакции
                is_payer = False
                for payer in tx_data[next_tx_id].get('payers', []):
                    if payer.get('id') == recipient_id:
                        is_payer = True
                        break
                        
                if is_payer:
                    # Нашли следующее звено, где получатель стал плательщиком
                    current_chain.append(next_tx_id)
                    visited.add(next_tx_id)
        
        # Если нашли цепочку достаточной длины, добавляем её
        if len(current_chain) >= min_chain_length:
            chain_info = []
            for chain_tx_id in current_chain:
                tx = tx_data[chain_tx_id]
                formatted_tx = {
                    'tx_id': chain_tx_id,
                    'amount': tx.get('amount'),
                    'tx_time': tx.get('tx_time_str'),
                }
                
                # Добавляем информацию о плательщиках
                if tx.get('payers'):
                    formatted_tx['payers'] = tx.get('payers')
                
                # Добавляем информацию о получателях
                if tx.get('recipients'):
                    formatted_tx['recipients'] = tx.get('recipients')
                
                chain_info.append(formatted_tx)
                
            chains.append(chain_info)
    
    return chains

def find_multiple_transactions_between_same_persons(tx_data, by_person, min_transactions=2):
    """Находит множественные транзакции между одними и теми же лицами"""
    # Ключ: (payer_id, recipient_id), значение: список ID транзакций
    person_pairs = {}
    
    for tx_id, tx_info in tx_data.items():
        payers = tx_info.get('payers', [])
        recipients = tx_info.get('recipients', [])
        
        for payer in payers:
            payer_id = payer.get('id')
            if not payer_id:
                continue
                
            for recipient in recipients:
                recipient_id = recipient.get('id')
                if not recipient_id:
                    continue
                    
                pair_key = (payer_id, recipient_id)
                if pair_key not in person_pairs:
                    person_pairs[pair_key] = []
                person_pairs[pair_key].append(tx_id)
    
    # Отбираем пары с количеством транзакций >= min_transactions
    result = []
    for (payer_id, recipient_id), tx_ids in person_pairs.items():
        if len(tx_ids) >= min_transactions:
            # Получаем информацию о плательщике и получателе из первой транзакции
            payer_info = None
            recipient_info = None
            
            for tx_id in tx_ids:
                tx = tx_data[tx_id]
                
                # Ищем плательщика с нужным ID
                for payer in tx.get('payers', []):
                    if payer.get('id') == payer_id:
                        payer_info = payer
                        break
                
                # Ищем получателя с нужным ID
                for recipient in tx.get('recipients', []):
                    if recipient.get('id') == recipient_id:
                        recipient_info = recipient
                        break
                
                if payer_info and recipient_info:
                    break
            
            # Получаем информацию о транзакциях
            transactions = []
            for tx_id in tx_ids:
                tx = tx_data[tx_id]
                transactions.append({
                    'tx_id': tx_id,
                    'amount': tx.get('amount'),
                    'tx_time': tx.get('tx_time_str')
                })
            
            result.append({
                'payer': payer_info,
                'recipient': recipient_info,
                'transaction_count': len(tx_ids),
                'transactions': transactions
            })
    
    return result

def find_split_payments(tx_data, by_person, by_time_window, max_time_diff_hours, min_transactions=2):
    """Находит возможное дробление платежей"""
    result = []
    
    # Проходим по всем лицам и ищем множественные исходящие или входящие транзакции в заданном временном окне
    for person_id, tx_ids in by_person.items():
        if len(tx_ids) < min_transactions:
            continue
            
        # Группируем транзакции по ролям (плательщик/получатель)
        outgoing = []  # Исходящие (person является плательщиком)
        incoming = []  # Входящие (person является получателем)
        
        for tx_id in tx_ids:
            tx = tx_data[tx_id]
            
            # Проверяем, является ли лицо плательщиком
            is_payer = False
            for payer in tx.get('payers', []):
                if payer.get('id') == person_id:
                    is_payer = True
                    outgoing.append(tx_id)
                    break
            
            # Если не плательщик, проверяем, является ли получателем
            if not is_payer:
                for recipient in tx.get('recipients', []):
                    if recipient.get('id') == person_id:
                        incoming.append(tx_id)
                        break
        
        # Проверяем исходящие транзакции на дробление
        if len(outgoing) >= min_transactions:
            time_groups = group_by_time_proximity(outgoing, tx_data, max_time_diff_hours)
            for group in time_groups:
                if len(group) >= min_transactions:
                    # Получаем информацию о лице
                    person_info = None
                    for tx_id in group:
                        tx = tx_data[tx_id]
                        for payer in tx.get('payers', []):
                            if payer.get('id') == person_id:
                                person_info = payer
                                break
                        if person_info:
                            break
                    
                    # Получаем информацию о транзакциях
                    transactions = []
                    total_amount = 0
                    for tx_id in group:
                        tx = tx_data[tx_id]
                        amount = tx.get('amount', 0)
                        if amount:
                            total_amount += amount
                        
                        tx_recipients = []
                        for recipient in tx.get('recipients', []):
                            tx_recipients.append(recipient)
                        
                        transactions.append({
                            'tx_id': tx_id,
                            'amount': amount,
                            'tx_time': tx.get('tx_time_str'),
                            'recipients': tx_recipients
                        })
                    
                    result.append({
                        'type': 'outgoing',
                        'person': person_info,
                        'transaction_count': len(group),
                        'total_amount': total_amount,
                        'transactions': transactions
                    })
        
        # Проверяем входящие транзакции на дробление
        if len(incoming) >= min_transactions:
            time_groups = group_by_time_proximity(incoming, tx_data, max_time_diff_hours)
            for group in time_groups:
                if len(group) >= min_transactions:
                    # Получаем информацию о лице
                    person_info = None
                    for tx_id in group:
                        tx = tx_data[tx_id]
                        for recipient in tx.get('recipients', []):
                            if recipient.get('id') == person_id:
                                person_info = recipient
                                break
                        if person_info:
                            break
                    
                    # Получаем информацию о транзакциях
                    transactions = []
                    total_amount = 0
                    for tx_id in group:
                        tx = tx_data[tx_id]
                        amount = tx.get('amount', 0)
                        if amount:
                            total_amount += amount
                        
                        tx_payers = []
                        for payer in tx.get('payers', []):
                            tx_payers.append(payer)
                        
                        transactions.append({
                            'tx_id': tx_id,
                            'amount': amount,
                            'tx_time': tx.get('tx_time_str'),
                            'payers': tx_payers
                        })
                    
                    result.append({
                        'type': 'incoming',
                        'person': person_info,
                        'transaction_count': len(group),
                        'total_amount': total_amount,
                        'transactions': transactions
                    })
    
    return result

def find_same_amount_transactions(tx_data, by_amount, by_time_window, max_time_diff_hours, min_transactions=2):
    """Находит транзакции с одинаковыми суммами в ограниченном временном окне"""
    result = []
    
    # Проходим по всем суммам и ищем транзакции с одинаковой суммой в заданном временном окне
    for amount, tx_ids in by_amount.items():
        if len(tx_ids) < min_transactions:
            continue
            
        # Группируем транзакции по временной близости
        time_groups = group_by_time_proximity(tx_ids, tx_data, max_time_diff_hours)
        
        for group in time_groups:
            if len(group) >= min_transactions:
                # Получаем информацию о транзакциях
                transactions = []
                for tx_id in group:
                    tx = tx_data[tx_id]
                    
                    tx_info = {
                        'tx_id': tx_id,
                        'tx_time': tx.get('tx_time_str')
                    }
                    
                    # Добавляем информацию о плательщиках
                    if tx.get('payers'):
                        tx_info['payers'] = tx.get('payers')
                    
                    # Добавляем информацию о получателях
                    if tx.get('recipients'):
                        tx_info['recipients'] = tx.get('recipients')
                    
                    transactions.append(tx_info)
                
                result.append({
                    'amount': amount,
                    'transaction_count': len(group),
                    'transactions': transactions
                })
    
    return result

def group_by_time_proximity(tx_ids, tx_data, max_time_diff_hours):
    """Группирует транзакции по временной близости"""
    # Сортируем транзакции по времени
    sorted_tx = []
    for tx_id in tx_ids:
        tx_time = tx_data[tx_id].get('tx_time')
        if tx_time:
            sorted_tx.append((tx_id, tx_time))
    sorted_tx.sort(key=lambda x: x[1])
    
    if not sorted_tx:
        return []
    
    # Группируем транзакции, находящиеся в пределах max_time_diff_hours друг от друга
    groups = []
    current_group = [sorted_tx[0][0]]
    current_time = sorted_tx[0][1]
    
    for tx_id, tx_time in sorted_tx[1:]:
        time_diff = (tx_time - current_time).total_seconds() / 3600  # разница в часах
        
        if time_diff <= max_time_diff_hours:
            # Транзакция находится в пределах временного окна
            current_group.append(tx_id)
        else:
            # Начинаем новую группу
            if len(current_group) > 1:
                groups.append(current_group)
            current_group = [tx_id]
        
        current_time = tx_time
    
    # Добавляем последнюю группу
    if len(current_group) > 1:
        groups.append(current_group)
    
    return groups

def print_related_transactions(related_groups):
    """Выводит информацию о связанных транзакциях"""
    if not related_groups:
        print("Взаимосвязанные транзакции не найдены")
        return
    
    for group_info in related_groups:
        print(f"\n{'='*80}")
        print(f"Тип связи: {group_info['description']}")
        print(f"{'='*80}")
        
        if group_info['type'] == 'chain_by_person':
            for i, chain in enumerate(group_info['chains']):
                print(f"\nЦепочка {i+1} (длина: {len(chain)}):")
                for j, tx in enumerate(chain):
                    print(f"  {j+1}. ID: {tx['tx_id']}, Сумма: {tx['amount']}, Время: {tx['tx_time']}")
                    # Вывод плательщиков
                    if 'payers' in tx:
                        for payer in tx['payers']:
                            print(f"     Плательщик: {payer['name']} ({payer['id']})")
                    # Вывод получателей
                    if 'recipients' in tx:
                        for recipient in tx['recipients']:
                            print(f"     Получатель: {recipient['name']} ({recipient['id']})")
        
        elif group_info['type'] == 'multiple_tx_between_same_persons':
            for i, group in enumerate(group_info['groups']):
                print(f"\nГруппа {i+1}: {group['transaction_count']} транзакций между")
                print(f"  Плательщик: {group['payer']['name']} ({group['payer']['id']})")
                print(f"  Получатель: {group['recipient']['name']} ({group['recipient']['id']})")
                for j, tx in enumerate(group['transactions']):
                    print(f"   {j+1}. ID: {tx['tx_id']}, Сумма: {tx['amount']}, Время: {tx['tx_time']}")
        
        elif group_info['type'] == 'split_payments':
            for i, group in enumerate(group_info['groups']):
                direction = "исходящих" if group['type'] == 'outgoing' else "входящих"
                print(f"\nГруппа {i+1}: {group['transaction_count']} {direction} транзакций")
                print(f"  Лицо: {group['person']['name']} ({group['person']['id']})")
                print(f"  Общая сумма: {group['total_amount']}")
                
                for j, tx in enumerate(group['transactions']):
                    print(f"   {j+1}. ID: {tx['tx_id']}, Сумма: {tx['amount']}, Время: {tx['tx_time']}")
                    if group['type'] == 'outgoing':
                        for recipient in tx.get('recipients', []):
                            print(f"      Получатель: {recipient['name']} ({recipient['id']})")
                    else:
                        for payer in tx.get('payers', []):
                            print(f"      Плательщик: {payer['name']} ({payer['id']})")
        
        elif group_info['type'] == 'same_amount_in_time_window':
            for i, group in enumerate(group_info['groups']):
                print(f"\nГруппа {i+1}: {group['transaction_count']} транзакций с суммой {group['amount']}")
                for j, tx in enumerate(group['transactions']):
                    print(f"   {j+1}. ID: {tx['tx_id']}, Время: {tx['tx_time']}")
                    # Вывод плательщиков
                    if 'payers' in tx:
                        for payer in tx['payers']:
                            print(f"      Плательщик: {payer['name']} ({payer['id']})")
                    # Вывод получателей
                    if 'recipients' in tx:
                        for recipient in tx['recipients']:
                            print(f"      Получатель: {recipient['name']} ({recipient['id']})")

def main():
    try:
        # Загружаем JSON с сообщениями
        with open('json do_range.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            # Определяем структуру данных
            if isinstance(data, list):
                messages = data
            elif isinstance(data, dict) and 'messages' in data:
                messages = data['messages']
            else:
                messages = [data]
            
            print(f"Загружено {len(messages)} сообщений")
            
            # Находим взаимосвязанные транзакции
            related_groups = find_related_transactions(messages, max_time_diff_hours=48)
            
            # Выводим результаты
            print_related_transactions(related_groups)
            
            # Сохраняем результаты в файл
            if related_groups:
                with open('related_transactions.json', 'w', encoding='utf-8') as out_file:
                    json.dump(related_groups, out_file, ensure_ascii=False, indent=2)
                print("\nРезультаты сохранены в файл 'related_transactions.json'")
    
    except FileNotFoundError:
        print("Файл с сообщениями не найден")
    except json.JSONDecodeError as e:
        print(f"Ошибка при декодировании JSON: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main() 