import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd

# --- LÓGICA DEL PDF CONSOLIDADO ---
def generar_reporte_consolidado(df_datos, info_cabecera):
    # Usamos orientación 'L' (Landscape/Horizontal) para que quepan todos los datos en el detalle
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Encabezado Corporativo
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "REGISTRO INSPECCIÓN CENTROS EXTERNOS PROVENCESA", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Datos Generales
    pdf.set_font("helvetica", size=10)
    pdf.cell(90, 8, f"Fecha: {info_cabecera['fecha']}", border=1)
    pdf.cell(90, 8, f"Centro: {info_cabecera['centro']}", border=1)
    pdf.cell(97, 8, f"Analista: {info_cabecera['analista']}", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # --- SECCIÓN 1: RESUMEN Y PROMEDIOS (SOLO APROBADOS) ---
    col_izq, col_der = st.columns(2)
    
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 8, "ESTADÍSTICAS Y PROMEDIOS (SOLO VEHÍCULOS APROBADOS)", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    df_aprobados = df_datos[df_datos['Estado'] == 'APROBADO']
    total_v = len(df_datos)
    total_aprob = len(df_aprobados)
    total_rech = total_v - total_aprob

    pdf.set_font("helvetica", size=10)
    pdf.cell(92, 8, f"Total Analizados: {total_v}  |  Aprobados: {total_aprob}  |  Rechazados: {total_rech}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Tabla de Promedios de Aprobados
    cols_tecnicas = ['Humedad', 'Impurezas', 'Dañados', 'Partidos', 'Aflatoxinas']
    if not df_aprobados.empty:
        promedios = df_aprobados[cols_tecnicas].mean()
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", 'B', 9)
        for col in cols_tecnicas:
            pdf.cell(55, 7, f"Prom. {col}", border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_font("helvetica", size=10)
        for col in cols_tecnicas:
            pdf.cell(55, 7, f"{promedios[col]:.2f}", border=1, align='C')
    else:
        pdf.cell(0, 8, "No hay vehículos aprobados para promediar.", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)

    # --- SECCIÓN 2: DETALLE COMPLETO DE VEHÍCULOS ---
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 8, "DETALLE COMPLETO DE LA JORNADA (TODOS LOS VEHÍCULOS)", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", 'B', 8)
    
    # Encabezados de la gran tabla
    pdf.cell(20, 7, "Lote", border=1, align='C')
    pdf.cell(40, 7, "Tipo", border=1, align='C')
    pdf.cell(20, 7, "Hum %", border=1, align='C')
    pdf.cell(20, 7, "Imp %", border=1, align='C')
    pdf.cell(20, 7, "Dañ %", border=1, align='C')
    pdf.cell(20, 7, "Part %", border=1, align='C')
    pdf.cell(20, 7, "Aflat.", border=1, align='C')
    pdf.cell(25, 7, "Estado", border=1, align='C')
    pdf.cell(92, 7, "Motivo / Observaciones", border=1, align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", size=8)
    for _, fila in df_datos.iterrows():
        pdf.cell(20, 7, str(int(fila['Lote'])), border=1, align='C')
        pdf.cell(40, 7, str(fila['Tipo']), border=1)
        pdf.cell(20, 7, f"{fila['Humedad']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Impurezas']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Dañados']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Partidos']:.2f}", border=1, align='C')
        pdf.cell(20, 7, f"{fila['Aflatoxinas']:.1f}", border=1, align='C')
        
        # Color según estado
        pdf.cell(25, 7, fila['Estado'], border=1, align='C')
        pdf.cell(92, 7, str(fila['Motivo']), border=1, new_x="LMARGIN", new_y="NEXT")

    return pdf.output()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="RICP Provencesa", layout="wide")

if 'lista_inspecciones' not in st.session_state:
    st.session_state.lista_inspecciones = []

st.title("🌾 Registro Inspección Centros Externos Provencesa")

with st.expander("📝 Configuración de Cabecera", expanded=False):
    col_c1, col_c2, col_c3 = st.columns(3)
    fecha_hoy = col_c1.date_input("Fecha de Análisis", datetime.now())
    centro_trabajo = col_c2.text_input("Centro / Ubicación", "Planta Araure")
    analista_calidad = col_c3.selectbox("Analista", ["Willianny", "Yusmary", "Osmar"])

st.divider()

# --- FORMULARIO ---
st.header("🚚 Ingreso de Análisis")
with st.form("registro_vehiculo", clear_on_submit=True):
    d1, d2 = st.columns(2)
    lote_v = d1.number_input("Número de Lote / Pedido", step=1, value=0)
    tipo_v = d2.selectbox("Tipo de Materia Prima", ["Maiz Blanco Nac.", "Maiz Amar. Nac.", "Maiz Blanco Imp.", "Maiz Amar. Imp."])
    
    st.write("**Resultados de Laboratorio**")
    f1, f2, f3, f4, f5 = st.columns(5)
    h = f1.number_input("Humedad (%)", value=0.0, format="%.2f")
    imp = f2.number_input("Impurezas (%)", value=0.0, format="%.2f")
    dan = f3.number_input("Dañados (%)", value=0.0, format="%.2f")
    par = f4.number_input("Partidos (%)", value=0.0, format="%.2f")
    afla = f5.number_input("Aflatoxinas (ppb)", value=0.0, format="%.2f")
    
    st.write("---")
    estado_v = st.selectbox("Dictamen Final", ["APROBADO", "RECHAZADO"])
    motivo_v = st.text_input("Observación o Motivo de Rechazo")
    
    if st.form_submit_button("✅ Guardar Vehículo"):
        if estado_v == "RECHAZADO" and not motivo_v:
            st.error("Debe escribir un motivo para los rechazos.")
        else:
            nueva_data = {
                "Lote": lote_v, "Tipo": tipo_v, "Estado": estado_v, 
                "Motivo": motivo_v if motivo_v else "Sin novedad",
                "Humedad": h, "Impurezas": imp, "Dañados": dan, "Partidos": par, "Aflatoxinas": afla
            }
            st.session_state.lista_inspecciones.append(nueva_data)
            st.success(f"Vehículo {lote_v} añadido.")

# --- TABLA Y REPORTE ---
if st.session_state.lista_inspecciones:
    df = pd.DataFrame(st.session_state.lista_inspecciones)
    
    # Cálculos en pantalla para referencia rápida
    df_ap = df[df['Estado'] == 'APROBADO']
    
    st.subheader("📊 Resumen de la Jornada")
    m1, m2, m3 = st.columns(3)
    m1.metric("Analizados Hoy", len(df))
    m2.metric("Aprobados", len(df_ap))
    if not df_ap.empty:
        m3.metric("Prom. Humedad (Aprobados)", f"{df_ap['Humedad'].mean():.2f}%")
    
    st.dataframe(df, use_container_width=True)

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("📄 GENERAR PDF CONSOLIDADO"):
            info_cab = {"fecha": fecha_hoy.strftime("%d/%m/%Y"), "centro": centro_trabajo, "analista": analista_calidad}
            pdf_bytes = generar_reporte_consolidado(df, info_cab)
            st.download_button("⬇️ Descargar Reporte Completo", data=bytes(pdf_bytes), file_name=f"RICP_{fecha_hoy.strftime('%d%m%Y')}.pdf")
    
    with c_btn2:
        if st.button("🗑️ Borrar Todo"):
            st.session_state.lista_inspecciones = []
            st.rerun()