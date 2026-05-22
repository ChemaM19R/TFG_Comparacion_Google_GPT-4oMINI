# DISEÑO DE UNA HERRAMIENTA PARA EL ANÁLISIS COMPARATIVO DE LA BÚSQUEDA DE INFORMACIÓN ENTRE MODELOS DE LENGUAJE Y BUSCADORES TRADICIONALES EN ESPAÑA

**Trabajo Fin de Grado — ETSIT-UPM · Curso 2025–2026**  
---

## Descripción

Este TFG analiza y compara empíricamente el comportamiento de tres sistemas de recuperación de información ante un conjunto de 10.000 consultas locales en español centradas en el mercado español, complementado con un subconjunto de 200 consultas de alta popularidad. Los sistemas evaluados son Google Search (vía API de DataForSEO), GPT-4o mini con búsqueda web activada y GPT-4o mini sin acceso a Internet (ambos vía API de OpenAI). La comparativa se centra en el solapamiento de URLs y dominios, el orden de los resultados y el perfil cualitativo de las fuentes priorizadas por cada sistema. Como parte del trabajo se ha desarrollado además una herramienta web interactiva que permite a cualquier usuario realizar comparativas en tiempo real entre los tres sistemas introduciendo una consulta en lenguaje natural.

---

## Estructura del repositorio

```
├── Analisis/                         # Notebooks de análisis comparativo
├── Datasets/
│   ├── 10000_consultas/              # Pool principal de consultas y resultados
│   │   └── Reformulacion/            # Scripts y ficheros del proceso de reformulación
│   └── 200_consultas_populares/      # Subconjunto de consultas populares y resultados
├── Herramienta_web/                  # Backend (Flask) y frontend de la herramienta
└── Obtencion_respuestas/             # Scripts de obtención de resultados de cada API
```
