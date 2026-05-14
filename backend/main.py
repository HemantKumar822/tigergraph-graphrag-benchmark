from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.models.schemas import APIResponse, APIError
from app.api.routes import router as pipeline_router
from app.api.orchestrator import orchestrator as orchestrator_router
from app.api.ingestion import router as ingestion_router
from app.core.config import settings
from app.core.logging_setup import setup_rich_logging
import logging
import uvicorn

# Initialize structural terminal logging
setup_rich_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="TigerGraph GraphRAG API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)
app.include_router(orchestrator_router)
app.include_router(ingestion_router, prefix="/api/ingestion", tags=["ingestion"])

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_response = APIResponse(
        status="error",
        error=APIError(code=str(exc.status_code), message=exc.detail)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(by_alias=True)
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_response = APIResponse(
        status="error",
        error=APIError(code="VALIDATION_ERROR", message=str(exc.errors()))
    )
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(by_alias=True)
    )

# Global Exception Handler to ensure we always return the standard envelope
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    error_response = APIResponse(
        status="error",
        error=APIError(code="INTERNAL_SERVER_ERROR", message="An unexpected error occurred.")
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(by_alias=True)
    )

@app.get("/api/health", response_model=APIResponse[dict])
async def health_check():
    return APIResponse(status="success", data={"ping": "pong"})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
