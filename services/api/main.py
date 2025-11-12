import os
import time
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# --- Conectores de Bases de Datos ---
import pysolr
from pymilvus import connections, Collection
from dotenv import load_dotenv

# --- Stack de IA (Embeddings y Generador) ---
from sentence_transformers import SentenceTransformer
#from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import google.generativeai as genai

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
EMBEDDING_MODEL_NAME = 'models/text-embedding-004' # Modelo de Google
LLM_NAME = 'gemini-flash-latest'
MODEL_DIMENSION = 768 # ¡Importante!

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
    
    load_dotenv()
    # 2. Configurar y cargar el LLM de Google
    print(f"Configurando modelo generador (LLM) de Google: {LLM_NAME}")
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada. Asegúrate de definirla en el .env")
        
        genai.configure(api_key=api_key)
        
        # Configuración de seguridad (ajusta según necesidad)
        generation_config = {
            "temperature": 0.5,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 8192
        }
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        print("Características de seguridad actuales:",safety_settings)
        
        models["llm_model"] = genai.GenerativeModel(
            model_name=LLM_NAME,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        print("Modelo Generador de Google cargado.")
        
        # 2. Configurar el modelo de Embeddings de Google
        #    (Ya no cargamos SentenceTransformer)
        print(f"Configurando modelo de embeddings de Google: {EMBEDDING_MODEL_NAME}")
        models["embedding_model"] = EMBEDDING_MODEL_NAME # Solo guardamos el nombre
        
    except Exception as e:
        print(f"Error fatal al cargar el modelo de Google: {e}")
        models["llm_model"] = None 
        models["embedding_model"] = None
        
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
    retrieval_latency_sec: float
    
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
        start_search = time.time()
        results = solr.search(q=f"text_content_txt_es:({query})", **search_params)
        retrieval_time = time.time() - start_search        
        
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
        return documents, retrieval_time
        
    except Exception as e:
        print(f"Error en rag_with_solr: {e}")
        return []

# --- Lógica RAG: Milvus (Vectorial) --- 
def rag_with_milvus(query: str, k: int) -> List[SourceDocument]:
    print(f"Recuperando (Milvus) k={k} para: '{query}'")
    try:
        collection = models.get("milvus_collection")    
        model_name = models.get("embedding_model")
        if collection is None or model_name is None:
            raise Exception("Colección de Milvus o modelo de embedding no cargado.")            
            
        # 1. Generar embedding del query (USANDO LA API DE GOOGLE)
        #    Usamos 'retrieval_query' para la tarea de consulta
        start_embed = time.time()
        result = genai.embed_content(
            model=model_name,
            content=query,
            task_type="retrieval_query"
        )
        query_vector = [result['embedding']] # La API devuelve un vector, lo ponemos en una lista
        print(f"Embedding de consulta generado en {time.time() - start_embed:.4f}s")
        
        # 2. Ejecutar búsqueda de similitud [cite: 186]
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        start_search = time.time()
        results = collection.search(
            data=query_vector,
            anns_field=VECTOR_FIELD_NAME,
            param=search_params,
            limit=k,
            output_fields=[TEXT_FIELD_NAME, "source_document"]
        )
        retrieval_time = time.time() - start_search        
        
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
        return documents, retrieval_time

    except Exception as e:
        print(f"Error en rag_with_milvus: {e}")
        return []

# --- Lógica RAG: Generación (LLM) --- 
def generate_answer(query: str, context_docs: List[SourceDocument]) -> str:
    print(f"Generando respuesta con {LLM_NAME}...")
    
    # 1. Formatear el Prompt [cite: 191]
    context = "\n\n".join([doc.content for doc in context_docs])
    
    prompt = f"""
Usando SÓLO el siguiente contexto, responde la pregunta.
Si la respuesta no está en el contexto, di "No tengo información suficiente".

Contexto:
{context}

Pregunta:
{query}

Respuesta (en español):
"""    
    try:
        model = models.get("llm_model")
        if model is None:
            raise Exception("El modelo LLM de Google no está cargado.")
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # Llamada a la API de Gemini
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # --- VERIFICACIÓN DE RESPUESTA (CORREGIDA) ---
        
        if not response.candidates:
            # Manejar bloqueo de prompt (esto no ha cambiado)
            if response.prompt_feedback:
                error_detail = f"BLOQUEO DE PROMPT. Razón: {response.prompt_feedback.block_reason}. Ratings: {response.prompt_feedback.safety_ratings}"
                print(f"Error en generate_answer (Gemini): {error_detail}")
                return f"Error al generar la respuesta: {error_detail}"
            else:
                return "Error al generar la respuesta: Respuesta vacía sin feedback."

        candidate = response.candidates[0]
        
        # --- CORRECCIÓN CLAVE AQUÍ ---
        # Aceptamos la respuesta si se detuvo (1) O si alcanzó el límite de tokens (2)
        if candidate.finish_reason.value in [1, 2]: # 1 = STOP, 2 = MAX_TOKENS
            return response.text # Éxito, devuelve el texto (incluso si está truncado)
        # --- FIN DE LA CORRECCIÓN CLAVE ---

        # Si no es 1 ni 2, ES un error (SAFETY, RECITATION, OTHER)
        error_detail = f"Razón: {candidate.finish_reason.name} ({candidate.finish_reason.value}). "
        
        if candidate.safety_ratings:
            ratings = [f"{rating.category.name}: {rating.probability.name}" for rating in candidate.safety_ratings]
            error_detail += f"Ratings: [{', '.join(ratings)}]"
        
        print(f"Error en generate_answer (Gemini): {error_detail}")
        return f"Error al generar la respuesta: {error_detail}"
        
    except Exception as e:
        print(f"Error en generate_answer (Gemini): {e}")
        return f"Error al generar la respuesta: {e}"
# --- FIN DE LA MODIFICACIÓN ---

# --- Endpoint Principal de la API ---
@app.post("/ask", response_model=AskResponse)
async def post_ask(request: AskRequest):
    """
    Recibe una consulta y la enruta al backend RAG especificado (Solr o Milvus).
    """
    print(f"Petición recibida: backend={request.backend}, k={request.k}")
    start_time = time.time()
    
    source_documents = []
    retrieval_latency = 0.0
    
    # 1. Lógica de Enrutamiento (Dispatch) 
    if request.backend == "solr":
        source_documents, retrieval_latency = rag_with_solr(request.query, request.k)
    elif request.backend == "milvus":
        source_documents, retrieval_latency = rag_with_milvus(request.query, request.k)
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
        source_documents=source_documents,
        retrieval_latency_sec=retrieval_latency
    )

# Endpoint de salud para verificar que la API esté viva
@app.get("/health")
async def health_check():
    return {"status": "ok", "models_loaded": list(models.keys())}