/* Helper frontend Sistem HRM Kelompok 12 */

function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatRupiah(amount) {
  const num = Number(amount || 0);
  return "Rp " + num.toLocaleString("id-ID");
}

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const colors = {
    success: "bg-emerald-700 text-white",
    error: "bg-rose-700 text-white",
    info: "bg-slate-800 text-white",
  };
  const el = document.createElement("div");
  el.className = `px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 transition-all ${colors[type] || colors.info}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("opacity-0");
    setTimeout(() => el.remove(), 300);
  }, 3800);
}

async function apiFetch(url, options = {}) {
  const opts = {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  };
  const res = await fetch(url, opts);
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data?.detail;
    const msg =
      data?.error?.message ||
      (typeof detail === "string"
        ? detail
        : detail?.error?.message || detail?.error?.error || detail?.message || detail?.error || JSON.stringify(detail || `HTTP ${res.status}`));
    throw new Error(msg);
  }
  return data;
}

function statusBadge(status) {
  const s = String(status || "").toUpperCase();
  const map = {
    AKTIF: "badge-green",
    ONLINE: "badge-green",
    APPROVED: "badge-green",
    PAID: "badge-green",
    VALID: "badge-green",
    HIRED: "badge-green",
    FILLED: "badge-green",
    HADIR: "badge-green",
    SENT_TO_FINANCE: "badge-blue",
    POSTED: "badge-blue",
    FINAL: "badge-blue",
    INTERVIEW: "badge-blue",
    OPEN: "badge-blue",
    SCREENING: "badge-purple",
    OFFERED: "badge-purple",
    PENDING: "badge-amber",
    PENDING_APPROVAL: "badge-amber",
    UNPAID: "badge-amber",
    BELUM_CEK: "badge-amber",
    CUTI: "badge-amber",
    TERLAMBAT: "badge-amber",
    DRAFT: "badge-slate",
    INTERNAL: "badge-slate",
    CRM_SALES: "badge-purple",
    SCM_OPS: "badge-blue",
    FINANCE: "badge-amber",
    NONAKTIF: "badge-red",
    OFFLINE: "badge-red",
    REJECTED: "badge-red",
    FAILED: "badge-red",
    ALPHA: "badge-red",
  };
  return `<span class="badge ${map[s] || "badge-slate"}">${esc(s)}</span>`;
}

async function switchCompanyTheme(themeKey) {
  if (!confirm(`Ubah profil perusahaan & muat ulang data demo untuk tema "${themeKey.toUpperCase()}"?\n(Konfigurasi URL partner tetap dipertahankan)`)) {
    window.location.reload();
    return;
  }
  try {
    const res = await apiFetch("/api/v1/system/switch-theme", {
      method: "POST",
      body: JSON.stringify({ theme_key: themeKey, preserve_partners: true }),
    });
    showToast(`Tema berubah: ${res.company_name}`, "success");
    setTimeout(() => window.location.reload(), 600);
  } catch (err) {
    showToast("Gagal mengganti tema: " + err.message, "error");
  }
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("hidden");
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add("hidden");
}
