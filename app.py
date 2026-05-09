import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import google.generativeai as genai
from PIL import Image
import os

# --- LÓGICA DE IA (MÉTODO OFICIAL) ---
def leer_ticket_con_ia_directo(imagen_pil, api_key):
    try:
        # Configuración de la API oficial
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = "Extrae de este ticket de Alimentos Polar los valores de Humedad e Impurezas. Responde solo siguiendo este formato estricto: Humedad: valor, Impurezas: valor"
        
        # Envío directo de la imagen
        response = model.generate_content([prompt, imagen_pil])
        
        if response.text:
            return response.text
        else:
            return "Error: La IA no pudo procesar la imagen."
            
    except Exception as e:
        return f"Error de conexión/configuración: {str(e)}"

# --- LÓGICA DEL PDF ---
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
    
    pdf.set_font("helvetica", 'B', 9)
    columnas = [("Lote", 30), ("Tipo", 50), ("Hum %", 25), ("Imp %", 25), ("Estado", 30), ("Observaciones", 100)]
    for col, ancho in columnas:
        pdf.cell(ancho, 7, col, border=1)
    pdf.ln(7)
    
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
st.set_page_config(page_title="RICP Provencesa", layout="wide")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}

st.title("🌾 RICP Provencesa - Escáner Inteligente")

with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("Configurar Google API Key", type="password")
    archivo_img = st.file_uploader("Subir foto de Alimentos Polar", type=['jpg', 'png', 'jpeg'])
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img)
        st.image(img, caption="Ticket cargado", use_container_width=True)
        if st.button("🚀 Extraer Datos con IA"):
            with st.spinner("Procesando imagen con IA..."):
                resultado = leer_ticket_con_ia_directo(img, api_key_input)
                st.info(f"Respuesta IA: {resultado}")
                try:
                    # Lógica para extraer los números de la respuesta
                    for parte in resultado.split(','):
                        if "Humedad" in parte:
                            st.session_state.datos_ia["h"] = float(''.join(filter(lambda x: x.isdigit() or x=='.', parte)))
                        if "Impurezas" in parte:
                            st.session_state.datos_ia["imp"] = float(''.join(filter(lambda x: x.isdigit() or x=='.', parte)))
                    st.success("Valores cargados correctamente.")
                except Exception as e:
                    st.warning("No se pudieron parsear los decimales automáticamente. Por favor, ingrésalos manual.")

with st.expander("📝 Configuración de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha", datetime.now())
    centro_t = c2.text_input("Centro", "Planta Araure")
    analista = c3.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

st.header("🚚 Ingreso de Análisis")
with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("Número de Lote", step=1, value=0)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    h_val = f1.number_input("Humedad %", value=st.session_state.datos_ia["h"], format="%.2f")
    i_val = f2.number_input("Impurezas %", value=st.session_state.datos_ia["imp"], format="%.2f")
    
    estado = st.selectbox("Dictamen", ["APROBADO", "RECHAZADO"])
    obs = st.text_input("Observaciones")
    
    if st.form_submit_button("✅ Guardar en Lista"):
        st.session_state.lista_inspecciones.append({
            "Lote": lote, "Tipo": materia, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado, "Motivo": obs if obs else "Sin novedad"
        })
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
        st.success("Guardado en la tabla temporal.")
        st.rerun()

if st.session_state.lista_inspecciones:
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df, use_container_width=True)
    if st.button("📄 GENERAR PDF"):
        info = {"fecha": fecha_hoy.strftime("%d/%m/%Y"), "centro": centro_t, "analista": analista}
        pdf_out = generar_reporte_consolidado(df, info)
        st.download_button("⬇️ Descargar PDF", data=bytes(pdf_out), file_name=f"reporte_{fecha_hoy}.pdf")
