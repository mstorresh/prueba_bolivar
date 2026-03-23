"""
Enums compartidos entre modelos internos y modelos de API.
Separados para evitar dependencia circular.
"""
from enum import Enum


class ProximoPaso(str, Enum):
    GESTION_EXTERNA = "GESTION_EXTERNA"
    RESPUESTA_DIRECTA = "RESPUESTA_DIRECTA"
    CIERRE_POR_INFORMACION_INSUFICIENTE = "CIERRE_POR_INFORMACION_INSUFICIENTE"


class EstadoCaso(str, Enum):
    PENDIENTE = "pendiente"
    CERRADO = "cerrado"
    PENDIENTE_REINTENTO = "pendiente_reintento"


class Prioridad(str, Enum):
    ALTA = "Alta"
    MEDIA = "Media"
    BAJA = "Baja"