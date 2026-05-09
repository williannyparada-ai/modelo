import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import google.generativeai as genai
from PIL import Image
import os

# --- LÓGICA DE IA (CONFIGURACIÓN ROBUSTA) ---
def leer_ticket_con_ia_directo(imagen_pil, api_key):
    try:
        # Configuración forzada de la API
        genai.configure(api_key=api_key)
        
        # Usamos el nombre de recurso completo para evitar errores de versión (v1beta/v1)
        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
        
        prompt = """
        Extrae de este ticket de Alimentos Polar los valores de Humedad e Impurezas. 
        Responde estrictamente en este formato:
        Humedad: valor
        Impurezas: valor
        """
        
        # Procesamiento de la imagen
        response = model.generate_content([prompt, imagen_pil])
        
        if response.text:
            return response.text
        else:
            return "Error: El servidor no devolvió datos legibles."
            
    except Exception as e:
        return f"Error de comunicación: {str(e)}"

# --- LÓGICA DEL PDF (REGISTRO INSPECCIÓN) ---
def generar_reporte_consolidado(df_datos, info_cabecera):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "REGISTRO INSPECCIÓN CENTROS EXTERNOS PROVENCESA", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(90, 8, f"Fecha: {info_cabecera['fecha']}", border=1)
    pdf.cell(90, 8, f"Centro: {info_cabecera['centro']}", border=1)
    pdf.cell(97, 8, f"Analista: {info_cabecera['analista']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Encabezados de tabla
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 7, "Lote", border=1)
    pdf.cell(50, 7, "Materia Prima", border=1)
    pdf.cell(25, 7, "Humedad %", border=1)
    pdf.cell(25, 7, "Impureza %", border=1)
    pdf.cell(30, 7, "Estado", border=1)
    pdf.cell(100, 7, "Observaciones", border=1, new_x="LMARGIN", new_y="NEXT")
    
    # Datos de la tabla
    pdf.set_font("helvetica", size=9)
    for _, fila in df_datos.iterrows():
        pdf.cell(30, 7, str(fila['Lote']), border=1)
        pdf.cell(50, 7, str(fila['Tipo']), border=1)
        pdf.cell(25, 7, f"{fila['Humedad']}", border=1)
        pdf.cell(25, 7, f"{fila['Impurezas']}", border=1)
        pdf.cell(30, 7, fila['Estado'], border=1)
        pdf.cell(100, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="RICP Provencesa", layout="wide", page_icon="🌾")

# Inicialización de estados
if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}

st.title("🌾 RICP Provencesa - Escáner Inteligente")

# Sidebar para escaneo
with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("Google API Key", type="password", help="Pega tu clave de Google AI Studio")
    archivo_img = st.file_uploader("Subir ticket Alimentos Polar", type=['jpg', 'png', 'jpeg'])
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img)
        st.image(img, caption="Ticket cargado", use_container_width=True)
        
        if st.button("🚀 Extraer Datos con IA"):
            with st.spinner("Analizando ticket..."):
                resultado = leer_ticket_con_ia_directo(img, api_key_input)
                st.info(f"Resultado: {resultado}")
                
                try:
                    # Limpieza y extracción numérica
                    for linea in resultado.split('\n'):
                        if "Humedad" in linea:
                            num = ''.join(filter(lambda x: x.isdigit() or x=='.', linea))
                            st.session_state.datos_ia["h"] = float(num) if num else 0.0
                        if "Impurezas" in linea:
                            num = ''.join(filter(lambda x: x.isdigit() or x=='.', linea))
                            st.session_state.datos_ia["imp"] = float(num) if num else 0.0
                    st.success("Valores cargados en el formulario.")
                except:
                    st.warning("IA respondió, pero los valores requieren ajuste manual.")

# Cabecera de datos
with st.expander("📝 Configuración de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha de Análisis", datetime.now())
    centro_t = c2.text_input("Centro de Recepción", "Planta Araure")
    analista = c3.selectbox("Analista de Calidad", ["Willianny", "Yusmary", "Osmar"])

# Formulario de Registro
st.header("🚚 Ingreso de Análisis")
with st.form("registro_analisis", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("N° de Lote / Guía", step=1, value=0)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    # Los valores se precargan desde st.session_state si la IA tuvo éxito
    h_val = f1.number_input("Humedad %", value=st.session_state.datos_ia["h"], format="%.2f")
    i_val = f2.number_input("Impurezas %", value=st.session_state.datos_ia["imp"], format="%.2f")
    
    estado = st.selectbox("Dictamen de Calidad", ["APROBADO", "RECHAZADO"])
    obs = st.text_input("Observaciones Adicionales")
    
    if st.form_submit_button("✅ Guardar Análisis"):
        st.session_state.lista_inspecciones.append({
            "Lote": lote, "Tipo": materia, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado, "Motivo": obs if obs else "Sin novedad"
        })
        # Limpiar datos de IA para el siguiente ticket
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
        st.success("Registro añadido a la tabla.")
        st.rerun()

# Tabla de Resultados y PDF
if st.session_state.lista_inspecciones:
    st.divider()
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df, use_container_width=True)
    
    if st.button("📄 GENERAR REPORTE PDF"):
        info = {
            "fecha": fecha_hoy.strftime("%d/%m/%Y"), 
            "centro": centro_t, 
            "analista": analista
        }
        pdf_out = generar_reporte_consolidado(df, info)
        st.download_button(
            label="⬇️ Descargar PDF",
            data=bytes(pdf_out),
            file_name=f"RICP_{centro_t}_{fecha_hoy}.pdf",
            mime="application/pdf"
        )
