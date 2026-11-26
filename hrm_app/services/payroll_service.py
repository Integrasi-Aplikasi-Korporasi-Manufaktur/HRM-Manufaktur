"""Layanan perhitungan dan pengelolaan penggajian (Payroll Engine) HRM Kelompok 12."""
from datetime import datetime
from typing import Any

from hrm_app.database import db_session
from hrm_app.services.integration_service import fetch_crm_commissions, fetch_scm_overtime


def _calculate_tax_and_bpjs(base_salary: int, gross_salary: int) -> tuple[int, int]:
    """Menghitung potongan BPJS (3% gaji pokok) dan PPh21 progresif sederhana."""
    bpjs = round(base_salary * 0.03)
    ptkp_bulanan = 4_500_000
    pkp = max(0, gross_salary - bpjs - ptkp_bulanan)
    tax = round(pkp * 0.05)
    return tax, bpjs


def generate_payroll(period: str, sync_external: bool = True) -> dict[str, Any]:
    """Menyusun atau menghitung ulang batch payroll periode YYYY-MM beserta sinkronisasi CRM & SCM."""
    sync_summary: dict[str, Any] = {"crm": None, "scm": None}
    crm_comm_map: dict[str, dict[str, int]] = {}

    if sync_external:
        crm_res = fetch_crm_commissions(period)
        sync_summary["crm"] = crm_res
        if crm_res.get("success"):
            crm_comm_map = crm_res.get("commissions", {})

        scm_res = fetch_scm_overtime(period)
        sync_summary["scm"] = scm_res

    batch_code = f"PAY-{period}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    period_like = f"{period}-%"

    with db_session() as conn:
        existing_run = conn.execute(
            "SELECT * FROM payroll_runs WHERE period = ?", (period,),
        ).fetchone()
        if existing_run and existing_run["status"] in ("SENT_TO_FINANCE", "PAID"):
            raise ValueError(
                f"Payroll periode {period} sudah berstatus {existing_run['status']} dan terkunci."
            )

        employees = conn.execute(
            """
            SELECT e.*, d.name AS department_name
            FROM employees e
            JOIN departments d ON d.id = e.department_id
            WHERE e.status != 'NONAKTIF'
            ORDER BY e.employee_code
            """
        ).fetchall()

        if existing_run:
            run_id = existing_run["id"]
            conn.execute("DELETE FROM payroll_items WHERE payroll_run_id = ?", (run_id,))
        else:
            cur = conn.execute(
                """
                INSERT INTO payroll_runs (batch_code, period, total_employees, total_gross, total_deductions, total_net, status, created_at, updated_at)
                VALUES (?, ?, 0, 0, 0, 0, 'DRAFT', ?, ?)
                """,
                (batch_code, period, now, now),
            )
            run_id = int(cur.lastrowid)

        total_gross = 0
        total_deductions = 0
        total_net = 0

        for emp in employees:
            att = conn.execute(
                """
                SELECT
                    COALESCE(SUM(overtime_hours), 0) AS total_ot,
                    COALESCE(SUM(CASE WHEN source = 'SCM_SYNC' THEN overtime_hours ELSE 0 END), 0) AS scm_ot,
                    COALESCE(SUM(CASE WHEN status = 'ALPHA' THEN 1 ELSE 0 END), 0) AS alpha_days
                FROM attendance_logs
                WHERE employee_id = ? AND work_date LIKE ?
                """,
                (emp["id"], period_like),
            ).fetchone()

            ot_hours = float(att["total_ot"] or 0.0)
            scm_ot_hours = float(att["scm_ot"] or 0.0)
            alpha_days = int(att["alpha_days"] or 0)

            base_sal = int(emp["base_salary"])
            allowance = int(emp["fixed_allowance"])
            ot_pay = round(ot_hours * int(emp["overtime_rate"]))

            if emp["integration_role"] == "CRM_SALES":
                crm_info = crm_comm_map.get(emp["employee_code"], {"commission": 0, "deals_count": 0})
            else:
                crm_info = {"commission": 0, "deals_count": 0}
            crm_comm = int(crm_info["commission"])
            crm_deals = int(crm_info["deals_count"])

            absent_ded = alpha_days * round(base_sal / 22)
            gross = base_sal + allowance + ot_pay + crm_comm
            tax, bpjs = _calculate_tax_and_bpjs(base_sal, gross)
            total_ded = tax + bpjs + absent_ded
            net = max(0, gross - total_ded)

            notes = []
            if crm_comm > 0:
                notes.append(f"Komisi CRM ({crm_deals} deal)")
            if scm_ot_hours > 0:
                notes.append(f"Lembur SCM {scm_ot_hours:g} jam")
            if alpha_days > 0:
                notes.append(f"Potongan Alpha {alpha_days} hari")

            conn.execute(
                """
                INSERT INTO payroll_items (
                    payroll_run_id, employee_id, base_salary, fixed_allowance,
                    overtime_hours, overtime_pay, crm_commission, crm_deals_count,
                    other_bonus, tax_pph21, bpjs_deduction, absent_deduction,
                    gross_salary, net_salary, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, emp["id"], base_sal, allowance, ot_hours, ot_pay,
                    crm_comm, crm_deals, tax, bpjs, absent_ded, gross, net, ", ".join(notes),
                ),
            )

            total_gross += gross
            total_deductions += total_ded
            total_net += net

        conn.execute(
            """
            UPDATE payroll_runs
            SET total_employees = ?, total_gross = ?, total_deductions = ?, total_net = ?, status = 'FINAL', updated_at = ?
            WHERE id = ?
            """,
            (len(employees), total_gross, total_deductions, total_net, now, run_id),
        )

    return {
        "payroll_run": get_payroll_run(period),
        "sync_summary": sync_summary,
    }


def get_payroll_run(period: str) -> dict[str, Any] | None:
    """Mengambil header batch payroll beserta daftar rincian item per karyawan."""
    with db_session() as conn:
        run = conn.execute(
            "SELECT * FROM payroll_runs WHERE period = ? OR batch_code = ?",
            (period, period),
        ).fetchone()
        if not run:
            return None
        items = conn.execute(
            """
            SELECT pi.*, e.employee_code, e.full_name, e.position_title,
                   e.bank_name, e.bank_account, e.integration_role,
                   d.code AS department_code, d.name AS department_name, d.cost_center
            FROM payroll_items pi
            JOIN employees e ON e.id = pi.employee_id
            JOIN departments d ON d.id = e.department_id
            WHERE pi.payroll_run_id = ?
            ORDER BY e.employee_code
            """,
            (run["id"],),
        ).fetchall()
    result = dict(run)
    result["items"] = [dict(r) for r in items]
    return result


def list_payroll_runs() -> list[dict[str, Any]]:
    """Menampilkan daftar seluruh batch payroll yang pernah dibuat."""
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM payroll_runs ORDER BY period DESC").fetchall()
    return [dict(r) for r in rows]


def get_payslip_item(item_id: int) -> dict[str, Any] | None:
    """Mengambil data slip gaji tunggal per item payroll."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT pi.*, pr.batch_code, pr.period, pr.status AS batch_status, pr.finance_batch_ref,
                   e.employee_code, e.full_name, e.email, e.position_title, e.employment_type,
                   e.bank_name, e.bank_account, d.code AS department_code, d.name AS department_name, d.cost_center
            FROM payroll_items pi
            JOIN payroll_runs pr ON pr.id = pi.payroll_run_id
            JOIN employees e ON e.id = pi.employee_id
            JOIN departments d ON d.id = e.department_id
            WHERE pi.id = ?
            """,
            (item_id,),
        ).fetchone()
    return dict(row) if row else None
