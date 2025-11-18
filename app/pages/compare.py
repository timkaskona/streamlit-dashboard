import numpy as np
import streamlit as st
import pandas as pd
import os
import pyarrow as pa
import pyarrow.parquet as pq
import io
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title='Askona', layout = 'wide', page_icon = 'logo.png', initial_sidebar_state = 'auto')
pd.set_option('mode.chained_assignment', None)  # Отключает предупреждения
st.title("Сравнение")

def load(file_path):
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
    
    return df

#st.write(os.getcwd())
spisok_gp = pd.read_excel(r"pages/references/spisok_gp.xlsx")
#st.dataframe(spisok_gp)
#st.write(spisok_gp.gp_name.unique())
companies = spisok_gp.company.unique()
selected_company = st.selectbox("Компания", companies)
if selected_company:
    gp = spisok_gp[spisok_gp['company'] == selected_company]["gp_name"].unique()
    selected_gp = st.selectbox("ГП", gp)
    
if selected_gp:
    periods = spisok_gp[(spisok_gp['company'] == selected_company)&(spisok_gp['gp_name'] == selected_gp)]["period"].unique()
    col1, col2 = st.columns(2)
    
    with col1:
        selected_period_bp = st.selectbox("Базовый период", periods)
        path_bp = "output_xlsb_" + selected_period_bp + ".parquet"
    with col2:
        selected_period_op = st.selectbox("Отчетный период", periods)
        path_op = "output_xlsb_" + selected_period_op + ".parquet"

#st.write(path_bp)
#st.write(path_op)

df_bp = load(r"pages/source/" + path_bp)
df_op = load(r"pages/source/" + path_op)

df_bp = df_bp.loc[selected_gp]
df_op = df_op.loc[selected_gp]

df_bp = df_bp[~df_bp["gfu"].str.contains("ГП Солвис|ГП Литвуд & Солвис|ПФ Солвис|ПФ Литвуд & Солвис", na=False)]
df_op = df_op[~df_op["gfu"].str.contains("ГП Солвис|ГП Литвуд & Солвис|ПФ Солвис|ПФ Литвуд & Солвис", na=False)]

df_bp["period"] = selected_period_bp
df_op["period"] = selected_period_op
#st.dataframe(df_bp)
#st.dataframe(df_op)
########################################################################################################
# сводную по сырью, которую буду выводить пользователю
pivot_df_bp_crude = pd.pivot_table(df_bp, values = ["costs" , "cost_crude"], index = "crude" , aggfunc = "sum")
pivot_df_op_crude = pd.pivot_table(df_op, values = ["costs" , "cost_crude"], index = "crude" , aggfunc = "sum")

#st.dataframe(pivot_df_bp_crude)
#st.dataframe(pivot_df_op_crude)
########################################################################################################


pivot_df_bp = pd.pivot_table(df_bp, values = ["cost_crude"], index = "gau",  aggfunc = "sum")
pivot_df_op = pd.pivot_table(df_op, values = ["cost_crude"], index = "gau", aggfunc = "sum")

#st.dataframe(pivot_df_bp)
#st.dataframe(pivot_df_op)

merged_pivot_df = pd.merge(pivot_df_bp, pivot_df_op, on = "gau", how = "outer", suffixes = ["_БП","_ОП"])
merged_pivot_df.fillna(0, inplace=True)
merged_pivot_df["diff"] = merged_pivot_df["cost_crude_ОП"] - merged_pivot_df["cost_crude_БП"]
#st.dataframe(merged_pivot_df)
merged_pivot_df = merged_pivot_df.reset_index()
merged_pivot_df = merged_pivot_df.sort_values(by = "diff", ascending = False)
mz_bp = df_bp["cost_crude"].sum()
mz_op = df_op["cost_crude"].sum()
negative_sum = np.sum(np.where(merged_pivot_df['diff'] < 0, merged_pivot_df['diff'], 0))
pozitive_sum = np.sum(np.where(merged_pivot_df['diff'] > 0, merged_pivot_df['diff'], 0))
maximum = mz_bp + pozitive_sum
minimum = maximum + negative_sum
#st.write(minimum)
##st.write(maximum)
n_gau = merged_pivot_df.shape[0]
#st.write(mz_bp)
##st.write(mz_op)
#st.write(n_gau)
#st.write(mz_op + mz_bp)
fig = go.Figure(go.Waterfall(
    name="Compare",
    orientation="h",
    measure=["absolute"] + ["relative"]* n_gau + ["absolute"],
    y=["База"] + merged_pivot_df["gau"].tolist() + ["Отчет"],
    x=[mz_bp] + merged_pivot_df["diff"].tolist() + [mz_op],
    decreasing={"marker": {"color": "green", "line": {"color": "green"}}},
    increasing={"marker": {"color": "red", "line": {"color": "red"}}}
))
s ="d"
fig.update_layout(title=f"{selected_gp} в {selected_period_op} и {selected_period_bp}")
fig.update_layout(
    xaxis=dict(
        range=[minimum*0.95, maximum*1.05]
    )
)
fig.update_layout(height=800)
if selected_period_op != selected_period_bp:
    with st.expander("Горизонтальный водопад"):
        st.plotly_chart(fig, use_container_width=True)
    #st.dataframe(merged_pivot_df)
###################################################################################################################
# сортируем по изменениям (по модулю)
merged_pivot_df = merged_pivot_df.sort_values(by="diff", key=abs, ascending=False)

# дофелтно будет 8 пощиций
initial_gau = merged_pivot_df.head(8)["gau"].tolist()

# галку для всех позиций
select_all = st.checkbox("Выбрать все гр. ВЕК")

if select_all:
    selected_gau = merged_pivot_df["gau"].unique().tolist()
else:
    selected_gau = st.multiselect("Выбрать все гр. ВЕК", merged_pivot_df["gau"].unique().tolist(), default=initial_gau)

filtered_pivot_df = merged_pivot_df[merged_pivot_df["gau"].isin(selected_gau)]

# создаем прочее и наполняем его
other_gau = merged_pivot_df[~merged_pivot_df["gau"].isin(selected_gau)]
other_gau["gau"] = "Прочее"
other_gau["diff"] = other_gau["diff"].sum()

merged_pivot_df = pd.concat([filtered_pivot_df, other_gau])

###################################################################################################################
fig2 = go.Figure(go.Waterfall(
    name = "Compare",
    orientation = "v",
    measure = ["absolute"] + ["relative"]* n_gau + ["absolute"],
    y = [mz_bp] + merged_pivot_df["diff"].tolist() + [mz_op],
    x = ["База"] + merged_pivot_df["gau"].tolist() + ["Отчет"],
    decreasing = {"marker": {"color": "green", "line": {"color": "green"}}},
    increasing = {"marker": {"color": "red", "line": {"color": "red"}}},
    hovertemplate="<br>".join([
        "Гр. ВЕК: %{x}",
        "Отклонение: %{delta:,.2f}",
        "<extra></extra>"
    ]),
    customdata=np.stack((merged_pivot_df["gau"],), axis=-1)
    
))
#hovertemplate="<br>".join([
        #"Гр. ВЕК: %{customdata[0]}",
        #"Отклонение: %{y:.2f}",
        #"<extra></extra>"
   # ]),
 #   customdata=np.stack((merged_pivot_df["gau"],), axis=-1)

s ="d"
fig2.update_layout(title=f"{selected_gp} в {selected_period_op} и {selected_period_bp}")
#fig2.update_layout(hovermode='x')
fig2.update_layout(
    hoverlabel=dict(
        font_size=14,
        font_family="Arial"
    )
)
fig2.update_layout(
    yaxis=dict(
        range=[minimum*0.97, maximum*1.03]
    )
)
fig2.update_layout(height=800)
if selected_period_op != selected_period_bp:
    st.plotly_chart(fig2, use_container_width=True)
    with st.expander("Табличные данные"):
        df4download_bp = df_bp[["crude","gfu","gau","volume","costs","cost_crude","gp_name"]]
        df4download_bp = df4download_bp.rename(columns = {"crude" : "МЦ", "gfu" : "ГФУ", "gau":"гр. ВЕК", "volume" : "Количество", "costs" : "Затраты", "cost_crude" : "Стоимость затрат","gp_name":"Выбранная позиция"})
        df4download_bp["Период"] = selected_period_bp
        df4download_op = df_op[["crude","gfu","gau","volume","costs","cost_crude","gp_name"]]
        df4download_op = df4download_op.rename(columns = {"crude" : "МЦ", "gfu" : "ГФУ", "gau":"гр. ВЕК", "volume" : "Количество", "costs" : "Затраты", "cost_crude" : "Стоимость затрат","gp_name":"Выбранная позиция"})
        df4download_op["Период"] = selected_period_op
        combined_df = pd.concat([df4download_bp, df4download_op], ignore_index=True)
        st.dataframe(combined_df, hide_index = True, use_container_width = True)
    buffer = io.BytesIO()
    #pivot_df.to_excel(buffer)
    combined_df.to_excel(buffer)
        # копочка для скачивания полученной сводной
    download_button = st.download_button(
        label="Скачать Excel",
        data=buffer.getvalue(),
        file_name="data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )