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
            s.cedula_supervisor AS supervisor_cedula,
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
    fecha_nac = data.get("fecha_nac") or data.get("fecha_afiliacion")

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
                fecha_nac,
                data.get("municipio", ""),
                data.get("direccion", ""),
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


def beneficiary_document_exists(documento: str, exclude_cedula: str | None = None) -> bool:
    if exclude_cedula:
        row = _fetchone(
            """
            SELECT 1 AS ok FROM beneficiarios
            WHERE documento_benef = %s AND cedula_asociado <> %s
            """,
            (documento, exclude_cedula),
        )
    else:
        row = _fetchone(
            "SELECT 1 AS ok FROM beneficiarios WHERE documento_benef = %s",
            (documento,),
        )
    return row is not None


def get_beneficiaries_by_associate(cedula: str) -> list[dict]:
    return _fetchall(
        """
        SELECT
            documento_benef AS documento,
            primer_nombre AS nombre,
            apellido,
            parentesco,
            porcentaje_participacion AS porcentaje
        FROM beneficiarios
        WHERE cedula_asociado = %s
        ORDER BY documento_benef
        """,
        (cedula,),
    )


def register_beneficiaries_for_associate(
    cedula: str,
    beneficiaries: list[dict],
) -> tuple[bool, str]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM beneficiarios WHERE cedula_asociado = %s",
                    (cedula,),
                )
                for beneficiary in beneficiaries:
                    cur.execute(
                        """
                        INSERT INTO beneficiarios (
                            documento_benef,
                            primer_nombre,
                            segundo_nombre,
                            apellido,
                            parentesco,
                            porcentaje_participacion,
                            cedula_asociado
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            beneficiary["documento"],
                            beneficiary["nombre"],
                            None,
                            beneficiary["apellido"],
                            beneficiary["parentesco"],
                            beneficiary["porcentaje"],
                            cedula,
                        ),
                    )
        return True, "Beneficiarios registrados correctamente."
    except pg_errors.UniqueViolation:
        return False, "El documento de uno de los beneficiarios ya está registrado."
    except pg_errors.ForeignKeyViolation:
        return False, "El asociado indicado no existe en el sistema."


def savings_account_exists(numero_cuenta: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM cuenta_de_ahorros WHERE numero_cuenta = %s",
        (numero_cuenta,),
    )
    return row is not None


def _next_sequential_code(prefix: str, table: str, column: str) -> str:
    start_index = len(prefix) + 1
    pattern = f"^{prefix}[0-9]+$"
    row = _fetchone(
        f"""
        SELECT COALESCE(
            MAX(CAST(SUBSTRING({column} FROM {start_index}) AS INTEGER)),
            0
        ) AS max_num
        FROM {table}
        WHERE {column} ~ %s
        """,
        (pattern,),
    )
    max_num = int(row["max_num"]) if row else 0
    return f"{prefix}{max_num + 1:03d}"


def generate_savings_account_number() -> str:
    return _next_sequential_code("CA", "cuenta_de_ahorros", "numero_cuenta")


def create_savings_account(data: dict) -> tuple[bool, str, str]:
    numero_cuenta = data.get("numero_cuenta") or generate_savings_account_number()

    if savings_account_exists(numero_cuenta):
        return False, "El número de cuenta ya existe en el sistema.", numero_cuenta

    try:
        _execute(
            """
            INSERT INTO cuenta_de_ahorros
                (numero_cuenta, fecha_apertura, estado, cedula_asociado, codigo_agencia)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                numero_cuenta,
                data["fecha_apertura"],
                data["estado"],
                data["cedula_asociado"],
                data["codigo_agencia"],
            ),
        )
        return True, f"Cuenta de ahorro {numero_cuenta} abierta correctamente.", numero_cuenta
    except pg_errors.UniqueViolation:
        return False, "El número de cuenta ya existe en el sistema.", numero_cuenta
    except pg_errors.ForeignKeyViolation:
        return False, "El asociado o la agencia indicados no existen.", numero_cuenta


def get_savings_accounts_by_associate(cedula: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            c.numero_cuenta,
            c.fecha_apertura,
            c.estado,
            c.codigo_agencia,
            a.primer_nombre AS agencia_primer_nombre,
            a.segundo_nombre AS agencia_segundo_nombre
        FROM cuenta_de_ahorros c
        INNER JOIN agencia a ON a.codigo_agencia = c.codigo_agencia
        WHERE c.cedula_asociado = %s
        ORDER BY c.fecha_apertura DESC
        """,
        (cedula,),
    )
    for row in rows:
        row["agencia_nombre"] = " ".join(
            part
            for part in [row.get("agencia_primer_nombre"), row.get("agencia_segundo_nombre")]
            if part
        )
        row["fecha_apertura"] = str(row["fecha_apertura"])
    return rows


def get_savings_account(numero_cuenta: str) -> dict | None:
    row = _fetchone(
        """
        SELECT numero_cuenta, fecha_apertura, estado, cedula_asociado, codigo_agencia
        FROM cuenta_de_ahorros
        WHERE numero_cuenta = %s
        """,
        (numero_cuenta,),
    )
    if row is None:
        return None
    row["fecha_apertura"] = str(row["fecha_apertura"])
    return row


def get_active_savings_accounts() -> list[dict]:
    rows = _fetchall(
        """
        SELECT numero_cuenta, estado, cedula_asociado, codigo_agencia
        FROM cuenta_de_ahorros
        WHERE estado = 'activa'
        ORDER BY numero_cuenta
        """
    )
    return rows


def calculate_account_balance(numero_cuenta: str):
    row = _fetchone(
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN tipo_movimiento IN ('deposito', 'transferencia_entrante') THEN valor
                WHEN tipo_movimiento IN ('retiro', 'transferencia_saliente') THEN -valor
                ELSE 0
            END
        ), 0) AS saldo
        FROM movimientos
        WHERE numero_cuenta = %s
        """,
        (numero_cuenta,),
    )
    return row["saldo"] if row else 0


def generate_movement_number() -> str:
    return _next_sequential_code("MOV", "movimientos", "numero_transaccion")


def get_associate_cedula_by_email(email: str) -> str | None:
    row = _fetchone(
        """
        SELECT cedula_asociado
        FROM asociado_correo
        WHERE LOWER(correo) = %s
        """,
        (email.strip().lower(),),
    )
    return row["cedula_asociado"] if row else None


def get_employee_by_email(email: str) -> dict | None:
    row = _fetchone(
        """
        SELECT cedula_empleado, codigo_agencia, primer_nombre, apellido, cargo
        FROM empleado
        WHERE LOWER(correo_corp) = %s
        """,
        (email.strip().lower(),),
    )
    return dict(row) if row else None


def get_employee_agency_by_email(email: str) -> str | None:
    employee = get_employee_by_email(email)
    return employee["codigo_agencia"] if employee else None


def get_overdue_associates_for_advisor(
    cedula_empleado: str,
    codigo_agencia: str,
) -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            a.cedula_asociado,
            a.primer_nombre,
            a.segundo_nombre,
            a.apellido,
            c.numero_radicado,
            q.numero_cuota,
            q.fecha_vencimiento,
            q.estado_cuota,
            (CURRENT_DATE - q.fecha_vencimiento) AS dias_mora
        FROM cuotas q
        INNER JOIN credito c ON c.numero_radicado = q.numero_radicado
        INNER JOIN asociado a ON a.cedula_asociado = c.cedula_asociado
        INNER JOIN atiende at ON at.cedula_asociado = a.cedula_asociado
        WHERE at.cedula_empleado = %s
          AND c.codigo_agencia = %s
          AND q.fecha_vencimiento < CURRENT_DATE
          AND q.estado_cuota IN ('pendiente', 'con_mora')
          AND NOT EXISTS (
              SELECT 1 FROM pagos p WHERE p.id_cuota = q.id_cuota
          )
        ORDER BY dias_mora DESC, a.cedula_asociado, c.numero_radicado, q.numero_cuota
        """,
        (cedula_empleado, codigo_agencia.upper()),
    )
    for row in rows:
        row["fecha_vencimiento"] = str(row["fecha_vencimiento"])
        row["dias_mora"] = int(row["dias_mora"])
        row["nombre_completo"] = " ".join(
            part
            for part in [row.get("primer_nombre"), row.get("segundo_nombre"), row["apellido"]]
            if part
        )
    return rows


def get_savings_accounts_by_agency(codigo_agencia: str) -> list[dict]:
    return _fetchall(
        """
        SELECT numero_cuenta, estado, cedula_asociado, codigo_agencia
        FROM cuenta_de_ahorros
        WHERE codigo_agencia = %s
        ORDER BY numero_cuenta
        """,
        (codigo_agencia.upper(),),
    )


def get_movements_by_account(numero_cuenta: str) -> list[dict]:
    return get_movements_filtered(numero_cuenta)


def get_movements_filtered(
    numero_cuenta: str,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    tipo_movimiento: str | None = None,
    canal: str | None = None,
) -> list[dict]:
    query = """
        SELECT numero_transaccion, tipo_movimiento, valor, canal, fecha_hora
        FROM movimientos
        WHERE numero_cuenta = %s
    """
    params: list[str] = [numero_cuenta]

    if fecha_desde:
        query += " AND fecha_hora::date >= %s::date"
        params.append(fecha_desde)

    if fecha_hasta:
        query += " AND fecha_hora::date <= %s::date"
        params.append(fecha_hasta)

    if tipo_movimiento:
        query += " AND tipo_movimiento = %s"
        params.append(tipo_movimiento)

    if canal:
        query += " AND canal = %s"
        params.append(canal)

    query += " ORDER BY fecha_hora DESC"

    rows = _fetchall(query, tuple(params))
    for row in rows:
        row["valor"] = float(row["valor"])
        row["fecha_hora"] = str(row["fecha_hora"])
    return rows


def create_movement(data: dict) -> tuple[bool, str, str]:
    numero_transaccion = data.get("numero_transaccion")
    for _ in range(5):
        if not numero_transaccion:
            numero_transaccion = generate_movement_number()
        try:
            _execute(
                """
                INSERT INTO movimientos
                    (numero_transaccion, tipo_movimiento, valor, canal, fecha_hora, numero_cuenta)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    numero_transaccion,
                    data["tipo_movimiento"],
                    data["valor"],
                    data["canal"],
                    data["fecha_hora"],
                    data["numero_cuenta"],
                ),
            )
            return True, "Movimiento registrado correctamente.", numero_transaccion
        except pg_errors.UniqueViolation:
            numero_transaccion = None
        except pg_errors.ForeignKeyViolation:
            return False, "La cuenta indicada no existe en el sistema.", numero_transaccion or ""

    return False, "No se pudo generar un número de transacción único.", numero_transaccion or ""


def create_transfer_movements(data: dict) -> tuple[bool, str, str]:
    cuenta_origen = data["cuenta_origen"]
    cuenta_destino = data["cuenta_destino"]
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                numero_saliente = generate_movement_number()
                numero_entrante = f"MOV{int(numero_saliente[3:]) + 1:03d}"

                cur.execute(
                    """
                    INSERT INTO movimientos
                        (numero_transaccion, tipo_movimiento, valor, canal, fecha_hora, numero_cuenta)
                    VALUES (%s, 'transferencia_saliente', %s, %s, %s, %s)
                    """,
                    (
                        numero_saliente,
                        data["valor"],
                        data["canal"],
                        data["fecha_hora"],
                        cuenta_origen,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO movimientos
                        (numero_transaccion, tipo_movimiento, valor, canal, fecha_hora, numero_cuenta)
                    VALUES (%s, 'transferencia_entrante', %s, %s, %s, %s)
                    """,
                    (
                        numero_entrante,
                        data["valor"],
                        data["canal"],
                        data["fecha_hora"],
                        cuenta_destino,
                    ),
                )
        return (
            True,
            f"Transferencia registrada: {cuenta_origen} → {cuenta_destino}.",
            numero_saliente,
        )
    except pg_errors.UniqueViolation:
        return False, "No se pudo generar un número de transacción único.", ""
    except pg_errors.ForeignKeyViolation:
        return False, "Una de las cuentas de la transferencia no existe.", ""


def credit_radicado_exists(numero_radicado: str) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM credito WHERE numero_radicado = %s",
        (numero_radicado,),
    )
    return row is not None


def generate_credit_radicado() -> str:
    return _next_sequential_code("CR", "credito", "numero_radicado")


def create_credit_application(data: dict) -> tuple[bool, str, str]:
    numero_radicado = data.get("numero_radicado") or generate_credit_radicado()

    if credit_radicado_exists(numero_radicado):
        return False, "El número de radicado ya existe en el sistema.", numero_radicado

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO credito (
                        numero_radicado,
                        vlr_solicitado,
                        vlr_aprobado,
                        linea_credito,
                        tasa_interes,
                        plazo_meses,
                        fecha_aprobacion,
                        fecha_primer_vencimiento,
                        estado_credito,
                        cedula_asociado,
                        codigo_agencia
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        numero_radicado,
                        data["vlr_solicitado"],
                        data["vlr_aprobado"],
                        data["linea_credito"],
                        data["tasa_interes"],
                        data["plazo_meses"],
                        data["fecha_aprobacion"],
                        data["fecha_primer_vencimiento"],
                        data["estado_credito"],
                        data["cedula_asociado"],
                        data["codigo_agencia"],
                    ),
                )
                if data.get("cedula_codeudor"):
                    cur.execute(
                        """
                        INSERT INTO codeudora (cedula_codeudor, numero_radicado, fecha_firma)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            data["cedula_codeudor"],
                            numero_radicado,
                            data["fecha_firma_codeudor"],
                        ),
                    )
        return True, f"Solicitud de crédito {numero_radicado} radicada correctamente.", numero_radicado
    except pg_errors.UniqueViolation:
        return False, "El número de radicado ya existe en el sistema.", numero_radicado
    except pg_errors.ForeignKeyViolation:
        return False, "El asociado, la agencia o el codeudor indicados no existen.", numero_radicado


def get_credits_by_associate(cedula: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            c.numero_radicado,
            c.vlr_solicitado,
            c.vlr_aprobado,
            c.linea_credito,
            c.tasa_interes,
            c.plazo_meses,
            c.fecha_aprobacion,
            c.estado_credito,
            c.codigo_agencia,
            a.primer_nombre AS agencia_primer_nombre,
            a.segundo_nombre AS agencia_segundo_nombre
        FROM credito c
        INNER JOIN agencia a ON a.codigo_agencia = c.codigo_agencia
        WHERE c.cedula_asociado = %s
        ORDER BY c.fecha_aprobacion DESC
        """,
        (cedula,),
    )
    for row in rows:
        row["vlr_solicitado"] = float(row["vlr_solicitado"])
        row["vlr_aprobado"] = float(row["vlr_aprobado"])
        row["tasa_interes"] = float(row["tasa_interes"])
        row["fecha_aprobacion"] = str(row["fecha_aprobacion"])
        row["agencia_nombre"] = " ".join(
            part
            for part in [row.get("agencia_primer_nombre"), row.get("agencia_segundo_nombre")]
            if part
        )
    return rows


def get_credit_by_radicado(numero_radicado: str) -> dict | None:
    row = _fetchone(
        """
        SELECT
            numero_radicado,
            plazo_meses,
            vlr_aprobado,
            cedula_asociado,
            estado_credito
        FROM credito
        WHERE numero_radicado = %s
        """,
        (numero_radicado,),
    )
    if row is None:
        return None
    row["vlr_aprobado"] = float(row["vlr_aprobado"])
    return row


def get_credits_with_installments() -> list[dict]:
    return _fetchall(
        """
        SELECT DISTINCT c.numero_radicado, c.cedula_asociado, c.plazo_meses, c.estado_credito
        FROM credito c
        INNER JOIN cuotas q ON q.numero_radicado = c.numero_radicado
        ORDER BY c.numero_radicado
        """
    )


def get_installment(numero_radicado: str, numero_cuota: int) -> dict | None:
    row = _fetchone(
        """
        SELECT id_cuota, numero_cuota, fecha_vencimiento, estado_cuota, numero_radicado
        FROM cuotas
        WHERE numero_radicado = %s AND numero_cuota = %s
        """,
        (numero_radicado, numero_cuota),
    )
    if row is None:
        return None
    row["fecha_vencimiento"] = str(row["fecha_vencimiento"])
    return row


def installment_has_payment(id_cuota: int) -> bool:
    row = _fetchone(
        "SELECT 1 AS ok FROM pagos WHERE id_cuota = %s",
        (id_cuota,),
    )
    return row is not None


def get_installments_by_credit(numero_radicado: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT id_cuota, numero_cuota, fecha_vencimiento, estado_cuota
        FROM cuotas
        WHERE numero_radicado = %s
        ORDER BY numero_cuota
        """,
        (numero_radicado,),
    )
    for row in rows:
        row["fecha_vencimiento"] = str(row["fecha_vencimiento"])
    return rows


def get_payments_by_credit(numero_radicado: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            p.id_pago,
            p.fecha_pago,
            p.valor_pagado,
            p.estado_pago,
            q.numero_cuota,
            q.fecha_vencimiento
        FROM pagos p
        INNER JOIN cuotas q ON q.id_cuota = p.id_cuota
        WHERE q.numero_radicado = %s
        ORDER BY p.fecha_pago DESC, q.numero_cuota DESC
        """,
        (numero_radicado,),
    )
    for row in rows:
        row["valor_pagado"] = float(row["valor_pagado"])
        row["fecha_pago"] = str(row["fecha_pago"])
        row["fecha_vencimiento"] = str(row["fecha_vencimiento"])
    return rows


def register_installment_payment(
    id_cuota: int,
    fecha_pago: str,
    valor_pagado,
    estado_pago: str,
    estado_cuota: str,
) -> tuple[bool, str, int]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pagos (fecha_pago, valor_pagado, estado_pago, id_cuota)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id_pago
                    """,
                    (fecha_pago, valor_pagado, estado_pago, id_cuota),
                )
                id_pago = cur.fetchone()[0]
                cur.execute(
                    "UPDATE cuotas SET estado_cuota = %s WHERE id_cuota = %s",
                    (estado_cuota, id_cuota),
                )
        return True, "Pago de cuota registrado correctamente.", id_pago
    except pg_errors.UniqueViolation:
        return False, "Esta cuota ya tiene un pago registrado.", 0
    except pg_errors.ForeignKeyViolation:
        return False, "La cuota indicada no existe en el sistema.", 0


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


def _map_data_update_request(row: dict) -> dict:
    request_row = dict(row)
    request_row["fecha_solicitud"] = str(request_row["fecha_solicitud"])
    if request_row.get("fecha_resolucion"):
        request_row["fecha_resolucion"] = str(request_row["fecha_resolucion"])
    request_row["nombre_completo"] = " ".join(
        part
        for part in [
            request_row.get("primer_nombre"),
            request_row.get("segundo_nombre"),
            request_row.get("apellido"),
        ]
        if part
    )
    return request_row


def has_pending_data_update_request(cedula_asociado: str) -> bool:
    row = _fetchone(
        """
        SELECT 1 AS ok
        FROM solicitud_actualizacion_datos
        WHERE cedula_asociado = %s AND estado = 'pendiente'
        """,
        (cedula_asociado,),
    )
    return row is not None


def create_data_update_request(data: dict) -> tuple[bool, str, int]:
    try:
        row = _fetchone(
            """
            INSERT INTO solicitud_actualizacion_datos (
                cedula_asociado,
                telefono_solicitado,
                correo_solicitado,
                direccion_solicitada,
                telefono_actual,
                correo_actual,
                direccion_actual
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_solicitud
            """,
            (
                data["cedula_asociado"],
                data.get("telefono_solicitado"),
                data.get("correo_solicitado"),
                data.get("direccion_solicitada"),
                data.get("telefono_actual"),
                data.get("correo_actual"),
                data.get("direccion_actual"),
            ),
        )
        return True, "Solicitud registrada. Quedará pendiente de aprobación por un asesor.", row["id_solicitud"]
    except pg_errors.ForeignKeyViolation:
        return False, "El asociado indicado no existe en el sistema.", 0


def get_data_update_requests_by_associate(cedula_asociado: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            s.id_solicitud,
            s.cedula_asociado,
            s.telefono_solicitado,
            s.correo_solicitado,
            s.direccion_solicitada,
            s.telefono_actual,
            s.correo_actual,
            s.direccion_actual,
            s.estado,
            s.comentario_asesor,
            s.fecha_solicitud,
            s.fecha_resolucion,
            s.notificacion_vista,
            a.primer_nombre,
            a.segundo_nombre,
            a.apellido
        FROM solicitud_actualizacion_datos s
        INNER JOIN asociado a ON a.cedula_asociado = s.cedula_asociado
        WHERE s.cedula_asociado = %s
        ORDER BY s.fecha_solicitud DESC
        """,
        (cedula_asociado,),
    )
    return [_map_data_update_request(row) for row in rows]


def get_unread_data_update_notifications(cedula_asociado: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT id_solicitud, estado, fecha_resolucion, comentario_asesor
        FROM solicitud_actualizacion_datos
        WHERE cedula_asociado = %s
          AND estado IN ('aprobada', 'rechazada')
          AND notificacion_vista = FALSE
        ORDER BY fecha_resolucion DESC
        """,
        (cedula_asociado,),
    )
    for row in rows:
        if row.get("fecha_resolucion"):
            row["fecha_resolucion"] = str(row["fecha_resolucion"])
    return rows


def mark_data_update_notifications_read(cedula_asociado: str, ids: list[int]) -> None:
    if not ids:
        return
    placeholders = ", ".join(["%s"] * len(ids))
    _execute(
        f"""
        UPDATE solicitud_actualizacion_datos
        SET notificacion_vista = TRUE
        WHERE cedula_asociado = %s AND id_solicitud IN ({placeholders})
        """,
        (cedula_asociado, *ids),
    )


def get_pending_data_update_requests_for_advisor(cedula_empleado: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT
            s.id_solicitud,
            s.cedula_asociado,
            s.telefono_solicitado,
            s.correo_solicitado,
            s.direccion_solicitada,
            s.telefono_actual,
            s.correo_actual,
            s.direccion_actual,
            s.estado,
            s.fecha_solicitud,
            a.primer_nombre,
            a.segundo_nombre,
            a.apellido
        FROM solicitud_actualizacion_datos s
        INNER JOIN asociado a ON a.cedula_asociado = s.cedula_asociado
        INNER JOIN atiende at ON at.cedula_asociado = s.cedula_asociado
        WHERE at.cedula_empleado = %s
          AND s.estado = 'pendiente'
        ORDER BY s.fecha_solicitud ASC
        """,
        (cedula_empleado,),
    )
    return [_map_data_update_request(row) for row in rows]


def get_data_update_request_by_id(id_solicitud: int) -> dict | None:
    row = _fetchone(
        """
        SELECT
            s.id_solicitud,
            s.cedula_asociado,
            s.telefono_solicitado,
            s.correo_solicitado,
            s.direccion_solicitada,
            s.telefono_actual,
            s.correo_actual,
            s.direccion_actual,
            s.estado,
            s.comentario_asesor,
            s.fecha_solicitud,
            s.fecha_resolucion,
            a.primer_nombre,
            a.segundo_nombre,
            a.apellido
        FROM solicitud_actualizacion_datos s
        INNER JOIN asociado a ON a.cedula_asociado = s.cedula_asociado
        WHERE s.id_solicitud = %s
        """,
        (id_solicitud,),
    )
    return _map_data_update_request(row) if row else None


def advisor_can_manage_data_request(cedula_empleado: str, id_solicitud: int) -> bool:
    row = _fetchone(
        """
        SELECT 1 AS ok
        FROM solicitud_actualizacion_datos s
        INNER JOIN atiende at ON at.cedula_asociado = s.cedula_asociado
        WHERE s.id_solicitud = %s
          AND at.cedula_empleado = %s
          AND s.estado = 'pendiente'
        """,
        (id_solicitud, cedula_empleado),
    )
    return row is not None


def apply_associate_contact_update(
    cedula_asociado: str,
    telefono: str | None,
    correo: str | None,
    direccion: str | None,
) -> None:
    if direccion:
        _execute(
            "UPDATE asociado SET calle = %s WHERE cedula_asociado = %s",
            (direccion, cedula_asociado),
        )

    if telefono:
        phone_row = _fetchone(
            """
            SELECT id_tel_asociado
            FROM asociado_telefono
            WHERE cedula_asociado = %s
            ORDER BY id_tel_asociado
            LIMIT 1
            """,
            (cedula_asociado,),
        )
        if phone_row:
            _execute(
                "UPDATE asociado_telefono SET telefono = %s WHERE id_tel_asociado = %s",
                (telefono, phone_row["id_tel_asociado"]),
            )
        else:
            _execute(
                "INSERT INTO asociado_telefono (cedula_asociado, telefono) VALUES (%s, %s)",
                (cedula_asociado, telefono),
            )

    if correo:
        email_row = _fetchone(
            """
            SELECT id_cor_asociado
            FROM asociado_correo
            WHERE cedula_asociado = %s
            ORDER BY id_cor_asociado
            LIMIT 1
            """,
            (cedula_asociado,),
        )
        if email_row:
            _execute(
                "UPDATE asociado_correo SET correo = %s WHERE id_cor_asociado = %s",
                (correo.lower(), email_row["id_cor_asociado"]),
            )
        else:
            _execute(
                "INSERT INTO asociado_correo (cedula_asociado, correo) VALUES (%s, %s)",
                (cedula_asociado, correo.lower()),
            )


def resolve_data_update_request(
    id_solicitud: int,
    estado: str,
    cedula_asesor: str,
    comentario_asesor: str = "",
) -> tuple[bool, str]:
    request_row = get_data_update_request_by_id(id_solicitud)
    if request_row is None:
        return False, "La solicitud indicada no existe."

    if request_row["estado"] != "pendiente":
        return False, "Esta solicitud ya fue procesada."

    if estado == "aprobada":
        apply_associate_contact_update(
            request_row["cedula_asociado"],
            request_row.get("telefono_solicitado"),
            request_row.get("correo_solicitado"),
            request_row.get("direccion_solicitada"),
        )

    _execute(
        """
        UPDATE solicitud_actualizacion_datos
        SET estado = %s,
            cedula_asesor = %s,
            comentario_asesor = %s,
            fecha_resolucion = CURRENT_TIMESTAMP,
            notificacion_vista = FALSE
        WHERE id_solicitud = %s
        """,
        (estado, cedula_asesor, comentario_asesor or None, id_solicitud),
    )
    return True, "Solicitud procesada correctamente."
