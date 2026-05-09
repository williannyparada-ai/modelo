import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import json

# Configurar la IA con tu llave secreta
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="IA de Calidad - Provencesa", layout="wide")

# Inicializar datos en la sesión
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {}

st.title("🌾 Escáner Inteligente de Cereales")

# --- LÓGICA DE VISIÓN ---
def procesar_planilla_con_ia(imagen):
    prompt = """
    Analiza esta planilla de Alimentos Polar. Extrae los siguientes datos en formato JSON:
    - cabecera: {procedencia, destino, contrato, cereal, documento, placa, silo, analista, fecha}
    - items: Un diccionario del 01 al 20 con los valores numéricos o de texto que aparezcan en los recuadros.
    Si un campo está vacío, pon 0.0. Devuelve SOLO el JSON puro.
    """
    response = model.generate_content([prompt, imagen])
    # Limpiar la respuesta para obtener solo el JSON
    texto_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(texto_json)

# --- SIDEBAR: CARGA Y ESCANEO ---
with st.sidebar:
    st.header("📸 Captura de Ticket")
    archivo = st.file_uploader("Subir foto de la planilla", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_pil = Image.open(archivo)
        st.image(img_pil, use_container_width=True)
        if st.button("🤖 ESCANEAR CON IA"):
            with st.spinner("La IA está leyendo los datos..."):
                resultado = procesar_planilla_con_ia(img_pil)
                st.session_state.datos_ia = resultado
                st.success("¡Datos extraídos con éxito!")

# --- FORMULARIO CON AUTO-RELLENADO ---
d = st.session_state.datos_ia # Acceso directo a los datos leídos
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("planilla_final"):
    st.subheader("📋 Cabecera (Verificar)")
    c1, c2, c3 = st.columns(3)
    # Si la IA leyó el dato, lo pone. Si no, lo dejas tú.
    analista = c1.text_input("Analista", value=cabe.get('analista', ''))
    procedencia = c2.text_input("Procedencia", value=cabe.get('procedencia', ''))
    placa = c3.text_input("Placa", value=cabe.get('placa', ''))
    
    st.divider()
    st.subheader("🔬 Resultados Técnicos (Auto-completados)")
    col1, col2, col3, col4 = st.columns(4)
    
    # Lista de nombres para los 20 ítems
    nombres = ["Humedad", "Impureza", "Germen D.", "Calor", "Insecto", "Infectados", "Total D.", "Part. Peq", "G. Part.", "Total P.", "Cristal.", "Mezcla", "P. Vol", "Color", "Olor", "Aflatoxina", "Insec. V", "Quemados", "Sensorial", "Semillas"]
    
    respuestas_finales = {}
    for i in range(1, 21):
        idx = str(i).zfill(2)
        with [col1, col2, col3, col4][(i-1)%4]:
            # La IA nos da el valor, nosotros lo mostramos para que lo confirmes
            val_ia = items.get(idx, 0.0)
            # Intentamos convertir a float por si viene como texto
            try: val_ia = float(str(val_ia).replace(',', '.'))
            except: val_ia = 0.0
            
            respuestas_finales[idx] = st.number_input(f"{idx}. {nombres[i-1]}", value=val_ia)

    if st.form_submit_button("💾 GUARDAR Y GENERAR REPORTE"):
        st.balloons()
        st.write("¡Datos guardados!")
        # Aquí puedes añadir tu lógica de PDF que ya tenemos
