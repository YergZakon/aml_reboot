import json
import os
from datetime import datetime, timedelta
import sys
import argparse
from tabulate import tabulate
from colorama import init, Fore, Style

# Инициализация colorama
init()

# Настройки мониторинга
MONITORING_SETTINGS = {
    "threshold_amount": 10000000,  # Пороговая сумма для крупных операций (10 млн)
    "high_risk_countries": [840, 392, 36, 826, 276, 784, 756, 156, 702, 410],  # Коды высокорисковых стран
    "high_risk_operation_types": [2020, 1001, 1002, 7001, 7002],  # Типы высокорисковых операций
    "suspicious_amount_range": [8000000, 9999999],  # Диапазон подозрительных сумм (для обхода пороговых значений)
    "rapid_movement_threshold": 0.9,  # Порог для выявления быстрого движения средств (90% от входящих)
    "unusual_activity_multiplier": 1.5,  # Множитель для выявления необычной активности
    "max_transaction_age_days": 30,  # Максимальный возраст транзакции для включения в анализ
    "blacklisted_entities": []  # Список БИН/ИИН в черном списке
}

# Полный список правил мониторинга
MONITORING_RULES = [
    "threshold_exceeded",           # Превышение пороговой суммы
    "high_risk_jurisdiction",       # Операция с высокорисковой юрисдикцией
    "missing_recipient",            # Отсутствие получателя
    "missing_payment_purpose",      # Отсутствие назначения платежа
    "suspicious_activity",          # Подозрительная активность (признаки в данных)
    "unusual_transaction_type",     # Необычный тип транзакции
    "blacklisted_entity",           # Участник в черном списке
    "round_amount",                 # Подозрительно круглая сумма
    "structured_transactions",      # Признаки дробления
    "high_risk_client"              # Клиент с высоким риском
]

# ============= Функции проверки правил AML =============

def is_threshold_exceeded(tx_data):
    """Проверка превышения пороговой суммы"""
    amount = tx_data.get('goper_tenge_amount', 0)
    
    if amount is None:
        return 0
    
    if isinstance(amount, str):
        try:
            amount = float(amount.replace(',', '.'))
        except (ValueError, TypeError):
            return 0
    
    if amount > MONITORING_SETTINGS["threshold_amount"]:
        return 1
    return 0

def is_high_risk_jurisdiction(tx_data):
    """Проверка на высокорисковые юрисдикции"""
    high_risk_countries = MONITORING_SETTINGS["high_risk_countries"]
    
    residence_pl1 = tx_data.get('gmember_residence_pl1')
    residence_pl2 = tx_data.get('gmember_residence_pl2')
    residence_pol1 = tx_data.get('gmember_residence_pol1')
    residence_pol2 = tx_data.get('gmember_residence_pol2')
    
    # Проверяем резидентство всех участников
    if any(residence in high_risk_countries for residence in [residence_pl1, residence_pl2, residence_pol1, residence_pol2] if residence):
        return 1
    return 0

def is_missing_recipient(tx_data):
    """Проверка отсутствия получателя"""
    # Проверяем наличие информации о получателе
    recipient_name_pol1 = tx_data.get('gmember_name_pol1', '')
    recipient_name_pol2 = tx_data.get('gmember_name_pol2', '')
    recipient_id_pol1 = tx_data.get('gmember_maincode_pol1')
    recipient_id_pol2 = tx_data.get('gmember_maincode_pol2')
    
    # Если информация о получателе отсутствует, возвращаем 1
    if (not recipient_name_pol1 or recipient_name_pol1.strip() == '') and \
       (not recipient_name_pol2 or recipient_name_pol2.strip() == '') and \
       not recipient_id_pol1 and not recipient_id_pol2:
        return 1
    return 0

def is_missing_payment_purpose(tx_data):
    """Проверка отсутствия назначения платежа"""
    purpose = tx_data.get('goper_dopinfo', '')
    
    if not purpose or purpose.strip() == '':
        return 1
    return 0

def is_suspicious_activity(tx_data):
    """Проверка на признаки подозрительной активности"""
    # Проверяем признаки подозрительности в данных транзакции
    susp_first = tx_data.get('goper_susp_first')
    susp_second = tx_data.get('goper_susp_second')
    susp_third = tx_data.get('goper_susp_third')
    
    # Если есть хотя бы один признак подозрительности, возвращаем 1
    if susp_first or susp_second or susp_third:
        return 1
    return 0

def is_unusual_transaction_type(tx_data):
    """Проверка на необычный тип транзакции"""
    high_risk_types = MONITORING_SETTINGS["high_risk_operation_types"]
    operation_type = tx_data.get('goper_idview')
    
    if operation_type in high_risk_types:
        return 1
    return 0

def is_blacklisted_entity(tx_data):
    """Проверка на наличие участника в черном списке"""
    blacklist = MONITORING_SETTINGS["blacklisted_entities"]
    
    # Проверяем всех участников
    payer_id_pl1 = tx_data.get('gmember_maincode_pl1')
    payer_id_pl2 = tx_data.get('gmember_maincode_pl2')
    recipient_id_pol1 = tx_data.get('gmember_maincode_pol1')
    recipient_id_pol2 = tx_data.get('gmember_maincode_pol2')
    
    # Проверяем дополнительных участников
    member1_id = tx_data.get('gmember1_maincode')
    member2_id = tx_data.get('gmember2_maincode')
    
    # Список всех участников транзакции
    all_participants = [payer_id_pl1, payer_id_pl2, recipient_id_pol1, recipient_id_pol2, member1_id, member2_id]
    
    # Если хотя бы один участник находится в черном списке, возвращаем 1
    if any(participant in blacklist for participant in all_participants if participant):
        return 1
    
    # Проверяем, есть ли в описании упоминание о высоком риске
    purpose = tx_data.get('goper_dopinfo', '')
    
    # Проверяем, что purpose не None перед вызовом lower()
    if purpose is None:
        purpose = ''
    else:
        purpose = purpose.lower()
        
    if 'высок' in purpose and 'риск' in purpose:
        return 1
        
    return 0

def is_round_amount(tx_data):
    """Проверка на подозрительно круглую сумму"""
    amount = tx_data.get('goper_tenge_amount', 0)
    
    if amount is None:
        return 0
    
    if isinstance(amount, str):
        try:
            amount = float(amount.replace(',', '.'))
        except (ValueError, TypeError):
            return 0
    
    # Проверяем, является ли сумма круглой (заканчивается на несколько нулей)
    str_amount = str(int(amount))
    if str_amount.endswith('000000'):  # Миллионы
        return 1
    if amount > 100000 and str_amount.endswith('00000'):  # Сотни тысяч
        return 1
        
    return 0

def is_structured_transaction(tx_data):
    """Проверка на признаки дробления платежей"""
    # Для полноценной проверки нужны исторические данные
    # Здесь проверяем косвенные признаки в самой транзакции
    
    amount = tx_data.get('goper_tenge_amount', 0)
    
    if amount is None:
        return 0
    
    if isinstance(amount, str):
        try:
            amount = float(amount.replace(',', '.'))
        except (ValueError, TypeError):
            return 0
    
    # Проверяем, попадает ли сумма в подозрительный диапазон
    if MONITORING_SETTINGS["suspicious_amount_range"][0] <= amount <= MONITORING_SETTINGS["suspicious_amount_range"][1]:
        return 1
        
    return 0

def is_high_risk_client(tx_data):
    """Проверка на клиента с высоким риском"""
    # Проверяем наличие признаков высокого риска в описании операции
    purpose = tx_data.get('goper_dopinfo', '')
    
    # Проверяем, что purpose не None перед вызовом lower()
    if purpose is None:
        purpose = ''
    else:
        purpose = purpose.lower()
    
    risk_keywords = ['высок', 'риск', 'афм', 'од', 'фт', 'отмыв', 'терроризм', 'подозр']
    
    # Если в описании есть ключевые слова, связанные с риском
    for keyword in risk_keywords:
        if keyword in purpose:
            return 1
    
    return 0

def check_all_aml_rules(tx_data):
    """Проверяет транзакцию на соответствие всем правилам AML"""
    results = {}
    
    # Выполняем все проверки
    results['threshold_exceeded'] = is_threshold_exceeded(tx_data)
    results['high_risk_jurisdiction'] = is_high_risk_jurisdiction(tx_data)
    results['missing_recipient'] = is_missing_recipient(tx_data)
    results['missing_payment_purpose'] = is_missing_payment_purpose(tx_data)
    results['suspicious_activity'] = is_suspicious_activity(tx_data)
    results['unusual_transaction_type'] = is_unusual_transaction_type(tx_data)
    results['blacklisted_entity'] = is_blacklisted_entity(tx_data)
    results['round_amount'] = is_round_amount(tx_data)
    results['structured_transactions'] = is_structured_transaction(tx_data)
    results['high_risk_client'] = is_high_risk_client(tx_data)
    
    # Подсчитываем общий риск
    risk_score = sum(results.values())
    results['risk_score'] = risk_score
    results['risk_level'] = 'Высокий' if risk_score >= 3 else 'Средний' if risk_score >= 1 else 'Низкий'
    
    return results

def format_amount(amount):
    """Форматирует сумму для отображения"""
    if amount is None:
        return "0"
    
    if isinstance(amount, str):
        try:
            amount = float(amount.replace(',', '.'))
        except (ValueError, TypeError):
            return amount
    
    return f"{amount:,.2f}".replace(',', ' ')

def get_person_info(tx_data, is_payer=True):
    """Получает информацию о человеке (плательщик или получатель)"""
    if is_payer:
        name = tx_data.get('gmember_name_pl1', '')
        code = tx_data.get('gmember_maincode_pl1', '')
    else:
        name = tx_data.get('gmember_name_pol1', '')
        code = tx_data.get('gmember_maincode_pol1', '')
    
    if not name or name.strip() == '':
        name = 'Не указан'
    
    if code:
        return f"{name} ({code})"
    else:
        return name

def print_high_risk_transactions(risky_transactions, min_score=3, limit=10):
    """Выводит информацию о транзакциях с высоким риском"""
    filtered_transactions = [tx for tx in risky_transactions if tx['risk_score'] >= min_score]
    
    if not filtered_transactions:
        print(f"{Fore.YELLOW}Транзакций с оценкой риска >= {min_score} не найдено.{Style.RESET_ALL}")
        return
    
    # Сортируем по убыванию оценки риска
    filtered_transactions.sort(key=lambda tx: tx['risk_score'], reverse=True)
    
    print(f"\n{Fore.RED}{'=' * 80}")
    print(f"{Fore.WHITE}ТРАНЗАКЦИИ С ВЫСОКИМ РИСКОМ (Оценка >= {min_score})")
    print(f"{Fore.RED}{'=' * 80}{Style.RESET_ALL}")
    
    displayed_count = 0
    
    headers = ["ID", "Дата", "Сумма", "Плательщик", "Получатель", "Оценка риска", "Уровень"]
    table_data = []
    
    for tx in filtered_transactions:
        tx_data = tx['tx_data']
        
        table_data.append([
            tx_data.get('gmess_id', ''),
            tx_data.get('goper_trans_date', '')[:10] if tx_data.get('goper_trans_date') else '',
            format_amount(tx_data.get('goper_tenge_amount', 0)),
            get_person_info(tx_data, True),
            get_person_info(tx_data, False),
            tx['risk_score'],
            tx['risk_level']
        ])
        
        displayed_count += 1
        if limit and displayed_count >= limit:
            break
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if limit and len(filtered_transactions) > limit:
        print(f"\n{Fore.YELLOW}Показано {limit} из {len(filtered_transactions)} транзакций с высоким риском.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}Всего найдено {len(filtered_transactions)} транзакций с высоким риском.{Style.RESET_ALL}")

def print_rule_statistics(risky_transactions):
    """Выводит статистику по сработавшим правилам"""
    rule_stats = {rule: 0 for rule in MONITORING_RULES}
    total_transactions = len(risky_transactions)
    high_risk_count = sum(1 for tx in risky_transactions if tx['risk_level'] == 'Высокий')
    medium_risk_count = sum(1 for tx in risky_transactions if tx['risk_level'] == 'Средний')
    low_risk_count = sum(1 for tx in risky_transactions if tx['risk_level'] == 'Низкий')
    
    # Подсчитываем сработавшие правила
    for tx in risky_transactions:
        for rule in MONITORING_RULES:
            if tx.get(rule, 0) == 1:
                rule_stats[rule] += 1
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.WHITE}СТАТИСТИКА ПО РИСКАМ")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    print(f"{Fore.WHITE}Всего проанализировано транзакций: {Fore.YELLOW}{total_transactions}{Style.RESET_ALL}")
    print(f"{Fore.RED}Транзакций с высоким риском: {high_risk_count} ({high_risk_count/total_transactions:.1%}){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Транзакций со средним риском: {medium_risk_count} ({medium_risk_count/total_transactions:.1%}){Style.RESET_ALL}")
    print(f"{Fore.GREEN}Транзакций с низким риском: {low_risk_count} ({low_risk_count/total_transactions:.1%}){Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Статистика по сработавшим правилам:{Style.RESET_ALL}")
    
    rule_stats_sorted = sorted(rule_stats.items(), key=lambda x: x[1], reverse=True)
    
    table_data = []
    for rule, count in rule_stats_sorted:
        percentage = count / total_transactions * 100
        table_data.append([rule, count, f"{percentage:.1f}%"])
    
    print(tabulate(table_data, headers=["Правило", "Количество", "% от всех"], tablefmt="grid"))

def process_all_transactions(json_file_path, min_risk_score=1, limit=None):
    """Обрабатывает все транзакции из файла и возвращает статистику"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Определяем структуру данных
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict) and 'messages' in data:
            messages = data['messages']
        else:
            messages = [data]
        
        total_count = len(messages)
        print(f"{Fore.CYAN}Загружено {total_count} сообщений для анализа...{Style.RESET_ALL}")
        
        risky_transactions = []
        tx_count = 0
        progress_step = max(1, total_count // 20)  # Обновляем прогресс каждые 5%
        
        # Обрабатываем каждое сообщение
        for i, msg in enumerate(messages):
            if 'row_to_json' in msg:
                tx_data = msg['row_to_json']
                tx_count += 1
                
                # Проверяем на риски
                aml_results = check_all_aml_rules(tx_data)
                
                # Если есть риски, добавляем в список
                if aml_results['risk_score'] >= min_risk_score:
                    # Добавляем данные транзакции к результатам
                    aml_results['tx_data'] = tx_data
                    risky_transactions.append(aml_results)
                
                # Отображаем прогресс
                if (i + 1) % progress_step == 0 or i + 1 == total_count:
                    progress = (i + 1) / total_count * 100
                    sys.stdout.write(f"\r{Fore.CYAN}Прогресс: {progress:.1f}% ({i+1}/{total_count}){Style.RESET_ALL}")
                    sys.stdout.flush()
        
        print(f"\n{Fore.GREEN}Анализ завершен. Проанализировано {tx_count} транзакций.{Style.RESET_ALL}")
        
        return risky_transactions
        
    except FileNotFoundError:
        print(f"{Fore.RED}Ошибка: Файл {json_file_path} не найден{Style.RESET_ALL}")
        return []
        
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Ошибка при декодировании JSON: {e}{Style.RESET_ALL}")
        return []
        
    except Exception as e:
        print(f"{Fore.RED}Произошла ошибка: {e}{Style.RESET_ALL}")
        return []

def main():
    parser = argparse.ArgumentParser(description='Анализ транзакций на предмет рисков ОД/ФТ')
    parser.add_argument('--file', '-f', default='json do_range.json', help='Путь к файлу с данными')
    parser.add_argument('--min-score', '-ms', type=int, default=1, help='Минимальная оценка риска для отображения (1-10)')
    parser.add_argument('--high-risk', '-hr', type=int, default=3, help='Порог для высокого риска (3-10)')
    parser.add_argument('--limit', '-l', type=int, default=20, help='Ограничение количества отображаемых транзакций')
    
    args = parser.parse_args()
    
    # Проверка существования файла
    if not os.path.exists(args.file):
        print(f"{Fore.RED}Ошибка: Файл {args.file} не найден{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.WHITE}АНАЛИЗ ТРАНЗАКЦИЙ НА ПРЕДМЕТ РИСКОВ ОД/ФТ")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    # Обрабатываем все транзакции
    risky_transactions = process_all_transactions(args.file, args.min_score, args.limit)
    
    if not risky_transactions:
        print(f"{Fore.YELLOW}Транзакций с рисками не найдено.{Style.RESET_ALL}")
        return
    
    # Выводим статистику по рискам
    print_rule_statistics(risky_transactions)
    
    # Выводим транзакции с высоким риском
    print_high_risk_transactions(risky_transactions, args.high_risk, args.limit)

if __name__ == "__main__":
    main() 