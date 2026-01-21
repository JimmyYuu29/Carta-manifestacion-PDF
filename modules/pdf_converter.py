"""
PDF Converter Module - Convert DOCX files to PDF
Modulo de Conversion PDF - Convertir archivos DOCX a PDF
"""

import subprocess
import os
import platform
import io
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil

# PDF manipulation imports
try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    PDF_FOOTER_AVAILABLE = True
except ImportError:
    PDF_FOOTER_AVAILABLE = False


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
    # Common absolute paths for LibreOffice (checked first for systemd compatibility)
    absolute_paths = [
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/usr/local/bin/libreoffice",
        "/usr/local/bin/soffice",
        "/snap/bin/libreoffice",
        "/opt/libreoffice/program/soffice",
        # macOS paths
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        # Windows paths
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
 
    # First check absolute paths directly (works even without PATH)
    for path in absolute_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return True, path
 
    # Fallback to PATH-based check
    for cmd in ["libreoffice", "soffice"]:
        found = shutil.which(cmd)
        if found:
            return True, found

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
        "pdf_footer_available": PDF_FOOTER_AVAILABLE,
        "recommended_method": "libreoffice" if libreoffice_available else None,
        "platform": platform.system()
    }


def create_hash_footer_overlay(
    hash_code: str,
    page_width: float,
    page_height: float,
    font_size: int = 8
) -> io.BytesIO:
    """
    Create a PDF overlay with hash code footer
    Crear una capa PDF con el codigo hash en el pie de pagina

    Args:
        hash_code: The hash code to display
        page_width: Width of the page
        page_height: Height of the page
        font_size: Font size for the hash code

    Returns:
        BytesIO buffer containing the overlay PDF
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Set font and color (gray for subtle appearance)
    c.setFont("Helvetica", font_size)
    c.setFillColor(Color(0.4, 0.4, 0.4, alpha=1))  # Gray color

    # Calculate center position for the hash code
    text_width = c.stringWidth(hash_code, "Helvetica", font_size)
    x_position = (page_width - text_width) / 2
    y_position = 25  # 25 points from bottom

    # Draw the hash code
    c.drawString(x_position, y_position, hash_code)

    c.save()
    packet.seek(0)
    return packet


def add_hash_footer_to_pdf(
    pdf_path: Path,
    hash_code: str,
    output_path: Optional[Path] = None,
    font_size: int = 8
) -> Path:
    """
    Add hash code footer to all pages of a PDF
    Anadir codigo hash en el pie de pagina a todas las paginas del PDF

    Args:
        pdf_path: Path to the input PDF
        hash_code: Hash code to add as footer
        output_path: Optional output path (defaults to overwrite input)
        font_size: Font size for the hash code

    Returns:
        Path to the output PDF

    Raises:
        PDFConversionError: If footer addition fails
    """
    if not PDF_FOOTER_AVAILABLE:
        raise PDFConversionError(
            "Las bibliotecas PyPDF2 y reportlab no estan instaladas. "
            "Instale con: pip install PyPDF2 reportlab"
        )

    if not pdf_path.exists():
        raise PDFConversionError(f"Archivo PDF no encontrado: {pdf_path}")

    if output_path is None:
        output_path = pdf_path

    try:
        # Read the original PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()

        # Process each page
        for page_num, page in enumerate(reader.pages):
            # Get page dimensions
            media_box = page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)

            # Create footer overlay for this page
            footer_overlay = create_hash_footer_overlay(
                hash_code, page_width, page_height, font_size
            )
            footer_pdf = PdfReader(footer_overlay)
            footer_page = footer_pdf.pages[0]

            # Merge footer onto original page
            page.merge_page(footer_page)
            writer.add_page(page)

        # Write to temporary file first (in case output_path == pdf_path)
        temp_output = pdf_path.parent / f"{pdf_path.stem}_temp_footer.pdf"
        with open(temp_output, "wb") as output_file:
            writer.write(output_file)

        # Move temp file to final destination
        shutil.move(str(temp_output), str(output_path))

        return output_path

    except Exception as e:
        if isinstance(e, PDFConversionError):
            raise
        raise PDFConversionError(f"Error al anadir pie de pagina al PDF: {str(e)}")


def convert_docx_to_pdf_with_hash(
    docx_path: Path,
    hash_code: str,
    output_path: Optional[Path] = None,
    method: str = "auto",
    font_size: int = 8
) -> Path:
    """
    Convert DOCX to PDF and add hash code footer
    Convertir DOCX a PDF y anadir codigo hash en el pie de pagina

    Args:
        docx_path: Path to the DOCX file
        hash_code: Hash code to add as footer
        output_path: Optional specific output path for PDF
        method: Conversion method ('auto', 'libreoffice')
        font_size: Font size for the hash code footer

    Returns:
        Path to the generated PDF file with hash footer

    Raises:
        PDFConversionError: If conversion or footer addition fails
    """
    # First convert to PDF
    pdf_path = convert_docx_to_pdf(docx_path, output_path, method)

    # Then add hash footer
    if PDF_FOOTER_AVAILABLE:
        pdf_path = add_hash_footer_to_pdf(pdf_path, hash_code, font_size=font_size)

    return pdf_path

