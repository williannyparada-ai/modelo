import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import requests
import json
import base64
from PIL import Image
from io import BytesIO

# --- LÓGICA DE IA (PROTOCOLOS DE RESPALDO) ---
def leer_ticket_con_ia_directo(imagen_pil, api_key):
    try:
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Intentamos con Gemini 1.5 Pro que es más estable ante errores 404
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae del ticket de Alimentos Polar los valores de Humedad e Impurezas. Responde solo: Humedad: valor, Impurezas: valor"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                ]
            }]
        }

        response = requests.post(url, json=payload)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # Si falla el Pro, intentamos una ruta alternativa para el Flash
            url_alt = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
            response_alt = requests.post(url_alt, json=payload)
            if response_alt.status_code == 200:
                return response_alt.json()['candidates'][0]['content']['parts'][0]['text']
            return f"Error {response.status_code}: {res_json.get('error', {}).get('message', 'Sin conexión')}"

    except Exception as e:
        return f"Error: {str(e)}"

# --- LÓGICA DEL REPORTE PDF (RESTAURADA) ---
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
    headers = ["Lote", "Materia Prima", "Humedad %", "Impureza %", "Estado", "Observaciones"]
    widths = [30, 50, 25, 25, 30, 100]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 7, h, border=1)
    pdf.ln()
    
    pdf.set_font("helvetica", size=9)
    for _, fila in df_datos.iterrows():
        pdf.cell(30, 7, str(fila['Lote']), border=1)
        pdf.cell(50, 7, str(fila['Tipo']), border=1)
        pdf.cell(25, 7, str(fila['Humedad']), border=1)
        pdf.cell(25, 7, str(fila['Impurezas']), border=1)
        pdf.cell(30, 7, fila['Estado'], border=1)
        pdf.cell(100, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- INTERFAZ STREAMLIT (RESTAURADA COMPLETAMENTE) ---
st.set_page_config(page_title="RICP Provencesa", layout="wide", page_icon="🌾")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}

st.title("🌾 RICP Provencesa - Escáner Inteligente")

with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("Google API Key", type="password")
    archivo_img = st.file_uploader("Subir ticket Alimentos Polar", type=['jpg', 'png', 'jpeg'])
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img).convert("RGB")
        st.image(img, caption="Ticket cargado", use_container_width=True)
        if st.button("🚀 Extraer Datos con IA"):
            with st.spinner("Analizando ticket con motor Pro..."):
                resultado = leer_ticket_con_ia_directo(img, api_key_input)
                st.info(f"Respuesta: {resultado}")
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", resultado.replace(',', '.'))
                if len(nums) >= 2:
                    st.session_state.datos_ia["h"] = float(nums[0])
                    st.session_state.datos_ia["imp"] = float(nums[1])
                    st.success("Valores cargados en el formulario.")

# Formulario de Registro
with st.expander("📝 Configuración de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha de Análisis", datetime.now())
    centro_t = c2.text_input("Centro de Recepción", "Planta Araure")
    analista = c3.selectbox("Analista de Calidad", ["Willianny", "Yusmary", "Osmar"])

st.header("🚚 Ingreso de Análisis")
with st.form("registro_analisis", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("N° de Lote / Guía", step=1)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    h_val = f1.number_input("Humedad %", value=st.session_state.datos_ia["h"], format="%.2f")
    i_val = f2.number_input("Impurezas %", value=st.session_state.datos_ia["imp"], format="%.2f")
    
    estado = st.selectbox("Dictamen de Calidad", ["APROBADO", "RECHAZADO"])
    obs = st.text_input("Observaciones Adicionales")
    
    if st.form_submit_button("✅ Guardar Análisis"):
        st.session_state.lista_inspecciones.append({
            "Lote": lote, "Tipo": materia, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado, "Motivo": obs if obs else "Sin novedad"
        })
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
        st.success("Registro añadido a la tabla.")
        st.rerun()

# Tabla y PDF
if st.session_state.lista_inspecciones:
    st.divider()
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df, use_container_width=True)
    
    if st.button("📄 GENERAR REPORTE PDF"):
        info = {"fecha": fecha_hoy.strftime("%d/%m/%Y"), "centro": centro_t, "analista": analista}
        pdf_out = generar_reporte_consolidado(df, info)
        st.download_button("⬇️ Descargar PDF", data=bytes(pdf_out), file_name=f"Reporte_{centro_t}.pdf")
