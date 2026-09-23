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
# MOTOR DE CACHÉ Y LECTURA
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
        
        if 'Es_Fijo' not in t.columns:
            t['Es_Fijo'] = False
        else:
            t['Es_Fijo'] = t['Es_Fijo'].fillna(False).astype(bool)
            
        return t, f, d, c
    except Exception as e:
        st.error(f"Error al leer bases de datos. Detalle: {e}")
        st.stop()

df_trans, df_fijos, df_deudas, df_config = cargar_datos_desde_sheets()

# --- LECTURA DE CONFIGURACIÓN FINANCIERA ---
def obtener_parametro(nombre, default):
    try:
        return float(df_config[df_config['Parametro'] == nombre]['Valor'].iloc[0])
    except:
        return default

fondo_diario = obtener_parametro('Fondo_Diario', 0.0)
sueldo_proximo = obtener_parametro('Sueldo_Proximo', 0.0)
dia_cierre = int(obtener_parametro('Dia_Cierre', 25))

# --- PANEL LATERAL: ASESOR FINANCIERO ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parámetros del Mes")

with st.sidebar.form("form_config"):
    nuevo_fondo = st.number_input("1. Saldo Inicial del mes (Billetera/Débito)", min_value=0.0, value=fondo_diario, step=10000.0, help="Plata con la que arrancas el mes para el día a día.")
    nuevo_sueldo = st.number_input("2. Sueldo esperado (Mes que viene)", min_value=0.0, value=sueldo_proximo, step=50000.0)
    nuevo_cierre = st.number_input("3. Día de cierre de Tarjetas", min_value=1, max_value=31, value=dia_cierre, step=1)
    
    if st.form_submit_button("Guardar Parámetros"):
        # Actualizar los 3 parámetros en la base
        for param, val in [('Fondo_Diario', nuevo_fondo), ('Sueldo_Proximo', nuevo_sueldo), ('Dia_Cierre', nuevo_cierre)]:
            if param in df_config['Parametro'].values:
                df_config.loc[df_config['Parametro'] == param, 'Valor'] = val
            else:
                df_config = pd.concat([df_config, pd.DataFrame([{'Parametro': param, 'Valor': val}])], ignore_index=True)
        
        conn.update(spreadsheet=SHEET_URL, worksheet="Configuracion", data=df_config)
        st.success("Configuración guardada.")
        st.cache_data.clear()
        time.sleep(1.5)
        st.rerun()

# --- HISTORIAL MENSUAL ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Historial")

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

mes_seleccionado = st.sidebar.selectbox("Mes de análisis:", meses_disponibles)
df_trans_mes = df_trans[df_trans['Mes_Año'] == mes_seleccionado] if not df_trans.empty else df_trans

# ==========================================
# PANTALLA 1: DASHBOARD ANALÍTICO
# ==========================================
if menu == "📊 Dashboard Analítico":
    st.title(f"📊 Análisis Estratégico: {mes_seleccionado}")
    
    medios_contado = ["Efectivo", "Dinero en cuenta", "Descubierto"]
    medios_credito = ["Mercado Crédito", "Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander", "Tarjeta Carrefour"]
    
    total_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]['Monto'].sum()
    total_cuotas = df_deudas['Cuota_Mensual'].sum()
    
    df_vars = df_trans_mes[df_trans_mes['Es_Fijo'] == False] if not df_trans_mes.empty else pd.DataFrame(columns=['Medio_Pago', 'Monto'])
        
    variables_contado = df_vars[df_vars['Medio_Pago'].isin(medios_contado)]['Monto'].sum()
    variables_credito = df_vars[df_vars['Medio_Pago'].isin(medios_credito)]['Monto'].sum()
    
    # NUEVA FÓRMULA DE LIQUIDEZ Y FUTURO
    liquidez_hoy = fondo_diario - variables_contado
    deuda_proximo_mes = variables_credito + total_cuotas
    disponible_futuro = sueldo_proximo - total_fijos - deuda_proximo_mes
    
    if st.button("👁️ Mostrar / Ocultar Saldos"):
        st.session_state.mostrar_saldo = not st.session_state.mostrar_saldo
        st.rerun()
    
    st.markdown("---")
    
    st.subheader("💵 Tu Liquidez HOY (Plata en mano / Débito)")
    col1, col2, col3 = st.columns(3)
    col1.metric("1. Fondo Mensual Asignado", formato_moneda(fondo_diario))
    col2.metric("2. Gastos Variables (Día a Día)", formato_moneda(variables_contado))
    
    if liquidez_hoy >= 0:
        col3.metric("✅ DISPONIBLE REAL HOY", formato_moneda(liquidez_hoy))
    else:
        col3.metric("🚨 DISPONIBLE REAL HOY", formato_moneda(liquidez_hoy), delta="Sin fondos" if st.session_state.mostrar_saldo else None, delta_color="inverse")
        
    st.markdown("---")
    
    st.subheader("💳 Compromisos PRÓXIMO MES (Para tu próximo sueldo)")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Sueldo Esperado", formato_moneda(sueldo_proximo))
    c2.metric("Presupuesto Fijo", formato_moneda(total_fijos))
    c3.metric("Tarjetas (1 pago)", formato_moneda(variables_credito))
    c4.metric("Cuotas Activas", formato_moneda(total_cuotas))
    
    if disponible_futuro >= 0:
        c5.metric("🔮 DISPONIBLE FUTURO", formato_moneda(disponible_futuro))
    else:
        c5.metric("🚨 DISPONIBLE FUTURO", formato_moneda(disponible_futuro), delta="Faltará plata" if st.session_state.mostrar_saldo else None, delta_color="inverse")
    
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
    es_fijo_check = st.checkbox("📌 Este es un Gasto Fijo (Ya estaba contemplado en el presupuesto mensual)")
    
    es_credito = "Tarjeta" in medio or "Crédito" in medio
    post_cierre = False
    
    if es_credito:
        st.markdown("---")
        st.markdown("💳 **Opciones de Tarjeta y Financiación**")
        
        # SISTEMA AUTOMÁTICO DE CIERRE DE TARJETA
        st.info(f"💡 Configuraste tus cierres para el día **{dia_cierre}**. La aplicación lo detectará automáticamente.")
        es_post_cierre_defecto = fecha.day >= dia_cierre
        post_cierre = st.checkbox("⏩ Gasto Post-Cierre (Impacta directo en el resumen del mes que viene)", value=es_post_cierre_defecto)
        
        opcion_cuotas = st.selectbox("Cantidad de Cuotas", ["1", "3", "6", "9", "12", "Otra cantidad"])
        cuotas = st.number_input("Ingresa la cantidad exacta", min_value=2, max_value=72, value=2, step=1) if opcion_cuotas == "Otra cantidad" else int(opcion_cuotas)
            
        tipo_cuota = "1 Pago"
        valor_cuota_manual = 0.0
        if cuotas > 1:
            tipo_cuota = st.radio("Tipo de financiación:", ["1. Cuotas sin interés", "2. Cuotas fijas (con recargo)"], horizontal=True)
            if tipo_cuota == "2. Cuotas fijas (con recargo)":
                valor_cuota_manual = st.number_input("Monto EXACTO de la cuota mensual ($)", min_value=0.0, step=100.0)
    else:
        cuotas = 1
        tipo_cuota = "1 Pago"

    if st.button("Guardar Gasto"):
        if monto > 0 and desc:
            
            # LÓGICA DE DERIVACIÓN (Contado vs Deudas Futuras)
            va_a_transacciones = not es_credito or (es_credito and cuotas == 1 and not post_cierre)
            
            if va_a_transacciones:
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"), "Descripcion": desc,
                    "Monto": monto, "Categoria": categoria, "Medio_Pago": medio, "Es_Fijo": es_fijo_check
                }])
                df_limpio = df_trans.drop(columns=['Fecha_Obj', 'Mes_Año'], errors='ignore')
                df_actualizado = pd.concat([df_limpio, nuevo_dato], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Transacciones", data=df_actualizado)
                st.success("✅ Gasto procesado en el mes actual. Actualizando...")
                
            else:
                # Si es cuotas, o es 1 pago pero POST-CIERRE, va al panel de deudas
                if tipo_cuota == "2. Cuotas fijas (con recargo)" and valor_cuota_manual <= 0:
                    st.error("🚨 Ingresa el valor exacto de la cuota mensual.")
                    st.stop()
                
                valor_cuota_mensual = (monto / cuotas) if tipo_cuota == "1. Cuotas sin interés" else (valor_cuota_manual if cuotas > 1 else monto)
                saldo_total = valor_cuota_mensual * cuotas
                detalle_tipo = "Post-Cierre (1 pago)" if cuotas == 1 else ("Sin interés" if tipo_cuota == "1. Cuotas sin interés" else "Con interés")
                
                nueva_deuda = pd.DataFrame([{
                    "Deuda": f"{desc} ({medio} - {cuotas} cuotas {detalle_tipo})",
                    "Saldo_Total": saldo_total,
                    "Cuota_Mensual": valor_cuota_mensual,
                    "Cuotas_Restantes": cuotas
                }])
                df_deudas_actualizado = pd.concat([df_deudas, nueva_deuda], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_actualizado)
                st.success("✅ Consumo derivado a la agenda de compromisos futuros. Actualizando...")

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
    st.info("💡 Estos montos se restan automáticamente de tu sueldo futuro para calcular tu disponible. Cuando pagues físicamente uno de estos, ve a 'Cargar Gasto' y marca la casilla 'Es un Gasto Fijo'.")
    
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
    
    if st.button("⏩ Procesar pago de Tarjetas (Descuenta 1 cuota a todo)"):
        if not df_deudas.empty:
            df_deudas_calc = df_deudas.copy()
            df_deudas_calc['Cuotas_Restantes'] = df_deudas_calc['Cuotas_Restantes'] - 1
            df_deudas_calc['Saldo_Total'] = df_deudas_calc['Cuotas_Restantes'] * df_deudas_calc['Cuota_Mensual']
            df_deudas_calc = df_deudas_calc[df_deudas_calc['Cuotas_Restantes'] > 0]
            
            conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_calc)
            st.success("✅ Cuotas descontadas. Consumos liquidados eliminados.")
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()
    
    st.markdown("---")
    st.subheader("🔴 Tus Cuotas y Post-Cierres Activos")
    
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
