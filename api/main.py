"""
FastAPI Main Application - Carta de Manifestacion Generator API
Aplicacion Principal FastAPI - API del Generador de Cartas de Manifestacion
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime
import uuid
import secrets
import sys
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.schemas import (
    LoginRequest, LoginResponse, UserResponse,
    DocumentGenerationRequest, DocumentGenerationResponse,
    DownloadRequest, DownloadResponse,
    SystemStatusResponse, AccountsListResponse, FileHashInfo,
    AccountTypeEnum
)
from modules.auth import (
    AccountType, verify_normal_account, verify_pro_account,
    get_all_normal_accounts, get_user_permissions
)
from modules.generate import generate_from_form
from modules.plugin_loader import load_plugin
from modules.file_hash import generate_file_hash, create_full_metadata_record
from modules.pdf_converter import (
    convert_docx_to_pdf, get_pdf_conversion_status, PDFConversionError,
    add_hash_footer_to_pdf, PDF_FOOTER_AVAILABLE
)
import json


# Plugin configuration
PLUGIN_ID = "carta_manifestacion"

# Simple in-memory token storage (in production, use proper session/JWT management)
active_sessions = {}

# Store generated documents info
generated_documents = {}

# Create FastAPI app
app = FastAPI(
    title="Carta de Manifestacion Generator API",
    description="API para generar Cartas de Manifestacion - Forvis Mazars",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the UI
static_path = PROJECT_ROOT / "api" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ==================== Helper Functions ====================

def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get current user from authorization token
    Obtener usuario actual desde token de autorizacion
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization token provided")

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = parts[1]

    if token not in active_sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return active_sessions[token]


# ==================== Authentication Endpoints ====================

@app.post("/api/auth/login", response_model=LoginResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """
    Login endpoint - Authenticate user
    Endpoint de inicio de sesion - Autenticar usuario
    """
    user = None

    if request.account_type == AccountTypeEnum.NORMAL:
        user = verify_normal_account(request.username)
        if not user:
            return LoginResponse(
                success=False,
                message="Usuario no encontrado. Verifique el correo electronico."
            )
    else:  # PRO account
        if not request.password:
            return LoginResponse(
                success=False,
                message="Se requiere contrasena para cuentas Pro."
            )
        user = verify_pro_account(request.username, request.password)
        if not user:
            return LoginResponse(
                success=False,
                message="Credenciales incorrectas."
            )

    # Generate session token
    token = secrets.token_urlsafe(32)
    active_sessions[token] = user

    # Get permissions
    permissions = get_user_permissions(user)

    return LoginResponse(
        success=True,
        message=f"Bienvenido/a, {user.display_name}!",
        user=UserResponse(
            username=user.username,
            account_type=AccountTypeEnum(user.account_type.value),
            display_name=user.display_name,
            email=user.email,
            permissions=permissions
        ),
        token=token
    )


@app.post("/api/auth/logout", tags=["Authentication"])
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout endpoint - End user session
    Endpoint de cierre de sesion - Terminar sesion de usuario
    """
    if authorization:
        parts = authorization.split()
        if len(parts) == 2:
            token = parts[1]
            if token in active_sessions:
                del active_sessions[token]

    return {"success": True, "message": "Sesion cerrada correctamente."}


@app.get("/api/auth/accounts", response_model=AccountsListResponse, tags=["Authentication"])
async def get_accounts():
    """
    Get available accounts list
    Obtener lista de cuentas disponibles
    """
    return AccountsListResponse(
        normal_accounts=get_all_normal_accounts(),
        pro_accounts_hint=["admin", "mariajose.arrebola@forvismazars.com"]
    )


@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(user=Depends(get_current_user)):
    """
    Get current user information
    Obtener informacion del usuario actual
    """
    permissions = get_user_permissions(user)
    return UserResponse(
        username=user.username,
        account_type=AccountTypeEnum(user.account_type.value),
        display_name=user.display_name,
        email=user.email,
        permissions=permissions
    )


# ==================== Document Generation Endpoints ====================

@app.post("/api/documents/generate", response_model=DocumentGenerationResponse, tags=["Documents"])
async def generate_document(request: DocumentGenerationRequest, user=Depends(get_current_user)):
    """
    Generate a new Carta de Manifestacion document
    Generar un nuevo documento de Carta de Manifestacion
    """
    try:
        # Load plugin
        plugin = load_plugin(PLUGIN_ID)

        # Get template path
        template_path = PROJECT_ROOT / "Modelo de plantilla.docx"
        if not template_path.exists():
            template_path = plugin.get_template_path()

        if not template_path.exists():
            return DocumentGenerationResponse(
                success=False,
                message="No se encontro el archivo de plantilla."
            )

        # Prepare form data
        form_data = request.model_dump()

        # Convert directors list to expected format
        if request.lista_alto_directores:
            form_data['lista_alto_directores'] = [
                {"nombre": d.nombre, "cargo": d.cargo}
                for d in request.lista_alto_directores
            ]

        # Generate document
        result = generate_from_form(
            plugin_id=PLUGIN_ID,
            form_data=form_data,
            list_data={},
            output_dir=PROJECT_ROOT / "output",
            template_path=template_path
        )

        if result.success and result.output_path:
            # Generate file hash with document type
            creation_time = datetime.now()
            hash_info = generate_file_hash(
                file_path=result.output_path,
                creation_time=creation_time,
                user_id=user.username,
                client_name=request.Nombre_Cliente,
                document_type=PLUGIN_ID  # Use plugin ID as document type
            )

            # Create user output directory for metadata storage
            user_output_dir = PROJECT_ROOT / "output" / user.username
            user_output_dir.mkdir(parents=True, exist_ok=True)

            # Create full metadata record and save to user folder
            metadata_record = create_full_metadata_record(
                hash_info=hash_info,
                form_data=form_data,
                trace_id=result.trace_id,
                output_file_name=result.output_path.name
            )

            # Save metadata JSON file to user folder root
            metadata_filename = f"metadata_{hash_info.hash_code}_{result.trace_id[:8]}.json"
            metadata_path = user_output_dir / metadata_filename
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_record, f, ensure_ascii=False, indent=2, default=str)

            # Store document info including form_data for future reference
            generated_documents[result.trace_id] = {
                "output_path": result.output_path,
                "hash_info": hash_info,
                "user": user,
                "client_name": request.Nombre_Cliente,
                "creation_time": creation_time,
                "form_data": form_data,
                "metadata_path": metadata_path
            }

            # Get user permissions
            permissions = get_user_permissions(user)

            # Prepare download links
            download_links = {
                "pdf": f"/api/documents/download/{result.trace_id}/pdf"
            }
            if permissions["can_download_word"]:
                download_links["docx"] = f"/api/documents/download/{result.trace_id}/docx"

            return DocumentGenerationResponse(
                success=True,
                message="Carta generada exitosamente!",
                trace_id=result.trace_id,
                hash_info=FileHashInfo(
                    hash_code=hash_info.hash_code,
                    algorithm=hash_info.algorithm,
                    file_size=hash_info.file_size,
                    creation_timestamp=hash_info.creation_timestamp,
                    creation_timestamp_iso=hash_info.creation_timestamp_iso,
                    content_hash=hash_info.content_hash,
                    metadata_hash=hash_info.metadata_hash,
                    combined_hash=hash_info.combined_hash,
                    user_id=hash_info.user_id,
                    client_name=hash_info.client_name,
                    document_type=hash_info.document_type,
                    document_type_display=hash_info.document_type_display
                ),
                duration_ms=result.duration_ms,
                download_links=download_links
            )
        else:
            return DocumentGenerationResponse(
                success=False,
                message=f"Error al generar la carta: {result.error}",
                trace_id=result.trace_id,
                validation_errors=result.validation_errors
            )

    except Exception as e:
        return DocumentGenerationResponse(
            success=False,
            message=f"Error al generar la carta: {str(e)}"
        )


@app.get("/api/documents/download/{trace_id}/{format}", tags=["Documents"])
async def download_document(trace_id: str, format: str, user=Depends(get_current_user)):
    """
    Download generated document
    Descargar documento generado
    """
    # Check if document exists
    if trace_id not in generated_documents:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    doc_info = generated_documents[trace_id]
    output_path = doc_info["output_path"]
    hash_info = doc_info["hash_info"]

    # Get user permissions
    permissions = get_user_permissions(user)

    # Check permissions
    if format == "docx" and not permissions["can_download_word"]:
        raise HTTPException(
            status_code=403,
            detail="Los usuarios normales solo pueden descargar en formato PDF."
        )

    base_filename = f"Carta_Manifestacion_{doc_info['client_name'].replace(' ', '_')}_{hash_info.hash_code[:8]}"

    if format == "pdf":
        # Check if PDF conversion is available
        pdf_status = get_pdf_conversion_status()
        if not pdf_status["pdf_conversion_available"]:
            raise HTTPException(
                status_code=503,
                detail="Conversion a PDF no disponible. LibreOffice no esta instalado."
            )

        try:
            pdf_path = convert_docx_to_pdf(output_path)

            # Add hash footer to PDF for normal users (non-PRO accounts)
            if PDF_FOOTER_AVAILABLE:
                try:
                    add_hash_footer_to_pdf(pdf_path, hash_info.hash_code)
                except Exception as footer_error:
                    # Log error but continue - footer is optional
                    print(f"Warning: Could not add hash footer to PDF: {footer_error}")

            return FileResponse(
                path=str(pdf_path),
                filename=f"{base_filename}.pdf",
                media_type="application/pdf"
            )
        except PDFConversionError as e:
            raise HTTPException(status_code=500, detail=f"Error al convertir a PDF: {str(e)}")

    elif format == "docx":
        return FileResponse(
            path=str(output_path),
            filename=f"{base_filename}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    else:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use 'pdf' o 'docx'.")


# ==================== System Endpoints ====================

@app.get("/api/system/status", response_model=SystemStatusResponse, tags=["System"])
async def get_system_status():
    """
    Get system status
    Obtener estado del sistema
    """
    pdf_status = get_pdf_conversion_status()

    return SystemStatusResponse(
        status="operational",
        pdf_conversion_available=pdf_status["pdf_conversion_available"],
        libreoffice_path=pdf_status["libreoffice"]["path"],
        platform=pdf_status["platform"],
        version="1.1.0"  # Updated version with hash footer feature
    )


@app.get("/api/system/health", tags=["System"])
async def health_check():
    """
    Health check endpoint
    Endpoint de verificacion de salud
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ==================== UI Endpoint ====================

@app.get("/", tags=["UI"])
async def serve_ui():
    """
    Serve the main UI page
    Servir la pagina principal de UI
    """
    ui_path = PROJECT_ROOT / "api" / "static" / "index.html"
    if ui_path.exists():
        return FileResponse(str(ui_path))
    else:
        return JSONResponse(
            content={
                "message": "API is running. Visit /api/docs for documentation.",
                "docs_url": "/api/docs",
                "redoc_url": "/api/redoc"
            }
        )


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
