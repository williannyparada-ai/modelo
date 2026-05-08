import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import google.generativeai as genai
from PIL import Image

# --- LÓGICA DE IA PARA ESCANEO ---
def leer_ticket_con_ia(imagen_pil, api_key):
    try:
        genai.configure(api_key=api_key)
        # Modelo actualizado para evitar errores de conexión
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Eres un experto en control de calidad de cereales en Venezuela. Analiza esta imagen de un ticket de laboratorio:
        1. Busca los valores de Humedad e Impurezas (pueden estar en tablas o filas).
        2. Responde estrictamente en este formato:
           Humedad: valor
           Impurezas: valor
        Si no los ves o la imagen es ilegible, pon 0.0.
        """
        response = model.generate_content([prompt, imagen_pil])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- LÓGICA DEL PDF CONSOLIDADO ---
def generar_reporte_consolidado(df_datos, info_cabecera):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "REGISTRO INSPECCIÓN CENTROS EXTERNOS PROVENCESA", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Cabecera de datos
    pdf.set_font("helvetica", size=10)
    pdf.cell(90, 8, f"Fecha: {info_cabecera['fecha']}", border=1)
    pdf.cell(90, 8, f"Centro: {info_cabecera['centro']}", border=1)
    pdf.cell(97, 8, f"Analista: {info_cabecera['analista']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Tabla de resultados
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 7, "Lote", border=1, fill=True)
    pdf.cell(50, 7, "Tipo", border=1, fill=True)
    pdf.cell(25, 7, "Hum %", border=1, fill=True)
    pdf.cell(25, 7, "Imp %", border=1, fill=True)
    pdf.cell(30, 7, "Estado", border=1, fill=True)
    pdf.cell(100, 7, "Observaciones", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", size=9)
    for _, fila in df_datos.iterrows():
        pdf.cell(30, 7, str(fila['Lote']), border=1)
        pdf.cell(50, 7, str(fila['Tipo']), border=1)
        pdf.cell(25, 7, f"{fila['Humedad']:.2f}", border=1)
        pdf.cell(25, 7, f"{fila['Impurezas']:.2f}", border=1)
        pdf.cell(30, 7, fila['Estado'], border=1)
        pdf.cell(100, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="RICP Provencesa", layout="wide", page_icon="🌾")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []

st.title("🌾 RICP Provencesa - Escáner Inteligente")

# BARRA LATERAL PARA IA
with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("Configurar Google API Key", type="password")
    archivo_img = st.file_uploader("Subir foto de Alimentos Polar", type=['jpg', 'png', 'jpeg'])
    
    datos_ia = {"h": 0.0, "imp": 0.0}
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img)
        st.image(img, caption="Ticket cargado", use_container_width=True)
        
        # AQUÍ ESTÁ LA CORRECCIÓN DE LA LÍNEA 92
        if st.button("🚀 Extraer Datos con IA"):
            with st.spinner("Leyendo ticket con Gemini AI..."):
                resultado = leer_ticket_con_ia(img, api_key_input)
                st.info(resultado)
                try:
                    for linea in resultado.split('\n'):
                        if "Humedad" in linea: 
                            datos_ia["h"] = float(linea.split(":")[1].strip())
                        if "Impurezas" in linea: 
                            datos_ia["imp"] = float(linea.split(":")[1].strip())
                except:
                    st.warning("No se pudo extraer automáticamente. Revisa el texto arriba.")

# FORMULARIO PRINCIPAL
with st.expander("📝 Configuración de Cabecera", expanded=False):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha", datetime.now())
    centro_t = c2.text_input("Centro", "Planta Araure")
    analista = c3.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

st.header("🚚 Ingreso de Análisis")
with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote_v = col1.number_input("Número de Lote / Pedido", step=1, value=0)
    materia_v = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Pad.", "Trigo"])
    
    st.write("**Valores de Laboratorio**")
    f1, f2 = st.columns(2)
    # Estos campos se llenan con lo que leyó la IA
    h_val = f1.number_input("Humedad (%)", value=datos_ia["h"], format="%.2f")
    i_val = f2.number_input("Impurezas (%)", value=datos_ia["imp"], format="%.2f")
    
    estado_v = st.selectbox("Dictamen Final", ["APROBADO", "RECHAZADO"])
    obs_v = st.text_input("Observaciones o Motivo de Rechazo")
    
    if st.form_submit_button("✅ Guardar en Lista"):
        nueva = {
            "Lote": lote_v, "Tipo": materia_v, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado_v, "Motivo": obs_v if obs_v else "Sin novedad"
        }
        st.session_state.lista_inspecciones.append(nueva)
        st.success(f"Vehículo {lote_v} registrado con éxito.")

# TABLA DE RESUMEN Y PDF
if st.session_state.lista_inspecciones:
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.subheader("📋 Lista de Inspecciones del Día")
    st.dataframe(df, use_container_width=True)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("📄 GENERAR REPORTE PDF"):
            info = {"fecha": fecha_hoy.strftime("%d/%m/%Y"), "centro": centro_t, "analista": analista}
            pdf_out = generar_reporte_consolidado(df, info)
            st.download_button(
                label="⬇️ Descargar PDF",
                data=bytes(pdf_out),
                file_name=f"Reporte_RICP_{fecha_hoy.strftime('%d%m%Y')}.pdf",
                mime="application/pdf"
            )
    with col_p2:
        if st.button("🗑️ Limpiar Todo"):
            st.session_state.lista_inspecciones = []
            st.rerun()
