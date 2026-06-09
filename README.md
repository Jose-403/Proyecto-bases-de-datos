# COOVALLUNA — Sistema de gestión

Aplicación web en **Python + Flask** conectada a **PostgreSQL** mediante **psycopg2** (sin ORM).

## Requisitos

- Python 3.10 o superior
- PostgreSQL 15 o superior
- Base de datos `Coovalluna` creada y cargada con el esquema del proyecto

## Configuración de la base de datos

### 1. Variables de entorno

Copie `.env.example` a `.env` y ajuste si es necesario:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Coovalluna
DB_USER=postgres
DB_PASSWORD=2005
```

### 2. Crear y cargar la base de datos

Desde `psql` o pgAdmin, ejecute en este orden:

```sql
CREATE DATABASE "Coovalluna";
```

```powershell
psql -U postgres -d Coovalluna -f schema_coovalluna.sql
psql -U postgres -d Coovalluna -f datos_prueba.sql
```

Al iniciar la aplicación, `init_db()` ejecuta automáticamente `schema_app_extension.sql`, que crea las tablas auxiliares `usuario_sistema` y `bitacora` si no existen.

### 3. Verificar conexión

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python inspect_db.py
```

## Esquema de la base de datos

### Tablas principales (DDL del proyecto)

Definidas en `schema_coovalluna.sql`:

| Área | Tablas |
|------|--------|
| Agencias | `agencia`, `agencia_telefono` |
| Asociados | `asociado`, `asociado_telefono`, `asociado_correo`, `fundador`, `beneficiarios` |
| Empleados | `empleado`, `empleado_telefono`, `cajero`, `asesor`, `director_agencia` |
| Supervisión | `supervisa` |
| Créditos | `credito`, `cuotas`, `pagos`, `codeudora` |
| Ahorros | `cuenta_de_ahorros`, `movimientos` |
| Atención | `atiende` |

### Tablas auxiliares de la aplicación

Definidas en `schema_app_extension.sql`:

- `usuario_sistema` — usuarios con acceso web (correo, contraseña hasheada, perfil)
- `bitacora` — registro de auditoría de operaciones

## Instalación

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar en localhost

```powershell
python app.py
```

Abre el navegador en: **http://127.0.0.1:5000**

## Acceso al sistema

La autenticación consulta dos fuentes:

1. **`usuario_sistema`** — usuarios creados desde el módulo de administración (contraseña hasheada con Werkzeug).
2. **`director_agencia` + `empleado`** — directores de agencia autenticados por `correo_corp` y `clave_acceso`.

### Usuario de prueba (datos de `datos_prueba.sql`)

| Correo | Contraseña | Perfil |
|--------|------------|--------|
| `manuel.rodriguez@gmail.com` | `Dir2025AG001` | Administrador (director de agencia) |

Los perfiles disponibles son: `administrador`, `asesor` y `asociado`.

## Módulos del administrador

| Módulo | Ruta | Descripción |
|--------|------|-------------|
| Agencias | `/admin/agencias` | Registro de agencias |
| Empleados | `/admin/empleados` | Registro de empleados por agencia |
| Supervisión | `/admin/supervision` | Asignación de jerarquía entre empleados |
| Asociados | `/admin/asociados` | Registro y cambio de estado de vinculación |
| Usuarios | `/admin/usuarios` | Creación de usuarios del sistema |
| Bitácora | `/admin/bitacora` | Consulta de auditoría con filtros |
| Estado de cartera | `/admin/estado-cartera` | Reporte por línea y estado, export CSV/PDF |

## Estructura del proyecto

```
├── app.py                    # Rutas Flask y control de acceso por rol
├── config.py                 # Constantes, roles y operaciones de bitácora
├── database.py               # Consultas SQL parametrizadas (psycopg2)
├── db_config.py              # Configuración de conexión PostgreSQL
├── db_mappers.py             # Mapeo entre columnas de BD y campos de la app
├── inspect_db.py             # Utilidad para inspeccionar tablas en PostgreSQL
├── schema_coovalluna.sql     # DDL principal del esquema
├── datos_prueba.sql          # Datos de prueba
├── schema_app_extension.sql    # Tablas auxiliares (usuario_sistema, bitacora)
├── services/                 # Lógica de negocio (sin SQL)
│   ├── agency_service.py
│   ├── employee_service.py
│   ├── supervision_service.py
│   ├── associate_service.py
│   ├── user_service.py
│   ├── audit_service.py
│   └── portfolio_service.py
├── templates/                # Vistas HTML (Jinja2)
│   └── admin/                # Módulos del administrador
└── static/                   # Hojas de estilo CSS
```

## Tecnologías

| Componente | Tecnología |
|------------|------------|
| RDBMS | PostgreSQL 15+ |
| Back-end | Python 3, Flask |
| Driver BD | psycopg2-binary |
| Front-end | HTML, CSS, Jinja2 |
| Reportes | fpdf2 (PDF), csv (exportación) |

## Repositorio

Código fuente en GitHub: [Proyecto-bases-de-datos](https://github.com/Jose-403/Proyecto-bases-de-datos)
