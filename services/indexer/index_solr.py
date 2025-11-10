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
        solr = pysolr.Solr(SOLR_URL, always_commit=True, timeout=30)
        
        # 2. Verificar conexión
        if not wait_for_solr(solr):
            print("Asegúrese de que el contenedor 'solr' esté corriendo ('docker-compose ps').")
            return

    except Exception as e:
        print(f"Error: No se pudo conectar a Solr en {SOLR_URL}")
        print(f"Detalle: {e}")
        return

    # --- Lógica de Fase 2 (Implementación) ---
    # Este bloque es un placeholder. Deberás adaptarlo a la
    # estructura de tu corpus (tu DataFrame).

    print("Preparando documentos para Solr...")
    
    # 3. (Opcional pero recomendado) Limpiar índice existente
    # print("Limpiando índice anterior...")
    # solr.delete(q='*:*') # ¡Cuidado! Borra todo.

    # 4. Preparar y añadir documentos en lotes
    batch_size = 500
    documents_batch = []
    
    # ***************************************************************
    # *** ¡ACCIÓN REQUERIDA! ***
    # Ajusta los nombres de las columnas ('id', 'texto', 'fuente')
    # para que coincidan con tu DataFrame.
    #
    # Solr (con el 'managed-schema') es flexible, pero se
    # recomienda usar sufijos como:
    #   '_s' para strings exactos (ej. 'id', 'fuente_s')
    #   '_txt_es' para texto en español (ej. 'contenido_txt_es')
    # ***************************************************************

    print("Iniciando iteración del corpus (esto es un placeholder)...")
    
    # --- EJEMPLO DE LÓGICA DE INDEXACIÓN ---
    # (Actualmente comentado para que el placeholder se ejecute rápido)
    #
    # if data_df is not None and not data_df.empty:
    #     try:
    #         for index, row in tqdm(data_df.iterrows(), total=data_df.shape[0], desc="Indexando en Solr"):
    #             # *** ¡AJUSTA ESTO! ***
    #             doc = {
    #                 'id': str(row['id_columna_en_tu_df']),
    #                 'contenido_txt_es': str(row['texto_columna_en_tu_df']),
    #                 'fuente_s': str(row['fuente_columna_en_tu_df'])
    #                 # Añade más campos si los necesitas
    #             }
    #             documents_batch.append(doc)
                
    #             # Enviar lote cuando esté lleno
    #             if len(documents_batch) >= batch_size:
    #                 solr.add(documents_batch)
    #                 documents_batch = []

    #         # Enviar el último lote restante
    #         if documents_batch:
    #             solr.add(documents_batch)
            
    #         print(f"Indexación en Solr completada. Total: {data_df.shape[0]} documentos.")

    #     except Exception as e:
    #         print(f"Error durante la indexación de Solr: {e}")
    #         print("Verifica los nombres de las columnas y el esquema de Solr.")
    # else:
    #     print("No se proporcionaron datos (DataFrame vacío) para indexar.")

    # --- Fin del Ejemplo ---

    print("--- Indexación en Solr (Placeholder) Finalizada ---")