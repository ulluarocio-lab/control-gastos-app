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
menu = st.sidebar.radio("Ir a:", ["📊 Dashboard", "💸 Cargar Gasto", "⚙️ Gastos Fijos", "🏦 Panel de Deudas"])

# --- PANTALLA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Mi Resumen Financiero")
    
    try:
        # Leer datos de la pestaña "Transacciones"
        df_transacciones = conn.read(spreadsheet=SHEET_URL, worksheet="Transacciones")
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
                # Leer los datos actuales
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
                
                # Enviar la actualización a Google Sheets (Corrección aplicada aquí)
                conn.update(spreadsheet=SHEET_URL, worksheet="Transacciones", data=df_actualizado)
                
                st.success(f"✅ Gasto de ${monto} en '{desc}' guardado exitosamente.")
                st.cache_data.clear() # Refresca los datos en segundo plano
            else:
                st.error("Por favor, ingresa una descripción y un monto mayor a 0.")

# --- PANTALLA: GASTOS FIJOS ---
elif menu == "⚙️ Gastos Fijos":
    st.title("⚙️ Administrar Gastos Fijos")
    st.write("Edita los montos de tus servicios o actividades directamente en la tabla.")
    
    try:
        # Leer la pestaña de gastos fijos
        df_fijos = conn.read(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos")
        df_fijos = df_fijos.dropna(subset=['Concepto'])
        
        # Filtro automático para excluir tarjetas de crédito
        df_fijos = df_fijos[~df_fijos['Concepto'].str.contains("Tarjeta", case=False, na=False)]
        
        # Crear un editor interactivo
        df_editado = st.data_editor(
            df_fijos, 
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Monto": st.column_config.NumberColumn("Monto ($)", min_value=0, step=1000)
            }
        )
        
        # Botón para guardar los cambios (Corrección aplicada aquí)
        if st.button("💾 Guardar Cambios en Gastos Fijos"):
            conn.update(spreadsheet=SHEET_URL, worksheet="Gastos_Fijos", data=df_editado)
            st.success("¡Montos actualizados correctamente!")
            st.cache_data.clear()
            
        st.markdown("---")
        total_fijos = pd.to_numeric(df_editado['Monto'], errors='coerce').sum()
        st.info(f"**Total estimado de Gastos Fijos (Servicios y Actividades):** ${total_fijos:,.2f}")
        
    except Exception as e:
        st.warning(f"Asegúrate de haber creado la pestaña 'Gastos_Fijos' en tu Excel. Detalle: {e}")

# --- PANTALLA: DEUDAS ---
elif menu == "🏦 Panel de Deudas":
    st.title("🏦 Panel de Deudas")
    st.write("Gestiona tus deudas activas. Modifica el saldo o descuenta las cuotas cada mes.")
    
    try:
        # Leer y limpiar datos de deudas activas
        df_deudas_activas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Activas")
        df_deudas_activas = df_deudas_activas.dropna(subset=['Deuda'])
        
        st.subheader("🔴 Deudas Activas")
        
        # Crear editor interactivo para las deudas
        df_deudas_edit = st.data_editor(
            df_deudas_activas, 
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Saldo_Total": st.column_config.NumberColumn("Saldo Total ($)", min_value=0, step=1000),
                "Cuota_Mensual": st.column_config.NumberColumn("Cuota Mensual ($)", min_value=0, step=1000),
                "Cuotas_Restantes": st.column_config.NumberColumn("Cuotas Restantes", min_value=0, step=1)
            }
        )
        
        # Botón para guardar cambios (Corrección aplicada aquí)
        if st.button("💾 Guardar Cambios en Deudas"):
            conn.update(spreadsheet=SHEET_URL, worksheet="Deudas_Activas", data=df_deudas_edit)
            st.success("¡Deudas actualizadas correctamente!")
            st.cache_data.clear()
            
        st.markdown("---")
        
        # Leer y mostrar deudas saldadas
        df_deudas_saldadas = conn.read(spreadsheet=SHEET_URL, worksheet="Deudas_Saldadas")
        df_deudas_saldadas = df_deudas_saldadas.dropna(subset=['Deuda'])
        
        st.subheader("✅ Historial de Victorias (Deudas Saldadas)")
        if not df_deudas_saldadas.empty:
            st.dataframe(df_deudas_saldadas, use_container_width=True)
        else:
            st.info("Aquí aparecerán las deudas que logres cancelar. ¡Cada vez falta menos!")
            
    except Exception as e:
        st.warning(f"Asegúrate de tener las columnas correctas en tu Excel. Detalle: {e}")
