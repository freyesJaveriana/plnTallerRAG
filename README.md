# Taller RAG Comparativo (Solr vs. Milvus)
Docente: **Luis Gabriel Moreno Sandoval**

---
*Grupo Número 1:*

- LUCENA ORJUELA, JULIAN
- MARTINEZ BERMUDEZ, JUAN
- MONTENEGRO MAFLA, MARIA
- REYES PALACIO, FELIPE 


Este repositorio contiene el código fuente de un sistema dual de Generación Aumentada por Recuperación (RAG) diseñado para una evaluación de rendimiento avanzada. El proyecto compara dos *pipelines* de búsqueda fundamentalmente diferentes sobre el mismo corpus:

1.  **Léxico + Semántica Manual:** Implementado con **Solr 8.11**, mejorado con el **Tesauro CEV** (`resource-tesauro.rdf`) que se carga dinámicamente en el esquema.
2.  **Semántica de IA:** Implementado con **Milvus 2.4**, utilizando *embeddings* de alta calidad (`text-embedding-004` de Google, 768 dimensiones).

El sistema expone una única API de FastAPI que utiliza el modelo **Gemini (Google)** para la generación de respuestas y está configurada para medir por separado la latencia de recuperación y la latencia total.

## 🏛️ Arquitectura del Sistema

El proyecto está orquestado con `docker-compose` y consiste en los siguientes servicios:

  * `solr`: Instancia de Solr 8.11 que sirve como *backend* léxico.
  * `milvus`: Instancia de Milvus 2.4 (standalone) configurada para vectores de 768 dimensiones.
  * `api`: Servicio de FastAPI (Python) que expone el *endpoint* `POST /ask`. Utiliza la API de Google (`Gemini` para generación, `text-embedding-004` para consultas).
  * `indexer`: Un script (servicio de un solo uso) que lee el corpus, lo segmenta (5 oraciones, 2 de superposición), y pobla ambos *backends* (Solr+Tesauro y Milvus+Google Embeddings).
  * `evaluator`: Un script de evaluación (servicio de un solo uso) que ejecuta el `gold_standard.json` contra la API para generar el `evaluation_results.csv`.
  * `attu-gui`: Interfaz de usuario web para visualizar la base de datos vectorial de Milvus.

## 🗂️ Estructura de Carpetas

  * `/.env`: **(¡Archivo crítico, debe ser creado\!)** Contiene la `GOOGLE_API_KEY` necesaria.
  * `/data/corpus/`: Contiene los archivos `.txt` del corpus.
  * `/data/resource-tesauro.rdf`: El tesauro de semántica manual para Solr.
  * `/services/api/`: Código fuente de la API de FastAPI (`main.py`).
  * `/services/indexer/`: Scripts de indexación (`main_indexer.py`, `index_solr.py`, `index_milvus.py`, `parse_tesauro.py`).
  * `/services/evaluator/`: Script de evaluación (`evaluate.py`) y sus dependencias.
  * `/reports/`: Contiene el `gold_standard_conceptual.json` (entrada) y genera el `evaluation_results.csv` (salida).
  * `docker-compose.yml`: Archivo principal que orquesta todos los servicios.

-----

## 🚀 Guía de Instalación y Ejecución

**Requisitos:**

  * Docker y Docker Compose.
  * Una **Clave de API de Google** (para Gemini y los Embeddings).

### Paso 1: Configuración de la Clave de API (Obligatorio)

En la carpeta raíz del proyecto (junto a `docker-compose.yml`), crea un archivo llamado `.env` y añade tu clave:

```ini
# Archivo: .env
GOOGLE_API_KEY=tu_clave_de_api_aqui
```

Esta clave es utilizada por los servicios `api`, `indexer` y `evaluator`.

### Paso 2: Iniciar Servicios y Reconstruir Imágenes

Este comando construirá las imágenes con todas las dependencias (`google-generativeai`, `rdflib`, `tabulate`, `rouge-score`, etc.) e iniciará los servicios de base de datos (`solr`, `milvus`, `attu`).

```bash
docker-compose up -d --build
```

*(Nota: El volumen `huggingface_cache` se usará para los modelos de embeddings `MiniLM` si se usan, pero nuestra configuración final usa la API de Google).*

### Paso 3: Ejecutar la Indexación

Este comando ejecuta el `indexer`. El script esperará a que `solr` y `milvus` estén *healthy* antes de ejecutarse.

```bash
docker-compose run --rm indexer
```

Este script (si no está comentado) realizará dos acciones:

1.  **En Solr:** Cargará los 186 sinónimos del Tesauro en el esquema, borrará el índice y re-indexará los *chunks* de 5 oraciones.
2.  **En Milvus:** Creará la colección de 768 dimensiones y generará los *embeddings* usando la API de Google (`text-embedding-004`).

### Paso 4: Acceder a las Interfaces Gráficas

Puedes verificar que los datos se hayan cargado correctamente:

  * **Solr (Léxico + Tesauro):** `http://localhost:8983/solr` (Busca el núcleo `taller_rag_core`).
  * **Attu (Vectorial):** `http://localhost:8001` (Conéctate a `milvus-standalone:19530` y explora `taller_rag_corpus`).

### Paso 5: Ejecutar la Evaluación

Este comando ejecuta el `evaluator`. Esperará a que el servicio `api` pase su *healthcheck* (es decir, que la API de Gemini esté cargada) antes de enviar las 216 solicitudes.

*(Asegúrate de que tu Gold Standard conceptual esté en `/reports/gold_standard.json`).*

```bash
docker-compose run --rm evaluator
```

Al finalizar, se creará el archivo `/reports/evaluation_results.csv`.

### Paso 6: Analizar Resultados

Usa el *notebook* (`ComparativoModelos.ipynb`) para cargar el `evaluation_results.csv`. El *notebook* está configurado para:

1.  Filtrar cualquier error de generación (`Error al generar la respuesta...`).
2.  Calcular las métricas promedio (Recall, MRR, ROUGE-L, y ambas latencias).
3.  Generar los gráficos de barras y diagramas de caja para el informe final.

### Paso 7: Probar la API Manualmente (Opcional)

Puedes usar Insomnia o Postman para probar la API en `http://localhost:8000/ask`.

**Ejemplo de Body (Prueba Semántica Conceptual):**

```json
{
	"query": "¿Qué componente de la tríada de paz de Betancur resultó incompleto?",
	"backend": "milvus",
	"k": 3
}
```

**Respuesta Esperada:**

```json
{
  "answer": "El componente de la tríada de paz de Betancur que resultó incompleto fue el de la reforma política y social...",
  "source_documents": [
    {
      "id": "26-®Los enemigos agazapados de la paz¯.txt_0000",
      "content": "La tríada de la paz de Betancur -diálogo, reforma y apertura- estaba incompleta...",
      "source_file": "26-®Los enemigos agazapados de la paz¯.txt"
    }
  ],
  "retrieval_latency_sec": 0.0041
}
```