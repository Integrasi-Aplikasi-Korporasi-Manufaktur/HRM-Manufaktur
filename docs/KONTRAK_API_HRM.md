# Kontrak API Resmi Sistem HRM — Kelompok 12 (IAK)

Dokumen ini merupakan kontrak integrasi resmi modul **HRM (Kelompok 12)** untuk studi kasus manufaktur **PT Panata Jaya Mandiri** dan diselaraskan dengan kontrak 4 divisi bersama **Kelompok 2 (Keuangan)**, **Kelompok 7 (CRM)**, dan **Kelompok 8 (SCM)**.

- **Live Cloud Portal (24/7):** https://hrm-panata-jaya-mandiri.up.railway.app
- **Swagger / OpenAPI:** https://hrm-panata-jaya-mandiri.up.railway.app/docs
- **GitHub Organisasi Kelompok Besar:** https://github.com/Integrasi-Aplikasi-Korporasi-Manufaktur/HRM-Manufaktur
- **GitHub Personal Repository:** https://github.com/Ezra696969/HumanResourceManagement

---

## 1. Autentikasi & Aturan Lintas Divisi (`API-CONTRACT.md`)

Seluruh endpoint eksternal HRM (`/api/v1/external/...`) diamankan menggunakan **Bearer Token** (kecuali `/health` dan `/oauth/token`).

1. **Minta Token:** `POST /oauth/token`
   ```json
   {
     "client_id": "kel7_crm",
     "client_secret": "secret-kel7-crm"
   }
   ```
   **Kredensial Default Terdaftar:**
   - **Kelompok 2 (Keuangan):** `client_id = "kel2_keuangan"`, `client_secret = "secret-kel2-keuangan"`
   - **Kelompok 7 (CRM):** `client_id = "kel7_crm"`, `client_secret = "secret-kel7-crm"`
   - **Kelompok 8 (SCM):** `client_id = "kel8_scm"`, `client_secret = "secret-kel8-scm"`
   *(Dapat ditambah/ubah langsung melalui menu **Integration Hub** di Web UI HRM).*

2. **Header Standar Permintaan & Pelacakan:**
   ```http
   Authorization: Bearer <access_token>
   X-Request-ID: <uuid-v4>
   Idempotency-Key: <deterministic-key>   # Wajib pada mutasi uang & callback
   ngrok-skip-browser-warning: true
   ```
   - **Idempotensi:** Key sama + payload sama menghasilkan respons lama (200 replay); key sama + payload berbeda ditolak **`409 IDEMPOTENCY_CONFLICT`**. Callback gagal diulang menggunakan key asli peristiwa yang sama.
   - **Format Uang & Waktu:** Nominal uang menggunakan integer **`amount_minor`** dengan **`currency: "IDR"`** (rupiah bulat). Timestamp menggunakan format **ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)**.
   - **Format Error Envelope Standar:**
     ```json
     {
       "error": {
         "code": "BUDGET_INSUFFICIENT",
         "message": "...",
         "request_id": "..."
       },
       "detail": "..."
     }
     ```
     Kode HTTP yang dipakai: `400` payload tidak valid, `401`/`403` auth gagal, `404` entitas tidak ada, `409` konflik / idempotensi, `422` pelanggaran aturan bisnis.

---

## 2. Daftar Endpoint HRM yang Disediakan untuk Mitra (Inbound)

| Sistem Pemanggil | Method & Endpoint | Fungsi & Aturan Kontrak |
| :--- | :--- | :--- |
| **Semua Mitra** | `POST /oauth/token` | Menukar `client_id` & `client_secret` menjadi Bearer `access_token`. |
| **CRM (Kel. 7)** | `GET /api/v1/external/employees?role=CRM_SALES&status=AKTIF` *(mendukung alias `role=sales`)* | Daftar staf Sales aktif beserta `employee_code` (`EMP-xxx`), `cost_center`, dan status K3. |
| **SCM (Kel. 8)** | `GET /api/v1/external/employees?role=SCM_OPS&status=AKTIF` *(opsional filter `&k3_valid=true`)* | Daftar staf gudang/operator lini produksi beserta **`cost_center`**, **`k3_status`** (`VALID`/`EXPIRING_SOON`/`EXPIRED`/`NONE`), **`k3_valid`**, dan **`assignable`** untuk memblokir operator K3 kedaluwarsa. |
| **Semua Mitra** | `GET /api/v1/external/employees/{employee_code}` | Mengecek profil, `cost_center`, keaktifan, dan validitas K3 1 karyawan (`EMP-xxx`). |
| **SCM / CRM** | `POST /api/v1/external/manpower-requests` | Mengirim permintaan penambahan tenaga kerja (`headcount`, `estimated_salary`, `cost_center`/`department_code`, `period`). |
| **SCM / CRM** | `GET /api/v1/external/manpower-requests` | Melihat status permintaan tenaga kerja, `cost_center`, `period`, dan status persetujuan anggaran. |
| **Keuangan (Kel. 2)** | `POST /api/v1/external/payroll/{batch_code}/payment-callback` | Callback **boundary `PaymentStatus`** (`UNPAID` \| `PAID` \| `FAILED`) dengan `Idempotency-Key` deterministik. `FAILED` **tidak** mengembalikan status `SENT_TO_FINANCE`/`POSTED` ke `FINAL`. Slip gaji baru terbuka jika `PaymentStatus = PAID`. |
| **Semua Mitra** | `GET /api/v1/external/logs/summary` | Ringkasan log audit integrasi `INBOUND`/`OUTBOUND`. |

### Contoh Payload `POST /api/v1/external/manpower-requests` (dari SCM/CRM)
```json
{
  "requester_system": "SCM",
  "department_code": "SCM",
  "cost_center": "CC-300",
  "period": "2026-11",
  "position_title": "Operator Gudang & Receiving Material Otomotif",
  "headcount": 2,
  "estimated_salary": 7000000,
  "reason": "Kenaikan volume distribusi komponen otomotif OEM"
}
```

### Contoh Payload `POST /api/v1/external/payroll/PAY-2026-11/payment-callback` (dari Keuangan)
Header: `Idempotency-Key: payroll-accrual:PAY-2026-11:2026-11`
```json
{
  "payment_status": "PAID",
  "finance_ref": "FIN-PAY-202611-01",
  "amount_minor": 80218841,
  "currency": "IDR",
  "note": "Transfer gaji batch November selesai diproses (maker-checker)"
}
```

---

## 3. Endpoint Mitra yang Dipanggil oleh HRM (Outbound)

HRM sebagai pemilik master **Cost Center** (`CC-100` s.d. `CC-500`) mengirimkan dimensi `cost_center` secara konsisten ke Keuangan untuk pencatatan jurnal. Seluruh path, autentikasi, dan *field mapping* tetap adaptif melalui menu **Integration Hub → Edit Adapter**.

### A. Keuangan (Kelompok 2) — Kontrak Kanonik `H1`–`H9`
1. **`POST /v1/budget-reservations`** *(Header `Idempotency-Key: budget-reservation:{manpower_request_id}`)*  
   Mengajukan **`BudgetReservation`** (`manpower_request_id`, `cost_center`, `period`, `headcount`, `estimated_salary_minor`, `amount_minor`, `currency: "IDR"`).  
   Keuangan merespons **`APPROVED`**, **`PENDING_APPROVAL`** (> Rp 100.000.000), atau **`REJECTED`**, serta menolak **`422 BUDGET_INSUFFICIENT`** tanpa reservasi sebagian jika melebihi sisa anggaran. Reservasi dilepas tepat satu kali saat `PayrollAccrual` diposting.
2. **`GET /v1/budgets/{cost_center}/remaining`** *(dan **`GET /v1/reports/budget`**)*  
   Memeriksa sisa anggaran per `cost_center` dan `period` sebelum pengajuan reservasi anggaran rekrutmen.
3. **`POST /v1/payroll-accruals`** *(Header `Idempotency-Key: payroll-accrual:{payroll_run_id}:{period}`)*  
   Mengirim **`PayrollAccrual`** per periode (`payroll_run_id` = `run_id` = `batch_code` sebagai nilai bisnis yang sama) beserta array **`lines`** per karyawan lengkap dengan **`cost_center`**, komponen gaji/lembur/komisi, PPh 21, BPJS, potongan Alpha, rekening, dan **`currency: "IDR"`**. Total seluruh baris wajib sama persis dengan total batch; selisih ditolak **`422 PAYROLL_TOTAL_MISMATCH`**. Status di Keuangan diposting menjadi **`POSTED`**.
4. **`GET /v1/payroll-accruals/{run_id}`**  
   Mengecek status accrual (`POSTED`/`PAID`) dan `payment_status` (`UNPAID`/`PAID`/`FAILED`) dari Keuangan.

> **Catatan Slip Gaji (`H9`):** Endpoint internal `GET /api/v1/payroll/payslip/{item_id}` dan tombol **Slip** di UI mewajibkan status batch **`PAID`** dari `PaymentStatus` Keuangan; sebelum `PAID`, API mengembalikan **`422 PAYSLIP_NOT_PAID`**.

### B. CRM (Kelompok 7)
- `GET /v1/sales/komisi?periode=2026-11` → HRM menarik daftar komisi sales B2B/OEM per `kode_karyawan` untuk dihitung otomatis ke Payroll.

### C. SCM (Kelompok 8)
- `GET /v1/operasional/lembur?periode=2026-11` → HRM menarik daftar `total_jam_lembur` operator shift pabrik/gudang per `kode_karyawan` ke absensi (`SCM_SYNC`) dan Payroll.
