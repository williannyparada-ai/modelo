import streamlit as st
import google.generativeai as genai
from PIL import Image
from datetime import datetime
import json
import io
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema Provencesa", layout="wide", page_icon="🌾")

if 'historico' not in st.session_state: st.session_state.historico = []
if 'datos_ia' not in st.session_state: st.session_state.datos_ia = {}

# Configuración IA
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except: st.error("Error de configuración de IA")

def procesar_planilla_con_ia(imagen_pil):
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    prompt = """Analiza la planilla. Extrae cabecera y los 20 items. 
    Devuelve SOLO JSON con estructura {'cabecera': {...}, 'items': {'01': val, ..., '20': val}}"""
    response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
    texto = response.text.strip()
    return json.loads(texto[texto.find('{'):texto.rfind('}')+1])

# --- ESTRUCTURA DE DATOS ---
nombres_items = [
    "Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
    "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
    "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
    "Insectos V.", "Quemados", "Sensorial", "Fumonisina"
]

# --- 1. RESUMEN DE JORNADA ---
if st.session_state.historico:
    df_hist = pd.DataFrame(st.session_state.historico)
    st.subheader("📊 Resumen de Jornada")
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Total", len(df_hist))
    m2.metric("✅ Aprob.", len(df_hist[df_hist['Estatus'] == 'Aprobado']))
    m3.metric("❌ Rech.", len(df_hist[df_hist['Estatus'] == 'Rechazado']))
    m4.metric("💧 Humedad", f"{df_hist['Humedad'].mean():.2f}")
    m5.metric("🌾 GDT", f"{df_hist['Total Dañados'].mean():.2f}")
    m6.metric("🍄 Aflatoxina", f"{df_hist['Aflatoxina'].mean():.2f}")
    m7.metric("🧪 Fumonisina", f"{df_hist['Fumonisina'].mean():.2f}")
    st.divider()

# --- 2. ESCÁNER ---
with st.sidebar:
    st.header("📸 Escáner")
    archivo = st.file_uploader("Subir planilla", type=['jpg', 'png'])
    if archivo and st.button("🤖 LEER DATOS"):
        st.session_state.datos_ia = procesar_planilla_con_ia(Image.open(archivo))
        st.success("¡Datos extraídos!")

# --- 3. FORMULARIO COMPLETO ---
d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_maestro"):
    st.subheader("📋 Datos del Vehículo")
    c1, c2, c3, c4, c5 = st.columns(5)
    f_fecha = c1.date_input("Fecha", datetime.now())
    f_analista = c2.text_input("Analista", value=cabe.get('analista', ''))
    f_placa = c3.text_input("Placa", value=cabe.get('placa', ''))
    f_cereal = c4.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo"])
    f_origen = c5.selectbox("Origen", ["Nacional", "Importado"])
    
    st.subheader("🔬 Resultados de Laboratorio")
    cols = st.columns(5)
    vals_registro = {}
    for i in range(20):
        idx = str(i+1).zfill(2)
        val_ia = items.get(idx, 0.0)
        with cols[i % 5]:
            vals_registro[nombres_items[i]] = st.number_input(f"{nombres_items[i]}", value=float(val_ia))
    
    f_estatus = st.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)

    if st.form_submit_button("✅ REGISTRAR Y GENERAR EXCEL"):
        nuevo = {"Fecha": f_fecha.strftime("%Y-%m-%d"), "Analista": f_analista, "Placa": f_placa, 
                 "Cereal": f_cereal, "Origen": f_origen, **vals_registro, "Estatus": f_estatus}
        st.session_state.historico.append(nuevo)
        st.rerun()

# --- 4. TABLA Y EXCEL ---
if st.session_state.historico:
    df = pd.DataFrame(st.session_state.historico)
    st.dataframe(df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
    
    st.download_button("📥 Descargar Reporte Completo (Excel)", buffer.getvalue(), "Reporte_Provencesa.xlsx", "application/vnd.ms-excel")
    
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.historico = []
        st.rerun()
