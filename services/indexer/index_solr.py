import os
import pysolr
from tqdm import tqdm
import time

# --- Variables de Entorno ---
SOLR_HOST = os.getenv("SOLR_HOST", "localhost")
SOLR_PORT = os.getenv("SOLR_PORT", "8983")
SOLR_CORE = os.getenv("SOLR_CORE", "taller_rag_core")

# URL de conexión para Solr
SOLR_URL = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/{SOLR_CORE}"

def wait_for_solr(solr_instance, timeout=120):
    """
    Espera a que Solr esté disponible antes de continuar.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            solr_instance.ping()
            print("Conexión con Solr exitosa.")
            return True
        except pysolr.SolrError:
            print("Esperando a Solr...")
            time.sleep(5)
    print(f"Error: Timeout esperando a Solr en {SOLR_URL}")
    return False

def index_data_in_solr(data_df):
    """
    Función principal para indexar datos en Solr.
    Recibe un DataFrame de pandas con los datos del corpus.
    """
    print("\n--- Iniciando Indexación en Solr ---")
    
    try:
        # 1. Conectar a Solr
        print(f"Conectando a Solr en: {SOLR_URL}")
        solr = pysolr.Solr(SOLR_URL, always_commit=True, timeout=30, decoder='utf-8')
        
        # 2. Verificar conexión
        if not wait_for_solr(solr):
            print("Asegúrese de que el contenedor 'solr' esté corriendo ('docker-compose ps').")
            return

    except Exception as e:
        print(f"Error: No se pudo conectar a Solr en {SOLR_URL}")
        print(f"Detalle: {e}")
        return

    # --- Lógica de Fase 2 (Implementación) ---

    print("Preparando documentos para Solr...")
    
    # 3. (Opcional pero recomendado) Limpiar índice existente
    # print("Limpiando índice anterior...")
    solr.delete(q='*:*') # ¡Cuidado! Borra todo.

    # 4. Preparar y añadir documentos en lotes
    batch_size = 500
    documents_batch = []
    
    print("Iniciando iteración del corpus...")
    
    if data_df is not None and not data_df.empty:
        try:
            for index, row in tqdm(data_df.iterrows(), total=data_df.shape[0], desc="Indexando en Solr"):
                
                # *** ¡AJUSTE REALIZADO! ***
                # Usamos los nombres de columna del DataFrame
                doc = {
                    'id': str(row['chunk_id']),
                    'text_content_txt_es': str(row['text_content']), # Campo de texto en español
                    'source_document_s': str(row['source_document'])  # Campo string
                }
                documents_batch.append(doc)
                
                # Enviar lote cuando esté lleno
                if len(documents_batch) >= batch_size:
                    solr.add(documents_batch)
                    documents_batch = []

            # Enviar el último lote restante
            if documents_batch:
                solr.add(documents_batch)
            
            print(f"\nIndexación en Solr completada. Total: {data_df.shape[0]} documentos.")

        except Exception as e:
            print(f"\nError durante la indexación de Solr: {e}")
            print("Verifica los nombres de las columnas y el esquema de Solr.")
    else:
        print("No se proporcionaron datos (DataFrame vacío) para indexar.")

    print("--- Indexación en Solr Finalizada ---")

 