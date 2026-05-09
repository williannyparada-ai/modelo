import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import requests
import json
import base64
from PIL import Image
from io import BytesIO

# --- CONEXIÓN A OPENAI (BYPASS TOTAL AL ERROR 404) ---
def leer_ticket_con_openai(imagen_pil, api_key):
    try:
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae de este ticket de Alimentos Polar: Humedad e Impurezas. Responde solo: Humedad: valor, Impurezas: valor"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['choices'][0]['message']['content']
        else:
            return f"Error: {res_json.get('error', {}).get('message', 'Falla de conexión')}"

    except Exception as e:
        return f"Error técnico: {str(e)}"

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
    for h in ["Lote", "Materia Prima", "Humedad %", "Impureza %", "Estado", "Observaciones"]:
        pdf.cell(45, 7, h, border=1)
    pdf.ln()
    
    pdf.set_font("helvetica", size=9)
    for _, fila in df_datos.iterrows():
        pdf.cell(45, 7, str(fila['Lote']), border=1)
        pdf.cell(45, 7, str(fila['Tipo']), border=1)
        pdf.cell(45, 7, str(fila['Humedad']), border=1)
        pdf.cell(45, 7, str(fila['Impurezas']), border=1)
        pdf.cell(45, 7, fila['Estado'], border=1)
        pdf.cell(45, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- INTERFAZ ---
st.set_page_config(page_title="RICP Provencesa", layout="wide")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}

st.title("🌾 RICP Provencesa - Escáner Inteligente")

with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("OpenAI API Key", type="password", help="Usa tu llave de OpenAI para evitar el error 404")
    archivo_img = st.file_uploader("Subir ticket", type=['jpg', 'png', 'jpeg'])
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img).convert("RGB")
        st.image(img, use_container_width=True)
        if st.button("🚀 Extraer con OpenAI"):
            with st.spinner("Analizando..."):
                resultado = leer_ticket_con_openai(img, api_key_input)
                st.info(resultado)
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", resultado.replace(',', '.'))
                if len(nums) >= 2:
                    st.session_state.datos_ia["h"] = float(nums[0])
                    st.session_state.datos_ia["imp"] = float(nums[1])
                    st.success("¡Datos cargados!")

# Formulario
with st.expander("📝 Configuración de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha", datetime.now())
    centro_t = c2.text_input("Centro", "Planta Araure")
    analista = c3.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

st.header("🚚 Ingreso de Análisis")
with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("N° de Lote / Guía", step=1)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    h_val = f1.number_input("Humedad %", value=st.session_state.datos_ia["h"])
    i_val = f2.number_input("Impurezas %", value=st.session_state.datos_ia["imp"])
    
    estado = st.selectbox("Dictamen", ["APROBADO", "RECHAZADO"])
    obs = st.text_input("Observaciones")
    
    if st.form_submit_button("✅ Guardar"):
        st.session_state.lista_inspecciones.append({
            "Lote": lote, "Tipo": materia, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado, "Motivo": obs
        })
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
        st.rerun()

if st.session_state.lista_inspecciones:
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df, use_container_width=True)
    if st.button("📄 GENERAR PDF"):
        info = {"fecha": fecha_hoy.strftime("%d/%m/%Y"), "centro": centro_t, "analista": analista}
        pdf_out = generar_reporte_consolidado(df, info)
        st.download_button("⬇️ Descargar PDF", data=bytes(pdf_out), file_name="Reporte.pdf")
