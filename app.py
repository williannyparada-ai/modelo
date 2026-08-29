from datetime import datetime
import io
import json
import time
from urllib.parse import quote
import google.generativeai as genai
from PIL import Image, ImageOps, ImageDraw, ImageFont
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sistema Provencesa - Control de Calidad",
    layout="wide",
    page_icon="🌾",
)

# --- ESTILOS CSS PERSONALIZADOS (Encabezado y Semáforo Visual) ---
st.markdown(
    """
    <style>
        .stApp {
            background-color: #F4F6F9;
        }

        :root {
            --primary-blue: #00467F;
            --secondary-blue: #0066B3;
            --bg-card: #FFFFFF;
            --text-main: #2C3E50;
            --border-color: #D1D8E0;
        }
        
        .header-corp-card {
            background: var(--bg-card);
            padding: 18px 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 70, 127, 0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 6px solid var(--primary-blue);
            margin-bottom: 25px;
        }
        .header-corp-card h1 {
            color: var(--primary-blue);
            font-size: 30px !important;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.5px;
        }
        .header-corp-brand {
            font-weight: 700;
            color: var(--secondary-blue);
            font-size: 16px;
            background: #E8F1F5;
            padding: 6px 14px;
            border-radius: 8px;
        }

        .section-header {
            font-size: 20px;
            color: var(--primary-blue);
            border-bottom: 2px solid var(--primary-blue);
            padding-bottom: 8px;
            margin-top: 30px;
            margin-bottom: 15px;
            font-weight: 700;
        }

        p, span, label, .stTextInput label, .stNumberInput label {
            font-size: 16px !important;
            color: var(--text-main);
        }

        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
            border: 1px solid var(--border-color);
        }

        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            padding: 0.6rem 1rem;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 70, 127, 0.2);
        }

        .semaforo-box {
            padding: 10px 15px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .semaforo-rojo { background-color: #FADBD8; color: #78281F; border: 1px solid #F5B7B1; }
        .semaforo-amarillo { background-color: #FCF3CF; color: #7D6608; border: 1px solid #F9E79F; }
        .semaforo-verde { background-color: #D4EFDF; color: #145A32; border: 1px solid #A9DFBF; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CABECERA VISUAL CORPORATIVA ---
st.markdown(
    """
    <div class="header-corp-card">
        <h1>🌾 Sistema Provencesa - Control de Calidad</h1>
        <div class="header-corp-brand">EMPRESAS POLAR</div>
    </div>
""",
    unsafe_allow_html=True,
)

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

if "historico" not in st.session_state:
    st.session_state.historico = []
if "datos_ia" not in st.session_state:
    st.session_state.datos_ia = {}
if "lote_procesado_exitoso" not in st.session_state:
    st.session_state.lote_procesado_exitoso = False

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    st.error(f"Error de configuración (Verifica tus secrets.toml): {e}")


def optimizar_imagen_para_ia(imagen_pil):
    try:
        imagen_pil = ImageOps.exif_transpose(imagen_pil)
    except Exception:
        pass
    if imagen_pil.mode != "RGB":
        imagen_pil = imagen_pil.convert("RGB")
    max_ancho = 1200
    if imagen_pil.width > max_ancho:
        proporcion = max_ancho / float(imagen_pil.width)
        nuevo_alto = int(float(imagen_pil.height) * float(proporcion))
        imagen_pil = imagen_pil.resize(
            (max_ancho, nuevo_alto), Image.Resampling.LANCZOS
        )
    return imagen_pil


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


def procesar_bytes_planilla_con_ia(img_bytes):
    try:
        imagen_pil = Image.open(io.BytesIO(img_bytes))
        imagen_pil = optimizar_imagen_para_ia(imagen_pil)

        img_byte_arr = io.BytesIO()
        imagen_pil.save(img_byte_arr, format="JPEG", quality=85)
        img_bytes_limpios = img_byte_arr.getvalue()

        prompt = """Analiza la imagen de esta planilla de laboratorio agroindustrial. La foto fue tomada con un teléfono móvil, por lo que puede tener ligeras sombras o inclinaciones. Extrae la información disponible de los campos de cabecera y los 20 ítems numéricos. 
        Si algún campo numérico no se lee con claridad absoluta, estima el valor más lógico o coloca 0.0. Si un campo de texto no se ve, déjalo como cadena vacía ("").
        
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


def procesar_planilla_con_ia(archivo):
    try:
        img_bytes = archivo.read()
        return procesar_bytes_planilla_con_ia(img_bytes)
    except Exception as e:
        st.error(f"Error técnico procesando la imagen: {e}")
        return None


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

# --- 2. SIDEBAR CON CHECKLIST VISUAL DE ESTADOS ---
with st.sidebar:
    st.header("📸 Escáner por Lotes")

    modo_carga = st.radio("Modo de escaneo:", ["Individual", "Lote de Fotos"])

    if modo_carga == "Individual":
        archivo = st.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])

        if archivo is None:
            st.markdown(
                '<div class="semaforo-box semaforo-rojo">🔴 Estado: Esperando foto (Sube una imagen)</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="semaforo-box semaforo-verde">🟢 Estado: Foto cargada y lista para procesar</div>',
                unsafe_allow_html=True,
            )

        if archivo and st.button("🤖 LEER PLANILLA"):
            st.markdown(
                '<div class="semaforo-box semaforo-amarillo">🟡 Estado: Analizando planilla con IA...</div>',
                unsafe_allow_html=True,
            )
            with st.spinner("Procesando imagen..."):
                resultado = procesar_planilla_con_ia(archivo)
                if resultado:
                    st.session_state.datos_ia = resultado
                    st.success("¡Lectura exitosa!")
                    st.rerun()
    else:
        st.info("Sube tus fotos de golpe. Se procesarán todas de forma continua.")
        
        if "ultimo_conteo_lote" not in st.session_state:
            st.session_state.ultimo_conteo_lote = 0

        archivos_lote = st.file_uploader(
            "Subir fotos de vehículos",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="uploader_lotes",
        )

        if archivos_lote and len(archivos_lote) != st.session_state.ultimo_conteo_lote:
            st.session_state.ultimo_conteo_lote = len(archivos_lote)
            st.session_state.lote_procesado_exitoso = False

        # --- CHECKLIST VISUAL DE PROGRESO ---
        st.markdown("### 📋 Estado del Proceso")
        
        if not archivos_lote:
            st.session_state.ultimo_conteo_lote = 0
            st.markdown("⬜ **1. Fotos cargadas:** Pendiente")
            st.markdown("⬜ **2. Procesamiento IA:** En espera")
            st.markdown("⬜ **3. Resultados listos:** Pendiente")
            st.markdown(
                '<div class="semaforo-box semaforo-rojo" style="margin-top: 10px;">🔴 Esperando lote de fotos</div>',
                unsafe_allow_html=True,
            )
        else:
            total_cargados = len(archivos_lote)
            
            if st.session_state.lote_procesado_exitoso:
                st.markdown(f"✅ **1. Fotos cargadas:** {total_cargados} listas")
                st.markdown("✅ **2. Procesamiento IA:** Finalizado")
                st.markdown("✅ **3. Resultados listos:** Disponibles en reporte")
                st.markdown(
                    f'<div class="semaforo-box semaforo-verde" style="margin-top: 10px;">🟢 ¡Lote procesado con éxito!</div>',
                    unsafe_allow_html=True,
                )
                st.success("Las fotos de este lote ya fueron procesadas y agregadas al reporte general.")
            else:
                st.markdown(f"✅ **1. Fotos cargadas:** {total_cargados} listas")
                st.markdown("🔄 **2. Procesamiento IA:** Listo para iniciar")
                st.markdown("⬜ **3. Resultados listos:** Pendiente")
                st.markdown(
                    f'<div class="semaforo-box semaforo-verde" style="margin-top: 10px;">🟢 {total_cargados} fotos cargadas, listas para procesar</div>',
                    unsafe_allow_html=True,
                )

                if st.button(f"🤖 PROCESAR LAS {total_cargados} FOTOS CARGADAS"):
                    barra_progreso = st.progress(0)
                    total_archivos = len(archivos_lote)
                    procesados_exito = 0

                    st.markdown(
                        '<div class="semaforo-box semaforo-amarillo" style="margin-top: 10px;">🟡 Procesando lote completo con IA...</div>',
                        unsafe_allow_html=True,
                    )

                    for i, archivo_item in enumerate(archivos_lote):
                        try:
                            img_bytes = archivo_item.getvalue()
                            if not img_bytes:
                                continue

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

                            # Pausa obligatoria de 4 segundos para evitar el error 429
                            time.sleep(4)

                        except Exception as ex:
                            if "429" in str(ex) or "ResourceExhausted" in str(ex):
                                st.error("⚠️ Se alcanzó el límite de la API (Error 429). Espera 1 minuto antes de procesar más fotos.")
                            else:
                                st.warning(f"Incidencia en archivo {archivo_item.name}: {ex}")

                        barra_progreso.progress((i + 1) / total_archivos)

                    if procesados_exito > 0:
                        st.session_state.lote_procesado_exitoso = True
                        st.success(f"¡Lote completado! Se procesaron {procesados_exito} de {total_archivos} fotos.")
                        st.rerun()

    st.divider()

    st.subheader("🗑️ Gestión de Jornada")
    if st.button("🧹 Limpiar Registro Actual (Borrar Acumulado)"):
        st.session_state.historico = []
        st.session_state.datos_ia = {}
        st.session_state.lote_procesado_exitoso = False
        st.session_state.ultimo_conteo_lote = 0
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
        ultimo = df.iloc[-1]
        analista = ultimo.get("Analista", "Analista Calidad")
        silo = ultimo.get("Centros Externos", "PROVECESA")
        destino = ultimo.get("Destino", "Planta")

        reporte = f"*{analista}*\n"
        reporte += "Buenos días.\n"
        reporte += f"Despacho:\n"
        reporte += f"Fecha: {datetime.now().strftime('%d/%m/%Y')}\n"
        reporte += f"Silos: {silo}\n"
        reporte += "Material: MBI(12202968)\n"
        reporte += f"Destino: {destino}.\n"

        parametros_formato = [
            ("Humedad", "H", "%"),
            ("Impureza", "Imp", "%"),
            ("Partidos Peq.", "Gpp", "%"),
            ("Germen Dañado", "G.D", "%"),
            ("Dañado Calor", "DC", "%"),
            ("Dañado Insecto", "D Insecto", "%"),
            ("Infectados", "G Infect", "%"),
            ("Total Dañados", "GDT", "%"),
            ("Granos Part.", "GP", "%"),
            ("Cristalizados", "GC", "%"),
            ("Mezcla Color", "M/C", "%"),
            ("Peso Vol", "P.Esp", ""),
            ("Aflatoxina", "Aflatoxina", "PPB"),
            ("Fumonisina", "Fumonisina", "PPM"),
        ]

        for col_df, abreviatura, unidad in parametros_formato:
            valor = promedios.get(col_df, 0.0)
            if unidad == "PPB" or unidad == "PPM":
                reporte += f"⬛ {abreviatura}: {valor:.1f} {unidad}\n"
            elif unidad == "%":
                reporte += f"⬛ {abreviatura}: {valor:.2f}%\n"
            else:
                reporte += f"⬛ {abreviatura}: {valor:.3f}\n"

        aprobados = len(df[df["Estatus"] == "Aprobado"])
        rechazados = len(df[df["Estatus"] == "Rechazado"])
        if aprobados > 0:
            reporte += f"✅ {aprobados} vehículos despachados.\n"
        if rechazados > 0:
            reporte += f"❌ {rechazados} vehículos rechazados.\n"
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
            agrupacion_cols = ["Fecha", "Centros Externos", "Cereal", "Origen"]
            agrupacion_cols = [c for c in agrupacion_cols if c in df.columns]

            if agrupacion_cols:
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
            else:
                df_resumen = df[columnas_numericas].mean().to_frame().T
                df_resumen["N° Vehículos Analizados"] = len(df)
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
