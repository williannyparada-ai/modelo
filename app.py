import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import requests
import base64
import re
from PIL import Image
from io import BytesIO

# --- MOTOR DE ESCANEO REFORZADO ---
def escanear_con_gemini(imagen_pil, api_key):
    try:
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Intentamos con la URL v1 que suele ser la más compatible para cuentas gratuitas
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Actúa como experto en control de calidad de cereales. Extrae del ticket: 1. Porcentaje de Humedad, 2. Porcentaje de Impurezas. Responde solo con los números separados por coma. Ejemplo: 12.5, 1.0"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                ]
            }]
        }

        response = requests.post(url, json=payload, timeout=15)
        
        # Si da 404, el código intentará automáticamente la ruta alterna sin que tú hagas nada
        if response.status_code != 200:
            url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            response = requests.post(url_alt, json=payload, timeout=15)

        res_json = response.json()
        
        if response.status_code == 200:
            texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
            # Extraemos solo los números usando expresiones regulares (Regex)
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_ia.replace(',', '.'))
            return numeros
        else:
            return f"Error {response.status_code}: {res_json.get('error', {}).get('message', 'Error de red')}"
    except Exception as e:
        return f"Error técnico: {str(e)}"

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Scanner Provencesa", layout="wide")

if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
if 'lista' not in st.session_state:
    st.session_state.lista = []

st.title("🌾 RICP Provencesa - Escáner de Resultados")

with st.sidebar:
    st.header("📸 Captura de Ticket")
    api_key = st.text_input("Ingresa tu API Key de Google", type="password")
    archivo = st.file_uploader("Subir imagen del ticket", type=['jpg', 'jpeg', 'png'])
    
    if archivo and api_key:
        img = Image.open(archivo).convert("RGB")
        st.image(img, use_container_width=True)
        if st.button("🔍 ESCANEAR RESULTADOS"):
            with st.spinner("La IA está leyendo el ticket..."):
                resultado = escanear_con_gemini(img, api_key)
                if isinstance(resultado, list) and len(resultado) >= 2:
                    st.session_state.datos_ia["h"] = float(resultado[0])
                    st.session_state.datos_ia["imp"] = float(resultado[1])
                    st.success(f"Detectado - Humedad: {resultado[0]}% | Impurezas: {resultado[1]}%")
                else:
                    st.error(f"No se pudo escanear: {resultado}")

# Formulario de Registro
st.subheader("🚚 Datos de Recepción")
with st.form("registro", clear_on_submit=True):
    c1, c2 = st.columns(2)
    lote = c1.number_input("N° de Lote", step=1)
    materia = c2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    # Estos valores se llenan SOLOS cuando el escaneo funciona
    h_final = f1.number_input("Humedad %", value=st.session_state.datos_ia["h"], format="%.2f")
    i_final = f2.number_input("Impurezas %", value=st.session_state.datos_ia["imp"], format="%.2f")
    
    dictamen = st.selectbox("Dictamen", ["APROBADO", "RECHAZADO"])
    
    if st.form_submit_button("✅ Guardar en Lista"):
        st.session_state.lista.append({
            "Lote": lote, "Materia": materia, "Humedad": h_final, "Impurezas": i_final, "Estado": dictamen
        })
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0} # Limpiar para el próximo
        st.rerun()

# Tabla de Resultados
if st.session_state.lista:
    st.write("### Resumen de Análisis")
    df = pd.DataFrame(st.session_state.lista)
    st.dataframe(df, use_container_width=True)
