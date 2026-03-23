import logging
import os
from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.routes import router

# Carga variables de entorno desde .env si existe
load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title="BPO-AI Microservicio",
    description=(
        "Microservicio de IA para automatización del proceso de gestión de solicitudes BPO. "
        "Automatiza validación, clasificación, prioridad y enrutamiento de casos."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.get("/", tags=["Root"])
def root():
    return {
        "servicio": "BPO-AI Microservicio",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("APP_ENV", "development") == "development",
    )