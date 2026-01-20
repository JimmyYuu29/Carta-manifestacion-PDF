"""
Pydantic Schemas for API - Request and Response Models
Schemas Pydantic para API - Modelos de Solicitud y Respuesta
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import date, datetime


class AccountTypeEnum(str, Enum):
    """Account type enumeration / Enumeracion de tipo de cuenta"""
    NORMAL = "normal"
    PRO = "pro"


# ==================== Authentication Schemas ====================

class LoginRequest(BaseModel):
    """Login request model / Modelo de solicitud de inicio de sesion"""
    username: str = Field(..., description="Username or email")
    password: Optional[str] = Field(None, description="Password (required for Pro accounts)")
    account_type: AccountTypeEnum = Field(..., description="Account type (normal or pro)")


class UserResponse(BaseModel):
    """User response model / Modelo de respuesta de usuario"""
    username: str
    account_type: AccountTypeEnum
    display_name: str
    email: Optional[str] = None
    permissions: Dict[str, bool]


class LoginResponse(BaseModel):
    """Login response model / Modelo de respuesta de inicio de sesion"""
    success: bool
    message: str
    user: Optional[UserResponse] = None
    token: Optional[str] = None


# ==================== Document Generation Schemas ====================

class DirectorInfo(BaseModel):
    """Director information / Informacion del director"""
    nombre: str = Field(..., description="Director name")
    cargo: str = Field(..., description="Director position")


class DocumentGenerationRequest(BaseModel):
    """Document generation request / Solicitud de generacion de documento"""
    # Office info
    Direccion_Oficina: str = Field(..., description="Office address")
    CP: str = Field(..., description="Postal code")
    Ciudad_Oficina: str = Field(..., description="Office city")

    # Client info
    Nombre_Cliente: str = Field(..., description="Client name")

    # Dates (accept both string and date formats)
    Fecha_de_hoy: Optional[str] = Field(None, description="Today's date (DD/MM/YYYY)")
    Fecha_encargo: Optional[str] = Field(None, description="Assignment date (DD/MM/YYYY)")
    FF_Ejecicio: Optional[str] = Field(None, description="Fiscal year end date (DD/MM/YYYY)")
    Fecha_cierre: Optional[str] = Field(None, description="Closing date (DD/MM/YYYY)")

    # General info
    Lista_Abogados: Optional[str] = Field("", description="List of lawyers and tax advisors")
    anexo_partes: Optional[str] = Field("2", description="Related parties annex number")
    anexo_proyecciones: Optional[str] = Field("3", description="Projections annex number")

    # Administration organ
    organo: Optional[str] = Field("consejo", description="Administration organ type")

    # Conditional options (as 'si' or 'no')
    comision: Optional[str] = Field("no", description="Has audit committee")
    junta: Optional[str] = Field("no", description="Include shareholders meeting")
    comite: Optional[str] = Field("no", description="Include committee")
    incorreccion: Optional[str] = Field("no", description="Has uncorrected misstatements")
    dudas: Optional[str] = Field("no", description="Going concern doubts")
    rent: Optional[str] = Field("no", description="Include leases paragraph")
    A_coste: Optional[str] = Field("no", description="Assets at cost")
    experto: Optional[str] = Field("no", description="Used independent expert")
    unidad_decision: Optional[str] = Field("no", description="Under same decision unit")
    activo_impuesto: Optional[str] = Field("no", description="Has deferred tax assets")
    operacion_fiscal: Optional[str] = Field("no", description="Tax haven operations")
    compromiso: Optional[str] = Field("no", description="Pension commitments")
    gestion: Optional[str] = Field("no", description="Include management report")
    limitacion_alcance: Optional[str] = Field("no", description="Scope limitation")

    # Additional fields for conditional options
    Anio_incorreccion: Optional[str] = Field("", description="Misstatement year")
    Epigrafe: Optional[str] = Field("", description="Affected section")
    detalle_limitacion: Optional[str] = Field("", description="Limitation details")
    nombre_experto: Optional[str] = Field("", description="Expert name")
    experto_valoracion: Optional[str] = Field("", description="Expert valuation element")
    nombre_unidad: Optional[str] = Field("", description="Unit name")
    nombre_mayor_sociedad: Optional[str] = Field("", description="Largest company name")
    localizacion_mer: Optional[str] = Field("", description="Commercial location")
    ejercicio_recuperacion_inicio: Optional[str] = Field("", description="Recovery start year")
    ejercicio_recuperacion_fin: Optional[str] = Field("", description="Recovery end year")
    detalle_operacion_fiscal: Optional[str] = Field("", description="Tax operation details")

    # Directors list
    lista_alto_directores: Optional[List[DirectorInfo]] = Field(default_factory=list)

    # Signature
    Nombre_Firma: Optional[str] = Field("", description="Signatory name")
    Cargo_Firma: Optional[str] = Field("", description="Signatory position")

    class Config:
        json_schema_extra = {
            "example": {
                "Direccion_Oficina": "Calle Example 123",
                "CP": "28001",
                "Ciudad_Oficina": "Madrid",
                "Nombre_Cliente": "Empresa ABC S.L.",
                "Fecha_de_hoy": "20/01/2026",
                "organo": "consejo",
                "comision": "si",
                "lista_alto_directores": [
                    {"nombre": "Juan Perez", "cargo": "Director General"},
                    {"nombre": "Maria Garcia", "cargo": "Director Financiero"}
                ],
                "Nombre_Firma": "Carlos Lopez",
                "Cargo_Firma": "Presidente"
            }
        }


class FileHashInfo(BaseModel):
    """File hash information / Informacion de hash del archivo"""
    hash_code: str
    algorithm: str
    file_size: int
    creation_timestamp: str
    creation_timestamp_iso: str
    content_hash: str
    metadata_hash: str
    combined_hash: str
    user_id: Optional[str] = None
    client_name: Optional[str] = None


class DocumentGenerationResponse(BaseModel):
    """Document generation response / Respuesta de generacion de documento"""
    success: bool
    message: str
    trace_id: Optional[str] = None
    hash_info: Optional[FileHashInfo] = None
    duration_ms: Optional[int] = None
    download_links: Optional[Dict[str, str]] = None
    validation_errors: Optional[List[str]] = None


# ==================== Download Schemas ====================

class DownloadRequest(BaseModel):
    """Download request model / Modelo de solicitud de descarga"""
    trace_id: str = Field(..., description="Document trace ID")
    format: str = Field(..., description="Download format (pdf or docx)")


class DownloadResponse(BaseModel):
    """Download response model / Modelo de respuesta de descarga"""
    success: bool
    message: str
    download_url: Optional[str] = None
    filename: Optional[str] = None


# ==================== System Status Schemas ====================

class SystemStatusResponse(BaseModel):
    """System status response / Respuesta de estado del sistema"""
    status: str
    pdf_conversion_available: bool
    libreoffice_path: Optional[str] = None
    platform: str
    version: str = "1.0.0"


# ==================== Accounts List Schema ====================

class AccountsListResponse(BaseModel):
    """Available accounts list response / Respuesta de lista de cuentas disponibles"""
    normal_accounts: List[str]
    pro_accounts_hint: List[str]
