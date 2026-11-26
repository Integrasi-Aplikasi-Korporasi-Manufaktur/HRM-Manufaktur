"""Skema Pydantic untuk validasi request/response REST API Sistem HRM."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    client_id: str = Field(..., examples=["kel7_crm"])
    client_secret: str = Field(..., examples=["secret-kel7-crm"])


class ThemeSwitchRequest(BaseModel):
    theme_key: Literal["software", "manufaktur", "telekomunikasi"]
    preserve_partners: bool = True


class EmployeeCreate(BaseModel):
    employee_code: Optional[str] = Field(default=None, description="Kosongkan untuk generate otomatis (EMP-xxx)")
    full_name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    phone: str = ""
    department_id: int
    position_title: str = Field(..., min_length=2)
    employment_type: Literal["TETAP", "KONTRAK", "MAGANG"] = "TETAP"
    integration_role: Literal["INTERNAL", "CRM_SALES", "SCM_OPS", "FINANCE"] = "INTERNAL"
    status: Literal["AKTIF", "CUTI", "NONAKTIF"] = "AKTIF"
    join_date: str = "2026-11-01"
    base_salary: int = Field(..., ge=0)
    fixed_allowance: int = Field(default=0, ge=0)
    overtime_rate: int = Field(default=50000, ge=0)
    bank_name: str = "BCA"
    bank_account: str = ""
    leave_quota: int = Field(default=12, ge=0)
    notes: str = ""


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    position_title: Optional[str] = None
    employment_type: Optional[Literal["TETAP", "KONTRAK", "MAGANG"]] = None
    integration_role: Optional[Literal["INTERNAL", "CRM_SALES", "SCM_OPS", "FINANCE"]] = None
    status: Optional[Literal["AKTIF", "CUTI", "NONAKTIF"]] = None
    base_salary: Optional[int] = Field(default=None, ge=0)
    fixed_allowance: Optional[int] = Field(default=None, ge=0)
    overtime_rate: Optional[int] = Field(default=None, ge=0)
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    leave_quota: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class CertificationCreate(BaseModel):
    employee_id: int
    cert_name: str = Field(..., min_length=2)
    issuer: str = Field(..., min_length=2)
    issued_date: str
    expiry_date: str = ""
    status: Literal["VALID", "EXPIRED", "RENEWAL"] = "VALID"


class AttendanceCreate(BaseModel):
    employee_id: int
    work_date: str
    status: Literal["HADIR", "TERLAMBAT", "IZIN", "SAKIT", "CUTI", "ALPHA"] = "HADIR"
    regular_hours: float = Field(default=8.0, ge=0)
    overtime_hours: float = Field(default=0.0, ge=0)
    note: str = ""


class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: Literal["TAHUNAN", "SAKIT", "MELAHIRKAN", "KHUSUS"] = "TAHUNAN"
    start_date: str
    end_date: str
    days_count: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3)


class LeaveDecision(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    reviewed_by: str = "HR Manager"


class ManpowerRequestCreate(BaseModel):
    requester_system: Literal["INTERNAL", "SCM", "CRM"] = "INTERNAL"
    department_id: Optional[int] = None
    department_code: Optional[str] = None
    cost_center: Optional[str] = None
    position_title: str = Field(..., min_length=2)
    headcount: int = Field(default=1, ge=1)
    estimated_salary: int = Field(default=7000000, ge=0)
    period: str = Field(default="2026-11", pattern=r"^\d{4}-\d{2}$")
    reason: str = Field(..., min_length=3)


class ApplicantCreate(BaseModel):
    manpower_request_id: int
    full_name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    phone: str = ""
    skills: str = ""


class ApplicantStageUpdate(BaseModel):
    stage: Literal["APPLIED", "SCREENING", "INTERVIEW", "OFFERED", "HIRED", "REJECTED"]
    hire_bank_name: str = "BCA"
    hire_bank_account: str = ""
    hire_integration_role: Literal["INTERNAL", "CRM_SALES", "SCM_OPS", "FINANCE"] = "INTERNAL"


class PayrollGenerateRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$", examples=["2026-11"])
    sync_external: bool = True


class PaymentCallbackRequest(BaseModel):
    status: Optional[Literal["UNPAID", "PAID", "FAILED", "REJECTED"]] = None
    payment_status: Optional[Literal["UNPAID", "PAID", "FAILED", "REJECTED"]] = None
    finance_ref: str = ""
    amount_minor: Optional[int] = Field(default=None, ge=0)
    currency: str = "IDR"
    note: str = ""

    def resolved_status(self) -> str:
        val = self.payment_status or self.status
        if not val:
            raise ValueError("Field 'payment_status' atau 'status' wajib diisi.")
        return val


class PartnerConfigUpdate(BaseModel):
    partner_name: Optional[str] = None
    base_url: str
    auth_type: Literal["OAUTH_BEARER", "API_KEY", "NONE"] = "OAUTH_BEARER"
    token_endpoint: str = "/oauth/token"
    client_id: str = ""
    client_secret: str = ""
    api_key_header: str = "X-API-Key"
    api_key_value: str = ""
    endpoints: dict[str, Any]
    field_mapping: dict[str, Any]
    is_active: bool = True


class InboundClientCreate(BaseModel):
    client_id: str = Field(..., min_length=3)
    client_secret: str = Field(..., min_length=6)
    partner_name: str = Field(..., min_length=3)
    allowed_scopes: str = "read,write"
