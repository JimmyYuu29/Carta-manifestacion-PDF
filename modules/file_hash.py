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

    # Build metadata for hashing
    metadata = {
        "creation_timestamp": creation_time.isoformat(),
        "file_name": file_path.name,
        "file_size": file_size,
        "content_hash": content_hash
    }

    if user_id:
        metadata["user_id"] = user_id
    if client_name:
        metadata["client_name"] = client_name
    if additional_metadata:
        metadata.update(additional_metadata)

    # Generate metadata hash
    metadata_hash = generate_metadata_hash(metadata)

    # Generate combined hash (content + metadata + timestamp)
    combined_string = f"{content_hash}:{metadata_hash}:{creation_time.isoformat()}"
    combined_hash = hashlib.sha256(combined_string.encode()).hexdigest()

    # Create short hash code for display (first 16 characters of combined hash)
    hash_code = combined_hash[:16].upper()

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
        client_name=client_name
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
        "file_size": hash_info.file_size,
        "algorithm": hash_info.algorithm
    }

    if hash_info.user_id:
        record["user_id"] = hash_info.user_id
    if hash_info.client_name:
        record["client_name"] = hash_info.client_name
    if additional_info:
        record["additional_info"] = additional_info

    return record
