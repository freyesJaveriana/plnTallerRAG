import os
from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import time

# --- Constantes y Variables de Entorno ---
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_ALIAS = "default" # Alias de la conexión

# --- Configuración del Modelo y Colección ---
# ***************************************************************
# *** ¡ACCIÓN REQUERIDA! (Opcional) ***
# Puedes cambiar el modelo, pero asegúrate de que la dimensión
# (MODEL_DIMENSION) coincida.
# 'paraphrase-multilingual-MiniLM-L12-v2' es bueno para multilingüe
# y tiene una dimensión de 384.
# ***************************************************************
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MODEL_DIMENSION = 384
COLLECTION_NAME = "taller_rag_corpus"
ID_FIELD_NAME = "doc_id"
TEXT_FIELD_NAME = "text_content"
VECTOR_FIELD_NAME = "vector_embedding"
METRIC_TYPE = "L2" # Métrica de distancia (L2 = Euclidiana)

def wait_for_milvus(timeout=120):
    """
    Espera a que Milvus esté disponible antes de continuar.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            connections.connect(
                alias=MILVUS_ALIAS,
                host=MILVUS_HOST,
                port=MILVUS_PORT
            )
            connections.disconnect(MILVUS_ALIAS)
            print("Conexión con Milvus exitosa.")
            return True
        except Exception:
            print("Esperando a Milvus...")
            time.sleep(5)
    print(f"Error: Timeout esperando a Milvus en {MILVUS_HOST}:{MILVUS_PORT}")
    return False

def create_milvus_collection():
    """
    Define y crea la colección en Milvus si no existe.
    """
    if utility.has_collection(COLLECTION_NAME, using=MILVUS_ALIAS):
        print(f"Colección '{COLLECTION_NAME}' ya existe.")
        return Collection(COLLECTION_NAME, using=MILVUS_ALIAS)

    print(f"Creando colección '{COLLECTION_NAME}'...")
    
    # 1. Definir campos
    field_id = FieldSchema(
        name=ID_FIELD_NAME,
        dtype=DataType.VARCHAR,
        is_primary=True,
        auto_id=False,
        max_length=256
    )
    field_text = FieldSchema(
        name=TEXT_FIELD_NAME,
        dtype=DataType.VARCHAR,
        max_length=65535
    )
    
    # --- CAMBIO AQUÍ: AÑADIDO NUEVO CAMPO ---
    field_source = FieldSchema(
        name="source_document", # El campo que faltaba
        dtype=DataType.VARCHAR,
        max_length=512 # Suficiente para un nombre de archivo
    )
    # --- FIN DEL CAMBIO ---

    field_vector = FieldSchema(
        name=VECTOR_FIELD_NAME,
        dtype=DataType.FLOAT_VECTOR,
        dim=MODEL_DIMENSION
    )

    # 2. Crear esquema (¡Añadir el nuevo campo!)
    schema = CollectionSchema(
        # --- CAMBIO AQUÍ: AÑADIDO field_source ---
        fields=[field_id, field_text, field_source, field_vector],
        description="Colección para Taller RAG"
    )
    # --- FIN DEL CAMBIO ---

    # 3. Crear colección
    collection = Collection(
        name=COLLECTION_NAME,
        schema=schema,
        using=MILVUS_ALIAS
    )
    
    print(f"Colección '{COLLECTION_NAME}' creada.")
    
    # 4. Crear índice
    print(f"Creando índice HNSW para '{VECTOR_FIELD_NAME}'...")
    index_params = {
        "metric_type": METRIC_TYPE,
        "index_type": "HNSW",
        "params": {"M": 8, "efConstruction": 64}
    }
    collection.create_index(
        field_name=VECTOR_FIELD_NAME,
        index_params=index_params
    )
    print("Índice creado.")
    
    return collection

def index_data_in_milvus(data_df):
    """
    Función principal para indexar datos en Milvus.
    Recibe un DataFrame de pandas con los datos del corpus.
    """
    print("\n--- Iniciando Indexación en Milvus ---")
    
    # 1. Conectar a Milvus
    if not wait_for_milvus():
        print("Asegúrese de que el contenedor 'milvus' esté corriendo ('docker-compose ps').")
        return
    
    connections.connect(alias=MILVUS_ALIAS, host=MILVUS_HOST, port=MILVUS_PORT)
    
    # 2. Cargar modelo de Embeddings
    print(f"Cargando modelo de embeddings: '{MODEL_NAME}'...")
    # (device='cuda') si tienes GPU disponible y torch con CUDA
    model = SentenceTransformer(MODEL_NAME, device='cpu')
    print("Modelo cargado.")

    # 3. Obtener/Crear Colección
    collection = create_milvus_collection()

    # --- Lógica de Fase 2 (Implementación) ---
    print("Preparando documentos para Milvus...")
    
    # 4. (Opcional) Limpiar colección existente
    # print("Limpiando colección anterior...")
    # if collection.num_entities > 0:
    #     collection.truncate()

    # 5. Preparar y añadir documentos en lotes
    batch_size = 100
    
    print("Iniciando iteración del corpus...")
    
    if data_df is not None and not data_df.empty:
        try:
            # Iterar en lotes (más eficiente)
            for i in tqdm(range(0, len(data_df), batch_size), desc="Indexando en Milvus"):
                batch = data_df.iloc[i:i + batch_size]
                
                # *** ¡AJUSTE REALIZADO! ***
                ids_batch = batch['chunk_id'].astype(str).tolist()
                text_batch = batch['text_content'].astype(str).tolist()
                source_batch = batch['source_document'].astype(str).tolist() # <-- AÑADIDO
                
                # Generar embeddings
                embeddings_batch = model.encode(text_batch)
                
                # Preparar datos para Milvus (de acuerdo al esquema)
                entities = [
                    ids_batch,      # Campo ID_FIELD_NAME
                    text_batch,     # Campo TEXT_FIELD_NAME
                    source_batch,   # field_source <-- AÑADIDO
                    embeddings_batch  # Campo VECTOR_FIELD_NAME
                ]
                
                # Insertar en Milvus
                collection.insert(entities)
            
            # 'Flush' final para asegurar que se escriban los datos
            collection.flush()
            print(f"\nIndexación en Milvus completada. Total: {len(data_df)} vectores.")
            
            # Cargar colección en memoria para búsqueda
            print("Cargando colección en memoria...")
            collection.load()
            print("Colección cargada.")

        except Exception as e:
            print(f"\nError durante la indexación de Milvus: {e}")
            print("Verifica los nombres de las columnas y la conexión.")
    else:
        print("No se proporcionaron datos (DataFrame vacío) para indexar.")

    # Cargar la colección (incluso si está vacía) para que esté lista
    print("Asegurando que la colección esté cargada (incluso si estaba vacía)...")
    collection.load()
    
    connections.disconnect(MILVUS_ALIAS)
    print("--- Indexación en Milvus Finalizada ---")    
 