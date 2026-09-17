import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuración básica de la aplicación
st.set_page_config(page_title="Control de Gastos", layout="wide")

# Conectar a Google Sheets usando los secrets configurados
conn = st.connection("gsheets", type=GSheetsConnection)

# URL de tu base de datos en Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_lnER4_Y_BtLksTcwFv1tgfWqLupo5tU6aMjRwJrJBA/edit"

# Tus medios de pago exactos
MEDIOS_DE_PAGO = [
    "Efectivo", 
    "Dinero en cuenta", 
    "Descubierto", 
    "Mercado Crédito",
    "Tarjeta de Crédito - Provincia", 
    "Tarjeta Naranja", 
    "Tarjeta Visa - Santander"
]

# --- MENÚ LATERAL ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["📊 Dashboard", "💸 Cargar Gasto", "🏦 Panel de Deudas"])

# --- PANTALLA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Mi Resumen Financiero")
    
    try:
        # Leer datos de la pestaña "Transacciones"
        df_transacciones = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones")
        
        # Limpiar filas vacías basándonos en la columna 'Monto'
        df_transacciones = df_transacciones.dropna(subset=['Monto'])
        
        if not df_transacciones.empty:
            st.subheader("Últimos gastos registrados")
            st.dataframe(df_transacciones.tail(10), use_container_width=True)
            
            # --- CÁLCULOS DE ALARMAS ---
            tarjetas = ["Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander"]
            
            # Asegurar que el monto sea numérico para poder sumar
            df_transacciones['Monto'] = pd.to_numeric(df_transacciones['Monto'], errors='coerce').fillna(0)
            
            gasto_tarjetas = df_transacciones[df_transacciones['Medio_Pago'].isin(tarjetas)]['Monto'].sum()
            gasto_mc = df_transacciones[df_transacciones['Medio_Pago'] == 'Mercado Crédito']['Monto'].sum()
            
            st.markdown("---")
            st.subheader("🚨 Alarmas de Consumo a Crédito")
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"💳 Total gastado con Tarjetas:\n### ${gasto_tarjetas:,.2f}")
            with col2:
                st.warning(f"🛒 Total gastado con Mercado Crédito:\n### ${gasto_mc:,.2f}")
                
        else:
            st.info("Aún no hay gastos registrados. Ve a 'Cargar Gasto' para empezar.")
            
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Asegúrate de haber compartido el archivo con el correo de la cuenta de servicio. Detalle del error: {e}")

# --- PANTALLA: CARGAR GASTO ---
elif menu == "💸 Cargar Gasto":
    st.title("💸 Registrar Nuevo Gasto")
    
    with st.form("nuevo_gasto", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.today())
        desc = st.text_input("Descripción (Ej: Súper, Nafta, Salida)")
        monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        medio = st.selectbox("Medio de Pago", MEDIOS_DE_PAGO)
        categoria = st.selectbox("Categoría", ["Supermercado", "Servicios", "Ocio/Salidas", "Transporte", "Ropa", "Otros"])
        
        enviado = st.form_submit_button("Guardar Gasto")
        
        if enviado:
            if monto > 0 and desc:
                # Leer los datos actuales para no sobrescribirlos
                df_actual = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones")
                
                # Crear una nueva fila con el gasto ingresado
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Descripcion": desc,
                    "Monto": monto,
                    "Categoria": categoria,
                    "Medio_Pago": medio
                }])
                
                # Unir el historial con el nuevo gasto
                df_actualizado = pd.concat([df_actual, nuevo_dato], ignore_index=True)
                
                # Enviar la actualización a Google Sheets
                conn.update(worksheet="Transacciones", data=df_actualizado)
                
                st.success(f"✅ Gasto de ${monto} en '{desc}' guardado exitosamente.")
            else:
                st.error("Por favor, ingresa una descripción y un monto mayor a 0.")

# --- PANTALLA: DEUDAS ---
elif menu == "🏦 Panel de Deudas":
    st.title("🏦 Panel de Deudas")
    
    try:
        df_deudas_activas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas")
        df_deudas_activas = df_deudas_activas.dropna(subset=['Deuda'])
        
        st.subheader("🔴 Deudas Activas")
        if not df_deudas_activas.empty:
            st.dataframe(df_deudas_activas, use_container_width=True)
        else:
            st.success("¡No tienes deudas activas registradas!")
            
        st.markdown("---")
        
        df_deudas_saldadas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Saldadas")
        df_deudas_saldadas = df_deudas_saldadas.dropna(subset=['Deuda'])
        
        st.subheader("✅ Historial de Victorias (Deudas Saldadas)")
        if not df_deudas_saldadas.empty:
            st.dataframe(df_deudas_saldadas, use_container_width=True)
        else:
            st.info("Aquí aparecerán las deudas que logres cancelar.")
            
    except Exception as e:
        st.warning("Para ver este panel, asegúrate de haber creado las pestañas 'Deudas_Activas' y 'Deudas_Saldadas' en tu Google Sheets.")
