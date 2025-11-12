import os
import pysolr
import time
import requests
import json
import pandas as pd
from tqdm import tqdm
from parse_tesauro import parse_rdf_to_synonyms

# --- Variables de Entorno ---
SOLR_HOST = os.getenv("SOLR_HOST", "localhost")
SOLR_PORT = os.getenv("SOLR_PORT", "8983")
SOLR_CORE = os.getenv("SOLR_CORE", "taller_rag_core")

# URL de conexión para Solr
SOLR_URL = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/{SOLR_CORE}"
SOLR_SCHEMA_API_URL = f"{SOLR_URL}/schema"

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

def configure_solr_with_tesauro(solr: pysolr.Solr):
    """
    Usa la API de Solr para:
    1. BORRAR el recurso antiguo (si existe).
    2. CREAR el nuevo recurso de sinónimos.
    3. Modificar el fieldType 'text_es' para que USE ese tesauro.
    """
    print("\n--- Configurando Solr con Tesauro CEV ---")
    
    # 1. Parsear el RDF (sin cambios)
    synonym_list = parse_rdf_to_synonyms()
    if not synonym_list:
        print("No se encontraron sinónimos. Saltando configuración del tesauro.")
        return

    # 2. Definir URLs y Payloads
    synonym_resource_url = f"{SOLR_URL}/schema/analysis/synonyms/tesauro_cev"
    headers = {'Content-type': 'application/json'}
    
    # Payload para CREAR (PUT) - Usa el nombre de clase completo y correcto
    payload_create = {
        "class": "org.apache.solr.rest.schema.analysis.ManagedSynonymGraphFilterFactory$SynonymManager", # <-- CLASE CORREGIDA
        "initArgs": {"ignoreCase": True},
        "synonyms": synonym_list
    }

    # --- PASO 1 (NUEVO): Borrar el recurso existente ---
    try:
        print(f"Intentando borrar el recurso obsoleto en: {synonym_resource_url}")
        response_delete = requests.delete(synonym_resource_url, headers=headers)
        if response_delete.status_code == 200 or response_delete.status_code == 404:
            print(f"Recurso obsoleto borrado (o no existía). Status: {response_delete.status_code}")
        else:
            print(f"Advertencia: El borrado del recurso falló (status: {response_delete.status_code}), continuando de todos modos.")
    except Exception as e:
        print(f"Advertencia durante el borrado: {e}")
    # --- FIN DEL PASO 1 ---

    # --- PASO 2: Crear el recurso ---
    try:
        print(f"Creando recurso de sinónimos 'tesauro_cev' (PUT)...")
        
        # Intentamos CREAR (PUT) con el payload (el dict)
        response_put = requests.put(synonym_resource_url, data=json.dumps(payload_create), headers=headers)
        
        if response_put.status_code == 200:
            print("Recurso de sinónimos 'tesauro_cev' CREADO.")
        else:
            # Si falla, es un error inesperado
            raise Exception(f"PUT falló inesperadamente: {response_put.text}")

    except Exception as e:
        print(f"Error Crítico al cargar sinónimos en Solr: {e}")
        return

    # --- PASO 3: Modificar el FieldType 'text_es' ---
    # (Esta parte ya estaba bien)
    print("Modificando el FieldType 'text_es' para incluir el filtro de sinónimos...")
    
    schema_payload = {
        "replace-field-type": {
            "name": "text_es",
            "class": "solr.TextField",
            "positionIncrementGap": "100",
            "analyzer": {
                "tokenizer": {
                    "class": "solr.StandardTokenizerFactory"
                },
                "filters": [
                    {"class": "solr.LowerCaseFilterFactory"},
                    {"class": "solr.StopFilterFactory", "ignoreCase": True, "words": "lang/stopwords_es.txt", "format": "snowball"},
                    {
                        "class": "solr.ManagedSynonymGraphFilterFactory",
                        "managed": "tesauro_cev"
                    },
                    {"class": "solr.SpanishLightStemFilterFactory"}
                ]
            }
        }
    }
    
    try:
        response = requests.post(SOLR_SCHEMA_API_URL, data=json.dumps(schema_payload), headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error: {response.text}")
        print("¡Éxito! El FieldType 'text_es' ahora usa el Tesauro CEV.")
    except Exception as e:
        print(f"Error Crítico al modificar el esquema de Solr: {e}")
        print("Es posible que la API de esquema esté deshabilitada o el formato sea incorrecto.")
        
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

        # --- PASO 1: Configurar el Tesauro (Nuevo) ---
        configure_solr_with_tesauro(solr)

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

 