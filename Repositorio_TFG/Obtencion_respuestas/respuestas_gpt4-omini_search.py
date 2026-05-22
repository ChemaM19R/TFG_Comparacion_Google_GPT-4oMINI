from openai import OpenAI
import os
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
                    "content": [
                        {"type": "input_text", "text": texto_consulta}
                    ]
                }
            ],
            reasoning={},
            tools=[
                {
                    "type": "web_search",
                    "user_location": {
                        "type": "approximate",
                        "country": "ES",
                        "region": "España",
                        "city": "España"
                    },
                    "search_context_size": "medium"
                }
            ],
            temperature=1,
            max_output_tokens=2048,
            top_p=1,
            store=True,
            include=["web_search_call.action.sources"],
            text_format=LinksResponse,  # Aquí puede fallar Pydantic
        )
        return response.output_parsed
    except Exception as e:
        print(f"⚠️ Error al procesar consulta: {texto_consulta}")
        return None


archivo_entrada = "Copia de preguntas_locales_espana.xlsx"
archivo_salida = "200preguntas_locales_espana(gptsearch).xlsx"

df = pd.read_excel(archivo_entrada)

respuestas = []

for idx, consulta in enumerate(df["Pregunta"]):
    print(f"Procesando fila {idx}: {consulta}")
    resultado = consultar_openai(consulta)
    respuestas.append(resultado)

# -----------------------------
# Guardar resultados
# -----------------------------
df["respuesta"] = respuestas
df.to_excel(archivo_salida, index=False)

print(f"Archivo guardado: {archivo_salida}")