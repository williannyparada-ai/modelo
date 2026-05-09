import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Control de Calidad Provencesa", layout="wide")

if 'lista_completa' not in st.session_state:
    st.session_state.lista_completa = []

st.title("🌾 Análisis de Calidad - Alimentos Polar")

# --- FORMULARIO EXTENDIDO ---
with st.form("analisis_detallado", clear_on_submit=True):
    st.subheader("Datos de Identificación")
    c1, c2, c3 = st.columns(3)
    lote = c1.text_input("N° Control / Documento")
    placa = c2.text_input("Placa Vehículo")
    cereal = c3.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo", "Arroz Paddy"])

    st.divider()
    st.subheader("Resultados del Análisis (1-20)")
    
    # Bloque 1: Humedad a Granos Dañados
    col1, col2, col3, col4 = st.columns(4)
    h = col1.number_input("01. Humedad %", step=0.01, format="%.2f")
    imp = col2.number_input("02. Impurezas %", step=0.01, format="%.2f")
    g_germ_dan = col3.number_input("03. Germen Dañado %", step=0.01, format="%.2f")
    g_dan_calor = col4.number_input("04. Dañados Calor %", step=0.01, format="%.2f")

    # Bloque 2: Insectos a Total Dañados
    col5, col6, col7, col8 = st.columns(4)
    g_dan_ins = col5.number_input("05. Dañados Insectos %", step=0.01, format="%.2f")
    g_inf = col6.number_input("06. Granos Infectados %", step=0.01, format="%.2f")
    tot_dan = col7.number_input("07. Total Dañados %", step=0.01, format="%.2f")
    g_part_peq = col8.number_input("08. Partidos Pequeños %", step=0.01, format="%.2f")

    # Bloque 3: Partidos a Mezcla
    col9, col10, col11, col12 = st.columns(4)
    g_part = col9.number_input("09. Granos Partidos %", step=0.01, format="%.2f")
    tot_part = col10.number_input("10. Total Partidos %", step=0.01, format="%.2f")
    g_crist = col11.number_input("11. Cristalizados %", step=0.01, format="%.2f")
    mezcla = col12.number_input("12. Mezcla Color %", step=0.01, format="%.2f")

    # Bloque 4: Físicos y Organolépticos
    col13, col14, col15, col16 = st.columns(4)
    peso_vol = col13.number_input("13. Peso Volumétrico", step=0.001, format="%.3f")
    color = col14.text_input("14. Color", value="N")
    olor = col15.text_input("15. Olor", value="N")
    aflatoxina = col16.number_input("16. Aflatoxina (ppb)", step=0.1)

    # Bloque 5: Finales
    col17, col18, col19, col20 = st.columns(4)
    insectos_v = col17.number_input("17. Insectos Vivos", step=1)
    g_quemados = col18.number_input("18. Granos Quemados %", step=0.01, format="%.2f")
    sensorial = col19.text_input("19. Sensorial", value="H")
    semillas_obj = col20.number_input("20. Semillas Objetadas", step=1)

    if st.form_submit_button("✅ GUARDAR ANÁLISIS COMPLETO"):
        nuevo_registro = {
            "Lote": lote, "Placa": placa, "Cereal": cereal,
            "Humedad": h, "Impurezas": imp, "Germen Dañ": g_germ_dan,
            "Dañ Calor": g_dan_calor, "Total Dañ": tot_dan, "Peso Vol": peso_vol,
            "Aflatoxina": aflatoxina, "Semillas Obj": semillas_obj
        }
        st.session_state.lista_completa.append(nuevo_registro)
        st.success(f"Registro del lote {lote} guardado correctamente.")
        st.rerun()

# --- VISUALIZACIÓN ---
if st.session_state.lista_completa:
    st.divider()
    st.write("### Histórico de Recepción Detallado")
    df = pd.DataFrame(st.session_state.lista_completa)
    st.dataframe(df, use_container_width=True)
