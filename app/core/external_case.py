"""
Paso 6: Creación del caso en la plataforma externa.

Solo se ejecuta si el siguiente paso es GESTION_EXTERNA.
Usa el registro de plataformas para obtener el adaptador correcto
según la configuración de la empresa, y crea el caso.

Si la plataforma falla, el estado queda como PENDIENTE_REINTENTO
y se registra el error para monitoreo.
"""
import logging
from app.config.loader import get_company_config
from app.integrations.platform_registry import get_platform
from app.integrations.base_platform import CasoExterno
from app.models.internal_models import ContextoPipeline
from app.models.enums import ProximoPaso

logger = logging.getLogger(__name__)


def crear_caso_externo(contexto: ContextoPipeline) -> ContextoPipeline:
    """
    Paso 6 del pipeline.

    Si el siguiente paso es GESTION_EXTERNA, crea el caso en la
    plataforma externa configurada para la empresa.
    Si no aplica (RESPUESTA_DIRECTA o CIERRE), retorna sin hacer nada.
    """
    if contexto.proximo_paso != ProximoPaso.GESTION_EXTERNA:
        logger.info(
            "Paso 6 - No aplica para solicitud '%s' (siguiente paso: %s)",
            contexto.solicitud_id,
            contexto.proximo_paso.value if contexto.proximo_paso else "None",
        )
        return contexto

    logger.info(
        "Paso 6 - Creando caso externo para solicitud '%s' en empresa '%s'",
        contexto.solicitud_id,
        contexto.compania,
    )

    try:
        config = get_company_config(contexto.compania)
        plataforma = get_platform(config.plataforma_externa.tipo)

        entidades = contexto.validacion.entidades if contexto.validacion else None
        caso = CasoExterno(
            solicitud_id=contexto.solicitud_id,
            compania=contexto.compania,
            categoria=contexto.clasificacion.categoria if contexto.clasificacion else "Otro",
            prioridad=contexto.prioridad.prioridad.value if contexto.prioridad else "Media",
            descripcion=contexto.solicitud_descripcion,
            nombre_cliente=entidades.nombre_cliente if entidades else None,
            tipo_id=entidades.tipo_id if entidades else None,
            numero_id=entidades.numero_id if entidades else None,
            justificacion=contexto.justificacion or "",
        )

        resultado = plataforma.crear_caso(caso)

        if resultado.exitoso:
            contexto.id_plataforma_externa = resultado.id_externo
            logger.info(
                "Paso 6 - Caso creado exitosamente | id_externo='%s' | plataforma='%s'",
                resultado.id_externo,
                plataforma.nombre_plataforma(),
            )
        else:
            raise RuntimeError(f"La plataforma rechazó el caso: {resultado.mensaje}")

    except Exception as e:
        logger.error(
            "Paso 6 - Error creando caso externo para '%s': %s. "
            "Estado quedará como PENDIENTE_REINTENTO.",
            contexto.solicitud_id, e,
        )
        contexto.plataforma_error = True

    return contexto