"""Helper bersama untuk 3 server simulator kasar (Keuangan, CRM, SCM)."""
import os
import secrets
import time
import uuid
from typing import Any

import requests
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

def get_hrm_base_url() -> str:
    """Membaca URL dasar HRM secara dinamis agar kompatibel dengan mode lokal maupun cloud."""
    return os.environ.get("HRM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def get_root_prefix(request: Request) -> str:
    """Mengembalikan prefix root_path ASGI saat di-mount sebagai sub-aplikasi."""
    return request.scope.get("root_path", "").rstrip("/")


class MockTokenReq(BaseModel):
    client_id: str
    client_secret: str


def create_mock_app(
    service_name: str,
    group_label: str,
    expected_client_id: str,
    expected_client_secret: str,
) -> tuple[FastAPI, Any]:
    """Membuat instance FastAPI ringan dengan endpoint /health, /oauth/token, dan dependency auth."""
    app = FastAPI(title=f"{group_label} — {service_name} (Mock Kasar)")
    tokens: dict[str, float] = {}

    @app.middleware("http")
    async def mock_request_id_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    @app.get("/health")
    def health():
        return {"status": "OK", "service": service_name, "group": group_label, "mock": True}

    @app.post("/oauth/token")
    def oauth_token(payload: MockTokenReq):
        if payload.client_id != expected_client_id or payload.client_secret != expected_client_secret:
            raise HTTPException(status_code=401, detail="Kredensial mock salah")
        tok = secrets.token_urlsafe(24)
        tokens[tok] = time.time() + 1800
        return {"access_token": tok, "token_type": "Bearer", "expires_in": 1800}

    def require_token(request: Request):
        h = request.headers.get("Authorization", "")
        if not h.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token tidak ada")
        tok = h[len("Bearer "):].strip()
        exp = tokens.get(tok)
        if not exp or exp < time.time():
            raise HTTPException(status_code=401, detail="Token tidak valid atau kedaluwarsa")
        return True

    return app, Depends(require_token)


def call_hrm_endpoint(
    method: str,
    path: str,
    client_id: str,
    client_secret: str,
    json_body: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[bool, Any]:
    """Helper mock server untuk memanggil API HRM (dengan /oauth/token)."""
    hrm_base = get_hrm_base_url()
    try:
        tok_resp = requests.post(
            f"{hrm_base}/oauth/token",
            json={"client_id": client_id, "client_secret": client_secret},
            headers={"ngrok-skip-browser-warning": "true", "X-Request-ID": str(uuid.uuid4())},
            timeout=6,
        )
        if tok_resp.status_code != 200:
            return False, f"Gagal dapat token HRM ({tok_resp.status_code}): {tok_resp.text}"
        token = tok_resp.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "ngrok-skip-browser-warning": "true",
            "X-Request-ID": str(uuid.uuid4()),
        }
        if extra_headers:
            for k, v in extra_headers.items():
                if k.lower() != "authorization":
                    headers[k] = v
        resp = requests.request(
            method=method.upper(),
            url=f"{hrm_base}{path}",
            headers=headers,
            json=json_body,
            timeout=8,
        )
        try:
            data = resp.json()
        except ValueError:
            data = resp.text
        return (200 <= resp.status_code < 300), data
    except requests.RequestException as exc:
        return False, f"Koneksi ke HRM gagal: {exc}"


def render_rough_html(title: str, badge: str, body_html: str) -> str:
    """Merender HTML sederhana/kasar ala prototipe kelompok sebelah."""
    hrm_link = "/" if os.environ.get("CLOUD_UNIFIED_MODE") == "1" else get_hrm_base_url()
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f4f4f5; color: #18181b; }}
    .box {{ background: #fff; border: 2px solid #52525b; padding: 16px; margin-bottom: 16px; }}
    .banner {{ background: #fef08a; border: 2px dashed #a16207; padding: 10px 14px; margin-bottom: 16px; font-size: 13px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 13px; }}
    th, td {{ border: 1px solid #a1a1aa; padding: 6px 8px; text-align: left; }}
    th {{ background: #e4e4e7; }}
    button {{ padding: 6px 12px; cursor: pointer; background: #27272a; color: #fff; border: none; }}
    input, select {{ padding: 5px; border: 1px solid #71717a; }}
  </style>
</head>
<body>
  <div class="banner">
    <b>[SIMULATOR KASAR — {badge}]</b> Halaman prototipe sederhana untuk menguji integrasi REST API dengan <b>HRM Kelompok 12</b> (<a href="{hrm_link}" target="_blank">Buka HRM</a>).
  </div>
  <h2>{title}</h2>
  {body_html}
</body>
</html>"""
