import streamlit as st
import pandas as pd
import os
import io
from textwrap import wrap
import plotly.express as px

st.set_page_config(page_title='Askona', layout = 'wide', page_icon = 'logo.png', initial_sidebar_state = 'auto')

st.title("Сравнение")

source_dir = "pages/source"
files = [f.split('.')[0][12:] for f in os.listdir(source_dir) if f.startswith("output_") and f.endswith(".parquet")]

selected_file = st.selectbox("Месяц", files)

month = selected_file
file = source_dir + "/output_xlsb_" + selected_file + ".parquet"
#print(file)
if selected_file:
    #file_path = os.path.join(source_dir, file)
    file_path = file
    data = pd.read_parquet(file_path)
df = pd.DataFrame(
    {
    "nuzhno_1": data["nuzhno_1"],
    "nuzhno_2": data["nuzhno_2"],
    "crude": data['crude'],
    "gfu": data['gfu'],
    "izm": data['izm'],
    "gau": data['gau'],
    "volume": data['new_volume'],
    "costs": data['new_costs'],
    "cost_crude": data['new_cost_crude'],
    "gp_name": data['gau_gp']
    }
)

df['gp_name_cat'] = df['gp_name'].astype('category')
df.set_index('gp_name_cat', inplace=True)


# это для графиков по выбранным позициям (как в main)
@st.cache_data
def load_data():
    data = pd.read_parquet(r"pages/output_xlsb.parquet")
    df = pd.DataFrame(data)
    
    df["day"] = "1"
    df["month"] = df["month"].astype(str)
    df["year"] = df["year"].astype(str)
    df["date"] = df[["month", "day", "year"]].agg(".".join, axis = 1)
    df["date"] = pd.to_datetime(df["date"])
    df["index"] = df["Name"].astype('category')
    df['Group'] = df["Name"].str.split().str[0]
    df.set_index('index', inplace = True)
    df.drop(["month", "year", "day"], axis = 1, inplace = True)
    return df
df_line = load_data()  
names = df_line["Name"].unique()

# нужно написать выбор только сырья
df = df[df["gau"].notna()]
df = df[~df["nuzhno_1"].notna()]
df = df[~df["gfu"].str.contains("ГП Солвис|ГП Литвуд & Солвис|ПФ Солвис|ПФ Литвуд & Солвис", na=False)]

# справочник сырья и гр.ВЕК
spr_crude = df[["crude","gau"]]
spr_crude.reset_index(inplace = True)
del spr_crude["gp_name_cat"]
spr_crude = spr_crude.drop_duplicates(subset = ["crude","gau"])

# добавляем аплоудер на сайдбар
uploaded_file = st.sidebar.file_uploader("Загружаем .xlsx файл с нужными позициями", type=["xlsx"])

if uploaded_file:
    df_uploaded = pd.read_excel(uploaded_file)
    
    
    positions_from_file = df_uploaded.iloc[:, 0].tolist()
    if positions_from_file:
        #st.balloons() до лучших времен ((
        st.toast('Файл успешно загружен 😉')
    # можно удалить потом, сделал, чтобы пользователь мог видеть что содержится в файле
    
    # Извлекаем уникальные имена
    names = set([i for i in df["gp_name"].unique()])
    
    diff = set(positions_from_file) - names
    if diff:
        st.error(f"В файле есть позиции ({len(diff)} шт.), которых нет в источнике")
        with st.expander("Показать позиции, которых нет в источнике"):
            df_exp = pd.DataFrame(data = set(positions_from_file) - names)
            df_exp.rename( columns = {0: "Позиции"}, inplace = True)
            st.dataframe(df_exp, hide_index = True, use_container_width=True)
            
            
    positions_from_file = [i for i  in set(positions_from_file)&names]
    st.success(f"Загружено {len(positions_from_file)} позиций:")
    with st.expander("Показать загруженные позиции"):
        df_exp = pd.DataFrame(positions_from_file)
        df_exp.rename( columns = {0: "Позиции"}, inplace = True)
        st.dataframe(df_exp, hide_index = True, use_container_width=True)
    selected_products = positions_from_file
else:
    # селектим нужные продукты
    products = df.iloc[:, 9].unique() # похоже этот тут уже не нужно

    # Извлекаем уникальные имена
    names = df["gp_name"].unique()

    # Добавляем поле ввода для фильтрации
    search_query = st.text_input("Поиск позиции", "")

    # Фильтруем имена на основе введённого текста
    filtered_names = [name for name in names if search_query.lower() in name.lower()]

    selected_products = st.multiselect("Выберите ГП", options = filtered_names)

df_sub = df.loc[selected_products]

pivot_df = pd.pivot_table(df_sub, values = "cost_crude", index = "crude", columns = "gp_name", aggfunc = "sum")
pivot_df_with_gau = pivot_df.reset_index()
pivot_df_with_gau = pd.melt(pivot_df_with_gau, id_vars=["crude"], var_name="Products", value_name="Price")
pivot_df_with_gau = pd.merge(pivot_df_with_gau, spr_crude, on = "crude")



#st.write(pivot_df)
#st.table(pivot_df)

# Create a container for the cards
cards_container = st.container()

# создаем карточку для каждого выбранного продукта (мб как-то улучшить читаемость этого элемента?)
def build_cols():
    cols = st.columns(len(selected_products))
    for i, product in enumerate(selected_products):
        col = cols[i]
        product_sum = df_sub.loc[product, "cost_crude"].sum()
        card_content = f"""
        <span style="display: inline-block; padding: 10px; margin: 10px; border-radius: 10px; background-color: #f7f7f7;">
        <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 5px;">{product.split(",")[1]}</div>
        <div style="font-size: 1.2em;">Сумма: { "{:,.0f}".format(product_sum).replace(",", " ") }</div>
        </span>
        """
        col.markdown(card_content, unsafe_allow_html=True)

def build_table():
    table_data = pd.DataFrame({
        "Product": [product.split(",")[1] for product in selected_products],
        "Sum": [df_sub.loc[product, "cost_crude"].sum() for product in selected_products]
    })
    table_data["Sum"] = table_data["Sum"].apply(lambda x: "{:,.0f}".format(x).replace(",", " "))
    table_data = table_data.sort_values(by="Sum", ascending=False)
    st.dataframe(table_data, hide_index=True, use_container_width=True)


fig = px.bar(pivot_df_with_gau, x="Price", y="Products", color='gau', orientation='h',
             hover_name="crude",
             custom_data=["crude", "Price"],
             height=800,
             title='Структура продукта',
             labels=["gau"])

fig.update_traces(hovertemplate='<b>Сырье:</b> %{customdata[0]}<br><b>Стоимость:</b> %{customdata[1]:.2f}<br>')
wrapped_labels = [f"<br>".join(wrap(label.split(",")[1], 30)) for label in pivot_df_with_gau["Products"].unique()]
fig.update_layout(
    yaxis=dict(
        ticktext=wrapped_labels,
        tickvals=pivot_df_with_gau["Products"].unique()
    )
)

if selected_products:
    build_table()


@st.cache_data
def build_chart(df_line, selected_products):
    df_line_filtered = df_line[df_line['Name'].isin([i.split(", ")[1] for i in selected_products])]
    fig2 = px.line(df_line_filtered, x="date", y="Total", color='Name', title="График", markers = True)
    return fig2

if selected_products:
    tab1, tab2 = st.tabs(["Структура", "График"])
    with tab1:
        
        with st.expander("Структура"):
            st.plotly_chart(fig, use_container_width = True)
       
        with st.expander("Графики"):
            fig2 = build_chart(df_line, selected_products)
            st.plotly_chart(fig2, use_container_width=True)
        
        with st.expander("Таблица с сырьём"):
            #st.dataframe(pivot_df, use_container_width = True)
            df4download = df.loc[selected_products]
            st.dataframe(df4download, hide_index = True)
        
        buffer = io.BytesIO()
        #pivot_df.to_excel(buffer)
        df4download["period"] = month
        df4download.to_excel(buffer)
        # копочка для скачивания полученной сводной
        download_button = st.download_button(
            label="Скачать Excel",
            data=buffer.getvalue(),
            file_name="data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        if 'file_downloaded' not in st.session_state:
            st.session_state['file_downloaded'] = False
        if download_button:
            st.session_state['file_downloaded'] = True
            #st.balloons()
        
        with st.expander("Таблица с сырьём"):
            st.dataframe(df.loc[selected_products], hide_index = True)
        
    

    with tab2:
        fig2 = build_chart(df_line, selected_products)
        st.plotly_chart(fig2, use_container_width=True)