import json
from datetime import datetime, timedelta
import os

# Идентификаторы транзакций для проверки
tx_ids = [67808456, 67808459]

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
    purpose = tx_data.get('goper_dopinfo', '').lower()
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
    purpose = tx_data.get('goper_dopinfo', '').lower()
    
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

# ============= Основной код =============

def main():
    try:
        # Проверяем существование файла
        json_file_path = 'json do_range.json'
        if not os.path.exists(json_file_path):
            print(f"Ошибка: Файл {json_file_path} не найден")
            return
            
        # Открываем исходный JSON-файл
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            # Определяем структуру данных
            if isinstance(data, list):
                messages = data
            elif isinstance(data, dict) and 'messages' in data:
                messages = data['messages']
            else:
                messages = [data]
            
            print(f"Загружено {len(messages)} сообщений")
            
            # Ищем нужные транзакции
            found = False
            for msg in messages:
                if 'row_to_json' in msg and msg['row_to_json'].get('gmess_id') in tx_ids:
                    tx_data = msg['row_to_json']
                    found = True
                    
                    print(f"\n{'='*80}")
                    print(f"АНАЛИЗ ТРАНЗАКЦИИ")
                    print(f"{'='*80}")
                    print(f"ID транзакции: {tx_data.get('gmess_id')}")
                    print(f"Дата операции: {tx_data.get('goper_trans_date')}")
                    print(f"Сумма: {tx_data.get('goper_tenge_amount'):,} тенге".replace(',', ' '))
                    print(f"Тип операции: {tx_data.get('goper_idview')} (вид), {tx_data.get('goper_idtype')} (тип)")
                    
                    # Информация о назначении
                    print(f"\nНазначение платежа:")
                    print(f"{tx_data.get('goper_dopinfo')}")
                    
                    # Информация о плательщике
                    print("\nПлательщик (pl1):")
                    print(f"  Имя: {tx_data.get('gmember_name_pl1')}")
                    print(f"  ИИН/БИН: {tx_data.get('gmember_maincode_pl1')}")
                    print(f"  Страна: {tx_data.get('gmember_residence_pl1')}")
                    print(f"  Тип: {tx_data.get('gmember_type_pl1')}")
                    
                    if tx_data.get('gmember_name_pl2'):
                        print("\nПлательщик (pl2):")
                        print(f"  Имя: {tx_data.get('gmember_name_pl2')}")
                        print(f"  ИИН/БИН: {tx_data.get('gmember_maincode_pl2')}")
                        print(f"  Страна: {tx_data.get('gmember_residence_pl2')}")
                        print(f"  Тип: {tx_data.get('gmember_type_pl2')}")
                    
                    # Информация о получателе
                    print("\nПолучатель (pol1):")
                    print(f"  Имя: {tx_data.get('gmember_name_pol1') or 'Не указан'}")
                    print(f"  ИИН/БИН: {tx_data.get('gmember_maincode_pol1') or 'Не указан'}")
                    print(f"  Страна: {tx_data.get('gmember_residence_pol1') or 'Не указана'}")
                    print(f"  Тип: {tx_data.get('gmember_type_pol1') or 'Не указан'}")
                    
                    if tx_data.get('gmember_name_pol2'):
                        print("\nПолучатель (pol2):")
                        print(f"  Имя: {tx_data.get('gmember_name_pol2')}")
                        print(f"  ИИН/БИН: {tx_data.get('gmember_maincode_pol2')}")
                        print(f"  Страна: {tx_data.get('gmember_residence_pol2')}")
                        print(f"  Тип: {tx_data.get('gmember_type_pol2')}")
                    
                    # Дополнительная информация из полей gmemberX
                    print("\nДополнительная информация:")
                    if tx_data.get("gmember1_maincode"):
                        print("\nУчастник 1:")
                        print(f"  ИИН/БИН: {tx_data.get('gmember1_maincode')}")
                        print(f"  Тип: {tx_data.get('gmember1_member_type')}")
                        
                        if tx_data.get('gmember1_ur_name'):
                            print(f"  Наименование ЮЛ: {tx_data.get('gmember1_ur_name')}")
                        else:
                            print(f"  ФИО: {tx_data.get('gmember1_ac_secondname')} {tx_data.get('gmember1_ac_firstname')} {tx_data.get('gmember1_ac_middlename')}")
                    
                    if tx_data.get("gmember2_maincode"):
                        print("\nУчастник 2:")
                        print(f"  ИИН/БИН: {tx_data.get('gmember2_maincode')}")
                        print(f"  Тип: {tx_data.get('gmember2_member_type')}")
                        
                        if tx_data.get('gmember2_ur_name'):
                            print(f"  Наименование ЮЛ: {tx_data.get('gmember2_ur_name')}")
                        else:
                            print(f"  ФИО: {tx_data.get('gmember2_ac_secondname')} {tx_data.get('gmember2_ac_firstname')} {tx_data.get('gmember2_ac_middlename')}")
                    
                    # Выполняем проверку на AML
                    aml_results = check_all_aml_rules(tx_data)
                    
                    print(f"\n{'='*80}")
                    print(f"РЕЗУЛЬТАТЫ ПРОВЕРКИ РИСКОВ")
                    print(f"{'='*80}")
                    print(f"Оценка риска: {aml_results['risk_score']} из 10")
                    print(f"Уровень риска: {aml_results['risk_level']}")
                    print(f"\nСработавшие правила:")
                    
                    triggered_rules = []
                    for rule in MONITORING_RULES:
                        if rule in aml_results and aml_results[rule] == 1:
                            triggered_rules.append(rule)
                    
                    if triggered_rules:
                        for rule in triggered_rules:
                            print(f"  - {rule}")
                    else:
                        print("  Нет сработавших правил")
                    
                    # Добавим рекомендации по дальнейшим действиям
                    print(f"\n{'='*80}")
                    print(f"РЕКОМЕНДАЦИИ")
                    print(f"{'='*80}")
                    
                    if aml_results['risk_level'] == 'Высокий':
                        print("Рекомендуется тщательная проверка транзакции и участников.")
                        print("Возможно потребуется направление сообщения в АФМ.")
                        
                        if aml_results.get('missing_recipient') == 1:
                            print("* Необходимо запросить информацию о получателе денежных средств.")
                        
                        if aml_results.get('threshold_exceeded') == 1:
                            print("* Требуется проверка источника происхождения средств.")
                            
                        if aml_results.get('high_risk_client') == 1:
                            print("* Требуется обновить данные о клиенте и провести углубленную проверку.")
                            
                    elif aml_results['risk_level'] == 'Средний':
                        print("Рекомендуется дополнительная проверка по сработавшим индикаторам.")
                        
                        if aml_results.get('unusual_transaction_type') == 1:
                            print("* Проверьте соответствие операции профилю клиента.")
                            
                        if aml_results.get('round_amount') == 1:
                            print("* Изучите историю операций для выявления паттернов.")
                    else:
                        print("Особых рекомендаций нет, транзакция имеет низкий уровень риска.")
                    
                    print(f"{'='*80}")
                    
            if not found:
                print(f"Транзакции с ID {tx_ids} не найдены в исходных данных")

    except FileNotFoundError:
        print("Файл json do_range.json не найден")
    except json.JSONDecodeError as e:
        print(f"Ошибка при декодировании JSON: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main() 