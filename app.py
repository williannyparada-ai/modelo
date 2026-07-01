import streamlit as st
import google.generativeai as genai
from PIL import Image
from datetime import datetime
import json
import io
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema Provencesa", layout="wide", page_icon="🌾")

# Inicialización de estado
if 'historico' not in st.session_state: st.session_state.historico = []
if 'datos_ia' not in st.session_state: st.session_state.datos_ia = {}

# Configuración IA (Búsqueda dinámica de modelo para evitar error 404)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # Buscamos cualquier modelo disponible que soporte generación
    modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if modelos_disponibles:
        model = genai.GenerativeModel(modelos_disponibles[0])
    else:
        st.error("No se encontraron modelos de IA disponibles.")
except Exception as e:
    st.error(f"Error de configuración: {e}")

# Función de lectura
def procesar_planilla_con_ia(archivo):
    imagen_pil = Image.open(archivo)
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    prompt = """Analiza la planilla y extrae los datos. Devuelve un JSON sin formato Markdown.
    Formato: {"cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "documento": ""},
    "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}}"""
    
    try:
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
        texto = response.text.replace("```json", "").replace("```", "").strip()
        inicio, fin = texto.find('{'), texto.rfind('}') + 1
        return json.loads(texto[inicio:fin])
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None

# Etiquetas para resultados
nombres_items = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.", "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina", "Insectos V.", "Quemados", "Sensorial", "Fumonisina"]

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

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("📸 Escáner")
    archivo = st.file_uploader("Subir foto", type=['jpg', 'png', 'jpeg'])
    if archivo and st.button("🤖 LEER PLANILLA"):
        with st.spinner("Procesando..."):
            resultado = procesar_planilla_con_ia(archivo)
            if resultado:
                st.session_state.datos_ia = resultado
                st.rerun()

# --- 3. FORMULARIO ---
d = st.session_state.get('datos_ia', {})
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_maestro"):
    col1, col2, col3, col4 = st.columns(4)
    f_fecha = col1.date_input("Fecha", datetime.now())
    f_cereal = col2.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo"])
    f_origen = col3.selectbox("Origen", ["Nacional", "Importado"])
    f_estatus = col4.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)

    c1, c2, c3, c4 = st.columns(4)
    f_analista = c1.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = c2.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = c3.text_input("Placa", value=cabe.get('placa', ''))
    f_silo = c4.text_input("Silo", value=cabe.get('silo', ''))
    
    st.subheader("🔬 Resultados de Laboratorio")
    cols = st.columns(5)
    vals_registro = {}
    for i in range(20):
        idx = str(i+1).zfill(2)
        with cols[i % 5]:
            vals_registro[nombres_items[i]] = st.number_input(f"{nombres_items[i]}", value=float(items.get(idx, 0.0)))

    if st.form_submit_button("✅ REGISTRAR Y GENERAR EXCEL"):
        nuevo = {"Fecha": str(f_fecha), "Cereal": f_cereal, "Origen": f_origen, "Estatus": f_estatus, **vals_registro}
        st.session_state.historico.append(nuevo)
        st.session_state.datos_ia = {}
        st.rerun()

# --- 4. EXCEL ---
if st.session_state.historico:
    df = pd.DataFrame(st.session_state.historico)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), "Reporte.xlsx", "application/vnd.ms-excel")
