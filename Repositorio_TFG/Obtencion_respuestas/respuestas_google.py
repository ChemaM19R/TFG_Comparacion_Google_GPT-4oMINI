import pandas as pd
import requests
import time
import json
import os
import base64

OUTPUT_CSV = "200_preguntas_dataforseo.csv"
OUTPUT_JSON = "200_preguntas_dataforseo.json"
PROCESSED_QUERIES_FILE = "consultas_procesadas_200_preguntas_dataforseo.json"

LOGIN = ""
PASSWORD = ""

auth = base64.b64encode(f"{LOGIN}:{PASSWORD}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}

URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

def fetch_google_results(query):
    payload = [{
        "keyword": query,
        "language_code": "es",
        "location_code": 2724,  # España
        "device": "desktop",
        "depth": 10
    }]

    response = requests.post(URL, headers=HEADERS, json=payload)
    response.raise_for_status()  # Lanzar excepción si hay error HTTP
    
    data = response.json()
    
    task = data["tasks"][0]
    items = task["result"][0]["items"]

    organic_links = [
        {
            "rank": item.get("rank_group", ""),
            "title": item.get("title", ""),
            "url": item.get("url", "")
        }
        for item in items
        if item.get("type") == "organic"
    ]
    

    return organic_links, data

def cargar_consultas_procesadas():
    if os.path.exists(PROCESSED_QUERIES_FILE):
        try:
            with open(PROCESSED_QUERIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_consultas_procesadas(procesadas):
    with open(PROCESSED_QUERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(procesadas, f, ensure_ascii=False, indent=2)

def guardar_resultado_inmediato(resultado, es_exitosa=False):
    # Cargar resultados existentes
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            resultados_json = json.load(f)
    else:
        resultados_json = []
    
    # Buscar si ya existe una entrada para esta consulta
    query = resultado["query"]
    indice_anterior = None
    
    for i, res in enumerate(resultados_json):
        if res["query"] == query:
            indice_anterior = i
            break
    
    # Actualizar o agregar
    if indice_anterior is not None:
        # Si encontramos una entrada anterior, la actualizamos siempre
        resultados_json[indice_anterior] = resultado
        print(f"---Actualizando entrada anterior para: {query}")
    else:
        # Si no existe, la agregamos
        resultados_json.append(resultado)
    
    # Guardar JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados_json, f, ensure_ascii=False, indent=2)
    
    # Guardar CSV (reconstruir desde JSON para mantener consistencia)
    df_resultado = pd.DataFrame(resultados_json)
    df_resultado.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")



df = pd.read_excel("Copia de preguntas_locales_espana.xlsx")


consultas_procesadas = cargar_consultas_procesadas()

for idx, row in df.iterrows():
    query = row["Pregunta"]
    
    if query in consultas_procesadas:
        print(f"Saltando consulta {idx + 1}/{len(df)} (ya procesada): {query}")
        continue
    
    print(f"Procesando consulta {idx + 1}/{len(df)}: {query}")

    consulta_exitosa = False
    try:
        # Llamar a la función de DataForSEO
        organic_links, raw_response = fetch_google_results(query)

        resultado = {
            "query": query,
            "response": json.dumps(organic_links, ensure_ascii=False)
        }

        backup_resultado = {
            "query": query,
            "raw_response": raw_response
        }

        consulta_exitosa = True

    except Exception as e:
        print(f"Error para '{query}': {e}")
        resultado = {
            "query": query,
            "response": None,
            "error": str(e)
        }

        backup_resultado = {
            "query": query,
            "raw_response": None,
            "error": str(e)
        }

    guardar_resultado_inmediato(resultado, consulta_exitosa)
   
    # Solo marcar como procesada si fue exitosa
    if consulta_exitosa:
        consultas_procesadas.append(query)
        guardar_consultas_procesadas(consultas_procesadas)
    else:
        print(f"---Consulta con error, se volverá a intentar en la próxima ejecución")
    time.sleep(1)

print("Proceso terminado")
