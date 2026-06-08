"""Mapeos entre el esquema PostgreSQL real y la aplicación."""

ESTADO_LABORAL_DB_TO_APP = {
    "activo": "Activo",
    "en_licencia": "Licencia",
    "retirado": "Retirado",
}

ESTADO_LABORAL_APP_TO_DB = {
    "Activo": "activo",
    "Inactivo": "en_licencia",
    "Licencia": "en_licencia",
    "Retirado": "retirado",
}

LINEAS_CREDITO_LABELS = {
    "libre_inversion": "Libre inversión",
    "vivienda": "Vivienda",
    "agropecuario": "Agropecuario",
    "educativo": "Educativo",
    "empresarial": "Empresarial",
}

ESTADOS_CREDITO_LABELS = {
    "en_estudio": "En estudio",
    "aprobado": "Aprobado",
    "desembolsado": "Desembolsado",
    "al_dia": "Al día",
    "en_mora": "En mora",
    "cancelado": "Cancelado",
    "castigado": "Castigado",
}


def agency_display_name(row: dict) -> str:
    parts = [row.get("primer_nombre", ""), row.get("segundo_nombre") or ""]
    return " ".join(part for part in parts if part).strip()


def person_display_name(primer_nombre: str, segundo_nombre: str | None, apellido: str) -> str:
    nombre = primer_nombre
    if segundo_nombre:
        nombre = f"{nombre} {segundo_nombre}"
    return f"{nombre} {apellido}".strip()


def map_agency_row(row: dict, telefono: str | None = None) -> dict:
    return {
        "codigo": row["codigo_agencia"],
        "nombre": agency_display_name(row),
        "direccion": row.get("calle"),
        "municipio": row["municipio"],
        "telefono": telefono,
        "fecha_apertura": str(row["fecha_apertura"]),
    }


def map_employee_row(row: dict, telefono: str | None = None) -> dict:
    return {
        "cedula": row["cedula_empleado"],
        "nombre": row["primer_nombre"],
        "apellido": row["apellido"],
        "agency_codigo": row["codigo_agencia"],
        "agencia_nombre": row.get("agencia_nombre"),
        "cargo": row["cargo"],
        "estado_laboral": ESTADO_LABORAL_DB_TO_APP.get(
            row["estado_laboral"],
            row["estado_laboral"],
        ),
        "telefono": telefono,
        "fecha_ingreso": str(row["fecha_ingreso"]) if row.get("fecha_ingreso") else None,
    }


def map_associate_row(
    row: dict,
    telefono: str | None = None,
    email: str | None = None,
    es_fundador: bool = False,
) -> dict:
    return {
        "cedula": row["cedula_asociado"],
        "nombre": row["primer_nombre"],
        "apellido": f"{row.get('segundo_nombre') or ''} {row['apellido']}".strip(),
        "tipo_asociado": "fundador" if es_fundador else "regular",
        "estado_vinculacion": row["estado"],
        "direccion": row.get("calle"),
        "telefono": telefono,
        "email": email,
        "fecha_afiliacion": str(row["fecha_ingreso"]),
    }
