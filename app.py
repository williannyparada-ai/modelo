import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import json
import io

# --- CONFIGURACIÓN DE IA ROBUSTA ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    nombre_modelo = next((m for m in modelos if 'gemini-1.5-flash' in m), modelos[0])
    model = genai.GenerativeModel(nombre_modelo)
except Exception as e:
    st.error(f"Error de configuración: {e}")

st.set_page_config(
    page_title="Registro de Información en Centros Externos Provencesa", 
    layout="wide", 
    page_icon="🌾"
)

if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {}
if 'pdf_listo' not in st.session_state:
    st.session_state.pdf_listo = None

def procesar_planilla_con_ia(imagen_pil):
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()

    imagen_para_ia = {"mime_type": "image/jpeg", "data": img_bytes}

    prompt = """
    Analiza la planilla de Alimentos Polar y extrae los datos. 
    Es CRÍTICO que tu respuesta sea exclusivamente un objeto JSON válido.
    Asegúrate de incluir:
    - cabecera: analista, procedencia, placa, silo, destino, contrato, cereal, documento.
    - items: valores del 01 al 20.
    Si un valor no es legible, pon 0.0.
    """
    
    response = model.generate_content([prompt, imagen_para_ia])
    texto = response.text.strip()
    
    # --- BUSCADOR DE JSON ROBUSTO ---
    try:
        # Buscamos el primer '{' y el último '}' para ignorar cualquier texto extra
        inicio = texto.find('{')
        fin = texto.rfind('}') + 1
        if inicio != -1 and fin != 0:
            json_puro = texto[inicio:fin]
            return json.loads(json_puro)
        else:
            return json.loads(texto) # Intento normal
    except Exception as e:
        st.error(f"Error al procesar el formato de la IA: {e}")
        # Muestra lo que la IA respondió en la consola para depurar
        print("Respuesta de la IA:", texto)
        return {}

st.title("🌾 Registro de Información en Centros Externos Provencesa")

with st.sidebar:
    st.header("📸 Escáner")
    archivo = st.file_uploader("Subir foto de planilla", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_pil = Image.open(archivo)
        st.image(img_pil, use_container_width=True)
        if st.button("🤖 ESCANEAR CON IA"):
            with st.spinner("Leyendo planilla..."):
                try:
                    st.session_state.datos_ia = procesar_planilla_con_ia(img_pil)
                    st.success("¡Lectura completada!")
                except Exception as e:
                    st.error(f"Error: {e}")

d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

# --- FORMULARIO ---
with st.form("planilla_completa"):
    st.subheader("📋 Datos del Encabezado")
    c1, c2, c3, c4 = st.columns(4)
    f_analista = c1.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = c2.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = c3.text_input("Placa de Vehículo", value=cabe.get('placa', ''))
    f_silo = c4.text_input("Silo", value=cabe.get('silo', ''))
    
    c5, c6, c7, c8 = st.columns(4)
    f_destino = c5.text_input("Destino", value=cabe.get('destino', ''))
    f_contrato = c6.text_input("Número de Contrato", value=cabe.get('contrato', ''))
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
            try: val_final = float(str(val_ia).replace(',', '.'))
            except: val_final = 0.0
            respuestas[idx] = st.number_input(f"{idx}. {nombres[i-1]}", value=val_final)

    enviar = st.form_submit_button("✅ GENERAR REPORTE")
    if enviar:
        # Crear PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE DE CALIDAD - PROVENCESA", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(100, 8, f"Analista: {f_analista}")
        pdf.cell(100, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(100, 8, f"Placa: {f_placa}")
        pdf.cell(100, 8, f"Cereal: {f_cereal}", ln=True)
        pdf.ln(10)
        # Guardar en el estado para descargar afuera del form
        st.session_state.pdf_listo = pdf.output(dest='S').encode('latin-1')

# --- BOTÓN DE DESCARGA (FUERA DEL FORMULARIO) ---
if st.session_state.pdf_listo:
    st.download_button(
        label="📥 DESCARGAR REPORTE PDF",
        data=st.session_state.pdf_listo,
        file_name=f"Analisis_{f_placa}.pdf",
        mime="application/pdf"
    )
