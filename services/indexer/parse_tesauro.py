# Archivo: /services/indexer/parse_tesauro.py

from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
from tqdm import tqdm

TESAURO_PATH = "/data/resource-tesauro.rdf"

def parse_rdf_to_synonyms():
    """
    Carga el resource-tesauro.rdf y lo convierte en una lista de
    sinónimos planos para Solr, usando skos:prefLabel y skos:altLabel.
    """
    print(f"Cargando tesauro desde: {TESAURO_PATH}")
    g = Graph()
    try:
        g.parse(TESAURO_PATH, format="xml")
    except Exception as e:
        print(f"Error fatal al parsear el RDF: {e}")
        print("Asegúrate de que 'resource-tesauro.rdf' esté en la carpeta /data.")
        return []

    print(f"Tesauro cargado. {len(g)} tripletas encontradas. Parseando conceptos...")
    
    # SKOS (Simple Knowledge Organization System) es el estándar que usa este tesauro.
    # skos:prefLabel = El término preferido (ej. "FARC-EP")
    # skos:altLabel = El término alternativo (ej. "FARC")
    
    concepts = list(g.subjects(predicate=SKOS.prefLabel))
    synonym_groups = []

    for concept_uri in tqdm(concepts, desc="Parseando conceptos"):
        # Encontrar el término principal
        pref_labels = list(g.objects(subject=concept_uri, predicate=SKOS.prefLabel))
        if not pref_labels:
            continue
        
        # El grupo de sinónimos empieza con el término principal
        group = [str(pref_labels[0])]
        
        # Encontrar todos los términos alternativos
        for alt_label in g.objects(subject=concept_uri, predicate=SKOS.altLabel):
            group.append(str(alt_label))
            
        # Solr espera una línea separada por comas
        # ej: "FARC-EP, FARC, Fuerzas Armadas Revolucionarias de Colombia"
        if len(group) > 1:
            synonym_groups.append(", ".join(group))

    print(f"Parseo completado. {len(synonym_groups)} grupos de sinónimos encontrados.")
    return synonym_groups

if __name__ == "__main__":
    # Para probar el script manualmente si es necesario
    synonyms = parse_rdf_to_synonyms()
    print("\n--- 10 Ejemplos de Grupos de Sinónimos ---")
    for s in synonyms[:10]:
        print(s)