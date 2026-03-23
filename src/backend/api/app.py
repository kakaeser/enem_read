from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1.endpoints.exams import router as exams_router
from backend.api.v1.endpoints.ocr import router as ocr_router
from backend.api.v1.endpoints.participants import (
    exam_participants_router,
    participants_router,
)
from backend.api.v1.endpoints.results import router as results_router
from backend.core.exceptions import AppException

app = FastAPI(
    title="Enem da Read API",
    version="2.0.0",
    description="Multi-exam OCR system API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


PREFIX = "/api/v1"

app.include_router(exams_router, prefix=PREFIX)
app.include_router(exam_participants_router, prefix=PREFIX)
app.include_router(participants_router, prefix=PREFIX)
app.include_router(ocr_router, prefix=PREFIX)
app.include_router(results_router, prefix=PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
