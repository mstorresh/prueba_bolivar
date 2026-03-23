# prueba_bolivar
Prueba tecnica para seguros bolivar

La idea es tener solo el branch main al final

bpo-ai-service/
│
├── app/
│   ├── main.py                  # Entrypoint FastAPI
│   ├── api/
│   │   └── routes.py            # Endpoints REST
│   │
│   ├── core/
│   │   ├── pipeline.py          # Orquestador del flujo completo
│   │   ├── validator.py         # Paso 1: Validación de información mínima
│   │   ├── classifier.py        # Paso 2: Clasificación del tipo de solicitud
│   │   ├── priority_engine.py   # Paso 3: Motor de prioridad (reglas + ext)
│   │   ├── next_step_engine.py  # Paso 5: Decisión del siguiente paso
│   │   └── justification.py    # Paso 4: Generación de justificación
│   │
│   ├── integrations/
│   │   ├── base_platform.py     # Interfaz abstracta para plataformas externas
│   │   ├── platform_registry.py # Registro de plataformas por empresa
│   │   ├── mock_platform_a.py   # Simulación plataforma empresa A
│   │   └── external_priority.py # Cliente para APIs de prioridad externas
│   │
│   ├── config/
│   │   ├── loader.py            # Carga configs por empresa
│   │   └── companies/
│   │       ├── gases_del_orinoco.yaml
│   │       ├── mensajeria_del_valle.yaml
│   │       └── ... (una por empresa)
│   │
│   ├── models/
│   │   ├── request_models.py    # Pydantic: input/output schemas
│   │   └── internal_models.py   # Modelos internos del pipeline
│   │
│   └── llm/
│       ├── client.py            # Abstracción del cliente LLM (Groq/OpenAI/etc)
│       └── prompts.py           # Todos los prompts centralizados
│
├── tests/
│   ├── test_validator.py
│   ├── test_classifier.py
│   ├── test_priority_engine.py
│   └── test_pipeline_integration.py
│
├── .env.example                 # Variables de entorno documentadas
├── requirements.txt
├── docker-compose.yml           # Para ejecución local fácil
└── README.md                    # Instrucciones de ejecución local