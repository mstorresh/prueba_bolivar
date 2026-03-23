import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.internal_models import ContextoPipeline
from app.core.classifier import clasificar_solicitud
from app.llm.client import LLMParseError


def _make_contexto(descripcion: str, compania: str = "GASES DEL ORINOCO") -> ContextoPipeline:
    return ContextoPipeline(
        compania=compania,
        solicitud_id="REQ-TEST-002",
        solicitud_descripcion=descripcion,
    )


def _mock_llm(categoria: str, confianza: str = "alta"):
    mock_client = MagicMock()
    mock_client.complete_json.return_value = {
        "categoria": categoria,
        "confianza": confianza,
    }
    return mock_client


class TestClasificador:

    def test_clasifica_incidente_tecnico(self):
        """Clasifica correctamente un incidente técnico."""
        with patch("app.core.classifier.get_llm_client", return_value=_mock_llm("Incidente técnico")):
            ctx = _make_contexto("Mi estufa de gas presenta fallas y no enciende.")
            ctx = clasificar_solicitud(ctx)

        assert ctx.clasificacion.categoria == "Incidente técnico"
        assert ctx.clasificacion.confianza == "alta"

    def test_clasifica_consulta_facturacion(self):
        """Clasifica correctamente una consulta de facturación."""
        with patch("app.core.classifier.get_llm_client", return_value=_mock_llm("Consulta de facturación", "alta")):
            ctx = _make_contexto("Quisiera saber por qué me llegó un cobro adicional este mes.")
            ctx = clasificar_solicitud(ctx)

        assert ctx.clasificacion.categoria == "Consulta de facturación"

    def test_clasifica_para_mensajeria_del_valle(self):
        """Verifica que usa las categorías correctas según la empresa."""
        with patch("app.core.classifier.get_llm_client", return_value=_mock_llm("Pérdida de paquete")):
            ctx = _make_contexto(
                "Mi paquete salió hace 10 días y no ha llegado.",
                compania="MENSAJERIA DEL VALLE",
            )
            ctx = clasificar_solicitud(ctx)

        assert ctx.clasificacion.categoria == "Pérdida de paquete"

    def test_fallback_si_categoria_invalida(self):
        """Si el LLM devuelve una categoría que no existe, aplica fallback."""
        with patch("app.core.classifier.get_llm_client", return_value=_mock_llm("Categoría inventada")):
            ctx = _make_contexto("Tengo un problema con mi servicio.")
            ctx = clasificar_solicitud(ctx)

        # Fallback debe asignar "Otro" (existe en gases_del_orinoco.yaml)
        assert ctx.clasificacion.categoria == "Otro"
        assert ctx.clasificacion.confianza == "baja"

    def test_fallback_si_llm_parse_error(self):
        """Si el LLM falla con JSON inválido, aplica fallback."""
        with patch("app.core.classifier.get_llm_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.complete_json.side_effect = LLMParseError("JSON inválido")
            mock_factory.return_value = mock_client

            ctx = _make_contexto("Necesito ayuda con algo.")
            ctx = clasificar_solicitud(ctx)

        assert ctx.clasificacion.categoria in ["Otro", "Incidente técnico"]
        assert ctx.clasificacion.confianza == "baja"

    def test_fallback_si_llm_exception(self):
        """Si el LLM lanza cualquier excepción, aplica fallback."""
        with patch("app.core.classifier.get_llm_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.complete_json.side_effect = Exception("Timeout")
            mock_factory.return_value = mock_client

            ctx = _make_contexto("Problema con el servicio.")
            ctx = clasificar_solicitud(ctx)

        assert ctx.clasificacion is not None
        assert ctx.clasificacion.confianza == "baja"

    def test_confianza_media_se_preserva(self):
        """La confianza media reportada por el LLM se conserva."""
        with patch("app.core.classifier.get_llm_client", return_value=_mock_llm("Reclamo comercial", "media")):
            ctx = _make_contexto("No estoy de acuerdo con el contrato que firmé.")
            ctx = clasificar_solicitud(ctx)

        assert ctx.clasificacion.categoria == "Reclamo comercial"
        assert ctx.clasificacion.confianza == "media"

if __name__ == "__main__":
    tests = TestClasificador()
    casos = [
        ("test_clasifica_incidente_tecnico",         "Clasifica incidente técnico"),
        ("test_clasifica_consulta_facturacion",      "Clasifica consulta de facturación"),
        ("test_clasifica_para_mensajeria_del_valle", "Categorías correctas por empresa"),
        ("test_fallback_si_categoria_invalida",      "Fallback - categoría inválida del LLM"),
        ("test_fallback_si_llm_parse_error",         "Fallback - JSON inválido"),
        ("test_fallback_si_llm_exception",           "Fallback - excepción genérica"),
        ("test_confianza_media_se_preserva",         "Confianza media se preserva"),
    ]

    print("\n Tests Paso 2 - Clasificador\n")
    passed = 0
    for method_name, descripcion in casos:
        try:
            getattr(tests, method_name)()
            print(f"  Check {descripcion}")
            passed += 1
        except Exception as e:
            print(f"  Error: {descripcion}: {e}")

    print(f"\n{'Done' if passed == len(casos) else 'Warning '} {passed}/{len(casos)} tests pasaron\n")