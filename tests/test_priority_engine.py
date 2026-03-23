import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.internal_models import (
    ContextoPipeline,
    ResultadoValidacion,
    ResultadoClasificacion,
    EntidadesExtraidas,
)
from app.models.enums import Prioridad
from app.core.priority_engine import asignar_prioridad


def _make_contexto(
    descripcion: str,
    categoria: str,
    compania: str = "GASES DEL ORINOCO",
    tipo_id: str = "CC",
    numero_id: str = "123456",
) -> ContextoPipeline:
    ctx = ContextoPipeline(
        compania=compania,
        solicitud_id="REQ-TEST-003",
        solicitud_descripcion=descripcion,
    )
    ctx.validacion = ResultadoValidacion(
        es_valida=True,
        razon="OK",
        entidades=EntidadesExtraidas(
            nombre_cliente="Test User",
            tipo_id=tipo_id,
            numero_id=numero_id,
        ),
    )
    ctx.clasificacion = ResultadoClasificacion(categoria=categoria, confianza="alta")
    return ctx


class TestMotorPrioridad:

    # ── Reglas locales ─────────────────────────────────────────────────────────

    def test_prioridad_alta_por_palabras_clave(self):
        """Palabras clave como 'urgente' deben disparar prioridad Alta."""
        ctx = _make_contexto(
            descripcion="Solicito una revisión urgente porque mi estufa presenta fallas.",
            categoria="Incidente técnico",
        )
        ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.prioridad == Prioridad.ALTA
        assert ctx.prioridad.fuente == "reglas_locales"

    def test_prioridad_media_por_default_incidente(self):
        """Incidente técnico sin palabras clave urgentes → Media por default."""
        ctx = _make_contexto(
            descripcion="La estufa no enciende bien, quisiera que la revisen.",
            categoria="Incidente técnico",
        )
        ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.prioridad == Prioridad.MEDIA
        assert ctx.prioridad.fuente == "reglas_locales"

    def test_prioridad_baja_consulta_facturacion(self):
        """Consulta de facturación siempre debe ser Baja."""
        ctx = _make_contexto(
            descripcion="Quisiera saber por qué me llegó un cobro adicional.",
            categoria="Consulta de facturación",
        )
        ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.prioridad == Prioridad.BAJA
        assert ctx.prioridad.fuente == "reglas_locales"

    def test_prioridad_alta_reclamo_con_palabra_fraude(self):
        """Reclamo con palabra clave 'fraude' → Alta."""
        ctx = _make_contexto(
            descripcion="Creo que hay un fraude en mi contrato de gas.",
            categoria="Reclamo comercial",
        )
        ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.prioridad == Prioridad.ALTA
        assert ctx.prioridad.fuente == "reglas_locales"

    def test_prioridad_sin_regla_definida_usa_media(self):
        """Si no hay regla para la categoría, asigna Media como seguro."""
        ctx = _make_contexto(
            descripcion="Tengo una duda general.",
            categoria="CategoriaInexistente",
        )
        ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.prioridad == Prioridad.MEDIA
        assert ctx.prioridad.fuente == "reglas_locales"

    # ── Servicio externo ───────────────────────────────────────────────────────

    def test_servicio_externo_retorna_prioridad_alta(self):
        """El servicio externo de Mensajería del Valle retorna Alta."""
        with patch("app.core.priority_engine.http_post_json", return_value={"prioridad": "Alta"}), \
             patch.dict("os.environ", {"MENSAJERIA_VALLE_PRIORITY_URL": "http://mock-service/prioridad"}):

            ctx = _make_contexto(
                descripcion="Mi paquete se perdió hace una semana.",
                categoria="Pérdida de paquete",
                compania="MENSAJERIA DEL VALLE",
            )
            ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.prioridad == Prioridad.ALTA
        assert ctx.prioridad.fuente == "servicio_externo"

    def test_fallback_si_servicio_externo_falla(self):
        """Si el servicio externo falla (timeout, error), usa reglas locales."""
        with patch("app.core.priority_engine.http_post_json", side_effect=Exception("Connection timeout")), \
             patch.dict("os.environ", {"MENSAJERIA_VALLE_PRIORITY_URL": "http://mock-service/prioridad"}):

            ctx = _make_contexto(
                descripcion="Mi paquete se perdió.",
                categoria="Pérdida de paquete",
                compania="MENSAJERIA DEL VALLE",
            )
            ctx = asignar_prioridad(ctx)

        # Fallback a reglas locales — Pérdida de paquete tiene prioridad_default Alta
        assert ctx.prioridad.prioridad == Prioridad.ALTA
        assert ctx.prioridad.fuente == "fallback"

    def test_fallback_si_servicio_externo_retorna_prioridad_invalida(self):
        """Si el servicio externo retorna un valor inválido, usa fallback."""
        with patch("app.core.priority_engine.http_post_json", return_value={"prioridad": "URGENTISIMA"}), \
             patch.dict("os.environ", {"MENSAJERIA_VALLE_PRIORITY_URL": "http://mock-service/prioridad"}):

            ctx = _make_contexto(
                descripcion="Mi paquete se perdió.",
                categoria="Pérdida de paquete",
                compania="MENSAJERIA DEL VALLE",
            )
            ctx = asignar_prioridad(ctx)

        assert ctx.prioridad.fuente == "fallback"



if __name__ == "__main__":
    tests = TestMotorPrioridad()
    casos = [
        ("test_prioridad_alta_por_palabras_clave",              "Alta por palabras clave"),
        ("test_prioridad_media_por_default_incidente",          "Media por default (incidente)"),
        ("test_prioridad_baja_consulta_facturacion",            "Baja (consulta facturación)"),
        ("test_prioridad_alta_reclamo_con_palabra_fraude",      "Alta por palabra clave 'fraude'"),
        ("test_prioridad_sin_regla_definida_usa_media",         "Sin regla → Media por defecto"),
        ("test_servicio_externo_retorna_prioridad_alta",        "Servicio externo → Alta"),
        ("test_fallback_si_servicio_externo_falla",             "Fallback si servicio externo falla"),
        ("test_fallback_si_servicio_externo_retorna_prioridad_invalida", "Fallback si prioridad inválida"),
    ]

    print("\n Tests Paso 3 - Motor de Prioridad\n")
    passed = 0
    for method_name, descripcion in casos:
        try:
            getattr(tests, method_name)()
            print(f"  Check {descripcion}")
            passed += 1
        except Exception as e:
            print(f"  Error: {descripcion}: {e}")

    print(f"\n{'Done' if passed == len(casos) else 'Warning '} {passed}/{len(casos)} tests pasaron\n")