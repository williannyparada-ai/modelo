import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import json
import io

# --- CONFIGURACIÓN DE IA ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("⚠️ La API Key no está configurada en los Secrets de Streamlit.")

# Inicializar estados
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {}
if 'historico' not in st.session_state:
    st.session_state.historico = []

# --- FUNCIÓN DE LECTURA INTELIGENTE ---
def procesar_planilla_con_ia(imagen_pil):
    # Convertir imagen a bytes
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()

    imagen_para_ia = {
        "mime_type": "image/jpeg",
        "data": img_bytes
    }

    # Prompt simplificado para evitar errores de sintaxis en Python
    prompt = "Analiza la planilla. Devuelve SOLO un JSON con 'cabecera' (analista, procedencia, placa, silo) e 'items' (del 01 al 20)."
    
    response = model.generate_content([prompt, imagen_para_ia])
    
    # Esta forma de limpiar es más segura contra errores de SyntaxError
    limpio = response.text.strip()
    if limpio.startswith("```json"):
        limpio = limpio[7:]
    if limpio.endswith("```"):
        limpio = limpio[:-3]
    
    return json.loads(limpio.strip())

# --- INTERFAZ ---
st.title("🌾 Sistema de Recepción Inteligente - Provencesa")

with st.sidebar:
    st.header("📸 Escáner de Planilla")
    archivo = st.file_uploader("Subir foto de Alimentos Polar", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_pil = Image.open(archivo)
        st.image(img_pil, use_container_width=True)
        if st.button("🤖 ESCANEAR CON IA"):
            with st.spinner("La IA está interpretando tu caligrafía..."):
                try:
                    resultado = procesar_planilla_con_ia(img_pil)
                    st.session_state.datos_ia = resultado
                    st.success("¡Lectura completada!")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

# --- FORMULARIO UNIFICADO ---
d = st.session_state.datos_ia
cabe = d.get('cabecera', {})
items = d.get('items', {})

with st.form("planilla_completa"):
    st.subheader("📋 Datos Generales (Cabecera)")
    col_a, col_b, col_c, col_d = st.columns(4)
    f_analista = col_a.text_input("Analista", value=cabe.get('analista', ''))
    f_procedencia = col_b.text_input("Procedencia", value=cabe.get('procedencia', ''))
    f_placa = col_c.text_input("Placa", value=cabe.get('placa', ''))
    f_silo = col_d.text_input("Silo", value=cabe.get('silo', ''))
    
    st.divider()
    st.subheader("🔬 Resultados del Análisis Físico")
    
    nombres = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
               "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
               "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
               "Insectos V.", "Quemados", "Sensorial", "Semillas Obj."]
    
    respuestas = {}
    c = st.columns(4)
    for i in range(1, 21):
        idx = str(i).zfill(2)
        with c[(i-1)%4]:
            val_ia = items.get(idx, 0.0)
            try: val_final = float(str(val_ia).replace(',', '.'))
            except: val_final = 0.0
            respuestas[idx] = st.number_input(f"{idx}. {nombres[i-1]}", value=val_final)

    if st.form_submit_button("✅ GUARDAR Y GENERAR PDF"):
        # Lógica de guardado
        registro_final = {"Analista": f_analista, "Placa": f_placa, **respuestas}
        st.session_state.historico.append(registro_final)
        
        # Generar PDF rápido
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, "REPORTE DE CALIDAD - PROVENCESA", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(200, 10, f"Placa: {f_placa} | Analista: {f_analista} | Fecha: {datetime.now()}", ln=True)
        pdf.ln(5)
        for k, v in respuestas.items():
            pdf.cell(50, 8, f"Item {k}: {v}", 1, 0 if int(k)%3 != 0 else 1)
        
        st.download_button("📄 Descargar Reporte PDF", data=pdf.output(dest='S').encode('latin-1'), file_name=f"Análisis_{f_placa}.pdf")
        st.success("¡Registro archivado!")
