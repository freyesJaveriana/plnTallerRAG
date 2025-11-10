import os
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal

# --- Modelos Pydantic ---
# Estos modelos validan los datos de entrada y salida de la API.

class AskRequest(BaseModel):
    """
    Define la estructura del JSON que esperamos en el POST /ask
    Coincide con la especificación del taller.
    """
    query: str
    backend: Literal["solr", "milvus"] # Solo permite "solr" o "milvus"
    k: int = Field(..., gt=0) # 'k' debe ser un entero mayor que 0

class AskResponse(BaseModel):
    """
    Define la estructura de la respuesta JSON.
    (Placeholder - esto se expandirá en la Fase 3)
    """
    message: str
    query_received: str
    backend_used: str
    k_value: int
    results: list = [] # Aquí irán los documentos fuente
    llm_response: str = "" # Aquí irá la respuesta del LLM

# --- Configuración de la App ---
app = FastAPI(
    title="Taller RAG API",
    description="API unificada para comparar RAG con Solr y Milvus",
    version="0.1.0"
)

# --- Conexiones (se inicializarán al arrancar) ---
# (Dejaremos esto listo para la Fase 3)
# solr_client = None
# milvus_client = None
# llm_pipeline = None

# @app.on_event("startup")
# async def startup_event():
#     """
#     Función que se ejecuta al iniciar la API.
#     Ideal para cargar modelos y establecer conexiones.
#     """
#     global solr_client, milvus_client, llm_pipeline
#     print("Iniciando API y conectando a servicios...")
    
#     # Aquí conectaríamos a Solr
#     solr_host = os.getenv("SOLR_HOST", "localhost")
#     solr_port = os.getenv("SOLR_PORT", "8983")
#     solr_core = os.getenv("SOLR_CORE", "taller_rag_core")
#     # solr_client = ...
    
#     # Aquí conectaríamos a Milvus
#     milvus_host = os.getenv("MILVUS_HOST", "localhost")
#     milvus_port = os.getenv("MILVUS_PORT", "19530")
#     # milvus_client = ...
    
#     # Aquí cargaríamos el modelo de LLM (ej. de Hugging Face)
#     # llm_pipeline = ...
    
#     print("API iniciada (conexiones placeholder).")


# --- Endpoints de la API ---

@app.get("/")
def read_root():
    """
    Endpoint raíz para verificar que la API esté viva.
    """
    return {"status": "ok", "message": "Bienvenido a la API RAG"}


@app.post("/ask", response_model=AskResponse)
async def ask_rag(request: AskRequest):
    """
    Endpoint principal del taller.
    Recibe una consulta y la enruta al backend RAG (Solr o Milvus).
    """
    
    # --- FASE 1: Placeholder ---
    # En esta fase, solo devolvemos un mensaje confirmando que
    # recibimos la solicitud.
    # La lógica real se implementará en la Fase 3.
    # ---------------------------
    
    print(f"Recibida solicitud: query='{request.query}', backend='{request.backend}', k={request.k}")
    
    # Lógica de la Fase 3 (comentada por ahora)
    # 1. Recuperar contexto (Retrieve)
    # if request.backend == "solr":
    #     context_docs = retrieve_from_solr(request.query, request.k)
    # else:
    #     context_docs = retrieve_from_milvus(request.query, request.k)
    
    # 2. Generar respuesta (Generate)
    # prompt = create_prompt(request.query, context_docs)
    # llm_answer = generate_with_llm(prompt)
    
    # 3. Devolver respuesta
    # return AskResponse(...)

    # Respuesta de placeholder (Fase 1)
    return AskResponse(
        message="Solicitud recibida (Placeholder)",
        query_received=request.query,
        backend_used=request.backend,
        k_value=request.k,
        results=[{"source": "doc1.txt", "content": "Contenido placeholder..."}],
        llm_response="Respuesta generada por el LLM (placeholder)..."
    )

# --- Funciones (se implementarán en Fase 3) ---

# def retrieve_from_solr(query, k):
#     print("Buscando en Solr...")
#     # Lógica de pysolr
#     return []

# def retrieve_from_milvus(query, k):
#     print("Buscando en Milvus...")
#     # Lógica de pymilvus + sentence-transformers
#     return []

# def create_prompt(query, context_docs):
#     # Lógica para construir el prompt
#     return f"Contexto: {context_docs}\n\nPregunta: {query}\n\nRespuesta:"

# def generate_with_llm(prompt):
#     # Lógica del pipeline de transformers
#     return "Respuesta basada en el contexto."