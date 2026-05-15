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

st.set_page_config(page_title="Registro de Información en Centros Externos Provencesa", layout="wide", page_icon="🌾")

# --- MEMORIA DE LA SESIÓN ---
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {}

def procesar_planilla_con_ia(imagen_pil):
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    imagen_para_ia = {"mime_type": "image/jpeg", "data": img_bytes}
    
    prompt = """Analiza la planilla. Devuelve SOLO un JSON con:
    cabecera: (analista, procedencia, placa, silo, destino, contrato, cereal, documento)
    items: (valores del 01 al 20). Si no se lee, pon 0.0."""
    
    response = model.generate_content([prompt, imagen_para_ia])
    texto = response.text.strip()
    inicio, fin = texto.find('{'), texto.rfind('}') + 1
    return json.loads(texto[inicio:fin])

st.title("🌾 Registro de Información en Centros Externos Provencesa")

# --- PANEL DE ESTADÍSTICAS (ARRIBA) ---
if st.session_state.historico:
    df_hist = pd.DataFrame(st.session_state.historico)
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("Total Vehículos", len(df_hist))
    with col_stat2:
        aprobados = len(df_hist[df_hist['Estatus'] == 'Aprobado'])
        st.metric("✅ Aprobados", aprobados)
    with col_stat3:
        rechazados = len(df_hist[df_hist['Estatus'] == 'Rechazado'])
        st.metric("❌ Rechazados", rechazados)
    with col_stat4:
        prom_hum = df_hist['Humedad'].mean()
        st.metric("💧 Prom. Humedad", f"{prom_hum:.2f}%")
    st.divider()

# --- SIDEBAR (CARGA) ---
with st.sidebar:
    st.header("📸 Escáner")
    archivo = st.file_uploader("Subir foto", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_pil = Image.open(archivo)
        st.image(img_pil, use_container_width=True)
        if st.button("🤖 LEER PLANILLA"):
            with st.spinner("IA Procesando..."):
                st.session_state.datos_ia = procesar_planilla_con_ia(img_pil)
                st.success("Lectura lista")

# --- FORMULARIO DE REGISTRO ---
d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_vehiculo"):
    st.subheader("📝 Datos del Vehículo y Análisis")
    c1, c2, c3, c4 = st.columns(4)
    f_placa = c1.text_input("Placa", value=cabe.get('placa', ''))
    f_cereal = c2.text_input("Cereal", value=cabe.get('cereal', ''))
    f_humedad = c3.number_input("Humedad (%)", value=float(str(items.get('01', 0.0)).replace(',','.')))
    f_impureza = c4.number_input("Impureza (%)", value=float(str(items.get('02', 0.0)).replace(',','.')))

    st.divider()
    col_dec1, col_dec2 = st.columns(2)
    with col_dec1:
        f_estatus = st.radio("📢 Decisión de Recepción:", ["Aprobado", "Rechazado"], horizontal=True)
    with col_dec2:
        f_motivo = st.text_input("⚠️ Motivo de Rechazo (si aplica):", value="")

    if st.form_submit_button("📥 REGISTRAR Y ACUMULAR"):
        nuevo_registro = {
            "Fecha": datetime.now().strftime("%H:%M:%S"),
            "Placa": f_placa,
            "Cereal": f_cereal,
            "Humedad": f_humedad,
            "Impureza": f_impureza,
            "Estatus": f_estatus,
            "Motivo": f_motivo if f_estatus == "Rechazado" else "N/A"
        }
        st.session_state.historico.append(nuevo_registro)
        st.success(f"Vehículo {f_placa} registrado en el histórico.")
        st.rerun()

# --- TABLA DE REGISTROS ACUMULADOS ---
if st.session_state.historico:
    st.subheader("📋 Historial de Recepción del Día")
    st.table(st.session_state.historico)
    
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.historico = []
        st.rerun()
