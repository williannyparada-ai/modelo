from datetime import datetime
import io
import json
from urllib.parse import quote
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema Provencesa", layout="wide", page_icon="🌾")

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

# Inicialización de estado
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

  # 1. Crear lienzo blanco
  img = Image.new("RGB", (800, 1100), color=(255, 255, 255))
  draw = ImageDraw.Draw(img)

  # 2. Cargar logo y ajustar proporciones
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

  # 3. Títulos
  draw.text((270, y_titulo), "REPORTE DIARIO DE RECEPCIÓN", fill=(0, 70, 127))
  draw.text(
      (320, y_titulo + 35),
      f"FECHA: {datetime.now().strftime('%d/%m/%Y')}",
      fill=(100, 100, 100),
  )

  # 4. Dibujar resultados
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

  # Footer
  draw.text(
      (300, 1050), f"Vehículos analizados: {len(df)}", fill=(0, 70, 127)
  )

  buffer = io.BytesIO()
  img.save(buffer, format="PNG")
  return buffer.getvalue()


# --- FUNCIÓN DE LECTURA (INDIVIDUAL) ---
def procesar_planilla_con_ia(archivo):
  imagen_pil = Image.open(archivo)
  img_byte_arr = io.BytesIO()
  imagen_pil.save(img_byte_arr, format="JPEG")
  img_bytes = img_byte_arr.getvalue()

  prompt = """Analiza la planilla y extrae los datos. Devuelve un JSON sin formato Markdown.
    Formato: {"cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "documento": ""},
    "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}}"""

  try:
    response = model.generate_content(
        [prompt, {"mime_type": "image/jpeg", "data": img_bytes}]
    )
    texto = response.text.replace("```json", "").replace("```", "").strip()
    inicio, fin = texto.find("{"), texto.rfind("}") + 1
    return json.loads(texto[inicio:fin])
  except Exception as e:
    st.error(f"Error técnico: {e}")
    return None


# --- FUNCIÓN DE LECTURA EN LOTE (NUEVA) ---
def procesar_bytes_planilla_con_ia(img_bytes):
  prompt = """Analiza la planilla y extrae los datos. Devuelve un JSON sin formato Markdown estricto.
    Formato requerido: 
    {
      "cabecera": {"analista": "", "procedencia": "", "placa": "", "silo": "", "destino": "", "contrato": "", "documento": ""},
      "items": {"01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0, "06": 0.0, "07": 0.0, "08": 0.0, "09": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0}
    }"""
  try:
    response = model.generate_content(
        [prompt, {"mime_type": "image/jpeg", "data": img_bytes}]
    )
    texto = response.text.replace("```json", "").replace("```", "").strip()
    inicio, fin = texto.find("{"), texto.rfind("}") + 1
    return json.loads(texto[inicio:fin])
  except Exception as e:
    return None


# --- 1. RESUMEN DE JORNADA Y TENDENCIAS ---
if st.session_state.historico:
  df_hist = pd.DataFrame(st.session_state.historico)
  df_hist["Fecha_Hora"] = pd.to_datetime(
      df_hist["Fecha"] + " " + datetime.now().strftime("%H:%M:%S")
  )

  st.subheader("📊 Resumen de Jornada")

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Total Analizado", len(df_hist))
  m2.metric("✅ Aprobados", len(df_hist[df_hist["Estatus"] == "Aprobado"]))
  m3.metric("❌ Rechazados", len(df_hist[df_hist["Estatus"] == "Rechazado"]))

  col_prom1, col_prom2, col_prom3, col_prom4 = st.columns(4)
  col_prom1.metric("💧 Prom. Humedad", f"{df_hist['Humedad'].mean():.2f} %")
  col_prom2.metric("🌾 Prom. GDT", f"{df_hist['Total Dañados'].mean():.2f} %")
  col_prom3.metric(
      "🍄 Prom. Aflatoxina", f"{df_hist['Aflatoxina'].mean():.2f} PPB"
  )
  col_prom4.metric(
      "🧪 Prom. Fumonisina", f"{df_hist['Fumonisina'].mean():.2f} PPM"
  )

  st.write("")

  with st.expander(
      "📈 Ver Gráficos de Tendencia (vs. Registro #)", expanded=False
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

# --- 2. SIDEBAR (CON CARGA EN LOTE Y MODO INDIVIDUAL) ---
with st.sidebar:
  st.header("📸 Escáner")

  # Pestañas en el sidebar para elegir entre 1 sola foto o un lote completo
  modo_carga = st.radio("Modo de escaneo:", ["Individual", "Carga en Lote"])

  if modo_carga == "Individual":
    archivo = st.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])
    if archivo and st.button("🤖 LEER PLANILLA"):
      with st.spinner("Procesando..."):
        resultado = procesar_planilla_con_ia(archivo)
        if resultado:
          st.session_state.datos_ia = resultado
          st.rerun()
  else:
    archivos_lote = st.file_uploader(
        "Subir múltiples fotos",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True,
    )
    if archivos_lote and st.button("🤖 PROCESAR LOTE"):
      barra_progreso = st.progress(0)
      total_archivos = len(archivos_lote)
      procesados_exito = 0

      for i, archivo_item in enumerate(archivos_lote):
        try:
          imagen_pil = Image.open(archivo_item)
          img_byte_arr = io.BytesIO()
          imagen_pil.save(img_byte_arr, format="JPEG")
          img_bytes = img_byte_arr.getvalue()

          res_json = procesar_bytes_planilla_con_ia(img_bytes)
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
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Analista": cabe_lote.get("analista", "Automático"),
                "Procedencia": cabe_lote.get("procedencia", "N/D"),
                "Placa": cabe_lote.get("placa", "N/D"),
                "Silo": cabe_lote.get("silo", "N/D"),
                "Destino": cabe_lote.get("destino", "N/D"),
                "Contrato": cabe_lote.get("contrato", "N/D"),
                "Documento": cabe_lote.get("documento", "N/D"),
                "Cereal": "Maíz Blanco",
                "Origen": "Nacional",
                **vals_lote,
                "Estatus": "Aprobado",
            }
            st.session_state.historico.append(nuevo_registro)
            procesados_exito += 1
        except Exception:
          pass

        barra_progreso.progress((i + 1) / total_archivos)

      st.success(f"¡Lote procesado! Se añadieron {procesados_exito} registros.")
      st.rerun()

# --- 3. FORMULARIO ---
d = st.session_state.get("datos_ia", {})
cabe = d.get("cabecera", {})
items = d.get("items", {})

with st.form("registro_maestro"):
  st.subheader("📋 Datos del Encabezado")
  c1, c2, c3, c4 = st.columns(4)
  f_fecha = c1.date_input("Fecha", datetime.now())
  f_analista = c2.text_input("Analista", value=cabe.get("analista", ""))
  f_procedencia = c3.text_input(
      "Procedencia", value=cabe.get("procedencia", "")
  )
  f_placa = c4.text_input("Placa", value=cabe.get("placa", ""))

  c5, c6, c7, c8 = st.columns(4)
  f_silo = c5.text_input("Silo", value=cabe.get("silo", ""))
  f_destino = c6.text_input("Destino", value=cabe.get("destino", ""))
  f_contrato = c7.text_input("Contrato", value=cabe.get("contrato", ""))
  f_doc = c8.text_input("Documento", value=cabe.get("documento", ""))

  c9, c10 = st.columns(2)
  f_cereal = c9.selectbox("Cereal", ["Maíz Blanco", "Maíz Amarillo"])
  f_origen = c10.selectbox("Origen", ["Nacional", "Importado"])

  st.subheader("🔬 Resultados de Laboratorio")
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

  f_estatus = st.radio("Estatus:", ["Aprobado", "Rechazado"], horizontal=True)

  submit = st.form_submit_button("✅ REGISTRAR Y GENERAR EXCEL")

  if submit:
    nuevo = {
        "Fecha": f_fecha.strftime("%Y-%m-%d"),
        "Analista": f_analista,
        "Procedencia": f_procedencia,
        "Placa": f_placa,
        "Silo": f_silo,
        "Destino": f_destino,
        "Contrato": f_contrato,
        "Documento": f_doc,
        "Cereal": f_cereal,
        "Origen": f_origen,
        **vals_registro,
        "Estatus": f_estatus,
    }
    st.session_state.historico.append(nuevo)
    st.session_state.datos_ia = {}
    st.rerun()

# --- NUEVA SECCIÓN: REPORTE PARA WHATSAPP ---
st.subheader("📱 Reporte para WhatsApp")

if st.session_state.historico:

  def generar_reporte_profesional(df):
    promedios = df.mean(numeric_only=True)
    reporte = "📋 *REPORTE DIARIO DE RECEPCIÓN*\n"
    reporte += "========================================\n"
    reporte += f"📅 FECHA: {datetime.now().strftime('%d/%m/%Y')}\n"
    reporte += f"🚚 VEHÍCULOS: {len(df)}\n"
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

    reporte += "📊 *RESULTADOS PROMEDIOS:*\n"
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
  st.info("Aún no hay datos para generar el reporte.")

# --- 4. EXCEL Y REPORTE VISUAL ---
if st.session_state.historico:
  st.divider()

  df = pd.DataFrame(st.session_state.historico)
  buffer_xls = io.BytesIO()
  with pd.ExcelWriter(buffer_xls, engine="xlsxwriter") as writer:
    df.to_excel(writer, index=False)
  st.download_button(
      "📥 Descargar Reporte Excel",
      buffer_xls.getvalue(),
      "Reporte.xlsx",
      "application/vnd.ms-excel",
  )

  st.subheader("🖼️ Reporte Visual Profesional")
  if st.button("🎨 Generar Infografía"):
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
  st.info("Aún no hay datos para generar reportes.")
