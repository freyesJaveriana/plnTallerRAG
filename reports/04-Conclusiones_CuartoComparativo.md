### 1. 🏆 Conclusión Clave: Solr (Léxico) es el Ganador Indiscutible

Esta es la gran sorpresa. Después de todo nuestro trabajo para crear un Gold Standard "conceptual" (que *debería* haber favorecido a Milvus), **Solr (léxico) ha ganado, y por un margen aplastante.**

* **Recall@k:** Solr (`0.6285`) encontró el **63%** de los documentos relevantes, más del *doble* que Milvus (`0.3158`).
* **MRR@k:** Solr (`0.8117`) fue *extremadamente* bueno (81%) en colocar la respuesta correcta en la primera posición, superando ampliamente a Milvus (`0.4840`).
* **ROUGE-L:** Como resultado directo de su mejor recuperación, Solr (`0.4176`) también produjo respuestas generadas de mayor calidad que Milvus (`0.3099`).

Los gráficos de distribución (`image_48329b.png`) lo confirman: las "cajas" (el rendimiento medio) de Solr están muy por encima de las de Milvus en todas las métricas de calidad.

### 2. 📈 Conclusión de Metodología: El *Chunking* de 5 Oraciones Funcionó

Nuestra hipótesis era que el *chunking* anterior (3 oraciones) era el cuello de botella. Esta prueba lo confirma al 100%.

* El ROUGE-L de Milvus saltó de un 3% a un **31%**.
* El ROUGE-L de Solr saltó de un 3% a un **42%**.

**Conclusión:** Arreglar el *chunking* arregló la calidad general del RAG. Los *chunks* de 5 oraciones proporcionan un contexto mucho mejor al LLM, permitiéndole (finalmente) generar respuestas correctas.

### 3. 🤔 ¿Por Qué Ganó Solr? (La Hipótesis Más Importante)

¿Por qué un buscador "tonto" (léxico) venció a un buscador "inteligente" (semántico) en un *test* conceptual?

La respuesta más probable es que nuestro modelo de *embeddings* es el eslabón débil.

Estamos usando `paraphrase-multilingual-MiniLM-L2-v2`, que es un modelo **pequeño y genérico**. Es muy probable que no entienda el vocabulario *altamente especializado y académico* de tu corpus. Para este modelo, las palabras "MAS", "paramilitarismo" y "autodefensa" pueden no ser semánticamente cercanas.

Solr (BM25) gana porque, aunque las preguntas eran "conceptuales", todavía compartían suficientes *palabras clave* (aunque fueran sinónimos o palabras raíz) con los *chunks* de 5 oraciones. Resulta que un *chunking* léxico bueno (Solr) superó a un *embedding* semántico pobre (Milvus).

### 4. ⚡ Conclusión de Latencia: La Búsqueda es Irrelevante

Este punto se confirma:

* **Latencia Total:** Ambos sistemas tardan ~4 segundos (`3.84s` vs `4.15s`).
* **Latencia de Recuperación:** Ambos son casi instantáneos (~4-5 milisegundos).

**Conclusión:** La latencia del buscador (Solr vs. Milvus) es completamente irrelevante para la experiencia del usuario. El 99.9% del tiempo de espera es la llamada a la API de Gemini.
