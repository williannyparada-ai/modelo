from datetime import datetime
import io
import json
import time
from urllib.parse import quote
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sistema Provencesa - Control de Calidad",
    layout="wide",
    page_icon="🌾",
)

# --- ESTILOS CSS PERSONALIZADOS (Estética Corporativa Profesional) ---
st.markdown(
    """
    <style>
        :root {
            --primary-blue: #00467F;
            --secondary-blue: #0066B3;
            --bg-light: #F8F9FA;
            --text-dark: #333333;
            --border-color: #E0E0E0;
        }
        
        /* Contenedores generales y métricas */
        .kpi-container {
            background-color: #FFFFFF;
            border-left: 4px solid var(--secondary-blue);
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        }

        /* Encabezados de sección estilizados */
        .section-header {
            font-size: 18px;
            color: var(--primary-blue);
            border-bottom: 2px solid var(--primary-blue);
            padding-bottom: 5px;
            margin-top: 25px;
            margin-bottom: 15px;
            font-weight: 600;
        }

        /* Ajuste visual para botones principales */
        .stButton>button {
            border-radius: 6px;
            font-weight: 600;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Etiquetas para resultados
nombres_items = [
    "Humedad",
    "Impureza",
    "Germen Dañado",
    "Dañado Calor",
    "Dañado Insecto",
    "Infectados",
    "Total Dañados",
    "Partidos Peq.",
    "Granos Part.",
    "Total Part.",
    "Cristalizados",
    "Mezcla Color",
    "Peso Vol",
    "Color",
    "Olor",
    "Aflatoxina",
    "Insectos V.",
    "Quemados",
    "Sensorial",
    "Fumonisina",
]

# Inicialización de estado para acumulación persistente
if "historico" not in st.session_state:
  st.session_state.historico = []
if "datos_ia" not in st.session_state:
  st.session_state.datos_ia = {}

# Configuración IA (Búsqueda dinámica de modelo para evitar error 404)
try:
  api_key = st.secrets["GOOGLE_API_KEY"]
  genai.configure(api_key=api_key)
  modelos_disponibles = [
      m.name
      for m in genai.list_models()
      if "generateContent" in m.supported_generation_methods
  ]
  if modelos_disponibles:
    model = genai.GenerativeModel(modelos_disponibles[0])
  else:
    st.error("No se encontraron modelos de IA disponibles.")
except Exception as e:
  st.error(f"Error de configuración: {e}")


# --- FUNCIÓN GENERADORA DE IMAGEN MEJORADA ---
def generar_reporte_infografia(df):
  promedios = df.mean(numeric_only=True)

  img = Image.new("RGB", (800, 1100), color=(255, 255, 255))
  draw = ImageDraw.Draw(img)

  try:
    logo = Image.open("modelo/EPC_cep_pd_2010-sn.webp")
    logo = logo.convert("RGBA")
    w_orig, h_orig = logo.size
    w_max = 300
    h_nuevo = int((h_orig / w_orig) * w_max)
    logo = logo.resize((w_max, h_nuevo), Image.LANCZOS)
    img.paste(logo, (250, 30), logo)
    y_titulo = 30 + h_nuevo + 30
  except Exception as e:
    draw.text((250, 50), "EMPRESAS POLAR", fill=(0, 70, 127))
    y_titulo = 200

  draw.text((270, y_titulo), "REPORTE DIARIO DE RECEPCIÓN", fill=(0, 70, 127))
  draw.text(
      (320, y_titulo + 35),
      f"FECHA: {datetime.now().strftime('%d/%m/%Y')}",
      fill=(100, 100, 100),
  )

  y = y_titulo + 100
  x_etiqueta = 100
  x_valor = 600

  for nombre in nombres_items:
    valor = promedios.get(nombre, 0.0)
    draw.text((x_etiqueta, y), f"{nombre}:", fill=(0, 0, 0))
    draw.text((x_valor, y), f"{valor:.2f}", fill=(0, 70, 127))
    y += 45
    if y > 1000:
      break

  draw.text(
      (300, 1050), f"Vehículos analizados: {len(df)}", fill=(0, 70, 127)
  )

  buffer = io.BytesIO()
  img.save(buffer, format="PNG")
  return buffer.getvalue()


# --- FUNCIÓN DE LECTURA (INDIVIDUAL) ---
def procesar_planilla_con_ia(archivo):
  try:
    imagen_pil = Image.open(archivo).convert("RGB")
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    prompt = """Analiza la planilla y extrae los datos. Devuelve un JSON sin formato Markdown.
      Formato: {"cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "documento": "", "estado": ""},
      "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}}"""

    response = model.generate_content(
        [prompt, {"mime_type": "image/jpeg", "data": img_bytes}]
    )
    texto = response.text.replace("```json", "").replace("```", "").strip()
    inicio, fin = texto.find("{"), texto.rfind("}") + 1
    return json.loads(texto[inicio:fin])
  except Exception as e:
    st.error(f"Error técnico: {e}")
    return None


# --- FUNCIÓN DE LECTURA EN BLOQUE ---
def procesar_bytes_planilla_con_ia(img_bytes):
  try:
    imagen_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format="JPEG")
    img_bytes_limpios = img_byte_arr.getvalue()

    prompt = """Analiza la imagen de esta planilla de laboratorio agroindustrial. Extrae la información disponible de los campos de cabecera (incluyendo 'estado' si aparece geográficamente) y los 20 ítems numéricos de laboratorio. 
    Devuelve ÚNICAMENTE un objeto JSON válido sin bloques de código ni texto adicional, respetando exactamente esta estructura:
    {
      "cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "documento": "", "estado": ""},
      "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}
    }"""

    response = model.generate_content(
        [prompt, {"mime_type": "image/jpeg", "data": img_bytes_limpios}]
    )
    texto = (
        response.text.replace("```json", "")
        .replace("```", "")
        .strip()
    )
    inicio, fin = texto.find("{"), texto.rfind("}") + 1
    if inicio != -1 and fin != 0:
      return json.loads(texto[inicio:fin])
    return None
  except Exception as e:
    raise e


# --- 1. RESUMEN DE JORNADA Y TENDENCIAS ---
if st.session_state.historico:
  df_hist = pd.DataFrame(st.session_state.historico)
  df_hist["Fecha_Hora"] = pd.to_datetime(
      df_hist["Fecha"] + " " + datetime.now().strftime("%H:%M:%S")
  )

  st.markdown(
      '<div class="section-header">📊 Resumen de Jornada Acumulado</div>',
      unsafe_allow_html=True,
  )

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Total Acumulado", len(df_hist))
  m2.metric("✅ Aprobados", len(df_hist[df_hist["Estatus"] == "Aprobado"]))
  m3.metric("❌ Rechazados", len(df_hist[df_hist["Estatus"] == "Rechazado"]))
  m4.metric("💧 Prom. Humedad", f"{df_hist['Humedad'].mean():.2f} %")

  col_prom1, col_prom2, col_prom3 = st.columns(3)
  col_prom1.metric("🌾 Prom. GDT", f"{df_hist['Total Dañados'].mean():.2f} %")
  col_prom2.metric(
      "🍄 Prom. Aflatoxina", f"{df_hist['Aflatoxina'].mean():.2f} PPB"
  )
  col_prom3.metric(
      "🧪 Prom. Fumonisina", f"{df_hist['Fumonisina'].mean():.2f} PPM"
  )

  st.write("")

  with st.expander(
      "📈 Ver Gráficos de Tendencia (Acumulado de la Jornada)", expanded=False
  ):
    c1, c2 = st.columns(2)

    with c1:
      st.caption("Tendencia de Humedad")
      st.line_chart(df_hist["Humedad"], use_container_width=True)
      st.caption("Tendencia de Aflatoxina (PPB)")
      st.line_chart(
          df_hist["Aflatoxina"], color="#FFA07A", use_container_width=True
      )

    with c2:
      st.caption("Tendencia de Granos Dañados Totales (GDT)")
      st.line_chart(
          df_hist["Total Dañados"], color="#90EE90", use_container_width=True
      )
      st.caption("Tendencia de Fumonisina (PPM)")
      st.line_chart(
          df_hist["Fumonisina"], color="#BA55D3", use_container_width=True
      )

  st.divider()

# --- 2. SIDEBAR ---
with st.sidebar:
  st.header("📸 Escáner por Lotes")

  modo_carga = st.radio("Modo de escaneo:", ["Individual", "Lote de Fotos"])

  if modo_carga == "Individual":
    archivo = st.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])
    if archivo and st.button("🤖 LEER PLANILLA"):
      with st.spinner("Procesando..."):
        resultado = procesar_planilla_con_ia(archivo)
        if resultado:
          st.session_state.datos_ia = resultado
          st.rerun()
  else:
    st.info(
        "Sube tus lotes progresivamente (ej. 5 fotos, luego 10 más). Se"
        " acumularán automáticamente."
    )
    archivos_lote = st.file_uploader(
        "Subir fotos de vehículos",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True,
        key="uploader_lotes",
    )

    if archivos_lote:
      total_cargados = len(archivos_lote)
      st.caption(
          f"📁 Archivos cargados en este selector: {total_cargados} fotos."
      )

      if st.button("🤖 PROCESAR LOTE CARGADO (Bloques de 5 recomendados)"):
        lote_a_procesar = archivos_lote[:5]
        barra_progreso = st.progress(0)
        total_archivos = len(lote_a_procesar)
        procesados_exito = 0

        for i, archivo_item in enumerate(lote_a_procesar):
          try:
            img_bytes = archivo_item.getvalue()
            res_json = procesar_bytes_planilla_con_ia(img_bytes)

            time.sleep(3)  # Pausa prudente anti-saturación

            if res_json:
              cabe_lote = res_json.get("cabecera", {})
              items_lote = res_json.get("items", {})

              vals_lote = {}
              for idx_item in range(20):
                k_str = str(idx_item + 1).zfill(2)
                try:
                  val_L = float(items_lote.get(k_str, 0.0))
                except:
                  val_L = 0.0
                vals_lote[nombres_items[idx_item]] = val_L

              nuevo_registro = {
                  "Estado": cabe_lote.get("estado", ""),
                  "Fecha": datetime.now().strftime("%Y-%m-%d"),
                  "Contrato": cabe_lote.get("contrato", "0"),
                  "Maíz": "MBI",
                  "COD MAIZ SAP": "MBI(12202968)",
                  "N° Vehículos Analizados": 1,
                  "Centros Externos": cabe_lote.get("procedencia", "PROVECESA"),
                  "Analista": cabe_lote.get("analista", "Automático"),
                  "Placa": cabe_lote.get("placa", "N/D"),
                  "Silo": cabe_lote.get("silo", "N/D"),
                  "Destino": cabe_lote.get("destino", "N/D"),
                  "Documento": cabe_lote.get("documento", "N/D"),
                  "Cereal": "Maíz Blanco",
                  "Origen": "Nacional",
                  **vals_lote,
                  "Estatus": "Aprobado",
              }
              st.session_state.historico.append(nuevo_registro)
              procesados_exito += 1
            else:
              st.warning(
                  f"La IA no devolvió estructura en: {archivo_item.name}"
              )
          except Exception as ex:
            st.error(f"Error en {archivo_item.name}: {ex}")

          barra_progreso.progress((i + 1) / total_archivos)

        if procesados_exito > 0:
          st.success(
              f"¡Lote procesado con éxito! Se acumularán {procesados_exito}"
              f" registros. Total acumulado en jornada:"
              f" {len(st.session_state.historico)}"
          )
          st.rerun()

  st.divider()

  st.subheader("🗑️ Gestión de Jornada")
  if st.button("🧹 Limpiar Registro Actual (Borrar Acumulado)"):
    st.session_state.historico = []
    st.session_state.datos_ia = {}
    st.success("¡Registro acumulado limpiado con éxito!")
    st.rerun()

# --- 3. FORMULARIO PRINCIPAL ---
d = st.session_state.get("datos_ia", {})
cabe = d.get("cabecera", {})
items = d.get("items", {})

with st.form("registro_maestro"):
  st.markdown(
      '<div class="section-header">📋 Datos del Encabezado</div>',
      unsafe_allow_html=True,
  )

  c1, c2, c3, c4 = st.columns(4)
  f_estado = c1.text_input("Estado", value=cabe.get("estado", ""))
  f_fecha = c2.date_input("Fecha", datetime.now())
  f_contrato = c3.text_input("Contrato", value=cabe.get("contrato", ""))
  f_procedencia = c4.text_input(
      "Centros Externos", value=cabe.get("procedencia", "")
  )

  c5, c6, c7, c8 = st.columns(4)
  f_analista = c5.text_input("Analista", value=cabe.get("analista", ""))
  f_placa = c6.text_input("Placa", value=cabe.get("placa", ""))
  f_silo = c7.text_input("Silo", value=cabe.get("silo", ""))
  f_doc = c8.text_input("Documento", value=cabe.get("documento", ""))

  st.markdown(
      '<div class="section-header">🔬 Resultados de Laboratorio</div>',
      unsafe_allow_html=True,
  )

  cols = st.columns(5)
  vals_registro = {}

  for i in range(20):
    idx = str(i + 1).zfill(2)
    valor_bruto = items.get(idx, 0.0)
    try:
      val_limpio = float(valor_bruto)
    except (ValueError, TypeError):
      val_limpio = 0.0

    with cols[i % 5]:
      vals_registro[nombres_items[i]] = st.number_input(
          f"{nombres_items[i]}", value=val_limpio, step=0.01
      )

  st.write("")
  f_estatus = st.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)

  submit = st.form_submit_button(
      "✅ REGISTRAR Y ACUMULAR EN REPORTE GENERAL", use_container_width=True
  )

  if submit:
    nuevo = {
        "Estado": f_estado,
        "Fecha": f_fecha.strftime("%Y-%m-%d"),
        "Contrato": f_contrato,
        "Maíz": "MBI",
        "COD MAIZ SAP": "MBI(12202968)",
        "N° Vehículos Analizados": 1,
        "Centros Externos": f_procedencia,
        "Analista": f_analista,
        "Placa": f_placa,
        "Silo": f_silo,
        "Documento": f_doc,
        "Cereal": "Maíz Blanco",
        "Origen": "Nacional",
        **vals_registro,
        "Estatus": f_estatus,
    }
    st.session_state.historico.append(nuevo)
    st.session_state.datos_ia = {}
    st.rerun()

# --- REPORTE PARA WHATSAPP ---
st.markdown(
    '<div class="section-header">📱 Reporte para WhatsApp</div>',
    unsafe_allow_html=True,
)

if st.session_state.historico:

  def generar_reporte_profesional(df):
    promedios = df.mean(numeric_only=True)
    reporte = "📋 *REPORTE DIARIO DE RECEPCIÓN*\n"
    reporte += "========================================\n"
    reporte += f"📅 FECHA: {datetime.now().strftime('%d/%m/%Y')}\n"
    reporte += f"🚚 VEHÍCULOS ACUMULADOS: {len(df)}\n"
    reporte += "========================================\n\n"

    campos = [
        ("Humedad", "Humedad %"),
        ("Impureza", "Impureza %"),
        ("Total Dañados", "Grano Dañado Total (GDT)"),
        ("Granos Part.", "Granos Partidos"),
        ("Mezcla Color", "Mezcla Color"),
        ("Peso Vol", "Peso Específico"),
        ("Insectos V.", "Insectos Vivos"),
        ("Aflatoxina", "Aflatoxinas Totales"),
        ("Granos Part. Peq.", "Granos Partidos Pequeños"),
        ("Fumonisina", "Fumonisina"),
    ]

    reporte += "📊 *RESULTADOS PROMEDIOS ACUMULADOS:*\n"
    reporte += "----------------------------------------\n"
    for key, label in campos:
      valor = promedios.get(key, 0.0)
      reporte += f"{label:<28} | {valor:>6.2f}\n"

    reporte += "----------------------------------------\n"
    reporte += f"✅ Aprobados: {len(df[df['Estatus']=='Aprobado'])}  |  ❌ Rechazados: {len(df[df['Estatus']=='Rechazado'])}"
    return reporte

  reporte_final = generar_reporte_profesional(
      pd.DataFrame(st.session_state.historico)
  )
  st.code(reporte_final, language="text")

  link_wa = f"https://wa.me/?text={quote(reporte_final)}"
  st.link_button("🚀 Enviar por WhatsApp", url=link_wa)

else:
  st.info("Aún no hay datos acumulados para generar el reporte.")

# --- 4. EXCEL MULTI-HOJA Y REPORTE VISUAL ---
if st.session_state.historico:
  st.divider()

  df = pd.DataFrame(st.session_state.historico)
  buffer_xls = io.BytesIO()

  with pd.ExcelWriter(buffer_xls, engine="xlsxwriter") as writer:
    df.to_excel(writer, sheet_name="Detalle", index=False)

    if not df.empty:
      columnas_numericas = [col for col in nombres_items if col in df.columns]

      agrupacion_cols = [
          "Estado",
          "Fecha",
          "Contrato",
          "Maíz",
          "COD MAIZ SAP",
          "Centros Externos",
      ]

      df_resumen = (
          df.groupby(agrupacion_cols, dropna=False)
          .agg(
              {
                  **{col: "mean" for col in columnas_numericas},
                  "N° Vehículos Analizados": "sum",
              }
          )
          .reset_index()
      )

      cols_ordenadas = [
          "Estado",
          "Fecha",
          "Contrato",
          "Maíz",
          "COD MAIZ SAP",
          "N° Vehículos Analizados",
          "Centros Externos",
      ] + columnas_numericas
      df_resumen = df_resumen[
          [c for c in cols_ordenadas if c in df_resumen.columns]
      ]

      df_resumen.to_excel(writer, sheet_name="Resumen por Día", index=False)

  st.download_button(
      "📥 Descargar Reporte Excel Acumulado",
      buffer_xls.getvalue(),
      "Reporte_General_Acumulado.xlsx",
      "application/vnd.ms-excel",
  )

  st.markdown(
      '<div class="section-header">🖼️ Reporte Visual Profesional</div>',
      unsafe_allow_html=True,
  )
  if st.button("🎨 Generar Infografía Acumulada"):
    with st.spinner("Diseñando reporte..."):
      img_bytes = generar_reporte_infografia(
          pd.DataFrame(st.session_state.historico)
      )
      st.image(img_bytes, caption="Reporte generado")
      st.download_button(
          "📥 Descargar Reporte (PNG)",
          data=img_bytes,
          file_name=f"Reporte_{datetime.now().strftime('%d%m%Y')}.png",
          mime="image/png",
      )
else:
  st.info("Aún no hay datos acumulados para generar reportes.")
