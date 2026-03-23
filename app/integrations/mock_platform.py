"""
Implementación mock de la plataforma externa.
Simula la creación de casos retornando un ID ficticio.
Se usa en desarrollo y pruebas. En producción se reemplaza
por un adaptador real (Salesforce, ServiceNow, etc.) sin tocar
ningún otro archivo — solo se registra en platform_registry.py.
"""
import uuid
import logging
from app.integrations.base_platform import PlataformaExternaBase, CasoExterno, ResultadoCasoExterno

logger = logging.getLogger(__name__)


class MockPlatform(PlataformaExternaBase):
    """
    Plataforma simulada para desarrollo y testing.
    Genera un ID único por caso y registra la operación en logs.
    """

    def nombre_plataforma(self) -> str:
        return "MockPlatform"

    def crear_caso(self, caso: CasoExterno) -> ResultadoCasoExterno:
        # Genera un ID ficticio que simula el formato de plataformas reales
        id_externo = f"EXT-{uuid.uuid4().hex[:10].upper()}"

        logger.info(
            "MockPlatform - Caso creado | id_externo='%s' | solicitud='%s' | "
            "empresa='%s' | categoria='%s' | prioridad='%s'",
            id_externo,
            caso.solicitud_id,
            caso.compania,
            caso.categoria,
            caso.prioridad,
        )

        return ResultadoCasoExterno(
            id_externo=id_externo,
            exitoso=True,
            mensaje=f"Caso creado exitosamente en {self.nombre_plataforma()}",
        )