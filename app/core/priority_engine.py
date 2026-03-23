"""
Paso 3: Asignación de prioridad.

Dos estrategias según la configuración de la empresa:

1. Servicio externo (ej. Mensajería del Valle): se llama a un microservicio
   del cliente que retorna la prioridad. Si falla, se usa fallback local.

2. Reglas locales (ej. Gases del Orinoco): se evalúan las reglas del YAML
   en orden. Primero busca coincidencia por palabras clave, luego usa
   la prioridad_default de la categoría.

El resultado siempre indica la fuente: "servicio_externo", "reglas_locales" o "fallback".
"""
import logging
import json
import urllib.request
import urllib.error
from typing import Optional
from app.config.loader import get_company_config, CompanyConfig
from app.models.internal_models import ContextoPipeline, ResultadoPrioridad
from app.models.enums import Prioridad

logger = logging.getLogger(__name__)

EXTERNAL_SERVICE_TIMEOUT = 5.0


def asignar_prioridad(contexto: ContextoPipeline) -> ContextoPipeline:
    """
    Paso 3 del pipeline.

    Decide la prioridad usando el servicio externo del cliente si está
    configurado, o las reglas locales del YAML en caso contrario.
    Si el servicio externo falla, hace fallback a reglas locales.
    """
    logger.info(
        "Paso 3 - Asignando prioridad para solicitud '%s' de empresa '%s'",
        contexto.solicitud_id,
        contexto.compania,
    )

    config = get_company_config(contexto.compania)

    if config.prioridad_externa.activa:
        resultado = _asignar_con_servicio_externo(contexto, config)
    else:
        resultado = _asignar_con_reglas_locales(contexto, config)

    contexto.prioridad = resultado
    logger.info(
        "Paso 3 - Resultado: prioridad='%s' | fuente='%s'",
        resultado.prioridad.value,
        resultado.fuente,
    )
    return contexto


# ── Estrategia 1: Servicio externo ─────────────────────────────────────────────

def _asignar_con_servicio_externo(
    contexto: ContextoPipeline,
    config: CompanyConfig,
) -> ResultadoPrioridad:
    """
    Llama al microservicio externo del cliente para obtener la prioridad.
    Si falla por cualquier razón, hace fallback a reglas locales.
    """
    try:
        endpoint = config.prioridad_externa.get_endpoint()
        entidades = contexto.validacion.entidades if contexto.validacion else None
        payload = {
            "tipo_documento": entidades.tipo_id if entidades else None,
            "numero_documento": entidades.numero_id if entidades else None,
            "tipo_solicitud": contexto.clasificacion.categoria if contexto.clasificacion else None,
        }

        logger.info(
            "Paso 3 - Llamando servicio externo: %s | payload: %s",
            endpoint, payload,
        )

        data = http_post_json(endpoint, payload)
        prioridad_str = data.get("prioridad", "").strip()
        prioridad = _parse_prioridad(prioridad_str)

        if prioridad is None:
            raise ValueError(f"Prioridad inválida del servicio externo: '{prioridad_str}'")

        logger.info("Paso 3 - Servicio externo retornó prioridad '%s'", prioridad_str)
        return ResultadoPrioridad(prioridad=prioridad, fuente="servicio_externo")

    except Exception as e:
        logger.warning(
            "Paso 3 - Servicio externo falló para '%s': %s. "
            "Aplicando fallback a reglas locales.",
            contexto.solicitud_id, e,
        )
        resultado = _asignar_con_reglas_locales(contexto, config)
        return ResultadoPrioridad(prioridad=resultado.prioridad, fuente="fallback")


# ── Estrategia 2: Reglas locales ───────────────────────────────────────────────

def _asignar_con_reglas_locales(
    contexto: ContextoPipeline,
    config: CompanyConfig,
) -> ResultadoPrioridad:
    """
    Evalúa las reglas del YAML en orden:
    1. Filtra reglas de la categoría clasificada.
    2. Busca coincidencia por palabras clave en la descripción.
    3. Si no hay coincidencia, usa prioridad_default de la categoría.
    4. Si no hay ninguna regla para esa categoría, asigna Media.
    """
    categoria = contexto.clasificacion.categoria if contexto.clasificacion else "Otro"
    descripcion = contexto.solicitud_descripcion.lower()

    reglas_categoria = [
        r for r in config.reglas_prioridad
        if r.categoria == categoria
    ]

    if not reglas_categoria:
        logger.warning(
            "Paso 3 - Sin reglas para categoría '%s' en '%s'. Usando Media.",
            categoria, contexto.compania,
        )
        return ResultadoPrioridad(prioridad=Prioridad.MEDIA, fuente="reglas_locales")

    # Primero: palabras clave
    for regla in reglas_categoria:
        if regla.palabras_clave:
            if any(palabra.lower() in descripcion for palabra in regla.palabras_clave):
                prioridad = _parse_prioridad(regla.prioridad) or Prioridad.MEDIA
                logger.info(
                    "Paso 3 - Palabras clave coinciden en '%s'. Prioridad: %s",
                    categoria, prioridad.value,
                )
                return ResultadoPrioridad(prioridad=prioridad, fuente="reglas_locales")

    # Segundo: default de categoría
    for regla in reglas_categoria:
        if regla.prioridad_default:
            prioridad = _parse_prioridad(regla.prioridad_default) or Prioridad.MEDIA
            return ResultadoPrioridad(prioridad=prioridad, fuente="reglas_locales")

    return ResultadoPrioridad(prioridad=Prioridad.MEDIA, fuente="reglas_locales")


# ── HTTP helper (mockeable en tests) ──────────────────────────────────────────

def http_post_json(url: str, payload: dict) -> dict:
    """
    Hace un POST JSON a una URL y retorna la respuesta como dict.
    Usa httpx si está disponible (producción), urllib como fallback.
    Función separada para facilitar mocking en tests.
    """
    try:
        import httpx
        response = httpx.post(url, json=payload, timeout=EXTERNAL_SERVICE_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except ImportError:
        pass

    # Fallback con urllib (siempre disponible)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=EXTERNAL_SERVICE_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Helper ────────────────────────────────────────────────────────────────────

def _parse_prioridad(valor: Optional[str]) -> Optional[Prioridad]:
    """Convierte un string a enum Prioridad. Retorna None si no es válido."""
    if not valor:
        return None
    mapa = {
        "alta": Prioridad.ALTA,
        "media": Prioridad.MEDIA,
        "baja": Prioridad.BAJA,
    }
    return mapa.get(valor.lower())