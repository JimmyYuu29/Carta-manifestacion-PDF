"""
Authentication Module - User management and login verification
Modulo de Autenticacion - Gestion de usuarios y verificacion de inicio de sesion
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List


class AccountType(Enum):
    """Account type enum / Enumeracion de tipo de cuenta"""
    NORMAL = "normal"
    PRO = "pro"


@dataclass
class User:
    """User data class / Clase de datos de usuario"""
    username: str
    account_type: AccountType
    display_name: str
    email: Optional[str] = None


# Pre-defined normal accounts (only username needed, email suffix @forvismazars.es)
# Cuentas normales predefinidas (solo se necesita usuario, sufijo de correo @forvismazars.es)
NORMAL_ACCOUNTS: List[str] = [
    "juan.garcia",
    "maria.lopez",
    "carlos.martinez",
    "ana.fernandez",
    "pedro.sanchez",
    "laura.rodriguez",
    "miguel.gonzalez",
    "elena.diaz",
    "david.perez",
    "sofia.ruiz"
]

# Pre-defined Pro accounts with passwords
# Cuentas Pro predefinidas con contrasenas
PRO_ACCOUNTS: Dict[str, str] = {
    "admin": "Forvis30",
    "mariajose.arrebola@forvismazars.com": "Forvis30"
}


def hash_password(password: str) -> str:
    """
    Hash password using SHA-256
    Hashear contrasena usando SHA-256
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_normal_account(username: str) -> Optional[User]:
    """
    Verify normal account login (username only)
    Verificar inicio de sesion de cuenta normal (solo usuario)

    Args:
        username: Username or email

    Returns:
        User object if valid, None otherwise
    """
    # Remove email suffix if present
    clean_username = username.replace("@forvismazars.es", "").strip().lower()

    # Check if username exists in normal accounts
    for account in NORMAL_ACCOUNTS:
        if account.lower() == clean_username:
            return User(
                username=account,
                account_type=AccountType.NORMAL,
                display_name=account.replace(".", " ").title(),
                email=f"{account}@forvismazars.es"
            )

    return None


def verify_pro_account(username: str, password: str) -> Optional[User]:
    """
    Verify Pro account login (username and password)
    Verificar inicio de sesion de cuenta Pro (usuario y contrasena)

    Args:
        username: Username or email
        password: Password

    Returns:
        User object if valid, None otherwise
    """
    # Check if username exists in pro accounts
    for account, stored_password in PRO_ACCOUNTS.items():
        if account.lower() == username.lower():
            if password == stored_password:
                # Determine display name
                if account == "admin":
                    display_name = "Administrador"
                else:
                    # Extract name from email
                    name_part = account.split("@")[0]
                    display_name = name_part.replace(".", " ").title()

                return User(
                    username=account,
                    account_type=AccountType.PRO,
                    display_name=display_name,
                    email=account if "@" in account else None
                )

    return None


def get_all_normal_accounts() -> List[str]:
    """
    Get list of all normal account usernames with email suffix
    Obtener lista de todos los usuarios de cuentas normales con sufijo de correo
    """
    return [f"{account}@forvismazars.es" for account in NORMAL_ACCOUNTS]


def get_user_permissions(user: User) -> Dict[str, bool]:
    """
    Get user permissions based on account type
    Obtener permisos de usuario basados en tipo de cuenta

    Args:
        user: User object

    Returns:
        Dictionary of permissions
    """
    if user.account_type == AccountType.PRO:
        return {
            "can_download_pdf": True,
            "can_download_word": True,
            "can_view_hash": True,
            "can_export_metadata": True,
            "can_import_metadata": True
        }
    else:
        return {
            "can_download_pdf": True,
            "can_download_word": False,
            "can_view_hash": True,
            "can_export_metadata": True,
            "can_import_metadata": True
        }
