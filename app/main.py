import pandas as pd
import streamlit as st
import plotly.express as px


st.set_page_config(page_title='Askona', layout = 'wide', page_icon = 'logo.png', initial_sidebar_state = 'auto')

st.title("Тут будет обща`я` информация")
st.text("Инструкция и информация")

st.sidebar.title("Общая информация")
# нужно подумать над описанием (инструкцией для пользователя)
st.sidebar.markdown("""Данная страница позволяет найти и сравнить несколько позиций между собой
                    \nВременной промежуток датасета: 
                    \nЯнварь 24 - Июнь 24
                    \nПод графиком появляются карточки с выбранными позициями и крайней ценой""")
#st.sidebar.expander("что-то", expanded = False)
