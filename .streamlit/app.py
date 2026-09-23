import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time 

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Mis Finanzas", page_icon="📱", layout="wide")

if 'mostrar_saldo' not in st.session_state:
    st.session_state.mostrar_saldo = False

def formato_moneda(valor):
    return f"${valor:,.0f}" if st.session_state.mostrar_saldo else "$ ***"

conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_lnER4_Y_BtLksTcwFv1tgfWqLupo5tU6aMjRwJrJBA/edit"

MEDIOS_DE_PAGO = [
    "Efectivo", "Dinero en cuenta", "Descubierto", "Mercado Crédito",
    "Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander",
    "Tarjeta Carrefour"
]

menu = st.radio("Navegación", 
                ["📊 Dashboard Analítico", "💸 Cargar Gasto", "⚙️ Gastos Fijos", "🏦 Panel de Deudas"], 
                horizontal=True, 
                label_visibility="collapsed")

# ==========================================
# MOTOR DE CACHÉ
# ==========================================
@st.cache_data(ttl=600) 
def cargar_datos_desde_sheets():
    try:
        t = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones", ttl=0).dropna(subset=['Monto'])
        f = conn.read(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos", ttl=0).dropna(subset=['Concepto'])
        d = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", ttl=0).dropna(subset=['Deuda'])
        c = conn.read(spreadsheet=SHEET_URL, worksheet="Configuracion", ttl=0).dropna(subset=['Parametro'])
        
        t['Monto'] = pd.to_numeric(t['Monto'], errors='coerce').fillna(0)
        f['Monto'] = pd.to_numeric(f['Monto'], errors='coerce').fillna(0)
        d['Cuota_Mensual'] = pd.to_numeric(d['Cuota_Mensual'], errors='coerce').fillna(0)
        d['Cuotas_Restantes'] = pd.to_numeric(d['Cuotas_Restantes'], errors='coerce').fillna(0)
        
        # Compatibilidad: Si la columna no existe, la crea (para gastos viejos)
        if 'Es_Fijo' not in t.columns:
            t['Es_Fijo'] = False
        else:
            t['Es_Fijo'] = t['Es_Fijo'].fillna(False).astype(bool)
            
        return t, f, d, c
    except Exception as e:
        st.error(f"Error al leer bases de datos. Detalle: {e}")
        st.stop()

df_trans, df_fijos, df_deudas, df_config = cargar_datos_desde_sheets()

# --- MEMORIA DEL SUELDO ---
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Tus Ingresos")

try:
    sueldo_guardado = float(df_config[df_config['Parametro'] == 'Sueldo']['Valor'].iloc[0])
except:
    sueldo_guardado = 0.0

with st.sidebar.form("form_sueldo"):
    nuevo_sueldo = st.number_input("Sueldo Base Mensual ($)", min_value=0.0, value=float(sueldo_guardado), step=50000.0)
    if st.form_submit_button("Guardar Sueldo"):
        df_config.loc[df_config['Parametro'] == 'Sueldo', 'Valor'] = nuevo_sueldo
        conn.update(spreadsheet=SHEET_URL, worksheet="Configuracion", data=df_config)
        st.success("Sueldo guardado.")
        st.cache_data.clear()
        time.sleep(1.5)
        st.rerun()

# --- HISTORIAL MENSUAL ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Historial Mensual")

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
    
    medios_contado = ["Efectivo", "Dinero en cuenta", "Descubierto"]
    medios_credito = [
        "Mercado Crédito", "Tarjeta de Crédito - Provincia", 
        "Tarjeta Naranja", "Tarjeta Visa - Santander", "Tarjeta Carrefour"
    ]
    
    total_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]['Monto'].sum()
    total_cuotas = df_deudas['Cuota_Mensual'].sum()
    
    # SOLO sumamos como variables los gastos que NO fueron marcados como fijos
    if not df_trans_mes.empty:
        df_vars = df_trans_mes[df_trans_mes['Es_Fijo'] == False]
    else:
        df_vars = pd.DataFrame(columns=['Medio_Pago', 'Monto'])
        
    variables_contado = df_vars[df_vars['Medio_Pago'].isin(medios_contado)]['Monto'].sum()
    variables_credito = df_vars[df_vars['Medio_Pago'].isin(medios_credito)]['Monto'].sum()
    
    disponible_actual = nuevo_sueldo - total_fijos - variables_contado
    deuda_proximo_mes = variables_credito + total_cuotas
    disponible_futuro = nuevo_sueldo - total_fijos - deuda_proximo_mes
    
    if st.button("👁️ Mostrar / Ocultar Saldos"):
        st.session_state.mostrar_saldo = not st.session_state.mostrar_saldo
        st.rerun()
    
    st.markdown("---")
    
    st.subheader("💵 Tu Billetera HOY (Plata real en cuenta)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("1. Sueldo", formato_moneda(nuevo_sueldo))
    col2.metric("2. Presupuesto Fijo", formato_moneda(total_fijos))
    col3.metric("3. Gastos Variables (Día a Día)", formato_moneda(variables_contado))
    
    if disponible_actual >= 0:
        col4.metric("✅ DISPONIBLE HOY", formato_moneda(disponible_actual))
    else:
        col4.metric("🚨 DISPONIBLE HOY", formato_moneda(disponible_actual), delta="En Rojo" if st.session_state.mostrar_saldo else None, delta_color="inverse")
        
    st.markdown("---")
    
    st.subheader("💳 Compromisos PRÓXIMO MES")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("1. Sueldo Próximo", formato_moneda(nuevo_sueldo))
    c2.metric("2. Tarjetas (1 pago)", formato_moneda(variables_credito))
    c3.metric("3. Cuotas / Préstamos", formato_moneda(total_cuotas))
    
    if disponible_futuro >= 0:
        c4.metric("🔮 DISPONIBLE FUTURO", formato_moneda(disponible_futuro))
    else:
        c4.metric("🚨 DISPONIBLE FUTURO", formato_moneda(disponible_futuro), delta="Faltará plata" if st.session_state.mostrar_saldo else None, delta_color="inverse")
    
    st.markdown("---")
    
    st.subheader("🛒 ¿En qué se fue el dinero? (Totales)")
    if not df_trans_mes.empty:
        gastos_categoria = df_trans_mes.groupby('Categoria')['Monto'].sum().sort_values(ascending=False)
        col_chart, col_data = st.columns([2, 1])
        with col_chart:
            st.bar_chart(gastos_categoria)
        with col_data:
            st.dataframe(gastos_categoria, use_container_width=True)
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
    desc = st.text_input("Descripción (Ej: Luz, Súper, Nafta)")
    medio = st.selectbox("Medio de Pago", MEDIOS_DE_PAGO)
    categoria = st.selectbox("Categoría", ["Supermercado", "Servicios", "Ocio/Salidas", "Transporte", "Ropa", "Otros"])
    monto = st.number_input("Monto de la compra ($)", min_value=0.0, step=100.0)
    
    st.markdown("---")
    # Nuevo checkbox para que el gasto fijo no reste doble
    es_fijo_check = st.checkbox("📌 Este es un Gasto Fijo (No restarlo del disponible de hoy, ya está descontado en el Presupuesto)")
    
    es_credito = "Tarjeta" in medio or "Crédito" in medio
    if es_credito:
        st.markdown("---")
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
                    "Monto": monto, "Categoria": categoria, "Medio_Pago": medio,
                    "Es_Fijo": es_fijo_check
                }])
                df_limpio = df_trans.drop(columns=['Fecha_Obj', 'Mes_Año'], errors='ignore')
                df_actualizado = pd.concat([df_limpio, nuevo_dato], ignore_index=True)
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Transacciones", data=df_actualizado)
                st.success("✅ Gasto guardado. Actualizando pantalla...")
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
                
            else:
                if tipo_cuota == "2. Cuotas fijas (con recargo)" and valor_cuota_manual <= 0:
                    st.error("🚨 Ingresa el valor exacto de la cuota mensual.")
                    st.stop()
                else:
                    valor_cuota_mensual = (monto / cuotas) if tipo_cuota == "1. Cuotas sin interés" else valor_cuota_manual
                    saldo_total = valor_cuota_mensual * cuotas
                    detalle_tipo = "Sin interés" if tipo_cuota == "1. Cuotas sin interés" else "Con interés"
                    
                    nueva_deuda = pd.DataFrame([{
                        "Deuda": f"{desc} ({medio} - {cuotas} cuotas {detalle_tipo})",
                        "Saldo_Total": saldo_total,
                        "Cuota_Mensual": valor_cuota_mensual,
                        "Cuotas_Restantes": cuotas
                    }])
                    df_deudas_actualizado = pd.concat([df_deudas, nueva_deuda], ignore_index=True)
                    
                    conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_actualizado)
                    st.success(f"✅ Compra agendada para {cuotas} meses. Actualizando...")
                    st.cache_data.clear()
                    time.sleep(2) 
                    st.rerun()
        else:
            st.error("Ingresa una descripción y monto válido.")

# ==========================================
# PANTALLA 3: GASTOS FIJOS
# ==========================================
elif menu == "⚙️ Gastos Fijos":
    st.title("⚙️ Presupuesto de Gastos Fijos")
    st.info("💡 Estos montos se reservan automáticamente de tu sueldo todos los meses. Cuando pagues uno de estos, ve a 'Cargar Gasto' y marca la casilla 'Es un Gasto Fijo'.")
    
    df_fijos_pantalla = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]
    df_editado = st.data_editor(df_fijos_pantalla, num_rows="dynamic", use_container_width=True,
                                column_config={"Monto": st.column_config.NumberColumn("Monto ($)", min_value=0, step=1000)})
    
    if st.button("💾 Guardar Cambios en Fijos"):
        conn.update(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos", data=df_editado)
        st.success("¡Presupuesto Actualizado!")
        st.cache_data.clear()
        time.sleep(1.5)
        st.rerun()
    
    total_fijos_vista = pd.to_numeric(df_editado['Monto'], errors='coerce').sum()
    st.info(f"**Total del Presupuesto Fijo:** {formato_moneda(total_fijos_vista)}")

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
            time.sleep(2)
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
        time.sleep(2)
        st.rerun()
