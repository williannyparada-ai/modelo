import io  # Necesitamos esto para manejar los bytes de la imagen

def procesar_planilla_con_ia(imagen_pil):
    # 1. Preparamos la imagen para la IA (Convertirla a bytes)
    img_byte_arr = io.BytesIO()
    imagen_pil.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()

    # 2. Creamos la estructura que Google exige
    imagen_para_ia = {
        "mime_type": "image/jpeg",
        "data": img_bytes
    }

    # 3. El Prompt "Maestro" para que no se equivoque con los decimales
    prompt = """
    Analiza esta planilla de Alimentos Polar. 
    1. Identifica la cabecera: Procedencia, Placa, Silo, Analista.
    2. Lee los 20 ítems técnicos. IMPORTANTE: Los números están escritos a mano, usa comas para decimales (ej. 12,10).
    3. Devuelve los datos en este formato JSON exacto:
    {
      "cabecera": {"analista": "Nombre", "procedencia": "Lugar", "placa": "ABC123", "silo": "04"},
      "items": {"01": 12.10, "02": 0.49, "03": 1.80, ... hasta el 20}
    }
    Devuelve SOLO el JSON, sin texto adicional.
    """

    # 4. Llamada a la IA
    response = model.generate_content([prompt, imagen_para_ia])
    
    # Limpiamos la respuesta para obtener solo el JSON
    texto_limpio = response.text.replace('```json', '').replace('
```', '').strip()
    return json.loads(texto_limpio)
