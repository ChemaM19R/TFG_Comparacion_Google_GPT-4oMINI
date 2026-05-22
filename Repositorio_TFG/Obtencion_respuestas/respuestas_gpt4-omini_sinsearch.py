from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import pandas as pd

#is not working

def openai_login():
    load_dotenv("exampe_apis.env")
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    return client

# Configura la API key directamente en la llamada
client = openai_login()

# Definimos la estructura esperada del array
class LinkItem(BaseModel):
    name: str
    url: str

# El modelo debe devolver una lista de esos objetos
class LinksResponse(BaseModel):
    links: List[LinkItem]

 
def consultar_openai(texto_consulta: str) -> LinksResponse | None:
    try:
        response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {
            "role": "user",
            "content": [{"type": "input_text", "text": texto_consulta}]
            } 
        ],
        reasoning={},
        tools=[],
        temperature=0,
        max_output_tokens=2048,
        top_p=1,
        store=True,
        text_format=LinksResponse,  # El modelo debe ajustarse a este formato)
        )
        return response.output_parsed
    except Exception as e:
        print(f"⚠️ Error al procesar consulta: {texto_consulta}")
        return None


archivo_entrada = "Copia de preguntas_locales_espana.xlsx"
archivo_salida = "200preguntas_locales_espana(gptsinsearch).xlsx"

df = pd.read_excel(archivo_entrada)

if "respuesta" not in df.columns:
    df["respuesta"] = ""

if os.path.exists(archivo_salida):
    try:
        df_guardado = pd.read_excel(archivo_salida)
        if "respuesta" in df_guardado.columns:
            filas_a_copiar = min(len(df), len(df_guardado))
            for i in range(filas_a_copiar):
                valor_guardado = df_guardado.at[i, "respuesta"]
                if pd.notna(valor_guardado) and str(valor_guardado).strip() != "":
                    df.at[i, "respuesta"] = valor_guardado
    except Exception as e:
        print(f"⚠️ No se pudo cargar el archivo de salida previo: {e}")

for idx, consulta in enumerate(df["Pregunta"]):
    if pd.notna(df.at[idx, "respuesta"]) and str(df.at[idx, "respuesta"]).strip() != "":
        print(f"Saltando fila {idx}: ya tiene respuesta guardada")
        continue

    print(f"Procesando fila {idx}: {consulta}")
    resultado = consultar_openai(consulta)
    if resultado is not None:
        df.at[idx, "respuesta"] = resultado
    else:
        df.at[idx, "respuesta"] = ""

    df.to_excel(archivo_salida, index=False)
    print(f"Guardado incremental en fila {idx}")

print(f"Archivo guardado: {archivo_salida}")