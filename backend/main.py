import json
import sqlite3
import asyncio
from fastapi import FastAPI, WebSocket, Query
from datetime import datetime, timedelta

DB_FILE = "DATABASE/air_quality_cleaned.db"

app = FastAPI()

def get_pollution_data(start_date=None, end_date=None, station_id=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = """
        SELECT s.device_name, a.pm25, a.pm10, a.co, a.no2, a.so2, a.datetime
        FROM air_data a
        JOIN stations s ON a.station_id = s.id
    """
    conditions = []
    params = []

    if start_date and end_date:
        conditions.append("a.datetime BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    if station_id:
        conditions.append("s.device_name = ?")
        params.append(station_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY a.datetime DESC LIMIT 500"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"sensor_id": row[0], "pm25": row[1], "pm10": row[2],
         "co": row[3], "no2": row[4], "so2": row[5], "datetime": row[6]}
        for row in rows
    ]


def get_stations():
    """Получаем список всех станций с координатами"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, device_name, latitude, longitude, description FROM stations")
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": row[0], "device_name": row[1], "lat": row[2], "lon": row[3], "description": row[4]}
        for row in rows
    ]

def get_last_record_date(station_id: str):
    """Возвращает дату последней записи по станции"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(a.datetime) "
        "FROM air_data a "
        "JOIN stations s ON a.station_id = s.id "
        "WHERE s.device_name = ?",
        (station_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None

def get_filtered_data(start_date, end_date, stations):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    placeholders = ",".join(["?"]*len(stations))
    query = f"""
        SELECT s.device_name, a.datetime, a.pm25, a.pm10, a.co, a.no2, a.so2
        FROM air_data a
        JOIN stations s ON a.station_id = s.id
        WHERE s.device_name IN ({placeholders})
          AND a.datetime BETWEEN ? AND ?
        ORDER BY a.datetime DESC
    """

    cursor.execute(query, (*stations, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "sensor_id": row[0],
            "datetime": row[1],
            "pm25": row[2],
            "pm10": row[3],
            "co": row[4],
            "no2": row[5],
            "so2": row[6]
        }
        for row in rows
    ]

@app.get("/pollution/filter/")
def pollution_filter(
    start_date: str = Query(...),
    end_date: str = Query(...),
    station1: str = Query(...),
    station2: str = Query(...)
):
    return get_filtered_data(start_date, end_date, [station1, station2])

@app.get("/pollution/last3days/")
def pollution_last3days(station_id: str = Query(..., description="ID станции")):
    """
    Возвращает данные станции за 3 дня до последней записи.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. Находим дату последней записи станции
    cursor.execute(
        """
        SELECT MAX(a.datetime)
        FROM air_data a
        JOIN stations s ON a.station_id = s.id
        WHERE s.device_name = ?
        """,
        (station_id,)
    )
    last_date_row = cursor.fetchone()
    if not last_date_row or not last_date_row[0]:
        conn.close()
        return {"pollution": []}

    last_date = last_date_row[0]

    # 2. Берём все записи за последние 3 дня от last_date
    cursor.execute(
        """
        SELECT s.device_name, a.pm25, a.pm10, a.co, a.no2, a.so2, a.datetime
        FROM air_data a
        JOIN stations s ON a.station_id = s.id
        WHERE s.device_name = ?
        AND a.datetime BETWEEN datetime(?, '-3 days') AND ?
        ORDER BY a.datetime DESC
        """,
        (station_id, last_date, last_date)
    )
    rows = cursor.fetchall()
    conn.close()

    return {"pollution": [
        {"sensor_id": r[0], "pm25": r[1], "pm10": r[2], "co": r[3],
         "no2": r[4], "so2": r[5], "datetime": r[6]}
        for r in rows
    ]}

@app.get("/pollution/today/")
def pollution_today():
    """Возвращает последние данные каждой станции за сегодня (UTC)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.device_name, s.latitude, s.longitude, a.pm25, a.pm10, a.co, a.no2, a.so2, a.datetime
        FROM stations s
        LEFT JOIN air_data a ON a.station_id = s.id
        AND DATE(a.datetime) = DATE('now')
        ORDER BY a.datetime DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return {"pollution": [
        {
            "sensor_id": r[0],
            "lat": r[1],
            "lon": r[2],
            "pm25": r[3] if r[3] is not None else "N/A",
            "pm10": r[4] if r[4] is not None else "N/A",
            "co": r[5] if r[5] is not None else "N/A",
            "no2": r[6] if r[6] is not None else "N/A",
            "so2": r[7] if r[7] is not None else "N/A",
            "datetime": r[8] if r[8] is not None else "N/A"
        }
        for r in rows
    ]}

@app.get("/pollution/latest/")
def pollution_latest():
    """Возвращает последние данные каждой станции (оптимизированный запрос)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.device_name, s.latitude, s.longitude,
               a.pm25, a.pm10, a.co, a.no2, a.so2, a.datetime
        FROM stations s
        LEFT JOIN (
            SELECT ad1.*
            FROM air_data ad1
            INNER JOIN (
                SELECT station_id, MAX(datetime) AS max_dt
                FROM air_data
                GROUP BY station_id
            ) ad2 ON ad1.station_id = ad2.station_id AND ad1.datetime = ad2.max_dt
        ) a ON a.station_id = s.id
    """)

    rows = cursor.fetchall()
    conn.close()

    return {
        "pollution": [
            {
                "sensor_id": r[0],
                "lat": r[1],
                "lon": r[2],
                "pm25": r[3] if r[3] is not None else "N/A",
                "pm10": r[4] if r[4] is not None else "N/A",
                "co": r[5] if r[5] is not None else "N/A",
                "no2": r[6] if r[6] is not None else "N/A",
                "so2": r[7] if r[7] is not None else "N/A",
                "datetime": r[8] if r[8] is not None else "N/A"
            }
            for r in rows
        ]
    }


@app.get("/pollution/")
def pollution_data(
    start_date: str = Query(None, description="Дата начала"),
    end_date: str = Query(None, description="Дата конца"),
    station_id: str = Query(None, description="ID станции")
):
    return {"pollution": get_pollution_data(start_date, end_date, station_id)}


@app.get("/stations/")
def stations_data():
    return {"stations": get_stations()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = get_pollution_data()
        await websocket.send_text(json.dumps(data))
        await asyncio.sleep(5)
