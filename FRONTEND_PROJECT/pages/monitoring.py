import streamlit as st
import plotly.express as px
from utils.api import get_data

st.title("📊 Мониторинг загрязнения воздуха в Алматы (Live)")

data = get_data()

if not data.empty:
    station_ids = data["sensor_id"].unique().tolist()
    selected_station = st.selectbox("Выберите станцию:", station_ids)

    pollutants = ["pm25", "pm10", "co", "no2"]
    selected_pollutant = st.radio("Выберите параметр для отображения:", pollutants)

    filtered_data = data[data["sensor_id"] == selected_station]

    fig = px.line(filtered_data, x="datetime", y=selected_pollutant,
                  title=f"{selected_pollutant.upper()} на станции {selected_station}")
    st.plotly_chart(fig)

    st.write("### 📋 Таблица с данными")
    st.dataframe(filtered_data)
else:
    st.warning("Данные не загружены. Проверьте сервер.")
