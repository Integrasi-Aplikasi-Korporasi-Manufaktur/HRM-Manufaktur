"""Pengujian unit, API, UI routes, dan integrasi End-to-End HRM <-> Keuangan/CRM/SCM."""
import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

import hrm_app.config as cfg
import hrm_app.database as db_mod
from hrm_app.auth import ACTIVE_TOKENS
from hrm_app.main import create_app
from hrm_app.seed_data import seed_database
from hrm_app.services.integration_service import _OUTBOUND_TOKEN_CACHE
from mocks.mock_crm import app as crm_app
from mocks.mock_keuangan import app as fin_app, reset_mock_state
from mocks.mock_scm import app as scm_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_uvicorn_bg(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    deadline = time.time() + 5
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    return server


@pytest.fixture()
def hrm_client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_hrm.db"
    monkeypatch.setattr(cfg, "HRM_DB_PATH", test_db)
    monkeypatch.setattr(db_mod, "HRM_DB_PATH", test_db)
    ACTIVE_TOKENS.clear()
    _OUTBOUND_TOKEN_CACHE.clear()
    reset_mock_state()
    seed_database(theme_key="software", force_reset=True, preserve_partners=False, db_path=test_db)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_all_web_pages_render_200(hrm_client: TestClient):
    for route in ("/", "/employees", "/attendance", "/recruitment", "/payroll", "/integration"):
        resp = hrm_client.get(route)
        assert resp.status_code == 200, f"Gagal merender {route}"
        assert "HRM" in resp.text


def test_theme_switching_preserves_custom_partner_url(hrm_client: TestClient):
    # Ubah URL CRM dulu
    partners = hrm_client.get("/api/v1/integration/partners").json()
    crm = next(p for p in partners if p["partner_key"] == "crm")
    upd = hrm_client.put(
        "/api/v1/integration/partners/crm",
        json={
            "base_url": "https://crm-custom.ngrok-free.app",
            "auth_type": crm["auth_type"],
            "token_endpoint": crm["token_endpoint"],
            "client_id": crm["client_id"],
            "client_secret": crm["client_secret"],
            "api_key_header": crm["api_key_header"],
            "api_key_value": crm["api_key_value"],
            "endpoints": crm["endpoints"],
            "field_mapping": crm["field_mapping"],
            "is_active": True,
        },
    )
    assert upd.status_code == 200

    # Switch ke manufaktur dan telekomunikasi
    for theme, expected_name in (
        ("manufaktur", "PT Panata Jaya Mandiri"),
        ("telekomunikasi", "PT Cakrawala Telekomunikasi Nusantara"),
    ):
        sw = hrm_client.post("/api/v1/system/switch-theme", json={"theme_key": theme, "preserve_partners": True})
        assert sw.status_code == 200
        assert sw.json()["company_name"] == expected_name

    # Pastikan URL custom CRM tetap terjaga
    partners_after = hrm_client.get("/api/v1/integration/partners").json()
    crm_after = next(p for p in partners_after if p["partner_key"] == "crm")
    assert crm_after["base_url"] == "https://crm-custom.ngrok-free.app"


def test_inbound_oauth_and_external_endpoints(hrm_client: TestClient):
    # Tanpa token -> 401
    assert hrm_client.get("/api/v1/external/employees").status_code == 401

    # Secret salah -> 401
    bad_tok = hrm_client.post("/oauth/token", json={"client_id": "kel7_crm", "client_secret": "salah"})
    assert bad_tok.status_code == 401

    # Token valid -> 200
    tok_resp = hrm_client.post("/oauth/token", json={"client_id": "kel7_crm", "client_secret": "secret-kel7-crm"})
    assert tok_resp.status_code == 200
    token = tok_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sales = hrm_client.get("/api/v1/external/employees?role=CRM_SALES", headers=headers)
    assert sales.status_code == 200
    assert sales.json()["total"] >= 2
    assert all(it["integration_role"] == "CRM_SALES" for it in sales.json()["items"])

    # SCM kirim manpower request
    mr = hrm_client.post(
        "/api/v1/external/manpower-requests",
        headers=headers,
        json={
            "requester_system": "SCM",
            "position_title": "Staff Gudang Uji",
            "headcount": 1,
            "estimated_salary": 6500000,
            "reason": "Testing integrasi inbound",
        },
    )
    assert mr.status_code == 201
    assert mr.json()["request_code"].startswith("MR-2026-")


def test_employee_leave_and_auto_onboarding(hrm_client: TestClient):
    # Tambah pelamar & HIRED -> otomatis membuat karyawan baru
    mrs = hrm_client.get("/api/v1/manpower-requests").json()
    mr_id = mrs[0]["id"]
    app_resp = hrm_client.post(
        "/api/v1/applicants",
        json={
            "manpower_request_id": mr_id,
            "full_name": "Bintang Pratama",
            "email": "bintang.pratama@example.com",
            "phone": "081299998888",
            "skills": "Supply Chain, Python",
        },
    )
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    hire = hrm_client.patch(f"/api/v1/applicants/{app_id}/stage", json={"stage": "HIRED"})
    assert hire.status_code == 200
    new_code = hire.json()["hired_employee_code"]
    assert new_code.startswith("EMP-")

    emps = hrm_client.get("/api/v1/employees").json()
    created_emp = next(e for e in emps if e["employee_code"] == new_code)
    assert created_emp["full_name"] == "Bintang Pratama"

    # Ajukan cuti & approve -> kuota berkurang
    lv = hrm_client.post(
        "/api/v1/leaves",
        json={
            "employee_id": created_emp["id"],
            "leave_type": "TAHUNAN",
            "start_date": "2026-11-24",
            "end_date": "2026-11-25",
            "days_count": 2,
            "reason": "Urusan keluarga",
        },
    )
    assert lv.status_code == 201
    dec = hrm_client.patch(f"/api/v1/leaves/{lv.json()['id']}", json={"status": "APPROVED", "reviewed_by": "HR"})
    assert dec.status_code == 200

    emps_after = hrm_client.get("/api/v1/employees").json()
    emp_after = next(e for e in emps_after if e["id"] == created_emp["id"])
    assert emp_after["leave_quota"] == 10


def test_end_to_end_live_integration_with_three_mocks(hrm_client: TestClient):
    p_fin, p_crm, p_scm = _free_port(), _free_port(), _free_port()
    s_fin = _start_uvicorn_bg(fin_app, p_fin)
    s_crm = _start_uvicorn_bg(crm_app, p_crm)
    s_scm = _start_uvicorn_bg(scm_app, p_scm)
    try:
        # Arahkan adapter HRM ke port test mock servers
        partners = {p["partner_key"]: p for p in hrm_client.get("/api/v1/integration/partners").json()}
        for key, port in (("keuangan", p_fin), ("crm", p_crm), ("scm", p_scm)):
            p = partners[key]
            r = hrm_client.put(
                f"/api/v1/integration/partners/{key}",
                json={
                    "base_url": f"http://127.0.0.1:{port}",
                    "auth_type": p["auth_type"],
                    "token_endpoint": p["token_endpoint"],
                    "client_id": p["client_id"],
                    "client_secret": p["client_secret"],
                    "api_key_header": p["api_key_header"],
                    "api_key_value": p["api_key_value"],
                    "endpoints": p["endpoints"],
                    "field_mapping": p["field_mapping"],
                    "is_active": True,
                },
            )
            assert r.status_code == 200

        # 1. Health check seluruh mitra
        hc = hrm_client.post("/api/v1/integration/partners/health-all")
        assert hc.status_code == 200
        assert all(x["status"] == "ONLINE" for x in hc.json())

        # 2. Cek anggaran rekrutmen ke Mock Keuangan
        mrs = hrm_client.get("/api/v1/manpower-requests").json()
        bgt = hrm_client.post(f"/api/v1/manpower-requests/{mrs[0]['id']}/check-budget")
        assert bgt.status_code == 200
        assert bgt.json()["finance_budget_status"] == "APPROVED"

        # 3. Generate payroll dengan sync komisi CRM & lembur SCM
        gen = hrm_client.post("/api/v1/payroll/generate", json={"period": "2026-11", "sync_external": True})
        assert gen.status_code == 200
        gen_data = gen.json()
        assert gen_data["sync_summary"]["crm"]["success"] is True
        assert gen_data["sync_summary"]["scm"]["success"] is True

        items = gen_data["payroll_run"]["items"]
        emp5 = next(i for i in items if i["employee_code"] == "EMP-005")
        emp3 = next(i for i in items if i["employee_code"] == "EMP-003")
        assert emp5["crm_commission"] == 3200000
        assert emp3["overtime_hours"] >= 6.0

        # 4. Kirim payroll ke Keuangan
        sub = hrm_client.post("/api/v1/payroll/2026-11/submit-finance")
        assert sub.status_code == 200
        assert sub.json()["status"] == "SENT_TO_FINANCE"

        # 5. Keuangan memproses bayar (callback ke HRM) via token Kel. 2
        tok_fin = hrm_client.post("/oauth/token", json={"client_id": "kel2_keuangan", "client_secret": "secret-kel2-keuangan"}).json()["access_token"]
        cb = hrm_client.post(
            "/api/v1/external/payroll/PAY-2026-11/payment-callback",
            headers={"Authorization": f"Bearer {tok_fin}"},
            json={"status": "PAID", "finance_ref": sub.json()["finance_batch_ref"], "note": "Lunas via E2E Test"},
        )
        assert cb.status_code == 200
        assert cb.json()["status"] == "PAID"

        # 6. Verifikasi status di HRM sudah PAID & log tercatat
        pr_check = hrm_client.get("/api/v1/payroll/2026-11").json()
        assert pr_check["status"] == "PAID"
        logs = hrm_client.get("/api/v1/integration/logs?limit=50").json()
        assert len(logs) >= 6
    finally:
        s_fin.should_exit = True
        s_crm.should_exit = True
        s_scm.should_exit = True


def test_cloud_unified_single_port_gateway(tmp_path, monkeypatch):
    import os
    import requests
    from cloud_entry import create_cloud_app

    test_db = tmp_path / "cloud_hrm.db"
    monkeypatch.setattr(cfg, "HRM_DB_PATH", test_db)
    monkeypatch.setattr(db_mod, "HRM_DB_PATH", test_db)
    port = _free_port()
    monkeypatch.setenv("PORT", str(port))
    monkeypatch.delenv("VERCEL", raising=False)
    ACTIVE_TOKENS.clear()
    _OUTBOUND_TOKEN_CACHE.clear()
    reset_mock_state()

    cloud_app = create_cloud_app()
    server = _start_uvicorn_bg(cloud_app, port)
    try:
        base = f"http://127.0.0.1:{port}"
        health = requests.get(f"{base}/health", timeout=5)
        assert health.status_code == 200
        assert health.json()["company_name"] == "PT Panata Jaya Mandiri"
        assert requests.get(f"{base}/", timeout=5).status_code == 200
        assert requests.get(f"{base}/mock/keuangan/", timeout=5).status_code == 200
        assert requests.get(f"{base}/mock/crm/", timeout=5).status_code == 200
        assert requests.get(f"{base}/mock/scm/", timeout=5).status_code == 200

        hc = requests.post(f"{base}/api/v1/integration/partners/health-all", timeout=5)
        assert hc.status_code == 200
        assert all(item["status"] == "ONLINE" for item in hc.json())

        gen = requests.post(
            f"{base}/api/v1/payroll/generate",
            json={"period": "2026-11", "sync_external": True},
            timeout=5,
        )
        assert gen.status_code == 200
        assert gen.json()["sync_summary"]["crm"]["success"] is True
        assert gen.json()["sync_summary"]["scm"]["success"] is True
    finally:
        server.should_exit = True
        os.environ.pop("CLOUD_UNIFIED_MODE", None)
        os.environ.pop("HRM_BASE_URL", None)


def test_contract_headers_error_envelope_and_k3_gate(hrm_client: TestClient):
    # 1. X-Request-ID echo & error envelope standar
    hc = hrm_client.get("/health", headers={"X-Request-ID": "req-test-123"})
    assert hc.status_code == 200
    assert hc.headers.get("X-Request-ID") == "req-test-123"
    assert hc.json()["timestamp"].endswith("Z")

    unauth = hrm_client.get("/api/v1/external/employees", headers={"X-Request-ID": "req-err-401"})
    assert unauth.status_code == 401
    assert unauth.headers.get("X-Request-ID") == "req-err-401"
    unauth_body = unauth.json()
    assert unauth_body["error"]["code"] == "UNAUTHORIZED"
    assert unauth_body["error"]["request_id"] == "req-err-401"
    assert "detail" in unauth_body

    # 2. Switch ke manufaktur & tambah sertifikat EXPIRED pada EMP-003 (gate K3 SCM)
    sw = hrm_client.post("/api/v1/system/switch-theme", json={"theme_key": "manufaktur", "preserve_partners": True})
    assert sw.status_code == 200
    emps = hrm_client.get("/api/v1/employees").json()
    emp3 = next(e for e in emps if e["employee_code"] == "EMP-003")

    cert_exp = hrm_client.post(
        "/api/v1/certifications",
        json={
            "employee_id": emp3["id"],
            "cert_name": "K3 Operator Press",
            "issuer": "Kemnaker RI",
            "issued_date": "2023-01-01",
            "expiry_date": "2024-01-01",
            "status": "EXPIRED",
        },
    )
    assert cert_exp.status_code == 201

    tok = hrm_client.post("/oauth/token", json={"client_id": "kel8_scm", "client_secret": "secret-kel8-scm"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    ops_all = hrm_client.get("/api/v1/external/employees?role=SCM_OPS", headers=headers).json()["items"]
    ext_emp3 = next(it for it in ops_all if it["employee_code"] == "EMP-003")
    assert ext_emp3["cost_center"] == "CC-200"
    assert ext_emp3["k3_status"] == "EXPIRED"
    assert ext_emp3["k3_valid"] is False
    assert ext_emp3["assignable"] is False

    # Filter k3_valid=true wajib mengecualikan EMP-003
    ops_valid = hrm_client.get("/api/v1/external/employees?role=SCM_OPS&k3_valid=true", headers=headers).json()["items"]
    assert all(it["employee_code"] != "EMP-003" for it in ops_valid)

    # Alias role=sales wajib mengembalikan CRM_SALES
    sales_alias = hrm_client.get("/api/v1/external/employees?role=sales", headers=headers)
    assert sales_alias.status_code == 200
    assert sales_alias.json()["total"] >= 2
    assert all(it["integration_role"] == "CRM_SALES" for it in sales_alias.json()["items"])


def test_contract_h1_to_h9_budget_payroll_idempotency_and_payslip_gate(hrm_client: TestClient):
    import requests

    p_fin, p_crm, p_scm = _free_port(), _free_port(), _free_port()
    s_fin = _start_uvicorn_bg(fin_app, p_fin)
    s_crm = _start_uvicorn_bg(crm_app, p_crm)
    s_scm = _start_uvicorn_bg(scm_app, p_scm)
    try:
        sw = hrm_client.post("/api/v1/system/switch-theme", json={"theme_key": "manufaktur", "preserve_partners": True})
        assert sw.status_code == 200

        partners = {p["partner_key"]: p for p in hrm_client.get("/api/v1/integration/partners").json()}
        for key, port in (("keuangan", p_fin), ("crm", p_crm), ("scm", p_scm)):
            p = partners[key]
            r = hrm_client.put(
                f"/api/v1/integration/partners/{key}",
                json={
                    "base_url": f"http://127.0.0.1:{port}",
                    "auth_type": p["auth_type"],
                    "token_endpoint": p["token_endpoint"],
                    "client_id": p["client_id"],
                    "client_secret": p["client_secret"],
                    "api_key_header": p["api_key_header"],
                    "api_key_value": p["api_key_value"],
                    "endpoints": p["endpoints"],
                    "field_mapping": p["field_mapping"],
                    "is_active": True,
                },
            )
            assert r.status_code == 200

        # H8: Sisa anggaran CC-300 awal 150.000.000 IDR
        rem = hrm_client.get("/api/v1/budgets/CC-300/remaining?period=2026-11")
        assert rem.status_code == 200
        assert rem.json()["remaining_minor"] == 150_000_000
        assert rem.json()["currency"] == "IDR"

        # H1 Insufficient budget -> 422 BUDGET_INSUFFICIENT & tanpa reservasi sebagian
        mr_over = hrm_client.post(
            "/api/v1/manpower-requests",
            json={
                "requester_system": "SCM",
                "cost_center": "CC-300",
                "position_title": "Operator Overbudget",
                "headcount": 20,
                "estimated_salary": 50_000_000,
                "period": "2026-11",
                "reason": "Uji penolakan 422 BUDGET_INSUFFICIENT",
            },
        ).json()
        res_over = hrm_client.post(f"/api/v1/manpower-requests/{mr_over['id']}/check-budget")
        assert res_over.status_code == 422
        assert res_over.json()["error"]["code"] == "BUDGET_INSUFFICIENT"
        rem_after_over = hrm_client.get("/api/v1/budgets/CC-300/remaining?period=2026-11").json()
        assert rem_after_over["remaining_minor"] == 150_000_000

        # H1 Pending approval (> 100jt dan <= 150jt)
        mr_pend = hrm_client.post(
            "/api/v1/manpower-requests",
            json={
                "requester_system": "SCM",
                "cost_center": "CC-200",
                "position_title": "Tim CNC Khusus",
                "headcount": 12,
                "estimated_salary": 10_000_000,
                "period": "2026-11",
                "reason": "Uji PENDING_APPROVAL > 100jt",
            },
        ).json()
        res_pend = hrm_client.post(f"/api/v1/manpower-requests/{mr_pend['id']}/check-budget")
        assert res_pend.status_code == 200
        assert res_pend.json()["finance_budget_status"] == "PENDING_APPROVAL"

        # H1 Normal approved MR (MR-2026-001: 2 * 6.5jt = 13jt di CC-300)
        mrs = hrm_client.get("/api/v1/manpower-requests").json()
        mr1 = next(m for m in mrs if m["request_code"] == "MR-2026-001")
        res_ok = hrm_client.post(f"/api/v1/manpower-requests/{mr1['id']}/check-budget")
        assert res_ok.status_code == 200
        assert res_ok.json()["finance_budget_status"] == "APPROVED"
        rem_after_mr1 = hrm_client.get("/api/v1/budgets/CC-300/remaining?period=2026-11").json()
        assert rem_after_mr1["remaining_minor"] == 150_000_000 - 13_000_000

        # H6 Total mismatch langsung ke Mock Keuangan -> 422 PAYROLL_TOTAL_MISMATCH
        fin_tok = requests.post(
            f"http://127.0.0.1:{p_fin}/oauth/token",
            json={"client_id": "hrm_kel12", "client_secret": "rahasia-hrm-ke-keuangan"},
            timeout=5,
        ).json()["access_token"]
        mismatch = requests.post(
            f"http://127.0.0.1:{p_fin}/v1/payroll-accruals",
            headers={"Authorization": f"Bearer {fin_tok}", "Idempotency-Key": "payroll-mismatch-1"},
            json={
                "payroll_run_id": "PAY-MISMATCH",
                "period": "2026-11",
                "currency": "IDR",
                "total_employees": 1,
                "total_gross_minor": 10_000_000,
                "total_deductions_minor": 500_000,
                "total_net_minor": 9_500_000,
                "lines": [{"employee_code": "EMP-001", "cost_center": "CC-100", "gross_salary_minor": 10_000_000, "net_salary_minor": 9_000_000}],
            },
            timeout=5,
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "PAYROLL_TOTAL_MISMATCH"

        # H2, H5, H9: Generate payroll -> cek cost_center -> slip terkunci 422 -> submit accrual (POSTED)
        gen = hrm_client.post("/api/v1/payroll/generate", json={"period": "2026-11", "sync_external": True})
        assert gen.status_code == 200
        items = gen.json()["payroll_run"]["items"]
        assert all(it.get("cost_center") for it in items)
        first_item_id = items[0]["id"]

        slip_locked = hrm_client.get(f"/api/v1/payroll/payslip/{first_item_id}")
        assert slip_locked.status_code == 422
        assert slip_locked.json()["error"]["code"] == "PAYSLIP_NOT_PAID"

        sub = hrm_client.post("/api/v1/payroll/2026-11/submit-finance")
        assert sub.status_code == 200
        assert sub.json()["status"] == "SENT_TO_FINANCE"
        assert sub.json()["detail"]["status"] == "POSTED"

        # Cek status via GET /v1/payroll-accruals/{run_id}
        polled = hrm_client.post("/api/v1/payroll/2026-11/sync-finance-status")
        assert polled.status_code == 200
        assert polled.json()["remote_status"] == "POSTED"
        assert polled.json()["local_status"] == "SENT_TO_FINANCE"

        # Reservasi anggaran periode 2026-11 dilepas saat PayrollAccrual diposting
        rem_released = hrm_client.get("/api/v1/budgets/CC-300/remaining?period=2026-11").json()
        assert rem_released["remaining_minor"] == 150_000_000

        # H4 & H7: Callback FAILED -> tetap SENT_TO_FINANCE, idempotent replay -> 200, conflict -> 409
        cb_tok = hrm_client.post("/oauth/token", json={"client_id": "kel2_keuangan", "client_secret": "secret-kel2-keuangan"}).json()["access_token"]
        fail_payload = {"payment_status": "FAILED", "finance_ref": sub.json()["finance_batch_ref"], "note": "Gagal transfer bank"}

        cb_fail = hrm_client.post(
            "/api/v1/external/payroll/PAY-2026-11/payment-callback",
            headers={"Authorization": f"Bearer {cb_tok}", "Idempotency-Key": "pay-cb-fail-1"},
            json=fail_payload,
        )
        assert cb_fail.status_code == 200
        assert cb_fail.json()["status"] == "SENT_TO_FINANCE"
        assert cb_fail.json()["payment_status"] == "FAILED"

        # Replay payload sama -> 200 tanpa error
        cb_replay = hrm_client.post(
            "/api/v1/external/payroll/PAY-2026-11/payment-callback",
            headers={"Authorization": f"Bearer {cb_tok}", "Idempotency-Key": "pay-cb-fail-1"},
            json=fail_payload,
        )
        assert cb_replay.status_code == 200
        assert cb_replay.json()["status"] == "SENT_TO_FINANCE"

        # Replay key sama + payload beda -> 409 IDEMPOTENCY_CONFLICT
        cb_conflict = hrm_client.post(
            "/api/v1/external/payroll/PAY-2026-11/payment-callback",
            headers={"Authorization": f"Bearer {cb_tok}", "Idempotency-Key": "pay-cb-fail-1"},
            json={"payment_status": "PAID", "finance_ref": sub.json()["finance_batch_ref"], "note": "Payload beda"},
        )
        assert cb_conflict.status_code == 409
        assert cb_conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

        # H3 & H9: Callback PAID -> status PAID -> slip gaji terbuka 200
        cb_paid = hrm_client.post(
            "/api/v1/external/payroll/PAY-2026-11/payment-callback",
            headers={"Authorization": f"Bearer {cb_tok}", "Idempotency-Key": "pay-cb-paid-1"},
            json={"payment_status": "PAID", "finance_ref": sub.json()["finance_batch_ref"], "note": "Lunas via contract test"},
        )
        assert cb_paid.status_code == 200
        assert cb_paid.json()["status"] == "PAID"

        slip_ok = hrm_client.get(f"/api/v1/payroll/payslip/{first_item_id}")
        assert slip_ok.status_code == 200
        assert slip_ok.json()["batch_status"] == "PAID"
        assert slip_ok.json()["cost_center"]
    finally:
        s_fin.should_exit = True
        s_crm.should_exit = True
        s_scm.should_exit = True
