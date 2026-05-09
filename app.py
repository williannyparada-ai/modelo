import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import requests
import json
import base64
from PIL import Image
from io import BytesIO

# --- LÓGICA DE IA (CONEXIÓN WEB DIRECTA - PROTOCOLO BETA) ---
def leer_ticket_con_ia_directo(imagen_pil, api_key):
    try:
        # 1. Preparar la imagen (Convertir a Base64)
        buffered = BytesIO()
        imagen_pil.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # 2. URL de conexión (Usando v1beta para máxima compatibilidad con Gemini 1.5 Flash)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analiza este ticket de Alimentos Polar. Extrae: Humedad e Impurezas. Responde únicamente siguiendo este formato: Humedad: valor, Impurezas: valor"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                ]
            }]
        }

        # 3. Petición POST directa
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            error_msg = res_json.get('error', {}).get('message', 'Error desconocido')
            return f"Error del servidor ({response.status_code}): {error_msg}"

    except Exception as e:
        return f"Error de conexión: {str(e)}"

# --- LÓGICA DEL REPORTE PDF ---
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
    
    # Encabezados
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 7, "Lote", border=1)
    pdf.cell(50, 7, "Materia Prima", border=1)
    pdf.cell(25, 7, "Humedad %", border=1)
    pdf.cell(25, 7, "Impureza %", border=1)
    pdf.cell(30, 7, "Estado", border=1)
    pdf.cell(100, 7, "Observaciones", border=1, new_x="LMARGIN", new_y="NEXT")
    
    # Filas de datos
    pdf.set_font("helvetica", size=9)
    for _, fila in df_datos.iterrows():
        pdf.cell(30, 7, str(fila['Lote']), border=1)
        pdf.cell(50, 7, str(fila['Tipo']), border=1)
        pdf.cell(25, 7, f"{fila['Humedad']}", border=1)
        pdf.cell(25, 7, f"{fila['Impurezas']}", border=1)
        pdf.cell(30, 7, fila['Estado'], border=1)
        pdf.cell(100, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="RICP Provencesa", layout="wide", page_icon="🌾")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []
if 'datos_ia' not in st.session_state:
    st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}

st.title("🌾 RICP Provencesa - Escáner Inteligente")

# Sidebar
with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("Google API Key", type="password")
    archivo_img = st.file_uploader("Subir ticket de Alimentos Polar", type=['jpg', 'png', 'jpeg'])
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img).convert("RGB")
        st.image(img, caption="Ticket cargado", use_container_width=True)
        
        if st.button("🚀 Extraer Datos con IA"):
            with st.spinner("Analizando con protocolo v1beta..."):
                resultado = leer_ticket_con_ia_directo(img, api_key_input)
                st.info(f"Respuesta IA: {resultado}")
                
                try:
                    import re
                    # Buscamos números decimales en la respuesta
                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", resultado)
                    if len(nums) >= 2:
                        st.session_state.datos_ia["h"] = float(nums[0])
                        st.session_state.datos_ia["imp"] = float(nums[1])
                        st.success("Valores cargados en el formulario.")
                except:
                    st.warning("Se recibió respuesta, pero el formato numérico es inusual.")

# Cuerpo principal
with st.expander("📝 Configuración de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha de Análisis", datetime.now())
    centro_t = c2.text_input("Centro de Recepción", "Planta Araure")
    analista = c3.selectbox("Analista de Calidad", ["Willianny", "Yusmary", "Osmar"])

st.header("🚚 Ingreso de Análisis")
with st.form("registro_analisis", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("N° de Lote / Guía", step=1)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Arroz Paddy"])
    
    f1, f2 = st.columns(2)
    # Se precargan los datos de la IA si existen
    h_val = f1.number_input("Humedad %", value=st.session_state.datos_ia["h"], format="%.2f")
    i_val = f2.number_input("Impurezas %", value=st.session_state.datos_ia["imp"], format="%.2f")
    
    estado = st.selectbox("Dictamen", ["APROBADO", "RECHAZADO"])
    obs = st.text_input("Observaciones")
    
    if st.form_submit_button("✅ Guardar Registro"):
        st.session_state.lista_inspecciones.append({
            "Lote": lote, "Tipo": materia, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado, "Motivo": obs if obs else "N/A"
        })
        # Reset de valores temporales
        st.session_state.datos_ia = {"h": 0.0, "imp": 0.0}
        st.success("Análisis guardado localmente.")
        st.rerun()

# Visualización y Exportación
if st.session_state.lista_inspecciones:
    st.divider()
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df, use_container_width=True)
    
    if st.button("📄 GENERAR REPORTE PDF"):
        info = {
            "fecha": fecha_hoy.strftime("%d/%m/%Y"), 
            "centro": centro_t, 
            "analista": analista
        }
        pdf_out = generar_reporte_consolidado(df, info)
        st.download_button(
            label="⬇️ Descargar Reporte Final",
            data=bytes(pdf_out),
            file_name=f"Reporte_Provencesa_{fecha_hoy}.pdf",
            mime="application/pdf"
        )
