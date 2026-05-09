import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="Sistema RICP - Provencesa", layout="wide")

# --- ESTADOS DE SESIÓN ---
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {str(i).zfill(2): 0.0 for i in range(1, 21)}

# --- FUNCIÓN PDF ---
def generar_pdf_completo(registro):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REPORTE DE ANÁLISIS DE CALIDAD - PROVENCESA", ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    # Cabecera en el PDF
    pdf.cell(40, 8, "Analista:", 1, 0, 'L', True)
    pdf.cell(100, 8, str(registro['Analista']), 1, 0)
    pdf.cell(40, 8, "Fecha:", 1, 0, 'L', True)
    pdf.cell(0, 8, str(registro['Fecha']), 1, 1)
    
    pdf.cell(40, 8, "Procedencia:", 1, 0, 'L', True)
    pdf.cell(100, 8, str(registro['Procedencia']), 1, 0)
    pdf.cell(40, 8, "Placa:", 1, 0, 'L', True)
    pdf.cell(0, 8, str(registro['Placa']), 1, 1)
    
    pdf.ln(5)
    # Tabla de resultados (20 ítems)
    pdf.set_font("Arial", 'B', 9)
    # Aquí podrías iterar para crear una tabla de 2 filas x 10 columnas o similar
    pdf.cell(0, 10, "Resultados del Análisis Físico:", 0, 1)
    for i in range(1, 21):
        idx = str(i).zfill(2)
        pdf.cell(27, 8, f"{idx}: {registro.get(idx, 0.0)}", 1, 0 if i % 10 != 0 else 1)
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ ---
st.title("🌾 Panel de Control de Calidad")

with st.sidebar:
    st.header("📸 Escáner de Planilla")
    archivo = st.file_uploader("Cargar imagen de Alimentos Polar", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img = Image.open(archivo)
        st.image(img, use_container_width=True)
        if st.button("🔍 LEER DATOS"):
            texto = pytesseract.image_to_string(img.convert('L'))
            numeros = re.findall(r"(\d+[.,]\d+)", texto)
            # Intentar asignar los primeros encontrados a Humedad e Impureza
            if len(numeros) >= 2:
                st.session_state.temp_datos["01"] = float(numeros[0].replace(',', '.'))
                st.session_state.temp_datos["02"] = float(numeros[1].replace(',', '.'))
                st.success("Lectura inicial lista. Verifique abajo.")

# --- FORMULARIO COMPLETO ---
with st.form("registro_total"):
    st.subheader("📋 Información General")
    c1, c2, c3, c4 = st.columns(4)
    analista = c1.selectbox("Analista", ["Willianny Parada", "Yusmary", "Osmar"])
    fecha = c2.date_input("Fecha", datetime.now())
    procedencia = c3.text_input("Procedencia")
    destino = c4.text_input("Destino", "APC Turmero")
    
    c5, c6, c7, c8, c9 = st.columns(5)
    contrato = c5.text_input("N° Contrato")
    cereal = c6.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo", "Arroz"])
    documento = c7.text_input("Documento")
    placa = c8.text_input("Placa Vehículo")
    silo = c9.text_input("Silo")

    st.divider()
    st.subheader("🔬 Resultados Técnicos (1-20)")
    
    nombres = ["Humedad", "Impureza", "Germen Dañado", "Dañado Calor", "Dañado Insecto", 
               "Infectados", "Total Dañados", "Partidos Peq.", "Granos Part.", "Total Part.",
               "Cristalizados", "Mezcla Color", "Peso Vol", "Color", "Olor", "Aflatoxina",
               "Insectos V.", "Quemados", "Sensorial", "Semillas Obj."]
    
    datos_finales = {}
    cols = st.columns(4)
    for i in range(1, 21):
        idx = str(i).zfill(2)
        with cols[(i-1)%4]:
            val_sugerido = st.session_state.temp_datos.get(idx, 0.0)
            datos_finales[idx] = st.number_input(f"{idx}. {nombres[i-1]}", value=float(val_sugerido), format="%.2f", step=0.01)

    if st.form_submit_button("📥 GUARDAR Y REGISTRAR"):
        nuevo_registro = {
            "Analista": analista, "Fecha": fecha, "Procedencia": procedencia, 
            "Placa": placa, "Contrato": contrato, "Cereal": cereal, **datos_finales
        }
        st.session_state.historico.append(nuevo_registro)
        st.success("Registro guardado en la bitácora local.")
        st.rerun()

# --- HISTÓRICO Y PDF ---
if st.session_state.historico:
    st.divider()
    st.subheader("📂 Histórico de la Sesión")
    df = pd.DataFrame(st.session_state.historico)
    st.dataframe(df)
    
    # Generar PDF del último registro
    pdf_bytes = generar_pdf_completo(st.session_state.historico[-1])
    st.download_button("📄 Descargar PDF del último registro", data=pdf_bytes, file_name=f"Analisis_{placa}.pdf")
