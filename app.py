import streamlit as st
import pandas as pd
import requests
import base64
import re
from PIL import Image
from io import BytesIO

# --- MOTOR DE ESCANEO (VERSIÓN ESTABLE) ---
def escanear_ticket_polar(imagen_pil, api_key):
    try:
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Forzamos la URL v1 para evitar errores 404
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        prompt = """Analiza este ticket de Alimentos Polar. Extrae los valores numéricos de:
        1. Humedad, 2. Impureza, 3. Germen Dañado, 4. Dañados Calor, 5. Dañados Insectos, 
        6. Infectados, 7. Total Dañados, 8. Partidos Peq, 9. Partidos, 10. Total Partidos.
        Responde SOLO los números separados por comas en ese orden."""

        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}]}]
        }

        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            texto = res_json['candidates'][0]['content']['parts'][0]['text']
            return re.findall(r"[-+]?\d*\.\d+|\d+", texto.replace(',', '.'))
        return None
    except:
        return None

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="RICP Provencesa", layout="wide")

# Inicializar estados para los 20 parámetros
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = [0.0] * 20 # Espacio para los 20 datos
if 'lista_completa' not in st.session_state:
    st.session_state.lista_completa = []

st.title("🌾 RICP Provencesa - Escáner e Ingreso")

# --- SECCIÓN DEL ESCÁNER (SIDEBAR) ---
with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key = st.text_input("API Key de Google", type="password")
    archivo = st.file_uploader("Subir imagen del ticket", type=['jpg', 'jpeg', 'png'])
    
    if archivo and api_key:
        img = Image.open(archivo).convert("RGB")
        st.image(img, use_container_width=True)
        if st.button("🔍 EJECUTAR ESCÁNER"):
            with st.spinner("Leyendo parámetros del ticket..."):
                resultados = escanear_ticket_polar(img, api_key)
                if resultados and len(resultados) >= 10:
                    # Mapeamos los primeros 10 resultados a nuestro estado
                    for i in range(len(resultados)):
                        if i < 20: st.session_state.datos_ia[i] = float(resultados[i])
                    st.success("✅ Datos extraídos. Revisa el formulario.")
                else:
                    st.error("No se pudo leer automáticamente. Ingresa los datos manualmente.")

# --- FORMULARIO DE 20 PARÁMETROS ---
with st.form("registro_calidad", clear_on_submit=True):
    st.subheader("🚚 Datos de Recepción")
    c1, c2, c3 = st.columns(3)
    lote = c1.text_input("N° Control")
    placa = c2.text_input("Placa")
    cereal = c3.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo", "Arroz Paddy"])

    st.divider()
    st.write("### Resultados de Laboratorio")
    
    # Bloque 1: Humedad (0), Impureza (1), Germen (2), Calor (3)
    col1, col2, col3, col4 = st.columns(4)
    h = col1.number_input("01. Humedad %", value=st.session_state.datos_ia[0], format="%.2f", step=0.01)
    imp = col2.number_input("02. Impureza %", value=st.session_state.datos_ia[1], format="%.2f", step=0.01)
    g_germ = col3.number_input("03. Germen Dañ %", value=st.session_state.datos_ia[2], format="%.2f", step=0.01)
    g_calor = col4.number_input("04. Dañ Calor %", value=st.session_state.datos_ia[3], format="%.2f", step=0.01)

    # Bloque 2: Insectos (4), Infectados (5), Total Dañados (6), Partidos Peq (7)
    col5, col6, col7, col8 = st.columns(4)
    g_ins = col5.number_input("05. Dañ Insectos %", value=st.session_state.datos_ia[4], format="%.2f")
    g_inf = col6.number_input("06. Infectados %", value=st.session_state.datos_ia[5], format="%.2f")
    t_dan = col7.number_input("07. Total Dañados %", value=st.session_state.datos_ia[6], format="%.2f")
    p_peq = col8.number_input("08. Partidos Peq %", value=st.session_state.datos_ia[7], format="%.2f")

    # Bloque 3: Partidos (8), Total Partidos (9), Cristalizados (10), Mezcla (11)
    col9, col10, col11, col12 = st.columns(4)
    g_part = col9.number_input("09. Partidos %", value=st.session_state.datos_ia[8], format="%.2f")
    t_part = col10.number_input("10. Total Partidos %", value=st.session_state.datos_ia[9], format="%.2f")
    g_crist = col11.number_input("11. Cristalizados %", value=st.session_state.datos_ia[10], format="%.2f")
    mezcla = col12.number_input("12. Mezcla Color %", value=st.session_state.datos_ia[11], format="%.2f")

    # ... (Puedes seguir agregando los otros bloques hasta el 20 siguiendo este patrón)
    
    if st.form_submit_button("✅ GUARDAR EN BITÁCORA"):
        st.session_state.lista_completa.append({
            "Lote": lote, "Placa": placa, "Cereal": cereal, "H%": h, "I%": imp, "T.Dañ%": t_dan
        })
        # Limpiar datos de IA para el siguiente ticket
        st.session_state.datos_ia = [0.0] * 20
        st.rerun()

# --- TABLA DE RESULTADOS ---
if st.session_state.lista_completa:
    st.divider()
    df = pd.DataFrame(st.session_state.lista_completa)
    st.dataframe(df, use_container_width=True)
