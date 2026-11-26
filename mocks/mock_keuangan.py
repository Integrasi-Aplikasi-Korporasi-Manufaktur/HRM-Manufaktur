"""Simulator Kasar Kelompok 2: Sistem Keuangan & Akuntansi (Port 5001) — Kontrak Kanonik 4 Divisi."""
import hashlib
import html
import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import uvicorn
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from mocks.common_mock import call_hrm_endpoint, create_mock_app, get_root_prefix, render_rough_html

app, auth_dep = create_mock_app(
    service_name="Sistem Keuangan (Mock Kel. 2)",
    group_label="Kelompok 2",
    expected_client_id="hrm_kel12",
    expected_client_secret="rahasia-hrm-ke-keuangan",
)

AUTO_APPROVE_LIMIT_MINOR = 100_000_000
PAYROLL_DISBURSEMENTS: dict[str, dict[str, Any]] = {}
BUDGET_REQUESTS: list[dict[str, Any]] = []
COST_CENTER_BUDGETS: dict[str, dict[str, int]] = {}
IDEMPOTENCY_STORE: dict[str, dict[str, Any]] = {}
AUTO_APPROVE_BUDGET = {"enabled": True}


def reset_mock_state() -> None:
    """Mereset state memori simulator Keuangan agar bersih sebelum demo atau pengujian."""
    PAYROLL_DISBURSEMENTS.clear()
    BUDGET_REQUESTS.clear()
    IDEMPOTENCY_STORE.clear()
    AUTO_APPROVE_BUDGET["enabled"] = True
    COST_CENTER_BUDGETS.clear()
    COST_CENTER_BUDGETS.update({
        "CC-100": {"allocated_minor": 150_000_000, "reserved_minor": 0, "spent_minor": 0},
        "CC-200": {"allocated_minor": 250_000_000, "reserved_minor": 0, "spent_minor": 0},
        "CC-300": {"allocated_minor": 150_000_000, "reserved_minor": 0, "spent_minor": 0},
        "CC-400": {"allocated_minor": 150_000_000, "reserved_minor": 0, "spent_minor": 0},
        "CC-500": {"allocated_minor": 150_000_000, "reserved_minor": 0, "spent_minor": 0},
    })


reset_mock_state()


def _req_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    rid = _req_id(request)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": rid}, "detail": code},
        headers={"X-Request-ID": rid},
    )


def _payload_hash(canon: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(canon, sort_keys=True).encode("utf-8")).hexdigest()


def _check_idempotency(request: Request, p_hash: str) -> tuple[str, JSONResponse | None]:
    idem_key = request.headers.get("Idempotency-Key", "").strip()
    if not idem_key or idem_key not in IDEMPOTENCY_STORE:
        return idem_key, None
    rec = IDEMPOTENCY_STORE[idem_key]
    if rec["payload_hash"] == p_hash:
        return idem_key, JSONResponse(
            status_code=rec["status_code"],
            content=rec["body"],
            headers={"X-Request-ID": _req_id(request)},
        )
    return idem_key, _error_response(
        request,
        409,
        "IDEMPOTENCY_CONFLICT",
        "Idempotency-Key sudah digunakan dengan payload berbeda.",
    )


def _store_idempotency(idem_key: str, p_hash: str, status_code: int, body: dict[str, Any]) -> None:
    if idem_key:
        IDEMPOTENCY_STORE[idem_key] = {
            "payload_hash": p_hash,
            "status_code": status_code,
            "body": body,
        }


def _get_or_init_budget(cost_center: str) -> dict[str, int]:
    if cost_center not in COST_CENTER_BUDGETS:
        COST_CENTER_BUDGETS[cost_center] = {
            "allocated_minor": 150_000_000,
            "reserved_minor": 0,
            "spent_minor": 0,
        }
    return COST_CENTER_BUDGETS[cost_center]


def _remaining_minor(b: dict[str, int]) -> int:
    return max(0, b["allocated_minor"] - b["reserved_minor"] - b["spent_minor"])


class PayrollAccrualIn(BaseModel):
    payroll_run_id: Optional[str] = None
    run_id: Optional[str] = None
    batch_code: Optional[str] = None
    period: str
    currency: str = "IDR"
    total_employees: int
    total_gross_minor: Optional[int] = None
    total_gross: Optional[int] = None
    total_deductions_minor: Optional[int] = None
    total_deductions: Optional[int] = None
    total_net_minor: Optional[int] = None
    total_net: Optional[int] = None
    lines: list[dict[str, Any]] = []
    rincian_karyawan: list[dict[str, Any]] = []


class BudgetReservationIn(BaseModel):
    manpower_request_id: Optional[str] = None
    request_code: Optional[str] = None
    cost_center: str = "CC-300"
    period: str = "2026-11"
    requester_system: str = "INTERNAL"
    position_title: str
    headcount: int = 1
    estimated_salary_minor: Optional[int] = None
    estimated_salary_per_head: Optional[int] = None
    amount_minor: Optional[int] = None
    total_monthly_budget: Optional[int] = None
    currency: str = "IDR"
    reason: str = ""


def _handle_payroll_accrual(payload: PayrollAccrualIn, request: Request):
    run_id = payload.payroll_run_id or payload.run_id or payload.batch_code or ""
    if not run_id:
        return _error_response(request, 400, "BAD_REQUEST", "payroll_run_id/run_id/batch_code wajib diisi.")

    tot_gross = payload.total_gross_minor if payload.total_gross_minor is not None else (payload.total_gross or 0)
    tot_ded = payload.total_deductions_minor if payload.total_deductions_minor is not None else (payload.total_deductions or 0)
    tot_net = payload.total_net_minor if payload.total_net_minor is not None else (payload.total_net or 0)
    items = payload.lines or payload.rincian_karyawan

    p_hash = _payload_hash({
        "run_id": run_id,
        "period": payload.period,
        "currency": payload.currency,
        "total_employees": payload.total_employees,
        "total_gross_minor": tot_gross,
        "total_deductions_minor": tot_ded,
        "total_net_minor": tot_net,
        "lines": items,
    })
    idem_key, conflict_or_replay = _check_idempotency(request, p_hash)
    if conflict_or_replay is not None:
        return conflict_or_replay

    # Kontrak H6: total baris karyawan wajib sama dengan total batch
    if items:
        sum_net = sum(int(it.get("net_salary_minor", it.get("gaji_bersih", 0)) or 0) for it in items)
        has_gross = any("gross_salary_minor" in it or "gross_salary" in it for it in items)
        sum_gross = sum(int(it.get("gross_salary_minor", it.get("gross_salary", 0)) or 0) for it in items)
        if sum_net != tot_net or (has_gross and sum_gross != tot_gross):
            err = {
                "error": {
                    "code": "PAYROLL_TOTAL_MISMATCH",
                    "message": (
                        f"Selisih total batch vs baris karyawan: net({tot_net} != {sum_net}), "
                        f"gross({tot_gross} != {sum_gross})."
                    ),
                    "request_id": _req_id(request),
                },
                "detail": "PAYROLL_TOTAL_MISMATCH",
            }
            _store_idempotency(idem_key, p_hash, 422, err)
            return JSONResponse(status_code=422, content=err, headers={"X-Request-ID": _req_id(request)})

    # Lepas reservasi anggaran rekrutmen untuk periode terkait tepat satu kali (H1/K-E)
    released_count = 0
    for b in BUDGET_REQUESTS:
        if not b["released"] and b["period"] == payload.period and b["status"] in ("APPROVED", "PENDING_APPROVAL"):
            cc_b = _get_or_init_budget(b["cost_center"])
            cc_b["reserved_minor"] = max(0, cc_b["reserved_minor"] - b["amount_minor"])
            b["released"] = True
            released_count += 1

    # Jurnal per cost_center (H5: Dr Beban Gaji / Cr Utang Gaji)
    cc_totals: dict[str, int] = {}
    for it in items:
        cc = str(it.get("cost_center") or "CC-100")
        cc_totals[cc] = cc_totals.get(cc, 0) + int(it.get("gross_salary_minor", it.get("net_salary_minor", 0)) or 0)

    ref = f"FIN-PAY-{payload.period.replace('-', '')}-{len(PAYROLL_DISBURSEMENTS) + 1:02d}"
    PAYROLL_DISBURSEMENTS[run_id] = {
        "batch_code": run_id,
        "payroll_run_id": run_id,
        "period": payload.period,
        "total_employees": payload.total_employees,
        "total_gross": tot_gross,
        "total_deductions": tot_ded,
        "total_net": tot_net,
        "finance_ref": ref,
        "status": "POSTED",
        "payment_status": "UNPAID",
        "payment_attempt": 0,
        "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rincian": items,
        "cost_center_summary": cc_totals,
        "released_reservations": released_count,
    }
    body = {
        "finance_ref": ref,
        "run_id": run_id,
        "payroll_run_id": run_id,
        "batch_code": run_id,
        "status": "POSTED",
        "payment_status": "UNPAID",
        "currency": "IDR",
        "cost_center_summary": cc_totals,
        "journal_entry": f"Dr Beban Gaji ({', '.join(cc_totals.keys()) or 'CC-ALL'}) / Cr Utang Gaji",
        "message": f"PayrollAccrual {run_id} diposting (POSTED). Menunggu maker-checker bayar.",
    }
    _store_idempotency(idem_key, p_hash, 200, body)
    return body


def _handle_get_payroll_accrual(run_id: str, request: Request):
    item = PAYROLL_DISBURSEMENTS.get(run_id)
    if not item:
        return _error_response(request, 404, "NOT_FOUND", f"Payroll accrual {run_id} tidak ditemukan.")
    return {
        "run_id": run_id,
        "payroll_run_id": run_id,
        "batch_code": run_id,
        "status": item["status"],
        "payment_status": item["payment_status"],
        "finance_ref": item["finance_ref"],
        "note": f"Status Keuangan: {item['status']} (PaymentStatus: {item['payment_status']})",
    }


def _handle_budget_reservation(payload: BudgetReservationIn, request: Request):
    mr_id = payload.manpower_request_id or payload.request_code or ""
    if not mr_id:
        return _error_response(request, 400, "BAD_REQUEST", "manpower_request_id/request_code wajib diisi.")
    sal_minor = (
        payload.estimated_salary_minor
        if payload.estimated_salary_minor is not None
        else (payload.estimated_salary_per_head or 0)
    )
    amt_minor = (
        payload.amount_minor
        if payload.amount_minor is not None
        else (payload.total_monthly_budget if payload.total_monthly_budget is not None else payload.headcount * sal_minor)
    )

    p_hash = _payload_hash({
        "manpower_request_id": mr_id,
        "cost_center": payload.cost_center,
        "period": payload.period,
        "headcount": payload.headcount,
        "estimated_salary_minor": sal_minor,
        "amount_minor": amt_minor,
        "currency": payload.currency,
    })
    idem_key, conflict_or_replay = _check_idempotency(request, p_hash)
    if conflict_or_replay is not None:
        return conflict_or_replay

    cc_budget = _get_or_init_budget(payload.cost_center)
    remaining = _remaining_minor(cc_budget)
    if amt_minor > remaining:
        err = {
            "error": {
                "code": "BUDGET_INSUFFICIENT",
                "message": (
                    f"Sisa anggaran {payload.cost_center} periode {payload.period} "
                    f"(Rp {remaining:,}) tidak mencukupi untuk reservasi Rp {amt_minor:,}."
                ),
                "request_id": _req_id(request),
            },
            "detail": "BUDGET_INSUFFICIENT",
        }
        _store_idempotency(idem_key, p_hash, 422, err)
        return JSONResponse(status_code=422, content=err, headers={"X-Request-ID": _req_id(request)})

    ref = f"FIN-BGT-{len(BUDGET_REQUESTS) + 1:03d}"
    if not AUTO_APPROVE_BUDGET["enabled"]:
        res_status = "REJECTED"
        approved = False
        msg = "Mode simulasi penolakan aktif — reservasi anggaran ditolak Keuangan."
    elif amt_minor > AUTO_APPROVE_LIMIT_MINOR:
        cc_budget["reserved_minor"] += amt_minor
        res_status = "PENDING_APPROVAL"
        approved = False
        msg = "Melebihi batas auto-approval Rp 100.000.000 — menunggu persetujuan Finance Manager."
    else:
        cc_budget["reserved_minor"] += amt_minor
        res_status = "APPROVED"
        approved = True
        msg = f"BudgetReservation disetujui & dikunci untuk {payload.cost_center}."

    new_remaining = _remaining_minor(cc_budget)
    BUDGET_REQUESTS.insert(
        0,
        {
            "finance_ref": ref,
            "request_code": mr_id,
            "cost_center": payload.cost_center,
            "period": payload.period,
            "position_title": payload.position_title,
            "headcount": payload.headcount,
            "amount_minor": amt_minor,
            "status": res_status,
            "approved": approved,
            "released": False,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    body = {
        "reservation_id": ref,
        "finance_ref": ref,
        "manpower_request_id": mr_id,
        "cost_center": payload.cost_center,
        "period": payload.period,
        "amount_minor": amt_minor,
        "remaining_minor": new_remaining,
        "currency": "IDR",
        "status": res_status,
        "approved": approved,
        "message": msg,
    }
    _store_idempotency(idem_key, p_hash, 200, body)
    return body


@app.post("/v1/payroll-accruals")
def receive_payroll_accrual(payload: PayrollAccrualIn, request: Request, _=auth_dep):
    return _handle_payroll_accrual(payload, request)


@app.get("/v1/payroll-accruals/{run_id}")
def get_payroll_accrual(run_id: str, request: Request, _=auth_dep):
    return _handle_get_payroll_accrual(run_id, request)


@app.post("/v1/budget-reservations")
def create_budget_reservation(payload: BudgetReservationIn, request: Request, _=auth_dep):
    return _handle_budget_reservation(payload, request)


@app.get("/v1/budgets/{cost_center}/remaining")
def get_budget_remaining(cost_center: str, period: str = "2026-11", _=auth_dep):
    b = _get_or_init_budget(cost_center)
    return {
        "cost_center": cost_center,
        "period": period,
        "allocated_minor": b["allocated_minor"],
        "reserved_minor": b["reserved_minor"],
        "spent_minor": b["spent_minor"],
        "remaining_minor": _remaining_minor(b),
        "currency": "IDR",
    }


@app.get("/v1/reports/budget")
def get_budget_report(period: str = "2026-11", _=auth_dep):
    return {
        "period": period,
        "currency": "IDR",
        "items": [
            {
                "cost_center": cc,
                **vals,
                "remaining_minor": _remaining_minor(vals),
            }
            for cc, vals in COST_CENTER_BUDGETS.items()
        ],
    }


# Alias kompatibilitas endpoint lama
@app.post("/v1/payroll/disbursement")
def receive_payroll_legacy(payload: PayrollAccrualIn, request: Request, _=auth_dep):
    return _handle_payroll_accrual(payload, request)


@app.get("/v1/payroll/status/{batch_code}")
def get_payroll_status_legacy(batch_code: str, request: Request, _=auth_dep):
    return _handle_get_payroll_accrual(batch_code, request)


@app.post("/v1/anggaran/cek-rekrutmen")
def check_recruitment_budget_legacy(payload: BudgetReservationIn, request: Request, _=auth_dep):
    return _handle_budget_reservation(payload, request)


@app.post("/ui/bayar-payroll")
def ui_pay_payroll(request: Request, batch_code: str = Form(...)):
    item = PAYROLL_DISBURSEMENTS.get(batch_code)
    if item:
        item["payment_attempt"] += 1
        item["status"] = "PAID"
        item["payment_status"] = "PAID"
        idem = f"payment:payroll:{batch_code}:paid-{item['payment_attempt']}"
        call_hrm_endpoint(
            "POST",
            f"/api/v1/external/payroll/{batch_code}/payment-callback",
            "kel2_keuangan",
            "secret-kel2-keuangan",
            json_body={
                "status": "PAID",
                "payment_status": "PAID",
                "finance_ref": item["finance_ref"],
                "amount_minor": item["total_net"],
                "currency": "IDR",
                "note": "Dana gaji telah ditransfer oleh Keuangan (Kel. 2) via maker-checker",
            },
            extra_headers={"Idempotency-Key": idem},
        )
    root = get_root_prefix(request)
    return RedirectResponse(f"{root}/", status_code=303)


@app.post("/ui/gagal-bayar-payroll")
def ui_fail_payroll(request: Request, batch_code: str = Form(...)):
    item = PAYROLL_DISBURSEMENTS.get(batch_code)
    if item:
        item["payment_attempt"] += 1
        item["payment_status"] = "FAILED"
        # Status entitas Keuangan tetap POSTED meski PaymentStatus FAILED
        idem = f"payment:payroll:{batch_code}:failed-{item['payment_attempt']}"
        call_hrm_endpoint(
            "POST",
            f"/api/v1/external/payroll/{batch_code}/payment-callback",
            "kel2_keuangan",
            "secret-kel2-keuangan",
            json_body={
                "status": "FAILED",
                "payment_status": "FAILED",
                "finance_ref": item["finance_ref"],
                "amount_minor": item["total_net"],
                "currency": "IDR",
                "note": "Simulasi gagal transfer bank (status POSTED dipertahankan untuk retry)",
            },
            extra_headers={"Idempotency-Key": idem},
        )
    root = get_root_prefix(request)
    return RedirectResponse(f"{root}/", status_code=303)


@app.post("/ui/toggle-budget")
def ui_toggle_budget(request: Request):
    AUTO_APPROVE_BUDGET["enabled"] = not AUTO_APPROVE_BUDGET["enabled"]
    root = get_root_prefix(request)
    return RedirectResponse(f"{root}/", status_code=303)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    root = get_root_prefix(request)
    rows_pay = "".join(
        f"""<tr>
          <td>{html.escape(v['batch_code'])}</td>
          <td>{html.escape(v['finance_ref'])}</td>
          <td>{v['total_employees']} org</td>
          <td>Rp {v['total_net']:,}</td>
          <td><b>{html.escape(v['status'])}</b> (PaymentStatus: <b>{html.escape(v['payment_status'])}</b>)</td>
          <td>
            {"<form method='post' action='" + root + "/ui/bayar-payroll' style='display:inline;'><input type='hidden' name='batch_code' value='" + html.escape(k) + "'><button type='submit'>Setujui & Bayar (LUNAS)</button></form> <form method='post' action='" + root + "/ui/gagal-bayar-payroll' style='display:inline;'><input type='hidden' name='batch_code' value='" + html.escape(k) + "'><button type='submit' style='background:#991b1b;'>Simulasi Gagal</button></form>" if v['status'] != 'PAID' else "Sudah Dibayar (PAID)"}
          </td>
        </tr>"""
        for k, v in PAYROLL_DISBURSEMENTS.items()
    ) or "<tr><td colspan='6'>Belum ada PayrollAccrual masuk dari HRM.</td></tr>"

    rows_bgt = "".join(
        f"""<tr>
          <td>{html.escape(b['finance_ref'])}</td>
          <td>{html.escape(b['request_code'])} ({html.escape(b['cost_center'])})</td>
          <td>{html.escape(b['position_title'])} ({b['headcount']})</td>
          <td>Rp {b['amount_minor']:,}</td>
          <td><b>{html.escape(b['status'])}</b>{' (Released)' if b['released'] else ''}</td>
        </tr>"""
        for b in BUDGET_REQUESTS
    ) or "<tr><td colspan='5'>Belum ada BudgetReservation rekrutmen.</td></tr>"

    rows_cc = "".join(
        f"""<tr>
          <td><b>{html.escape(cc)}</b></td>
          <td>Rp {vals['allocated_minor']:,}</td>
          <td>Rp {vals['reserved_minor']:,}</td>
          <td>Rp {_remaining_minor(vals):,}</td>
        </tr>"""
        for cc, vals in COST_CENTER_BUDGETS.items()
    )

    mode_label = "AUTO-APPROVE (<= 100jt, sisa cukup)" if AUTO_APPROVE_BUDGET["enabled"] else "AUTO-REJECT (Simulasi Tolak)"
    body = f"""
    <div class="box">
      <h3>1. PayrollAccrual Masuk (POST /v1/payroll-accruals)</h3>
      <table>
        <tr><th>Batch / run_id</th><th>Ref Keuangan</th><th>Pegawai</th><th>Total Net (IDR)</th><th>Status & PaymentStatus</th><th>Aksi</th></tr>
        {rows_pay}
      </table>
    </div>
    <div class="box">
      <h3>2. Reservasi Anggaran Rekrutmen (POST /v1/budget-reservations)</h3>
      <form method="post" action="{root}/ui/toggle-budget" style="margin-bottom:8px;">
        Mode Persetujuan: <b>{mode_label}</b>
        <button type="submit" style="margin-left:8px;">Ganti Mode</button>
      </form>
      <table>
        <tr><th>Ref</th><th>Kode MR & CC</th><th>Posisi</th><th>Nominal (IDR)</th><th>Status</th></tr>
        {rows_bgt}
      </table>
    </div>
    <div class="box">
      <h3>3. Sisa Anggaran Per Cost Center (GET /v1/budgets/{{cost_center}}/remaining)</h3>
      <table>
        <tr><th>Cost Center</th><th>Pagu (IDR)</th><th>Reserved</th><th>Sisa (Remaining)</th></tr>
        {rows_cc}
      </table>
    </div>
    """
    return render_rough_html("Sistem Keuangan — Kelompok 2 (Port 5001)", "KELOMPOK 2: KEUANGAN", body)


if __name__ == "__main__":
    port = int(os.environ.get("MOCK_KEUANGAN_PORT", "5001"))
    print(f"[Mock Keuangan Kel. 2] http://127.0.0.1:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
