import streamlit as st
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
import sys
import io
import base64

# Импортируем функции из check_all_transactions.py
from check_all_transactions import (
    MONITORING_SETTINGS, MONITORING_RULES, RULE_NAMES_RU,
    is_threshold_exceeded, is_high_risk_jurisdiction, is_missing_recipient,
    is_missing_payment_purpose, is_suspicious_activity, is_unusual_transaction_type,
    is_blacklisted_entity, is_round_amount, is_structured_transaction, is_high_risk_client,
    check_all_aml_rules, format_amount, get_person_info
)

st.set_page_config(
    page_title="Анализ транзакций - АML Мониторинг",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Функция для настройки параметров мониторинга
def settings_page():
    st.title("⚙️ Настройки мониторинга")
    
    st.markdown("### Пороговые значения")
    threshold_amount = st.number_input(
        "Пороговая сумма для крупных операций",
        min_value=1000000, 
        max_value=100000000,
        value=MONITORING_SETTINGS["threshold_amount"],
        step=1000000,
        format="%d"
    )
    
    st.markdown("### Страны высокого риска")
    countries_text = st.text_area(
        "Коды стран высокого риска (через запятую)",
        value=", ".join(map(str, MONITORING_SETTINGS["high_risk_countries"])),
        height=100
    )
    high_risk_countries = [int(code.strip()) for code in countries_text.split(",") if code.strip().isdigit()]
    
    st.markdown("### Типы высокорисковых операций")
    operation_types_text = st.text_area(
        "Коды типов высокорисковых операций (через запятую)",
        value=", ".join(map(str, MONITORING_SETTINGS["high_risk_operation_types"])),
        height=100
    )
    high_risk_operation_types = [int(code.strip()) for code in operation_types_text.split(",") if code.strip().isdigit()]
    
    st.markdown("### Диапазон подозрительных сумм")
    col1, col2 = st.columns(2)
    with col1:
        min_suspicious = st.number_input(
            "Минимальная сумма",
            min_value=1000000,
            max_value=50000000,
            value=MONITORING_SETTINGS["suspicious_amount_range"][0],
            step=1000000,
            format="%d"
        )
    with col2:
        max_suspicious = st.number_input(
            "Максимальная сумма",
            min_value=1000000,
            max_value=50000000,
            value=MONITORING_SETTINGS["suspicious_amount_range"][1],
            step=1000000,
            format="%d"
        )
    
    # Обновляем настройки
    if st.button("Сохранить настройки"):
        MONITORING_SETTINGS["threshold_amount"] = threshold_amount
        MONITORING_SETTINGS["high_risk_countries"] = high_risk_countries
        MONITORING_SETTINGS["high_risk_operation_types"] = high_risk_operation_types
        MONITORING_SETTINGS["suspicious_amount_range"] = [min_suspicious, max_suspicious]
        
        st.success("Настройки успешно обновлены!")
        st.json(MONITORING_SETTINGS)

# Функция для анализа загруженного файла
def process_uploaded_file(uploaded_file, min_risk_score=1):
    try:
        # Загружаем содержимое файла
        file_content = uploaded_file.read()
        data = json.loads(file_content)
        
        # Определяем структуру данных
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict) and 'messages' in data:
            messages = data['messages']
        else:
            messages = [data]
        
        total_count = len(messages)
        st.info(f"Загружено {total_count} сообщений для анализа...")
        
        # Создаем прогресс-бар
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        risky_transactions = []
        tx_count = 0
        
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
                
                # Обновляем прогресс
                progress = (i + 1) / total_count
                progress_bar.progress(progress)
                status_text.text(f"Прогресс: {progress*100:.1f}% ({i+1}/{total_count})")
        
        status_text.text(f"Анализ завершен. Проанализировано {tx_count} транзакций.")
        return risky_transactions, tx_count
        
    except json.JSONDecodeError as e:
        st.error(f"Ошибка при декодировании JSON: {e}")
        return [], 0
        
    except Exception as e:
        st.error(f"Произошла ошибка: {e}")
        return [], 0

# Функция для подготовки DataFrame с результатами
def prepare_results_dataframe(risky_transactions):
    data = []
    
    for tx in risky_transactions:
        tx_data = tx['tx_data']
        
        # Формируем строку данных
        tx_row = {
            'ID': tx_data.get('gmess_id', ''),
            'Дата': tx_data.get('goper_trans_date', '')[:10] if tx_data.get('goper_trans_date') else '',
            'Сумма': tx_data.get('goper_tenge_amount', 0),
            'Плательщик': get_person_info(tx_data, True),
            'Получатель': get_person_info(tx_data, False),
            'Оценка риска': tx['risk_score'],
            'Уровень риска': tx['risk_level']
        }
        
        # Добавляем флаги для каждого правила
        for rule in MONITORING_RULES:
            tx_row[rule] = tx.get(rule, 0)
        
        data.append(tx_row)
    
    # Создаем DataFrame
    df = pd.DataFrame(data)
    
    # Преобразуем сумму в числовой формат
    df['Сумма'] = pd.to_numeric(df['Сумма'], errors='coerce')
    
    return df

# Функция для отображения статистики
def show_statistics(df, total_transactions):
    st.title("📊 Статистика")
    
    # Общая статистика
    high_risk_count = len(df[df['Уровень риска'] == 'Высокий'])
    medium_risk_count = len(df[df['Уровень риска'] == 'Средний'])
    low_risk_count = len(df[df['Уровень риска'] == 'Низкий'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Транзакций с высоким риском", f"{high_risk_count} ({high_risk_count/total_transactions:.1%})")
    with col2:
        st.metric("Транзакций со средним риском", f"{medium_risk_count} ({medium_risk_count/total_transactions:.1%})")
    with col3:
        st.metric("Транзакций с низким риском", f"{low_risk_count} ({low_risk_count/total_transactions:.1%})")
    
    # Гистограмма по оценкам риска
    fig = px.histogram(
        df, 
        x='Оценка риска', 
        color='Уровень риска',
        color_discrete_map={'Высокий': 'red', 'Средний': 'orange', 'Низкий': 'green'},
        title='Распределение транзакций по оценке риска'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Статистика по сработавшим правилам
    st.subheader("Частота срабатывания правил")
    
    rule_stats = {}
    rule_names = {}
    for rule in MONITORING_RULES:
        rule_stats[rule] = df[rule].sum()
        rule_names[rule] = RULE_NAMES_RU.get(rule, rule)
    
    rule_stats_df = pd.DataFrame({
        'Правило': [rule_names[rule] for rule in rule_stats.keys()],
        'Код правила': list(rule_stats.keys()),
        'Количество': list(rule_stats.values()),
        'Процент': [count / len(df) * 100 for count in rule_stats.values()]
    })
    rule_stats_df = rule_stats_df.sort_values('Количество', ascending=False)
    
    fig2 = px.bar(
        rule_stats_df,
        x='Правило',
        y='Процент',
        color='Процент',
        title='Процент срабатывания каждого правила',
        color_continuous_scale='Reds'
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Суммы транзакций
    st.subheader("Распределение сумм транзакций")
    
    fig3 = px.box(
        df,
        y='Сумма',
        color='Уровень риска',
        color_discrete_map={'Высокий': 'red', 'Средний': 'orange', 'Низкий': 'green'},
        points="all",
        title='Распределение сумм транзакций по уровню риска'
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    # Топ-10 крупнейших транзакций
    st.subheader("ТОП-10 транзакций по сумме")
    top_by_amount = df.sort_values('Сумма', ascending=False).head(10)
    st.dataframe(
        top_by_amount[['ID', 'Дата', 'Сумма', 'Плательщик', 'Получатель', 'Оценка риска', 'Уровень риска']],
        use_container_width=True
    )
    
    # Топ-10 транзакций по оценке риска
    st.subheader("ТОП-10 транзакций по оценке риска")
    top_by_risk = df.sort_values('Оценка риска', ascending=False).head(10)
    st.dataframe(
        top_by_risk[['ID', 'Дата', 'Сумма', 'Плательщик', 'Получатель', 'Оценка риска', 'Уровень риска']],
        use_container_width=True
    )

# Функция для отображения результатов
def show_results(df):
    st.title("🔍 Детальный анализ")
    
    # Проверяем, есть ли данные
    if df.empty:
        st.warning("Нет данных для отображения.")
        return
    
    # Настройки фильтров
    st.sidebar.header("Фильтры")
    
    # Фильтр по уровню риска
    risk_levels = df['Уровень риска'].unique().tolist()
    selected_risk_levels = st.sidebar.multiselect(
        "Уровень риска",
        options=risk_levels,
        default=risk_levels
    )
    
    # Фильтр по оценке риска
    min_score = int(df['Оценка риска'].min())
    max_score = int(df['Оценка риска'].max())
    selected_score_range = st.sidebar.slider(
        "Оценка риска",
        min_value=min_score,
        max_value=max_score,
        value=(min_score, max_score)
    )
    
    # Фильтр по диапазону сумм
    min_amount = float(df['Сумма'].min())
    max_amount = float(df['Сумма'].max())
    selected_amount_range = st.sidebar.slider(
        "Диапазон сумм",
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount),
        format="%.0f"
    )
    
    # Фильтр по правилам
    rule_options = {RULE_NAMES_RU.get(rule, rule): rule for rule in MONITORING_RULES}
    selected_rule_names = st.sidebar.multiselect(
        "Сработавшие правила",
        options=list(rule_options.keys()),
        default=[]
    )
    selected_rules = [rule_options[name] for name in selected_rule_names]
    
    # Применяем фильтры
    mask = (
        df['Уровень риска'].isin(selected_risk_levels) &
        (df['Оценка риска'] >= selected_score_range[0]) &
        (df['Оценка риска'] <= selected_score_range[1]) &
        (df['Сумма'] >= selected_amount_range[0]) &
        (df['Сумма'] <= selected_amount_range[1])
    )
    
    # Фильтр по правилам
    if selected_rules:
        rule_mask = df[selected_rules[0]] == 1
        for rule in selected_rules[1:]:
            rule_mask = rule_mask & (df[rule] == 1)
        mask = mask & rule_mask
    
    filtered_df = df[mask]
    
    # Результаты фильтрации
    st.subheader(f"Найдено {len(filtered_df)} транзакций")
    
    # Опции отображения
    st.sidebar.header("Отображение")
    sort_by = st.sidebar.selectbox(
        "Сортировать по",
        options=["Оценка риска", "Сумма", "Дата", "ID"],
        index=0
    )
    
    sort_order = st.sidebar.radio(
        "Порядок сортировки",
        options=["По убыванию", "По возрастанию"],
        index=0
    )
    
    # Применяем сортировку
    ascending = sort_order == "По возрастанию"
    filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)
    
    # Пагинация
    rows_per_page = st.sidebar.slider(
        "Строк на странице",
        min_value=10,
        max_value=100,
        value=25,
        step=5
    )
    
    total_pages = max(1, len(filtered_df) // rows_per_page + (1 if len(filtered_df) % rows_per_page > 0 else 0))
    
    if total_pages > 1:
        page = st.sidebar.number_input(
            f"Страница (всего {total_pages})",
            min_value=1,
            max_value=total_pages,
            value=1
        )
    else:
        page = 1
    
    start_idx = (page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, len(filtered_df))
    
    # Отображаем таблицу результатов
    st.dataframe(
        filtered_df.iloc[start_idx:end_idx][['ID', 'Дата', 'Сумма', 'Плательщик', 'Получатель', 'Оценка риска', 'Уровень риска']],
        use_container_width=True,
        height=500
    )
    
    # Экспорт результатов
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Скачать результаты в CSV",
            data=csv,
            file_name="risky_transactions.csv",
            mime="text/csv",
        )
    
    # Просмотр деталей транзакции
    st.subheader("Детали транзакции")
    
    selected_tx_id = st.selectbox(
        "Выберите ID транзакции для просмотра деталей",
        options=filtered_df['ID'].unique().tolist(),
        format_func=lambda x: f"ID: {x}"
    )
    
    if selected_tx_id:
        selected_tx = filtered_df[filtered_df['ID'] == selected_tx_id].iloc[0]
        tx_data = None
        
        # Находим данные транзакции
        for tx in st.session_state.risky_transactions:
            if tx['tx_data'].get('gmess_id') == selected_tx_id:
                tx_data = tx['tx_data']
                aml_results = {k: v for k, v in tx.items() if k != 'tx_data'}
                break
        
        if tx_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Основная информация")
                st.markdown(f"**ID:** {tx_data.get('gmess_id')}")
                st.markdown(f"**Дата:** {tx_data.get('goper_trans_date')}")
                st.markdown(f"**Сумма:** {format_amount(tx_data.get('goper_tenge_amount', 0))} тенге")
                st.markdown(f"**Тип операции:** {tx_data.get('goper_idview')} (вид), {tx_data.get('goper_idtype')} (тип)")
                
                st.subheader("Назначение платежа")
                st.text_area("", value=tx_data.get('goper_dopinfo', 'Не указано'), height=150, disabled=True)
                
                st.subheader("Плательщик")
                st.markdown(f"**Имя:** {tx_data.get('gmember_name_pl1', 'Не указан')}")
                st.markdown(f"**ИИН/БИН:** {tx_data.get('gmember_maincode_pl1', 'Не указан')}")
                st.markdown(f"**Страна:** {tx_data.get('gmember_residence_pl1', 'Не указана')}")
                
                st.subheader("Получатель")
                st.markdown(f"**Имя:** {tx_data.get('gmember_name_pol1', 'Не указан')}")
                st.markdown(f"**ИИН/БИН:** {tx_data.get('gmember_maincode_pol1', 'Не указан')}")
                st.markdown(f"**Страна:** {tx_data.get('gmember_residence_pol1', 'Не указана')}")
                
            with col2:
                st.subheader("Результаты проверки")
                st.markdown(f"**Оценка риска:** {aml_results['risk_score']}/10")
                st.markdown(f"**Уровень риска:** {aml_results['risk_level']}")
                
                st.subheader("Сработавшие правила")
                triggered_rules = []
                for rule in MONITORING_RULES:
                    if aml_results.get(rule, 0) == 1:
                        triggered_rules.append(rule)
                
                if triggered_rules:
                    for rule in triggered_rules:
                        rule_name = RULE_NAMES_RU.get(rule, rule)
                        st.markdown(f"- {rule_name}")
                else:
                    st.markdown("Нет сработавших правил")
                
                st.subheader("Рекомендации")
                if aml_results['risk_level'] == 'Высокий':
                    st.warning("""
                    Рекомендуется тщательная проверка транзакции и участников.
                    Возможно потребуется направление сообщения в АФМ.
                    """)
                    
                    if aml_results.get('missing_recipient') == 1:
                        st.info("* Необходимо запросить информацию о получателе денежных средств.")
                    
                    if aml_results.get('threshold_exceeded') == 1:
                        st.info("* Требуется проверка источника происхождения средств.")
                        
                    if aml_results.get('high_risk_client') == 1:
                        st.info("* Требуется обновить данные о клиенте и провести углубленную проверку.")
                        
                elif aml_results['risk_level'] == 'Средний':
                    st.info("""
                    Рекомендуется дополнительная проверка по сработавшим индикаторам.
                    """)
                    
                    if aml_results.get('unusual_transaction_type') == 1:
                        st.info("* Проверьте соответствие операции профилю клиента.")
                        
                    if aml_results.get('round_amount') == 1:
                        st.info("* Изучите историю операций для выявления паттернов.")
                else:
                    st.success("Особых рекомендаций нет, транзакция имеет низкий уровень риска.")
                
                # Дополнительные данные
                st.subheader("Дополнительная информация")
                
                with st.expander("Все поля транзакции"):
                    for key, value in tx_data.items():
                        if key.startswith('gmember') or key.startswith('goper') or key.startswith('gcfm'):
                            st.markdown(f"**{key}:** {value}")

# Главная функция
def main():
    st.sidebar.image("https://www.astanatimes.com/wp-content/uploads/2022/07/FIU_AFMRK.png", width=200)
    st.sidebar.title("AML Мониторинг")
    
    # Инициализируем сессионные переменные, если они еще не существуют
    if 'risky_transactions' not in st.session_state:
        st.session_state.risky_transactions = []
    
    if 'total_transactions' not in st.session_state:
        st.session_state.total_transactions = 0
    
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    
    # Навигация
    page = st.sidebar.radio(
        "Навигация",
        options=["Загрузка данных", "Статистика", "Детальный анализ", "Настройки"]
    )
    
    # Страница загрузки данных
    if page == "Загрузка данных":
        st.title("📁 Загрузка данных")
        
        st.write("""
        Загрузите файл с транзакциями в формате JSON для анализа. 
        Система проверит каждую транзакцию на соответствие правилам AML и выделит подозрительные операции.
        """)
        
        uploaded_file = st.file_uploader("Выберите файл JSON", type=["json"])
        
        min_risk_score = st.slider(
            "Минимальная оценка риска для включения в результаты",
            min_value=1,
            max_value=10,
            value=1
        )
        
        if uploaded_file is not None:
            if st.button("Начать анализ"):
                with st.spinner("Выполняется анализ данных..."):
                    risky_transactions, total_transactions = process_uploaded_file(uploaded_file, min_risk_score)
                    
                    if risky_transactions:
                        # Сохраняем результаты в сессии
                        st.session_state.risky_transactions = risky_transactions
                        st.session_state.total_transactions = total_transactions
                        
                        # Подготавливаем DataFrame для анализа
                        results_df = prepare_results_dataframe(risky_transactions)
                        st.session_state.results_df = results_df
                        
                        st.success(f"Анализ завершен! Найдено {len(risky_transactions)} транзакций с рисками.")
                        st.balloons()
                        
                        # Переход к следующей странице
                        st.markdown("### [Перейти к статистике](#Статистика)")
                    else:
                        st.warning("Транзакций с рисками не найдено, или произошла ошибка при обработке файла.")
                        
    # Страница статистики
    elif page == "Статистика":
        if st.session_state.results_df is not None:
            show_statistics(st.session_state.results_df, st.session_state.total_transactions)
        else:
            st.warning("Нет данных для отображения. Сначала загрузите и проанализируйте файл с транзакциями.")
    
    # Страница детального анализа
    elif page == "Детальный анализ":
        if st.session_state.results_df is not None:
            show_results(st.session_state.results_df)
        else:
            st.warning("Нет данных для отображения. Сначала загрузите и проанализируйте файл с транзакциями.")
    
    # Страница настроек
    elif page == "Настройки":
        settings_page()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("© 2023 AML Мониторинг")

if __name__ == "__main__":
    main() 