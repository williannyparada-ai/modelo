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
    # Usamos gemini-1.0-pro por estabilidad
    model = genai.GenerativeModel('gemini-1.0-pro')
except Exception as e:
    st.error(f"Error de configuración de IA: {e}")

st.set_page_config(page_title="Sistema Provencesa", layout="wide", page_icon="🌾")

# --- MEMORIA Y ESTADO ---
if 'historico' not in st.session_state: st.session_state.historico = []
if 'datos_ia' not in st.session_state: st.session_state.datos_ia = {}
if 'pdf_listo' not in st.session_state: st.session_state.pdf_listo = None

# --- 2. LÓGICA DE LECTURA (CÓDIGO ORIGINAL INTEGRADO) ---
def procesar_planilla_con_ia(imagen_pil):
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    prompt = """Analiza la planilla de Alimentos Polar. Extrae:
    cabecera: (analista, procedencia, placa, silo, destino, contrato, cereal, documento)
    items: (valores del 01 al 20). 
    Devuelve SOLO el JSON. Si algo no es legible pon 0.0."""
    
    response = model.generate_content([prompt, imagen_pil])
    texto = response.text.replace("```json", "").replace("```", "").strip()
    inicio, fin = texto.find('{'), texto.rfind('}') + 1
    return json.loads(texto[inicio:fin])

# --- 3. INTERFAZ Y LÓGICA DE JORNADA ---
st.title("🌾 Registro de Información en Centros Externos Provencesa")

# Estadísticas de la Jornada
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

# Formulario Maestro
d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("registro_maestro"):
    st.subheader("📋 Datos del Encabezado")
    c1, c2, c3, c4 = st.columns(4)
    f_fecha = c1.text_input("Fecha", value=datetime.now().strftime("%Y/%m/%d"))
    f_analista = c2.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = c3.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = c4.text_input("Placa", value=cabe.get('placa', ''))
    
    c5, c6, c7, c8 = st.columns(4)
    f_silo = c5.text_input("Silo", value=cabe.get('silo', ''))
    f_destino = c6.text_input("Destino", value=cabe.get('destino', ''))
    f_contrato = c7.text_input("Contrato", value=cabe.get('contrato', ''))
    f_doc = c8.text_input("Documento", value=cabe.get('documento', ''))

    st.subheader("🔬 Resultados del Análisis Físico")
    nombres = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
               "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
               "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
               "Insectos V.", "Quemados", "Sensorial", "Semillas Obj."]
    
    respuestas = {}
    cols = st.columns(4)
    for i in range(1, 21):
        idx = str(i).zfill(2)
        val_ia = items.get(idx, 0.0)
        with cols[(i-1)%4]:
            respuestas[nombres[i-1]] = st.number_input(f"{idx}. {nombres[i-1]}", value=float(val_ia))

    f_estatus = st.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)
    f_motivo = st.text_input("Motivo de Rechazo:")

    if st.form_submit_button("✅ REGISTRAR VEHÍCULO Y GENERAR REPORTE"):
        nuevo = {"Fecha": f_fecha, "Placa": f_placa, "Humedad": respuestas["Humedad"], 
                 "Estatus": f_estatus, "Motivo": f_motivo, **respuestas}
        st.session_state.historico.append(nuevo)
        
        # Generar PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE DE CALIDAD - PROVENCESA", ln=True, align='C')
        st.session_state.pdf_listo = pdf.output(dest='S').encode('latin-1')
        st.rerun()

# --- 4. EXPORTACIÓN Y ACCIONES ---
if st.session_state.pdf_listo:
    st.download_button("📥 Descargar PDF", st.session_state.pdf_listo, "reporte.pdf", "application/pdf")

if st.session_state.historico:
    st.subheader("📋 Historial de Vehículos")
    df = pd.DataFrame(st.session_state.historico)
    st.dataframe(df, use_container_width=True)
    
    # Exportar Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Jornada en Excel", buffer.getvalue(), "Jornada_Provencesa.xlsx", "application/vnd.ms-excel")
    
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.historico = []
        st.rerun()
