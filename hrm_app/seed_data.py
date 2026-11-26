"""Data preset multi-tema (Software, Manufaktur, Telekomunikasi) untuk Sistem HRM Kelompok 12."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from hrm_app.database import db_session, init_schema

THEME_PRESETS: dict[str, dict[str, Any]] = {
    "software": {
        "company_name": "PT Nusantara Digital Solusi",
        "industry_label": "Software & Layanan Teknologi Informasi",
        "description": (
            "Perusahaan pengembang perangkat lunak enterprise, SaaS, dan konsultansi sistem "
            "dengan fokus manajemen engineer, alokasi proyek, sertifikasi cloud, dan sales B2B."
        ),
        "departments": [
            ("HRD", "Human Resources & People Ops", "CC-100", "Pengelolaan talenta, absensi, sertifikasi, dan payroll."),
            ("ENG", "Software Engineering & DevOps", "CC-200", "Tim developer backend, frontend, QA, dan infrastruktur cloud."),
            ("SLS", "Enterprise Sales & CRM", "CC-300", "Tim penjualan lisensi SaaS, account executive, dan customer success."),
            ("DLV", "IT Procurement & Delivery (SCM)", "CC-400", "Pengadaan lisensi, perangkat keras server, dan manajemen vendor."),
            ("FIN", "Finance & Accounting", "CC-500", "Pengelolaan arus kas, pajak, dan pencairan payroll."),
        ],
        "employees": [
            ("EMP-001", "Nadira Kusuma", "nadira.kusuma@nusantaradigital.id", "081230001001", "HRD", "HR Manager", "TETAP", "INTERNAL", "AKTIF", "2023-02-01", 12500000, 2000000, 75000, "BCA", "5210011221", "Penanggung jawab kebijakan SDM & payroll"),
            ("EMP-002", "Raka Pratama", "raka.pratama@nusantaradigital.id", "081230001002", "ENG", "Senior Backend Engineer", "TETAP", "INTERNAL", "AKTIF", "2023-05-15", 14000000, 2500000, 95000, "Mandiri", "1400099112", "Lead API & arsitektur microservices"),
            ("EMP-003", "Siti Rahmawati", "siti.rahma@nusantaradigital.id", "081230001003", "ENG", "DevOps & Cloud Engineer", "TETAP", "SCM_OPS", "AKTIF", "2024-01-10", 13000000, 2000000, 85000, "BCA", "5210088331", "On-call deployment & server infrastructure"),
            ("EMP-004", "Dimas Wijaya", "dimas.wijaya@nusantaradigital.id", "081230001004", "SLS", "Enterprise Account Executive", "TETAP", "CRM_SALES", "AKTIF", "2023-09-01", 9500000, 1500000, 65000, "BNI", "0331122990", "Sales B2B kontrak SaaS korporat (komisi CRM)"),
            ("EMP-005", "Alya Putri", "alya.putri@nusantaradigital.id", "081230001005", "SLS", "Solution Consultant & Sales", "TETAP", "CRM_SALES", "AKTIF", "2024-03-18", 9000000, 1500000, 60000, "BCA", "5210044552", "Sales demo & onboarding klien enterprise (komisi CRM)"),
            ("EMP-006", "Bagus Santoso", "bagus.santoso@nusantaradigital.id", "081230001006", "DLV", "IT Procurement & License Officer", "TETAP", "SCM_OPS", "AKTIF", "2024-06-01", 8500000, 1200000, 60000, "BRI", "0029188221", "Koordinator vendor hardware & pengadaan cloud (SCM)"),
            ("EMP-007", "Kevin Hartono", "kevin.hartono@nusantaradigital.id", "081230001007", "ENG", "QA Automation Engineer", "KONTRAK", "INTERNAL", "AKTIF", "2025-01-15", 8800000, 1000000, 55000, "BCA", "5210077219", "Pengujian API & regression suite"),
            ("EMP-008", "Clara Devina", "clara.devina@nusantaradigital.id", "081230001008", "FIN", "Payroll & Tax Specialist", "TETAP", "FINANCE", "AKTIF", "2023-11-01", 9800000, 1500000, 65000, "Mandiri", "1400077231", "Verifikasi beban gaji & rekonsiliasi PPh21"),
        ],
        "certifications": [
            ("EMP-002", "AWS Solutions Architect Associate", "Amazon Web Services", "2025-03-10", "2028-03-10", "VALID"),
            ("EMP-003", "Certified Kubernetes Administrator (CKA)", "CNCF", "2025-07-01", "2028-07-01", "VALID"),
            ("EMP-004", "Enterprise SaaS Consultative Selling", "Sandler Training", "2024-11-15", "2027-11-15", "VALID"),
        ],
        "manpower": ("MR-2026-001", "SCM", "DLV", "Cloud Asset & Vendor Analyst", 1, 9000000, "Peningkatan pengadaan lisensi & server klien kuartal IV"),
        "applicant": ("Fajar Nugroho", "fajar.n@mail.id", "081355667788", "Procurement IT, Vendor SLA, Cloud FinOps", "INTERVIEW"),
    },
    "manufaktur": {
        "company_name": "PT Panata Jaya Mandiri",
        "industry_label": "Manufaktur Komponen Otomotif & OEM",
        "description": (
            "PT Panata Jaya Mandiri adalah perusahaan manufaktur komponen otomotif OEM dengan fokus "
            "pengelolaan upah buruh pabrik per cost center, shift & lembur lini produksi, sertifikasi K3, "
            "gudang bahan baku & penerimaan barang 3-way match (SCM/Keuangan), serta akun pelanggan OEM (CRM)."
        ),
        "departments": [
            ("HRD", "Human Resources & K3", "CC-100", "Manajemen SDM pabrik, shift kerja, sertifikasi K3, dan payroll."),
            ("PRD", "Produksi Komponen Otomotif", "CC-200", "Lini produksi stamping/CNC otomotif, pencatatan upah buruh pabrik per cost center, dan quality control."),
            ("SCM", "Warehouse, Logistik & Procurement", "CC-300", "Gudang bahan baku otomotif, Goods Receipt (GR) PO 3-way match, dan pengiriman OEM."),
            ("SLS", "B2B Sales & OEM Account (CRM)", "CC-400", "Penjualan komponen otomotif ke customer OEM dan distributor (termin & komisi)."),
            ("FIN", "Finance, Treasury & Cost Accounting", "CC-500", "Three-way match AP (PO/GR/Invoice), aging piutang OEM, dan pembayaran gaji per cost center."),
        ],
        "employees": [
            ("EMP-001", "Hendra Gunawan", "hendra.gunawan@panatajayamandiri.co.id", "081240002001", "HRD", "HR & Industrial Relations Manager", "TETAP", "INTERNAL", "AKTIF", "2022-04-01", 11500000, 2000000, 70000, "BCA", "5310011221", "Pengelola hubungan industrial, K3, & payroll pabrik"),
            ("EMP-002", "Budi Santoso", "budi.santoso@panatajayamandiri.co.id", "081240002002", "PRD", "Supervisor Lini Produksi Otomotif", "TETAP", "SCM_OPS", "AKTIF", "2022-08-12", 9500000, 1800000, 65000, "BRI", "0038122331", "Pengawas target output OEM & shift operator mesin (CC-200)"),
            ("EMP-003", "Slamet Riyadi", "slamet.riyadi@panatajayamandiri.co.id", "081240002003", "PRD", "Operator Mesin Stamping & CNC Senior", "TETAP", "SCM_OPS", "AKTIF", "2023-03-01", 6800000, 1200000, 50000, "BRI", "0038199442", "Buruh pabrik lini otomotif + tunjangan shift & K3 (CC-200)"),
            ("EMP-004", "Agus Setiawan", "agus.setiawan@panatajayamandiri.co.id", "081240002004", "SCM", "Kepala Gudang Bahan Baku & Receiving", "TETAP", "SCM_OPS", "AKTIF", "2023-01-20", 8200000, 1500000, 55000, "Mandiri", "1410088123", "Penanggung jawab stok gudang & Goods Receipt (GR) SCM (CC-300)"),
            ("EMP-005", "Rina Marlina", "rina.marlina@panatajayamandiri.co.id", "081240002005", "SLS", "OEM Key Account Sales Lead", "TETAP", "CRM_SALES", "AKTIF", "2023-07-01", 8800000, 1500000, 55000, "BCA", "5310044112", "Penjualan kontrak komponen ke customer OEM (komisi CRM)"),
            ("EMP-006", "Doni Saputra", "doni.saputra@panatajayamandiri.co.id", "081240002006", "SLS", "OEM & Distributor Account Executive", "KONTRAK", "CRM_SALES", "AKTIF", "2024-05-10", 7200000, 1200000, 48000, "BNI", "0441234561", "Akuisisi distributor & pemantauan termin OEM area Jawa (komisi CRM)"),
            ("EMP-007", "Taufik Hidayat", "taufik.h@panatajayamandiri.co.id", "081240002007", "PRD", "Quality Control (IATF/ISO) & K3 Inspector", "TETAP", "INTERNAL", "AKTIF", "2024-02-01", 7500000, 1300000, 52000, "BCA", "5310099812", "Inspeksi standar mutu komponen otomotif & K3"),
            ("EMP-008", "Maya Sari", "maya.sari@panatajayamandiri.co.id", "081240002008", "FIN", "Payroll & Cost Center Accounting Staff", "TETAP", "FINANCE", "AKTIF", "2023-10-15", 8000000, 1200000, 50000, "Mandiri", "1410055612", "Rekonsiliasi upah buruh per cost center & dukungan 3-way match Keuangan"),
        ],
        "certifications": [
            ("EMP-003", "Sertifikasi Operator CNC/Stamping & Keselamatan Mesin", "BNSP Kemnaker", "2025-01-20", "2028-01-20", "VALID"),
            ("EMP-007", "Ahli K3 Umum Sertifikasi Kemnaker", "Kemnaker RI", "2024-09-10", "2027-09-10", "VALID"),
            ("EMP-004", "Certified Warehouse & Forklift Safety", "Kemnaker RI", "2025-04-05", "2028-04-05", "VALID"),
        ],
        "manpower": ("MR-2026-001", "SCM", "SCM", "Operator Gudang & Receiving Material Otomotif", 2, 6500000, "Lonjakan batch komponen otomotif OEM & proses Goods Receipt gudang"),
        "applicant": ("Wahyu Prasetyo", "wahyu.p@mail.id", "081377889900", "Manajemen Gudang, Forklift SIO, Goods Receipt & Stock Opname", "INTERVIEW"),
    },
    "telekomunikasi": {
        "company_name": "PT Cakrawala Telekomunikasi Nusantara",
        "industry_label": "Telekomunikasi & Infrastruktur Jaringan",
        "description": (
            "Operator layanan konektivitas fiber optik dan menara BTS dengan manajemen "
            "teknisi lapangan 24/7, pengadaan perangkat jaringan (SCM), dan sales korporat/retail (CRM)."
        ),
        "departments": [
            ("HRD", "Human Capital & Field Compliance", "CC-100", "Pengelolaan SDM, sertifikasi kerja ketinggian/fiber, dan payroll."),
            ("NOC", "Network Operations & Engineering", "CC-200", "Monitoring jaringan 24/7, core network, dan maintenance BTS."),
            ("SCM", "Network Supply & Sparepart Logistics", "CC-300", "Pengadaan kabel fiber, perangkat router, dan logistik sparepart."),
            ("SLS", "Enterprise & Retail Sales (CRM)", "CC-400", "Penjualan layanan dedicated internet korporat & paket pelanggan."),
            ("FIN", "Finance & Revenue Assurance", "CC-500", "Penganggaran infrastruktur, pajak, dan pencairan payroll."),
        ],
        "employees": [
            ("EMP-001", "Dewi Lestari", "dewi.lestari@cakrawalatelko.id", "081250003001", "HRD", "Human Capital Manager", "TETAP", "INTERNAL", "AKTIF", "2022-06-01", 12800000, 2200000, 75000, "Mandiri", "1420011223", "Pengelolaan SDM NOC, teknisi, & tunjangan site"),
            ("EMP-002", "Farhan Akbar", "farhan.akbar@cakrawalatelko.id", "081250003002", "NOC", "NOC Shift Supervisor 24/7", "TETAP", "INTERNAL", "AKTIF", "2023-01-15", 11200000, 2000000, 75000, "BCA", "5410022119", "Pengawas SLA jaringan nasional & shift NOC"),
            ("EMP-003", "Ilham Ramadhan", "ilham.ramadhan@cakrawalatelko.id", "081250003003", "NOC", "Field Engineer BTS & Fiber", "TETAP", "SCM_OPS", "AKTIF", "2023-08-01", 8600000, 1800000, 65000, "BRI", "0049122334", "Perbaikan tower & penarikan sparepart gudang SCM"),
            ("EMP-004", "Yusuf Maulana", "yusuf.maulana@cakrawalatelko.id", "081250003004", "SCM", "Telecom Sparepart & Logistics Lead", "TETAP", "SCM_OPS", "AKTIF", "2023-04-10", 9000000, 1500000, 62000, "Mandiri", "1420099118", "Distribusi perangkat ONT, router, & kabel fiber (SCM)"),
            ("EMP-005", "Nadia Permata", "nadia.permata@cakrawalatelko.id", "081250003005", "SLS", "Enterprise Connectivity Sales", "TETAP", "CRM_SALES", "AKTIF", "2023-11-01", 9500000, 1600000, 60000, "BCA", "5410077881", "Kontrak internet B2B korporat & instansi (komisi CRM)"),
            ("EMP-006", "Reza Pahlevi", "reza.pahlevi@cakrawalatelko.id", "081250003006", "SLS", "Regional Retail Channel Lead", "TETAP", "CRM_SALES", "AKTIF", "2024-02-20", 8200000, 1400000, 55000, "BNI", "0551239871", "Akuisisi pelanggan area & mitra ISP (komisi CRM)"),
            ("EMP-007", "Galih Pratama", "galih.pratama@cakrawalatelko.id", "081250003007", "NOC", "Fiber Optic Splicing Specialist", "KONTRAK", "SCM_OPS", "AKTIF", "2025-01-05", 7400000, 1300000, 55000, "BCA", "5410033445", "Penyambungan backbone fiber antar-kota"),
            ("EMP-008", "Siska Amelia", "siska.amelia@cakrawalatelko.id", "081250003008", "FIN", "Payroll & Treasury Analyst", "TETAP", "FINANCE", "AKTIF", "2023-09-15", 9200000, 1500000, 60000, "Mandiri", "1420066554", "Rekonsiliasi tunjangan lapangan & pembayaran gaji"),
        ],
        "certifications": [
            ("EMP-003", "Sertifikasi K3 Bekerja di Ketinggian (TKPK)", "Kemnaker RI", "2025-02-14", "2028-02-14", "VALID"),
            ("EMP-002", "Cisco Certified Network Professional (CCNP)", "Cisco", "2024-08-20", "2027-08-20", "VALID"),
            ("EMP-007", "Certified Fiber Optic Technician (CFOT)", "FOA", "2025-05-01", "2028-05-01", "VALID"),
        ],
        "manpower": ("MR-2026-001", "SCM", "NOC", "Teknisi Lapangan Pemeliharaan BTS Regional", 2, 8000000, "Ekspansi site 5G & peningkatan kebutuhan maintenance perangkat SCM"),
        "applicant": ("Arif Rahman", "arif.rahman@mail.id", "081399001122", "Fiber Optic, BTS Maintenance, K3 Ketinggian", "INTERVIEW"),
    },
}


DEFAULT_PARTNERS = [
    {
        "partner_key": "keuangan",
        "partner_name": "Sistem Keuangan & Akuntansi",
        "group_label": "Kelompok 2",
        "base_url": "http://127.0.0.1:5001",
        "auth_type": "OAUTH_BEARER",
        "token_endpoint": "/oauth/token",
        "client_id": "hrm_kel12",
        "client_secret": "rahasia-hrm-ke-keuangan",
        "api_key_header": "X-API-Key",
        "api_key_value": "",
        "endpoints_json": json.dumps({
            "health": "/health",
            "submit_payroll": "/v1/payroll-accruals",
            "check_payroll_status": "/v1/payroll-accruals/{run_id}",
            "check_recruitment_budget": "/v1/budget-reservations",
            "check_budget_remaining": "/v1/budgets/{cost_center}/remaining",
            "budget_report": "/v1/reports/budget",
        }),
        "field_mapping_json": json.dumps({
            "batch_code_field": "payroll_run_id",
            "total_amount_field": "total_net_minor",
            "status_field": "status",
            "reference_field": "finance_ref",
            "approved_field": "approved",
        }),
    },
    {
        "partner_key": "crm",
        "partner_name": "Sistem CRM (Customer & Sales)",
        "group_label": "Kelompok 7",
        "base_url": "http://127.0.0.1:5002",
        "auth_type": "OAUTH_BEARER",
        "token_endpoint": "/oauth/token",
        "client_id": "hrm_kel12",
        "client_secret": "rahasia-hrm-ke-crm",
        "api_key_header": "X-API-Key",
        "api_key_value": "",
        "endpoints_json": json.dumps({
            "health": "/health",
            "get_commissions": "/v1/sales/komisi",
        }),
        "field_mapping_json": json.dumps({
            "period_query_param": "periode",
            "items_key": "items",
            "employee_code_field": "kode_karyawan",
            "commission_field": "total_komisi",
            "deals_count_field": "jumlah_deal",
        }),
    },
    {
        "partner_key": "scm",
        "partner_name": "Sistem SCM (Supply Chain)",
        "group_label": "Kelompok 8",
        "base_url": "http://127.0.0.1:5003",
        "auth_type": "OAUTH_BEARER",
        "token_endpoint": "/oauth/token",
        "client_id": "hrm_kel12",
        "client_secret": "rahasia-hrm-ke-scm",
        "api_key_header": "X-API-Key",
        "api_key_value": "",
        "endpoints_json": json.dumps({
            "health": "/health",
            "get_overtime": "/v1/operasional/lembur",
        }),
        "field_mapping_json": json.dumps({
            "period_query_param": "periode",
            "items_key": "items",
            "employee_code_field": "kode_karyawan",
            "overtime_hours_field": "total_jam_lembur",
            "note_field": "catatan",
        }),
    },
]

DEFAULT_INBOUND_CLIENTS = [
    ("kel2_keuangan", "secret-kel2-keuangan", "Kelompok 2 - Keuangan", "read,write"),
    ("kel7_crm", "secret-kel7-crm", "Kelompok 7 - CRM", "read"),
    ("kel8_scm", "secret-kel8-scm", "Kelompok 8 - SCM", "read,write"),
]


def _clear_business_tables(conn) -> None:
    """Menghapus data bisnis sebelum mengisi preset tema baru."""
    for tbl in (
        "idempotency_records",
        "payroll_items",
        "payroll_runs",
        "applicants",
        "manpower_requests",
        "leave_requests",
        "attendance_logs",
        "certifications",
        "employees",
        "departments",
        "company_profile",
    ):
        conn.execute(f"DELETE FROM {tbl}")


def seed_database(
    theme_key: str = "software",
    force_reset: bool = False,
    preserve_partners: bool = True,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Mengisi basis data awal sesuai tema perusahaan (software / manufaktur / telekomunikasi)."""
    if theme_key not in THEME_PRESETS:
        raise ValueError(f"Tema '{theme_key}' tidak valid. Pilih: {list(THEME_PRESETS.keys())}")

    init_schema(db_path)
    preset = THEME_PRESETS[theme_key]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_session(db_path) as conn:
        existing_profile = conn.execute("SELECT theme_key FROM company_profile WHERE id = 1").fetchone()
        if existing_profile and not force_reset:
            return {"seeded": False, "theme_key": existing_profile["theme_key"]}

        if force_reset:
            _clear_business_tables(conn)

        conn.execute(
            """
            INSERT INTO company_profile (id, theme_key, company_name, industry_label, description, payroll_cutoff_day, updated_at)
            VALUES (1, ?, ?, ?, ?, 25, ?)
            """,
            (theme_key, preset["company_name"], preset["industry_label"], preset["description"], now),
        )

        dept_id_map: dict[str, int] = {}
        for code, name, cc, desc in preset["departments"]:
            cur = conn.execute(
                "INSERT INTO departments (code, name, cost_center, description) VALUES (?, ?, ?, ?)",
                (code, name, cc, desc),
            )
            dept_id_map[code] = int(cur.lastrowid)

        emp_id_map: dict[str, int] = {}
        for emp in preset["employees"]:
            (
                emp_code, full_name, email, phone, dept_code, pos_title,
                emp_type, int_role, status, join_date, base_sal, allowance,
                ot_rate, bank_name, bank_acc, notes,
            ) = emp
            cur = conn.execute(
                """
                INSERT INTO employees (
                    employee_code, full_name, email, phone, department_id, position_title,
                    employment_type, integration_role, status, join_date, base_salary,
                    fixed_allowance, overtime_rate, bank_name, bank_account, leave_quota, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 12, ?, ?)
                """,
                (
                    emp_code, full_name, email, phone, dept_id_map[dept_code], pos_title,
                    emp_type, int_role, status, join_date, base_sal, allowance,
                    ot_rate, bank_name, bank_acc, notes, now,
                ),
            )
            emp_id_map[emp_code] = int(cur.lastrowid)

        for emp_code, cert_name, issuer, issued, expiry, status in preset["certifications"]:
            conn.execute(
                """
                INSERT INTO certifications (employee_id, cert_name, issuer, issued_date, expiry_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (emp_id_map[emp_code], cert_name, issuer, issued, expiry, status),
            )

        # Seed absensi awal periode 2026-11 untuk 5 hari kerja
        sample_dates = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
        for idx, (emp_code, emp_id) in enumerate(emp_id_map.items()):
            for day_idx, work_date in enumerate(sample_dates):
                status = "HADIR"
                reg_hours = 8.0
                ot_hours = 0.0
                note = "Kehadiran reguler"
                if emp_code == "EMP-002" and day_idx in (1, 3):
                    ot_hours = 2.0
                    note = "Lembur penyelesaian target departemen"
                elif emp_code == "EMP-007" and day_idx == 4:
                    status = "ALPHA"
                    reg_hours = 0.0
                    note = "Tanpa keterangan"
                conn.execute(
                    """
                    INSERT INTO attendance_logs (employee_id, work_date, status, regular_hours, overtime_hours, source, note)
                    VALUES (?, ?, ?, ?, ?, 'INTERNAL', ?)
                    """,
                    (emp_id, work_date, status, reg_hours, ot_hours, note),
                )

        # Seed 2 pengajuan cuti (1 approved, 1 pending)
        conn.execute(
            """
            INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, days_count, reason, status, reviewed_by, created_at)
            VALUES (?, 'TAHUNAN', '2026-11-19', '2026-11-20', 2, 'Keperluan acara keluarga', 'PENDING', '', ?)
            """,
            (emp_id_map["EMP-005"], now),
        )
        conn.execute(
            """
            INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, days_count, reason, status, reviewed_by, created_at)
            VALUES (?, 'SAKIT', '2026-11-09', '2026-11-09', 1, 'Pemulihan kesehatan (surat dokter)', 'APPROVED', 'HR Manager', ?)
            """,
            (emp_id_map["EMP-006"], now),
        )

        # Seed Manpower Request & Applicant
        mr_code, req_sys, mr_dept, mr_pos, mr_hc, mr_sal, mr_reason = preset["manpower"]
        mr_cur = conn.execute(
            """
            INSERT INTO manpower_requests (
                request_code, requester_system, department_id, position_title,
                headcount, estimated_salary, reason, finance_budget_status, hiring_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'BELUM_CEK', 'OPEN', ?)
            """,
            (mr_code, req_sys, dept_id_map[mr_dept], mr_pos, mr_hc, mr_sal, mr_reason, now),
        )
        mr_id = int(mr_cur.lastrowid)
        app_name, app_email, app_phone, app_skills, app_stage = preset["applicant"]
        conn.execute(
            """
            INSERT INTO applicants (manpower_request_id, full_name, email, phone, skills, stage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mr_id, app_name, app_email, app_phone, app_skills, app_stage, now),
        )

        # Seed partner integrasi hanya jika belum ada (atau jika preserve_partners=False)
        existing_partners = conn.execute("SELECT COUNT(*) FROM integration_partners").fetchone()[0]
        if existing_partners == 0 or not preserve_partners:
            if not preserve_partners:
                conn.execute("DELETE FROM integration_partners")
            for p in DEFAULT_PARTNERS:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO integration_partners (
                        partner_key, partner_name, group_label, base_url, auth_type, token_endpoint,
                        client_id, client_secret, api_key_header, api_key_value,
                        endpoints_json, field_mapping_json, is_active, last_health_status, last_checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'UNKNOWN', '')
                    """,
                    (
                        p["partner_key"], p["partner_name"], p["group_label"], p["base_url"],
                        p["auth_type"], p["token_endpoint"], p["client_id"], p["client_secret"],
                        p["api_key_header"], p["api_key_value"], p["endpoints_json"], p["field_mapping_json"],
                    ),
                )

        # Seed inbound API clients jika belum ada
        existing_clients = conn.execute("SELECT COUNT(*) FROM api_clients").fetchone()[0]
        if existing_clients == 0:
            for cid, csec, pname, scopes in DEFAULT_INBOUND_CLIENTS:
                conn.execute(
                    """
                    INSERT INTO api_clients (client_id, client_secret, partner_name, allowed_scopes, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (cid, csec, pname, scopes, now),
                )

    return {"seeded": True, "theme_key": theme_key, "company_name": preset["company_name"]}
