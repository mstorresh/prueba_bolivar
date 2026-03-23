"""
Tests para el config loader.
Verifica que las empresas se cargan correctamente y que los errores
se manejan de forma controlada.
"""
import pytest
import sys
from pathlib import Path

# Asegura que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.loader import get_company_config, CompanyNotFoundError


class TestConfigLoader:

    def setup_method(self):
        # Limpia cache entre tests para evitar estado compartido
        get_company_config.cache_clear()

    def test_carga_gases_del_orinoco(self):
        config = get_company_config("GASES DEL ORINOCO")
        assert config.empresa_id == "GASES_DEL_ORINOCO"
        assert "Incidente técnico" in config.categorias
        assert len(config.reglas_prioridad) > 0

    def test_carga_mensajeria_del_valle(self):
        config = get_company_config("MENSAJERIA DEL VALLE")
        assert config.empresa_id == "MENSAJERIA_DEL_VALLE"
        assert config.prioridad_externa.activa is True

    def test_empresa_no_registrada_lanza_error(self):
        with pytest.raises(CompanyNotFoundError) as exc_info:
            get_company_config("EMPRESA FANTASMA")
        assert "EMPRESA FANTASMA" in str(exc_info.value)

    def test_normalizacion_nombre_empresa(self):
        # Debe funcionar con mayúsculas, minúsculas, guiones
        config1 = get_company_config("GASES DEL ORINOCO")
        config2 = get_company_config("gases del orinoco")
        assert config1.empresa_id == config2.empresa_id

    def test_delegaciones_correctas_gases(self):
        config = get_company_config("GASES DEL ORINOCO")
        assert "Incidente técnico" in config.delegaciones.gestion_externa
        assert "Consulta de facturación" in config.delegaciones.respuesta_directa

    def test_cache_funciona(self):
        config1 = get_company_config("GASES DEL ORINOCO")
        config2 = get_company_config("GASES DEL ORINOCO")
        # Mismo objeto por cache
        assert config1 is config2