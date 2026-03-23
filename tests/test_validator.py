import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.internal_models import ContextoPipeline
from app.core.validator import validar_solicitud
from app.llm.client import LLMParseError


def _make_contexto(descripcion: str) -> ContextoPipeline:
    return ContextoPipeline(
        compania="GASES DEL ORINOCO",
        solicitud_id="REQ-TEST-001",
        solicitud_descripcion=descripcion,
    )


def _mock_llm_response(data: dict):
    """Crea un mock del LLM que retorna el dict dado como JSON."""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = data
    return mock_client


class TestValidador:

    def test_solicitud_valida_con_entidades(self):
        """Solicitud completa: válida y con entidades extraídas."""
        mock_respuesta = {
            "es_valida": True,
            "razon": "La solicitud describe un problema técnico con fecha y datos del cliente.",
            "entidades": {
                "nombre_cliente": "Juana Pérez",
                "tipo_id": "CC",
                "numero_id": "102045678",
            },
        }
        with patch("app.core.validator.get_llm_client", return_value=_mock_llm_response(mock_respuesta)):
            ctx = _make_contexto(
                "Mi nombre es Juana Pérez, CC 102045678. "
                "Hace 2 días mi estufa presenta fallas en la llave del gas."
            )
            ctx = validar_solicitud(ctx)

        assert ctx.validacion.es_valida is True
        assert ctx.validacion.entidades.nombre_cliente == "Juana Pérez"
        assert ctx.validacion.entidades.tipo_id == "CC"
        assert ctx.validacion.entidades.numero_id == "102045678"

    def test_solicitud_invalida_sin_descripcion(self):
        """Solicitud vacía: inválida."""
        mock_respuesta = {
            "es_valida": False,
            "razon": "El texto no describe ningún problema ni solicitud concreta.",
            "entidades": {"nombre_cliente": None, "tipo_id": None, "numero_id": None},
        }
        with patch("app.core.validator.get_llm_client", return_value=_mock_llm_response(mock_respuesta)):
            ctx = _make_contexto("Hola buenos días")
            ctx = validar_solicitud(ctx)

        assert ctx.validacion.es_valida is False
        assert ctx.validacion.entidades.nombre_cliente is None

    def test_solicitud_invalida_vaga(self):
        """Solicitud vaga sin información útil."""
        mock_respuesta = {
            "es_valida": False,
            "razon": "No se especifica qué problema tiene ni qué necesita.",
            "entidades": {"nombre_cliente": None, "tipo_id": None, "numero_id": None},
        }
        with patch("app.core.validator.get_llm_client", return_value=_mock_llm_response(mock_respuesta)):
            ctx = _make_contexto("Tengo un problema")
            ctx = validar_solicitud(ctx)

        assert ctx.validacion.es_valida is False

    def test_fallback_cuando_llm_falla_con_texto_largo(self):
        """Si el LLM falla, el fallback acepta textos con longitud suficiente."""
        with patch("app.core.validator.get_llm_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.complete_json.side_effect = LLMParseError("JSON inválido del modelo")
            mock_factory.return_value = mock_client

            ctx = _make_contexto(
                "Mi estufa de gas no enciende correctamente desde hace tres días "
                "y necesito que vengan a revisarla urgentemente."
            )
            ctx = validar_solicitud(ctx)

        # Fallback acepta porque el texto tiene más de 30 caracteres
        assert ctx.validacion.es_valida is True
        assert "automática" in ctx.validacion.razon

    def test_fallback_cuando_llm_falla_con_texto_corto(self):
        """Si el LLM falla, el fallback rechaza textos muy cortos."""
        with patch("app.core.validator.get_llm_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.complete_json.side_effect = Exception("Timeout")
            mock_factory.return_value = mock_client

            ctx = _make_contexto("Ayuda")
            ctx = validar_solicitud(ctx)

        assert ctx.validacion.es_valida is False

    def test_entidades_parciales(self):
        """Solicitud válida pero sin número de documento."""
        mock_respuesta = {
            "es_valida": True,
            "razon": "Describe un problema claro aunque no incluye número de documento.",
            "entidades": {
                "nombre_cliente": "Carlos Ruiz",
                "tipo_id": None,
                "numero_id": None,
            },
        }
        with patch("app.core.validator.get_llm_client", return_value=_mock_llm_response(mock_respuesta)):
            ctx = _make_contexto(
                "Soy Carlos Ruiz y llevo una semana esperando la instalación del medidor."
            )
            ctx = validar_solicitud(ctx)

        assert ctx.validacion.es_valida is True
        assert ctx.validacion.entidades.nombre_cliente == "Carlos Ruiz"
        assert ctx.validacion.entidades.numero_id is None



if __name__ == "__main__":
    tests = TestValidador()
    casos = [
        ("test_solicitud_valida_con_entidades", "Solicitud válida con entidades"),
        ("test_solicitud_invalida_sin_descripcion", "Solicitud inválida (vacía)"),
        ("test_solicitud_invalida_vaga", "Solicitud inválida (vaga)"),
        ("test_fallback_cuando_llm_falla_con_texto_largo", "Fallback - texto largo"),
        ("test_fallback_cuando_llm_falla_con_texto_corto", "Fallback - texto corto"),
        ("test_entidades_parciales", "Entidades parciales"),
    ]
    print("\n Tests Paso 1 - Validador\n")
    passed = 0
    for method_name, descripcion in casos:
        try:
            getattr(tests, method_name)()
            print(f"  check: {descripcion}")
            passed += 1
        except Exception as e:
            print(f"  error: {descripcion}: {e}")

    print(f"\n{'done' if passed == len(casos) else 'warning '} {passed}/{len(casos)} tests pasaron\n")