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

# Configuración de IA - Usamos gemini-1.5-pro por mayor compatibilidad de API
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')
except Exception as e:
    st.error(f"Error de configuración de IA: {e}")

def procesar_planilla_con_ia(imagen_pil):
    prompt = """Analiza la planilla. Extrae los datos y devuelve SOLO un JSON válido con esta estructura:
    {"cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "cereal": "", "documento": ""},
     "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, 
               "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}}"""
    
    try:
        response = model.generate_content([prompt, imagen_pil])
        texto = response.text.replace("```json", "").replace("```", "").strip()
        inicio, fin = texto.find('{'), texto.rfind('}') + 1
        return json.loads(texto[inicio:fin])
    except Exception as e:
        st.error(f"Error al procesar la imagen: {e}")
        return None

# --- ESTRUCTURA ---
nombres_items = [
    "Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
    "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
    "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
    "Insectos V.", "Quemados", "Sensorial", "Fumonisina"
]

# --- 1. RESUMEN ---
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

# --- 2. SIDEBAR ESCÁNER ---
with st.sidebar:
    st.header("📸 Escáner")
    archivo = st.file_uploader("Subir foto", type=['jpg', 'png', 'jpeg'])
    if archivo and st.button("🤖 LEER PLANILLA"):
        with st.spinner("Procesando con IA..."):
            res = procesar_planilla_con_ia(Image.open(archivo))
            if res:
                st.session_state.datos_ia = res
                st.rerun()

# --- 3. FORMULARIO ---
d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_maestro"):
    st.subheader("📋 Datos del Encabezado")
    c1, c2, c3, c4 = st.columns(4)
    f_fecha = c1.date_input("Fecha", datetime.now())
    f_analista = c2.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = c3.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = c4.text_input("Placa", value=cabe.get('placa', ''))
    
    c5, c6, c7, c8 = st.columns(4)
    f_silo = c5.text_input("Silo", value=cabe.get('silo', ''))
    f_destino = c6.text_input("Destino", value=cabe.get('destino', ''))
    f_contrato = c7.text_input("Contrato", value=cabe.get('contrato', ''))
    f_doc = c8.text_input("Documento", value=cabe.get('documento', ''))
    
    c9, c10 = st.columns(2)
    f_cereal = c9.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo"])
    f_origen = c10.selectbox("Origen", ["Nacional", "Importado"])
    
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
        nuevo = {
            "Fecha": f_fecha.strftime("%Y-%m-%d"), "Analista": f_analista, "Procedencia": f_procedencia,
            "Placa": f_placa, "Silo": f_silo, "Destino": f_destino, "Contrato": f_contrato, 
            "Documento": f_doc, "Cereal": f_cereal, "Origen": f_origen, **vals_registro, "Estatus": f_estatus
        }
        st.session_state.historico.append(nuevo)
        st.session_state.datos_ia = {}
        st.rerun()

# --- 4. EXCEL ---
if st.session_state.historico:
    df = pd.DataFrame(st.session_state.historico)
    cols_ordenadas = ["Fecha", "Analista", "Estatus", "Procedencia", "Destino", "Cereal", "Origen", "Silo", "Contrato", "Placa", "Documento"] + nombres_items
    df = df[cols_ordenadas]
    st.dataframe(df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
    
    st.download_button("📥 Descargar Reporte en Excel", buffer.getvalue(), "Reporte_Provencesa.xlsx", "application/vnd.ms-excel")
    
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.historico = []
        st.rerun()
