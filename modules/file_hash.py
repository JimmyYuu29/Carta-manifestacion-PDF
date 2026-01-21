"""
File Hash Module - Generate unique hash codes for document tracking and auditing
Modulo de Hash de Archivo - Generar codigos hash unicos para seguimiento y auditoria de documentos
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FileHashInfo:
    """File hash information / Informacion de hash de archivo"""
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
    document_type: Optional[str] = None
    document_type_display: Optional[str] = None


# Document type definitions / Definiciones de tipos de documento
DOCUMENT_TYPES = {
    "carta_manifestacion": {
        "code": "CM",
        "display_name": "Carta de Manifestación",
        "description": "Carta de manifestación de la dirección para auditoría"
    },
    "informe_auditoria": {
        "code": "IA",
        "display_name": "Informe de Auditoría",
        "description": "Informe oficial de auditoría"
    },
    "carta_encargo": {
        "code": "CE",
        "display_name": "Carta de Encargo",
        "description": "Carta de encargo de auditoría"
    },
    "informe_revision": {
        "code": "IR",
        "display_name": "Informe de Revisión",
        "description": "Informe de revisión limitada"
    },
    "otros": {
        "code": "OT",
        "display_name": "Otros Documentos",
        "description": "Otros documentos de auditoría"
    }
}


def get_document_type_info(document_type: str) -> Dict[str, str]:
    """
    Get document type information
    Obtener información del tipo de documento

    Args:
        document_type: Document type identifier

    Returns:
        Dictionary with document type info
    """
    return DOCUMENT_TYPES.get(document_type, DOCUMENT_TYPES["otros"])


def generate_content_hash(file_path: Path) -> str:
    """
    Generate SHA-256 hash from file content
    Generar hash SHA-256 del contenido del archivo

    Args:
        file_path: Path to the file

    Returns:
        SHA-256 hash string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def generate_metadata_hash(metadata: Dict[str, Any]) -> str:
    """
    Generate hash from metadata dictionary
    Generar hash del diccionario de metadatos

    Args:
        metadata: Dictionary containing metadata

    Returns:
        SHA-256 hash string
    """
    # Sort keys for consistent hashing
    metadata_str = json.dumps(metadata, sort_keys=True, default=str)
    return hashlib.sha256(metadata_str.encode()).hexdigest()


def generate_file_hash(
    file_path: Path,
    creation_time: Optional[datetime] = None,
    user_id: Optional[str] = None,
    client_name: Optional[str] = None,
    document_type: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> FileHashInfo:
    """
    Generate comprehensive hash for a file including content and timestamp
    Generar hash completo para un archivo incluyendo contenido y marca de tiempo

    Args:
        file_path: Path to the file
        creation_time: Optional creation timestamp (defaults to now)
        user_id: Optional user identifier
        client_name: Optional client name
        document_type: Optional document type identifier (e.g., 'carta_manifestacion')
        additional_metadata: Optional additional metadata to include

    Returns:
        FileHashInfo object with all hash details
    """
    if creation_time is None:
        creation_time = datetime.now()

    # Get file size
    file_size = file_path.stat().st_size

    # Generate content hash
    content_hash = generate_content_hash(file_path)

    # Get document type info
    doc_type_info = get_document_type_info(document_type) if document_type else get_document_type_info("otros")
    doc_type_code = doc_type_info["code"]
    doc_type_display = doc_type_info["display_name"]

    # Build metadata for hashing
    metadata = {
        "creation_timestamp": creation_time.isoformat(),
        "file_name": file_path.name,
        "file_size": file_size,
        "content_hash": content_hash,
        "document_type": document_type or "otros",
        "document_type_code": doc_type_code
    }

    if user_id:
        metadata["user_id"] = user_id
    if client_name:
        metadata["client_name"] = client_name
    if additional_metadata:
        metadata.update(additional_metadata)

    # Generate metadata hash
    metadata_hash = generate_metadata_hash(metadata)

    # Generate combined hash (content + metadata + timestamp + document_type)
    combined_string = f"{content_hash}:{metadata_hash}:{creation_time.isoformat()}:{doc_type_code}"
    combined_hash = hashlib.sha256(combined_string.encode()).hexdigest()

    # Create short hash code for display with document type prefix
    # Format: [DOC_TYPE_CODE]-[FIRST 12 CHARS OF HASH] e.g., CM-A1B2C3D4E5F6
    hash_code = f"{doc_type_code}-{combined_hash[:12].upper()}"

    return FileHashInfo(
        hash_code=hash_code,
        algorithm="SHA-256",
        file_size=file_size,
        creation_timestamp=creation_time.strftime("%d/%m/%Y %H:%M:%S"),
        creation_timestamp_iso=creation_time.isoformat(),
        content_hash=content_hash,
        metadata_hash=metadata_hash,
        combined_hash=combined_hash,
        user_id=user_id,
        client_name=client_name,
        document_type=document_type or "otros",
        document_type_display=doc_type_display
    )


def verify_file_hash(
    file_path: Path,
    expected_content_hash: str
) -> Tuple[bool, str]:
    """
    Verify file integrity by comparing content hash
    Verificar integridad del archivo comparando hash de contenido

    Args:
        file_path: Path to the file
        expected_content_hash: Expected SHA-256 hash

    Returns:
        Tuple of (is_valid, actual_hash)
    """
    actual_hash = generate_content_hash(file_path)
    is_valid = actual_hash.lower() == expected_content_hash.lower()
    return is_valid, actual_hash


def format_hash_for_display(hash_info: FileHashInfo) -> str:
    """
    Format hash information for display
    Formatear informacion de hash para mostrar

    Args:
        hash_info: FileHashInfo object

    Returns:
        Formatted string for display
    """
    lines = [
        f"Codigo de Hash: {hash_info.hash_code}",
        f"Tipo de Documento: {hash_info.document_type_display or 'No especificado'}",
        f"Algoritmo: {hash_info.algorithm}",
        f"Fecha de Creacion: {hash_info.creation_timestamp}",
        f"Tamano del Archivo: {hash_info.file_size:,} bytes",
    ]

    if hash_info.user_id:
        lines.append(f"Usuario: {hash_info.user_id}")
    if hash_info.client_name:
        lines.append(f"Cliente: {hash_info.client_name}")

    lines.extend([
        f"Hash de Contenido: {hash_info.content_hash[:32]}...",
        f"Hash Combinado: {hash_info.combined_hash[:32]}..."
    ])

    return "\n".join(lines)


def generate_audit_record(
    hash_info: FileHashInfo,
    action: str = "DOCUMENT_GENERATED",
    additional_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate audit record for tracking
    Generar registro de auditoria para seguimiento

    Args:
        hash_info: FileHashInfo object
        action: Action type
        additional_info: Additional information to include

    Returns:
        Dictionary with audit record
    """
    record = {
        "action": action,
        "timestamp": hash_info.creation_timestamp_iso,
        "hash_code": hash_info.hash_code,
        "content_hash": hash_info.content_hash,
        "combined_hash": hash_info.combined_hash,
        "metadata_hash": hash_info.metadata_hash,
        "file_size": hash_info.file_size,
        "algorithm": hash_info.algorithm,
        "document_type": hash_info.document_type,
        "document_type_display": hash_info.document_type_display
    }

    if hash_info.user_id:
        record["user_id"] = hash_info.user_id
    if hash_info.client_name:
        record["client_name"] = hash_info.client_name
    if additional_info:
        record["additional_info"] = additional_info

    return record


def create_full_metadata_record(
    hash_info: FileHashInfo,
    form_data: Dict[str, Any],
    trace_id: str,
    output_file_name: str
) -> Dict[str, Any]:
    """
    Create a complete metadata record for storage and verification
    Crear un registro de metadatos completo para almacenamiento y verificación

    Args:
        hash_info: FileHashInfo object
        form_data: Original form data used to generate the document
        trace_id: Unique trace ID for the document
        output_file_name: Name of the generated output file

    Returns:
        Complete metadata dictionary for JSON storage
    """
    return {
        "version": "1.0",
        "trace_id": trace_id,
        "hash_info": {
            "hash_code": hash_info.hash_code,
            "algorithm": hash_info.algorithm,
            "content_hash": hash_info.content_hash,
            "metadata_hash": hash_info.metadata_hash,
            "combined_hash": hash_info.combined_hash,
            "file_size": hash_info.file_size
        },
        "document_info": {
            "type": hash_info.document_type,
            "type_display": hash_info.document_type_display,
            "file_name": output_file_name,
            "creation_timestamp": hash_info.creation_timestamp,
            "creation_timestamp_iso": hash_info.creation_timestamp_iso
        },
        "user_info": {
            "user_id": hash_info.user_id,
            "client_name": hash_info.client_name
        },
        "form_data": form_data,
        "verification_instructions": {
            "es": "Para verificar este documento, use el código de hash en el verificador oficial de Forvis Mazars.",
            "en": "To verify this document, use the hash code in the official Forvis Mazars verifier."
        }
    }
