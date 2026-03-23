import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.internal_models import (
    ContextoPipeline,
    ResultadoValidacion,
    ResultadoClasificacion,
    ResultadoPrioridad,
    EntidadesExtraidas,
)
from app.models.enums import Prioridad, ProximoPaso
from app.core.justification import generar_justificacion
from app.core.next_step_engine import decidir_siguiente_paso
from app.llm.client import LLMParseError


def _make_contexto_completo(
    categoria: str,
    prioridad: Prioridad = Prioridad.ALTA,
    compania: str = "GASES DEL ORINOCO",
    descripcion: str = "El gas no funciona desde hace 2 días.",
) -> ContextoPipeline:
    ctx = ContextoPipeline(
        compania=compania,
        solicitud_id="REQ-TEST-004",
        solicitud_descripcion=descripcion,
    )
    ctx.validacion = ResultadoValidacion(
        es_valida=True,
        razon="OK",
        entidades=EntidadesExtraidas(
            nombre_cliente="Carlos López",
            tipo_id="CC",
            numero_id="987654321",
        ),
    )
    ctx.clasificacion = ResultadoClasificacion(categoria=categoria, confianza="alta")
    ctx.prioridad = ResultadoPrioridad(prioridad=prioridad, fuente="reglas_locales")
    return ctx



class TestJustificacion:

    def test_genera_justificacion_con_llm(self):
        """El LLM genera una justificación y se almacena en el contexto."""
        mock_client = MagicMock()
        mock_client.complete_json.return_value = {
            "justificacion": "Se detecta falla técnica en instalación de gas que requiere intervención presencial urgente."
        }
        with patch("app.core.justification.get_llm_client", return_value=mock_client):
            ctx = _make_contexto_completo("Incidente técnico")
            ctx = generar_justificacion(ctx)

        assert ctx.justificacion is not None
        assert len(ctx.justificacion) > 10
        assert "falla" in ctx.justificacion.lower()

    def test_fallback_si_llm_falla(self):
        """Si el LLM falla, la justificación genérica incluye categoría y prioridad."""
        with patch("app.core.justification.get_llm_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.complete_json.side_effect = LLMParseError("Error de parseo")
            mock_factory.return_value = mock_client

            ctx = _make_contexto_completo("Incidente técnico", Prioridad.ALTA)
            ctx = generar_justificacion(ctx)

        assert ctx.justificacion is not None
        assert "Incidente técnico" in ctx.justificacion
        assert "Alta" in ctx.justificacion

    def test_fallback_si_llm_exception(self):
        """Cualquier excepción del LLM activa el fallback."""
        with patch("app.core.justification.get_llm_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.complete_json.side_effect = Exception("Timeout")
            mock_factory.return_value = mock_client

            ctx = _make_contexto_completo("Consulta de facturación", Prioridad.BAJA)
            ctx = generar_justificacion(ctx)

        assert "Consulta de facturación" in ctx.justificacion
        assert "Baja" in ctx.justificacion



class TestSiguientePaso:

    def test_incidente_tecnico_requiere_gestion_externa(self):
        """Incidente técnico está en delegaciones externas de Gases del Orinoco."""
        ctx = _make_contexto_completo("Incidente técnico")
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.GESTION_EXTERNA

    def test_reclamo_comercial_requiere_gestion_externa(self):
        ctx = _make_contexto_completo("Reclamo comercial")
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.GESTION_EXTERNA

    def test_consulta_facturacion_es_respuesta_directa(self):
        """Consulta de facturación puede resolverla el BPO directamente."""
        ctx = _make_contexto_completo("Consulta de facturación")
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.RESPUESTA_DIRECTA

    def test_mantenimiento_es_respuesta_directa(self):
        ctx = _make_contexto_completo("Solicitud de mantenimiento")
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.RESPUESTA_DIRECTA

    def test_categoria_no_mapeada_escala_por_seguridad(self):
        """Categoría sin delegación asignada → GESTION_EXTERNA por seguridad."""
        ctx = _make_contexto_completo("CategoriaDesconocida")
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.GESTION_EXTERNA

    def test_perdida_paquete_mensajeria_gestion_externa(self):
        """Pérdida de paquete en Mensajería del Valle requiere gestión externa."""
        ctx = _make_contexto_completo(
            "Pérdida de paquete",
            compania="MENSAJERIA DEL VALLE",
        )
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.GESTION_EXTERNA

    def test_consulta_estado_mensajeria_respuesta_directa(self):
        """Consulta de estado en Mensajería del Valle es respuesta directa."""
        ctx = _make_contexto_completo(
            "Consulta de estado",
            compania="MENSAJERIA DEL VALLE",
        )
        ctx = decidir_siguiente_paso(ctx)
        assert ctx.proximo_paso == ProximoPaso.RESPUESTA_DIRECTA



if __name__ == "__main__":
    print("\n Tests Paso 4 - Justificación\n")
    tests_j = TestJustificacion()
    casos_j = [
        ("test_genera_justificacion_con_llm",  "Genera justificación con LLM"),
        ("test_fallback_si_llm_falla",         "Fallback si LLM falla (parse error)"),
        ("test_fallback_si_llm_exception",     "Fallback si LLM falla (exception)"),
    ]
    passed = 0
    for method_name, desc in casos_j:
        try:
            getattr(tests_j, method_name)()
            print(f"  Check: {desc}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {desc}: {e}")
    print(f"\n{'Done' if passed == len(casos_j) else 'Warning '} {passed}/{len(casos_j)} tests pasaron\n")

    print("\n Tests Paso 5 - Siguiente Paso\n")
    tests_n = TestSiguientePaso()
    casos_n = [
        ("test_incidente_tecnico_requiere_gestion_externa",    "Incidente técnico → gestión externa"),
        ("test_reclamo_comercial_requiere_gestion_externa",    "Reclamo comercial → gestión externa"),
        ("test_consulta_facturacion_es_respuesta_directa",     "Consulta facturación → respuesta directa"),
        ("test_mantenimiento_es_respuesta_directa",            "Mantenimiento → respuesta directa"),
        ("test_categoria_no_mapeada_escala_por_seguridad",     "Categoría sin mapeo → gestión externa"),
        ("test_perdida_paquete_mensajeria_gestion_externa",    "Pérdida paquete (Mensajería) → gestión externa"),
        ("test_consulta_estado_mensajeria_respuesta_directa",  "Consulta estado (Mensajería) → respuesta directa"),
    ]
    passed = 0
    for method_name, desc in casos_n:
        try:
            getattr(tests_n, method_name)()
            print(f"  Check: {desc}")
            passed += 1
        except Exception as e:
            print(f"  Error: {desc}: {e}")
    print(f"\n{'Done' if passed == len(casos_n) else 'Warning '} {passed}/{len(casos_n)} tests pasaron\n")