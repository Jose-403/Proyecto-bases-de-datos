"""Constantes de configuración y roles del sistema COOVALLUNA."""

ROLES = {
    "ADMINISTRADOR": "administrador",
    "ASESOR": "asesor",
    "ASOCIADO": "asociado",
}

ROLE_LABELS = {
    "administrador": "Administrador",
    "asesor": "Asesor",
    "asociado": "Asociado",
}

SYSTEM_USER_ROLES = {
    "administrador": "Administrador",
    "asesor": "Asesor",
    "asociado": "Asociado",
}

# Campos obligatorios al registrar una agencia
AGENCY_REQUIRED_FIELDS = ("codigo", "nombre", "municipio", "fecha_apertura")

# Campos obligatorios al registrar un empleado
EMPLOYEE_REQUIRED_FIELDS = ("cedula", "nombre", "agencia_codigo", "cargo", "estado_laboral")

ESTADOS_LABORALES = ("Activo", "Licencia", "Retirado")

# Campos obligatorios al registrar un asociado de la cooperativa
ASSOCIATE_REQUIRED_FIELDS = (
    "cedula",
    "nombre",
    "apellido",
    "tipo_asociado",
    "fecha_afiliacion",
)

TIPOS_ASOCIADO = {
    "fundador": "Fundador",
    "regular": "Asociado regular",
}

ESTADOS_VINCULACION = {
    "activo": "Activo",
    "suspendido": "Suspendido",
    "retirado": "Retirado",
}

LINEAS_CREDITO = ("Consumo", "Comercial", "Vivienda", "Microcrédito")

ESTADOS_CREDITO = ("Vigente", "Mora", "Cancelado", "Castigado")

OPERACIONES_BITACORA = {
    "acceso_sistema": "Acceso al sistema",
    "registro_agencia": "Registro de agencia",
    "registro_empleado": "Registro de empleado",
    "asignacion_supervision": "Asignación de supervisión",
    "registro_asociado": "Registro de asociado",
    "cambio_estado_vinculacion": "Cambio estado vinculación",
    "creacion_usuario": "Creación de usuario",
}
