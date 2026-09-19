import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración inicial de la página
st.set_page_config(page_title="Control de Calidad - Granos", layout="wide")

# Estilos CSS personalizados para los semáforos y contenedores
st.markdown("""
    <style>
    .semaforo-box {
        padding: 10px;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
    .semaforo-amarillo { background-color: #f39c12; }
    .semaforo-verde { background-color: #27ae60; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# INICIALIZACIÓN DEL SESSION STATE
# ---------------------------------------------------------
if "historico" not in st.session_state:
    st.session_state.historico = []

if "datos_ia" not in st.session_state:
    st.session_state.datos_ia = {}

# Lista estándar de los 20 ítems/parámetros de análisis físico-químico
nombres_items = [
    "Humedad (%)", "Impurezas (%)", "Grano Dañado", "Grano Quebrado", 
    "Grano Picado", "Grano Chocho", "Grano Arrugado", "Grano Manchado", 
    "Grano Calizo", "Aflatoxinas (ppb)", "Peso Hectolítrico", "Olor", 
    "Temperatura (°C)", "Gorgojos Vivos", "Gorgojos Muertos", 
    "Hongos Visibles", "Acidez", "Proteína (%)", "Cenizas (%)", "Observaciones"
]

# Función simulada de procesamiento por IA (reemplaza o conecta con tu función real)
def procesar_planilla_con_ia(archivo):
    # Aquí va tu lógica de IA real (ej. Gemini API / OCR)
    # Retornamos un diccionario de ejemplo para que veas la estructura
    return {
        "cabecera": {
            "estado": "Portuguesa",
            "contrato": "CNT-2026-001",
            "placa": "ABC1234",
            "silo": "Silo 06",
            "documento": "GUIA-98765"
        },
        "items": {
            "01": "12.5",  # Humedad
            "02": "0.8",   # Impurezas
        }
    }

# ---------------------------------------------------------
# BARRA LATERAL (ENTRADAS Y PROCESAMIENTO IA)
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración y Carga")
    
    procedencia_lote = st.selectbox("Procedencia / Centro", ["Planta Principal", "Centro Externo A", "Centro Externo B"])
    destino_lote = st.selectbox("Destino", ["Silo Principal", "Secado", "Procesamiento"])
    analista_lote = st.text_input("Analista Responsable", value="Willianny Parada")
    
    st.divider()
    st.subheader("🤖 Lectura Individual con IA")
    
    archivo = st.file_uploader("Sube la foto de la planilla", type=["jpg", "jpeg", "png"])
    
    if archivo and st.button("🤖 LEER PLANILLA"):
        st.markdown(
            '<div class="semaforo-box semaforo-amarillo">🟡 Analizando con IA...</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Procesando imagen..."):
            resultado = procesar_planilla_con_ia(archivo)
            if resultado:
                st.session_state.datos_ia = resultado
                
                # Extraer cabecera e ítems para guardarlos de una vez en el histórico acumulado
                cabe_ind = resultado.get("cabecera", {})
                items_ind = resultado.get("items", {})
                
                vals_ind = {}
                for idx_item in range(20):
                    k_str = str(idx_item + 1).zfill(2)
                    try:
                        val_L = float(items_ind.get(k_str, 0.0))
                    except Exception:
                        val_L = 0.0
                    vals_ind[nombres_items[idx_item]] = val_L

                registro_individual = {
                    "Estado": cabe_ind.get("estado", ""),
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "Contrato": cabe_ind.get("contrato", "0"),
                    "Maíz": "MBI",
                    "COD MAIZ SAP": "MBI(12202968)",
                    "N° Vehículos Analizados": 1,
                    "Centros Externos": procedencia_lote,
                    "Destino": destino_lote,
                    "Analista": analista_lote,
                    "Placa": cabe_ind.get("placa", "N/D"),
                    "Silo": cabe_ind.get("silo", "N/D"),
                    "Documento": cabe_ind.get("documento", "N/D"),
                    "Cereal": "Maíz Blanco",
                    "Origen": "Nacional",
                    **vals_ind,
                    "Estatus": "Aprobado",
                }
                
                # Guardar permanentemente en el acumulado de la jornada para evitar pérdidas
                st.session_state.historico.append(registro_individual)
                st.success("¡Lectura exitosa y acumulada en el reporte!")
                st.rerun()

    st.divider()
    if st.button("🧹 Limpiar Registro Actual"):
        st.session_state.historico = []
        st.session_state.datos_ia = {}
        st.success("¡Histórico limpiado correctamente!")
        st.rerun()

# ---------------------------------------------------------
# CUERPO PRINCIPAL DE LA APLICACIÓN
# ---------------------------------------------------------
st.title("📊 Panel de Control de Calidad y Recepción de Granos")

# Pestañas principales
tab1, tab2 = st.tabs(["📝 Formulario / Datos Actuales", "📈 Histórico Acumulado"])

with tab1:
    st.subheader("Detalles del Análisis Registrado")
    
    # Mostrar datos actuales si la IA los ha cargado
    datos_actuales = st.session_state.get("datos_ia", {})
    cabe = datos_actuales.get("cabecera", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Placa del Vehículo", value=cabe.get("placa", ""), key="input_placa")
    with col2:
        st.text_input("Número de Documento / Guía", value=cabe.get("documento", ""), key="input_doc")
    with col3:
        st.text_input("Silo Asignado", value=cabe.get("silo", ""), key="input_silo")

    st.markdown("### Parámetros Físico-Químicos")
    
    # Crear una grilla limpia para visualizar los 20 parámetros
    items_dict = datos_actuales.get("items", {})
    cols_params = st.columns(4)
    
    for i, nombre_param in enumerate(nombres_items):
        col_idx = i % 4
        k_str = str(i + 1).zfill(2)
        val_default = items_dict.get(k_str, 0.0)
        
        with cols_params[col_idx]:
            st.number_input(nombre_param, value=float(val_default) if str(val_default).replace('.','',1).isdigit() else 0.0, key=f"param_{i}")

with tab2:
    st.subheader("📋 Registros Acumulados en la Jornada")
    
    if len(st.session_state.historico) > 0:
        df_historico = pd.DataFrame(st.session_state.historico)
        st.dataframe(df_historico, use_container_width=True)
        
        # Botón de descarga en Excel/CSV
        csv_data = df_historico.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte en CSV",
            data=csv_data,
            file_name=f"reporte_calidad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay registros acumulados todavía. Sube y lee una planilla en la barra lateral para comenzar.")
