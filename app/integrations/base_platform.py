from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CasoExterno:
    """Payload estándar para crear un caso en cualquier plataforma externa."""
    solicitud_id: str
    compania: str
    categoria: str
    prioridad: str
    descripcion: str
    nombre_cliente: str | None
    tipo_id: str | None
    numero_id: str | None
    justificacion: str


@dataclass
class ResultadoCasoExterno:
    """Resultado de crear un caso en la plataforma externa."""
    id_externo: str      
    exitoso: bool
    mensaje: str | None = None


class PlataformaExternaBase(ABC):
    """
    Interfaz que toda plataforma externa debe implementar.
    Para agregar una nueva plataforma: crear una clase que herede de esta
    e implementar crear_caso(). Luego registrarla en platform_registry.py.
    """

    @abstractmethod
    def crear_caso(self, caso: CasoExterno) -> ResultadoCasoExterno:
        """
        Crea un caso en la plataforma externa.
        Retorna el ID asignado por la plataforma y el estado de la operación.
        """
        ...

    @abstractmethod
    def nombre_plataforma(self) -> str:
        """Nombre identificador de la plataforma (para logs)."""
        ...