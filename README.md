# Taller RAG Comparativo (Solr vs. Milvus)

Este repositorio contiene el código fuente de un sistema dual de Generación Aumentada por Recuperación (RAG). El proyecto levanta y compara dos *pipelines* de búsqueda:

1.  **Léxico (BM25):** Implementado con **Solr**.
2.  **Vectorial (Semántico):** Implementado con **Milvus** y modelos de *embeddings*.

El sistema expone una única API de FastAPI que puede enrutar una consulta a cualquiera de los dos *backends* para comparar la calidad de la respuesta, la latencia y los documentos recuperados.

## 🏛️ Arquitectura del Sistema

El proyecto está orquestado con `docker-compose` y consiste en los siguientes servicios:

  * `solr`: Instancia de Solr 8.11 que sirve como *backend* léxico.
  * `milvus`: Instancia de Milvus 2.4 (standalone) que sirve como *backend* vectorial.
  * `api`: Servicio de FastAPI (Python) que expone el *endpoint* `POST /ask`. Este servicio carga los modelos de IA (embeddings y LLM generador) y se conecta a ambos *backends*.
  * `indexer`: Un script (servicio de un solo uso) que lee el corpus, lo segmenta (chunking) en pasajes y pobla tanto Solr como Milvus.
  * `attu-gui`: (Opcional) Una interfaz de usuario web para visualizar y gestionar la base de datos vectorial de Milvus.

-----

## 🗂️ Estructura de Carpetas

  * `/data/corpus/`: Contiene los archivos `.txt` del corpus que se van a indexar.
  * `/data/chunks_debug.csv`: (Generado por el indexador) Un CSV para depuración que muestra todos los pasajes (chunks) creados.
  * `/services/api/`: Código fuente de la API de FastAPI (`main.py`) y sus dependencias (`requirements.txt`).
  * `/services/indexer/`: Scripts de indexación (`main_indexer.py`, `index_solr.py`, `index_milvus.py`) que leen el corpus y lo preparan.
  * `/services/milvus/volumes/`: (Generado en local) Mapeo de los volúmenes persistentes de Milvus.
  * `/reports/`: (Vacío) Destinado a los resultados de la Fase 4 (evaluación).
  * `docker-compose.yml`: Archivo principal que define y orquesta todos los servicios.

-----

## 🚀 Guía de Instalación y Ejecución

**Requisitos:**

  * Docker y Docker Compose instalados.

### 1\. Levantar Servicios (Bases de Datos y API)

Este comando construirá las imágenes (la primera vez puede tardar varios minutos en descargar los modelos base y las librerías de Python) y levantará los servicios en modo *detached* (-d).

```bash
docker-compose up --build -d
```

Espera a que los servicios estén listos, especialmente la API. Puedes monitorear la descarga de los modelos de IA (Embeddings y LLM) con:

```bash
docker-compose logs -f api
```

Espera hasta que veas el mensaje: `--- API Lista y Modelos Cargados ---`

### 2\. Ejecutar la Indexación

Una vez que los servicios (`solr`, `milvus` y `api`) estén corriendo, ejecuta el servicio de indexación. Este es un contenedor temporal que se conecta a las bases de datos y las puebla.

```bash
docker-compose run --rm indexer
```

Este script leerá todos los archivos de `/data/corpus/`, los segmentará en pasajes (chunks), y los indexará en Solr y Milvus.

### 3\. Acceder a las Interfaces Gráficas

Puedes verificar que los datos se hayan cargado correctamente accediendo a las interfaces web (asegúrate de que los puertos no estén en conflicto):

  * **Solr (Léxico):**

      * URL: `http://localhost:8983/solr`
      * Usa el "Core Selector" para elegir `taller_rag_core` y haz clic en "Query" para ver los documentos indexados.

  * **Attu (Vectorial):**

      * URL: `http://localhost:8001` (o el puerto que hayas definido para `attu-gui` en tu `docker-compose.yml`)
      * Conéctate a la instancia de Milvus (usualmente `milvus:19530` desde dentro de Docker, o `localhost:19530` si Attu se conecta desde fuera) y explora la colección `taller_rag_corpus`.

### 4\. Probar la API Unificada

La API está lista para recibir consultas en `http://localhost:8000`. Se recomienda usar un cliente como **Insomnia** o **Postman** para manejar correctamente la codificación de caracteres (UTF-8).

**Configuración de la Petición:**

  * **Método:** `POST`
  * **URL:** `http://localhost:8000/ask`
  * **Body:** `JSON`

**Ejemplo de Body (Prueba Léxica):**

```json
{
	"query": "Qué pasó con la Unión Patriótica?",
	"backend": "solr",
	"k": 3
}
```

**Ejemplo de Body (Prueba Semántica):**

```json
{
	"query": "Qué pasó con la Unión Patriótica?",
	"backend": "milvus",
	"k": 3
}
```

**Respuesta Esperada:**
Recibirás un JSON con la respuesta generada por el LLM (en español) y la lista de `source_documents` que se usaron como contexto.

```json
{
  "answer": "El genocidio de la Unión Patriótica fue una...",
  "source_documents": [
    {
      "id": "30-El genocidio de la Uni¢n Patri¢tica.txt_0001",
      "content": "El genocidio de la Unión Patriótica (UP) es uno de los episodios más oscuros...",
      "source_file": "30-El genocidio de la Uni¢n Patri¢tica.txt"
    },
    ...
  ]
}
```