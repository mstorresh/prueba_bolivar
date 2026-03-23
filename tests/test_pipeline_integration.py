"""
Tests de integración del pipeline completo.
Mockea el LLM y verifica que los 6 pasos se encadenen correctamente.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.pipeline import ejecutar_pipeline
from app.models.enums import ProximoPaso, EstadoCaso, Prioridad


def _make_input(descripcion: str, compania: str = "GASES DEL ORINOCO", solicitud_id: str = "REQ-INT-001"):
    """Helper: crea un SolicitudInput sin depender de Pydantic."""
    class FakeInput:
        pass
    obj = FakeInput()
    obj.compania = compania
    obj.solicitud_id = solicitud_id
    obj.solicitud_descripcion = descripcion
    return obj


def _mock_llm_responses(validacion: dict, clasificacion: dict, justificacion: dict):
    """
    Crea un mock del LLM que retorna respuestas distintas
    según el orden de llamada: validación → clasificación → justificación.
    """
    mock_client = MagicMock()
    mock_client.complete_json.side_effect = [validacion, clasificacion, justificacion]
    return mock_client


class TestPipelineIntegracion:

    def test_flujo_completo_gestion_externa(self):
        """
        Caso del enunciado: estufa con fallas → incidente técnico → Alta → gestión externa.
        Verifica que el pipeline completo produzca el output correcto.
        """
        mock_client = _mock_llm_responses(
            validacion={
                "es_valida": True,
                "razon": "Describe falla técnica con datos del cliente.",
                "entidades": {"nombre_cliente": "Juana", "tipo_id": "CC", "numero_id": "102045678"},
            },
            clasificacion={"categoria": "Incidente técnico", "confianza": "alta"},
            justificacion={"justificacion": "Falla técnica en estufa requiere intervención presencial urgente."},
        )

        with patch("app.core.validator.get_llm_client", return_value=mock_client), \
             patch("app.core.classifier.get_llm_client", return_value=mock_client), \
             patch("app.core.justification.get_llm_client", return_value=mock_client):

            input_data = _make_input(
                "Mi nombre es Juana, CC 102045678. La estufa que compré hace 2 semanas "
                "presenta fallas urgentes en la llave del gas.",
            )
            output = ejecutar_pipeline(input_data)

        assert output.proximo_paso == ProximoPaso.GESTION_EXTERNA
        assert output.solicitud_tipo == "Incidente técnico"
        assert output.solicitud_prioridad == Prioridad.ALTA
        assert output.solicitud_nombre_cliente == "Juana"
        assert output.solicitud_tipo_id_cliente == "CC"
        assert output.solicitud_numero_id_cliente == "102045678"
        assert output.solicitud_id_plataforma_externa is not None  # Mock creó el caso
        assert output.estado == EstadoCaso.PENDIENTE
        assert output.plataforma_error is False

    def test_flujo_completo_respuesta_directa(self):
        """Consulta de facturación → respuesta directa → estado cerrado."""
        mock_client = _mock_llm_responses(
            validacion={
                "es_valida": True,
                "razon": "Consulta clara de facturación.",
                "entidades": {"nombre_cliente": "Pedro", "tipo_id": "CC", "numero_id": "111222333"},
            },
            clasificacion={"categoria": "Consulta de facturación", "confianza": "alta"},
            justificacion={"justificacion": "Consulta de facturación estándar resuelta directamente."},
        )

        with patch("app.core.validator.get_llm_client", return_value=mock_client), \
             patch("app.core.classifier.get_llm_client", return_value=mock_client), \
             patch("app.core.justification.get_llm_client", return_value=mock_client):

            input_data = _make_input("Soy Pedro CC 111222333. ¿Por qué me cobraron de más este mes?")
            output = ejecutar_pipeline(input_data)

        assert output.proximo_paso == ProximoPaso.RESPUESTA_DIRECTA
        assert output.solicitud_tipo == "Consulta de facturación"
        assert output.solicitud_prioridad == Prioridad.BAJA
        assert output.estado == EstadoCaso.CERRADO
        assert output.solicitud_id_plataforma_externa is None  # No crea caso externo

    def test_flujo_cortocircuito_informacion_insuficiente(self):
        """Solicitud vaga → cortocircuito en paso 1 → cierre inmediato."""
        mock_client = MagicMock()
        mock_client.complete_json.return_value = {
            "es_valida": False,
            "razon": "No describe ningún problema concreto.",
            "entidades": {"nombre_cliente": None, "tipo_id": None, "numero_id": None},
        }

        with patch("app.core.validator.get_llm_client", return_value=mock_client):
            input_data = _make_input("Hola, tengo un problema.")
            output = ejecutar_pipeline(input_data)

        assert output.proximo_paso == ProximoPaso.CIERRE_POR_INFORMACION_INSUFICIENTE
        assert output.estado == EstadoCaso.CERRADO
        assert output.solicitud_tipo is None       # No se clasificó
        assert output.solicitud_prioridad is None  # No se asignó prioridad
        # El LLM solo fue llamado UNA vez (solo validación)
        assert mock_client.complete_json.call_count == 1

    def test_flujo_con_plataforma_error(self):
        """Si la plataforma externa falla, el estado es PENDIENTE_REINTENTO."""
        mock_client = _mock_llm_responses(
            validacion={
                "es_valida": True,
                "razon": "OK",
                "entidades": {"nombre_cliente": "Ana", "tipo_id": "CC", "numero_id": "555"},
            },
            clasificacion={"categoria": "Incidente técnico", "confianza": "alta"},
            justificacion={"justificacion": "Incidente técnico de alta prioridad."},
        )

        with patch("app.core.validator.get_llm_client", return_value=mock_client), \
             patch("app.core.classifier.get_llm_client", return_value=mock_client), \
             patch("app.core.justification.get_llm_client", return_value=mock_client), \
             patch("app.integrations.mock_platform.MockPlatform.crear_caso",
                   side_effect=Exception("Plataforma no disponible")):

            input_data = _make_input(
                "Soy Ana CC 555. Mi instalación de gas falló urgentemente.",
            )
            output = ejecutar_pipeline(input_data)

        assert output.estado == EstadoCaso.PENDIENTE_REINTENTO
        assert output.plataforma_error is True
        assert output.solicitud_id_plataforma_externa is None

    def test_output_tiene_todos_los_campos_requeridos(self):
        """Verifica que el output incluye todos los campos del enunciado."""
        mock_client = _mock_llm_responses(
            validacion={
                "es_valida": True,
                "razon": "OK",
                "entidades": {"nombre_cliente": "Luis", "tipo_id": "NIT", "numero_id": "900123456"},
            },
            clasificacion={"categoria": "Reclamo comercial", "confianza": "alta"},
            justificacion={"justificacion": "Reclamo comercial urgente que requiere revisión especializada."},
        )

        with patch("app.core.validator.get_llm_client", return_value=mock_client), \
             patch("app.core.classifier.get_llm_client", return_value=mock_client), \
             patch("app.core.justification.get_llm_client", return_value=mock_client):

            input_data = _make_input(
                "Soy Luis NIT 900123456. Hay un fraude en mi contrato.",
                solicitud_id="REQ-999",
            )
            output = ejecutar_pipeline(input_data)

        # Campos del enunciado
        assert output.compania == "GASES DEL ORINOCO"
        assert output.solicitud_id == "REQ-999"
        assert output.solicitud_fecha is not None
        assert output.solicitud_tipo is not None
        assert output.solicitud_prioridad is not None
        assert output.justificacion is not None
        assert output.proximo_paso is not None
        assert output.estado is not None


# ── Runner manual ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = TestPipelineIntegracion()
    casos = [
        ("test_flujo_completo_gestion_externa",          "Flujo completo → gestión externa"),
        ("test_flujo_completo_respuesta_directa",        "Flujo completo → respuesta directa"),
        ("test_flujo_cortocircuito_informacion_insuficiente", "Cortocircuito → info insuficiente"),
        ("test_flujo_con_plataforma_error",              "Plataforma externa falla → pendiente_reintento"),
        ("test_output_tiene_todos_los_campos_requeridos","Output tiene todos los campos requeridos"),
    ]

    print("\n Tests Integración - Pipeline Completo\n")
    passed = 0
    for method_name, desc in casos:
        try:
            getattr(tests, method_name)()
            print(f"  Check: {desc}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {desc}: {e}")

    print(f"\n{'Done' if passed == len(casos) else 'Warning '} {passed}/{len(casos)} tests pasaron\n")