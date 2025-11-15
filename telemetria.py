import streamlit as st
import pandas as pd
import json
import time
import os

DATA_FILE = "./logs/consumer/data/telemetria.jsonl"

st.set_page_config(page_title="Telemetría Kafka", layout="wide")

st.title("📡 Telemetría en Vivo desde Kafka")
st.caption("Actualiza automáticamente cada 2 segundos")

placeholder = st.empty()

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()

    rows = []
    with open(DATA_FILE, "r") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                pass

    return pd.DataFrame(rows)


while True:
    df = load_data()

    with placeholder.container():

        if df.empty:
            st.write("Esperando datos...")
        else:
            st.subheader("Gráfica en vivo")
            st.line_chart(df[["temperatura", "humedad", "direccion_viento"]])

            st.subheader("Últimos datos")
            st.dataframe(df.tail(10), use_container_width=True)

    time.sleep(2)
