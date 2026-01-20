"""
PDF Converter Module - Convert DOCX files to PDF
Modulo de Conversion PDF - Convertir archivos DOCX a PDF
"""

import subprocess
import os
import platform
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil


class PDFConversionError(Exception):
    """Custom exception for PDF conversion errors"""
    pass


def check_libreoffice_available() -> Tuple[bool, Optional[str]]:
    """
    Check if LibreOffice is available for conversion
    Verificar si LibreOffice esta disponible para conversion

    Returns:
        Tuple of (is_available, path_to_soffice)
    """
    # Common paths for LibreOffice
    possible_paths = [
        "libreoffice",
        "soffice",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/usr/local/bin/libreoffice",
        "/usr/local/bin/soffice",
        # macOS paths
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        # Windows paths
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for path in possible_paths:
        if shutil.which(path):
            return True, path

    return False, None


def convert_docx_to_pdf_libreoffice(
    docx_path: Path,
    output_dir: Optional[Path] = None,
    timeout: int = 60
) -> Path:
    """
    Convert DOCX to PDF using LibreOffice
    Convertir DOCX a PDF usando LibreOffice

    Args:
        docx_path: Path to the DOCX file
        output_dir: Optional output directory (defaults to same as input)
        timeout: Conversion timeout in seconds

    Returns:
        Path to the generated PDF file

    Raises:
        PDFConversionError: If conversion fails
    """
    is_available, soffice_path = check_libreoffice_available()

    if not is_available:
        raise PDFConversionError(
            "LibreOffice no esta instalado o no se encuentra en el PATH. "
            "Por favor instale LibreOffice para habilitar la conversion a PDF."
        )

    if output_dir is None:
        output_dir = docx_path.parent

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Build command
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(docx_path)
        ]

        # Run conversion
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            raise PDFConversionError(
                f"LibreOffice conversion failed: {result.stderr}"
            )

        # Get expected PDF path
        pdf_path = output_dir / f"{docx_path.stem}.pdf"

        if not pdf_path.exists():
            raise PDFConversionError(
                f"PDF file was not created at expected path: {pdf_path}"
            )

        return pdf_path

    except subprocess.TimeoutExpired:
        raise PDFConversionError(
            f"Conversion timed out after {timeout} seconds"
        )
    except Exception as e:
        if isinstance(e, PDFConversionError):
            raise
        raise PDFConversionError(f"Conversion error: {str(e)}")


def convert_docx_to_pdf(
    docx_path: Path,
    output_path: Optional[Path] = None,
    method: str = "auto"
) -> Path:
    """
    Convert DOCX to PDF using the best available method
    Convertir DOCX a PDF usando el mejor metodo disponible

    Args:
        docx_path: Path to the DOCX file
        output_path: Optional specific output path for PDF
        method: Conversion method ('auto', 'libreoffice')

    Returns:
        Path to the generated PDF file

    Raises:
        PDFConversionError: If conversion fails
    """
    if not docx_path.exists():
        raise PDFConversionError(f"DOCX file not found: {docx_path}")

    if output_path is None:
        output_dir = docx_path.parent
        output_path = output_dir / f"{docx_path.stem}.pdf"
    else:
        output_dir = output_path.parent

    # Try LibreOffice
    if method in ("auto", "libreoffice"):
        try:
            pdf_path = convert_docx_to_pdf_libreoffice(docx_path, output_dir)

            # Rename if needed
            if pdf_path != output_path:
                shutil.move(str(pdf_path), str(output_path))

            return output_path
        except PDFConversionError as e:
            if method == "libreoffice":
                raise
            # If auto, continue to next method or fail gracefully

    raise PDFConversionError(
        "No se pudo convertir el documento a PDF. "
        "Asegurese de que LibreOffice este instalado."
    )


def get_pdf_conversion_status() -> dict:
    """
    Get status of PDF conversion capabilities
    Obtener estado de capacidades de conversion a PDF

    Returns:
        Dictionary with conversion capability status
    """
    libreoffice_available, libreoffice_path = check_libreoffice_available()

    return {
        "pdf_conversion_available": libreoffice_available,
        "libreoffice": {
            "available": libreoffice_available,
            "path": libreoffice_path
        },
        "recommended_method": "libreoffice" if libreoffice_available else None,
        "platform": platform.system()
    }
