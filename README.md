# Taller RAG Comparativo (Solr vs. Milvus)

Este repositorio contiene el código para el taller de RAG, comparando un pipeline léxico (Solr + BM25) con uno vectorial (Milvus + Embeddings).

## Estructura

- **/data/corpus/**: (Vacío) Coloca aquí tus archivos de corpus (CSV, TXT, Parquet, etc.).
- **/services/api/**: Código de la API de FastAPI que sirve el endpoint `/ask`.
- **/services/indexer/**: Scripts para poblar Solr y Milvus desde el corpus.
- **/services/solr/**: (Vacío) Docker usa esta carpeta para configuraciones de Solr si es necesario.
- **/services/milvus/**: (Vacío) Docker usa esta carpeta para configuraciones de Milvus si es necesario.
- **/reports/**: (Vacío) Aquí irán los resultados de la evaluación (Fase 4).
- `docker-compose.yml`: Archivo principal que define y orquesta todos los servicios.

## Cómo Empezar

**Requisitos:**
- Docker y Docker Compose instalados.
- Un corpus en `/data/corpus/`.

### 1. Levantar los Servicios

Construye y levanta todos los contenedores (Solr, Milvus, API) en modo 'detached' (-d).

```bash
docker-compose up --build -d
````

Puedes verificar que todo esté corriendo con:

```bash
docker-compose ps
```

Deberías ver 3 servicios corriendo: `api`, `milvus`, y `solr`.

### 2\. Ejecutar la Indexación

Una vez que los servicios estén saludables (puede tomar 1-2 minutos para que Milvus y Solr inicien), puedes ejecutar el servicio `indexer`.

Este comando inicia un *nuevo* contenedor temporal usando la definición de `indexer` del `docker-compose.yml`, ejecuta el `main_indexer.py`, y luego se detiene.

```bash
docker-compose run --rm indexer
```

*(Deberás implementar la lógica en `index_solr.py` y `index_milvus.py` para que esto haga algo útil)*

### 3\. Probar la API

La API estará disponible en `http://localhost:8000`.

Puedes probar el endpoint (después de implementar la lógica) con `curl` o Postman:

```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{
           "query": "Tu pregunta aquí",
           "backend": "solr",
           "k": 3
         }'
```