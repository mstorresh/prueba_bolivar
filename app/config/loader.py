import os
import yaml
from pathlib import Path
from typing import Optional
from functools import lru_cache
from pydantic import BaseModel, field_validator

class ReglaProioridad(BaseModel):
    categoria: str
    palabras_clave: list[str] = []
    prioridad: Optional[str] = None        
    prioridad_default: Optional[str] = None  


class Delegaciones(BaseModel):
    gestion_externa: list[str] = []
    respuesta_directa: list[str] = []


class PlataformaExterna(BaseModel):
    tipo: str
    descripcion: Optional[str] = None


class PrioridadExterna(BaseModel):
    activa: bool = False
    endpoint_env_var: Optional[str] = None  

    def get_endpoint(self) -> Optional[str]:
        """Resuelve la URL real desde la variable de entorno."""
        if not self.activa or not self.endpoint_env_var:
            return None
        url = os.getenv(self.endpoint_env_var)
        if not url:
            raise EnvironmentError(
                f"La empresa requiere prioridad externa pero la variable de entorno "
                f"'{self.endpoint_env_var}' no está configurada."
            )
        return url


class CompanyConfig(BaseModel):
    empresa_id: str
    nombre: str
    categorias: list[str]
    reglas_prioridad: list[ReglaProioridad]
    delegaciones: Delegaciones
    plataforma_externa: PlataformaExterna
    prioridad_externa: PrioridadExterna = PrioridadExterna()

    @field_validator("categorias")
    @classmethod
    def categorias_no_vacias(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("La empresa debe tener al menos una categoría definida.")
        return v



COMPANIES_DIR = Path(__file__).parent / "companies"


def _normalize_key(name: str) -> str:
    """
    Normaliza el nombre de empresa.
    'GASES DEL ORINOCO' → 'gases_del_orinoco'
    """
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)



@lru_cache(maxsize=50)
def get_company_config(compania: str) -> CompanyConfig:
    """
    Carga la configuración de una empresa desde su YAML.
    Lanza CompanyNotFoundError si no está registrada.
    Usa lru_cache para evitar lecturas repetidas a disco.
    """
    key = _normalize_key(compania)
    yaml_path = COMPANIES_DIR / f"{key}.yaml"

    if not yaml_path.exists():
        registered = _list_registered_companies()
        raise CompanyNotFoundError(
            company_name=compania,
            registered_companies=registered,
        )

    data = _load_yaml(yaml_path)
    return CompanyConfig(**data)


def _list_registered_companies() -> list[str]:
    """Retorna los IDs de todas las empresas con YAML configurado."""
    return [
        p.stem.upper().replace("_", " ")
        for p in COMPANIES_DIR.glob("*.yaml")
    ]



class CompanyNotFoundError(Exception):
    def __init__(self, company_name: str, registered_companies: list[str]):
        self.company_name = company_name
        self.registered_companies = registered_companies
        super().__init__(
            f"Empresa '{company_name}' no está registrada en el sistema. "
            f"Empresas disponibles: {registered_companies}"
        )
        