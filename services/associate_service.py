"""Lógica de negocio para el registro de asociados de la cooperativa."""

from config import (
    ASSOCIATE_REQUIRED_FIELDS,
    ESTADOS_VINCULACION,
    TIPOS_ASOCIADO,
)
import database as db


def _enrich_associate(associate: dict) -> dict:
    associate["tipo_label"] = TIPOS_ASOCIADO.get(
        associate["tipo_asociado"],
        associate["tipo_asociado"],
    )
    associate["estado_label"] = ESTADOS_VINCULACION.get(
        associate.get("estado_vinculacion", "activo"),
        associate.get("estado_vinculacion", "activo"),
    )
    return associate


def _normalize_form_data(form_data: dict) -> dict:
    return {
        "cedula": form_data.get("cedula", "").strip(),
        "nombre": form_data.get("nombre", "").strip(),
        "apellido": form_data.get("apellido", "").strip(),
        "tipo_asociado": form_data.get("tipo_asociado", "").strip().lower(),
        "direccion": form_data.get("direccion", "").strip(),
        "telefono": form_data.get("telefono", "").strip(),
        "email": form_data.get("email", "").strip(),
        "fecha_afiliacion": form_data.get("fecha_afiliacion", "").strip(),
    }


def validate_associate_data(data: dict) -> tuple[bool, str]:
    missing = [
        field
        for field in ASSOCIATE_REQUIRED_FIELDS
        if not data.get(field)
    ]

    if missing:
        return False, "Debe completar todos los campos obligatorios del asociado."

    if data["tipo_asociado"] not in TIPOS_ASOCIADO:
        return False, "Debe seleccionar un tipo de asociado válido (fundador o regular)."

    if db.associate_cedula_exists(data["cedula"]):
        return False, "Ya existe un asociado registrado con ese número de cédula."

    return True, ""


def register_associate(form_data: dict) -> tuple[bool, str, dict]:
    data = _normalize_form_data(form_data)
    valid, message = validate_associate_data(data)

    if not valid:
        return False, message, data

    created, message = db.create_associate(data)
    return created, message, data


def search_associate(cedula: str) -> dict | None:
    cedula = cedula.strip()
    if not cedula:
        return None

    associate = db.get_associate_by_cedula(cedula)
    if associate is None:
        return None

    return _enrich_associate(associate)


def change_vinculation_status(
    cedula: str,
    nuevo_estado: str,
    usuario: str,
) -> tuple[bool, str]:
    cedula = cedula.strip()
    nuevo_estado = nuevo_estado.strip().lower()

    if not cedula:
        return False, "Debe indicar la cédula del asociado."

    if not nuevo_estado:
        return False, "Debe seleccionar un estado de vinculación."

    if nuevo_estado not in ESTADOS_VINCULACION:
        return False, "El estado de vinculación seleccionado no es válido."

    return db.update_associate_vinculation_status(cedula, nuevo_estado, usuario)


def list_associates() -> list[dict]:
    return [_enrich_associate(associate) for associate in db.get_all_associates()]


