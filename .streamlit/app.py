import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuración básica de la aplicación
st.set_page_config(page_title="Control de Gastos", layout="wide")

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

# --- PANTALLA: DASHBOARD ANALÍTICO ---
if menu == "📊 Dashboard Analítico":
    st.title("📊 Análisis Financiero Total")
    
    # Ingreso del sueldo en el menú lateral para calcular el disponible
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Tus Ingresos")
    sueldo = st.sidebar.number_input("Sueldo del mes ($)", min_value=0, value=1500000, step=50000)
    
    try:
        # 1. Leer todas las bases de datos
        df_trans = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones").dropna(subset=['Monto'])
        df_fijos = conn.read(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos").dropna(subset=['Concepto'])
        df_deudas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas").dropna(subset=['Deuda'])
        
        # 2. Asegurar que los montos sean numéricos
        df_trans['Monto'] = pd.to_numeric(df_trans['Monto'], errors='coerce').fillna(0)
        df_fijos['Monto'] = pd.to_numeric(df_fijos['Monto'], errors='coerce').fillna(0)
        df_deudas['Cuota_Mensual'] = pd.to_numeric(df_deudas['Cuota_Mensual'], errors='coerce').fillna(0)
        
        # 3. Cálculos de totales
        # Gastos Fijos (excluyendo tarjetas por si acaso)
        total_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]['Monto'].sum()
        # Cuotas de deudas (Ej: Amex)
        total_cuotas = df_deudas['Cuota_Mensual'].sum()
        # Gastos variables del mes (Día a día)
        total_variables = df_trans['Monto'].sum()
        
        # EL DISPONIBLE: Sueldo - (Fijos + Cuotas + Variables)
        disponible = sueldo - (total_fijos + total_cuotas + total_variables)
        
        # --- SECCIÓN 1: MÉTRICAS GENERALES ---
        st.subheader("Resumen de tu Dinero")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ingresos", f"${sueldo:,.0f}")
        col2.metric("Compromisos (Fijos + Cuotas)", f"${(total_fijos + total_cuotas):,.0f}")
        col3.metric("Gastado Día a Día", f"${total_variables:,.0f}")
        
        if disponible >= 0:
            col4.metric("✅ Disponible Restante", f"${disponible:,.0f}")
        else:
            col4.metric("🚨 Disponible Restante", f"${disponible:,.0f}", delta="En Rojo", delta_color="inverse")
            
        st.markdown("---")
        
        # --- SECCIÓN 2: ALARMAS DE CRÉDITO ---
        st.subheader("💳 Consumo a Crédito (A pagar próximo mes)")
        tarjetas = ["Tarjeta de Crédito - Provincia", "Tarjeta Naranja", "Tarjeta Visa - Santander"]
        gasto_tarjetas = df_trans[df_trans['Medio_Pago'].isin(tarjetas)]['Monto'].sum()
        gasto_mc = df_trans[df_trans['Medio_Pago'] == 'Mercado Crédito']['Monto'].sum()
        
        c1, c2 = st.columns(2)
        c1.info(f"**Total acumulado en Tarjetas:**\n### ${gasto_tarjetas:,.2f}")
        c2.warning(f"**Total acumulado en Mercado Crédito:**\n### ${gasto_mc:,.2f}")
        
        st.markdown("---")
        
        # --- SECCIÓN 3: ANÁLISIS POR CATEGORÍA ---
        st.subheader("🛒 ¿En qué se va el dinero variable?")
        if not df_trans.empty:
            # Agrupar por categoría
            gastos_categoria = df_trans.groupby('Categoria')['Monto'].sum().sort_values(ascending=False)
            
            col_chart, col_data = st.columns([2, 1])
            
            with col_chart:
                # Gráfico de barras nativo de Streamlit
                st.bar_chart(gastos_categoria)
                
            with col_data:
                st.write("**Detalle de Categorías:**")
                st.dataframe(gastos_categoria, use_container_width=True)
                
                # Destacar el entretenimiento (Ocio/Salidas)
                ocio = gastos_categoria.get("Ocio/Salidas", 0)
                st.success(f"🎭 **Gastado en Entretenimiento:**\n${ocio:,.2f}")
        else:
            st.write("Registra más gastos para ver el análisis por categorías.")
            
        # --- SECCIÓN 4: HISTORIAL (Oculto en un desplegable para limpieza) ---
        with st.expander("Ver últimos movimientos registrados"):
            st.dataframe(df_trans.tail(10), use_container_width=True)

    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Detalle: {e}")

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
                df_actual = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones")
                nuevo_dato = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"), "Descripcion": desc,
                    "Monto": monto, "Categoria": categoria, "Medio_Pago": medio
                }])
                df_actualizado = pd.concat([df_actual, nuevo_dato], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Transacciones", data=df_actualizado)
                st.success(f"✅ Gasto de ${monto} en '{desc}' guardado exitosamente.")
                st.cache_data.clear()
            else:
                st.error("Por favor, ingresa una descripción y un monto mayor a 0.")

# --- PANTALLA: GASTOS FIJOS ---
elif menu == "⚙️ Gastos Fijos":
    st.title("⚙️ Administrar Gastos Fijos")
    st.write("Edita los montos de tus servicios o actividades directamente en la tabla.")
    
    try:
        df_fijos = conn.read(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos")
        df_fijos = df_fijos.dropna(subset=['Concepto'])
        df_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]
        
        df_editado = st.data_editor(
            df_fijos, num_rows="dynamic", use_container_width=True,
            column_config={"Monto": st.column_config.NumberColumn("Monto ($)", min_value=0, step=1000)}
        )
        
        if st.button("💾 Guardar Cambios en Gastos Fijos"):
            conn.update(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos", data=df_editado)
            st.success("¡Montos actualizados correctamente!")
            st.cache_data.clear()
            
        st.markdown("---")
        total_fijos = pd.to_numeric(df_editado['Monto'], errors='coerce').sum()
        st.info(f"**Total estimado de Gastos Fijos (Servicios y Actividades):** ${total_fijos:,.2f}")
    except Exception as e:
        st.warning(f"Error. Detalle: {e}")

# --- PANTALLA: DEUDAS ---
elif menu == "🏦 Panel de Deudas":
    st.title("🏦 Panel de Deudas")
    
    try:
        df_deudas_activas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas")
        df_deudas_activas = df_deudas_activas.dropna(subset=['Deuda'])
        
        st.subheader("🔴 Deudas Activas")
        df_deudas_edit = st.data_editor(
            df_deudas_activas, num_rows="dynamic", use_container_width=True,
            column_config={
                "Saldo_Total": st.column_config.NumberColumn("Saldo Total ($)", min_value=0, step=1000),
                "Cuota_Mensual": st.column_config.NumberColumn("Cuota Mensual ($)", min_value=0, step=1000),
                "Cuotas_Restantes": st.column_config.NumberColumn("Cuotas Restantes", min_value=0, step=1)
            }
        )
        
        if st.button("💾 Guardar Cambios en Deudas"):
            conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_edit)
            st.success("¡Deudas actualizadas correctamente!")
            st.cache_data.clear()
            
        st.markdown("---")
        df_deudas_saldadas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Saldadas")
        df_deudas_saldadas = df_deudas_saldadas.dropna(subset=['Deuda'])
        
        st.subheader("✅ Historial de Victorias (Deudas Saldadas)")
        if not df_deudas_saldadas.empty:
            st.dataframe(df_deudas_saldadas, use_container_width=True)
        else:
            st.info("Aquí aparecerán las deudas que logres cancelar.")
    except Exception as e:
        st.warning(f"Error. Detalle: {e}")
