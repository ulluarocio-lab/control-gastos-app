import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración básica
st.set_page_config(page_title="Mis Finanzas", layout="wide")

# Conectar a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# El link de tu Google Sheets (Copia la URL de tu navegador y ponla aquí)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_lnER4_Y_BtLksTcwFv1tgfWqLupo5tU6aMjRwJrJBA/edit?gid=651657999#gid=651657999"

st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["Dashboard", "Cargar Gasto", "Panel de Deudas"])

if menu == "Dashboard":
    st.title("📊 Mi Resumen Financiero")
    
    # Leer datos de transacciones
    try:
        df_transacciones = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones")
        st.dataframe(df_transacciones) # Esto mostrará tu tabla en pantalla
    except Exception as e:
        st.warning("Aún no hay datos o revisa la conexión.")

elif menu == "Cargar Gasto":
    st.title("💸 Registrar Gasto")
    with st.form("nuevo_gasto"):
        fecha = st.date_input("Fecha")
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto", min_value=0)
        medio = st.selectbox("Medio de Pago", ["Tarjeta de Crédito", "Mercado Crédito", "Efectivo", "Dinero en Cuenta", "Descubierto"])
        enviado = st.form_submit_button("Guardar")
        
        if enviado:
            # Aquí luego programaremos la lógica para guardar el dato
            st.success(f"Gasto de ${monto} cargado correctamente.")

elif menu == "Panel de Deudas":
    st.title("🏦 Deudas Activas y Saldadas")
    st.write("Próximamente: Panel de préstamos y Cuotas B.")
