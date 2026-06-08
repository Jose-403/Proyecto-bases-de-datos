"""Lógica de negocio para la bitácora de auditoría."""

from config import OPERACIONES_BITACORA
import database as db


def log_operation(usuario: str, operacion: str, dato_afectado: str) -> None:
    db.log_audit(usuario, operacion, dato_afectado)


def query_bitacora(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    usuario: str = "",
    operacion: str = "",
) -> list[dict]:
    entries = db.get_bitacora_entries(
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
        usuario=usuario or None,
        operacion=operacion or None,
    )

    for entry in entries:
        entry["operacion_label"] = OPERACIONES_BITACORA.get(
            entry["operacion"],
            entry["operacion"],
        )

    return entries


def list_usuarios_bitacora() -> list[str]:
    return db.get_bitacora_usuarios()
