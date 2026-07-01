import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import json
import io
import pandas as pd

# --- 1. CONFIGURACIÓN ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Intentamos cargar un modelo compatible. 
    # 'gemini-1.5-flash' es el estándar actual. Si da error, puedes probar con 'gemini-pro'
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de configuración de IA: {e}")

st.set_page_config(page_title="Sistema Provencesa", layout="wide", page_icon="🌾")

if 'historico' not in st.session_state: st.session_state.historico = []
if 'datos_ia' not in st.session_state: st.session_state.datos_ia = {}
if 'pdf_listo' not in st.session_state: st.session_state.pdf_listo = None

# --- 2. LÓGICA DE LECTURA (Basada en tu versión original que funcionaba) ---
def procesar_planilla_con_ia(imagen_pil):
    # Prompt para forzar JSON
    prompt = """Analiza la planilla. Extrae los datos y devuelve SOLO un JSON válido.
    Formato: {"cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "cereal": "", "documento": ""},
    "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, 
              "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}}"""
    
    response = model.generate_content([prompt, imagen_pil])
    # Limpiamos posibles etiquetas markdown de la respuesta
    texto = response.text.replace("```json", "").replace("```", "").strip()
    inicio, fin = texto.find('{'), texto.rfind('}') + 1
    return json.loads(texto[inicio:fin])

# --- 3. INTERFAZ ---
st.title("🌾 Registro de Información en Centros Externos Provencesa")

# Paneles de estadísticas
if st.session_state.historico:
    df_hist = pd.DataFrame(st.session_state.historico)
    st.subheader("📊 Resumen de Jornada")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Vehículos", len(df_hist))
    m2.metric("✅ Aprobados", len(df_hist[df_hist['Estatus'] == 'Aprobado']))
    m3.metric("❌ Rechazados", len(df_hist[df_hist['Estatus'] == 'Rechazado']))
    m4.metric("💧 Prom. Humedad", f"{df_hist['Humedad'].mean():.2f}%")
    st.divider()

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
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al leer: {e}")

# Formulario
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
            respuestas[nombres[i-1]] = st.number_input(f"{idx}. {nombres[i-1]}", value=float(val_ia))

    f_estatus = st.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)
    f_motivo = st.text_input("Motivo de Rechazo:")

    if st.form_submit_button("✅ REGISTRAR Y GENERAR REPORTE"):
        nuevo = {"Fecha": datetime.now().strftime("%H:%M"), "Placa": f_placa, "Cereal": f_cereal, 
                 "Humedad": respuestas["Humedad"], "Estatus": f_estatus, "Motivo": f_motivo}
        st.session_state.historico.append(nuevo)
        
        # Generar PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE DE CALIDAD - PROVENCESA", ln=True, align='C')
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 10, f"Placa: {f_placa} | Estatus: {f_estatus}", ln=True)
        st.session_state.pdf_listo = pdf.output(dest='S').encode('latin-1')
        st.rerun()

# Historial y Descargas
if st.session_state.pdf_listo:
    st.download_button("📥 Descargar PDF", st.session_state.pdf_listo, "reporte.pdf", "application/pdf")

if st.session_state.historico:
    st.subheader("📋 Historial")
    st.dataframe(pd.DataFrame(st.session_state.historico), use_container_width=True)
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.historico = []
        st.rerun()
