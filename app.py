import streamlit as st
import pandas as pd
import requests
import base64
import re
from PIL import Image
from io import BytesIO

# --- CONEXIÓN DIRECTA (PROTOCOLO DE SEGURIDAD) ---
def escaneo_forzado(imagen_pil, api_key):
    try:
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Usamos la URL v1 (Estable) para evitar el error 404 de la v1beta
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae del ticket: Humedad e Impurezas. Responde solo los números separados por coma. Ejemplo: 12.5, 0.8"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                ]
            }]
        }

        response = requests.post(url, json=payload, timeout=20)
        res_json = response.json()

        if response.status_code == 200:
            texto = res_json['candidates'][0]['content']['parts'][0]['text']
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto.replace(',', '.'))
            return numeros
        else:
            # Si falla v1, intentamos v1beta como último intento
            url_beta = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            response_beta = requests.post(url_beta, json=payload)
            if response_beta.status_code == 200:
                texto = response_beta.json()['candidates'][0]['content']['parts'][0]['text']
                return re.findall(r"[-+]?\d*\.\d+|\d+", texto.replace(',', '.'))
            return f"Error {response.status_code}: {res_json.get('error', {}).get('message', 'Falla de red')}"
    except Exception as e:
        return f"Error técnico: {str(e)}"

# --- INTERFAZ ---
st.set_page_config(page_title="RICP Provencesa", layout="wide")

if 'h_ia' not in st.session_state: st.session_state.h_ia = 0.0
if 'i_ia' not in st.session_state: st.session_state.i_ia = 0.0
if 'lista' not in st.session_state: st.session_state.lista = []

st.title("🌾 RICP Provencesa - Escáner Inteligente")

with st.sidebar:
    st.header("📸 Captura")
    key = st.text_input("API Key", type="password")
    archivo = st.file_uploader("Subir ticket", type=['jpg', 'jpeg', 'png'])
    
    if archivo and key:
        img = Image.open(archivo).convert("RGB")
        st.image(img, use_container_width=True)
        if st.button("🔍 ESCANEAR RESULTADOS"):
            with st.spinner("Procesando cosecha..."):
                res = escaneo_forzado(img, key)
                if isinstance(res, list) and len(res) >= 2:
                    st.session_state.h_ia = float(res[0])
                    st.session_state.i_ia = float(res[1])
                    st.success("✅ Escaneo exitoso")
                else:
                    st.error(f"Falla: {res}")

# Formulario
st.subheader("🚚 Datos de Recepción")
with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("N° de Lote", step=1)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    h = f1.number_input("Humedad %", value=st.session_state.h_ia, format="%.2f")
    i = f2.number_input("Impurezas %", value=st.session_state.i_ia, format="%.2f")
    
    if st.form_submit_button("✅ Guardar en Lista"):
        st.session_state.lista.append({"Lote": lote, "Materia": materia, "H": h, "I": i})
        st.session_state.h_ia = 0.0
        st.session_state.i_ia = 0.0
        st.rerun()

if st.session_state.lista:
    st.table(pd.DataFrame(st.session_state.lista))
