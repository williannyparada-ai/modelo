import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from fpdf import FPDF

st.set_page_config(page_title="RICP Provencesa", layout="wide")

# Inicializar estados
if 'datos' not in st.session_state:
    st.session_state.datos = {str(i).zfill(2): 0.0 for i in range(1, 21)}
if 'historico' not in st.session_state:
    st.session_state.historico = []

st.title("🌾 RICP Provencesa - Visión Real 1-20")

# --- LÓGICA DE ESCANEO ---
with st.sidebar:
    st.header("📸 Escaneo de Planilla")
    archivo = st.file_uploader("Subir imagen de Alimentos Polar", type=['jpg', 'jpeg', 'png'])
    
    if archivo:
        img = Image.open(archivo)
        st.image(img, use_container_width=True)
        if st.button("🔍 LEER TICKET"):
            try:
                # Intento de lectura real
                texto = pytesseract.image_to_string(img.convert('L'))
                # Buscamos patrones numéricos (ejemplo: Humedad 12,10)
                numeros = re.findall(r"(\d+[.,]\d+)", texto)
                if len(numeros) >= 2:
                    st.session_state.datos["01"] = float(numeros[0].replace(',', '.'))
                    st.session_state.datos["02"] = float(numeros[1].replace(',', '.'))
                    st.success(f"Detectado: H:{numeros[0]}% I:{numeros[1]}%")
                else:
                    st.warning("Caligrafía difícil de leer. Por favor, ingrese los datos manualmente.")
            except Exception as e:
                st.error("Configure 'packages.txt' en GitHub para activar el motor.")

# --- FORMULARIO DE 20 CAMPOS ---
with st.form("planilla_polar"):
    st.subheader("📝 Datos del Análisis Físico")
    c1, c2 = st.columns(2)
    lote = c1.text_input("N° Control")
    placa = c2.text_input("Placa")

    # Generamos los 20 campos dinámicamente en 4 columnas
    cols = st.columns(4)
    nombres = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
               "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
               "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
               "Insectos V.", "Quemados", "Sensorial", "Semillas Obj."]
    
    inputs = {}
    for i in range(1, 21):
        idx = str(i).zfill(2)
        with cols[(i-1)%4]:
            # El valor por defecto viene del escáner si tuvo éxito
            val_def = st.session_state.datos.get(idx, 0.0)
            inputs[idx] = st.number_input(f"{idx}. {nombres[i-1]}", value=float(val_def), format="%.2f", step=0.01)

    if st.form_submit_button("✅ GUARDAR REGISTRO"):
        registro = {"Lote": lote, "Placa": placa, **inputs}
        st.session_state.historico.append(registro)
        st.balloons()
        st.rerun()

# --- TABLA Y PDF ---
if st.session_state.historico:
    df = pd.DataFrame(st.session_state.historico)
    st.write("### Bitácora de Recepción")
    st.dataframe(df)
