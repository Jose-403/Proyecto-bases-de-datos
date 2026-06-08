import os
from functools import wraps

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

from config import (
    ESTADOS_LABORALES,
    ESTADOS_VINCULACION,
    OPERACIONES_BITACORA,
    ROLE_LABELS,
    ROLES,
    SYSTEM_USER_ROLES,
    TIPOS_ASOCIADO,
)
import database as db
from services import (
    agency_service,
    associate_service,
    audit_service,
    employee_service,
    portfolio_service,
    supervision_service,
    user_service,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def password_change_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("must_change_password"):
            flash("Debes cambiar tu contraseña temporal antes de continuar.", "warning")
            return redirect(url_for("change_password"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("Debes iniciar sesión para acceder.", "warning")
                return redirect(url_for("login"))

            if session.get("must_change_password"):
                flash("Debes cambiar tu contraseña temporal antes de continuar.", "warning")
                return redirect(url_for("change_password"))

            if session.get("user_role") not in allowed_roles:
                flash("No tienes permisos para acceder a esta sección.", "error")
                return redirect(url_for("dashboard"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def dashboard_url_for_role(role: str) -> str:
    if role == ROLES["ADMINISTRADOR"]:
        return url_for("admin_agencias")
    return url_for("dashboard")


def _set_user_session(user: dict):
    session["user_id"] = user["email"]
    session["user_role"] = user["role"]
    session["user_db_id"] = user["id"]
    session["must_change_password"] = user.get("must_change_password", False)


@app.route("/")
@login_required
@password_change_required
def index():
    return redirect(dashboard_url_for_role(session.get("user_role")))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session and not session.get("must_change_password"):
        return redirect(dashboard_url_for_role(session.get("user_role")))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Correo y contraseña son obligatorios.", "error")
            return render_template("login.html")

        user = db.verify_user(email, password)
        if user:
            _set_user_session(user)
            if user.get("must_change_password"):
                flash("Debes cambiar tu contraseña temporal para continuar.", "warning")
                return redirect(url_for("change_password"))

            audit_service.log_operation(
                user["email"],
                "acceso_sistema",
                f"Acceso exitoso — perfil {ROLE_LABELS.get(user['role'], user['role'])}",
            )
            flash(f"Bienvenido, {user['email']}.", "success")
            return redirect(dashboard_url_for_role(user["role"]))

        flash("Credenciales incorrectas.", "error")

    return render_template("login.html")


@app.route("/cambiar-contrasena", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        ok, message = user_service.change_password(
            session["user_db_id"],
            request.form.get("current_password", ""),
            request.form.get("new_password", ""),
            request.form.get("confirm_password", ""),
        )
        flash(message, "success" if ok else "error")
        if ok:
            session["must_change_password"] = False
            flash("Contraseña actualizada. Ya puedes usar el sistema.", "success")
            return redirect(dashboard_url_for_role(session.get("user_role")))

    return render_template("cambiar_contrasena.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(dashboard_url_for_role(session.get("user_role")))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("register.html")

        if len(username) < 3:
            flash("El usuario debe tener al menos 3 caracteres.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("register.html")

        ok, message = db.create_user(username, password, ROLES["ASOCIADO"], email=email)
        flash(message, "success" if ok else "error")
        if ok:
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
@login_required
@password_change_required
def dashboard():
    role = session.get("user_role")
    role_label = ROLE_LABELS.get(role, role)

    return render_template(
        "dashboard.html",
        username=session["user_id"],
        role_label=role_label,
    )


@app.route("/admin/usuarios", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_usuarios():
    form_data = {}
    temp_password = None

    if request.method == "POST":
        ok, message, temp_password, form_data = user_service.create_system_user(
            request.form.get("email", ""),
            request.form.get("role", ""),
        )
        if ok:
            audit_service.log_operation(
                session["user_id"],
                "creacion_usuario",
                f"Usuario {form_data.get('email')} — perfil {form_data.get('role')}",
            )
            flash(
                f"{message} Contraseña temporal: {temp_password}",
                "success",
            )
        else:
            flash(message, "error")
            temp_password = None

    return render_template(
        "admin/usuarios.html",
        users=user_service.list_system_users(),
        system_roles=SYSTEM_USER_ROLES,
        form_data=form_data,
        temp_password=temp_password,
        active_page="usuarios",
    )


@app.route("/admin/asociados", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_asociados():
    form_data = {}
    search_cedula = request.args.get("cedula", "").strip()
    found_associate = None
    status_cedula = search_cedula

    if request.method == "POST":
        action = request.form.get("action", "register")

        if action == "search":
            search_cedula = request.form.get("search_cedula", "").strip()
            status_cedula = search_cedula
            found_associate = associate_service.search_associate(search_cedula)
            if found_associate is None:
                flash("No se encontró un asociado con esa cédula.", "error")
            else:
                flash("Asociado encontrado.", "success")

        elif action == "change_status":
            status_cedula = request.form.get("status_cedula", "").strip()
            search_cedula = status_cedula
            nuevo_estado = request.form.get("estado_vinculacion", "")
            ok, message = associate_service.change_vinculation_status(
                status_cedula,
                nuevo_estado,
                session["user_id"],
            )
            flash(message, "success" if ok else "error")
            if ok or status_cedula:
                found_associate = associate_service.search_associate(status_cedula)

        else:
            ok, message, form_data = associate_service.register_associate(request.form)
            if ok:
                audit_service.log_operation(
                    session["user_id"],
                    "registro_asociado",
                    f"Asociado {form_data.get('nombre')} {form_data.get('apellido')} ({form_data.get('cedula')})",
                )
            flash(message, "success" if ok else "error")

    elif search_cedula:
        found_associate = associate_service.search_associate(search_cedula)
        status_cedula = search_cedula

    return render_template(
        "admin/asociados.html",
        associates=associate_service.list_associates(),
        tipos_asociado=TIPOS_ASOCIADO,
        estados_vinculacion=ESTADOS_VINCULACION,
        form_data=form_data,
        found_associate=found_associate,
        search_cedula=search_cedula,
        status_cedula=status_cedula,
        active_page="asociados",
    )


@app.route("/admin/estado-cartera", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_estado_cartera():
    filters = {
        "agency_codigo": "",
        "fecha_desde": "",
        "fecha_hasta": "",
    }
    report = None

    if request.method == "POST":
        filters = {
            "agency_codigo": request.form.get("agency_codigo", "").strip(),
            "fecha_desde": request.form.get("fecha_desde", "").strip(),
            "fecha_hasta": request.form.get("fecha_hasta", "").strip(),
        }
        report = portfolio_service.generate_portfolio_report(**filters)

    return render_template(
        "admin/estado_cartera.html",
        agencies=agency_service.list_agencies(),
        filters=filters,
        report=report,
        active_page="estado_cartera",
    )


@app.route("/admin/estado-cartera/exportar/csv")
@role_required(ROLES["ADMINISTRADOR"])
def admin_estado_cartera_export_csv():
    filters = {
        "agency_codigo": request.args.get("agency_codigo", "").strip(),
        "fecha_desde": request.args.get("fecha_desde", "").strip(),
        "fecha_hasta": request.args.get("fecha_hasta", "").strip(),
    }
    report = portfolio_service.generate_portfolio_report(**filters)
    csv_content = portfolio_service.export_report_csv(report)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=estado_cartera.csv",
        },
    )


@app.route("/admin/estado-cartera/exportar/pdf")
@role_required(ROLES["ADMINISTRADOR"])
def admin_estado_cartera_export_pdf():
    filters = {
        "agency_codigo": request.args.get("agency_codigo", "").strip(),
        "fecha_desde": request.args.get("fecha_desde", "").strip(),
        "fecha_hasta": request.args.get("fecha_hasta", "").strip(),
    }
    report = portfolio_service.generate_portfolio_report(**filters)
    pdf_bytes = portfolio_service.export_report_pdf(report)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=estado_cartera.pdf",
        },
    )


@app.route("/admin/bitacora", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_bitacora():
    filters = {
        "fecha_desde": "",
        "fecha_hasta": "",
        "usuario": "",
        "operacion": "",
    }
    entries = []
    filtered = False

    if request.method == "POST":
        filtered = True
        filters = {
            "fecha_desde": request.form.get("fecha_desde", "").strip(),
            "fecha_hasta": request.form.get("fecha_hasta", "").strip(),
            "usuario": request.form.get("usuario", "").strip(),
            "operacion": request.form.get("operacion", "").strip(),
        }
        entries = audit_service.query_bitacora(**filters)

    return render_template(
        "admin/bitacora.html",
        entries=entries,
        filters=filters,
        filtered=filtered,
        usuarios=audit_service.list_usuarios_bitacora(),
        operaciones=OPERACIONES_BITACORA,
        active_page="bitacora",
    )


@app.route("/admin/supervision", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_supervision():
    form_data = {}

    if request.method == "POST":
        ok, message, form_data = supervision_service.assign_supervision(request.form)
        if ok:
            audit_service.log_operation(
                session["user_id"],
                "asignacion_supervision",
                f"Supervisor {form_data.get('supervisor_cedula')} → "
                f"Empleado {form_data.get('subordinate_cedula')}",
            )
        flash(message, "success" if ok else "error")

    return render_template(
        "admin/supervision.html",
        employees=supervision_service.list_employees_for_select(),
        hierarchy=supervision_service.build_hierarchy(),
        form_data=form_data,
        active_page="supervision",
    )


@app.route("/admin/empleados", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_empleados():
    form_data = {}

    if request.method == "POST":
        ok, message, form_data = employee_service.register_employee(request.form)
        if ok:
            audit_service.log_operation(
                session["user_id"],
                "registro_empleado",
                f"Empleado {form_data.get('nombre')} ({form_data.get('cedula')}) — "
                f"agencia {form_data.get('agencia_codigo')}",
            )
        flash(message, "success" if ok else "error")

    return render_template(
        "admin/empleados.html",
        employees=employee_service.list_employees(),
        agencies=agency_service.list_agencies(),
        estados_laborales=ESTADOS_LABORALES,
        form_data=form_data,
        active_page="empleados",
    )


@app.route("/admin/agencias", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_agencias():
    form_data = {}

    if request.method == "POST":
        ok, message, form_data = agency_service.register_agency(request.form)
        if ok:
            audit_service.log_operation(
                session["user_id"],
                "registro_agencia",
                f"Agencia {form_data.get('codigo')} — {form_data.get('nombre')}",
            )
        flash(message, "success" if ok else "error")

    agencies = agency_service.list_agencies()

    return render_template(
        "admin/agencias.html",
        agencies=agencies,
        form_data=form_data,
        active_page="agencias",
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    try:
        db.init_db()
    except Exception as exc:
        print(f"Error al conectar con PostgreSQL: {exc}")
        print("Verifique que PostgreSQL esté activo y las credenciales en db_config.py o .env")
        raise SystemExit(1) from exc
    app.run(debug=True, host="127.0.0.1", port=5000)
