"""Adapter Integrasi Lintas Kelompok (Keuangan Kel. 2, CRM Kel. 7, SCM Kel. 8)."""
import json
import time
import uuid
from datetime import datetime
from typing import Any

import requests

from hrm_app.auth import record_integration_log
from hrm_app.config import DEFAULT_PERIOD
from hrm_app.database import db_session

# Cache token outbound sementara di memori agar tidak selalu meminta token baru
_OUTBOUND_TOKEN_CACHE: dict[str, dict[str, Any]] = {}


def _get_partner(partner_key: str) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM integration_partners WHERE partner_key = ?",
            (partner_key,),
        ).fetchone()
    if not row:
        raise ValueError(f"Konfigurasi partner '{partner_key}' tidak ditemukan.")
    data = dict(row)
    data["endpoints"] = json.loads(data["endpoints_json"])
    data["field_mapping"] = json.loads(data["field_mapping_json"])
    return data


def _build_auth_headers(partner: dict[str, Any], force_refresh: bool = False) -> dict[str, str]:
    headers = {
        "ngrok-skip-browser-warning": "true",
        "Accept": "application/json",
    }
    auth_type = partner.get("auth_type", "NONE")
    if auth_type == "API_KEY":
        h_name = partner.get("api_key_header") or "X-API-Key"
        headers[h_name] = partner.get("api_key_value") or ""
        return headers

    if auth_type == "OAUTH_BEARER":
        pkey = partner["partner_key"]
        cached = _OUTBOUND_TOKEN_CACHE.get(pkey)
        if not force_refresh and cached and cached["exp"] > time.time() + 10:
            headers["Authorization"] = f"Bearer {cached['token']}"
            return headers

        base_url = partner["base_url"].rstrip("/")
        tok_ep = "/" + partner.get("token_endpoint", "/oauth/token").lstrip("/")
        token_url = f"{base_url}{tok_ep}"
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                token_url,
                json={
                    "client_id": partner.get("client_id", ""),
                    "client_secret": partner.get("client_secret", ""),
                },
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=8,
            )
            ms = int((time.perf_counter() - t0) * 1000)
            if resp.status_code == 200:
                payload = resp.json()
                token = payload.get("access_token", "")
                ttl = int(payload.get("expires_in", 600))
                _OUTBOUND_TOKEN_CACHE[pkey] = {"token": token, "exp": time.time() + ttl}
                headers["Authorization"] = f"Bearer {token}"
                record_integration_log(
                    "OUTBOUND", pkey, "POST", token_url, 200, ms,
                    f"Minta token client_id={partner.get('client_id')}",
                    "Token Bearer diterima", True,
                )
            else:
                record_integration_log(
                    "OUTBOUND", pkey, "POST", token_url, resp.status_code, ms,
                    f"Minta token client_id={partner.get('client_id')}",
                    resp.text[:250], False,
                )
        except requests.RequestException as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            record_integration_log(
                "OUTBOUND", pkey, "POST", token_url, 503, ms,
                f"Minta token client_id={partner.get('client_id')}",
                f"Koneksi gagal: {exc}", False,
            )
    return headers


def _call_partner(
    partner_key: str,
    method: str,
    endpoint_key: str,
    path_params: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    require_auth: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> tuple[bool, int, Any, dict[str, Any]]:
    """Memanggil API sistem mitra dengan pencatatan log dan dukungan adapter mapping."""
    partner = _get_partner(partner_key)
    if not partner["is_active"]:
        return False, 503, {"error": f"Integrasi {partner_key} sedang dinonaktifkan."}, partner

    ep_template = partner["endpoints"].get(endpoint_key)
    if not ep_template:
        return False, 400, {"error": f"Endpoint '{endpoint_key}' belum dikonfigurasi."}, partner

    ep_path = ep_template.format(**(path_params or {}))
    url = f"{partner['base_url'].rstrip('/')}/{ep_path.lstrip('/')}"
    req_id = (extra_headers or {}).get("X-Request-ID") or str(uuid.uuid4())
    headers = (
        _build_auth_headers(partner)
        if require_auth
        else {"ngrok-skip-browser-warning": "true", "Accept": "application/json"}
    )
    if extra_headers:
        for k, v in extra_headers.items():
            if k.lower() != "authorization":
                headers[k] = v
    headers.setdefault("X-Request-ID", req_id)

    t0 = time.perf_counter()
    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=10,
        )
        # Retry satu kali jika token kedaluwarsa (401) pada OAUTH_BEARER
        if resp.status_code == 401 and require_auth and partner.get("auth_type") == "OAUTH_BEARER":
            headers = _build_auth_headers(partner, force_refresh=True)
            if extra_headers:
                for k, v in extra_headers.items():
                    if k.lower() != "authorization":
                        headers[k] = v
            headers.setdefault("X-Request-ID", req_id)
            resp = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=10,
            )

        ms = int((time.perf_counter() - t0) * 1000)
        try:
            body_data = resp.json() if resp.content else {}
        except ValueError:
            body_data = {"raw": resp.text[:300]}

        ok = 200 <= resp.status_code < 300
        req_sum = json.dumps(json_body or params or {}, ensure_ascii=False)
        res_sum = json.dumps(body_data, ensure_ascii=False)
        record_integration_log(
            "OUTBOUND", partner_key, method.upper(), url, resp.status_code,
            ms, req_sum, res_sum, ok,
        )
        return ok, resp.status_code, body_data, partner
    except requests.RequestException as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        err = {"error": f"Tidak dapat terhubung ke {partner['partner_name']} ({url}): {exc}"}
        record_integration_log(
            "OUTBOUND", partner_key, method.upper(), url, 503, ms,
            json.dumps(json_body or params or {}, ensure_ascii=False), str(exc), False,
        )
        return False, 503, err, partner


def check_partner_health(partner_key: str) -> dict[str, Any]:
    """Mengecek status kesehatan server mitra dan memperbarui tabel integration_partners."""
    ok, code, data, partner = _call_partner(
        partner_key, "GET", "health", require_auth=False,
    )
    status_text = "ONLINE" if ok else "OFFLINE"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_session() as conn:
        conn.execute(
            "UPDATE integration_partners SET last_health_status = ?, last_checked_at = ? WHERE partner_key = ?",
            (status_text, now, partner_key),
        )
    return {
        "partner_key": partner_key,
        "partner_name": partner["partner_name"],
        "group_label": partner["group_label"],
        "base_url": partner["base_url"],
        "status": status_text,
        "status_code": code,
        "checked_at": now,
        "detail": data,
    }


def fetch_crm_commissions(period: str) -> dict[str, Any]:
    """Menarik data komisi & jumlah deal sales dari CRM (Kelompok 7) memakai field_mapping."""
    partner = _get_partner("crm")
    fmap = partner["field_mapping"]
    q_param = fmap.get("period_query_param", "periode")
    ok, code, data, _ = _call_partner("crm", "GET", "get_commissions", params={q_param: period})
    if not ok:
        return {"success": False, "status_code": code, "error": data, "commissions": {}}

    items_key = fmap.get("items_key", "items")
    raw_items = data if isinstance(data, list) else data.get(items_key, [])
    emp_field = fmap.get("employee_code_field", "kode_karyawan")
    comm_field = fmap.get("commission_field", "total_komisi")
    deals_field = fmap.get("deals_count_field", "jumlah_deal")

    comm_map: dict[str, dict[str, int]] = {}
    for item in raw_items:
        ecode = str(item.get(emp_field, "")).strip()
        if not ecode:
            continue
        comm_map[ecode] = {
            "commission": int(float(item.get(comm_field, 0) or 0)),
            "deals_count": int(item.get(deals_field, 0) or 0),
        }

    return {
        "success": True,
        "status_code": code,
        "period": period,
        "synced_count": len(comm_map),
        "commissions": comm_map,
    }


def fetch_scm_overtime(period: str) -> dict[str, Any]:
    """Menarik rekap lembur operasional dari SCM (Kelompok 8) dan menyimpannya ke attendance_logs."""
    partner = _get_partner("scm")
    fmap = partner["field_mapping"]
    q_param = fmap.get("period_query_param", "periode")
    ok, code, data, _ = _call_partner("scm", "GET", "get_overtime", params={q_param: period})
    if not ok:
        return {"success": False, "status_code": code, "error": data, "overtime": {}}

    items_key = fmap.get("items_key", "items")
    raw_items = data if isinstance(data, list) else data.get(items_key, [])
    emp_field = fmap.get("employee_code_field", "kode_karyawan")
    ot_field = fmap.get("overtime_hours_field", "total_jam_lembur")
    note_field = fmap.get("note_field", "catatan")

    sync_date = f"{period}-25"
    overtime_map: dict[str, dict[str, Any]] = {}

    with db_session() as conn:
        for item in raw_items:
            ecode = str(item.get(emp_field, "")).strip()
            hours = float(item.get(ot_field, 0) or 0)
            note = str(item.get(note_field, "Sinkronisasi lembur SCM") or "Sinkronisasi lembur SCM")
            if not ecode:
                continue
            emp_row = conn.execute(
                "SELECT id FROM employees WHERE employee_code = ?", (ecode,),
            ).fetchone()
            overtime_map[ecode] = {"overtime_hours": hours, "note": note, "matched_in_hrm": bool(emp_row)}
            if emp_row and hours > 0:
                conn.execute(
                    """
                    INSERT INTO attendance_logs (employee_id, work_date, status, regular_hours, overtime_hours, source, note)
                    VALUES (?, ?, 'HADIR', 0.0, ?, 'SCM_SYNC', ?)
                    ON CONFLICT(employee_id, work_date, source)
                    DO UPDATE SET overtime_hours = excluded.overtime_hours, note = excluded.note
                    """,
                    (emp_row["id"], sync_date, hours, f"[SCM] {note}"),
                )

    return {
        "success": True,
        "status_code": code,
        "period": period,
        "synced_count": len(overtime_map),
        "overtime": overtime_map,
    }


def submit_payroll_to_finance(payroll_run: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Mengirim tagihan rekap PayrollAccrual HRM ke sistem Keuangan (Kelompok 2)."""
    sum_gross = sum(int(it["gross_salary"]) for it in items)
    sum_ded = sum(int(it["tax_pph21"]) + int(it["bpjs_deduction"]) + int(it["absent_deduction"]) for it in items)
    sum_net = sum(int(it["net_salary"]) for it in items)
    if (
        sum_gross != int(payroll_run["total_gross"])
        or sum_ded != int(payroll_run["total_deductions"])
        or sum_net != int(payroll_run["total_net"])
    ):
        return {
            "success": False,
            "status_code": 422,
            "error": {
                "error": {
                    "code": "PAYROLL_TOTAL_MISMATCH",
                    "message": "Total baris karyawan tidak sama dengan total batch payroll.",
                }
            },
        }

    lines = [
        {
            "employee_code": it["employee_code"],
            "full_name": it["full_name"],
            "department_code": it.get("department_code", ""),
            "department_name": it["department_name"],
            "cost_center": it.get("cost_center", "CC-100"),
            "base_salary_minor": int(it["base_salary"]),
            "fixed_allowance_minor": int(it["fixed_allowance"]),
            "overtime_pay_minor": int(it["overtime_pay"]),
            "crm_commission_minor": int(it["crm_commission"]),
            "tax_pph21_minor": int(it["tax_pph21"]),
            "bpjs_deduction_minor": int(it["bpjs_deduction"]),
            "absent_deduction_minor": int(it["absent_deduction"]),
            "gross_salary_minor": int(it["gross_salary"]),
            "deductions_minor": int(it["tax_pph21"]) + int(it["bpjs_deduction"]) + int(it["absent_deduction"]),
            "net_salary_minor": int(it["net_salary"]),
            "bank_name": it["bank_name"],
            "bank_account": it["bank_account"],
        }
        for it in items
    ]
    payload = {
        "payroll_run_id": payroll_run["batch_code"],
        "run_id": payroll_run["batch_code"],
        "batch_code": payroll_run["batch_code"],
        "period": payroll_run["period"],
        "currency": "IDR",
        "total_employees": int(payroll_run["total_employees"]),
        "total_gross_minor": int(payroll_run["total_gross"]),
        "total_deductions_minor": int(payroll_run["total_deductions"]),
        "total_net_minor": int(payroll_run["total_net"]),
        "lines": lines,
    }
    idem_key = f"payroll-accrual:{payroll_run['batch_code']}:{payroll_run['period']}"
    ok, code, data, partner = _call_partner(
        "keuangan",
        "POST",
        "submit_payroll",
        json_body=payload,
        extra_headers={"Idempotency-Key": idem_key},
    )
    if not ok:
        return {"success": False, "status_code": code, "error": data}

    fmap = partner["field_mapping"]
    ref_field = fmap.get("reference_field", "finance_ref")
    finance_ref = str(data.get(ref_field) or data.get("reference_id") or f"FIN-{payroll_run['batch_code']}")
    fin_note = str(data.get("message") or "PayrollAccrual diterima (POSTED) oleh Keuangan, menunggu pencairan.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_session() as conn:
        conn.execute(
            """
            UPDATE payroll_runs
            SET status = 'SENT_TO_FINANCE', finance_batch_ref = ?, finance_note = ?, updated_at = ?
            WHERE id = ?
            """,
            (finance_ref, fin_note, now, payroll_run["id"]),
        )
    return {
        "success": True,
        "status_code": code,
        "finance_batch_ref": finance_ref,
        "status": "SENT_TO_FINANCE",
        "detail": data,
    }


def poll_payroll_status_from_finance(batch_code: str) -> dict[str, Any]:
    """Mengecek status pencairan gaji batch tertentu di Sistem Keuangan (Kelompok 2)."""
    ok, code, data, partner = _call_partner(
        "keuangan",
        "GET",
        "check_payroll_status",
        path_params={"run_id": batch_code, "batch_code": batch_code},
    )
    if not ok:
        return {"success": False, "status_code": code, "error": data}

    fmap = partner["field_mapping"]
    status_field = fmap.get("status_field", "status")
    remote_status = str(data.get(status_field) or data.get("status") or "").upper()
    payment_status = str(data.get("payment_status") or "").upper()
    fin_note = str(data.get("note") or data.get("message") or "")
    fin_ref = str(data.get(fmap.get("reference_field", "finance_ref"), "") or "")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mapped_local = (
        "PAID"
        if (remote_status in ("PAID", "LUNAS", "DISBURSED") or payment_status == "PAID")
        else "SENT_TO_FINANCE"
    )
    with db_session() as conn:
        conn.execute(
            """
            UPDATE payroll_runs
            SET status = ?,
                finance_batch_ref = COALESCE(NULLIF(?, ''), finance_batch_ref),
                finance_note = ?,
                updated_at = ?
            WHERE batch_code = ?
            """,
            (
                mapped_local,
                fin_ref,
                fin_note or f"Status dari Keuangan: {remote_status} (PaymentStatus: {payment_status or '-'})",
                now,
                batch_code,
            ),
        )
    return {
        "success": True,
        "status_code": code,
        "batch_code": batch_code,
        "remote_status": remote_status,
        "payment_status": payment_status or ("PAID" if mapped_local == "PAID" else "UNPAID"),
        "local_status": mapped_local,
        "detail": data,
    }


def check_budget_remaining_from_finance(cost_center: str, period: str = DEFAULT_PERIOD) -> dict[str, Any]:
    """Memeriksa sisa anggaran cost center tertentu di Sistem Keuangan (Kelompok 2)."""
    ok, code, data, _ = _call_partner(
        "keuangan",
        "GET",
        "check_budget_remaining",
        path_params={"cost_center": cost_center},
        params={"period": period},
    )
    if not ok:
        return {"success": False, "status_code": code, "cost_center": cost_center, "period": period, "error": data}
    return {"success": True, "status_code": code, "cost_center": cost_center, "period": period, "data": data}


def request_recruitment_budget_from_finance(manpower_req: dict[str, Any]) -> dict[str, Any]:
    """Mengajukan BudgetReservation rekrutmen karyawan baru ke Sistem Keuangan (Kelompok 2)."""
    period = manpower_req.get("period") or DEFAULT_PERIOD
    amount_minor = int(manpower_req["headcount"]) * int(manpower_req["estimated_salary"])
    payload = {
        "manpower_request_id": manpower_req["request_code"],
        "request_code": manpower_req["request_code"],
        "cost_center": manpower_req.get("cost_center") or "CC-300",
        "department_code": manpower_req.get("department_code") or "",
        "period": period,
        "headcount": int(manpower_req["headcount"]),
        "estimated_salary_minor": int(manpower_req["estimated_salary"]),
        "amount_minor": amount_minor,
        "currency": "IDR",
        "requester_system": manpower_req["requester_system"],
        "position_title": manpower_req["position_title"],
        "reason": manpower_req["reason"],
    }
    idem_key = f"budget-reservation:{manpower_req['request_code']}"
    ok, code, data, partner = _call_partner(
        "keuangan",
        "POST",
        "check_recruitment_budget",
        json_body=payload,
        extra_headers={"Idempotency-Key": idem_key},
    )
    if not ok:
        if code == 422:
            with db_session() as conn:
                conn.execute(
                    "UPDATE manpower_requests SET finance_budget_status = 'REJECTED' WHERE id = ?",
                    (manpower_req["id"],),
                )
            return {"success": False, "status_code": 422, "finance_budget_status": "REJECTED", "error": data}
        return {"success": False, "status_code": code, "error": data}

    fmap = partner["field_mapping"]
    raw_status = str(data.get("status") or "").upper()
    if raw_status in ("APPROVED", "PENDING_APPROVAL", "REJECTED"):
        new_status = raw_status
    else:
        approved = bool(data.get(fmap.get("approved_field", "approved"), False))
        new_status = "APPROVED" if approved else "REJECTED"
    fin_ref = str(
        data.get(fmap.get("reference_field", "finance_ref"))
        or data.get("reservation_id")
        or data.get("id")
        or f"BGT-{manpower_req['request_code']}"
    )

    with db_session() as conn:
        conn.execute(
            "UPDATE manpower_requests SET finance_budget_status = ?, finance_ref = ? WHERE id = ?",
            (new_status, fin_ref, manpower_req["id"]),
        )
    return {
        "success": True,
        "status_code": code,
        "finance_budget_status": new_status,
        "finance_ref": fin_ref,
        "detail": data,
    }
