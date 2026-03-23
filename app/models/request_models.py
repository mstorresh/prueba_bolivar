from typing import Optional
from datetime import date
from app.models.enums import ProximoPaso, EstadoCaso, Prioridad

try:
    from pydantic import BaseModel, Field

    class SolicitudInput(BaseModel):
        compania: str = Field(..., description="Nombre de la empresa cliente")
        solicitud_id: str = Field(..., description="Identificador único de la solicitud")
        solicitud_descripcion: str = Field(
            ..., min_length=10,
            description="Texto libre con la descripción de la solicitud",
        )

        model_config = {
            "json_schema_extra": {
                "example": {
                    "compania": "GASES DEL ORINOCO",
                    "solicitud_id": "REQ-001",
                    "solicitud_descripcion": (
                        "Mi nombre es Juana y mi número de cédula es 102045678. "
                        "Solicito una revisión urgente porque la estufa que compré "
                        "hace 2 semanas presenta fallas."
                    ),
                }
            }
        }

    class SolicitudOutput(BaseModel):
        compania: str
        solicitud_id: str
        solicitud_fecha: date
        solicitud_tipo: Optional[str] = None
        solicitud_prioridad: Optional[Prioridad] = None
        solicitud_tipo_id_cliente: Optional[str] = None
        solicitud_numero_id_cliente: Optional[str] = None
        solicitud_nombre_cliente: Optional[str] = None
        solicitud_id_plataforma_externa: Optional[str] = None
        proximo_paso: ProximoPaso
        justificacion: str
        estado: EstadoCaso
        plataforma_error: bool = False

except ImportError:
    # En entornos sin Pydantic (tests locales), se definen como clases simples
    class SolicitudInput:  # type: ignore
        def __init__(self, compania, solicitud_id, solicitud_descripcion):
            self.compania = compania
            self.solicitud_id = solicitud_id
            self.solicitud_descripcion = solicitud_descripcion

    class SolicitudOutput:  # type: ignore
        pass
    """
    ejemplo:
            {
        "compania": "GASES DEL ORINOCO",
        “solicitud_id": "REQ-001",
        “Solicitud_fecha”: 2026-02-06,
        "solicitud_tipo": "Incidente técnico",
        "solicitud_prioridad": "Alta",
        "solicitud_id_cliente": "CC",
        "solicitud_tipo_id_cliente": "102045678",
        “solicitud_id_plataforma_externa": "ID123456789",
        "proximo_paso": “GESTIÓN EXTERNA”,
        "justificacion": "Se detecta falla técnica en estufa de gas que requiere intervención presencial (delegacion externa).",
        "estado": “pendiente”,
        }
    """
    
    