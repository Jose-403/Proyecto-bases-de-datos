"""Lógica de negocio para el registro de empleados."""

from config import EMPLOYEE_REQUIRED_FIELDS, ESTADOS_LABORALES
import database as db


def _normalize_form_data(form_data: dict) -> dict:
    return {
        "cedula": form_data.get("cedula", "").strip(),
        "nombre": form_data.get("nombre", "").strip(),
        "apellido": form_data.get("apellido", "").strip(),
        "agencia_codigo": form_data.get("agencia_codigo", "").strip().upper(),
        "cargo": form_data.get("cargo", "").strip(),
        "estado_laboral": form_data.get("estado_laboral", "").strip(),
        "telefono": form_data.get("telefono", "").strip(),
        "fecha_ingreso": form_data.get("fecha_ingreso", "").strip(),
    }


def validate_employee_data(data: dict) -> tuple[bool, str]:
    missing = [
        field
        for field in EMPLOYEE_REQUIRED_FIELDS
        if not data.get(field)
    ]

    if missing:
        return False, (
            "Debe completar todos los campos obligatorios: "
            "cédula, nombre, agencia, cargo y estado laboral."
        )

    if db.employee_cedula_exists(data["cedula"]):
        return False, "El número de cédula ya está registrado en el sistema."

    agency = db.get_agency_by_codigo(data["agencia_codigo"])
    if agency is None:
        return False, "La agencia seleccionada no existe en el sistema."

    if data["estado_laboral"] not in ESTADOS_LABORALES:
        return False, "El estado laboral seleccionado no es válido."

    return True, ""


def register_employee(form_data: dict) -> tuple[bool, str, dict]:
    data = _normalize_form_data(form_data)
    valid, message = validate_employee_data(data)

    if not valid:
        return False, message, data

    created, message = db.create_employee(data)
    return created, message, data


def list_employees() -> list[dict]:
    return db.get_all_employees()
