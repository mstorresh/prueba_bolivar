import logging
from app.llm.client import get_llm_client, LLMParseError
from app.llm.prompts import VALIDACION_SYSTEM, validacion_user_prompt
from app.models.internal_models import (
    ContextoPipeline,
    ResultadoValidacion,
    EntidadesExtraidas,
)

logger = logging.getLogger(__name__)


def validar_solicitud(contexto: ContextoPipeline) -> ContextoPipeline:
    """
    Paso 1 del pipeline.

    Llama al LLM para:
    - Determinar si la solicitud tiene información mínima (qué, quién).
    - Extraer entidades: nombre del cliente, tipo y número de documento.

    Modifica contexto.validacion y retorna el contexto actualizado.
    Si ocurre un error con el LLM, hace fallback a validación básica por longitud.
    """
    logger.info(
        "Paso 1 - Validando solicitud '%s' para empresa '%s'",
        contexto.solicitud_id,
        contexto.compania,
    )

    try:
        resultado = _validar_con_llm(contexto.solicitud_descripcion)
    except LLMParseError as e:
        logger.warning(
            "Paso 1 - LLM retornó JSON inválido para '%s'. "
            "Aplicando fallback por longitud. Error: %s",
            contexto.solicitud_id, e,
        )
        resultado = _fallback_validacion(contexto.solicitud_descripcion)
    except Exception as e:
        logger.error(
            "Paso 1 - Error inesperado en validación de '%s': %s",
            contexto.solicitud_id, e,
        )
        resultado = _fallback_validacion(contexto.solicitud_descripcion)

    contexto.validacion = resultado
    logger.info(
        "Paso 1 - Resultado: es_valida=%s | razon='%s'",
        resultado.es_valida,
        resultado.razon,
    )
    return contexto


def _validar_con_llm(descripcion: str) -> ResultadoValidacion:
    """Llama al LLM y parsea la respuesta en un ResultadoValidacion."""
    client = get_llm_client()
    data = client.complete_json(
        system_prompt=VALIDACION_SYSTEM,
        user_prompt=validacion_user_prompt(descripcion),
    )

    entidades = EntidadesExtraidas(
        nombre_cliente=data.get("entidades", {}).get("nombre_cliente"),
        tipo_id=data.get("entidades", {}).get("tipo_id"),
        numero_id=data.get("entidades", {}).get("numero_id"),
    )

    return ResultadoValidacion(
        es_valida=bool(data.get("es_valida", False)),
        razon=str(data.get("razon", "Sin razón provista por el modelo")),
        entidades=entidades,
    )


def _fallback_validacion(descripcion: str) -> ResultadoValidacion:
    """
    Validación de respaldo cuando el LLM no está disponible o falla.
    Usa heurísticas simples: longitud mínima y presencia de palabras clave básicas.
    Es mejor aceptar con duda que rechazar una solicitud válida.
    """
    descripcion_limpia = descripcion.strip()
    es_valida = len(descripcion_limpia) >= 30

    return ResultadoValidacion(
        es_valida=es_valida,
        razon=(
            "Validación automática (servicio LLM no disponible): "
            "la solicitud tiene longitud suficiente."
            if es_valida
            else "Validación automática: texto demasiado corto o vacío."
        ),
        entidades=EntidadesExtraidas(),
    )