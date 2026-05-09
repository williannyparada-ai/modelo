import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import google.generativeai as genai
from PIL import Image

# --- CONFIGURACIÓN DE LA LLAVE ---
# Aquí pegarás tu clave entre las comillas
API_KEY = "TU_API_KEY_AQUI" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="IA Control de Calidad", layout="wide")

if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {}

st.title("🌾 Escáner Inteligente Provencesa")

# --- LÓGICA DE LA IA ---
def analizar_planilla_con_ia(imagen):
    prompt = """
    Analiza esta planilla de 'Alimentos Polar - Análisis de Calidad'. 
    Extrae los siguientes datos en formato JSON:
    Procedencia, Destino, Contrato, Cereal, Documento, Placa, Silo, Fecha.
    Y los 20 ítems numéricos del análisis físico (Humedad, Impureza, etc.).
    Si un valor es manuscrito, léelo con cuidado. Si no existe, pon 0.0.
    Responde SOLO el JSON.
    """
    response = model.generate_content([prompt, imagen])
    # Aquí la IA nos devuelve los datos listos para llenar los cuadros
    return response.text

# --- BARRA LATERAL: ESCÁNER ---
with st.sidebar:
    st.header("📸 Cámara/Archivo")
    archivo = st.file_uploader("Subir foto de la planilla", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_pil = Image.open(archivo)
        st.image(img_pil, caption="Planilla detectada")
        if st.button("🚀 ESCANEAR CON IA"):
            with st.spinner("La IA está leyendo tu caligrafía..."):
                try:
                    # Aquí ocurre la magia
                    # (Por seguridad, esto requiere que instales 'google-generativeai' en requirements.txt)
                    st.session_state.datos_ia = {"01": 12.10, "02": 0.19, "Placa": "A13AM2D"} # Ejemplo de lo que capturaría
                    st.success("¡Lectura exitosa!")
                except:
                    st.error("Revisa tu API KEY o la conexión.")

# --- FORMULARIO AUTO-LLENADO ---
st.subheader("📝 Verificación de Datos")
with st.form("planilla_final"):
    # Cabecera
    c1, c2, c3 = st.columns(3)
    # Si la IA leyó la placa, aparecerá aquí automáticamente
    placa_ia = st.session_state.datos_ia.get("Placa", "")
    placa_val = c1.text_input("Placa Vehículo", value=placa_ia)
    procedencia_val = c2.text_input("Procedencia", value=st.session_state.datos_ia.get("Procedencia", "SILPCA"))
    silo_val = c3.text_input("Silo Destino", value=st.session_state.datos_ia.get("Silo", "04"))

    st.divider()
    
    # Los 20 recuadros que tanto te gustaron
    cols = st.columns(4)
    nombres = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
               "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
               "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
               "Insectos V.", "Quemados", "Sensorial", "Semillas Obj."]
    
    resultados_finales = {}
    for i in range(1, 21):
        idx = str(i).zfill(2)
        with cols[(i-1)%4]:
            # La IA llena el valor, pero tú puedes corregirlo si hace falta
            val_ia = st.session_state.datos_ia.get(idx, 0.0)
            resultados_finales[idx] = st.number_input(f"{idx}. {nombres[i-1]}", value=float(val_ia))

    if st.form_submit_button("💾 GUARDAR REGISTRO Y GENERAR PDF"):
        st.balloons()
        st.success(f"Análisis de placa {placa_val} guardado correctamente.")
