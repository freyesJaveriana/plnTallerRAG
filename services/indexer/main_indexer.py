import os
import glob
import time
import pandas as pd
import nltk
from tqdm import tqdm

# Importamos las funciones de los otros archivos
from index_solr import index_data_in_solr
from index_milvus import index_data_in_milvus

# --- Configuración del Corpus y Segmentación ---
CORPUS_PATH = "/data/corpus" # Ruta en Docker
FILE_PATTERN = "*.txt"
CHUNK_SIZE = 3       # Número de oraciones por "pasaje" (chunk)
CHUNK_OVERLAP = 1    # Número de oraciones a superponer

def setup_nltk():
    """Descarga los paquetes necesarios de NLTK."""
    try:
        print("Verificando NLTK (punkt)...")
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Descargando NLTK 'punkt' y 'punkt_tab' (para español)...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True) # <-- AÑADE ESTA LÍNEA    print("NLTK listo.")

def process_corpus_to_dataframe():
    """
    Carga, segmenta y procesa el corpus desde los archivos .txt.
    """
    print(f"Cargando corpus desde: {CORPUS_PATH}/{FILE_PATTERN}")
    
    # Usamos glob para encontrar todos los archivos de texto
    file_paths = glob.glob(os.path.join(CORPUS_PATH, FILE_PATTERN))
    
    if not file_paths:
        print(f"Error: No se encontraron archivos '{FILE_PATTERN}' en '{CORPUS_PATH}'.")
        print("Asegúrate de que tus archivos de corpus estén en la carpeta /data/corpus/")
        return None

    print(f"Se encontraron {len(file_paths)} archivos de corpus.")
    
    all_chunks = []
    
    # Iteramos sobre cada archivo .txt encontrado
    for file_path in tqdm(file_paths, desc="Procesando archivos"):
        file_name = os.path.basename(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Leemos el contenido. Asumimos que es una sola línea larga.
                content = f.read()

            # 1. Dividir en oraciones
            # Usamos 'spanish' para mejor tokenización de "¡Hola! ¿Qué tal?"
            sentences = nltk.sent_tokenize(content, language='spanish')
            
            if not sentences:
                continue

            # 2. Agrupar en pasajes (chunks) con superposición
            chunk_num = 0
            step = CHUNK_SIZE - CHUNK_OVERLAP
            
            for i in range(0, len(sentences), step):
                chunk_sentences = sentences[i : i + CHUNK_SIZE]
                if not chunk_sentences:
                    continue
                
                # Unimos las oraciones del chunk en un solo texto
                chunk_text = " ".join(chunk_sentences)
                
                # Creamos un ID único para este chunk
                chunk_id = f"{file_name}_{chunk_num:04d}"
                
                chunk_data = {
                    "chunk_id": chunk_id,          # ID único del pasaje
                    "text_content": chunk_text,    # El texto del pasaje
                    "source_document": file_name   # De qué archivo vino
                }
                all_chunks.append(chunk_data)
                chunk_num += 1
                
        except Exception as e:
            print(f"Error procesando el archivo {file_name}: {e}")
            
    if not all_chunks:
        print("Error: No se pudo generar ningún chunk del corpus.")
        return None

    # 3. Convertir a DataFrame
    df = pd.DataFrame(all_chunks)
    return df

# --- Función Principal ---
def main():
    """
    Orquestador principal del proceso de indexación.
    """
    print("--- INICIANDO PROCESO DE INDEXACIÓN (FASE 2) ---")
    start_time = time.time()
    
    # 1. Preparar NLTK
    setup_nltk()

    # 2. Cargar y procesar el corpus
    data_df = process_corpus_to_dataframe()
    
    if data_df is None or data_df.empty:
        print("Finalizando: No hay datos para indexar.")
        return

    print(f"\nCorpus procesado. Total de {len(data_df)} chunks (pasajes) generados.")
    print("Ejemplo de chunks generados:")
    print(data_df.head())

    try:
        debug_path = "/data/chunks_debug.csv"
        data_df.to_csv(debug_path, index=False, encoding='utf-8')
        print(f"DataFrame de depuración guardado en: {debug_path}")
    except Exception as e:
        print(f"Error al guardar el CSV de depuración: {e}")
        
    # 3. Indexar en Solr
    try:
        index_data_in_solr(data_df)
    except Exception as e:
        print(f"\n*** ERROR FATAL DURANTE INDEXACIÓN DE SOLR: {e} ***\n")

    print("\n" + "="*50 + "\n")
    
    # 4. Indexar en Milvus
    try:
        index_data_in_milvus(data_df)
    except Exception as e:
        print(f"\n*** ERROR FATAL DURANTE INDEXACIÓN DE MILVUS: {e} ***\n")

    end_time = time.time()
    print("\n" + "="*50)
    print(f"--- PROCESO DE INDEXACIÓN COMPLETADO ---")
    print(f"Tiempo total: {end_time - start_time:.2f} segundos.")

if __name__ == "__main__":
    main()