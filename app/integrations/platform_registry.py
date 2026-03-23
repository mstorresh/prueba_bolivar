"""
Registro de plataformas externas disponibles.

Para agregar una nueva plataforma:
1. Crear la clase en un nuevo archivo (ej. salesforce_platform.py)
2. Importarla aquí
3. Agregarla al dict _REGISTRY con su clave

Ningún otro archivo necesita modificarse.
"""
import logging
from app.integrations.base_platform import PlataformaExternaBase
from app.integrations.mock_platform import MockPlatform

logger = logging.getLogger(__name__)

# Registro: clave del YAML → clase de plataforma
_REGISTRY: dict[str, type[PlataformaExternaBase]] = {
    "mock_platform_default": MockPlatform,
    # "salesforce": SalesforcePlatform,
    # "servicenow": ServiceNowPlatform,
}

# Cache de instancias para no crear una nueva por cada request
_instances: dict[str, PlataformaExternaBase] = {}


def get_platform(tipo: str) -> PlataformaExternaBase:
    """
    Retorna la instancia de plataforma correspondiente al tipo configurado.
    Lanza PlatformNotFoundError si el tipo no está registrado.
    """
    if tipo not in _instances:
        if tipo not in _REGISTRY:
            raise PlatformNotFoundError(
                f"Plataforma '{tipo}' no está registrada. "
                f"Plataformas disponibles: {list(_REGISTRY.keys())}"
            )
        _instances[tipo] = _REGISTRY[tipo]()
        logger.info("Platform registry - Instancia creada para plataforma '%s'", tipo)

    return _instances[tipo]


class PlatformNotFoundError(Exception):
    pass