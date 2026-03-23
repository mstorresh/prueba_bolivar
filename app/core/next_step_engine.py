"""
Paso 5: Decisión del siguiente paso.

- GESTION_EXTERNA     → requiere atención del personal de la empresa
- RESPUESTA_DIRECTA   → el BPO puede resolver directamente
- Si la categoría no está en ninguna delegación → GESTION_EXTERNA por seguridad
"""
import logging
from app.config.loader import get_company_config
from app.models.internal_models import ContextoPipeline
from app.models.enums import ProximoPaso

logger = logging.getLogger(__name__)


def decidir_siguiente_paso(contexto: ContextoPipeline) -> ContextoPipeline:
    """
    Paso 5 del pipeline.

    Consulta las delegaciones del YAML de la empresa y decide si el caso
    requiere gestión externa o puede resolverse directamente.

    Si la categoría no está en ninguna lista de delegaciones, se asigna
    GESTION_EXTERNA como decisión conservadora (es mejor escalar que ignorar).
    """
    logger.info(
        "Paso 5 - Decidiendo siguiente paso para solicitud '%s'",
        contexto.solicitud_id,
    )

    config = get_company_config(contexto.compania)
    categoria = contexto.clasificacion.categoria if contexto.clasificacion else "Otro"
    delegaciones = config.delegaciones

    if categoria in delegaciones.gestion_externa:
        proximo_paso = ProximoPaso.GESTION_EXTERNA
    elif categoria in delegaciones.respuesta_directa:
        proximo_paso = ProximoPaso.RESPUESTA_DIRECTA
    else:
        # Categoría no mapeada: escalar por seguridad
        logger.warning(
            "Paso 5 - Categoría '%s' no está en ninguna delegación de '%s'. "
            "Asignando GESTION_EXTERNA por seguridad.",
            categoria, contexto.compania,
        )
        proximo_paso = ProximoPaso.GESTION_EXTERNA

    contexto.proximo_paso = proximo_paso
    logger.info("Paso 5 - Siguiente paso: '%s'", proximo_paso.value)
    return contexto