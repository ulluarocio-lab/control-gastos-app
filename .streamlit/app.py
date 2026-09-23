import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Mis Finanzas", page_icon="📱", layout="wide")

# --- CONTROL DE ESTADO PARA OCULTAR/MOSTRAR SALDO ---
if 'mostrar_saldo' not in st.session_state:
    st.session_state.mostrar_saldo = False

def formato_moneda(valor):
    return f"${valor:,.0f}" if st.session_state.mostrar_saldo else "$ ***"

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_lnER4_Y_BtLksTcwFv1tgfWqLupo5tU6aMjRwJrJBA/edit"

MEDIOS_DE_PAGO = [
    "Efectivo", "Dinero en cuenta", "Descubierto", "Mercado Crédito",
    "Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander",
    "Tarjeta Carrefour"
]

# --- MENÚ PRINCIPAL HORIZONTAL ---
menu = st.radio("Navegación", 
                ["📊 Dashboard Analítico", "💸 Cargar Gasto", "⚙️ Gastos Fijos", "🏦 Panel de Deudas"], 
                horizontal=True, 
                label_visibility="collapsed")

# ==========================================
# MOTOR DE CACHÉ (OPTIMIZACIÓN DE VELOCIDAD)
# ==========================================
@st.cache_data(ttl="10m") 
def cargar_datos_desde_sheets():
    try:
        t = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones").dropna(subset=['Monto'])
        f = conn.read(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos").dropna(subset=['Concepto'])
        d = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas").dropna(subset=['Deuda'])
        c = conn.read(spreadsheet=SHEET_URL, worksheet="Configuracion").dropna(subset=['Parametro'])
        
        # Asegurar formatos correctos
        t['Monto'] = pd.to_numeric(t['Monto'], errors='coerce').fillna(0)
        f['Monto'] = pd.to_numeric(f['Monto'], errors='coerce').fillna(0)
        d['Cuota_Mensual'] = pd.to_numeric(d['Cuota_Mensual'], errors='coerce').fillna(0)
        d['Cuotas_Restantes'] = pd.to_numeric(d['Cuotas_Restantes'], errors='coerce').fillna(0)
        
        return t, f, d, c
    except Exception as e:
        st.error(f"Error al leer bases de datos. Detalle: {e}")
        st.stop()

df_trans, df_fijos, df_deudas, df_config = cargar_datos_desde_sheets()

# --- MEMORIA DEL SUELDO (MENÚ LATERAL) ---
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Tus Ingresos")

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
        st.rerun()

# --- FILTRO DE HISTORIAL (MENÚ LATERAL) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Historial Mensual")

# Generar columnas de fecha internamente (sin enviarlas a Sheets)
if not df_trans.empty:
    df_trans = df_trans.copy()
    df_trans['Fecha_Obj'] = pd.to_datetime(df_trans['Fecha'], errors='coerce')
    df_trans['Mes_Año'] = df_trans['Fecha_Obj'].dt.strftime('%Y-%m')
    meses_disponibles = sorted(df_trans['Mes_Año'].dropna().unique().tolist(), reverse=True)
else:
    meses_disponibles = []

mes_actual = datetime.today().strftime('%Y-%m')
if mes_actual not in meses_disponibles:
    meses_disponibles.insert(0, mes_actual)

mes_seleccionado = st.sidebar.selectbox("Selecciona el mes a analizar:", meses_disponibles)

if not df_trans.empty:
    df_trans_mes = df_trans[df_trans['Mes_Año'] == mes_seleccionado]
else:
    df_trans_mes = df_trans

# ==========================================
# PANTALLA 1: DASHBOARD ANALÍTICO
# ==========================================
if menu == "📊 Dashboard Analítico":
    st.title(f"📊 Análisis Financiero: {mes_seleccionado}")
    
    total_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]['Monto'].sum()
    total_cuotas = df_deudas['Cuota_Mensual'].sum()
    total_variables = df_trans_mes['Monto'].sum()
    disponible = nuevo_sueldo - total_fijos - total_cuotas - total_variables
    
    st.subheader("Desglose de tu Dinero")
    
    if st.button("👁️ Mostrar / Ocultar Saldos"):
        st.session_state.mostrar_saldo = not st.session_state.mostrar_saldo
        st.rerun()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("1. Sueldo", formato_moneda(nuevo_sueldo))
    col2.metric("2. Gastos Fijos", formato_moneda(total_fijos))
    col3.metric("3. Cuotas Deudas", formato_moneda(total_cuotas))
    col4.metric("4. Variables Totales", formato_moneda(total_variables))
    
    if disponible >= 0:
        col5.metric("✅ DISPONIBLE REAL", formato_moneda(disponible))
    else:
        delta_texto = "En Rojo" if st.session_state.mostrar_saldo else None
        col5.metric("🚨 DISPONIBLE REAL", formato_moneda(disponible), delta=delta_texto, delta_color="inverse")
        
    st.markdown("---")
    st.subheader("💳 Consumo a Crédito (A pagar próximo mes)")
    
    tarjetas = [
        "Tarjeta de Crédito - Provincia", "Tarjeta Naranja", 
        "Tarjeta Visa - Santander", "Tarjeta Carrefour"
    ]
    
    gasto_tarjetas = df_trans_mes[df_trans_mes['Medio_Pago'].isin(tarjetas)]['Monto'].sum()
    gasto_mc = df_trans_mes[df_trans_mes['Medio_Pago'] == 'Mercado Crédito']['Monto'].sum()
    
    c1, c2 = st.columns(2)
    c1.info(f"**Total acumulado en Tarjetas:**\n### {formato_moneda(gasto_tarjetas)}")
    c2.warning(f"**Total acumulado en Mercado Crédito:**\n### {formato_moneda(gasto_mc)}")
    
    st.markdown("---")
    st.subheader("🛒 ¿En qué se fue el dinero variable?")
    
    if not df_trans_mes.empty:
        gastos_categoria = df_trans_mes.groupby('Categoria')['Monto'].sum().sort_values(ascending=False)
        col_chart, col_data = st.columns([2, 1])
        with col_chart:
            st.bar_chart(gastos_categoria)
        with col_data:
            st.dataframe(gastos_categoria, use_container_width=True)
            ocio = gastos_categoria.get("Ocio/Salidas", 0)
            st.success(f"🎭 **Entretenimiento:**\n{formato_moneda(ocio)}")
    else:
        st.write("No hay gastos registrados en este mes.")
        
    with st.expander(f"Ver movimientos de {mes_seleccionado}"):
        st.dataframe(df_trans_mes.drop(columns=['Fecha_Obj', 'Mes_Año'], errors='ignore'), use_container_width=True)

# ==========================================
# PANTALLA 2: CARGAR GASTO
# ==========================================
elif menu == "💸 Cargar Gasto":
    st.title("💸 Registrar Nuevo Gasto")
    
    fecha = st.date_input("Fecha", datetime.today())
    desc = st.text_input("Descripción (Ej: Súper, Nafta, Salida)")
    medio = st.selectbox("Medio de Pago", MEDIOS_DE_PAGO)
    categoria = st.selectbox("Categoría", ["Supermercado", "Servicios", "Ocio/Salidas", "Transporte", "Ropa", "Otros"])
    monto = st.number_input("Monto de la compra (o valor de contado) ($)", min_value=0.0, step=100.0)
    
    st.markdown("---")
    
    es_credito = "Tarjeta" in medio or "Crédito" in medio
    if es_credito:
        st.markdown("💳 **Opciones de Financiación**")
        opcion_cuotas = st.selectbox("Cantidad de Cuotas", ["1", "3", "6", "9", "12", "Otra cantidad"])
        
        if opcion_cuotas == "Otra cantidad":
            cuotas = st.number_input("Ingresa la cantidad exacta de cuotas", min_value=2, max_value=72, value=2, step=1)
        else:
            cuotas = int(opcion_cuotas)
            
        tipo_cuota = "1 Pago"
        valor_cuota_manual = 0.0
        
        if cuotas > 1:
            tipo_cuota = st.radio("Tipo de financiación:", ["1. Cuotas sin interés", "2. Cuotas fijas (con recargo)"], horizontal=True)
            if tipo_cuota == "2. Cuotas fijas (con recargo)":
                valor_cuota_manual = st.number_input("Monto EXACTO de la cuota mensual ($)", min_value=0.0, step=100.0)
    else:
        cuotas = 1
        tipo_cuota = "1 Pago"
        valor_cuota_manual = 0.0

    if st.button("Guardar Gasto"):
        if monto > 0 and desc:
            if cuotas == 1:
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"), "Descripcion": desc,
                    "Monto": monto, "Categoria": categoria, "Medio_Pago": medio
                }])
                # Se eliminan las columnas generadas en memoria antes de enviar a Sheets
                df_limpio = df_trans.drop(columns=['Fecha_Obj', 'Mes_Año'], errors='ignore')
                df_actualizado = pd.concat([df_limpio, nuevo_dato], ignore_index=True)
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Transacciones", data=df_actualizado)
                st.cache_data.clear()
                st.success("✅ Gasto de 1 pago guardado. Actualizando pantalla...")
                st.rerun() # Fuerza la actualización visual inmediata
                
            else:
                if tipo_cuota == "2. Cuotas fijas (con recargo)" and valor_cuota_manual <= 0:
                    st.error("🚨 Seleccionaste cuotas con recargo. Debes ingresar el valor exacto de la cuota mensual.")
                    st.stop()
                else:
                    if tipo_cuota == "1. Cuotas sin interés":
                        valor_cuota_mensual = monto / cuotas
                        saldo_total = monto
                        detalle_tipo = "Sin interés"
                    else:
                        valor_cuota_mensual = valor_cuota_manual
                        saldo_total = valor_cuota_mensual * cuotas
                        detalle_tipo = "Con interés"
                    
                    nueva_deuda = pd.DataFrame([{
                        "Deuda": f"{desc} ({medio} - {cuotas} cuotas {detalle_tipo})",
                        "Saldo_Total": saldo_total,
                        "Cuota_Mensual": valor_cuota_mensual,
                        "Cuotas_Restantes": cuotas
                    }])
                    df_deudas_actualizado = pd.concat([df_deudas, nueva_deuda], ignore_index=True)
                    
                    conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_actualizado)
                    st.cache_data.clear()
                    st.success(f"✅ Compra agendada para {cuotas} meses. Actualizando pantalla...")
                    st.rerun() # Fuerza la actualización visual inmediata
        else:
            st.error("Ingresa una descripción y monto válido.")

# ==========================================
# PANTALLA 3: GASTOS FIJOS
# ==========================================
elif menu == "⚙️ Gastos Fijos":
    st.title("⚙️ Administrar Gastos Fijos")
    df_fijos_pantalla = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]
    df_editado = st.data_editor(df_fijos_pantalla, num_rows="dynamic", use_container_width=True,
                                column_config={"Monto": st.column_config.NumberColumn("Monto ($)", min_value=0, step=1000)})
    
    if st.button("💾 Guardar Cambios en Fijos"):
        conn.update(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos", data=df_editado)
        st.success("¡Actualizado!")
        st.cache_data.clear()
        st.rerun()
    
    total_fijos_vista = pd.to_numeric(df_editado['Monto'], errors='coerce').sum()
    st.info(f"**Total Fijos:** {formato_moneda(total_fijos_vista)}")

# ==========================================
# PANTALLA 4: DEUDAS Y CUOTAS
# ==========================================
elif menu == "🏦 Panel de Deudas":
    st.title("🏦 Panel de Deudas y Cuotas")
    
    if st.button("⏩ Procesar pago del mes (Resta 1 cuota a todo)"):
        if not df_deudas.empty:
            df_deudas_calc = df_deudas.copy()
            df_deudas_calc['Cuotas_Restantes'] = df_deudas_calc['Cuotas_Restantes'] - 1
            df_deudas_calc['Saldo_Total'] = df_deudas_calc['Cuotas_Restantes'] * df_deudas_calc['Cuota_Mensual']
            df_deudas_calc = df_deudas_calc[df_deudas_calc['Cuotas_Restantes'] > 0]
            
            conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_calc)
            st.success("✅ Cuotas descontadas. Los consumos finalizados se eliminaron automáticamente.")
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    st.subheader("🔴 Tus Cuotas Activas")
    
    df_deudas_edit = st.data_editor(df_deudas, num_rows="dynamic", use_container_width=True,
                                    column_config={
                                        "Saldo_Total": st.column_config.NumberColumn("Saldo Total ($)", min_value=0, step=1000),
                                        "Cuota_Mensual": st.column_config.NumberColumn("Cuota Mensual ($)", min_value=0, step=1000),
                                        "Cuotas_Restantes": st.column_config.NumberColumn("Cuotas Restantes", min_value=0, step=1)})
    
    if st.button("💾 Guardar Cambios Manuales"):
        conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_edit)
        st.success("¡Deudas actualizadas!")
        st.cache_data.clear()
        st.rerun()
