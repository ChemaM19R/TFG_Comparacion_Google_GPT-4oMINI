"""
Script para procesar preguntas con OpenAI Batch API
Reformula preguntas para que sean más naturales y correctas en español
"""

import json
import time
from openai import OpenAI
from dotenv import load_dotenv
import os
# Inicializar el cliente de OpenAI
# Asegúrate de tener tu API key en la variable de entorno OPENAI_API_KEY
def openai_login():
    load_dotenv("exampe_apis.env")
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    return client

# Configura la API key directamente en la llamada
client = openai_login()

# ============================================================================
# PASO 1: Subir el archivo JSONL a OpenAI
# ============================================================================

print("📤 Subiendo archivo JSONL a OpenAI...")

batch_input_file = client.files.create(
    file=open("batch_reformulacion_10000.jsonl", "rb"),
    purpose="batch"
)

file_id = batch_input_file.id
print(f"✅ Archivo subido exitosamente. File ID: {file_id}")

# ============================================================================
# PASO 2: Crear el trabajo de batch
# ============================================================================

print("\n🚀 Creando trabajo de batch...")

batch_job = client.batches.create(
    input_file_id=file_id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
    metadata={
        "description": "Reformulación de 10,000 preguntas locales en español"
    }
)

batch_id = batch_job.id
print(f" Batch creado exitosamente. Batch ID: {batch_id}")
print(f"   Estado inicial: {batch_job.status}")

# ============================================================================
# PASO 3: Monitorear el estado del batch
# ============================================================================

print("\n⏳ Monitoreando el progreso del batch...")
print("   (Esto puede tomar varias horas para 10,000 preguntas)")

status = batch_job.status
while status not in ["completed", "failed", "cancelled", "expired"]:
    time.sleep(60)  # Esperar 1 minuto entre consultas
    batch_job = client.batches.retrieve(batch_id)
    status = batch_job.status

    # Mostrar progreso si está disponible
    if hasattr(batch_job, 'request_counts'):
        counts = batch_job.request_counts
        total = counts.total
        completed = counts.completed
        failed = counts.failed
        print(f"   Estado: {status} | Completadas: {completed}/{total} | Fallidas: {failed}")
    else:
        print(f"   Estado: {status}")

# ============================================================================
# PASO 4: Descargar los resultados
# ============================================================================

if status == "completed":
    print("\n Batch completado exitosamente!")
    print("\n Descargando resultados...")

    output_file_id = batch_job.output_file_id

    # Descargar el contenido del archivo de resultados
    file_response = client.files.content(output_file_id)

    # Guardar los resultados
    with open("batch_resultados_10000.jsonl", "wb") as f:
        f.write(file_response.content)

    print(" Resultados guardados en 'batch_resultados_10000.jsonl'")

    # ============================================================================
    # PASO 5: Procesar los resultados y crear un CSV
    # ============================================================================

    print("\n Procesando resultados y creando CSV...")

    import pandas as pd

    # Leer el dataset original
    df_original = pd.read_excel('Dataset_Local_Spain_10000_preguntas.xlsx')

    # Leer los resultados del batch
    resultados = []
    with open("batch_resultados_10000.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            resultados.append(json.loads(line))

    # Extraer las preguntas reformuladas
    preguntas_reformuladas = {}
    for resultado in resultados:
        custom_id = resultado['custom_id']
        idx = int(custom_id.split('-')[1])

        if resultado['response']['status_code'] == 200:
            contenido = resultado['response']['body']['choices'][0]['message']['content']
            preguntas_reformuladas[idx] = contenido
        else:
            preguntas_reformuladas[idx] = "ERROR"

    # Agregar la columna de preguntas reformuladas
    df_original['Pregunta_Reformulada'] = df_original.index.map(
        lambda x: preguntas_reformuladas.get(x, "NO PROCESADA")
    )

    # Guardar el resultado final
    df_original.to_excel('Dataset_Local_Spain_10000_reformulado.xlsx', index=False)
    df_original.to_csv('Dataset_Local_Spain_10000_reformulado.csv', index=False, encoding='utf-8')

    print(" Dataset reformulado guardado en:")
    print("   - Dataset_Local_Spain_10000_reformulado.xlsx")
    print("   - Dataset_Local_Spain_10000_reformulado.csv")

    # Mostrar estadísticas
    print("\n Estadísticas:")
    print(f"   Total de preguntas: {len(df_original)}")
    print(f"   Reformuladas exitosamente: {sum(1 for v in preguntas_reformuladas.values() if v != 'ERROR')}")
    print(f"   Errores: {sum(1 for v in preguntas_reformuladas.values() if v == 'ERROR')}")

    # Mostrar algunos ejemplos
    print("\n Ejemplos de reformulaciones:")
    for i in range(min(5, len(df_original))):
        print(f"\n   Original: {df_original.loc[i, 'Pregunta']}")
        print(f"   Reformulada: {df_original.loc[i, 'Pregunta_Reformulada']}")

elif status == "failed":
    print("\n El batch falló. Revisa los errores:")
    if hasattr(batch_job, 'errors'):
        for error in batch_job.errors.data:
            print(f"   - {error}")

else:
    print(f"\n El batch terminó con estado: {status}")

print("\n Proceso completado!")
