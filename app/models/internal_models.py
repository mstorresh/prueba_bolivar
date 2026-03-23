
from dataclasses import dataclass, field
from typing import Optional
from app.models.enums import Prioridad, ProximoPaso


@dataclass
class EntidadesExtraidas:
    """Entidades que el LLM extrae del texto libre."""
    nombre_cliente: Optional[str] = None
    tipo_id: Optional[str] = None        # CC, NIT, CE, etc.
    numero_id: Optional[str] = None


@dataclass
class ResultadoValidacion:
    es_valida: bool
    razon: str
    entidades: EntidadesExtraidas = field(default_factory=EntidadesExtraidas)


@dataclass
class ResultadoClasificacion:
    categoria: str
    confianza: Optional[str] = None  # "alta" | "media" | "baja"


@dataclass
class ResultadoPrioridad:
    prioridad: Prioridad
    fuente: str  # "reglas_locales" | "servicio_externo" | "fallback"


@dataclass
class ContextoPipeline:
    """
    Objeto que viaja por todo el pipeline acumulando resultados.
    Cada paso lee lo que necesita y escribe su resultado.
    """
    # Input original
    compania: str
    solicitud_id: str
    solicitud_descripcion: str

    # Resultados por paso (se van llenando)
    validacion: Optional[ResultadoValidacion] = None
    clasificacion: Optional[ResultadoClasificacion] = None
    prioridad: Optional[ResultadoPrioridad] = None
    justificacion: Optional[str] = None
    proximo_paso: Optional[ProximoPaso] = None
    id_plataforma_externa: Optional[str] = None
    plataforma_error: bool = False