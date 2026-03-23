"""
Cliente LLM abstracto.
Soporta Groq, OpenAI y Anthropic desde una interfaz única.
El proveedor se elige via variable de entorno LLM_PROVIDER.
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
# ── Interfaz base ──────────────────────────────────────────────────────────────

class LLMClient(ABC):
    """Interfaz común para cualquier proveedor LLM."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        """
        Llama al modelo y retorna el texto de respuesta.
        temperature=0.0 para respuestas determinísticas (clasificación, extracción).
        """
        ...

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
    ) -> dict:
        """
        Wrapper que llama a complete() y parsea el resultado como JSON.
        Lanza LLMParseError si la respuesta no es JSON válido.
        """
        raw = self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=max_tokens,
        )
        return _parse_json_safe(raw)


# ── Implementaciones ───────────────────────────────────────────────────────────

class GroqClient(LLMClient):
    """Cliente para Groq (compatible con la API de OpenAI)."""

    def __init__(self):
        api_key = _require_env("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "llama3-8b-8192")

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        except ImportError:
            raise ImportError(
                "El paquete 'openai' es necesario para usar Groq. "
                
            )

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=1000):
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

# ---------------------------------------------------------------------------------------------------
# si  se tiene un token directo de openai se descomenta esta clase y se comenta la que se esta utilizando, en mi caso toco de la segunda forma ya que estaba usando el LLM por medio de github
#-------------------------------------------------------------------------------------------------

# class OpenAIClient(LLMClient):
#     """Cliente para OpenAI."""

#     def __init__(self):
#         api_key = _require_env("LLM_API_KEY")
#         self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

#         try:
#             from openai import OpenAI
#             self._client = OpenAI(api_key=api_key)
#         except ImportError:
#             raise ImportError("Instala el paquete 'openai': pip install openai")

#     def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=1000):
#         response = self._client.chat.completions.create(
#             model=self.model,
#             temperature=temperature,
#             max_tokens=max_tokens,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt},
#             ],
#         )
#         return response.choices[0].message.content.strip()

class OpenAIClient(LLMClient):
    """Cliente para OpenAI (usando GitHub Models gratis)."""

    def __init__(self):
        api_key = _require_env("LLM_API_KEY")
        # Por defecto usaremos gpt-4o de GitHub
        self.model = os.getenv("LLM_MODEL", "gpt-4o")

        try:
            from openai import OpenAI
            # CAMBIO CLAVE: Añadimos la base_url de GitHub
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://models.inference.ai.azure.com"
            )
        except ImportError:
            raise ImportError("Instala el paquete 'openai': pip install openai")

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=1000):
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()


class AnthropicClient(LLMClient):
    """Cliente para Anthropic (Claude)."""

    def __init__(self):
        api_key = _require_env("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Instala el paquete 'anthropic': pip install anthropic")

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=1000):
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text.strip()


# ── Factory ────────────────────────────────────────────────────────────────────

_PROVIDERS = {
    "groq": GroqClient,
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
}

_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Retorna el cliente LLM configurado via LLM_PROVIDER.
    Singleton: una sola instancia por proceso.
    """
    global _instance
    if _instance is None:
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        if provider not in _PROVIDERS:
            raise ValueError(
                f"Proveedor LLM '{provider}' no soportado. "
                f"Opciones: {list(_PROVIDERS.keys())}"
            )
        _instance = _PROVIDERS[provider]()
    return _instance


def reset_llm_client():
    """Resetea el singleton. Útil para tests."""
    global _instance
    _instance = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_env(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(
            f"Variable de entorno requerida '{var}' no está configurada. "
            f"Revisa el archivo .env"
        )
    return value


def _parse_json_safe(raw: str) -> dict:
    """
    Parsea JSON desde la respuesta del LLM.
    Maneja casos donde el modelo envuelve el JSON en ```json ... ```.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            f"La respuesta del LLM no es JSON válido.\n"
            f"Error: {e}\n"
            f"Respuesta recibida:\n{raw}"
        )


# ── Errores ────────────────────────────────────────────────────────────────────

class LLMParseError(Exception):
    """Se lanza cuando la respuesta del LLM no puede parsearse como JSON."""
    pass