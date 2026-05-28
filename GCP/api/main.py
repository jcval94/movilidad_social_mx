"""Aplicación FastAPI para servir el modelo de Movilidad Social MX."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from GCP.api.errors import register_exception_handlers
from GCP.api.model_service import ModelService
from GCP.api.schemas import HealthResponse, PredictRequest, PredictResponse
from GCP.api.settings import Settings, get_settings


def get_model_service(settings: Settings = Depends(get_settings)) -> ModelService:
    """Factory inyectable del servicio de modelo."""

    return ModelService(settings.model_path)


def create_app() -> FastAPI:
    """Construye la aplicación FastAPI con rutas y handlers registrados."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API de inferencia para predicción probabilística de clase socioeconómica en México.",
        contact={"name": "Movilidad Social MX"},
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    register_exception_handlers(app)

    @app.get("/healthz", response_model=HealthResponse, tags=["operación"])
    async def healthz() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )

    @app.get("/readyz", tags=["operación"])
    async def readyz(service: ModelService = Depends(get_model_service)) -> dict[str, str | int]:
        return service.readiness()

    @app.post("/v1/predict", response_model=PredictResponse, tags=["predicción"])
    async def predict(request: PredictRequest, service: ModelService = Depends(get_model_service)) -> PredictResponse:
        return service.predict(request)

    return app


app = create_app()
