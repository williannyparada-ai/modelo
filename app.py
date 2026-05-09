import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN PROFESIONAL ---
st.set_page_config(page_title="Control de Calidad - Provencesa", layout="wide")

if 'bitacora' not in st.session_state:
    st.session_state.bitacora = []

st.title("🌾 Registro de Recepción de Cereales")
st.markdown("### Formulario Digital de Análisis Físico")

# --- CABECERA DE LA PLANILLA ---
with st.container():
    st.subheader("📋 Datos de Identificación")
    c1, c2, c3, c4 = st.columns(4)
    analista = c1.selectbox("Analista de Calidad", ["Willianny Parada", "Yusmary", "Osmar"])
    fecha = c2.date_input("Fecha de Análisis", datetime.now())
    procedencia = c3.text_input("Procedencia (Ej: SILPCA)", "SILPCA")
    destino = c4.text_input("Destino", "APC TURMERO")
    
    c5, c6, c7, c8, c9 = st.columns(5)
    n_contrato = c5.text_input("N° Contrato")
    cereal = c6.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo", "Arroz Paddy"])
    documento = c7.text_input("N° Documento / Control")
    placa = c8.text_input("Placa Vehículo")
    silo = c9.text_input("Silo Destino")

st.divider()

# --- BLOQUE DE 20 PARÁMETROS (Réplica de Planilla) ---
st.subheader("🔬 Resultados del Análisis (1-20)")
datos = {}

# Organizado en 3 bloques como la planilla física
col1, col2, col3 = st.columns(3)

with col1:
    st.info("Bloque A")
    datos["01"] = st.number_input("01. Humedad % (Max 24%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["02"] = st.number_input("02. Impureza % (Max 2%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["03"] = st.number_input("03. Germen Dañado % (Max 11%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["04"] = st.number_input("04. Dañado Calor % (Max 3%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["05"] = st.number_input("05. Dañado Insecto % (Max 11%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["06"] = st.number_input("06. Infectados % (Max 11%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["07"] = st.number_input("07. Total Dañados % (Max 11%)", 0.0, 100.0, step=0.01, format="%.2f")

with col2:
    st.info("Bloque B")
    datos["08"] = st.number_input("08. Partidos Pequeños %", 0.0, 100.0, step=0.01, format="%.2f")
    datos["09"] = st.number_input("09. Granos Partidos %", 0.0, 100.0, step=0.01, format="%.2f")
    datos["10"] = st.number_input("10. Total Partidos % (Max 7%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["11"] = st.number_input("11. Cristalizados % (Max 15%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["12"] = st.number_input("12. Mezcla de Color % (Max 3%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["13"] = st.number_input("13. Peso Volumétrico (>= 0,715)", 0.0, 2.0, step=0.001, format="%.3f")
    datos["14"] = st.text_input("14. Color", "N")

with col3:
    st.info("Bloque C")
    datos["15"] = st.text_input("15. Olor", "N")
    datos["16"] = st.number_input("16. Aflatoxina (ppb) (Max 20)", 0.0, 1000.0, step=0.1, format="%.1f")
    datos["17"] = st.number_input("17. N° Insectos Vivos", 0, 100, step=1)
    datos["18"] = st.number_input("18. Granos Quemados % (<= 0,2%)", 0.0, 100.0, step=0.01, format="%.2f")
    datos["19"] = st.text_input("19. Sensorial", "II")
    datos["20"] = st.number_input("20. Semillas Objetadas (Max 1)", 0, 100, step=1)

# --- BOTONES DE ACCIÓN ---
if st.button("📥 GUARDAR ANÁLISIS EN BITÁCORA"):
    registro = {
        "Fecha": fecha, "Analista": analista, "Placa": placa, "Lote": documento,
        "H%": datos["01"], "Imp%": datos["02"], "T.Dañ%": datos["07"], "P.Vol": datos["13"]
    }
    st.session_state.bitacora.append(registro)
    st.success(f"¡Registro {documento} guardado exitosamente!")

# --- GENERACIÓN DE PDF ---
if st.session_state.bitacora:
    st.divider()
    df = pd.DataFrame(st.session_state.bitacora)
    st.write("### 📂 Últimos Registros Guardados")
    st.table(df)

    # Lógica de PDF simplificada
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="REPORTE DE CALIDAD PROVENCESA", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Fecha: {fecha} | Analista: {analista}", ln=True)
    pdf.cell(200, 10, txt=f"Placa: {placa} | Documento: {documento}", ln=True)
    pdf.cell(200, 10, txt=f"Humedad: {datos['01']}% | Impureza: {datos['02']}%", ln=True)
    
    st.download_button("📄 DESCARGAR PDF DEL ANÁLISIS", 
                       data=pdf.output(dest='S').encode('latin-1'), 
                       file_name=f"Analisis_{placa}_{documento}.pdf")
