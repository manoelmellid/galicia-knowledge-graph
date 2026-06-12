```
# Knowledge Graph de Galicia — Patrimonio e Espazos Naturais

Aplicación web de explotación do Knowledge Graph do patrimonio natural e cultural de Galicia e norte de Portugal, construído seguindo a metodoloxía LOT4KG.

## Estrutura do proxecto

```
├── README.md                     # Documentación principal do proxecto
├── .env                          # Variables de contorna (OPENAI_API_KEY, etc.)
│
├── deploy/                       # Cartafol contenedor para o despregue da App
│   ├── app.py                    # Punto de entrada de Streamlit
│   ├── requirements.txt          # Dependencias do proxecto
│   ├── kg/                       # Grafo e Ontoloxía (fontes de datos da App)
│   │   ├── output.nt             # KG materializado final (usado pola App)
│   │   └── ontologia.ttl         # Ontoloxía OWL do dominio
│   ├── pages/                    # Módulos de interface de Streamlit
│   │   ├── chat.py               # Chatbot RAG con LLM
│   │   ├── mapa.py               # Mapa interactivo e buscador por radio
│   │   ├── sparql.py             # Explorador SPARQL libre
│   │   └── wikidata.py           # Enriquecemento federado en tempo real
│   ├── utils/                    # Lóxica de backend
│   │   ├── rag_engine.py         # Motor RAG: intent detection + context injection
│   │   └── sparql_queries.py     # Biblioteca de queries e utilidades rdflib
│   └── config/                   # Configuración da construción do KG
│       ├── prepare_csvs.py       # Script inicial de limpeza
│       ├── mappings/             # Definicións de mapeo (YARRRML, RML, ini)
│       │   ├── mapping_final.yarrrml.yaml
│       │   ├── mapping.rml.ttl
│       │   └── config.ini         # Configuración para Morph-KGC
│       └── data/                 # Fontes de datos CSV
│           ├── *.csv             # CSVs orixinais de patrimonio
│           └── clean/            # CSVs procesados e catálogos unificados
│
├── src/                          # Scripts de procesamento e explotación fóra de deploy
│   ├── federated_wikidata.py     # Script para xeración de resultados enriquecidos
│   ├── fix_catalogs.py           # Reparación e unificación de catálogos de concellos
│   └── step_final.py             # Enriquecemento final de CSVs con identificadores
│
├── queries/                      # Almacén de consultas SPARQL (.rq)
│   ├── local_query_*.rq          # Consultas ao KG local
│   └── federated_query_*.rq      # Consultas federadas (KG + Wikidata)
│
├── results/                      # Artefactos xerados na explotación
│   ├── query_results/            # Exportacións CSV (p.ex. enriched_concellos.csv)
│   ├── maps/                     # Mapas HTML estáticos (Folium)
│   └── figures/                  # Gráficos de análise de datos (PNG)
└── .gitignore
```

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración

Crea un ficheiro `.env` na raíz do proxecto:

```
OPENAI_API_KEY=sk-...
```

## Executar

```bash
streamlit run deploy/app.py
```

## Reproducir o KG desde cero

```bash
# 1. Limpar e preparar os CSVs (Rutas corrixidas ao cartafol deploy)
python deploy/config/prepare_csvs.py
python src/fix_catalogs.py
python src/step_final.py

# 2. Xerar o mapping RML
yatter -i deploy/config/mappings/mapping_final.yarrrml.yaml -o deploy/config/mappings/mapping.rml.ttl

# 3. Materializar o KG (Morph-KGC necesita a ruta ao .ini)
python -m morph_kgc deploy/config/mappings/config.ini

# 4. Xerar resultados da explotación federada
python src/federated_wikidata.py
```

## Páxinas da aplicación

### 🗺️ Mapa & Buscador
Visualiza os ~2.000 PDIs do KG nun mapa interactivo con capas filtrables por tipo. Permite seleccionar calquera PDI como punto de partida e buscar elementos nun radio configurable usando distancia Haversine real.

### 💬 Asistente IA
Chatbot con RAG sobre o KG. O LLM detecta o intent da pregunta, o sistema lanza a query SPARQL correspondente ao KG local, e os resultados reais pásanse como contexto ao LLM para xerar a resposta. Soporta galego, castelán e inglés.

### 📊 Explorador SPARQL
Editor libre de queries SPARQL contra o KG local con 8 exemplos precargados, táboa de resultados descargable en CSV e mapa automático cando os resultados conteñen coordenadas.

### 🔗 Wikidata
Explotación federada: extrae os enlaces `owl:sameAs` do KG e consulta Wikidata para enriquecer as praias con Bandeira Azul (lonxitude oficial, imaxe, nome en galego) e os concellos (poboación, superficie, web oficial).

## Tarea 6 — Explotación do Knowledge Graph

### Consultas SPARQL locais
As queries en `queries/local_query_*.rq` permiten responder preguntas sobre once fontes de datos distintas cunha soa consulta, respetando a xerarquía PDI → Concello → Provincia → País definida na ontoloxía.

### Consultas federadas con Wikidata
O grafo contén enlaces `owl:sameAs` a Wikidata para todas as praias con Bandeira Azul e para os concellos con código INE. As queries en `queries/federated_query_*.rq` usan eses enlaces para recuperar datos externos non presentes nos CSVs orixinais. O campo `delta_coord` nos resultados mide a desviación entre as coordenadas do KG e as de Wikidata como indicador de calidade de datos.

### Valor da explotación
SPARQL permite consultar once fontes unificadas como se foran unha soa, respetando a xerarquía ontolóxica. A federación con Wikidata achega datos que non estaban nos CSVs orixinais. Os mapas converten listas de coordenadas en información accionable. O LLM elimina a barreira de entrada para usuarios sen coñecementos de SPARQL, respondendo con datos reais do KG en lugar do coñecemento xeral do modelo.

## Clases da ontoloxía

| Clase | Descrición |
|---|---|
| `gamere:Praia` | Praias de mar e fluviais |
| `gamere:CastilloEmprazamento` | Castelos, pazos, zonas militares |
| `gamere:FervenzaAuga` | Fervenzas, ríos, lagos, encoros |
| `gamere:IgrexaRelixiosa` | Igrexas, santuarios, ermidas |
| `gamere:ConstrucionTradicional` | Muíños, hórreos, cruceiros, aldeas |
| `gamere:MonasterioCovento` | Mosteiros e conventos |
| `gamere:EspazoNatural` | Montañas, miradoiros, cabos, parques |
| `gamere:OutrosPDI` | Outros puntos de interese |
| `gamere:Ponte` | Pontes, pontellas, poldras |
| `gamere:XacementoArqueoloxco` | Xacementos arqueolóxicos |

## Tecnoloxías

- **Ontoloxía**: OWL/RDF (Turtle), modelada con Chowlk, documentada con OnToology
- **Mappings**: YARRRML → RML con Yatter
- **Materialización**: Morph-KGC
- **Validación**: SHACL con pySHACL
- **Consultas**: rdflib, SPARQLWrapper
- **Aplicación**: Streamlit, Folium, OpenAI API
```