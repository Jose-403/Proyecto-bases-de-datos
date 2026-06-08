"""Capa de acceso a datos PostgreSQL — esquema COOVALLUNA."""

import secrets
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash

from config import OPERACIONES_BITACORA, ROLES
from db_config import DB_CONFIG
from db_mappers import (
    ESTADO_LABORAL_APP_TO_DB,
    ESTADOS_CREDITO_LABELS,
    LINEAS_CREDITO_LABELS,
    map_agency_row,
    map_associate_row,
    map_employee_row,
)

SCHEMA_EXTENSION = Path(__file__).parent / "schema_app_extension.sql"


@contextmanager
def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _fetchone(query: str, params: tuple = ()) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
    return dict(row) if row else None


def _fetchall(query: str, params: tuple = ()) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def _execute(query: str, params: tuple = ()) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)


def init_db() -> None:
    """Verifica conexión y crea tablas auxiliares de la aplicación."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            if SCHEMA_EXTENSION.exists():
                cur.execute(SCHEMA_EXTENSION.read_text(encoding="utf-8"))


def _user_row_to_dict(row: dict) -> dict:
    user = dict(row)
    user["username"] = user.get("correo", "")
    user["email"] = user.get("correo", "")
    user["role"] = user.get("perfil", user.get("role"))
    user["must_change_password"] = bool(user.get("debe_cambiar_clave", False))
    return user


def _get_agency_phone(codigo_agencia: str) -> str | None:
    row = _fetchone(
        """
        SELECT telefono FROM agencia_telefono
        WHERE codigo_agencia = %s
        ORDER BY id_tel_agencia
        LIMIT 1
        """,
        (codigo_agencia,),
    )
    return row["telefono"] if row else None


def _get_associate_phone(cedula: str) -> str | None:
    row = _fetchone(
        """
        SELECT telefono FROM asociado_telefono
        WHERE cedula_asociado = %s
        ORDER BY id_tel_asociado
        LIMIT 1
        """,
        (cedula,),
    )
    return row["telefono"] if row else None


def _get_associate_email(cedula: str) -> str | None:
    row = _fetchone(
        """
        SELECT correo FROM asociado_correo
        WHERE cedula_asociado = %s
        ORDER BY id_cor_asociado
        LIMIT 1
        """,
        (cedula,),
    )
    return row["correo"] if row else None


def _is_fundador(cedula: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM fundador WHERE cedula_asociado = %s",
        (cedula,),
    )
    return row is not None


def _verify_director(email: str, password: str) -> dict | None:
    row = _fetchone(
        """
        SELECT e.cedula_empleado, e.correo_corp, d.clave_acceso
        FROM empleado e
        INNER JOIN director_agencia d ON d.cedula_empleado = e.cedula_empleado
        WHERE LOWER(e.correo_corp) = %s
        """,
        (email.strip().lower(),),
    )
    if row is None or row["clave_acceso"] != password:
        return None

    return {
        "id": row["cedula_empleado"],
        "username": row["correo_corp"],
        "email": row["correo_corp"],
        "password_hash": "",
        "role": ROLES["ADMINISTRADOR"],
        "must_change_password": False,
    }


def create_user(
    username: str,
    password: str,
    role: str = ROLES["ASOCIADO"],
    email: str | None = None,
    must_change_password: bool = False,
) -> tuple[bool, str]:
    user_email = (email or f"{username}@coovalluna.local").strip().lower()
    password_hash = generate_password_hash(password)
    try:
        _execute(
            """
            INSERT INTO usuario_sistema (correo, password_hash, perfil, debe_cambiar_clave)
            VALUES (%s, %s, %s, %s)
            """,
            (user_email, password_hash, role, must_change_password),
        )
        return True, "Usuario creado correctamente."
    except pg_errors.UniqueViolation:
        return False, "El correo electrónico ya está registrado en el sistema."


def email_exists(email: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM usuario_sistema WHERE correo = %s",
        (email.strip().lower(),),
    )
    return row is not None


def generate_temp_password() -> str:
    return secrets.token_urlsafe(8)


def create_system_user(email: str, role: str) -> tuple[bool, str, str]:
    email = email.strip().lower()
    temp_password = generate_temp_password()
    password_hash = generate_password_hash(temp_password)
    try:
        _execute(
            """
            INSERT INTO usuario_sistema (correo, password_hash, perfil, debe_cambiar_clave)
            VALUES (%s, %s, %s, TRUE)
            """,
            (email, password_hash, role),
        )
        return True, temp_password, "Usuario del sistema creado correctamente."
    except pg_errors.UniqueViolation:
        return False, "", "El correo electrónico ya está registrado en el sistema."


def get_user_by_username(username: str) -> dict | None:
    return get_user_by_email(username)


def get_user_by_id(user_id: int) -> dict | None:
    row = _fetchone(
        """
        SELECT id_usuario AS id, correo, password_hash, perfil, debe_cambiar_clave
        FROM usuario_sistema WHERE id_usuario = %s
        """,
        (user_id,),
    )
    return _user_row_to_dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    row = _fetchone(
        """
        SELECT id_usuario AS id, correo, password_hash, perfil, debe_cambiar_clave
        FROM usuario_sistema WHERE correo = %s
        """,
        (email.strip().lower(),),
    )
    return _user_row_to_dict(row) if row else None


def get_all_system_users() -> list[dict]:
    rows = _fetchall(
        """
        SELECT id_usuario AS id, correo, perfil, debe_cambiar_clave, fecha_creacion AS created_at
        FROM usuario_sistema
        ORDER BY fecha_creacion DESC
        """
    )
    return [_user_row_to_dict(row) for row in rows]


def update_user_password(user_id: int, new_password: str) -> tuple[bool, str]:
    password_hash = generate_password_hash(new_password)
    _execute(
        """
        UPDATE usuario_sistema
        SET password_hash = %s, debe_cambiar_clave = FALSE
        WHERE id_usuario = %s
        """,
        (password_hash, user_id),
    )
    return True, "Contraseña actualizada correctamente."


def verify_user(login: str, password: str) -> dict | None:
    login = login.strip().lower()
    user = get_user_by_email(login)

    if user and check_password_hash(user["password_hash"], password):
        return user

    return _verify_director(login, password)


def agency_code_exists(codigo: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM agencia WHERE codigo_agencia = %s",
        (codigo.upper(),),
    )
    return row is not None


def create_agency(data: dict) -> tuple[bool, str]:
    try:
        _execute(
            """
            INSERT INTO agencia
                (codigo_agencia, primer_nombre, municipio, calle, fecha_apertura)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                data["codigo"],
                data["nombre"],
                data["municipio"],
                data["direccion"] or "Por registrar",
                data["fecha_apertura"],
            ),
        )
        if data.get("telefono"):
            _execute(
                """
                INSERT INTO agencia_telefono (codigo_agencia, telefono)
                VALUES (%s, %s)
                """,
                (data["codigo"], data["telefono"]),
            )
        return True, "Agencia registrada correctamente."
    except pg_errors.UniqueViolation:
        return False, "El código de agencia ya existe en el sistema."


def get_all_agencies() -> list[dict]:
    rows = _fetchall(
        """
        SELECT codigo_agencia, primer_nombre, segundo_nombre, municipio, calle, fecha_apertura
        FROM agencia
        ORDER BY fecha_apertura DESC
        """
    )
    return [
        map_agency_row(row, _get_agency_phone(row["codigo_agencia"]))
        for row in rows
    ]


def get_agency_by_codigo(codigo: str) -> dict | None:
    row = _fetchone(
        """
        SELECT codigo_agencia, primer_nombre, segundo_nombre, municipio, calle, fecha_apertura
        FROM agencia
        WHERE codigo_agencia = %s
        """,
        (codigo.upper(),),
    )
    if row is None:
        return None
    return map_agency_row(row, _get_agency_phone(row["codigo_agencia"]))


def employee_cedula_exists(cedula: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM empleado WHERE cedula_empleado = %s",
        (cedula,),
    )
    return row is not None


def create_employee(data: dict) -> tuple[bool, str]:
    estado_db = ESTADO_LABORAL_APP_TO_DB.get(
        data["estado_laboral"],
        data["estado_laboral"].lower(),
    )
    correo = f"{data['cedula']}@empleado.coovalluna.com"
    try:
        _execute(
            """
            INSERT INTO empleado
                (cedula_empleado, primer_nombre, apellido, fecha_ingreso,
                 salario_base, estado_laboral, cargo, correo_corp, codigo_agencia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["cedula"],
                data["nombre"],
                data.get("apellido") or data["nombre"],
                data.get("fecha_ingreso") or "2024-01-01",
                2000000,
                estado_db,
                data["cargo"],
                correo,
                data["agencia_codigo"],
            ),
        )
        if data.get("telefono"):
            _execute(
                """
                INSERT INTO empleado_telefono (cedula_empleado, telefono)
                VALUES (%s, %s)
                """,
                (data["cedula"], data["telefono"]),
            )
        return True, "Empleado registrado correctamente."
    except pg_errors.UniqueViolation:
        return False, "El número de cédula ya está registrado en el sistema."


def get_all_employees() -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            e.cedula_empleado,
            e.primer_nombre,
            e.apellido,
            e.codigo_agencia,
            a.primer_nombre AS agencia_primer_nombre,
            a.segundo_nombre AS agencia_segundo_nombre,
            e.cargo,
            e.estado_laboral,
            e.fecha_ingreso
        FROM empleado e
        INNER JOIN agencia a ON a.codigo_agencia = e.codigo_agencia
        ORDER BY e.fecha_ingreso DESC
        """
    )
    result = []
    for row in rows:
        row["agencia_nombre"] = " ".join(
            part
            for part in [row.get("agencia_primer_nombre"), row.get("agencia_segundo_nombre")]
            if part
        )
        result.append(
            map_employee_row(row, _get_employee_phone(row["cedula_empleado"]))
        )
    return result


def _get_employee_phone(cedula: str) -> str | None:
    row = _fetchone(
        """
        SELECT telefono FROM empleado_telefono
        WHERE cedula_empleado = %s
        ORDER BY id_tel_empleado
        LIMIT 1
        """,
        (cedula,),
    )
    return row["telefono"] if row else None


def get_employee_by_cedula(cedula: str) -> dict | None:
    row = _fetchone(
        """
        SELECT
            e.cedula_empleado,
            e.primer_nombre,
            e.apellido,
            e.codigo_agencia,
            a.primer_nombre AS agencia_primer_nombre,
            a.segundo_nombre AS agencia_segundo_nombre,
            e.cargo,
            e.estado_laboral,
            e.fecha_ingreso
        FROM empleado e
        INNER JOIN agencia a ON a.codigo_agencia = e.codigo_agencia
        WHERE e.cedula_empleado = %s
        """,
        (cedula,),
    )
    if row is None:
        return None
    row["agencia_nombre"] = " ".join(
        part
        for part in [row.get("agencia_primer_nombre"), row.get("agencia_segundo_nombre")]
        if part
    )
    return map_employee_row(row, _get_employee_phone(cedula))


def get_supervisor_cedula(subordinate_cedula: str) -> str | None:
    row = _fetchone(
        """
        SELECT cedula_supervisor
        FROM supervisa
        WHERE cedula_supervisado = %s
        LIMIT 1
        """,
        (subordinate_cedula,),
    )
    return row["cedula_supervisor"] if row else None


def assign_supervision(supervisor_cedula: str, subordinate_cedula: str) -> tuple[bool, str]:
    if supervisor_cedula == subordinate_cedula:
        return False, "Un empleado no puede ser supervisor de sí mismo."

    try:
        _execute(
            "DELETE FROM supervisa WHERE cedula_supervisado = %s",
            (subordinate_cedula,),
        )
        _execute(
            """
            INSERT INTO supervisa (cedula_supervisor, cedula_supervisado)
            VALUES (%s, %s)
            """,
            (supervisor_cedula, subordinate_cedula),
        )
        return True, "Relación de supervisión asignada correctamente."
    except pg_errors.IntegrityError:
        return False, "No se pudo asignar la relación de supervisión."


def get_all_supervisions() -> list[dict]:
    return _fetchall(
        """
        SELECT
            s.cedula_supervisor,
            s.cedula_supervisado AS subordinate_cedula,
            sup.primer_nombre AS supervisor_nombre,
            sup.apellido AS supervisor_apellido,
            sup.cargo AS supervisor_cargo,
            sub.primer_nombre AS subordinate_nombre,
            sub.apellido AS subordinate_apellido,
            sub.cargo AS subordinate_cargo
        FROM supervisa s
        INNER JOIN empleado sup ON sup.cedula_empleado = s.cedula_supervisor
        INNER JOIN empleado sub ON sub.cedula_empleado = s.cedula_supervisado
        """
    )


def associate_cedula_exists(cedula: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM asociado WHERE cedula_asociado = %s",
        (cedula,),
    )
    return row is not None


def create_associate(data: dict) -> tuple[bool, str]:
    apellido_parts = data["apellido"].split(" ", 1)
    apellido = apellido_parts[0]
    segundo_nombre = apellido_parts[1] if len(apellido_parts) > 1 else None

    try:
        _execute(
            """
            INSERT INTO asociado
                (cedula_asociado, primer_nombre, segundo_nombre, apellido,
                 fecha_nac, municipio, calle, fecha_ingreso, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'activo')
            """,
            (
                data["cedula"],
                data["nombre"],
                segundo_nombre,
                apellido,
                "1990-01-01",
                data.get("municipio") or "Por registrar",
                data.get("direccion") or "Por registrar",
                data["fecha_afiliacion"],
            ),
        )
        if data.get("telefono"):
            _execute(
                """
                INSERT INTO asociado_telefono (cedula_asociado, telefono)
                VALUES (%s, %s)
                """,
                (data["cedula"], data["telefono"]),
            )
        if data.get("email"):
            _execute(
                """
                INSERT INTO asociado_correo (cedula_asociado, correo)
                VALUES (%s, %s)
                """,
                (data["cedula"], data["email"]),
            )
        if data.get("tipo_asociado") == "fundador":
            _execute(
                """
                INSERT INTO fundador (cedula_asociado, numero_acta, anio_reconocimiento)
                VALUES (%s, %s, %s)
                """,
                (data["cedula"], f"ACTA-{data['cedula']}", 2024),
            )
        return True, "Asociado registrado correctamente."
    except pg_errors.UniqueViolation:
        return False, "Ya existe un asociado registrado con ese número de cédula."


def get_associate_by_cedula(cedula: str) -> dict | None:
    row = _fetchone(
        """
        SELECT cedula_asociado, primer_nombre, segundo_nombre, apellido,
               fecha_ingreso, estado, calle
        FROM asociado
        WHERE cedula_asociado = %s
        """,
        (cedula,),
    )
    if row is None:
        return None
    return map_associate_row(
        row,
        _get_associate_phone(cedula),
        _get_associate_email(cedula),
        _is_fundador(cedula),
    )


def get_all_associates() -> list[dict]:
    rows = _fetchall(
        """
        SELECT cedula_asociado, primer_nombre, segundo_nombre, apellido,
               fecha_ingreso, estado, calle
        FROM asociado
        ORDER BY fecha_ingreso DESC
        """
    )
    return [
        map_associate_row(
            row,
            _get_associate_phone(row["cedula_asociado"]),
            _get_associate_email(row["cedula_asociado"]),
            _is_fundador(row["cedula_asociado"]),
        )
        for row in rows
    ]


def update_associate_vinculation_status(
    cedula: str,
    nuevo_estado: str,
    usuario: str,
) -> tuple[bool, str]:
    associate = get_associate_by_cedula(cedula)
    if associate is None:
        return False, "No se encontró un asociado con esa cédula."

    estado_anterior = associate["estado_vinculacion"]
    if estado_anterior == nuevo_estado:
        return False, "El asociado ya tiene ese estado de vinculación."

    _execute(
        "UPDATE asociado SET estado = %s WHERE cedula_asociado = %s",
        (nuevo_estado, cedula),
    )

    nombre = f"{associate['nombre']} {associate['apellido']}"
    dato_afectado = f"Asociado {nombre} ({cedula}): {estado_anterior} → {nuevo_estado}"
    log_audit(usuario, "cambio_estado_vinculacion", dato_afectado)

    return True, "Estado de vinculación actualizado correctamente."


def log_audit(usuario: str, operacion: str, dato_afectado: str) -> None:
    if operacion not in OPERACIONES_BITACORA:
        return

    _execute(
        """
        INSERT INTO bitacora (usuario, operacion, dato_afectado)
        VALUES (%s, %s, %s)
        """,
        (usuario, operacion, dato_afectado),
    )


def get_bitacora_entries(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    usuario: str | None = None,
    operacion: str | None = None,
) -> list[dict]:
    query = """
        SELECT usuario, operacion, dato_afectado, fecha_hora
        FROM bitacora
        WHERE 1 = 1
    """
    params: list[str] = []

    if fecha_desde:
        query += " AND fecha_hora::date >= %s::date"
        params.append(fecha_desde)

    if fecha_hasta:
        query += " AND fecha_hora::date <= %s::date"
        params.append(fecha_hasta)

    if usuario:
        query += " AND usuario = %s"
        params.append(usuario)

    if operacion:
        query += " AND operacion = %s"
        params.append(operacion)

    query += " ORDER BY fecha_hora DESC"
    return _fetchall(query, tuple(params))


def get_bitacora_usuarios() -> list[str]:
    rows = _fetchall("SELECT DISTINCT usuario FROM bitacora ORDER BY usuario")
    return [row["usuario"] for row in rows]


def get_portfolio_report(
    agency_codigo: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> list[dict]:
    query = """
        SELECT
            linea_credito,
            estado_credito AS estado,
            COUNT(*) AS num_creditos,
            SUM(vlr_aprobado) AS valor_total
        FROM credito
        WHERE 1 = 1
    """
    params: list[str] = []

    if agency_codigo:
        query += " AND codigo_agencia = %s"
        params.append(agency_codigo.upper())

    if fecha_desde:
        query += " AND fecha_aprobacion::date >= %s::date"
        params.append(fecha_desde)

    if fecha_hasta:
        query += " AND fecha_aprobacion::date <= %s::date"
        params.append(fecha_hasta)

    query += " GROUP BY linea_credito, estado_credito ORDER BY linea_credito, estado_credito"

    rows = _fetchall(query, tuple(params))
    for row in rows:
        row["linea_credito"] = LINEAS_CREDITO_LABELS.get(
            row["linea_credito"],
            row["linea_credito"],
        )
        row["estado"] = ESTADOS_CREDITO_LABELS.get(row["estado"], row["estado"])
    return rows
