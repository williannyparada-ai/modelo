import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import json
import io
import pandas as pd

# --- CONFIGURACIÓN DE IA ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    nombre_modelo = next((m for m in modelos if 'gemini-1.5-flash' in m), modelos[0])
    model = genai.GenerativeModel(nombre_modelo)
except Exception as e:
    st.error(f"Error de configuración: {e}")

# Configuración de página
st.set_page_config(page_title="Registro de Información en Centros Externos Provencesa", layout="wide", page_icon="🌾")

# --- MEMORIA DE LA SESIÓN ---
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {}
if 'pdf_listo' not in st.session_state:
    st.session_state.pdf_listo = None

def procesar_planilla_con_ia(imagen_pil):
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    imagen_para_ia = {"mime_type": "image/jpeg", "data": img_bytes}
    
    prompt = """Analiza la planilla de Alimentos Polar. Extrae:
    cabecera: (analista, procedencia, placa, silo, destino, contrato, cereal, documento)
    items: (valores del 01 al 20). 
    Devuelve SOLO el JSON. Si algo no es legible pon 0.0."""
    
    response = model.generate_content([prompt, imagen_para_ia])
    texto = response.text.strip()
    inicio, fin = texto.find('{'), texto.rfind('}') + 1
    return json.loads(texto[inicio:fin])

st.title("🌾 Registro de Información en Centros Externos Provencesa")

# --- 1. PANEL DE ESTADÍSTICAS (ARRIBA) ---
if st.session_state.historico:
    df_hist = pd.DataFrame(st.session_state.historico)
    st.subheader("📊 Resumen de Jornada")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Vehículos", len(df_hist))
    m2.metric("✅ Aprobados", len(df_hist[df_hist['Estatus'] == 'Aprobado']))
    m3.metric("❌ Rechazados", len(df_hist[df_hist['Estatus'] == 'Rechazado']))
    m4.metric("💧 Prom. Humedad", f"{df_hist['Humedad'].mean():.2f}%")
    st.divider()

# --- 2. SIDEBAR (ESCÁNER) ---
with st.sidebar:
    st.header("📸 Escáner de Planilla")
    archivo = st.file_uploader("Subir foto", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_pil = Image.open(archivo)
        st.image(img_pil, use_container_width=True)
        if st.button("🤖 LEER PLANILLA"):
            with st.spinner("IA Procesando..."):
                try:
                    st.session_state.datos_ia = procesar_planilla_con_ia(img_pil)
                    st.success("¡Lectura completada!")
                except: st.error("Error al leer. Reintente.")

# --- 3. FORMULARIO COMPLETO ---
d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_maestro"):
    st.subheader("📋 Datos del Encabezado")
    c1, c2, c3, c4 = st.columns(4)
    f_analista = c1.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = c2.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = c3.text_input("Placa", value=cabe.get('placa', ''))
    f_silo = c4.text_input("Silo", value=cabe.get('silo', ''))
    
    c5, c6, c7, c8 = st.columns(4)
    f_destino = c5.text_input("Destino", value=cabe.get('destino', ''))
    f_contrato = c6.text_input("Contrato", value=cabe.get('contrato', ''))
    f_cereal = c7.text_input("Cereal", value=cabe.get('cereal', ''))
    f_doc = c8.text_input("Documento", value=cabe.get('documento', ''))

    st.divider()
    st.subheader("🔬 Resultados del Análisis Físico")
    nombres = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
               "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
               "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
               "Insectos V.", "Quemados", "Sensorial", "Semillas Obj."]
    
    respuestas = {}
    cols = st.columns(4)
    for i in range(1, 21):
        idx = str(i).zfill(2)
        with cols[(i-1)%4]:
            val_ia = items.get(idx, 0.0)
            try: val_final = float(str(val_ia).replace(',','.'))
            except: val_final = 0.0
            respuestas[nombres[i-1]] = st.number_input(f"{idx}. {nombres[i-1]}", value=val_final)

    st.divider()
    st.subheader("📢 Decisión Final")
    cd1, cd2 = st.columns(2)
    f_estatus = cd1.radio("Estatus del Vehículo:", ["Aprobado", "Rechazado"], horizontal
