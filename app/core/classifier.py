import logging
from app.llm.client import get_llm_client, LLMParseError
from app.llm.prompts import CLASIFICACION_SYSTEM, clasificacion_user_prompt
from app.models.internal_models import ContextoPipeline, ResultadoClasificacion
from app.config.loader import get_company_config

logger = logging.getLogger(__name__)


def clasificar_solicitud(contexto: ContextoPipeline) -> ContextoPipeline:
    """
    Paso 2 del pipeline.

    Clasifica la solicitud en una categoría operativa usando el LLM.
    Las categorías válidas se leen del YAML de la empresa, por lo que
    el LLM nunca puede inventar una categoría que no esté configurada.

    Si el LLM devuelve una categoría inválida o falla, se aplica fallback
    asignando la categoría "Otro" si existe, o la primera categoría disponible.
    """
    logger.info(
        "Paso 2 - Clasificando solicitud '%s' para empresa '%s'",
        contexto.solicitud_id,
        contexto.compania,
    )

    config = get_company_config(contexto.compania)
    categorias = config.categorias

    try:
        resultado = _clasificar_con_llm(contexto.solicitud_descripcion, categorias)

        # Validar que la categoría retornada sea una de las permitidas
        if resultado.categoria not in categorias:
            logger.warning(
                "Paso 2 - LLM retornó categoría inválida '%s' para empresa '%s'. "
                "Categorías válidas: %s. Aplicando fallback.",
                resultado.categoria, contexto.compania, categorias,
            )
            resultado = _fallback_clasificacion(categorias)

    except LLMParseError as e:
        logger.warning(
            "Paso 2 - LLM retornó JSON inválido para '%s'. "
            "Aplicando fallback. Error: %s",
            contexto.solicitud_id, e,
        )
        resultado = _fallback_clasificacion(categorias)

    except Exception as e:
        logger.error(
            "Paso 2 - Error inesperado clasificando '%s': %s",
            contexto.solicitud_id, e,
        )
        resultado = _fallback_clasificacion(categorias)

    contexto.clasificacion = resultado
    logger.info(
        "Paso 2 - Resultado: categoria='%s' | confianza='%s'",
        resultado.categoria,
        resultado.confianza,
    )
    return contexto


def _clasificar_con_llm(
    descripcion: str,
    categorias: list[str],
) -> ResultadoClasificacion:
    """Llama al LLM y parsea la respuesta en un ResultadoClasificacion."""
    client = get_llm_client()
    data = client.complete_json(
        system_prompt=CLASIFICACION_SYSTEM,
        user_prompt=clasificacion_user_prompt(descripcion, categorias),
    )

    return ResultadoClasificacion(
        categoria=str(data.get("categoria", "")).strip(),
        confianza=data.get("confianza"),
    )


def _fallback_clasificacion(categorias: list[str]) -> ResultadoClasificacion:
    """
    Clasificación de respaldo cuando el LLM no está disponible o falla.
    Prioriza 'Otro' si existe, si no usa la primera categoría disponible.
    """
    categoria = "Otro" if "Otro" in categorias else categorias[0]
    return ResultadoClasificacion(
        categoria=categoria,
        confianza="baja",
    )