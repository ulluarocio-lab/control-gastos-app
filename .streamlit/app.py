import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuración básica de la aplicación
st.set_page_config(page_title="Mis Finanzas", page_icon="📱", layout="wide")

# Conectar a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_lnER4_Y_BtLksTcwFv1tgfWqLupo5tU6aMjRwJrJBA/edit"

# Medios de pago
MEDIOS_DE_PAGO = [
    "Efectivo", "Dinero en cuenta", "Descubierto", "Mercado Crédito",
    "Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander"
]

# --- MENÚ LATERAL ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["📊 Dashboard Analítico", "💸 Cargar Gasto", "⚙️ Gastos Fijos", "🏦 Panel de Deudas"])

# --- LEER BASES DE DATOS GLOBALES ---
try:
    df_trans = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones").dropna(subset=['Monto'])
    df_fijos = conn.read(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos").dropna(subset=['Concepto'])
    df_deudas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas").dropna(subset=['Deuda'])
    df_config = conn.read(spreadsheet=SHEET_URL, worksheet="Configuracion").dropna(subset=['Parametro'])
    
    # Asegurar formatos
    df_trans['Monto'] = pd.to_numeric(df_trans['Monto'], errors='coerce').fillna(0)
    df_fijos['Monto'] = pd.to_numeric(df_fijos['Monto'], errors='coerce').fillna(0)
    df_deudas['Cuota_Mensual'] = pd.to_numeric(df_deudas['Cuota_Mensual'], errors='coerce').fillna(0)
    
except Exception as e:
    st.error(f"Error al leer bases de datos. Asegúrate de haber creado la pestaña 'Configuracion'. Detalle: {e}")
    st.stop()

# --- MEMORIA DEL SUELDO (MENÚ LATERAL) ---
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Tus Ingresos")

# Leer sueldo guardado
try:
    sueldo_guardado = float(df_config[df_config['Parametro'] == 'Sueldo']['Valor'].iloc[0])
except:
    sueldo_guardado = 0.0

with st.sidebar.form("form_sueldo"):
    nuevo_sueldo = st.number_input("Sueldo del mes ($)", min_value=0.0, value=float(sueldo_guardado), step=50000.0)
    if st.form_submit_button("Guardar Sueldo"):
        df_config.loc[df_config['Parametro'] == 'Sueldo', 'Valor'] = nuevo_sueldo
        conn.update(spreadsheet=SHEET_URL, worksheet="Configuracion", data=df_config)
        st.success("Sueldo guardado en memoria.")
        st.cache_data.clear()

# --- FILTRO DE HISTORIAL (MENÚ LATERAL) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Historial Mensual")

if not df_trans.empty:
    df_trans['Fecha_Obj'] = pd.to_datetime(df_trans['Fecha'], errors='coerce')
    df_trans['Mes_Año'] = df_trans['Fecha_Obj'].dt.strftime('%Y-%m')
    meses_disponibles = sorted(df_trans['Mes_Año'].dropna().unique().tolist(), reverse=True)
else:
    meses_disponibles = []

mes_actual = datetime.today().strftime('%Y-%m')
if mes_actual not in meses_disponibles:
    meses_disponibles.insert(0, mes_actual)

mes_seleccionado = st.sidebar.selectbox("Selecciona el mes a analizar:", meses_disponibles)

# Filtrar transacciones por el mes elegido
if not df_trans.empty:
    df_trans_mes = df_trans[df_trans['Mes_Año'] == mes_seleccionado]
else:
    df_trans_mes = df_trans

# --- PANTALLA: DASHBOARD ANALÍTICO ---
if menu == "📊 Dashboard Analítico":
    st.title(f"📊 Análisis Financiero: {mes_seleccionado}")
    
    # Cálculos usando SÓLO los gastos del mes seleccionado
    total_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]['Monto'].sum()
    total_cuotas = df_deudas['Cuota_Mensual'].sum()
    total_variables = df_trans_mes['Monto'].sum()
    
    # EL DISPONIBLE REAL
    disponible = nuevo_sueldo - total_fijos - total_cuotas - total_variables
    
    # --- SECCIÓN 1: EL DESGLOSE DE TU DINERO ---
    st.subheader("Desglose de tu Dinero")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("1. Sueldo", f"${nuevo_sueldo:,.0f}")
    col2.metric("2. Gastos Fijos", f"${total_fijos:,.0f}")
    col3.metric("3. Cuotas Deudas", f"${total_cuotas:,.0f}")
    col4.metric("4. Variables Totales", f"${total_variables:,.0f}")
    
    if disponible >= 0:
        col5.metric("✅ DISPONIBLE REAL", f"${disponible:,.0f}")
    else:
        col5.metric("🚨 DISPONIBLE REAL", f"${disponible:,.0f}", delta="En Rojo", delta_color="inverse")
        
    st.markdown("---")
    
    # --- SECCIÓN 2: ALARMAS DE CRÉDITO Y ACUMULADOS ---
    st.subheader("💳 Consumo a Crédito (A pagar próximo mes)")
    tarjetas = ["Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander"]
    
    gasto_tarjetas = df_trans_mes[df_trans_mes['Medio_Pago'].isin(tarjetas)]['Monto'].sum()
    gasto_mc = df_trans_mes[df_trans_mes['Medio_Pago'] == 'Mercado Crédito']['Monto'].sum()
    
    c1, c2 = st.columns(2)
    c1.info(f"**Total acumulado en Tarjetas:**\n### ${gasto_tarjetas:,.2f}")
    c2.warning(f"**Total acumulado en Mercado Crédito:**\n### ${gasto_mc:,.2f}")
    
    st.markdown("---")
    
    # --- SECCIÓN 3: ANÁLISIS POR CATEGORÍA ---
    st.subheader("🛒 ¿En qué se fue el dinero variable?")
    if not df_trans_mes.empty:
        gastos_categoria = df_trans_mes.groupby('Categoria')['Monto'].sum().sort_values(ascending=False)
        
        col_chart, col_data = st.columns([2, 1])
        with col_chart:
            st.bar_chart(gastos_categoria)
        with col_data:
            st.dataframe(gastos_categoria, use_container_width=True)
            ocio = gastos_categoria.get("Ocio/Salidas", 0)
            st.success(f"🎭 **Entretenimiento:**\n${ocio:,.2f}")
    else:
        st.write("No hay gastos registrados en este mes.")
        
    # --- SECCIÓN 4: HISTORIAL ---
    with st.expander(f"Ver movimientos de {mes_seleccionado}"):
        st.dataframe(df_trans_mes.drop(columns=['Fecha_Obj', 'Mes_Año'], errors='ignore'), use_container_width=True)

# --- PANTALLA: CARGAR GASTO ---
elif menu == "💸 Cargar Gasto":
    st.title("💸 Registrar Nuevo Gasto")
    with st.form("nuevo_gasto", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.today())
        desc = st.text_input("Descripción (Ej: Súper, Nafta, Salida)")
        monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        medio = st.selectbox("Medio de Pago", MEDIOS_DE_PAGO)
        categoria = st.selectbox("Categoría", ["Supermercado", "Servicios", "Ocio/Salidas", "Transporte", "Ropa", "Otros"])
        
        if st.form_submit_button("Guardar Gasto"):
            if monto > 0 and desc:
                df_actual = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones")
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"), "Descripcion": desc,
                    "Monto": monto, "Categoria": categoria, "Medio_Pago": medio
                }])
                df_actualizado = pd.concat([df_actual, nuevo_dato], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Transacciones", data=df_actualizado)
                st.success(f"✅ Gasto guardado exitosamente.")
                st.cache_data.clear()
            else:
                st.error("Ingresa una descripción y monto válido.")

# --- PANTALLA: GASTOS FIJOS ---
elif menu == "⚙️ Gastos Fijos":
    st.title("⚙️ Administrar Gastos Fijos")
    df_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]
    df_editado = st.data_editor(df_fijos, num_rows="dynamic", use_container_width=True,
                                column_config={"Monto": st.column_config.NumberColumn("Monto ($)", min_value=0, step=1000)})
    if st.button("💾 Guardar Cambios en Fijos"):
        conn.update(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos", data=df_editado)
        st.success("¡Actualizado!")
        st.cache_data.clear()
    st.info(f"**Total Fijos:** ${pd.to_numeric(df_editado['Monto'], errors='coerce').sum():,.2f}")

# --- PANTALLA: DEUDAS ---
elif menu == "🏦 Panel de Deudas":
    st.title("🏦 Panel de Deudas")
    st.subheader("🔴 Deudas Activas")
    df_deudas_edit = st.data_editor(df_deudas_activas, num_rows="dynamic", use_container_width=True,
                                    column_config={
                                        "Saldo_Total": st.column_config.NumberColumn("Saldo Total ($)", min_value=0, step=1000),
                                        "Cuota_Mensual": st.column_config.NumberColumn("Cuota Mensual ($)", min_value=0, step=1000),
                                        "Cuotas_Restantes": st.column_config.NumberColumn("Cuotas Restantes", min_value=0, step=1)})
    if st.button("💾 Guardar Cambios en Deudas"):
        conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_edit)
        st.success("¡Deudas actualizadas!")
        st.cache_data.clear()
