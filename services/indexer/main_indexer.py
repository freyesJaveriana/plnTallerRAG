import time
import pandas as pd

# Importamos las funciones que acabamos de definir en los otros archivos
from index_solr import index_data_in_solr
from index_milvus import index_data_in_milvus

# --- Configuración del Corpus ---
# ***************************************************************
# *** ¡ACCIÓN REQUERIDA! ***
#
# 1. Cambia 'tu_corpus.csv' al nombre de tu archivo en /data/corpus/
# 2. Asegúrate de que tu archivo esté en la carpeta /data/corpus/
# ***************************************************************
CORPUS_PATH = "/data/corpus/tu_corpus.csv" # Docker lo verá en esta ruta

def load_corpus():
    """
    Carga el corpus desde la ruta especificada.
    """
    print(f"Cargando corpus desde: {CORPUS_PATH}")
    try:
        # --- ¡ACCIÓN REQUERIDA! ---
        # Si tu archivo no es un CSV, cambia esta línea.
        # Usa pd.read_parquet(), pd.read_json(), pd.read_excel(), etc.
        df = pd.read_csv(CORPUS_PATH)
        
        print(f"Corpus cargado exitosamente. {len(df)} filas encontradas.")
        # print("Primeras filas del corpus:\n", df.head())
        return df
    
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado en '{CORPUS_PATH}'")
        print("Asegúrate de que tu archivo esté en la carpeta /data/corpus/ del proyecto.")
        return None
    except Exception as e:
        print(f"Error al cargar el corpus: {e}")
        return None

# --- Función Principal ---
def main():
    """
    Orquestador principal del proceso de indexación.
    """
    print("--- INICIANDO PROCESO DE INDEXACIÓN (FASE 2) ---")
    start_time = time.time()
    
    # 1. Cargar el corpus
    # (Descomenta esto cuando estés listo para la Fase 2)
    # data_df = load_corpus()
    
    # --- Placeholder (Fase 1) ---
    # Usamos None para que los scripts de indexación 
    # se ejecuten en modo 'placeholder' sin un corpus real.
    data_df = None
    if data_df is None:
        print("Ejecutando en modo placeholder (sin corpus real).")
        print("Edita 'main_indexer.py' para cargar tu corpus en la Fase 2.")
    # --- Fin del Placeholder ---

    # 2. Indexar en Solr
    try:
        index_data_in_solr(data_df)
    except Exception as e:
        print(f"\n*** ERROR FATAL DURANTE INDEXACIÓN DE SOLR: {e} ***\n")

    print("\n" + "="*50 + "\n")
    
    # 3. Indexar en Milvus
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