from datetime import datetime
import io
import json
import re
import time
from urllib.parse import quote
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sistema Provencesa - Control de Calidad",
    layout="wide",
    page_icon="🌾",
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown(
    """
    <style>
        .stApp { background-color: #F4F6F9; }
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

# --- CONFIGURACIÓN DE CLIENTE GEMINI ---
client = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        client = genai.Client(api_key=api_key)
    else:
        st.error("No se encontró la clave GOOGLE_API_KEY en secrets.toml")
except Exception as e:
    st.error(f"Error de configuración (Verifica tus secrets.toml): {e}")


def optimizar_imagen_para_ia(imagen_pil):
    try:
        imagen_pil = ImageOps.exif_transpose(imagen_pil)
    except Exception:
        pass
    if imagen_pil.mode != "RGB":
        imagen_pil = imagen_pil.convert("RGB")
    max_ancho = 1000
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
    except Exception:
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
    if not client:
        raise Exception("Cliente de Gemini no inicializado. Revisa API KEY.")

    imagen_pil = Image.open(io.BytesIO(img_bytes))
    imagen_pil = optimizar_imagen_para_ia(imagen_pil)

    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format="JPEG", quality=80)
    img_bytes_limpios = img_byte_arr.getvalue()

    prompt = """Analiza la imagen de la planilla de calidad de Alimentos Polar.
Extrae la información únicamente de los siguientes campos de cabecera:
- placa: PLACA DE VEHÍCULO
- silo: SILO
- contrato: N° DE CONTRATO
- documento: DOCUMENTO
- estado: ESTADO

Extrae los ítems numéricos del 01 al 19 según la tabla.
MUY IMPORTANTE PARA EL ÍTEM 20 (Fumonisina):
La Fumonisina NO está en la tabla numerada, sino escrita a mano en la sección inferior "OBSERVACIONES" (por ejemplo "Fumonisina 1,8 ppm"). Lee el área de OBSERVACIONES, extrae el número de la Fumonisina y asígnalo como valor flotante al ítem "20". Si no hay mención de Fumonisina, asigna 0.0.

Si algún campo no es legible, asigna 0.0 para números o "" para textos."""

    schema = {
        "type": "OBJECT",
        "properties": {
            "cabecera": {
                "type": "OBJECT",
                "properties": {
                    "placa": {"type": "STRING"},
                    "silo": {"type": "STRING"},
                    "contrato": {"type": "STRING"},
                    "documento": {"type": "STRING"},
                    "estado": {"type": "STRING"},
                },
            },
            "items": {
                "type": "OBJECT",
                "properties": {
                    f"{str(i).zfill(2)}": {"type": "NUMBER"}
                    for i in range(1, 21)
                },
            },
        },
    }

    # Modelos actualizados y estables (se eliminó el sufijo -latest obsoleto)
    modelos_a_probar = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    ultimo_error = None

    for model_name in modelos_a_probar:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=img_bytes_limpios, mime_type="image/jpeg"
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            ultimo_error = e
            continue

    if ultimo_error:
        raise ultimo_error


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
                df_hist["Aflatoxina"],
                color="#FFA07A",
                use_container_width=True,
            )
        with c2:
            st.caption("Tendencia de Granos Dañados Totales (GDT)")
            st.line_chart(
                df_hist["Total Dañados"],
                color="#90EE90",
                use_container_width=True,
            )
            st.caption("Tendencia de Fumonisina (PPM)")
            st.line_chart(
                df_hist["Fumonisina"],
                color="#BA55D3",
                use_container_width=True,
            )

    st.divider()

# --- 2. SIDEBAR CON CHECKLIST VISUAL DE ESTADOS ---
with st.sidebar:
    st.header("📸 Escáner por Lotes")

    st.subheader("⚙️ Parámetros Fijos Manuales")
    procedencia_lote = st.text_input("Procedencia (Lotes)", value="Silos Xeax")
    destino_lote = st.text_input("Destino (Lotes)", value="APC Chivacoa")
    analista_lote = st.text_input("Analista (Lotes)", value="Terry Silva")

    st.divider()
    modo_carga = st.radio("Modo de escaneo:", ["Individual", "Lote de Fotos"])

    if modo_carga == "Individual":
        archivo = st.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])

        if archivo is None:
            st.markdown(
                '<div class="semaforo-box semaforo-rojo">🔴 Estado: Esperando foto</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="semaforo-box semaforo-verde">🟢 Estado: Foto cargada</div>',
                unsafe_allow_html=True,
            )

        if archivo and st.button("🤖 LEER PLANILLA"):
            st.markdown(
                '<div class="semaforo-box semaforo-amarillo">🟡 Analizando con IA...</div>',
                unsafe_allow_html=True,
            )
            with st.spinner("Procesando imagen..."):
                resultado = procesar_planilla_con_ia(archivo)
                if resultado:
                    st.session_state.datos_ia = resultado
                    st.success("¡Lectura exitosa!")
                    st.rerun()
    else:
        st.info("Sube tus fotos en lote.")

        if "ultimo_conteo_lote" not in st.session_state:
            st.session_state.ultimo_conteo_lote = 0

        archivos_lote = st.file_uploader(
            "Subir fotos de vehículos",
            type=["jpg", "png", "jpeg"],
            accept_multiple_files=True,
            key="uploader_lotes",
        )

        if (
            archivos_lote
            and len(archivos_lote) != st.session_state.ultimo_conteo_lote
        ):
            st.session_state.ultimo_conteo_lote = len(archivos_lote)
            st.session_state.lote_procesado_exitoso = False

        st.markdown("### 📋 Estado del Proceso")

        if not archivos_lote:
            st.session_state.ultimo_conteo_lote = 0
            st.markdown("⬜ **1. Fotos cargadas:** Pendiente")
            st.markdown("⬜ **2. Procesamiento IA:** En espera")
            st.markdown("⬜ **3. Resultados listos:** Pendiente")
            st.markdown(
                '<div class="semaforo-box semaforo-rojo">🔴 Esperando lote de fotos</div>',
                unsafe_allow_html=True,
            )
        else:
            total_cargados = len(archivos_lote)

            if st.session_state.lote_procesado_exitoso:
                st.markdown(f"✅ **1. Fotos cargadas:** {total_cargados} listas")
                st.markdown("✅ **2. Procesamiento IA:** Finalizado")
                st.markdown("✅ **3. Resultados listos:** Disponibles")
                st.markdown(
                    '<div class="semaforo-box semaforo-verde">🟢 ¡Lote procesado!</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"✅ **1. Fotos cargadas:** {total_cargados} listas")
                st.markdown("🔄 **2. Procesamiento IA:** Listo para iniciar")
                st.markdown("⬜ **3. Resultados listos:** Pendiente")

                if st.button(
                    f"🤖 PROCESAR LAS {total_cargados} FOTOS CARGADAS",
                    key="btn_procesar_lote",
                ):
                    procesados_exito = 0
                    errores_lote = []

                    with st.spinner(
                        f"Analizando {total_cargados} planillas con la IA de Gemini..."
                    ):
                        estado_texto = st.empty()
                        barra_progreso = st.progress(0)

                        for i, archivo_item in enumerate(archivos_lote):
                            nombre_f = archivo_item.name
                            estado_texto.text(
                                f"Procesando foto {i+1} de {total_cargados}: {nombre_f}..."
                            )

                            try:
                                img_bytes = archivo_item.getvalue()
                                if not img_bytes:
                                    errores_lote.append(
                                        f"{nombre_f}: Imagen vacía"
                                    )
                                    continue

                                res_json = procesar_bytes_planilla_con_ia(
                                    img_bytes
                                )

                                if res_json:
                                    cabe_lote = res_json.get("cabecera", {})
                                    items_lote = res_json.get("items", {})

                                    vals_lote = {}
                                    for idx_item in range(20):
                                        k_str = str(idx_item + 1).zfill(2)
                                        try:
                                            val_L = float(
                                                items_lote.get(k_str, 0.0)
                                            )
                                        except Exception:
                                            val_L = 0.0
                                        vals_lote[nombres_items[idx_item]] = (
                                            val_L
                                        )

                                    nuevo_registro = {
                                        "Estado": cabe_lote.get("estado", ""),
                                        "Fecha": datetime.now().strftime(
                                            "%Y-%m-%d"
                                        ),
                                        "Contrato": cabe_lote.get(
                                            "contrato", "0"
                                        ),
                                        "Maíz": "MBI",
                                        "COD MAIZ SAP": "MBI(12202968)",
                                        "N° Vehículos Analizados": 1,
                                        "Centros Externos": procedencia_lote,
                                        "Destino": destino_lote,
                                        "Analista": analista_lote,
                                        "Placa": cabe_lote.get("placa", "N/D"),
                                        "Silo": cabe_lote.get("silo", "N/D"),
                                        "Documento": cabe_lote.get(
                                            "documento", "N/D"
                                        ),
                                        "Cereal": "Maíz Blanco",
                                        "Origen": "Nacional",
                                        **vals_lote,
                                        "Estatus": "Aprobado",
                                    }
                                    st.session_state.historico.append(
                                        nuevo_registro
                                    )
                                    procesados_exito += 1
                                else:
                                    errores_lote.append(
                                        f"{nombre_f}: No devolvió respuesta válida de IA"
                                    )

                            except Exception as ex:
                                errores_lote.append(f"{nombre_f}: {str(ex)}")

                            time.sleep(0.1)
                            barra_progreso.progress(
                                int(((i + 1) / total_cargados) * 100)
                            )

                    if procesados_exito > 0:
                        st.session_state.lote_procesado_exitoso = True
                        st.sidebar.success(
                            f"¡Lote completado! {procesados_exito} fotos procesadas."
                        )
                        if errores_lote:
                            for err in errores_lote:
                                st.sidebar.warning(f"⚠️ {err}")
                        st.rerun()
                    else:
                        st.sidebar.error("No se pudo procesar ninguna foto.")
                        if errores_lote:
                            for err in errores_lote:
                                st.sidebar.error(f"❌ {err}")

    st.divider()
    st.subheader("🗑️ Gestión de Jornada")
    if st.button("🧹 Limpiar Registro Actual"):
        st.session_state.historico = []
        st.session_state.datos_ia = {}
        st.session_state.lote_procesado_exitoso = False
        st.session_state.ultimo_conteo_lote = 0
        st.success("¡Registro limpiado!")
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
    f_procedencia = c1.text_input("Procedencia", value="Silos Xeax")
    f_destino = c2.text_input("Destino", value="APC Chivacoa")
    f_estado = c3.text_input("Estado", value=cabe.get("estado", ""))
    f_fecha = c4.date_input("Fecha", datetime.now())

    c5, c6, c7, c8 = st.columns(4)
    f_contrato = c5.text_input("N° de Contrato", value=cabe.get("contrato", ""))
    f_placa = c6.text_input("Placa de Vehículo", value=cabe.get("placa", ""))
    f_silo = c7.text_input("Silo", value=cabe.get("silo", ""))
    f_doc = c8.text_input("Documento", value=cabe.get("documento", ""))

    f_analista = st.text_input("Analista de Calidad", value="Terry Silva")

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
            "Destino": f_destino,
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
        silo = ultimo.get("Centros Externos", "PROVENESA")
        destino = ultimo.get("Destino", "Planta")

        reporte = f"*{analista}*\n"
        reporte += "Buenos días.\n"
        reporte += "Despacho:\n"
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
            if unidad in ["PPB", "PPM"]:
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
            columnas_numericas = [
                col for col in nombres_items if col in df.columns
            ]
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
            df_resumen.to_excel(
                writer, sheet_name="Resumen por Día", index=False
            )

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
