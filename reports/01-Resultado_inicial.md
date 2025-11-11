### Análisis de Resultados (Fase 4)

Basado en tu tabla de resumen y los gráficos, esta es la interpretación correcta de la comparación:

| backend | latency\_sec | recall\_at\_k | mrr\_at\_k | rouge\_l\_f1 |
|:---|---:|---:|---:|---:|
| milvus | 4.2277 | 0.3406 | 0.4852 | 0.0827 |
| solr | 3.6362 | **0.5807** | **0.6804** | 0.0826 |


### 1. Calidad de Recuperación (Recall y MRR): Solr Gana
Esta es la mayor sorpresa, y tu observación original es correcta: **Solr (léxico) está superando a Milvus (semántico)** de manera significativa.

* **Recall@k:** Solr (0.58) encuentra el 58% de los documentos relevantes, mientras que Milvus (0.34) solo encuentra el 34%.
* **MRR@k:** Solr (0.68) es mucho mejor para poner el primer resultado correcto en una posición alta en la lista que Milvus (0.48).

**¿Por qué pasa esto? (Hipótesis)**
Esto no significa que la búsqueda semántica sea peor. Significa que nuestro *setup* actual favorece a Solr. Las causas más probables son:

1.  **Sesgo de Palabras Clave (Keyword Bias):** Tu Gold Standard de 108 preguntas probablemente usa las *mismas palabras clave* que están en los *chunks* relevantes. Por ejemplo, la pregunta `query="Qué fue el MAS?"` coincide perfectamente con un *chunk* que dice "El MAS (Muerte a Secuestradores)...". La búsqueda léxica (Solr) está diseñada para ganar en este escenario de coincidencia exacta.
2.  **Debilidad del Modelo de Embeddings:** Estamos usando un modelo de embeddings *pequeño* y *generalista* (`paraphrase-multilingual-MiniLM-L12-v2`). Es muy probable que este modelo no tenga un buen entendimiento de la jerga y los conceptos *extremadamente* específicos del conflicto colombiano. Por lo tanto, los vectores que genera para Milvus no son lo suficientemente precisos.

### 2. Calidad de Generación (ROUGE-L): Un Empate Desastroso
Este es el hallazgo más importante de todo el informe.

**Ambos sistemas tienen un ROUGE-L F1 promedio de ~0.08, que es casi cero.**

El gráfico de distribución (`image_f8d288.png`) lo confirma: la gran mayoría de las 216 respuestas (para ambos *backends*) tuvieron una puntuación de calidad de generación cercana a 0.

**¿Qué significa esto?**
Significa que el cuello de botella de tu sistema RAG **no es el buscador, es el generador**.

El modelo LLM (`google/flan-t5-base`) es demasiado "tonto" para la tarea. Incluso cuando Solr le entregó el contexto correcto (¡el 58% de las veces!), el LLM no fue capaz de usar ese contexto para redactar una respuesta que se pareciera a tu `ideal_answer`.

### 3. Latencia: Milvus es Ligeramente Más Lento
* **Solr:** 3.63 segundos
* **Milvus:** 4.22 segundos

Ambos son lentos, pero la diferencia entre ellos es de solo **~0.6 segundos**.

* **Causa de la Lentitud General:** La mayor parte del tiempo (probablemente ~3.5 segundos) en *ambas* llamadas se consume en la generación de la respuesta por parte del LLM (`flan-t5-base`) corriendo en la CPU.
* **Causa de la Diferencia:** Ese ~0.6 extra de Milvus es casi con seguridad el costo de vectorizar la consulta del usuario (`model.encode([query])`) en la CPU, un paso que Solr no necesita hacer.

---

### 💡 Conclusiones Clave (Qué Poner en tu Informe)

1.  **El Generador (LLM) es el Cuello de Botella:** La métrica ROUGE-L (la calidad final) es terrible para ambos sistemas, demostrando que `flan-t5-base` es insuficiente para esta tarea de síntesis.
2.  **Solr Gana en Búsqueda por Palabras Clave:** Con un Gold Standard basado en palabras clave, la búsqueda léxica (Solr) es superior en encontrar los documentos correctos (Recall) y clasificarlos alto (MRR).
3.  **Milvus está en Desventaja:** El rendimiento de Milvus se ve afectado por un modelo de embeddings pequeño y un Gold Standard que no prueba su fortaleza (la búsqueda *conceptual* o semántica).
4.  **La Latencia es Dominada por la Generación:** La mayor parte del tiempo de espera del usuario se debe a la inferencia del LLM en la CPU, no a la búsqueda.