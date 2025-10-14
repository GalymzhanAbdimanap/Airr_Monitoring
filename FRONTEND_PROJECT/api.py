import pandas as pd
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8855/pollution/"

def get_data(start_date=None, end_date=None, station=None):
    params = {}
    if start_date and end_date:
        params["start_date"] = start_date
        params["end_date"] = end_date
    if station:
        params["station_id"] = station

    try:
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            return pd.DataFrame(response.json()["pollution"])
    except Exception as e:
        st.error(f"Ошибка подключения: {e}")
    return pd.DataFrame()
