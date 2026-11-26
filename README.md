# Sistem HRM Terintegrasi — Kelompok 12 (Final Project UAS IAK)

Proyek ini berfokus penuh pada pengembangan **Sistem Human Resource Management (HRM — Kelompok 12)** untuk studi kasus manufaktur **PT Panata Jaya Mandiri** yang selaras dengan **kontrak API kanonik 4 divisi** bersama **Kelompok 2 (Keuangan)**, **Kelompok 7 (CRM)**, dan **Kelompok 8 (SCM)**.

- **Live Online Portal (24/7 Railway):** https://hrm-panata-jaya-mandiri.up.railway.app
- **Swagger / OpenAPI Docs:** https://hrm-panata-jaya-mandiri.up.railway.app/docs
- **GitHub Organisasi (Grup Manufaktur):** https://github.com/Integrasi-Aplikasi-Korporasi-Manufaktur/HRM-Manufaktur
- **GitHub Personal Mirror:** https://github.com/Ezra696969/HumanResourceManagement

Selama belum ada kesepakatan deployment akhir dengan server masing-masing kelompok mitra, proyek ini menyertakan **3 Simulator Kasar (Mock Servers)** pada port terpisah maupun terpadu di `/mock/keuangan/`, `/mock/crm/`, dan `/mock/scm/` sehingga seluruh alur integrasi REST API dua arah dapat diuji secara nyata sejak sekarang.

---

## Arsitektur Port & Layanan

| Layanan | Kelompok | Port Default | Keterangan |
| :--- | :--- | :---: | :--- |
| **Sistem HRM (UTAMA)** | **Kelompok 12** | `5000` | Web UI lengkap + REST API Provider + OpenAPI `/docs` + SQLite (14 tabel) |
| Mock Keuangan (Kasar) | Simulasi Kel. 2 | `5001` | Endpoint kanonik `POST /v1/budget-reservations`, `GET /v1/budgets/{cost_center}/remaining`, `POST /v1/payroll-accruals`, `GET /v1/payroll-accruals/{run_id}`, validasi `422`/`409`, & callback `PaymentStatus` (`PAID`/`FAILED`) |
| Mock CRM (Kasar) | Simulasi Kel. 7 | `5002` | Menyediakan data komisi sales & menarik daftar sales dari HRM |
| Mock SCM (Kasar) | Simulasi Kel. 8 | `5003` | Menyediakan lembur operasional, kirim manpower request, & tarik staf ops |

---

## Cara Menjalankan

1. Pastikan Python 3.10+ sudah terpasang (`pip install -r requirements.txt` jika belum).
2. Jalankan keempat server sekaligus dengan satu perintah:
   ```bash
   python jalankan_semua.py
   ```
   *(Atau klik ganda `jalankan_semua.bat` di Windows).*
3. Buka browser:
   - **Aplikasi HRM Utama (Kelompok 12):** http://127.0.0.1:5000
   - **Dokumentasi Interaktif API (Swagger):** http://127.0.0.1:5000/docs
   - Mock Keuangan (Kel. 2): http://127.0.0.1:5001
   - Mock CRM (Kel. 7): http://127.0.0.1:5002
   - Mock SCM (Kel. 8): http://127.0.0.1:5003

---

## Fitur Utama HRM (Kelompok 12)

1. **Multi-Tema Studi Kasus (1 Klik):** Melalui dropdown **Tema Studi Kasus** di kanan atas header, seluruh profil perusahaan, departemen, karyawan, sertifikasi, dan lowongan langsung menyesuaikan studi kasus **Software**, **Manufaktur**, atau **Telekomunikasi**.
2. **Manajemen Karyawan, Cost Center & Gate K3:** CRUD karyawan, pengelompokan `integration_role` (`CRM_SALES`, `SCM_OPS`, `INTERNAL`, `FINANCE`), kode master `cost_center` (`CC-100`..`CC-500`), dan status validitas sertifikasi K3 (`k3_valid`, `k3_status`, `assignable`) untuk memblokir operator dengan sertifikat kedaluwarsa.
3. **Absensi, Lembur & Cuti:** Input absensi harian, persetujuan cuti dengan pemotongan kuota otomatis, serta tombol **Tarik Lembur dari SCM**.
4. **Rekrutmen, BudgetReservation & Auto-Onboarding:** Menerima permintaan SDM (internal maupun API SCM/CRM), tombol **Sisa Anggaran** (`GET /v1/budgets/{cost_center}/remaining`), tombol **Reservasi Budget** (`POST /v1/budget-reservations` dengan `Idempotency-Key`, status `APPROVED`/`PENDING_APPROVAL`/`REJECTED`, penolakan `422 BUDGET_INSUFFICIENT`), dan konversi otomatis kandidat `HIRED` menjadi karyawan aktif baru (`EMP-xxx`).
5. **Payroll Engine (`PayrollAccrual`) & Slip Gaji Terproteksi:** Menghitung gaji pokok + tunjangan + lembur (Internal & SCM) + komisi sales (CRM) − potongan PPh21/BPJS/Alpha, validasi total baris (`422 PAYROLL_TOTAL_MISMATCH`), mengirim `PayrollAccrual` per `cost_center` (`POST /v1/payroll-accruals` dengan `Idempotency-Key`), menerima callback boundary `PaymentStatus` (`UNPAID`/`PAID`/`FAILED` dengan aturan `409 Conflict`), serta mengunci cetak **Slip Gaji Digital** hingga `PaymentStatus = PAID` (`422 PAYSLIP_NOT_PAID` sebelum lunas).
6. **Integration Hub, `X-Request-ID` & Audit Log:** Mengedit URL (`localhost`, `ngrok`, maupun hosting) dan *field mapping* JSON, pelacakan header `X-Request-ID`, error envelope standar `{"error": {"code", "message", "request_id"}}`, mengelola `client_id` mitra, dan memantau *live audit log* Inbound/Outbound.

---

## Cara Menyesuaikan Setelah Diskusi dengan Kel. 2, 7, 8

Saat kelompok lain sudah memiliki aplikasi sendiri (misalnya via `ngrok` atau hosting):
1. Buka **Integration Hub** di http://127.0.0.1:5000/integration.
2. Klik **Edit Adapter** pada partner terkait (Keuangan / CRM / SCM).
3. Ganti `Base URL`, sesuaikan `client_id`/`client_secret` atau `API Key`, dan ubah mapping path/nama *field* JSON bila berbeda.
4. Matikan mock server yang sudah digantikan oleh server asli kelompok tersebut.
5. Bagikan dokumen `docs/KONTRAK_API_HRM.md` kepada Kel. 2, 7, dan 8 agar mereka bisa memanggil API HRM.

---

## Menjalankan Automated Tests

```bash
pytest -v
```

---

## Deploy Online 24/7 (Agar Bisa Diakses Teman Saat Laptop Mati)

Repositori ini sudah dilengkapi `cloud_entry.py` yang menggabungkan **HRM Utama (`/`)** dan **3 Simulator Mitra (`/mock/keuangan/`, `/mock/crm/`, `/mock/scm/`)** ke dalam **1 port tunggal** sehingga langsung berjalan di layanan cloud gratis:

* **Render.com (Paling Mudah & Gratis via GitHub — `render.yaml` siap pakai):**
  1. Push folder ini ke repository GitHub baru.
  2. Buka [Render](https://render.com) → **New +** → **Blueprint** (atau **Web Service**) → pilih repo GitHub tersebut.
  3. Render otomatis membaca `render.yaml` (`uvicorn cloud_entry:app --host 0.0.0.0 --port $PORT`).
  4. Setelah selesai, bagikan link `https://<nama-app>.onrender.com` ke teman sekelompok dan kelompok lain!
     * HRM Utama: `https://<nama-app>.onrender.com/`
     * Swagger API: `https://<nama-app>.onrender.com/docs`
     * Mock Keuangan (Kel. 2): `https://<nama-app>.onrender.com/mock/keuangan/`
     * Mock CRM (Kel. 7): `https://<nama-app>.onrender.com/mock/crm/`
     * Mock SCM (Kel. 8): `https://<nama-app>.onrender.com/mock/scm/`
* **Railway / Hugging Face Spaces (`Dockerfile` / `Procfile` siap pakai):** Cukup hubungkan repo GitHub yang sama.
* **Vercel (`vercel.json` + `api/index.py` siap pakai):** Gunakan mode *Import Git Repository* di Vercel (catatan: di Vercel database SQLite tersimpan di `/tmp` sementara per sesi instance).

