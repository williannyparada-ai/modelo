import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd
import google.generativeai as genai
from PIL import Image

# --- LÓGICA DE IA PARA ESCANEO ---
def leer_ticket_con_ia(imagen_pil, api_key):
    try:
        genai.configure(api_key=api_key)
        # Usamos el modelo flash que es el más rápido y estable
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Eres un analista de calidad de cereales. 
        Analiza esta imagen y extrae exclusivamente los valores de Humedad e Impurezas.
        Responde estrictamente en este formato:
        Humedad: valor
        Impurezas: valor
        """
        
        # Esta es la forma correcta de enviar la imagen para evitar el error de InvalidArgument
        response = model.generate_content([prompt, imagen_pil])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- LÓGICA DEL PDF ---
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
    pdf.cell(50, 7, "Tipo", border=1)
    pdf.cell(25, 7, "Hum %", border=1)
    pdf.cell(25, 7, "Imp %", border=1)
    pdf.cell(30, 7, "Estado", border=1)
    pdf.cell(100, 7, "Observaciones", border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", size=9)
    for _, fila in df_datos.iterrows():
        pdf.cell(30, 7, str(fila['Lote']), border=1)
        pdf.cell(50, 7, str(fila['Tipo']), border=1)
        pdf.cell(25, 7, f"{fila['Humedad']}", border=1)
        pdf.cell(25, 7, f"{fila['Impurezas']}", border=1)
        pdf.cell(30, 7, fila['Estado'], border=1)
        pdf.cell(100, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="RICP Provencesa", layout="wide")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []

st.title("🌾 RICP Provencesa - Escáner Inteligente")

# BARRA LATERAL
with st.sidebar:
    st.header("📸 Escanear Ticket")
    api_key_input = st.text_input("Configurar Google API Key", type="password")
    archivo_img = st.file_uploader("Subir foto de Alimentos Polar", type=['jpg', 'png', 'jpeg'])
    
    datos_ia = {"h": 0.0, "imp": 0.0}
    
    if archivo_img and api_key_input:
        img = Image.open(archivo_img)
        st.image(img, caption="Ticket cargado", use_container_width=True)
        if st.button("🚀 Extraer Datos con IA"):
            with st.spinner("Leyendo ticket..."):
                resultado = leer_ticket_con_ia(img, api_key_input)
                st.info(resultado)
                try:
                    for linea in resultado.split('\n'):
                        if "Humedad" in linea: 
                            datos_ia["h"] = float(linea.split(":")[1].replace('%','').strip())
                        if "Impurezas" in linea: 
                            datos_ia["imp"] = float(linea.split(":")[1].replace('%','').strip())
                except:
                    st.warning("No se pudo autocompletar. Revisa manualmente.")

# FORMULARIO
with st.expander("📝 Configuración de Cabecera"):
    c1, c2, c3 = st.columns(3)
    fecha_hoy = c1.date_input("Fecha", datetime.now())
    centro_t = c2.text_input("Centro", "Planta Araure")
    analista = c3.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

st.header("🚚 Ingreso de Análisis")
with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    lote = col1.number_input("Número de Lote", step=1, value=0)
    materia = col2.selectbox("Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac."])
    
    f1, f2 = st.columns(2)
    h_val = f1.number_input("Humedad %", value=datos_ia["h"])
    i_val = f2.number_input("Impurezas %", value=datos_ia["imp"])
    
    estado = st.selectbox("Dictamen", ["APROBADO", "RECHAZADO"])
    obs = st.text_input("Observaciones")
    
    if st.form_submit_button("✅ Guardar en Lista"):
        st.session_state.lista_inspecciones.append({
            "Lote": lote, "Tipo": materia, "Humedad": h_val, 
            "Impurezas": i_val, "Estado": estado, "Motivo": obs if obs else "Sin novedad"
        })
        st.success("Guardado.")

# TABLA
if st.session_state.lista_inspecciones:
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    st.dataframe(df, use_container_width=True)
    if st.button("📄 GENERAR PDF"):
        info = {"fecha": fecha_hoy.strftime("%d/%m/%Y"), "centro": centro_t, "analista": analista}
        pdf_out = generar_reporte_consolidado(df, info)
        st.download_button("⬇️ Descargar PDF", data=bytes(pdf_out), file_name="reporte.pdf")
