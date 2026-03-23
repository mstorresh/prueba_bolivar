# BPO-AI Microservicio

Microservicio de IA para automatización del proceso de gestión de solicitudes BPO.
Automatiza los pasos 1 al 6: validación, clasificación, prioridad, justificación,
enrutamiento y creación de caso externo.

---

## Requisitos

- Python 3.11+
- API Key de un proveedor LLM (Groq, OpenAI o Anthropic)

---

## Instalación local

```bash
git clone <url-del-repo>
cd bpo-ai-service
pip install -r requirements.txt
cp .env.default .env
# Editar .env con tu API key y proveedor LLM
```

---

## Variables de entorno

Edita el archivo `.env` con los siguientes valores:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `LLM_PROVIDER` | Proveedor LLM | `groq` |
| `LLM_API_KEY` | API Key del proveedor | `gsk_...` |
| `LLM_MODEL` | Modelo a usar | `llama3-8b-8192` |
| `APP_HOST` | Host del servidor | `0.0.0.0` |
| `APP_PORT` | Puerto del servidor | `8000` |

**Obtener API Key gratuita de Groq:** https://console.groq.com/keys

**Variables opcionales por empresa:**

| Variable | Empresa | Descripción |
|---|---|---|
| `MENSAJERIA_VALLE_PRIORITY_URL` | Mensajería del Valle | URL del microservicio de prioridad |

---

## Ejecutar el servicio

```bash
bash run_api.sh
```

El servicio queda disponible en: `http://localhost:8000`
Documentación interactiva: `http://localhost:8000/docs`

---

## Endpoints

### `POST /solicitudes/`
Procesa una solicitud ejecutando el pipeline completo.

**Request:**
```json
{
  "compania": "GASES DEL ORINOCO",
  "solicitud_id": "REQ-001",
  "solicitud_descripcion": "Mi nombre es Juana, CC 102045678. La estufa que compré hace 2 semanas presenta fallas urgentes en la llave del gas."
}
```

**Response:**
```json
{
  "compania": "GASES DEL ORINOCO",
  "solicitud_id": "REQ-001",
  "solicitud_fecha": "2026-02-06",
  "solicitud_tipo": "Incidente técnico",
  "solicitud_prioridad": "Alta",
  "solicitud_tipo_id_cliente": "CC",
  "solicitud_numero_id_cliente": "102045678",
  "solicitud_nombre_cliente": "Juana",
  "solicitud_id_plataforma_externa": "EXT-A1B2C3D4E5",
  "proximo_paso": "GESTION_EXTERNA",
  "justificacion": "Se detecta falla técnica en estufa de gas que requiere intervención presencial urgente.",
  "estado": "pendiente",
  "plataforma_error": false
}
```

### `GET /solicitudes/health`
Verifica el estado del servicio y lista las empresas configuradas.

---

## Agregar una nueva empresa

1. Crear el archivo `app/config/companies/<nombre_empresa>.yaml`
2. Seguir la estructura de `gases_del_orinoco.yaml`
3. Reiniciar el servicio

No se requiere modificar ningún archivo Python.

---

## Ejecutar tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Por paso
python tests/test_config_loader.py
python tests/test_validator.py
python tests/test_classifier.py
python tests/test_priority_engine.py
python tests/test_justification_and_next_step.py
python tests/test_pipeline_integration.py
```

---

## Estructura del proyecto

```
bpo-ai-service/
├── app/
│   ├── main.py                          # Entrypoint FastAPI
│   ├── api/
│   │   └── routes.py                    # Endpoints REST
│   ├── core/
│   │   ├── pipeline.py                  # Orquestador del flujo
│   │   ├── validator.py                 # Paso 1: Validación semántica
│   │   ├── classifier.py                # Paso 2: Clasificación
│   │   ├── priority_engine.py           # Paso 3: Motor de prioridad
│   │   ├── justification.py             # Paso 4: Justificación
│   │   ├── next_step_engine.py          # Paso 5: Siguiente paso
│   │   └── external_case.py             # Paso 6: Caso externo
│   ├── integrations/
│   │   ├── base_platform.py             # Interfaz abstracta
│   │   ├── mock_platform.py             # Plataforma simulada
│   │   └── platform_registry.py         # Registro de plataformas
│   ├── config/
│   │   ├── loader.py                    # Carga configs por empresa
│   │   └── companies/
│   │       ├── gases_del_orinoco.yaml
│   │       └── mensajeria_del_valle.yaml
│   ├── llm/
│   │   ├── client.py                    # Cliente LLM (Groq/OpenAI/Anthropic)
│   │   └── prompts.py                   # Prompts centralizados
│   └── models/
│       ├── enums.py                     # Enums compartidos
│       ├── internal_models.py           # Modelos internos del pipeline
│       └── request_models.py            # Modelos de API (input/output)
└── tests/
    ├── test_config_loader.py
    ├── test_validator.py
    ├── test_classifier.py
    ├── test_priority_engine.py
    ├── test_justification_and_next_step.py
    └── test_pipeline_integration.py
```