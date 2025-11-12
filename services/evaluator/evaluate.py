import os
import time
import json
import requests
import pandas as pd
from tqdm import tqdm
from rouge_score import rouge_scorer
import nltk

# --- Configuración ---
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8000")
API_URL = f"http://{API_HOST}:{API_PORT}/ask"

# Rutas de los volúmenes (mapeadas en docker-compose.yml)
GOLD_STANDARD_PATH = "/reports/gold_standard.json"
RESULTS_PATH = "/reports/evaluation_results.csv"

# K para las métricas (coincide con el K de la API si se desea)
K_METRICS = 5 

# --- Funciones de Métricas ---

def setup_nltk():
    """Descarga los paquetes necesarios de NLTK."""
    try:
        print("Verificando NLTK (punkt)...")
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Descargando NLTK 'punkt' y 'punkt_tab' (para español)...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True) # <-- AÑADE ESTA LÍNEA    print("NLTK listo.")

def calculate_recall_at_k(retrieved_ids: list, relevant_ids: list, k: int) -> float:
    """Calcula Recall@k."""
    if not relevant_ids:
        return 0.0
    retrieved_at_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    hits = retrieved_at_k.intersection(relevant_set)
    return len(hits) / len(relevant_set)

def calculate_mrr_at_k(retrieved_ids: list, relevant_ids: list, k: int) -> float:
    """Calcula Mean Reciprocal Rank@k."""
    if not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_set:
            return 1.0 / (i + 1)
    return 0.0

def calculate_rouge_l(generated_answer: str, ideal_answer: str) -> float:
    """Calcula el F-score de ROUGE-L."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(ideal_answer, generated_answer)
    return scores['rougeL'].fmeasure

# --- Función Principal ---

def run_evaluation():
    """
    Ejecuta el pipeline de evaluación completo.
    """
    print("--- Iniciando Protocolo de Evaluación (Fase 4) ---")
    
    # 1. Cargar Gold Standard
    try:
        with open(GOLD_STANDARD_PATH, 'r', encoding='utf-8') as f:
            gold_standard = json.load(f)
        print(f"Gold Standard cargado. {len(gold_standard)} preguntas encontradas.")
    except FileNotFoundError:
        print(f"Error: No se encontró '{GOLD_STANDARD_PATH}'.")
        print("Asegúrate de que el archivo existe en la carpeta /reports.")
        return
    except Exception as e:
        print(f"Error al leer el Gold Standard: {e}")
        return

    # 2. Preparar NLTK (para ROUGE)
    setup_nltk()

    results_list = []
    
    # Iterar sobre cada pregunta y cada backend
    # Envolvemos el bucle principal con tqdm
    pbar = tqdm(total=len(gold_standard) * 2, desc="Evaluando (Solr/Milvus)")

    for item in gold_standard:
        query = item['query']
        relevant_ids = item['relevant_chunk_ids'] 
        ideal_answer = item['ideal_answer']

        for backend in ["solr", "milvus"]:
            try:
                # 3.1. Llamar a la API
                payload = {
                    "query": query,
                    "backend": backend,
                    "k": K_METRICS 
                }
                start_time = time.time()
                response = requests.post(API_URL, json=payload, timeout=180)
                # 'latency' aquí es la latencia TOTAL (Búsqueda + Generación)
                latency = time.time() - start_time
                
                if response.status_code != 200:
                    raise Exception(f"Error de API: {response.status_code} {response.text}")
                
                data = response.json()
                generated_answer = data.get('answer', '')
                retrieved_docs = data.get('source_documents', [])
                retrieved_ids = [doc.get('id', '') for doc in retrieved_docs]
                retrieval_latency = data.get('retrieval_latency_sec', -1)

                # 3.2. Calcular Métricas
                recall = calculate_recall_at_k(retrieved_ids, relevant_ids, K_METRICS)
                mrr = calculate_mrr_at_k(retrieved_ids, relevant_ids, K_METRICS)
                rouge_l = calculate_rouge_l(generated_answer, ideal_answer)

                # 3.3. Guardar resultados
                results_list.append({
                    "query": query,
                    "backend": backend,
                    "total_latency_sec": latency,
                    "retrieval_latency_sec": retrieval_latency,
                    "recall_at_k": recall,
                    "mrr_at_k": mrr,
                    "rouge_l_f1": rouge_l,
                    "generated_answer": generated_answer,
                    "retrieved_ids": "|".join(retrieved_ids),
                    "relevant_ids": "|".join(relevant_ids)
                })

            except Exception as e:
                # ... (el manejo de errores no cambia) ...
                results_list.append({
                    "query": query, "backend": backend, 
                    "total_latency_sec": -1, "retrieval_latency_sec": -1,
                    "recall_at_k": 0, "mrr_at_k": 0, "rouge_l_f1": 0,
                    "generated_answer": f"ERROR: {e}",
                })
            
            pbar.update(1) # Actualizar la barra de progreso
            # --- FIN DE LA MODIFICACIÓN ---

    pbar.close() # Cerrar la barra de progreso
    
    # ... (El guardado en CSV y el resumen final no cambian) ...
    if not results_list:
        print("No se generaron resultados.")
        return

    print("\nEvaluación completada. Guardando resultados...")
    df_results = pd.DataFrame(results_list)
    
    try:
        df_results.to_csv(RESULTS_PATH, index=False, encoding='utf-8')
        print(f"Resultados guardados exitosamente en: {RESULTS_PATH}")
    except Exception as e:
        print(f"Error al guardar el CSV en {RESULTS_PATH}: {e}")

    print("\n--- Resumen de Métricas (Promedio) ---")
    metric_cols = ['total_latency_sec', 'retrieval_latency_sec', 'recall_at_k', 'mrr_at_k', 'rouge_l_f1']
    df_summary = df_results.groupby('backend')[metric_cols].mean()
    
    print(df_summary.to_markdown(floatfmt=".4f"))


if __name__ == "__main__":
    run_evaluation()