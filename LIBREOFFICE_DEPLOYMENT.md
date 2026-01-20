# LibreOffice Deployment Guide / Guia de Despliegue de LibreOffice

This guide provides detailed instructions for deploying LibreOffice on a server to enable PDF conversion functionality.

Este documento proporciona instrucciones detalladas para desplegar LibreOffice en un servidor y habilitar la funcionalidad de conversion a PDF.

---

## Table of Contents / Indice

1. [Overview / Descripcion General](#overview--descripcion-general)
2. [Linux Server (Ubuntu/Debian)](#linux-server-ubuntudebian)
3. [Linux Server (CentOS/RHEL/Rocky)](#linux-server-centosrhelrocky)
4. [Docker Deployment](#docker-deployment)
5. [Windows Server](#windows-server)
6. [macOS Server](#macos-server)
7. [Verification / Verificacion](#verification--verificacion)
8. [Troubleshooting / Solucion de Problemas](#troubleshooting--solucion-de-problemas)
9. [Performance Optimization](#performance-optimization)

---

## Overview / Descripcion General

This application uses LibreOffice in headless mode to convert DOCX files to PDF. LibreOffice must be installed on the server for PDF generation to work.

Esta aplicacion utiliza LibreOffice en modo headless para convertir archivos DOCX a PDF. LibreOffice debe estar instalado en el servidor para que la generacion de PDF funcione.

### Requirements / Requisitos

- LibreOffice 7.0 or higher / LibreOffice 7.0 o superior
- At least 512MB of available RAM / Al menos 512MB de RAM disponible
- At least 1GB of disk space / Al menos 1GB de espacio en disco

---

## Linux Server (Ubuntu/Debian)

### Quick Installation / Instalacion Rapida

```bash
# Update package list / Actualizar lista de paquetes
sudo apt update

# Install LibreOffice (minimal installation for server)
# Instalar LibreOffice (instalacion minima para servidor)
sudo apt install -y libreoffice-writer libreoffice-calc --no-install-recommends

# Or install the full package / O instalar el paquete completo
sudo apt install -y libreoffice
```

### Headless Mode Installation (Recommended for Servers)
### Instalacion en Modo Headless (Recomendado para Servidores)

```bash
# Install only the core components needed for conversion
# Instalar solo los componentes basicos necesarios para conversion
sudo apt install -y \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu-core

# Install additional fonts for better document rendering
# Instalar fuentes adicionales para mejor renderizado de documentos
sudo apt install -y \
    fonts-liberation2 \
    fonts-freefont-ttf \
    fonts-noto-core \
    fonts-noto-mono
```

### Verify Installation / Verificar Instalacion

```bash
# Check LibreOffice version
libreoffice --version

# Test headless conversion
libreoffice --headless --convert-to pdf --outdir /tmp /path/to/test.docx

# Verify the binary path
which libreoffice
# Should return: /usr/bin/libreoffice
```

---

## Linux Server (CentOS/RHEL/Rocky)

### Installation / Instalacion

```bash
# For CentOS/RHEL 8+ and Rocky Linux
sudo dnf install -y libreoffice-writer libreoffice-calc

# For CentOS/RHEL 7
sudo yum install -y libreoffice-writer libreoffice-calc

# Install fonts
sudo dnf install -y \
    liberation-fonts \
    dejavu-sans-fonts \
    dejavu-serif-fonts \
    dejavu-sans-mono-fonts
```

### EPEL Repository (if needed)

```bash
# Enable EPEL repository for additional packages
sudo dnf install -y epel-release
```

---

## Docker Deployment

### Option 1: Using Pre-built Image with LibreOffice
### Opcion 1: Usar Imagen Pre-construida con LibreOffice

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install LibreOffice and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-core \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create output directory
RUN mkdir -p /app/output

# Expose Streamlit port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "ui/streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Option 2: Docker Compose Configuration
### Opcion 2: Configuracion Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  carta-manifestacion:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    volumes:
      - ./output:/app/output
      - ./config:/app/config
    environment:
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "libreoffice", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: API service
  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    volumes:
      - ./output:/app/output
    depends_on:
      - carta-manifestacion
```

### Build and Run / Construir y Ejecutar

```bash
# Build the image
docker build -t carta-manifestacion .

# Run the container
docker run -d -p 8501:8501 --name carta-app carta-manifestacion

# Or with docker-compose
docker-compose up -d
```

### Minimal Dockerfile (Optimized for Size)
### Dockerfile Minimo (Optimizado para Tamano)

```dockerfile
FROM python:3.11-alpine

# Install LibreOffice (Alpine uses different packages)
RUN apk add --no-cache \
    libreoffice-writer \
    libreoffice-common \
    font-noto \
    font-noto-extra \
    ttf-dejavu \
    ttf-liberation

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "ui/streamlit_app/app.py", "--server.port=8501"]
```

---

## Windows Server

### Installation Steps / Pasos de Instalacion

1. **Download LibreOffice** / **Descargar LibreOffice**
   - Visit: https://www.libreoffice.org/download/download/
   - Download the Windows x64 installer (MSI package recommended for servers)

2. **Silent Installation** / **Instalacion Silenciosa**

   ```powershell
   # Download and install silently (PowerShell as Administrator)
   $url = "https://download.documentfoundation.org/libreoffice/stable/7.6.4/win/x86_64/LibreOffice_7.6.4_Win_x86-64.msi"
   $output = "$env:TEMP\LibreOffice.msi"
   Invoke-WebRequest -Uri $url -OutFile $output

   # Install silently
   msiexec /i $output /quiet /norestart ADDLOCAL=ALL
   ```

3. **Add to System PATH** / **Agregar al PATH del Sistema**

   ```powershell
   # Add LibreOffice to PATH
   $libreOfficePath = "C:\Program Files\LibreOffice\program"
   [Environment]::SetEnvironmentVariable(
       "Path",
       [Environment]::GetEnvironmentVariable("Path", "Machine") + ";$libreOfficePath",
       "Machine"
   )
   ```

4. **Verify Installation** / **Verificar Instalacion**

   ```powershell
   # Test the installation
   & "C:\Program Files\LibreOffice\program\soffice.exe" --version
   ```

### Windows Service Configuration (Optional)
### Configuracion de Servicio Windows (Opcional)

For production environments, consider running the application as a Windows Service using NSSM or similar tools.

---

## macOS Server

### Installation with Homebrew / Instalacion con Homebrew

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install LibreOffice
brew install --cask libreoffice

# Verify installation
/Applications/LibreOffice.app/Contents/MacOS/soffice --version
```

### Manual Installation / Instalacion Manual

1. Download from https://www.libreoffice.org/download/download/
2. Open the DMG file and drag LibreOffice to Applications
3. The binary path will be: `/Applications/LibreOffice.app/Contents/MacOS/soffice`

---

## Verification / Verificacion

### Check Application Status / Verificar Estado de la Aplicacion

The application automatically checks for LibreOffice availability. You can verify the status:

1. **Via Streamlit UI**: After login, check the sidebar for "Estado del Sistema" section
2. **Via API**: Call `GET /api/v1/status` endpoint

### Manual Test / Prueba Manual

```bash
# Create a test DOCX file and convert it
echo "Test document" > /tmp/test.txt

# Convert to PDF using LibreOffice
libreoffice --headless --convert-to pdf --outdir /tmp /tmp/test.txt

# Check if PDF was created
ls -la /tmp/test.pdf
```

### Python Verification Script / Script de Verificacion en Python

```python
from modules.pdf_converter import get_pdf_conversion_status

status = get_pdf_conversion_status()
print(f"PDF Conversion Available: {status['pdf_conversion_available']}")
print(f"LibreOffice Path: {status['libreoffice']['path']}")
print(f"Platform: {status['platform']}")
```

---

## Troubleshooting / Solucion de Problemas

### Common Issues / Problemas Comunes

#### 1. "LibreOffice not found" / "LibreOffice no encontrado"

**Solution / Solucion:**
```bash
# Check if LibreOffice is installed
which libreoffice || which soffice

# If not found, install it
sudo apt install libreoffice-writer  # Ubuntu/Debian
sudo dnf install libreoffice-writer  # CentOS/RHEL
```

#### 2. Conversion Timeout / Tiempo de Espera Agotado

**Solution / Solucion:**
```bash
# Kill any stuck LibreOffice processes
pkill -9 soffice
pkill -9 libreoffice

# Clear LibreOffice cache
rm -rf ~/.config/libreoffice/4/user/

# For system-wide installation
sudo rm -rf /tmp/.~lock.*
```

#### 3. Font Issues / Problemas de Fuentes

**Solution / Solucion:**
```bash
# Install Microsoft core fonts (Ubuntu/Debian)
sudo apt install ttf-mscorefonts-installer

# Or install Liberation fonts (open source alternative)
sudo apt install fonts-liberation fonts-liberation2

# Refresh font cache
sudo fc-cache -fv
```

#### 4. Permission Issues / Problemas de Permisos

**Solution / Solucion:**
```bash
# Ensure the application user has write access to output directory
sudo chown -R $USER:$USER /path/to/output/directory

# Set appropriate permissions
chmod 755 /path/to/output/directory
```

#### 5. Display Issues (Headless Mode) / Problemas de Display (Modo Headless)

**Solution / Solucion:**
```bash
# Install virtual display packages
sudo apt install xvfb

# Run with virtual framebuffer (if needed)
xvfb-run libreoffice --headless --convert-to pdf --outdir /tmp document.docx
```

### Log Debugging / Depuracion de Logs

```bash
# Enable LibreOffice logging
export SAL_LOG="+INFO.cui.filter"

# Check system logs for errors
journalctl -xe | grep -i libreoffice

# Check application logs
tail -f /path/to/app/logs/application.log
```

---

## Performance Optimization

### Memory Settings / Configuracion de Memoria

Create or edit `/etc/libreoffice/sofficerc`:

```
[Bootstrap]
UserInstallation=$SYSUSERCONFIG/libreoffice/4
```

### Concurrent Conversions / Conversiones Concurrentes

For high-volume environments, consider:

1. **Connection Pool**: Use a pool of LibreOffice instances
2. **Queue System**: Implement a job queue (Redis, RabbitMQ) for conversions
3. **Resource Limits**: Set memory and CPU limits per conversion

### Example: Limiting Resources with Docker

```yaml
services:
  carta-manifestacion:
    # ... other config
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Caching Recommendations / Recomendaciones de Cache

1. Cache converted PDFs to avoid redundant conversions
2. Implement file hash comparison before conversion
3. Use temporary files cleanup job

---

## Security Considerations / Consideraciones de Seguridad

1. **Run as Non-Root User**: Always run LibreOffice and the application as a non-privileged user
2. **Sandbox Conversions**: Use container isolation for document conversion
3. **Input Validation**: Validate all uploaded documents before conversion
4. **Temporary File Cleanup**: Implement automatic cleanup of temporary files

```bash
# Create a dedicated user for conversions
sudo useradd -r -s /bin/false libreoffice-converter

# Set ownership of working directories
sudo chown libreoffice-converter:libreoffice-converter /app/output
```

---

## Support / Soporte

For issues specific to this application, please check:
- Application logs in the `logs/` directory
- LibreOffice conversion logs
- System resource availability (memory, disk space)

For LibreOffice-specific issues:
- https://www.libreoffice.org/get-help/documentation/
- https://ask.libreoffice.org/

---

*Last updated: January 2026*
