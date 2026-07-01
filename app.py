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

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except: st.error("Error de configuración de IA")

# --- TU FUNCIÓN DE LECTURA (INTACTA) ---
def procesar_planilla_con_ia(imagen_pil):
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    prompt = """Analiza la planilla y extrae los datos.
    Devuelve un JSON con este formato exacto:
    {"cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "documento": ""},
     "items": {"01": 0.0, "02": 0.0, ... "20": 0.0}}
    No incluyas texto extra, solo el JSON."""
    
    try:
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
        texto = response.text.replace("```json", "").replace("```", "").strip()
        inicio, fin = texto.find('{'), texto.rfind('}') + 1
        return json.loads(texto[inicio:fin])
    except Exception as e:
        return None

# --- NOMBRES PARA EL FORMULARIO ---
nombres_items = [
    "Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
    "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
    "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
    "Insectos V.", "Quemados", "Sensorial", "Fumonisina"
]

# --- 1. RESUMEN DE JORNADA (CON NUEVAS MÉTRICAS) ---
if st.session_state.historico:
    df_hist = pd.DataFrame(st.session_state.historico)
    st.subheader("📊 Resumen de Jornada")
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Total", len(df_hist))
    m2.metric("✅ Aprob.", len(df_hist[df_hist['Estatus'] == 'Aprobado']))
    m3.metric("❌ Rech.", len(df_hist[df_hist['Estatus'] == 'Rechazado']))
    m4.metric("💧 Hum.", f"{df_hist['Humedad'].mean():.2f}")
    m5.metric("🌾 GDT", f"{df_hist['Total Dañados'].mean():.2f}")
    m6.metric("🍄 Aflat.", f"{df_hist['Aflatoxina'].mean():.2f}")
    m7.metric("🧪 Fumonis.", f"{df_hist['Fumonisina'].mean():.2f}")
    st.divider()

# --- 2. SIDEBAR ESCÁNER ---
with st.sidebar:
    st.header("📸 Escáner")
    archivo = st.file_uploader("Subir foto", type=['jpg', 'png', 'jpeg'])
    
    # IMPORTANTE: Cambiamos ligeramente el orden
    if archivo:
        if st.button("🤖 LEER PLANILLA"):
            with st.spinner("Procesando..."):
                resultado = procesar_planilla_con_ia(Image.open(archivo))
                if resultado:
                    st.session_state.datos_ia = resultado
                    st.success("¡Datos extraídos!")
                    st.rerun() # Esto es vital para que el formulario se refresque con los nuevos datos
                else:
                    st.error("Error al leer la imagen. Intenta con otra.")

# --- 3. FORMULARIO ---
# Aseguramos que 'd' siempre sea un diccionario
d = st.session_state.get('datos_ia', {})
if d is None:
    d = {}

cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_maestro"):
    col1, col2, col3, col4 = st.columns(4)
    f_fecha = col1.date_input("Fecha", datetime.now())
    f_cereal = col2.selectbox("Cereal", ["Maíz Amarillo", "Maíz Blanco"])
    f_origen = col3.selectbox("Origen", ["Nacional", "Importado"])
    f_estatus = col4.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)

    # Campos de cabecera
    c1, c2, c3, c4 = st.columns(4)
    f_analista = c1.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = c2.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = c3.text_input("Placa", value=cabe.get('placa', ''))
    f_silo = c4.text_input("Silo", value=cabe.get('silo', ''))
    
    c5, c6, c7, c8 = st.columns(4)
    f_destino = c5.text_input("Destino", value=cabe.get('destino', ''))
    f_contrato = c6.text_input("Contrato", value=cabe.get('contrato', ''))
    f_doc = c7.text_input("Documento", value=cabe.get('documento', ''))
    
    st.subheader("🔬 Resultados de Laboratorio")
    cols = st.columns(5)
    vals_registro = {}
    for i in range(20):
        idx = str(i+1).zfill(2)
        val_ia = items.get(idx, 0.0)
        with cols[i % 5]:
            vals_registro[nombres_items[i]] = st.number_input(f"{nombres_items[i]}", value=float(val_ia))

    if st.form_submit_button("✅ REGISTRAR Y GENERAR EXCEL"):
        nuevo = {
            "Fecha": f_fecha.strftime("%Y-%m-%d"), "Cereal": f_cereal, "Origen": f_origen,
            "Estatus": f_estatus, "Analista": f_analista, "Procedencia": f_procedencia,
            "Placa": f_placa, "Silo": f_silo, "Destino": f_destino, "Contrato": f_contrato, 
            "Documento": f_doc, **vals_registro
        }
        st.session_state.historico.append(nuevo)
        st.session_state.datos_ia = {}
        st.rerun()

# --- 4. EXPORTACIÓN EXCEL ---
if st.session_state.historico:
    df = pd.DataFrame(st.session_state.historico)
    st.dataframe(df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
    
    st.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), "Reporte_Provencesa.xlsx", "application/vnd.ms-excel")
