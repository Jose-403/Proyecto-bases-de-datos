"""Lógica de negocio para usuarios del sistema."""

import re

from config import ROLE_LABELS, SYSTEM_USER_ROLES
import database as db

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str) -> tuple[bool, str]:
    if not email:
        return False, "El correo electrónico es obligatorio."

    if not EMAIL_PATTERN.match(email):
        return False, "El formato del correo electrónico no es válido."

    return True, ""


def create_system_user(email: str, role: str) -> tuple[bool, str, str, dict]:
    email = email.strip().lower()
    valid, message = _validate_email(email)
    form_data = {"email": email, "role": role}

    if not valid:
        return False, message, "", form_data

    if role not in SYSTEM_USER_ROLES:
        return False, "Debe seleccionar un perfil válido.", "", form_data

    if db.email_exists(email):
        return False, "El correo electrónico ya está registrado en el sistema.", "", form_data

    created, temp_password, message = db.create_system_user(email, role)
    return created, message, temp_password, form_data


def list_system_users() -> list[dict]:
    users = db.get_all_system_users()
    for user in users:
        user["role_label"] = ROLE_LABELS.get(user["role"], user["role"])
    return users


def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    confirm: str,
) -> tuple[bool, str]:
    user = db.get_user_by_id(user_id)
    if user is None:
        return False, "Usuario no encontrado."

    if not db.verify_user(user["email"], current_password):
        return False, "La contraseña actual no es correcta."

    if len(new_password) < 6:
        return False, "La nueva contraseña debe tener al menos 6 caracteres."

    if new_password != confirm:
        return False, "Las contraseñas no coinciden."

    return db.update_user_password(user_id, new_password)
