#!/usr/bin/env python
"""
Run FastAPI Server - Carta de Manifestacion Generator API
Ejecutar Servidor FastAPI - API del Generador de Cartas de Manifestacion
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    import uvicorn

    print("=" * 60)
    print("Generador de Cartas de Manifestacion - API Server")
    print("=" * 60)
    print()
    print("Starting FastAPI server...")
    print()
    print("API Documentation:")
    print("  - Swagger UI: http://localhost:8000/api/docs")
    print("  - ReDoc: http://localhost:8000/api/redoc")
    print()
    print("Web UI: http://localhost:8000/")
    print()
    print("=" * 60)

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT)]
    )


if __name__ == "__main__":
    main()
