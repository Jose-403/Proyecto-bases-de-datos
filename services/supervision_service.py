"""Lógica de negocio para relaciones de supervisión."""

import database as db


def _employee_display_name(employee: dict) -> str:
    name = employee["nombre"]
    if employee.get("apellido"):
        name = f"{name} {employee['apellido']}"
    return name


def _normalize_form_data(form_data: dict) -> dict:
    return {
        "supervisor_cedula": form_data.get("supervisor_cedula", "").strip(),
        "subordinate_cedula": form_data.get("subordinate_cedula", "").strip(),
    }


def validate_supervision_data(data: dict) -> tuple[bool, str]:
    if not data.get("supervisor_cedula") or not data.get("subordinate_cedula"):
        return False, "Debe seleccionar supervisor y empleado supervisado."

    if data["supervisor_cedula"] == data["subordinate_cedula"]:
        return False, "Un empleado no puede ser supervisor de sí mismo."

    supervisor = db.get_employee_by_cedula(data["supervisor_cedula"])
    if supervisor is None:
        return False, "El supervisor seleccionado no existe en el sistema."

    subordinate = db.get_employee_by_cedula(data["subordinate_cedula"])
    if subordinate is None:
        return False, "El empleado supervisado no existe en el sistema."

    return True, ""


def assign_supervision(form_data: dict) -> tuple[bool, str, dict]:
    data = _normalize_form_data(form_data)
    valid, message = validate_supervision_data(data)

    if not valid:
        return False, message, data

    had_supervisor = db.get_supervisor_cedula(data["subordinate_cedula"]) is not None
    created, message = db.assign_supervision(
        data["supervisor_cedula"],
        data["subordinate_cedula"],
    )

    if created and had_supervisor:
        message = "Se actualizó el supervisor del empleado."

    return created, message, data


def build_hierarchy() -> list[dict]:
    employees = db.get_all_employees()
    relations = db.get_all_supervisions()

    if not employees:
        return []

    children_map: dict[str, list[str]] = {}
    subordinates: set[str] = set()

    for relation in relations:
        supervisor = relation["supervisor_cedula"]
        subordinate = relation["subordinate_cedula"]
        children_map.setdefault(supervisor, []).append(subordinate)
        subordinates.add(subordinate)

    employee_map = {employee["cedula"]: employee for employee in employees}

    def build_node(cedula: str, level: int = 0) -> dict:
        employee = employee_map[cedula]
        children = [
            build_node(child_cedula, level + 1)
            for child_cedula in children_map.get(cedula, [])
            if child_cedula in employee_map
        ]
        return {
            "cedula": cedula,
            "nombre": _employee_display_name(employee),
            "cargo": employee["cargo"],
            "agencia": employee["agency_codigo"],
            "level": level,
            "children": children,
        }

    roots = [
        employee["cedula"]
        for employee in employees
        if employee["cedula"] not in subordinates
    ]

    return [build_node(cedula) for cedula in roots]


def list_employees_for_select() -> list[dict]:
    employees = db.get_all_employees()
    for employee in employees:
        employee["display_name"] = (
            f"{employee['cedula']} — {_employee_display_name(employee)} ({employee['cargo']})"
        )
    return employees
