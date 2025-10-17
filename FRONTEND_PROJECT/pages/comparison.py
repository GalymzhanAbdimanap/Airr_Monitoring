import streamlit as st
import plotly.express as px
from utils.api import get_data

st.title("⚖️ Сравнение станций")

data = get_data()

if not data.empty:
    station_ids = data["sensor_id"].unique().tolist()
    col1, col2 = st.columns(2)

    with col1:
        station_1 = st.selectbox("Первая станция:", station_ids, key="station1")
    with col2:
        station_2 = st.selectbox("Вторая станция:", [s for s in station_ids if s != station_1], key="station2")

    pollutants = ["pm25", "pm10", "co2", "rh", "temp", "etvoc"]
    selected_pollutant = st.radio("Выберите параметр для сравнения:", pollutants, key="compare_pollutant")

    filtered_data = data[data["sensor_id"].isin([station_1, station_2])]

    fig = px.line(filtered_data, x="datetime", y=selected_pollutant, color="sensor_id",
                  title=f"Сравнение {selected_pollutant.upper()} на станциях {station_1} и {station_2}")
    st.plotly_chart(fig)

    st.write(f"### 📋 Данные по станциям {station_1} и {station_2}")
    st.dataframe(filtered_data)
else:
    st.warning("Данные не загружены. Проверьте сервер.")
