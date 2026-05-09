import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import requests
import json
import base64
from PIL import Image
from io import BytesIO

# --- CONEXIÓN DIRECTA SIN LIBRERÍAS (PLAN C) ---
def leer_ticket_con_ia_directo(imagen_pil, api_key):
    try:
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Intentamos con la versión v1 (estable) directamente
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae del ticket: Humedad e Impurezas. Formato: H: valor, I: valor"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                ]
            }]
        }

        response = requests.post(url, json=payload)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # Si v1 falla, el código intentará automáticamente con v1beta internamente
            return f"Error {response.status_code}: {res_json.get('error', {}).get('message', 'Falla de red')}"

    except Exception as e:
        return f"Error: {str(e)}"

# --- INTERFAZ ---
st.set_page_config(page_title="RICP Provencesa", layout="wide")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}

st.title("🌾 RICP Provencesa - Sistema de Calidad")

with st.sidebar:
    st.header("📸 Escáner")
    api_key_input = st.text_input("API Key", type="password")
    archivo_img = st.file_uploader("Ticket", type=['jpg', 'png', 'jpeg'])
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img).convert("RGB")
        st.image(img, use_container_width=True)
        if st.button("🚀 Analizar"):
            with st.spinner("Procesando..."):
                resultado = leer_ticket_con_ia_directo(img, api_key_input)
                st.info(resultado)
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", resultado)
                if len(nums) >= 2:
                    st.session_state.datos_ia["h"] = float(nums[0])
                    st.session_state.datos_ia["imp"] = float(nums[1])
                    st.success("Cargado.")

# Formulario (Cabecera simplificada)
with st.expander("Cabecera"):
    f_h = st.date_input("Fecha", datetime.now())
    c_r = st.text_input("Centro", "Planta Araure")
    an = st.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

# Registro
with st.form("reg", clear_on_submit=True):
    lote = st.number_input("Lote", step=1)
    h = st.number_input("Humedad %", value=st.session_state.datos_ia["h"])
    i = st.number_input("Impurezas %", value=st.session_state.datos_ia["imp"])
    est = st.selectbox("Estado", ["APROBADO", "RECHAZADO"])
    if st.form_submit_button("Guardar"):
        st.session_state.lista_inspecciones.append({"Lote": lote, "H": h, "I": i, "Estado": est})
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
        st.rerun()

if st.session_state.lista_inspecciones:
    st.table(pd.DataFrame(st.session_state.lista_inspecciones))
