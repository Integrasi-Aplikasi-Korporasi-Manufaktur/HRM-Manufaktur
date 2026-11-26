"""Entrypoint utama FastAPI untuk Sistem HRM Kelompok 12 (Port 5000)."""
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from hrm_app.config import HRM_PORT
from hrm_app.routers.api_v1 import router as api_router
from hrm_app.routers.web import web_router
from hrm_app.seed_data import seed_database


def _status_to_error_code(code: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }.get(code, "INTERNAL_ERROR")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Memastikan skema SQLite dan data preset awal siap saat server menyala."""
    seed_database(theme_key="manufaktur", force_reset=False)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sistem HRM Terintegrasi — Kelompok 12 (IAK)",
        description=(
            "Aplikasi Human Resource Management (HRM) untuk Proyek UAS Integrasi Aplikasi Korporat. "
            "Dilengkapi REST API Provider (OAuth Bearer) untuk Kelompok 2 (Keuangan), Kelompok 7 (CRM), "
            "dan Kelompok 8 (SCM), serta Integration Adapter untuk menarik data komisi/lembur dan mengirim payroll."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        if isinstance(exc.detail, dict):
            err_obj = exc.detail.get("error") if isinstance(exc.detail.get("error"), dict) else exc.detail
            code = str(err_obj.get("code") or exc.detail.get("code") or _status_to_error_code(exc.status_code))
            message = str(
                err_obj.get("message")
                or exc.detail.get("message")
                or (exc.detail.get("error") if isinstance(exc.detail.get("error"), str) else "")
                or json.dumps(exc.detail, ensure_ascii=False)
            )
        else:
            code = _status_to_error_code(exc.status_code)
            message = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": code, "message": message, "request_id": req_id},
                "detail": exc.detail,
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        return JSONResponse(
            status_code=422,
            content={
                "error": {"code": "VALIDATION_ERROR", "message": "Payload tidak valid", "request_id": req_id},
                "detail": exc.errors(),
            },
            headers={"X-Request-ID": req_id},
        )

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(api_router)
    app.include_router(web_router)
    return app


app = create_app()


if __name__ == "__main__":
    print(f"[HRM Kel. 12] Menjalankan server di http://127.0.0.1:{HRM_PORT} (Swagger: /docs)")
    uvicorn.run("hrm_app.main:app", host="0.0.0.0", port=HRM_PORT, reload=False)
