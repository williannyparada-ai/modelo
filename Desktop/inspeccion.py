import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import google.generativeai as genai
from PIL import Image

# --- CONFIGURACIÓN DE IA (OCR) ---
# Aquí pondrás tu llave de Google o la configuraremos en Streamlit
API_KEY = st.sidebar.text_input("Configurar Google API Key", type="password")

def leer_ticket_con_ia(imagen):
    if not API_KEY:
        st.warning("Por favor, introduce la API Key en la barra lateral para escanear.")
        return None
    
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Analiza esta imagen de un ticket de laboratorio de cereales. 
    Extrae los valores numéricos de los siguientes campos:
    1. Humedad (Casilla 01)
    2. Impurezas (Casilla 02)
    3. Total de Granos Dañados (Casilla 07)
    4. Total Granos Partidos (Casilla 10)
    5. Análisis Aflatoxina (Casilla 16)
    
    Responde solo en este formato exacto de Python:
    humedad:valor, impurezas:valor, danados:valor, partidos:valor, aflatoxinas:valor
    Si no encuentras uno, pon 0.0. Solo números.
    """
    
    response = model.generate_content([prompt, imagen])
    return response.text

# --- LÓGICA DEL PDF (CORREGIDA) ---
def generar_reporte_consolidado(df_datos, info_cabecera):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "REGISTRO INSPECCIÓN CENTROS EXTERNOS PROVENCESA", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(90, 8, f"Fecha: {info_cabecera['fecha']}", border=1)
    pdf.cell(90, 8, f"Centro: {info_cabecera['centro']}", border=1)
    pdf.cell(97, 8, f"Analista: {info_cabecera['analista']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Detalle de la tabla
    pdf.set_font("helvetica", 'B', 8)
    columnas = ["Lote", "Tipo", "Hum %", "Imp %", "Dañ %", "Part %", "Aflat.", "Estado", "Motivo"]
    anchos = [20, 40, 20, 20, 20, 20, 20, 25, 92]
    
    for i, col in enumerate(columnas):
        pdf.cell(anchos[i], 7, col, border=1, align='C', fill=False)
    pdf.ln()

    pdf.set_font("helvetica", size=8)
    for _, fila in df_datos.iterrows():
        pdf.cell(20, 7, str(int(fila['Lote'])), border=1, align='C')
        pdf.cell(40, 7, str(fila['Tipo']), border=1)
        pdf.cell(20, 7, f"{fila['Humedad']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Impurezas']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Dañados']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Partidos']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Aflatoxinas']:.1f}", border=1, align='C')
        pdf.cell(25, 7, fila['Estado'], border=1, align='C')
        pdf.cell(92, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")

    return pdf.output()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="RICP Inteligente", layout="wide")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []

st.title("🌾 RICP Provencesa - Escáner Inteligente")

# Valores por defecto para el formulario (se actualizan con el escáner)
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"humedad": 0.0, "impurezas": 0.0, "danados": 0.0, "partidos": 0.0, "aflatoxinas": 0.0}

with st.sidebar:
    st.header("📸 Escanear Ticket")
    archivo_subido = st.file_uploader("Subir foto de Alimentos Polar", type=["jpg", "jpeg", "png"])
    if archivo_subido and st.button("🚀 Extraer Datos con IA"):
        img = Image.open(archivo_subido)
        with st.spinner("Leyendo ticket..."):
            resultado = leer_ticket_con_ia(img)
            if resultado:
                # Procesar la respuesta de la IA para meterla en los inputs
                try:
                    partes = resultado.split(",")
                    for p in partes:
                        k, v = p.split(":")
                        st.session_state.datos_ia[k.strip()] = float(v.strip())
                    st.success("¡Datos extraídos! Revisa el formulario abajo.")
                except:
                    st.error("Error al interpretar el ticket. Intenta con una foto más clara.")

# --- FORMULARIO ---
with st.expander("📝 Datos de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_h = c1.date_input("Fecha", datetime.now())
    centro_t = c2.text_input("Centro", "Planta Araure")
    analista_c = c3.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

with st.form("registro_vehiculo", clear_on_submit=True):
    col_d1, col_d2 = st.columns(2)
    lote_v = col_d1.number_input("Lote", step=1)
    tipo_v = col_d2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac."])

    st.subheader("Resultados (Auto-completados por IA si escaneaste)")
    f1, f2, f3, f4, f5 = st.columns(5)
    # Usamos los valores guardados en session_state que vienen de la IA
    h = f1.number_input("Humedad %", value=st.session_state.datos_ia["humedad"])
    imp = f2.number_input("Impurezas %", value=st.session_state.datos_ia["impurezas"])
    dan = f3.number_input("Dañados %", value=st.session_state.datos_ia["danados"])
    par = f4.number_input("Partidos %", value=st.session_state.datos_ia["partidos"])
    afla = f5.number_input("Aflatoxinas", value=st.session_state.datos_ia["aflatoxinas"])
    
    est = st.selectbox("Dictamen", ["APROBADO", "RECHAZADO"])
    mot = st.text_input("Observaciones")

    if st.form_submit_button("✅ Guardar en Lista"):
        nueva_fila = {
            "Lote": lote_v, "Tipo": tipo_v, "Humedad": h, "Impurezas": imp,
            "Dañados": dan, "Partidos": par, "Aflatoxinas": afla, "Estado": est, "Motivo": mot if mot else "Sin novedad"
        }
        st.session_state.lista_inspecciones.append(nueva_fila)
        st.success("Registrado.")

# --- TABLA Y PDF ---
if st.session_state.lista_inspecciones:
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df)
    if st.button("📄 Generar PDF"):
        info = {"fecha": fecha_h.strftime("%d/%m/%Y"), "centro": centro_t, "analista": analista_c}
        pdf_final = generar_reporte_consolidado(df, info)
        st.download_button("⬇️ Descargar Reporte", data=bytes(pdf_final), file_name="RICP_Consolidado.pdf")