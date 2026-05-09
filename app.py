import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re

def extraer_20_parametros(img):
    # Convertimos a escala de grises y aumentamos contraste para la caligrafía
    img_gris = img.convert('L')
    texto = pytesseract.image_to_string(img_gris, config='--psm 6') # Modo 6: asume bloque de texto uniforme
    
    # Buscamos todos los números con decimales (formato 0,00 o 0.00)
    encontrados = re.findall(r"(\d+[.,]\d+)", texto)
    
    # Creamos el diccionario de resultados
    resultados = {str(i).zfill(2): 0.0 for i in range(1, 21)}
    
    # Asignamos en orden de aparición (esto es lo más cercano a la estructura de la planilla)
    for i, valor in enumerate(encontrados):
        if i < 20:
            idx = str(i+1).zfill(2)
            resultados[idx] = float(valor.replace(',', '.'))
            
    return resultados

# --- En tu app.py, actualiza la parte del botón ---
if st.button("🔍 LEER TICKET"):
    with st.spinner("Procesando los 20 parámetros..."):
        try:
            datos_ia = extraer_20_parametros(img)
            # Actualizamos los 20 campos de una vez
            for k, v in datos_ia.items():
                st.session_state.datos[k] = v
            st.success("✅ Intento de lectura de 20 campos completado.")
        except Exception as e:
            st.error("Error de lectura: Asegúrate de que 'packages.txt' esté configurado.")
