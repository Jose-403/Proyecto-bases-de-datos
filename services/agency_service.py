"""Lógica de negocio para el catálogo de agencias."""

from config import AGENCY_REQUIRED_FIELDS
import database as db


def _normalize_form_data(form_data: dict) -> dict:
    return {
        "codigo": form_data.get("codigo", "").strip().upper(),
        "nombre": form_data.get("nombre", "").strip(),
        "direccion": form_data.get("direccion", "").strip(),
        "municipio": form_data.get("municipio", "").strip(),
        "telefono": form_data.get("telefono", "").strip(),
        "fecha_apertura": form_data.get("fecha_apertura", "").strip(),
    }


def validate_agency_data(data: dict) -> tuple[bool, str]:
    missing = [
        field
        for field in AGENCY_REQUIRED_FIELDS
        if not data.get(field)
    ]

    if missing:
        return False, (
            "Debe completar todos los campos obligatorios: "
            "código, nombre, municipio y fecha de apertura."
        )

    if db.agency_code_exists(data["codigo"]):
        return False, "El código de agencia ya existe en el sistema."

    return True, ""


def register_agency(form_data: dict) -> tuple[bool, str, dict]:
    data = _normalize_form_data(form_data)
    valid, message = validate_agency_data(data)

    if not valid:
        return False, message, data

    created, message = db.create_agency(data)
    return created, message, data


def list_agencies() -> list[dict]:
    return db.get_all_agencies()
