import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re

# --- MOTOR DE EXTRACCIÓN REAL ---
def extraer_datos_ticket(imagen_pil):
    # Convertimos la imagen a escala de grises para mejor lectura
    texto = pytesseract.image_to_string(imagen_pil.convert('L'))
    
    # Creamos un diccionario para guardar lo encontrado
    resultados = {str(i).zfill(2): 0.0 for i in range(1, 21)}
    
    # Buscamos números decimales en el texto extraído
    # Esta es una lógica simplificada: busca patrones de números cerca de palabras clave
    lineas = texto.split('\n')
    
    # Mapeo de palabras clave a sus índices en el ticket
    mapeo = {
        "Humedad": "01",
        "Impureza": "02",
        "Germen": "03",
        "Calor": "04",
        "Insectos": "05",
        "Infectados": "06",
        "Total de Granos": "07",
        "Partido Peque": "08",
        "Granos part": "09",
        "Total Granos": "10",
        "Cristalizados": "11",
        "Peso Vol": "13"
    }

    # Intentamos encontrar los valores en el texto
    for linea in lineas:
        for palabra, idx in mapeo.items():
            if palabra.lower() in linea.lower():
                # Buscamos el número decimal en esa línea
                match = re.search(r"(\d+[.,]\d+)", linea)
                if match:
                    valor = match.group(1).replace(',', '.')
                    resultados[idx] = float(valor)
    
    return resultados

# --- INTERFAZ ---
st.title("🌾 Escáner RICP Provencesa - Visión Real")

with st.sidebar:
    archivo = st.file_uploader("Subir planilla de Alimentos Polar", type=['jpg', 'jpeg', 'png'])
    if archivo:
        img_carga = Image.open(archivo)
        st.image(img_carga, use_container_width=True)
        
        if st.button("🔍 ESCANEAR TICKET REAL"):
            with st.spinner("Leyendo caligrafía del analista..."):
                datos_reales = extraer_datos_ticket(img_carga)
                st.session_state.datos_escaneados = datos_reales
                st.success("Lectura completada. Verifique los campos.")

# --- FORMULARIO CON DATOS REALES ---
# (Aquí el resto de tu código de los 20 campos, usando st.session_state.datos_escaneados)
