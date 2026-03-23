import logging
from fastapi import APIRouter, HTTPException, status
from app.core.pipeline import ejecutar_pipeline
from app.models.request_models import SolicitudInput, SolicitudOutput
from app.config.loader import CompanyNotFoundError, get_company_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])


@router.post(
    "/",
    response_model=SolicitudOutput,
    status_code=status.HTTP_200_OK,
    summary="Procesar una solicitud",
    description=(
        "Recibe una solicitud en texto libre y ejecuta el pipeline completo: "
        "validación, clasificación, prioridad, siguiente paso y creación de caso externo."
    ),
)
def procesar_solicitud(input_data: SolicitudInput) -> SolicitudOutput:
    """
    Procesa una solicitud BPO ejecutando el pipeline de 6 pasos.
    """
    logger.info(
        "POST /solicitudes | empresa='%s' | solicitud_id='%s'",
        input_data.compania,
        input_data.solicitud_id,
    )

    try:
        output = ejecutar_pipeline(input_data)
        return output

    except CompanyNotFoundError as e:
        logger.warning("Empresa no registrada: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "EMPRESA_NO_REGISTRADA",
                "mensaje": str(e),
                "empresas_disponibles": e.registered_companies,
            },
        )

    except Exception as e:
        logger.error("Error inesperado procesando solicitud: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ERROR_INTERNO",
                "mensaje": "Ocurrió un error procesando la solicitud. Intente nuevamente.",
            },
        )


@router.get(
    "/health",
    summary="Health check",
    description="Verifica que el servicio está activo y lista las empresas configuradas.",
)
def health_check():
    """Retorna el estado del servicio y empresas disponibles."""
    from pathlib import Path
    companies_dir = Path(__file__).parent.parent / "config" / "companies"
    empresas = [p.stem.upper().replace("_", " ") for p in companies_dir.glob("*.yaml")]

    return {
        "status": "ok",
        "empresas_configuradas": empresas,
    }