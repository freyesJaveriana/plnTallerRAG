import os
import time
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# --- Conectores de Bases de Datos ---
import pysolr
from pymilvus import connections, Collection

# --- Stack de IA (Embeddings y Generador) ---
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# --- Variables de Entorno (leídas desde docker-compose.yml) ---
SOLR_HOST = os.getenv("SOLR_HOST", "localhost")
SOLR_PORT = os.getenv("SOLR_PORT", "8983")
SOLR_CORE = os.getenv("SOLR_CORE", "taller_rag_core")
SOLR_URL = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/{SOLR_CORE}"

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_ALIAS = "default"

# --- Constantes del Modelo ---
# Mismo modelo de embeddings usado en la indexación [cite: 42, 43, 156]
EMBEDDING_MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
# Un modelo generador (LLM) Seq2Seq pequeño pero capaz
LLM_NAME = 'google/flan-t5-base'

# Constantes de la colección de Milvus (deben coincidir con index_milvus.py)
COLLECTION_NAME = "taller_rag_corpus"
TEXT_FIELD_NAME = "text_content"
VECTOR_FIELD_NAME = "vector_embedding"

# Diccionario global para almacenar los modelos cargados
models = {}

# --- Context Manager "Lifespan" ---
# Carga los modelos pesados (IA) una sola vez al iniciar la API 
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando API...")
    print(f"Cargando modelo de embeddings: {EMBEDDING_MODEL_NAME}")
    models["embedding_model"] = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    print(f"Cargando modelo generador (LLM): {LLM_NAME}")
    models["llm_tokenizer"] = AutoTokenizer.from_pretrained(LLM_NAME)
    models["llm_model"] = AutoModelForSeq2SeqLM.from_pretrained(LLM_NAME)
    
    print("Conectando a Milvus...")
    connections.connect(alias=MILVUS_ALIAS, host=MILVUS_HOST, port=MILVUS_PORT)
    
    # Cargar la colección de Milvus en memoria para búsquedas rápidas
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        models["milvus_collection"] = collection
        print(f"Colección de Milvus '{COLLECTION_NAME}' cargada.")
    except Exception as e:
        print(f"Error al cargar la colección de Milvus: {e}")
        models["milvus_collection"] = None

    print("--- API Lista y Modelos Cargados ---")
    
    yield
    
    # Código de limpieza al apagar la API
    print("Apagando API...")
    connections.disconnect(MILVUS_ALIAS)
    models.clear()
    print("Recursos liberados.")

# --- Inicialización de FastAPI ---
app = FastAPI(lifespan=lifespan)

# --- Modelos Pydantic (Request/Response) --- [cite: 168, 169]
class AskRequest(BaseModel):
    query: str
    backend: str # "solr" | "milvus" [cite: 50]
    k: int = 3   # Número de documentos a recuperar [cite: 51]

class SourceDocument(BaseModel):
    id: str
    content: str
    source_file: str

class AskResponse(BaseModel):
    answer: str
    source_documents: List[SourceDocument] # Para trazabilidad [cite: 57, 169, 193]

# --- Lógica RAG: Solr (Léxico) --- 
def rag_with_solr(query: str, k: int) -> List[SourceDocument]:
    print(f"Recuperando (Solr) k={k} para: '{query}'")
    try:
        # 1. Conectar a Solr [cite: 178]
        solr = pysolr.Solr(SOLR_URL, always_commit=True, timeout=10)

        # 2. Ejecutar consulta BM25 [cite: 179]
        # (Usamos los campos que definimos en index_solr.py)
        search_params = {
            "fl": "id, source_document_s, text_content_txt_es", # Campos a devolver
            "rows": k
        }
        results = solr.search(q=f"text_content_txt_es:({query})", **search_params)
        
        # 3. Recolectar contexto y fuentes [cite: 181]
        documents = []
        if results.hits > 0:
            for doc in results.docs:
                documents.append(
                    SourceDocument(
                        id=doc.get('id', 'N/A'),
                        content=doc.get('text_content_txt_es', ''),
                        source_file=doc.get('source_document_s', 'N/A')
                    )
                )
        return documents
        
    except Exception as e:
        print(f"Error en rag_with_solr: {e}")
        return []

# --- Lógica RAG: Milvus (Vectorial) --- 
def rag_with_milvus(query: str, k: int) -> List[SourceDocument]:
    print(f"Recuperando (Milvus) k={k} para: '{query}'")
    try:
        collection = models.get("milvus_collection")
        if collection is None:
            raise Exception("Colección de Milvus no está cargada.")
            
        # 1. Generar embedding del query [cite: 185]
        query_vector = models["embedding_model"].encode([query])
        
        # 2. Ejecutar búsqueda de similitud [cite: 186]
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        results = collection.search(
            data=query_vector,
            anns_field=VECTOR_FIELD_NAME,
            param=search_params,
            limit=k,
            output_fields=[TEXT_FIELD_NAME, "source_document"] # Pedimos los campos de texto
        )
        
        # 3. Recolectar contexto y fuentes [cite: 187]
        documents = []
        if results and results[0]:
            for hit in results[0]:
                entity = hit.entity
                documents.append(
                    SourceDocument(
                        id=hit.id,
                        content=entity.get(TEXT_FIELD_NAME, ''),
                        source_file=entity.get('source_document', 'N/A')
                    )
                )
        return documents

    except Exception as e:
        print(f"Error en rag_with_milvus: {e}")
        return []

# --- Lógica RAG: Generación (LLM) --- 
def generate_answer(query: str, context_docs: List[SourceDocument]) -> str:
    print(f"Generando respuesta...")
    
    # 1. Formatear el Prompt [cite: 191]
    context = "\n\n".join([doc.content for doc in context_docs])
    
    prompt_template = f"""
Usando SÓLO el siguiente contexto, responde la pregunta.
Si la respuesta no está en el contexto, di "No tengo información suficiente".

Contexto:
{context}

Pregunta:
{query}

Respuesta (en español):
"""    
    # 2. Ejecutar inferencia con el LLM [cite: 192]
    try:
        tokenizer = models["llm_tokenizer"]
        model = models["llm_model"]
        
        inputs = tokenizer(prompt_template, return_tensors="pt", max_length=1024, truncation=True)
        
        # Generar la respuesta
        outputs = model.generate(
            **inputs, 
            max_length=256, 
            num_beams=4, 
            early_stopping=True
        )
        
        # 3. Decodificar la respuesta [cite: 193]
        answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return answer

    except Exception as e:
        print(f"Error en generate_answer: {e}")
        return "Error al generar la respuesta."


# --- Endpoint Principal de la API ---
@app.post("/ask", response_model=AskResponse)
async def post_ask(request: AskRequest):
    """
    Recibe una consulta y la enruta al backend RAG especificado (Solr o Milvus).
    """
    print(f"Petición recibida: backend={request.backend}, k={request.k}")
    start_time = time.time()
    
    source_documents = []
    
    # 1. Lógica de Enrutamiento (Dispatch) 
    if request.backend == "solr":
        source_documents = rag_with_solr(request.query, request.k)
    elif request.backend == "milvus":
        source_documents = rag_with_milvus(request.query, request.k)
    else:
        raise HTTPException(status_code=400, detail="Backend no válido. Use 'solr' o 'milvus'.")
        
    # 2. Generar Respuesta (si hay contexto)
    if not source_documents:
        answer = "No se encontraron documentos relevantes para la consulta."
    else:
        # Llamamos al generador (el mismo para ambos backends) [cite: 54, 182, 188]
        answer = generate_answer(request.query, source_documents)

    end_time = time.time()
    print(f"Respuesta generada en {end_time - start_time:.2f} segundos.")

    # 3. Devolver respuesta con trazabilidad [cite: 57, 193]
    return AskResponse(
        answer=answer,
        source_documents=source_documents
    )

# Endpoint de salud para verificar que la API esté viva
@app.get("/health")
async def health_check():
    return {"status": "ok", "models_loaded": list(models.keys())}