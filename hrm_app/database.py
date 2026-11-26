"""Inisialisasi koneksi dan skema SQLite untuk Sistem HRM Kelompok 12."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from hrm_app.config import HRM_DB_PATH


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS company_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    theme_key TEXT NOT NULL,
    company_name TEXT NOT NULL,
    industry_label TEXT NOT NULL,
    description TEXT NOT NULL,
    payroll_cutoff_day INTEGER NOT NULL DEFAULT 25,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT DEFAULT '',
    department_id INTEGER NOT NULL REFERENCES departments(id),
    position_title TEXT NOT NULL,
    employment_type TEXT NOT NULL DEFAULT 'TETAP',
    integration_role TEXT NOT NULL DEFAULT 'INTERNAL',
    status TEXT NOT NULL DEFAULT 'AKTIF',
    join_date TEXT NOT NULL,
    base_salary INTEGER NOT NULL CHECK (base_salary >= 0),
    fixed_allowance INTEGER NOT NULL DEFAULT 0,
    overtime_rate INTEGER NOT NULL DEFAULT 50000,
    bank_name TEXT DEFAULT 'BCA',
    bank_account TEXT DEFAULT '',
    leave_quota INTEGER NOT NULL DEFAULT 12,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    cert_name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    issued_date TEXT NOT NULL,
    expiry_date TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'VALID'
);

CREATE TABLE IF NOT EXISTS attendance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    work_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'HADIR',
    regular_hours REAL NOT NULL DEFAULT 8.0,
    overtime_hours REAL NOT NULL DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'INTERNAL',
    note TEXT DEFAULT '',
    UNIQUE(employee_id, work_date, source)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type TEXT NOT NULL DEFAULT 'TAHUNAN',
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    days_count INTEGER NOT NULL CHECK (days_count > 0),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    reviewed_by TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS manpower_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_code TEXT NOT NULL UNIQUE,
    requester_system TEXT NOT NULL DEFAULT 'INTERNAL',
    department_id INTEGER NOT NULL REFERENCES departments(id),
    position_title TEXT NOT NULL,
    headcount INTEGER NOT NULL DEFAULT 1,
    estimated_salary INTEGER NOT NULL DEFAULT 0,
    period TEXT NOT NULL DEFAULT '2026-11',
    reason TEXT NOT NULL,
    finance_budget_status TEXT NOT NULL DEFAULT 'BELUM_CEK',
    finance_ref TEXT DEFAULT '',
    hiring_status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applicants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manpower_request_id INTEGER NOT NULL REFERENCES manpower_requests(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT DEFAULT '',
    skills TEXT DEFAULT '',
    stage TEXT NOT NULL DEFAULT 'APPLIED',
    hired_employee_code TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payroll_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_code TEXT NOT NULL UNIQUE,
    period TEXT NOT NULL UNIQUE,
    total_employees INTEGER NOT NULL DEFAULT 0,
    total_gross INTEGER NOT NULL DEFAULT 0,
    total_deductions INTEGER NOT NULL DEFAULT 0,
    total_net INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    finance_batch_ref TEXT DEFAULT '',
    finance_note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payroll_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payroll_run_id INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    base_salary INTEGER NOT NULL DEFAULT 0,
    fixed_allowance INTEGER NOT NULL DEFAULT 0,
    overtime_hours REAL NOT NULL DEFAULT 0.0,
    overtime_pay INTEGER NOT NULL DEFAULT 0,
    crm_commission INTEGER NOT NULL DEFAULT 0,
    crm_deals_count INTEGER NOT NULL DEFAULT 0,
    other_bonus INTEGER NOT NULL DEFAULT 0,
    tax_pph21 INTEGER NOT NULL DEFAULT 0,
    bpjs_deduction INTEGER NOT NULL DEFAULT 0,
    absent_deduction INTEGER NOT NULL DEFAULT 0,
    gross_salary INTEGER NOT NULL DEFAULT 0,
    net_salary INTEGER NOT NULL DEFAULT 0,
    note TEXT DEFAULT '',
    UNIQUE(payroll_run_id, employee_id)
);

CREATE TABLE IF NOT EXISTS integration_partners (
    partner_key TEXT PRIMARY KEY,
    partner_name TEXT NOT NULL,
    group_label TEXT NOT NULL,
    base_url TEXT NOT NULL,
    auth_type TEXT NOT NULL DEFAULT 'OAUTH_BEARER',
    token_endpoint TEXT DEFAULT '/oauth/token',
    client_id TEXT DEFAULT '',
    client_secret TEXT DEFAULT '',
    api_key_header TEXT DEFAULT 'X-API-Key',
    api_key_value TEXT DEFAULT '',
    endpoints_json TEXT NOT NULL,
    field_mapping_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_health_status TEXT DEFAULT 'UNKNOWN',
    last_checked_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS api_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT NOT NULL,
    partner_name TEXT NOT NULL,
    allowed_scopes TEXT NOT NULL DEFAULT 'read,write',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS integration_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    direction TEXT NOT NULL,
    partner_key TEXT NOT NULL,
    method TEXT NOT NULL,
    url_or_path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    request_summary TEXT DEFAULT '',
    response_summary TEXT DEFAULT '',
    success INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Membuka koneksi SQLite dengan row_factory dict-like dan foreign keys aktif."""
    target = Path(db_path) if db_path else HRM_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager koneksi SQLite dengan commit otomatis saat sukses."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(db_path: Path | None = None) -> None:
    """Membuat seluruh tabel skema HRM jika belum tersedia."""
    with db_session(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(manpower_requests)").fetchall()}
        if "period" not in cols:
            conn.execute("ALTER TABLE manpower_requests ADD COLUMN period TEXT NOT NULL DEFAULT '2026-11'")
