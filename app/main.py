import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(
    page_title="Индикативы",
    layout="wide",
    initial_sidebar_state="auto"
)

st.markdown("<h1 style='text-align: center;'>Отчёт сравнения МЗ различных SKU</h1>", unsafe_allow_html=True)

# Функция для преобразования чисел в названия месяцев
def month_number_to_name(month_number):
    month_mapping = {
        19: 'Июль',
        20: 'Август', 
        21: 'Сентябрь'
    }
    return month_mapping.get(month_number, f'Месяц {month_number}')

@st.cache_data
def load_total():  
    df_volume = pd.read_parquet("data/data_volume.parquet")
    return df_volume

df_volume = load_total()

# Создаем колонку с названиями месяцев для использования в интерфейсе
df_volume['Название_месяца'] = df_volume['Месяц'].map(month_number_to_name)

col1, col2 = st.columns(2)
    
positions = df_volume["Ном-ра, хар-ка"].unique()

with col1:
    pos1 = st.selectbox("Первая позиция:", options=positions)
    if pos1:
        # Используем названия месяцев в интерфейсе
        periods1_data = df_volume[df_volume["Ном-ра, хар-ка"].isin([pos1])]
        periods1_options = periods1_data["Название_месяца"].unique()
        pos1_per_name = st.selectbox("Месяц", options=periods1_options)
        
        # Находим соответствующий числовой месяц для фильтрации
        pos1_per_number = periods1_data[periods1_data["Название_месяца"] == pos1_per_name]["Месяц"].values[0]
        
        # Получаем все три значения
        quantity1 = df_volume.loc[(df_volume["Ном-ра, хар-ка"] == pos1) & 
                               (df_volume["Месяц"] == pos1_per_number)]["кол-во"].values[0]
        
        total_mz1 = df_volume.loc[(df_volume["Ном-ра, хар-ка"] == pos1) & 
                               (df_volume["Месяц"] == pos1_per_number)]["стоимость затрат"].values[0]
        
        mz_per_unit1 = total_mz1/quantity1
            
with col2:
    pos2 = st.selectbox("Вторая позиция:", options=positions, key="pos2")
    if pos2:
        # Используем названия месяцев в интерфейсе
        periods2_data = df_volume[df_volume["Ном-ра, хар-ка"].isin([pos2])]
        periods2_options = periods2_data["Название_месяца"].unique()
        pos2_per_name = st.selectbox("Месяц ", options=periods2_options, key="month2")
        
        # Находим соответствующий числовой месяц для фильтрации
        pos2_per_number = periods2_data[periods2_data["Название_месяца"] == pos2_per_name]["Месяц"].values[0]
        
        # Получаем все три значения
        quantity2 = df_volume.loc[(df_volume["Ном-ра, хар-ка"] == pos2) & 
                               (df_volume["Месяц"] == pos2_per_number)]["кол-во"].values[0]
        
        total_mz2 = df_volume.loc[(df_volume["Ном-ра, хар-ка"] == pos2) & 
                               (df_volume["Месяц"] == pos2_per_number)]["стоимость затрат"].values[0]
        
        mz_per_unit2 = total_mz2/quantity2

@st.cache_data
def load_data(period, poz):
    df = pd.read_parquet(f"data/df_period_{period}.parquet")
    df = df[df["позиция"].isin([poz])]
    df["Период"] = period
    return df

# Функция для подготовки данных Waterfall с группировкой - сравнение двух позиций
def prepare_waterfall_data(pos1_data, pos2_data, num_groups, pos1_name, pos2_name):
    # Агрегируем данные по группам век для каждой позиции
    pos1_totals = pos1_data.groupby('гр.ВЕК')['МЗ_ед'].sum()
    pos2_totals = pos2_data.groupby('гр.ВЕК')['МЗ_ед'].sum()
    
    # Объединяем данные по всем группам век
    all_groups = set(pos1_totals.index) | set(pos2_totals.index)
    
    # Создаем DataFrame с разницей между позициями
    comparison_data = []
    for group in all_groups:
        pos1_value = pos1_totals.get(group, 0)
        pos2_value = pos2_totals.get(group, 0)
        difference = pos2_value - pos1_value  # ИЗМЕНЕНИЕ: меняем порядок вычитания
        
        comparison_data.append({
            'Группа': group,
            'Позиция1': pos1_value,
            'Позиция2': pos2_value,
            'Разница': difference,  # Теперь разница показывает переход от pos1 к pos2
            'Абс_разница': abs(difference)
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Сортируем по абсолютной разнице
    sorted_groups = comparison_df.sort_values('Абс_разница', ascending=False)
    
    # Выбираем топ-N групп
    top_groups = sorted_groups.head(num_groups).copy()
    
    # Остальные группы объединяем в "Прочее"
    other_groups = sorted_groups.iloc[num_groups:]
    
    # Создаем результат с топ-группами
    result_df = top_groups[['Группа', 'Разница']]
    
    # Добавляем "Прочее" если есть остальные группы
    if not other_groups.empty and len(other_groups) > 0:
        other_row = pd.DataFrame({
            'Группа': ['Прочее'],
            'Разница': [other_groups['Разница'].sum()]
        })
        result_df = pd.concat([result_df, other_row], ignore_index=True)
    
    return result_df, pos1_totals.sum(), pos2_totals.sum(), pos1_name, pos2_name

# Функция для расчета оптимальных границ оси Y для waterfall chart
def calculate_waterfall_yaxis_range(start_value, end_value, relative_values, margin_percent=10):
    """
    Рассчитывает оптимальный диапазон для оси Y waterfall chart
    с учетом всех промежуточных изменений
    
    Args:
        start_value: начальное значение (первый столбец)
        end_value: конечное значение (последний столбец)
        relative_values: список относительных изменений
        margin_percent: запас в процентах
    """
    
    # Рассчитываем все промежуточные точки
    current_value = start_value
    all_values = [start_value]
    
    for change in relative_values:
        current_value += change
        all_values.append(current_value)
    
    # Добавляем конечное значение
    all_values.append(end_value)
    
    # Находим абсолютные минимум и максимум среди всех точек
    min_val = min(all_values)
    max_val = max(all_values)
    
    # Вычисляем диапазон значений
    value_range = max_val - min_val
    
    # Если все значения одинаковые, создаем небольшой диапазон
    if value_range == 0:
        if min_val == 0:
            return -10, 10  # Для нулевых значений
        else:
            margin = abs(min_val) * 0.1
            return min_val - margin, max_val + margin
    
    # Добавляем запас в процентах
    margin = value_range * margin_percent / 100
    
    # Устанавливаем границы с запасом
    y_min = min_val - margin
    y_max = max_val + margin
    
    # Гарантируем, что 0 будет виден если есть отрицательные значения
    if min_val < 0 and y_min > 0:
        y_min = min_val - margin
    
    return y_min, y_max

if pos1 and pos2:
    # Загружаем данные для выбранных позиций и периодов
    pos1_data = load_data(pos1_per_name, pos1)
    pos2_data = load_data(pos2_per_name, pos2)
    
    # Определяем логику отображения подписей
    if pos1 == pos2:
        # Если позиции одинаковые - показываем только месяцы
        pos1_display = f"{pos1_per_name}"
        pos2_display = f"{pos2_per_name}"
    else:
        # Если позиции разные - показываем и позицию и месяц
        pos1_display = f"{pos1} ({pos1_per_name})"
        pos2_display = f"{pos2} ({pos2_per_name})"
    
    # Объединяем данные
    combined_data = pd.concat([pos1_data, pos2_data])
    
    # Создаем сводную таблицу
    pivot_table_first = pd.pivot_table(combined_data, 
                                       values = ["кол_во_затрат_ед", "МЗ_ед", "МЗ_ед_скв"],
                                       index = ["гр.ВЕК", "Сырье"],
                                       columns = ["Период"],
                                       aggfunc = "sum"
                                       )
    pivot_table_first.columns = pivot_table_first.columns.map('_'.join)
    
    # Сохраняем в Excel
    pivot_table_first.to_excel("cc.xlsx")
    
    # ========== НОВОЕ РАСПОЛОЖЕНИЕ: 80% WATERFALL + 20% КАРТОЧКИ ==========
    st.markdown("---")
    st.subheader("🌊 Waterfall Chart - Сравнение позиций по группам век")
    
    # Настройка количества отображаемых групп
    max_groups = len(set(pos1_data['гр.ВЕК']) | set(pos2_data['гр.ВЕК']))
    num_groups = st.slider(
        "Количество групп:",
        min_value=1,
        max_value=min(20, max_groups),
        value=min(5, max_groups),
        help="Выберите количество групп для отображения в Waterfall chart"
    )
    
    # Подготавливаем данные для Waterfall с группировкой
    waterfall_df, total_pos1, total_pos2, pos1_final, pos2_final = prepare_waterfall_data(
        pos1_data, pos2_data, num_groups, pos1_display, pos2_display
    )
    
    # Создаем колонки: 80% для waterfall, 20% для карточек
    waterfall_col, cards_col = st.columns([8, 2])  # 80% / 20%
    
    with waterfall_col:
        # Создаем Waterfall chart для сравнения позиций
        fig_waterfall = go.Figure()
        
        # Подготовка данных для waterfall - НАЧИНАЕМ С POS1
        categories = []
        values = []
        measures = []
        relative_changes = []
        
        # НАЧАЛЬНОЕ ЗНАЧЕНИЕ (POS1) - ИЗМЕНЕНИЕ
        categories.append(pos1_final)
        values.append(total_pos1)
        measures.append("absolute")
        
        # Разницы по группам (топ-N + Прочее)
        for _, row in waterfall_df.iterrows():
            difference = row['Разница']
            categories.append(f"{row['Группа']}")
            values.append(difference)
            measures.append("relative")
            relative_changes.append(difference)
        
        # КОНЕЧНОЕ ЗНАЧЕНИЕ (POS2) - ИЗМЕНЕНИЕ
        categories.append(pos2_final)
        values.append(total_pos2)
        measures.append("total")
        
        # Рассчитываем оптимальные границы для оси Y
        y_min, y_max = calculate_waterfall_yaxis_range(
            total_pos1,  # ИЗМЕНЕНИЕ: начинаем с total_pos1
            total_pos2,  # ИЗМЕНЕНИЕ: заканчиваем total_pos2
            relative_changes, 
            margin_percent=20
        )
        
        # Создаем waterfall с правильными цветами
        fig_waterfall.add_trace(go.Waterfall(
            name="МЗ",
            orientation="v",
            measure=measures,
            x=categories,
            y=values,
            textposition="outside",
            text=[f"{v:,.0f}" for v in values],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            
            # Правильное задание цветов для Waterfall chart
            decreasing={"marker": {"color": "#35B124"}},  # Красный для отрицательных изменений
            increasing={"marker": {"color": "#E43D38"}},  # Синий для положительных изменений
            totals={"marker": {"color": "#8c8d8f"}},      # Темно-синий для первого и последнего столбцов
            
            base=0
        ))
        
        # НАСТРОЙКИ ШРИФТА - УВЕЛИЧЕННЫЕ РАЗМЕРЫ (ИСПРАВЛЕННАЯ ВЕРСИЯ)
        fig_waterfall.update_layout(
            title=f" ",
            xaxis_title="Группы век",
            yaxis_title="МЗ (руб.)",
            showlegend=False,
            height=800,
            
            # НАСТРОЙКИ ШРИФТА - УВЕЛИЧЕННЫЕ РАЗМЕРЫ
            font=dict(
                family="Arial, sans-serif",
                size=16,  # Основной размер шрифта увеличен
                color="black"
            ),
            
            # Настройки шрифта для оси X
            xaxis=dict(
                title_font=dict(size=18, family="Arial", color="black"),
                tickfont=dict(size=18, family="Arial"),
                title_standoff=25
            ),
            
            # Настройки шрифта для оси Y
            yaxis=dict(
                title_font=dict(size=18, family="Arial", color="black"),
                tickfont=dict(size=18, family="Arial"),
                range=[y_min, y_max],
                autorange=False
            ),
            
            # Настройки отступов
            margin=dict(l=80, r=80, t=80, b=120)  # Увеличил нижний отступ для подписей
        )
        
        # Увеличиваем шрифт в текстовых подписях на столбцах
        fig_waterfall.update_traces(
            texttemplate='%{text}',
            textfont=dict(
                family="Arial, sans-serif",
                size=14,  # Увеличенный размер шрифта для чисел на столбцах
                color="black"
            )
        )
        
        st.plotly_chart(fig_waterfall, use_container_width=True)
    
    with cards_col:
        st.markdown("### 📊 Ключевые метрики")
        
        # Карточка 1: МЗ позиции 1
        st.metric(
            label=f"МЗ позиция 1",
            value=f"{total_pos1:,.0f}",
            delta=None,
            help=f"Общий МЗ для {pos1}"
        )
        
        st.markdown("---")
        
        # Карточка 2: МЗ позиции 2
        st.metric(
            label=f"МЗ позиция 2",
            value=f"{total_pos2:,.0f}",
            delta=None,
            help=f"Общий МЗ для {pos2}"
        )
        
        st.markdown("---")
        
        # Карточка 3: Абсолютная разница
        total_difference = total_pos2 - total_pos1  # ИЗМЕНЕНИЕ: pos2 - pos1
        difference_percent = (total_difference / total_pos1 * 100) if total_pos1 != 0 else 0

        delta_color = "inverse"  # Теперь нормальные цвета: зеленый для уменьшения, красный для увеличения

        st.metric(
            label="Абсолютная разница",
            value=f"{abs(total_difference):,.0f} руб.",
            delta=f"{difference_percent:+.1f}%",
            delta_color=delta_color
        )
        
        
        st.markdown("---")
        
        # Дополнительная информация
        if total_difference > 0:
            st.error(f"**{pos2.split()[0] if len(pos2) > 20 else pos2}** дороже на **{abs(total_difference):,.0f} руб.**")
        elif total_difference < 0:
            st.success(f"**{pos2.split()[0] if len(pos2) > 20 else pos2}** дешевле на **{abs(total_difference):,.0f} руб.**")
        else:
            st.info("Стоимости равны")
    
    # Детализация по группам
    with st.expander("📊 Детализация по группам"):
        # Создаем таблицу с детализацией
        detail_table = waterfall_df.copy()
        detail_table['% от общей разницы'] = (detail_table['Разница'] / total_difference * 100).round(1)
        detail_table = detail_table.sort_values('Разница', key=abs, ascending=False)
        
        st.dataframe(
            detail_table.style.format({
                'Разница': '{:+,.0f}',
                '% от общей разницы': '{:+.1f}%'
            }),
            use_container_width=True
        )
        
        # Показываем сколько групп объединено в "Прочее"
        if 'Прочее' in detail_table['Группа'].values:
            other_count = max_groups - num_groups
            st.info(f"В категорию 'Прочее' объединено {other_count} групп")
    
    # Показываем исходные данные
    with st.expander("📋 Посмотреть исходные данные"):
        st.dataframe(pivot_table_first, use_container_width=True)
        
        # Кнопка для скачивания данных
        csv = pivot_table_first.to_csv().encode('utf-8')
        st.download_button(
            label="📥 Скачать данные (CSV)",
            data=csv,
            file_name="мз_анализ.csv",
            mime="text/csv"
        )