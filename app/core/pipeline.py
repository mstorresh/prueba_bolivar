import logging
from datetime import date
from app.models.internal_models import ContextoPipeline
from app.models.request_models import SolicitudInput, SolicitudOutput
from app.models.enums import ProximoPaso, EstadoCaso
from app.core.validator import validar_solicitud
from app.core.classifier import clasificar_solicitud
from app.core.priority_engine import asignar_prioridad
from app.core.justification import generar_justificacion
from app.core.next_step_engine import decidir_siguiente_paso
from app.core.external_case import crear_caso_externo

logger = logging.getLogger(__name__)


def ejecutar_pipeline(input_data: SolicitudInput) -> SolicitudOutput:
    """
    Ejecuta el pipeline completo para una solicitud.

    Flujo:
    1. Validación semántica (LLM)
       → Si inválida: cortocircuito, retorna CIERRE_POR_INFORMACION_INSUFICIENTE
    2. Clasificación (LLM)
    3. Asignación de prioridad (reglas o servicio externo)
    4. Generación de justificación (LLM)
    5. Decisión del siguiente paso (reglas)
    6. Creación de caso externo si aplica (adaptador)
    """
    logger.info(
        "Pipeline iniciado | solicitud='%s' | empresa='%s'",
        input_data.solicitud_id,
        input_data.compania,
    )

    # Inicializa el contexto que viajará por todo el pipeline
    contexto = ContextoPipeline(
        compania=input_data.compania,
        solicitud_id=input_data.solicitud_id,
        solicitud_descripcion=input_data.solicitud_descripcion,
    )

    # ── Paso 1: Validación ─────────────────────────────────────────────────────
    contexto = validar_solicitud(contexto)

    if not contexto.validacion.es_valida:
        logger.info(
            "Pipeline cortocircuitado | solicitud='%s' | razon='%s'",
            input_data.solicitud_id,
            contexto.validacion.razon,
        )
        return _construir_output(
            contexto=contexto,
            proximo_paso=ProximoPaso.CIERRE_POR_INFORMACION_INSUFICIENTE,
            justificacion=f"Información incompleta o faltante: {contexto.validacion.razon}",
            estado=EstadoCaso.CERRADO,
        )

    # ── Paso 2: Clasificación ──────────────────────────────────────────────────
    contexto = clasificar_solicitud(contexto)

    # ── Paso 3: Prioridad ──────────────────────────────────────────────────────
    contexto = asignar_prioridad(contexto)

    # ── Paso 4: Justificación ──────────────────────────────────────────────────
    contexto = generar_justificacion(contexto)

    # ── Paso 5: Siguiente paso ─────────────────────────────────────────────────
    contexto = decidir_siguiente_paso(contexto)

    # ── Paso 6: Caso externo (solo si aplica) ──────────────────────────────────
    contexto = crear_caso_externo(contexto)

    # ── Construir estado final ─────────────────────────────────────────────────
    estado = _determinar_estado(contexto)

    logger.info(
        "Pipeline completado | solicitud='%s' | paso='%s' | estado='%s'",
        input_data.solicitud_id,
        contexto.proximo_paso.value,
        estado.value,
    )

    return _construir_output(
        contexto=contexto,
        proximo_paso=contexto.proximo_paso,
        justificacion=contexto.justificacion or "",
        estado=estado,
    )


def _determinar_estado(contexto: ContextoPipeline) -> EstadoCaso:
    """Determina el estado final del caso según el resultado del pipeline."""
    if contexto.plataforma_error:
        return EstadoCaso.PENDIENTE_REINTENTO
    if contexto.proximo_paso == ProximoPaso.RESPUESTA_DIRECTA:
        return EstadoCaso.CERRADO
    return EstadoCaso.PENDIENTE


def _construir_output(
    contexto: ContextoPipeline,
    proximo_paso: ProximoPaso,
    justificacion: str,
    estado: EstadoCaso,
) -> SolicitudOutput:
    """Construye el objeto de respuesta a partir del contexto del pipeline."""
    entidades = (
        contexto.validacion.entidades
        if contexto.validacion and contexto.validacion.entidades
        else None
    )

    return SolicitudOutput(
        compania=contexto.compania,
        solicitud_id=contexto.solicitud_id,
        solicitud_fecha=date.today(),
        solicitud_tipo=contexto.clasificacion.categoria if contexto.clasificacion else None,
        solicitud_prioridad=contexto.prioridad.prioridad if contexto.prioridad else None,
        solicitud_tipo_id_cliente=entidades.tipo_id if entidades else None,
        solicitud_numero_id_cliente=entidades.numero_id if entidades else None,
        solicitud_nombre_cliente=entidades.nombre_cliente if entidades else None,
        solicitud_id_plataforma_externa=contexto.id_plataforma_externa,
        proximo_paso=proximo_paso,
        justificacion=justificacion,
        estado=estado,
        plataforma_error=contexto.plataforma_error,
    )