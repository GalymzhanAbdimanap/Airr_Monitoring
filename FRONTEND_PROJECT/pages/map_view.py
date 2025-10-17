import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests

API_URL = "http://172.20.107.4:8855"  # адрес API

st.set_page_config(page_title="🗺️ Карта Алматы", layout="wide")

st.title("🗺️ Интерактивная карта Алматы")

# Загружаем данные по станциям
resp = requests.get(f"{API_URL}/pollution/latest/")
data = pd.DataFrame(resp.json().get("pollution", []))

# Если данных нет — создаём пустой DataFrame с координатами города
if data.empty:
    data = pd.DataFrame([{
        "sensor_id": "N/A",
        "lat": 43.2389,
        "lon": 76.8897,
        "pm25": "N/A",
        "pm10": "N/A",
        "so2": "N/A"
    }])

# --- функция для выбора цвета по PM2.5 ---
def pm25_color(value):
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "gray"  # если N/A или не число

    if v <= 12:
        return "green"       # Хорошо
    elif v <= 35:
        return "orange"      # Умеренно
    elif v <= 55:
        return "red"         # Вредно
    elif v <= 150:
        return "purple"      # Очень вредно
    else:
        return "black"       # Опасно

# Создаём карту
m = folium.Map(location=[43.2389, 76.8897], zoom_start=11)

# Добавляем маркеры
for idx, row in data.iterrows():
    color = pm25_color(row.get("pm25"))
    folium.Marker(
        location=[row.get("lat", 43.2389), row.get("lon", 76.8897)],
        popup=(
            f"<b>{row.get('sensor_id', 'N/A')}</b><br>"
            f"PM2.5: {row.get('pm25', 'N/A')}<br>"
            f"PM10: {row.get('pm10', 'N/A')}<br>"
            f"CO₂: {row.get('co2', 'N/A')}<br>"
            f"RH: {row.get('rh', 'N/A')}<br>"
            f"eTVOC: {row.get('etvoc', 'N/A')}<br>"
            f"Temp: {row.get('temp', 'N/A')}"
        ),
        icon=folium.Icon(color=color, icon="info-sign")
    ).add_to(m)

# Отображаем карту
st_folium(m, width=1400, height=800)
