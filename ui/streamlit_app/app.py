"""
Main Streamlit Application - Carta de Manifestacion Generator
Aplicacion principal de Streamlit - Generador de Cartas de Manifestacion
With Authentication and User-based Download Options
Con Autenticacion y Opciones de Descarga basadas en Usuario
"""

import streamlit as st
from datetime import datetime, date
from pathlib import Path
import sys
import json
import io
import hashlib
import pandas as pd
from docx import Document

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.plugin_loader import load_plugin
from modules.generate import generate_from_form
from modules.context_builder import format_spanish_date, parse_date_string
from modules.auth import (
    AccountType, User, verify_normal_account, verify_pro_account,
    get_all_normal_accounts, get_user_permissions
)
from modules.file_hash import generate_file_hash, format_hash_for_display
from modules.pdf_converter import convert_docx_to_pdf, get_pdf_conversion_status, PDFConversionError

from ui.streamlit_app.state_store import (
    init_session_state,
    set_imported_data,
)
from ui.streamlit_app.form_renderer import FormRenderer


# Plugin configuration
PLUGIN_ID = "carta_manifestacion"


def create_hash_certificate(hash_info, trace_id: str, client_name: str, user_display_name: str) -> str:
    """
    Create a hash certificate in text format
    Crear un certificado de hash en formato texto

    Args:
        hash_info: FileHashInfo object
        trace_id: Document trace ID
        client_name: Client name
        user_display_name: User display name

    Returns:
        Certificate content as string
    """
    lines = [
        "=" * 60,
        "CERTIFICADO DE HASH - CARTA DE MANIFESTACION",
        "Forvis Mazars",
        "=" * 60,
        "",
        f"Codigo de Traza: {trace_id}",
        f"Codigo Hash: {hash_info.hash_code}",
        "",
        "-" * 60,
        "INFORMACION DEL DOCUMENTO",
        "-" * 60,
        f"Cliente: {client_name}",
        f"Usuario: {user_display_name}",
        f"Fecha de Creacion: {hash_info.creation_timestamp}",
        f"Tamano del Archivo: {hash_info.file_size:,} bytes",
        "",
        "-" * 60,
        "DETALLES DEL HASH",
        "-" * 60,
        f"Algoritmo: {hash_info.algorithm}",
        "",
        "Hash de Contenido (SHA-256):",
        hash_info.content_hash,
        "",
        "Hash de Metadatos (SHA-256):",
        hash_info.metadata_hash,
        "",
        "Hash Combinado (SHA-256):",
        hash_info.combined_hash,
        "",
        "-" * 60,
        "VERIFICACION",
        "-" * 60,
        "Este certificado puede utilizarse para verificar la",
        "integridad y autenticidad del documento generado.",
        "",
        "Para verificar el documento:",
        "1. Calcule el hash SHA-256 del archivo original",
        "2. Compare con el 'Hash de Contenido' indicado arriba",
        "3. Si coinciden, el documento no ha sido modificado",
        "",
        "=" * 60,
        f"Generado automaticamente el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "=" * 60,
    ]
    return "\n".join(lines)


def create_hash_json(hash_info, trace_id: str, client_name: str, user_id: str) -> str:
    """
    Create a hash certificate in JSON format
    Crear un certificado de hash en formato JSON

    Args:
        hash_info: FileHashInfo object
        trace_id: Document trace ID
        client_name: Client name
        user_id: User ID

    Returns:
        Certificate content as JSON string
    """
    certificate_data = {
        "certificate_type": "HASH_CERTIFICATE",
        "version": "1.0",
        "issuer": "Forvis Mazars - Carta de Manifestacion Generator",
        "trace_id": trace_id,
        "hash_code": hash_info.hash_code,
        "document_info": {
            "client_name": client_name,
            "user_id": user_id,
            "creation_timestamp": hash_info.creation_timestamp,
            "creation_timestamp_iso": hash_info.creation_timestamp_iso,
            "file_size_bytes": hash_info.file_size
        },
        "hash_details": {
            "algorithm": hash_info.algorithm,
            "content_hash": hash_info.content_hash,
            "metadata_hash": hash_info.metadata_hash,
            "combined_hash": hash_info.combined_hash
        },
        "verification_instructions": {
            "step_1": "Calculate SHA-256 hash of the original document file",
            "step_2": "Compare with content_hash in hash_details",
            "step_3": "If they match, the document has not been modified"
        },
        "generated_at": datetime.now().isoformat()
    }
    return json.dumps(certificate_data, indent=2, ensure_ascii=False)


def generate_form_hash(form_data: dict, user_id: str) -> dict:
    """
    Generate a hash code from form data before document generation
    Generar un codigo hash a partir de los datos del formulario antes de la generacion del documento

    Args:
        form_data: Dictionary with form data
        user_id: User identifier

    Returns:
        Dictionary with hash_code and hash details
    """
    timestamp = datetime.now()
    timestamp_iso = timestamp.isoformat()

    # Serialize form data for hashing (sort keys for consistency)
    serializable_data = {}
    for key, value in form_data.items():
        if isinstance(value, (date, datetime)):
            serializable_data[key] = value.strftime("%Y-%m-%d")
        elif isinstance(value, list):
            serializable_data[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            serializable_data[key] = str(value) if value is not None else ""

    form_json = json.dumps(serializable_data, sort_keys=True, ensure_ascii=False)
    form_hash = hashlib.sha256(form_json.encode('utf-8')).hexdigest()

    # Create metadata hash
    metadata = {
        "timestamp": timestamp_iso,
        "user_id": user_id,
        "doc_type": "CM"
    }
    metadata_json = json.dumps(metadata, sort_keys=True)
    metadata_hash = hashlib.sha256(metadata_json.encode('utf-8')).hexdigest()

    # Combined hash
    combined_string = f"{form_hash}:{metadata_hash}:{timestamp_iso}:CM"
    combined_hash = hashlib.sha256(combined_string.encode('utf-8')).hexdigest()

    # Format hash code: CM-XXXXXXXXXXXX (first 12 chars uppercase)
    hash_code = f"CM-{combined_hash[:12].upper()}"

    return {
        "hash_code": hash_code,
        "form_hash": form_hash,
        "metadata_hash": metadata_hash,
        "combined_hash": combined_hash,
        "timestamp": timestamp.strftime("%d/%m/%Y %H:%M:%S"),
        "timestamp_iso": timestamp_iso
    }


def init_auth_state():
    """Initialize authentication state / Inicializar estado de autenticacion"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'account_type' not in st.session_state:
        st.session_state.account_type = AccountType.NORMAL


def render_login_sidebar():
    """
    Render login form in sidebar
    Renderizar formulario de inicio de sesion en barra lateral
    """
    with st.sidebar:
        st.markdown("## 🔐 Inicio de Sesion")
        st.markdown("---")

        # Account type selection
        account_type_option = st.radio(
            "Tipo de Cuenta",
            options=["Cuenta Normal", "Cuenta Pro"],
            key="account_type_radio",
            help="Seleccione el tipo de cuenta para iniciar sesion"
        )

        st.session_state.account_type = (
            AccountType.NORMAL if account_type_option == "Cuenta Normal"
            else AccountType.PRO
        )

        st.markdown("---")

        if st.session_state.account_type == AccountType.NORMAL:
            # Normal account - username only
            st.markdown("### Cuenta Normal")
            st.info("Solo se requiere el usuario (correo electronico @forvismazars.es)")

            # Show available accounts as hint
            with st.expander("Ver cuentas disponibles"):
                for account in get_all_normal_accounts():
                    st.text(account)

            username = st.text_input(
                "Usuario (correo electronico)",
                placeholder="ejemplo: juan.garcia@forvismazars.es",
                key="normal_username"
            )

            if st.button("Iniciar Sesion", key="normal_login_btn", type="primary"):
                if username:
                    user = verify_normal_account(username)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"Bienvenido/a, {user.display_name}!")
                        st.rerun()
                    else:
                        st.error("Usuario no encontrado. Verifique el correo electronico.")
                else:
                    st.warning("Por favor ingrese su usuario.")

        else:
            # Pro account - username and password
            st.markdown("### Cuenta Pro")
            st.info("Se requiere usuario y contrasena")

            username = st.text_input(
                "Usuario",
                placeholder="admin o correo@forvismazars.com",
                key="pro_username"
            )

            password = st.text_input(
                "Contrasena",
                type="password",
                key="pro_password"
            )

            if st.button("Iniciar Sesion", key="pro_login_btn", type="primary"):
                if username and password:
                    user = verify_pro_account(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"Bienvenido/a, {user.display_name}!")
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas.")
                else:
                    st.warning("Por favor ingrese usuario y contrasena.")

        # Show current account type features
        st.markdown("---")
        st.markdown("### Caracteristicas")

        if st.session_state.account_type == AccountType.NORMAL:
            st.markdown("""
            **Cuenta Normal:**
            - Descarga en formato PDF
            - Codigo hash de verificacion
            - Exportar/Importar metadatos
            """)
        else:
            st.markdown("""
            **Cuenta Pro:**
            - Descarga en formato PDF
            - Descarga en formato Word
            - Codigo hash de verificacion
            - Exportar/Importar metadatos
            - Acceso completo
            """)


def render_user_info_sidebar():
    """
    Render user info and logout in sidebar when authenticated
    Renderizar info de usuario y cierre de sesion en barra lateral cuando autenticado
    """
    user = st.session_state.user

    with st.sidebar:
        st.markdown("## 👤 Usuario")
        st.markdown("---")

        # User info
        st.markdown(f"**Nombre:** {user.display_name}")
        st.markdown(f"**Tipo:** {'Pro' if user.account_type == AccountType.PRO else 'Normal'}")
        if user.email:
            st.markdown(f"**Email:** {user.email}")

        # Permissions
        permissions = get_user_permissions(user)
        st.markdown("---")
        st.markdown("### Permisos")

        perm_labels = {
            "can_download_pdf": "Descargar PDF",
            "can_download_word": "Descargar Word",
            "can_view_hash": "Ver Hash",
            "can_export_metadata": "Exportar Metadatos",
            "can_import_metadata": "Importar Metadatos"
        }

        for perm_key, perm_label in perm_labels.items():
            status = "✅" if permissions.get(perm_key, False) else "❌"
            st.markdown(f"{status} {perm_label}")

        # PDF conversion status
        st.markdown("---")
        st.markdown("### Estado del Sistema")
        pdf_status = get_pdf_conversion_status()
        if pdf_status["pdf_conversion_available"]:
            st.success("✅ Conversion PDF disponible")
        else:
            st.warning("⚠️ Conversion PDF no disponible (LibreOffice no instalado)")

        # Hash validator link
        st.markdown("---")
        st.markdown("### Herramientas")
        st.markdown("[🔍 Validador de Hash](http://10.32.1.150:9000/)")

        # Logout button
        st.markdown("---")
        if st.button("🚪 Cerrar Sesion", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()


def process_uploaded_file(uploaded_file, file_type: str) -> dict:
    """
    Process uploaded Excel or Word file
    Procesar archivo Excel o Word cargado
    """
    extracted_data = {}

    try:
        if file_type == "excel":
            df = pd.read_excel(uploaded_file, header=None)

            if df.shape[1] >= 2:
                for index, row in df.iterrows():
                    if pd.notna(row[0]) and pd.notna(row[1]):
                        var_name = str(row[0]).strip()
                        var_value = row[1]

                        if pd.api.types.is_datetime64_any_dtype(type(var_value)) or isinstance(var_value, datetime):
                            var_value = var_value.strftime("%d/%m/%Y")
                        else:
                            var_value = str(var_value).strip()

                        # Normalize boolean values
                        if var_value.upper() in ['SI', 'SÍ'] or var_value == '1':
                            var_value = True
                        elif var_value.upper() == 'NO' or var_value == '0':
                            var_value = False

                        extracted_data[var_name] = var_value

        elif file_type == "word":
            doc = Document(uploaded_file)

            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text and ':' in text:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        var_value = parts[1].strip()

                        if var_value.upper() in ['SI', 'SÍ'] or var_value == '1':
                            var_value = True
                        elif var_value.upper() == 'NO' or var_value == '0':
                            var_value = False

                        extracted_data[var_name] = var_value

    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        return {}

    return extracted_data


def process_json_file(uploaded_file) -> dict:
    """
    Process uploaded JSON file
    Procesar archivo JSON cargado
    """
    try:
        content = uploaded_file.read().decode('utf-8')
        data = json.loads(content)

        # Normalize boolean values
        for key, value in data.items():
            if isinstance(value, str):
                if value.upper() in ['SI', 'SÍ', 'TRUE', 'YES']:
                    data[key] = True
                elif value.upper() in ['NO', 'FALSE']:
                    data[key] = False

        return data
    except Exception as e:
        st.error(f"Error al procesar el archivo JSON: {str(e)}")
        return {}


def serialize_for_export(data: dict) -> dict:
    """
    Serialize data for JSON/Excel export, converting date objects to strings
    Serializar datos para exportacion JSON/Excel, convirtiendo fechas a strings
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.strftime("%d/%m/%Y")
        elif isinstance(value, list):
            # Handle list of dicts (like directors)
            result[key] = value
        else:
            result[key] = value
    return result


def export_to_json(data: dict) -> str:
    """Export data to JSON string"""
    serialized = serialize_for_export(data)
    return json.dumps(serialized, indent=2, ensure_ascii=False)


def export_to_excel(data: dict) -> bytes:
    """Export data to Excel bytes"""
    serialized = serialize_for_export(data)

    # Flatten the data for Excel
    rows = []
    for key, value in serialized.items():
        if isinstance(value, list):
            # For lists like directors, create a JSON string representation
            rows.append({"Variable": key, "Valor": json.dumps(value, ensure_ascii=False)})
        elif isinstance(value, bool):
            rows.append({"Variable": key, "Valor": "SI" if value else "NO"})
        else:
            rows.append({"Variable": key, "Valor": str(value) if value else ""})

    df = pd.DataFrame(rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Metadatos')
    output.seek(0)

    return output.getvalue()


def render_main_form():
    """
    Render main form for data entry (only when authenticated)
    Renderizar formulario principal para entrada de datos (solo cuando autenticado)
    """
    user = st.session_state.user
    permissions = get_user_permissions(user)

    # Initialize session state
    init_session_state(PLUGIN_ID)

    # Load plugin
    try:
        plugin = load_plugin(PLUGIN_ID)
    except Exception as e:
        st.error(f"Error loading plugin: {e}")
        return

    # Create form renderer
    form_renderer = FormRenderer(plugin)

    # Main title / Titulo principal
    st.title("🏢 Generador de Cartas de Manifestacion - Forvis Mazars")
    st.markdown("---")

    # Get template path
    template_path = PROJECT_ROOT / "Modelo de plantilla.docx"
    if not template_path.exists():
        # Try config path
        template_path = plugin.get_template_path()

    if not template_path.exists():
        st.error(f"⚠️ No se encontro el archivo de plantilla")
        st.info("Por favor, asegurate de que el archivo de plantilla este en la carpeta correcta.")
        return

    # Template analysis message
    st.success(f"✅ Plantilla analizada correctamente.")

    # Form subtitle / Subtitulo del formulario
    st.subheader("📝 Informacion de la Carta")

    # Import section / Seccion de importacion
    st.markdown("---")
    st.subheader("📁 Importar Metadatos")

    col_import1, col_import2, col_import3 = st.columns(3)

    with col_import1:
        uploaded_json = st.file_uploader(
            "Cargar archivo JSON (.json)",
            type=['json'],
            help="Archivo JSON con metadatos exportados previamente",
            key="json_upload"
        )

    with col_import2:
        uploaded_excel = st.file_uploader(
            "Cargar archivo Excel (.xlsx, .xls)",
            type=['xlsx', 'xls'],
            help="Formato: Columna 1 = Nombre variable, Columna 2 = Valor",
            key="excel_upload"
        )

    with col_import3:
        uploaded_word = st.file_uploader(
            "Cargar archivo Word (.docx)",
            type=['docx'],
            help="Formato: nombre_variable: valor (una por linea)",
            key="word_upload"
        )

    # Process uploaded files
    imported_data = {}

    if uploaded_json is not None:
        with st.spinner("Procesando archivo JSON..."):
            imported_data = process_json_file(uploaded_json)
            if imported_data:
                set_imported_data(imported_data)
                st.success(f"✅ Se importaron {len(imported_data)} valores desde JSON")

    elif uploaded_excel is not None:
        with st.spinner("Procesando archivo Excel..."):
            imported_data = process_uploaded_file(uploaded_excel, "excel")
            if imported_data:
                set_imported_data(imported_data)
                st.success(f"✅ Se importaron {len(imported_data)} valores desde Excel")

    elif uploaded_word is not None:
        with st.spinner("Procesando archivo Word..."):
            imported_data = process_uploaded_file(uploaded_word, "word")
            if imported_data:
                set_imported_data(imported_data)
                st.success(f"✅ Se importaron {len(imported_data)} valores desde Word")

    st.markdown("---")

    # Form sections in columns / Secciones del formulario en columnas
    col1, col2 = st.columns(2)

    # Get current form data
    var_values = dict(st.session_state.form_data)
    cond_values = {}

    with col1:
        # Office section / Seccion de oficina
        st.markdown("### 📋 Informacion de la Oficina")
        var_values = form_renderer.render_oficina_section(var_values)

        # Client section / Seccion de cliente
        st.markdown("### 🏢 Nombre de cliente")
        var_values['Nombre_Cliente'] = st.text_input(
            "Nombre del Cliente",
            value=var_values.get('Nombre_Cliente', ''),
            key="nombre_cliente"
        )

        # Dates section / Seccion de fechas
        st.markdown("### 📅 Fechas")

        # Store dates as date objects for validation, formatting happens in context_builder
        fecha_hoy = parse_date_string(var_values.get('Fecha_de_hoy', ''))
        if not fecha_hoy:
            fecha_hoy = datetime.now().date()
        var_values['Fecha_de_hoy'] = st.date_input("Fecha de Hoy", value=fecha_hoy, key="fecha_hoy")

        fecha_encargo = parse_date_string(var_values.get('Fecha_encargo', ''))
        if not fecha_encargo:
            fecha_encargo = datetime.now().date()
        var_values['Fecha_encargo'] = st.date_input("Fecha del Encargo", value=fecha_encargo, key="fecha_encargo")

        fecha_ff = parse_date_string(var_values.get('FF_Ejecicio', ''))
        if not fecha_ff:
            fecha_ff = datetime.now().date()
        var_values['FF_Ejecicio'] = st.date_input("Fecha Fin del Ejercicio", value=fecha_ff, key="ff_ejercicio")

        fecha_cierre = parse_date_string(var_values.get('Fecha_cierre', ''))
        if not fecha_cierre:
            fecha_cierre = datetime.now().date()
        var_values['Fecha_cierre'] = st.date_input("Fecha de Cierre", value=fecha_cierre, key="fecha_cierre")

        # General info section / Seccion de informacion general
        st.markdown("### 📝 Informacion General")
        var_values['Lista_Abogados'] = st.text_area(
            "Lista de abogados y asesores fiscales",
            value=var_values.get('Lista_Abogados', ''),
            placeholder="Ej: Despacho ABC - Asesoria fiscal\nDespacho XYZ - Asesoria legal",
            key="abogados"
        )
        var_values['anexo_partes'] = st.text_input(
            "Numero anexo partes vinculadas",
            value=var_values.get('anexo_partes', '2'),
            key="anexo_partes"
        )
        var_values['anexo_proyecciones'] = st.text_input(
            "Numero anexo proyecciones",
            value=var_values.get('anexo_proyecciones', '3'),
            key="anexo_proyecciones"
        )

    with col2:
        # Administration organ section / Seccion organo de administracion
        st.markdown("### 👥 Organo de Administracion")
        organo_options = ['consejo', 'administrador_unico', 'administradores']
        organo_labels = {
            'consejo': 'Consejo de Administracion',
            'administrador_unico': 'Administrador Unico',
            'administradores': 'Administradores'
        }
        organo_default = var_values.get('organo', 'consejo')
        if organo_default not in organo_options:
            organo_default = 'consejo'

        cond_values['organo'] = st.selectbox(
            "Tipo de Organo de Administracion",
            options=organo_options,
            index=organo_options.index(organo_default),
            format_func=lambda x: organo_labels.get(x, x),
            key="organo"
        )

        # Conditional options section / Seccion opciones condicionales
        st.markdown("### ✅ Opciones Condicionales")

        cond_values['comision'] = 'si' if st.checkbox(
            "Existe Comision de Auditoria?",
            value=var_values.get('comision', False) if isinstance(var_values.get('comision'), bool) else var_values.get('comision') == 'si',
            key="comision"
        ) else 'no'

        cond_values['junta'] = 'si' if st.checkbox(
            "Incluir Junta de Accionistas?",
            value=var_values.get('junta', False) if isinstance(var_values.get('junta'), bool) else var_values.get('junta') == 'si',
            key="junta"
        ) else 'no'

        cond_values['comite'] = 'si' if st.checkbox(
            "Incluir Comite?",
            value=var_values.get('comite', False) if isinstance(var_values.get('comite'), bool) else var_values.get('comite') == 'si',
            key="comite"
        ) else 'no'

        cond_values['incorreccion'] = 'si' if st.checkbox(
            "Hay incorrecciones no corregidas?",
            value=var_values.get('incorreccion', False) if isinstance(var_values.get('incorreccion'), bool) else var_values.get('incorreccion') == 'si',
            key="incorreccion"
        ) else 'no'

        if cond_values['incorreccion'] == 'si':
            with st.container():
                st.markdown("##### 📌 Detalles de incorrecciones")
                var_values['Anio_incorreccion'] = st.text_input(
                    "Ano de la incorreccion",
                    value=var_values.get('Anio_incorreccion', ''),
                    key="anio_inc"
                )
                var_values['Epigrafe'] = st.text_input(
                    "Epigrafe afectado",
                    value=var_values.get('Epigrafe', ''),
                    key="epigrafe"
                )
                cond_values['limitacion_alcance'] = 'si' if st.checkbox(
                    "Hay limitacion al alcance?",
                    value=var_values.get('limitacion_alcance', False) if isinstance(var_values.get('limitacion_alcance'), bool) else var_values.get('limitacion_alcance') == 'si',
                    key="limitacion"
                ) else 'no'
                if cond_values['limitacion_alcance'] == 'si':
                    var_values['detalle_limitacion'] = st.text_area(
                        "Detalle de la limitacion",
                        value=var_values.get('detalle_limitacion', ''),
                        key="det_limitacion"
                    )

        cond_values['dudas'] = 'si' if st.checkbox(
            "Existen dudas sobre empresa en funcionamiento?",
            value=var_values.get('dudas', False) if isinstance(var_values.get('dudas'), bool) else var_values.get('dudas') == 'si',
            key="dudas"
        ) else 'no'

        cond_values['rent'] = 'si' if st.checkbox(
            "Incluir parrafo sobre arrendamientos?",
            value=var_values.get('rent', False) if isinstance(var_values.get('rent'), bool) else var_values.get('rent') == 'si',
            key="rent"
        ) else 'no'

        cond_values['A_coste'] = 'si' if st.checkbox(
            "Hay activos valorados a coste en vez de valor razonable?",
            value=var_values.get('A_coste', False) if isinstance(var_values.get('A_coste'), bool) else var_values.get('A_coste') == 'si',
            key="a_coste"
        ) else 'no'

        cond_values['experto'] = 'si' if st.checkbox(
            "Se utilizo un experto independiente?",
            value=var_values.get('experto', False) if isinstance(var_values.get('experto'), bool) else var_values.get('experto') == 'si',
            key="experto"
        ) else 'no'

        if cond_values['experto'] == 'si':
            with st.container():
                st.markdown("##### 📌 Informacion del experto")
                var_values['nombre_experto'] = st.text_input(
                    "Nombre del experto",
                    value=var_values.get('nombre_experto', ''),
                    key="experto_nombre"
                )
                var_values['experto_valoracion'] = st.text_input(
                    "Elemento valorado por experto",
                    value=var_values.get('experto_valoracion', ''),
                    key="experto_val"
                )

        cond_values['unidad_decision'] = 'si' if st.checkbox(
            "Bajo la misma unidad de decision?",
            value=var_values.get('unidad_decision', False) if isinstance(var_values.get('unidad_decision'), bool) else var_values.get('unidad_decision') == 'si',
            key="unidad_decision"
        ) else 'no'

        if cond_values['unidad_decision'] == 'si':
            with st.container():
                st.markdown("##### 📌 Informacion de la unidad de decision")
                var_values['nombre_unidad'] = st.text_input(
                    "Nombre de la unidad",
                    value=var_values.get('nombre_unidad', ''),
                    key="nombre_unidad"
                )
                var_values['nombre_mayor_sociedad'] = st.text_input(
                    "Nombre de la mayor sociedad",
                    value=var_values.get('nombre_mayor_sociedad', ''),
                    key="nombre_mayor_sociedad"
                )
                var_values['localizacion_mer'] = st.text_input(
                    "Localizacion o domiciliacion mercantil",
                    value=var_values.get('localizacion_mer', ''),
                    key="localizacion_mer"
                )

        cond_values['activo_impuesto'] = 'si' if st.checkbox(
            "Hay activos por impuestos diferidos?",
            value=var_values.get('activo_impuesto', False) if isinstance(var_values.get('activo_impuesto'), bool) else var_values.get('activo_impuesto') == 'si',
            key="activo_impuesto"
        ) else 'no'

        if cond_values['activo_impuesto'] == 'si':
            with st.container():
                st.markdown("##### 📌 Recuperacion de activos")
                var_values['ejercicio_recuperacion_inicio'] = st.text_input(
                    "Ejercicio inicio recuperacion",
                    value=var_values.get('ejercicio_recuperacion_inicio', ''),
                    key="rec_inicio"
                )
                var_values['ejercicio_recuperacion_fin'] = st.text_input(
                    "Ejercicio fin recuperacion",
                    value=var_values.get('ejercicio_recuperacion_fin', ''),
                    key="rec_fin"
                )

        cond_values['operacion_fiscal'] = 'si' if st.checkbox(
            "Operaciones en paraisos fiscales?",
            value=var_values.get('operacion_fiscal', False) if isinstance(var_values.get('operacion_fiscal'), bool) else var_values.get('operacion_fiscal') == 'si',
            key="operacion_fiscal"
        ) else 'no'

        if cond_values['operacion_fiscal'] == 'si':
            with st.container():
                st.markdown("##### 📌 Detalle operaciones")
                var_values['detalle_operacion_fiscal'] = st.text_area(
                    "Detalle operaciones paraisos fiscales",
                    value=var_values.get('detalle_operacion_fiscal', ''),
                    key="det_fiscal"
                )

        cond_values['compromiso'] = 'si' if st.checkbox(
            "Compromisos por pensiones?",
            value=var_values.get('compromiso', False) if isinstance(var_values.get('compromiso'), bool) else var_values.get('compromiso') == 'si',
            key="compromiso"
        ) else 'no'

        cond_values['gestion'] = 'si' if st.checkbox(
            "Incluir informe de gestion?",
            value=var_values.get('gestion', False) if isinstance(var_values.get('gestion'), bool) else var_values.get('gestion') == 'si',
            key="gestion"
        ) else 'no'

    # Directors section / Seccion alta direccion
    st.markdown("---")
    st.markdown("### 👔 Alta Direccion")

    st.info("Introduce los nombres y cargos de los altos directivos. Estos reemplazaran completamente el ejemplo en la plantilla.")

    num_directivos = st.number_input(
        "Numero de altos directivos",
        min_value=0,
        max_value=10,
        value=2,
        key="num_directivos"
    )

    # Store directors as list of dicts for validation, formatting happens in context_builder
    directivos_list = []
    directivos_display = []
    indent = "                                  "

    for i in range(num_directivos):
        col_nombre, col_cargo = st.columns(2)
        with col_nombre:
            nombre = st.text_input(f"Nombre completo {i+1}", key=f"dir_nombre_{i}")
        with col_cargo:
            cargo = st.text_input(f"Cargo {i+1}", key=f"dir_cargo_{i}")
        if nombre and cargo:
            directivos_list.append({"nombre": nombre, "cargo": cargo})
            directivos_display.append(f"{indent} D. {nombre} - {cargo}")

    var_values['lista_alto_directores'] = directivos_list

    # Signature section / Seccion persona de firma
    st.markdown("---")
    st.markdown("### 👥 Persona de firma")

    var_values['Nombre_Firma'] = st.text_input(
        "Nombre del firmante",
        value=var_values.get('Nombre_Firma', ''),
        key="nombre_firma"
    )
    var_values['Cargo_Firma'] = st.text_input(
        "Cargo del firmante",
        value=var_values.get('Cargo_Firma', ''),
        key="cargo_firma"
    )

    # Preview directors list
    if directivos_display:
        st.markdown("#### Vista previa de la lista de directivos:")
        st.code("\n".join(directivos_display))

    # Update session state
    st.session_state.form_data = {**var_values, **cond_values}

    # Automatic review section / Seccion de revision automatica
    st.markdown("---")
    st.header("🔍 Revision automatica")

    # Required fields validation
    required_fields = ['Nombre_Cliente', 'Direccion_Oficina', 'CP', 'Ciudad_Oficina']
    missing_fields = [f for f in required_fields if not var_values.get(f)]

    # Show import summary if data was imported
    if imported_data:
        st.info(f"📊 Datos importados: {len(imported_data)} valores")

    # Inform user about validation status
    if not missing_fields:
        st.success("✅ Todas las variables y condiciones estan completas.")
    else:
        st.warning(f"⚠️ Faltan {len(missing_fields)} campos obligatorios: {', '.join(missing_fields)}")

    # Export metadata section / Seccion exportar metadatos
    st.markdown("---")
    st.subheader("💾 Exportar Metadatos")
    st.info("Exporta los datos del formulario para usarlos posteriormente o compartirlos.")

    # Combine all current data for export
    all_current_data = {**var_values, **cond_values}

    col_export1, col_export2 = st.columns(2)

    with col_export1:
        # Export to JSON
        json_data = export_to_json(all_current_data)
        client_name_safe = var_values.get('Nombre_Cliente', 'documento').replace(' ', '_').replace('/', '_')
        json_filename = f"metadatos_{client_name_safe}_{datetime.now().strftime('%Y%m%d')}.json"

        st.download_button(
            label="📄 Exportar a JSON",
            data=json_data,
            file_name=json_filename,
            mime="application/json",
            help="Descarga los metadatos en formato JSON para importarlos posteriormente"
        )

    with col_export2:
        # Export to Excel
        excel_data = export_to_excel(all_current_data)
        excel_filename = f"metadatos_{client_name_safe}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        st.download_button(
            label="📊 Exportar a Excel",
            data=excel_data,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Descarga los metadatos en formato Excel"
        )

    # Initialize confirmation state
    if 'data_confirmed' not in st.session_state:
        st.session_state.data_confirmed = False
    if 'confirmed_hash_info' not in st.session_state:
        st.session_state.confirmed_hash_info = None
    if 'confirmed_form_data' not in st.session_state:
        st.session_state.confirmed_form_data = None

    # Step 1: Confirm data button / Paso 1: Boton confirmar datos
    st.markdown("---")
    st.subheader("Paso 1: Confirmar los Datos")

    if st.button("✅ Confirmar los Datos", type="primary", key="confirm_data_btn"):
        if missing_fields:
            st.error(f"⚠️ Por favor completa los siguientes campos obligatorios: {', '.join(missing_fields)}")
            st.session_state.data_confirmed = False
        else:
            with st.spinner("Validando y generando hash..."):
                # Combine all data
                all_data = {**var_values, **cond_values}

                # Generate hash from form data
                hash_info = generate_form_hash(all_data, user.username)

                # Store in session state
                st.session_state.data_confirmed = True
                st.session_state.confirmed_hash_info = hash_info
                st.session_state.confirmed_form_data = all_data

                st.success("✅ Datos confirmados correctamente!")

    # Display hash info if data is confirmed
    if st.session_state.data_confirmed and st.session_state.confirmed_hash_info:
        hash_info = st.session_state.confirmed_hash_info

        st.markdown("### 🔖 Hash de Verificacion Generado")

        col_hash_display, col_hash_details = st.columns([1, 1])

        with col_hash_display:
            st.markdown("**Codigo Hash:**")
            st.code(hash_info["hash_code"], language=None)
            st.caption("Este codigo se insertara en el documento generado.")

        with col_hash_details:
            st.markdown("**Fecha/Hora de Confirmacion:**")
            st.code(hash_info["timestamp"], language=None)

        with st.expander("Ver detalles completos del hash"):
            st.markdown("**Hash de formulario:**")
            st.code(hash_info["form_hash"], language=None)
            st.markdown("**Hash de metadatos:**")
            st.code(hash_info["metadata_hash"], language=None)
            st.markdown("**Hash combinado:**")
            st.code(hash_info["combined_hash"], language=None)

        # Button to reset and modify data
        if st.button("🔄 Modificar Datos", key="reset_confirmation_btn"):
            st.session_state.data_confirmed = False
            st.session_state.confirmed_hash_info = None
            st.session_state.confirmed_form_data = None
            st.rerun()

        # Step 2: Generate document button / Paso 2: Boton generar documento
        st.markdown("---")
        st.subheader("Paso 2: Generar Carta de Manifestacion")

        if st.button("🚀 Generar Carta de Manifestacion", type="primary", key="generate_doc_btn"):
            with st.spinner("Generando carta..."):
                try:
                    # Use confirmed form data with hash included
                    all_data = dict(st.session_state.confirmed_form_data)
                    all_data['hash'] = hash_info["hash_code"]

                    # Generate document
                    result = generate_from_form(
                        plugin_id=PLUGIN_ID,
                        form_data=all_data,
                        list_data={},
                        output_dir=PROJECT_ROOT / "output",
                        template_path=template_path
                    )

                    if result.success and result.output_path:
                        st.success("✅ Carta generada exitosamente!")

                        # Generate file hash for the generated document
                        creation_time = datetime.now()
                        file_hash_info = generate_file_hash(
                            file_path=result.output_path,
                            creation_time=creation_time,
                            user_id=user.username,
                            client_name=var_values.get('Nombre_Cliente', '')
                        )

                        # Display trace code and hash
                        st.markdown("### 🔖 Codigo de Traza")

                        st.markdown("**Codigo de Traza:**")
                        st.code(result.trace_id, language=None)
                        st.caption("Este codigo identifica de forma unica este documento generado.")

                        # Display generation info
                        st.info(f"⏱️ Tiempo de generacion: {result.duration_ms}ms | Usuario: {user.display_name}")

                        # Read generated file
                        with open(result.output_path, 'rb') as f:
                            doc_bytes = f.read()

                        base_filename = f"Carta_Manifestacion_{var_values['Nombre_Cliente'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}_{hash_info['hash_code'][:8]}"

                        # Download section
                        st.markdown("### 📥 Descargar Documento")

                        download_cols = st.columns(3 if permissions["can_download_word"] else 2)

                        # PDF download (available for all users)
                        with download_cols[0]:
                            st.markdown("**Formato PDF (Impresion)**")

                            pdf_status = get_pdf_conversion_status()
                            if pdf_status["pdf_conversion_available"]:
                                try:
                                    # Convert to PDF using LibreOffice (exact rendering of Word)
                                    pdf_path = convert_docx_to_pdf(result.output_path)
                                    with open(pdf_path, 'rb') as f:
                                        pdf_bytes = f.read()

                                    st.download_button(
                                        label="📄 Descargar PDF",
                                        data=pdf_bytes,
                                        file_name=f"{base_filename}.pdf",
                                        mime="application/pdf",
                                        key="download_pdf"
                                    )
                                except PDFConversionError as e:
                                    st.error(f"Error al convertir a PDF: {str(e)}")
                                    st.info("Puede descargar el archivo Word en su lugar.")
                            else:
                                st.warning("⚠️ Conversion a PDF no disponible. LibreOffice no esta instalado.")
                                st.info("Contacte al administrador para habilitar la descarga en PDF.")

                        # Word download (only for Pro users)
                        if permissions["can_download_word"]:
                            with download_cols[1]:
                                st.markdown("**Formato Word (Editable)**")
                                st.download_button(
                                    label="📝 Descargar Word",
                                    data=doc_bytes,
                                    file_name=f"{base_filename}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key="download_word"
                                )
                            hash_col_index = 2
                        else:
                            st.info("💡 Los usuarios Pro pueden descargar tambien en formato Word editable.")
                            hash_col_index = 1

                        # Hash certificate download
                        with download_cols[hash_col_index]:
                            st.markdown("**Certificado de Hash**")

                            # Create hash certificate content using confirmed hash
                            class HashInfoWrapper:
                                def __init__(self, hash_dict, file_hash):
                                    self.hash_code = hash_dict["hash_code"]
                                    self.content_hash = file_hash.content_hash
                                    self.metadata_hash = hash_dict["metadata_hash"]
                                    self.combined_hash = hash_dict["combined_hash"]
                                    self.creation_timestamp = hash_dict["timestamp"]
                                    self.creation_timestamp_iso = hash_dict["timestamp_iso"]
                                    self.file_size = file_hash.file_size
                                    self.algorithm = "SHA-256"

                            wrapped_hash = HashInfoWrapper(hash_info, file_hash_info)

                            hash_certificate = create_hash_certificate(
                                hash_info=wrapped_hash,
                                trace_id=result.trace_id,
                                client_name=var_values.get('Nombre_Cliente', ''),
                                user_display_name=user.display_name
                            )

                            st.download_button(
                                label="📋 Descargar Hash (TXT)",
                                data=hash_certificate,
                                file_name=f"hash_certificado_{hash_info['hash_code']}.txt",
                                mime="text/plain",
                                key="download_hash_txt",
                                help="Descargar certificado de hash en formato texto plano"
                            )

                            hash_json = create_hash_json(
                                hash_info=wrapped_hash,
                                trace_id=result.trace_id,
                                client_name=var_values.get('Nombre_Cliente', ''),
                                user_id=user.username
                            )
                            st.download_button(
                                label="📄 Descargar Hash (JSON)",
                                data=hash_json,
                                file_name=f"hash_certificado_{hash_info['hash_code']}.json",
                                mime="application/json",
                                key="download_hash_json",
                                help="Descargar certificado de hash en formato JSON"
                            )

                        # Reset confirmation after successful generation
                        st.markdown("---")
                        if st.button("🔄 Generar Nueva Carta", key="new_generation_btn"):
                            st.session_state.data_confirmed = False
                            st.session_state.confirmed_hash_info = None
                            st.session_state.confirmed_form_data = None
                            st.rerun()

                    else:
                        st.error(f"❌ Error al generar la carta: {result.error}")
                        if result.validation_errors:
                            st.markdown("### Errores de validacion:")
                            for err in result.validation_errors:
                                st.warning(err)
                        # Also show trace code for failed generations
                        st.caption(f"Codigo de traza: {result.trace_id}")

                except Exception as e:
                    st.error(f"❌ Error al generar la carta: {str(e)}")
                    st.exception(e)


def main():
    """Main application entry point / Punto de entrada principal"""

    # Page configuration / Configuracion de pagina
    st.set_page_config(
        page_title="Generador de Cartas de Manifestacion",
        page_icon="📄",
        layout="wide"
    )

    # Initialize authentication state
    init_auth_state()

    # Check if user is authenticated
    if not st.session_state.authenticated:
        # Show login form
        render_login_sidebar()

        # Show welcome message in main area
        st.title("🏢 Generador de Cartas de Manifestacion")
        st.markdown("### Forvis Mazars")
        st.markdown("---")

        st.info("👈 Por favor, inicie sesion en la barra lateral para acceder al generador de documentos.")

        st.markdown("""
        ### Bienvenido al Sistema de Generacion de Cartas de Manifestacion

        Este sistema permite generar cartas de manifestacion de forma automatizada
        utilizando plantillas predefinidas.

        **Tipos de cuenta:**

        | Caracteristica | Cuenta Normal | Cuenta Pro |
        |---------------|---------------|------------|
        | Descarga PDF | ✅ | ✅ |
        | Descarga Word | ❌ | ✅ |
        | Hash de verificacion | ✅ | ✅ |
        | Importar/Exportar datos | ✅ | ✅ |

        Para comenzar, seleccione su tipo de cuenta e inicie sesion.
        """)

    else:
        # Show user info in sidebar
        render_user_info_sidebar()

        # Show main form
        render_main_form()


if __name__ == "__main__":
    main()
