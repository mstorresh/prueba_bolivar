import logging
from app.llm.client import get_llm_client, LLMParseError
from app.llm.prompts import JUSTIFICACION_SYSTEM, justificacion_user_prompt
from app.models.internal_models import ContextoPipeline

logger = logging.getLogger(__name__)


def generar_justificacion(contexto: ContextoPipeline) -> ContextoPipeline:
    """
    Paso 4 del pipeline.

    Genera una justificación en lenguaje natural usando la categoría
    y prioridad ya decididas. El LLM no toma decisiones aquí,
    solo redacta con los hechos consumados de los pasos anteriores.

    Si falla, usa un texto de justificación genérico como fallback.
    """
    logger.info(
        "Paso 4 - Generando justificación para solicitud '%s'",
        contexto.solicitud_id,
    )

    try:
        justificacion = _generar_con_llm(contexto)
    except (LLMParseError, Exception) as e:
        logger.warning(
            "Paso 4 - LLM falló generando justificación para '%s': %s. "
            "Usando justificación genérica.",
            contexto.solicitud_id, e,
        )
        justificacion = _fallback_justificacion(contexto)

    contexto.justificacion = justificacion
    logger.info("Paso 4 - Justificación generada: '%s'", justificacion)
    return contexto


def _generar_con_llm(contexto: ContextoPipeline) -> str:
    """Llama al LLM y extrae el texto de justificación."""
    nombre = (
        contexto.validacion.entidades.nombre_cliente
        if contexto.validacion and contexto.validacion.entidades
        else None
    )
    categoria = contexto.clasificacion.categoria if contexto.clasificacion else "No clasificado"
    prioridad = contexto.prioridad.prioridad.value if contexto.prioridad else "Media"

    client = get_llm_client()
    data = client.complete_json(
        system_prompt=JUSTIFICACION_SYSTEM,
        user_prompt=justificacion_user_prompt(
            descripcion=contexto.solicitud_descripcion,
            categoria=categoria,
            prioridad=prioridad,
            nombre_cliente=nombre,
        ),
    )
    return str(data.get("justificacion", "")).strip()


def _fallback_justificacion(contexto: ContextoPipeline) -> str:
    """Justificación genérica cuando el LLM no está disponible."""
    categoria = contexto.clasificacion.categoria if contexto.clasificacion else "solicitud"
    prioridad = contexto.prioridad.prioridad.value if contexto.prioridad else "Media"
    return (
        f"Solicitud clasificada como '{categoria}' con prioridad {prioridad} "
        f"según las reglas operativas de la empresa."
    )