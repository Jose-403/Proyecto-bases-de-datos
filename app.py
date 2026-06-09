import os
from functools import wraps

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

from config import (
    CANALES_MOVIMIENTO,
    ESTADOS_LABORALES,
    ESTADOS_VINCULACION,
    LINEAS_CREDITO,
    MAX_BENEFICIARIOS_POR_ASOCIADO,
    OPERACIONES_BITACORA,
    PARENTESCOS_BENEFICIARIO,
    ROLE_LABELS,
    ROLES,
    SYSTEM_USER_ROLES,
    TIPOS_ASOCIADO,
    TIPOS_MOVIMIENTO_ASESOR,
    TIPOS_MOVIMIENTO_EXTRACTO,
)
import database as db
from services import (
    agency_service,
    associate_credit_service,
    associate_export_service,
    associate_service,
    audit_service,
    beneficiary_service,
    credit_service,
    data_update_service,
    delinquency_service,
    employee_service,
    movement_service,
    payment_service,
    portfolio_service,
    reports_service,
    savings_account_service,
    statement_service,
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
    if role == ROLES["ASESOR"]:
        return url_for("asesor_registrar_asociado")
    if role == ROLES["ASOCIADO"]:
        return url_for("asociado_mis_ahorros")
    return url_for("dashboard")


def _set_user_session(user: dict):
    session["user_id"] = user["email"]
    session["user_role"] = user["role"]
    session["user_db_id"] = user["id"]
    session["must_change_password"] = user.get("must_change_password", False)
    employee = db.get_employee_by_email(user["email"])
    session["agencia_codigo"] = employee["codigo_agencia"] if employee else None
    session["cedula_empleado"] = employee["cedula_empleado"] if employee else None
    session["cedula_asociado"] = (
        db.get_associate_cedula_by_email(user["email"])
        if user.get("role") == ROLES["ASOCIADO"]
        else None
    )


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
            if user["role"] == ROLES["ASOCIADO"]:
                _flash_associate_notifications(session.get("cedula_asociado"))
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


@app.route("/admin/reporte-asociados", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_reporte_asociados():
    filters = {
        "estado": "",
        "codigo_agencia": "",
    }
    report = None

    if request.method == "POST":
        filters = {
            "estado": request.form.get("estado", "").strip(),
            "codigo_agencia": request.form.get("codigo_agencia", "").strip(),
        }
        report = reports_service.generate_associates_report(**filters)
        if report.get("error"):
            flash(report["error"], "warning")

    return render_template(
        "admin/reporte_asociados.html",
        agencies=agency_service.list_agencies(),
        estados_vinculacion=ESTADOS_VINCULACION,
        filters=filters,
        report=report,
        active_page="reporte_asociados",
    )


@app.route("/admin/reporte-asociados/exportar/csv")
@role_required(ROLES["ADMINISTRADOR"])
def admin_reporte_asociados_export_csv():
    filters = {
        "estado": request.args.get("estado", "").strip(),
        "codigo_agencia": request.args.get("codigo_agencia", "").strip(),
    }
    report = reports_service.generate_associates_report(**filters)
    if report.get("error"):
        flash(report["error"], "warning")
        return redirect(url_for("admin_reporte_asociados"))

    return Response(
        reports_service.export_associates_csv(report),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=asociados_por_estado_agencia.csv",
        },
    )


@app.route("/admin/reporte-asociados/exportar/pdf")
@role_required(ROLES["ADMINISTRADOR"])
def admin_reporte_asociados_export_pdf():
    filters = {
        "estado": request.args.get("estado", "").strip(),
        "codigo_agencia": request.args.get("codigo_agencia", "").strip(),
    }
    report = reports_service.generate_associates_report(**filters)
    if report.get("error"):
        flash(report["error"], "warning")
        return redirect(url_for("admin_reporte_asociados"))

    return Response(
        reports_service.export_associates_pdf(report),
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=asociados_por_estado_agencia.pdf",
        },
    )


@app.route("/admin/productividad-asesores", methods=["GET", "POST"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_productividad_asesores():
    filters = {
        "codigo_agencia": "",
        "fecha_desde": "",
        "fecha_hasta": "",
    }
    report = None

    if request.method == "POST":
        filters = {
            "codigo_agencia": request.form.get("codigo_agencia", "").strip(),
            "fecha_desde": request.form.get("fecha_desde", "").strip(),
            "fecha_hasta": request.form.get("fecha_hasta", "").strip(),
        }
        report = reports_service.generate_advisor_productivity_report(**filters)

    return render_template(
        "admin/productividad_asesores.html",
        agencies=agency_service.list_agencies(),
        filters=filters,
        report=report,
        active_page="productividad_asesores",
    )


@app.route("/admin/productividad-asesores/exportar/csv")
@role_required(ROLES["ADMINISTRADOR"])
def admin_productividad_asesores_export_csv():
    filters = {
        "codigo_agencia": request.args.get("codigo_agencia", "").strip(),
        "fecha_desde": request.args.get("fecha_desde", "").strip(),
        "fecha_hasta": request.args.get("fecha_hasta", "").strip(),
    }
    report = reports_service.generate_advisor_productivity_report(**filters)

    return Response(
        reports_service.export_productivity_csv(report),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=productividad_asesores.csv",
        },
    )


@app.route("/admin/codeudoria-activa", methods=["GET"])
@role_required(ROLES["ADMINISTRADOR"])
def admin_codeudoria_activa():
    report = reports_service.generate_cosigner_report()

    return render_template(
        "admin/codeudoria_activa.html",
        report=report,
        active_page="codeudoria_activa",
    )


@app.route("/admin/codeudoria-activa/exportar/csv")
@role_required(ROLES["ADMINISTRADOR"])
def admin_codeudoria_activa_export_csv():
    report = reports_service.generate_cosigner_report()

    return Response(
        reports_service.export_cosigner_csv(report),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=codeudoria_activa.csv",
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


@app.route("/asesor/beneficiarios/registrar", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_registrar_beneficiario():
    form_data = {"cedula_asociado": request.args.get("cedula_asociado", "").strip()}
    found_associate = None
    existing_beneficiaries = []

    if request.method == "POST":
        action = request.form.get("action", "register")

        if action == "search":
            form_data = {"cedula_asociado": request.form.get("cedula_asociado", "").strip()}
            found_associate = associate_service.search_associate(form_data["cedula_asociado"])
            if found_associate is None:
                flash("No se encontró un asociado con esa cédula.", "error")
            else:
                existing_beneficiaries = beneficiary_service.get_associate_beneficiaries(
                    form_data["cedula_asociado"]
                )
                flash("Asociado encontrado.", "success")
        else:
            ok, message, form_data = beneficiary_service.register_beneficiaries(request.form)
            if ok:
                audit_service.log_operation(
                    session["user_id"],
                    "registro_beneficiarios",
                    f"Asociado {form_data.get('cedula_asociado')} — beneficiarios registrados",
                )
            flash(message, "success" if ok else "error")
            if form_data.get("cedula_asociado"):
                found_associate = associate_service.search_associate(form_data["cedula_asociado"])
                existing_beneficiaries = beneficiary_service.get_associate_beneficiaries(
                    form_data["cedula_asociado"]
                )

    elif form_data.get("cedula_asociado"):
        found_associate = associate_service.search_associate(form_data["cedula_asociado"])
        existing_beneficiaries = beneficiary_service.get_associate_beneficiaries(
            form_data["cedula_asociado"]
        )

    return render_template(
        "asesor/registrar_beneficiario.html",
        form_data=form_data,
        found_associate=found_associate,
        existing_beneficiaries=existing_beneficiaries,
        parentescos=PARENTESCOS_BENEFICIARIO,
        max_beneficiarios=MAX_BENEFICIARIOS_POR_ASOCIADO,
        active_page="registrar_beneficiario",
    )


@app.route("/asesor/solicitudes-datos", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_solicitudes_datos():
    cedula_empleado = session.get("cedula_empleado")
    employee = db.get_employee_by_email(session.get("user_id", ""))

    if request.method == "POST":
        try:
            id_solicitud = int(request.form.get("id_solicitud", "0"))
        except ValueError:
            id_solicitud = 0

        ok, message = data_update_service.process_request(
            id_solicitud,
            request.form.get("action", ""),
            cedula_empleado,
            request.form,
            session.get("user_id", ""),
        )
        flash(message, "success" if ok else "error")

    pending_requests = data_update_service.list_pending_requests_for_advisor(cedula_empleado)

    return render_template(
        "asesor/solicitudes_datos.html",
        pending_requests=pending_requests,
        employee=employee,
        active_page="solicitudes_datos",
    )


@app.route("/asesor/creditos/radicar", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_radicar_credito():
    form_data = {"cedula_asociado": request.args.get("cedula_asociado", "").strip()}
    found_associate = None
    associate_credits = []

    if request.method == "POST":
        action = request.form.get("action", "register")

        if action == "search":
            form_data = {
                "cedula_asociado": request.form.get("cedula_asociado", "").strip(),
                "codigo_agencia": request.form.get("codigo_agencia", "").strip().upper(),
                "linea_credito": request.form.get("linea_credito", "").strip(),
                "vlr_solicitado": request.form.get("vlr_solicitado", "").strip(),
                "vlr_aprobado": request.form.get("vlr_aprobado", "").strip(),
                "tasa_interes": request.form.get("tasa_interes", "").strip(),
                "plazo_meses": request.form.get("plazo_meses", "").strip(),
                "fecha_primer_vencimiento": request.form.get("fecha_primer_vencimiento", "").strip(),
                "cedula_codeudor": request.form.get("cedula_codeudor", "").strip(),
                "fecha_firma_codeudor": request.form.get("fecha_firma_codeudor", "").strip(),
            }
            found_associate = associate_service.search_associate(form_data["cedula_asociado"])
            if found_associate is None:
                flash("No se encontró un asociado con esa cédula.", "error")
            else:
                associate_credits = credit_service.list_associate_credits(form_data["cedula_asociado"])
                flash("Asociado encontrado.", "success")
        else:
            ok, message, form_data, numero_radicado = credit_service.register_credit_application(
                request.form
            )
            if ok:
                audit_service.log_operation(
                    session["user_id"],
                    "radicacion_credito",
                    f"Crédito {numero_radicado} — asociado {form_data.get('cedula_asociado')} "
                    f"— ${form_data.get('vlr_aprobado')} — tasa {form_data.get('tasa_interes')}% "
                    f"— plazo {form_data.get('plazo_meses')} meses",
                )
            flash(message, "success" if ok else "error")
            if form_data.get("cedula_asociado"):
                found_associate = associate_service.search_associate(form_data["cedula_asociado"])
                associate_credits = credit_service.list_associate_credits(form_data["cedula_asociado"])

    elif form_data.get("cedula_asociado"):
        found_associate = associate_service.search_associate(form_data["cedula_asociado"])
        associate_credits = credit_service.list_associate_credits(form_data["cedula_asociado"])

    return render_template(
        "asesor/radicar_credito.html",
        form_data=form_data,
        found_associate=found_associate,
        associate_credits=associate_credits,
        lineas_credito=LINEAS_CREDITO,
        agencies=agency_service.list_agencies(),
        active_page="radicar_credito",
    )


@app.route("/asesor/asociados-mora")
@role_required(ROLES["ASESOR"])
def asesor_asociados_mora():
    ok, message, overdue_list, employee = delinquency_service.list_overdue_associates(
        session.get("user_id", "")
    )

    if not ok:
        flash(message, "error")

    return render_template(
        "asesor/asociados_mora.html",
        overdue_list=overdue_list,
        employee=employee,
        active_page="asociados_mora",
    )


@app.route("/asesor/extracto-cuenta", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_extracto_cuenta():
    asesor_agencia = session.get("agencia_codigo")
    form_data = {
        "numero_cuenta": request.args.get("numero_cuenta", "").strip().upper(),
        "fecha_desde": "",
        "fecha_hasta": "",
        "tipo_movimiento": "",
        "canal": "",
    }
    statement = None

    if request.method == "POST":
        form_data = {
            "numero_cuenta": request.form.get("numero_cuenta", "").strip().upper(),
            "fecha_desde": request.form.get("fecha_desde", "").strip(),
            "fecha_hasta": request.form.get("fecha_hasta", "").strip(),
            "tipo_movimiento": request.form.get("tipo_movimiento", "").strip(),
            "canal": request.form.get("canal", "").strip(),
        }
        ok, message, statement = statement_service.generate_account_statement(
            form_data,
            asesor_agencia,
        )
        flash(message, "success" if ok else "error")

    agency_accounts = statement_service.list_agency_accounts(asesor_agencia)

    return render_template(
        "asesor/extracto_cuenta.html",
        form_data=form_data,
        statement=statement,
        agency_accounts=agency_accounts,
        asesor_agencia=asesor_agencia,
        tipos_movimiento=TIPOS_MOVIMIENTO_EXTRACTO,
        canales_movimiento=CANALES_MOVIMIENTO,
        active_page="extracto_cuenta",
    )


@app.route("/asociado/mis-ahorros", methods=["GET", "POST"])
@role_required(ROLES["ASOCIADO"])
def asociado_mis_ahorros():
    cedula_asociado = session.get("cedula_asociado")
    _flash_associate_notifications(cedula_asociado)
    associate_accounts = statement_service.list_associate_accounts(cedula_asociado)
    form_data = {
        "numero_cuenta": request.args.get("numero_cuenta", "").strip().upper(),
        "fecha_desde": "",
        "fecha_hasta": "",
    }
    statement = None
    saldo_actual = None

    if not form_data["numero_cuenta"] and associate_accounts:
        form_data["numero_cuenta"] = associate_accounts[0]["numero_cuenta"]

    if request.method == "POST":
        form_data = {
            "numero_cuenta": request.form.get("numero_cuenta", "").strip().upper(),
            "fecha_desde": request.form.get("fecha_desde", "").strip(),
            "fecha_hasta": request.form.get("fecha_hasta", "").strip(),
        }
        ok, message, statement = statement_service.generate_associate_account_statement(
            form_data,
            cedula_asociado,
        )
        flash(message, "success" if ok else "error")
        if statement:
            saldo_actual = statement["saldo_actual"]
    elif form_data["numero_cuenta"]:
        ok, message, statement = statement_service.generate_associate_account_statement(
            form_data,
            cedula_asociado,
            include_movements=False,
        )
        if ok and statement:
            saldo_actual = statement["saldo_actual"]
        elif not ok:
            flash(message, "error")

    associate = associate_service.search_associate(cedula_asociado) if cedula_asociado else None

    return render_template(
        "asociado/mis_ahorros.html",
        form_data=form_data,
        statement=statement,
        saldo_actual=saldo_actual,
        associate_accounts=associate_accounts,
        associate=associate,
        active_page="mis_ahorros",
    )


@app.route("/asociado/mis-creditos")
@role_required(ROLES["ASOCIADO"])
def asociado_mis_creditos():
    cedula_asociado = session.get("cedula_asociado")
    _flash_associate_notifications(cedula_asociado)
    selected_radicado = request.args.get("numero_radicado", "").strip().upper()
    credit_plan = None

    ok, message, active_credits = associate_credit_service.list_active_credits(cedula_asociado)
    if not ok:
        flash(message, "error")
        active_credits = []

    if not selected_radicado and active_credits:
        selected_radicado = active_credits[0]["numero_radicado"]

    if selected_radicado:
        ok_plan, message_plan, credit_plan = associate_credit_service.get_credit_payment_plan(
            cedula_asociado,
            selected_radicado,
        )
        if not ok_plan:
            flash(message_plan, "error")

    associate = associate_service.search_associate(cedula_asociado) if cedula_asociado else None

    return render_template(
        "asociado/mis_creditos.html",
        active_credits=active_credits,
        credit_plan=credit_plan,
        selected_radicado=selected_radicado,
        associate=associate,
        active_page="mis_creditos",
    )


def _associate_export_params() -> dict:
    return {
        "tipo_documento": request.args.get("tipo_documento", "ahorro").strip().lower(),
        "numero_cuenta": request.args.get("numero_cuenta", "").strip().upper(),
        "numero_radicado": request.args.get("numero_radicado", "").strip().upper(),
        "fecha_desde": request.args.get("fecha_desde", "").strip(),
        "fecha_hasta": request.args.get("fecha_hasta", "").strip(),
    }


def _flash_associate_notifications(cedula_asociado: str | None) -> None:
    for message in data_update_service.notify_processed_requests(cedula_asociado):
        flash(message, "success" if "aprobada" in message else "warning")


def _record_associate_download(report: dict, formato: str) -> None:
    history = session.get("download_history", [])
    history.insert(
        0,
        {
            "fecha": report["generated_at"],
            "documento": report["document_type"],
            "referencia": report["reference"],
            "periodo": report["period_label"],
            "formato": formato,
        },
    )
    session["download_history"] = history[:10]


@app.route("/asociado/actualizar-datos", methods=["GET", "POST"])
@role_required(ROLES["ASOCIADO"])
def asociado_actualizar_datos():
    cedula_asociado = session.get("cedula_asociado")
    _flash_associate_notifications(cedula_asociado)

    associate = associate_service.search_associate(cedula_asociado) if cedula_asociado else None
    form_data = {
        "telefono": associate["telefono"] if associate else "",
        "correo": associate["email"] if associate else "",
        "direccion": associate["direccion"] if associate else "",
    }
    has_pending = (
        db.has_pending_data_update_request(cedula_asociado) if cedula_asociado else False
    )

    if request.method == "POST":
        form_data = {
            "telefono": request.form.get("telefono", "").strip(),
            "correo": request.form.get("correo", "").strip(),
            "direccion": request.form.get("direccion", "").strip(),
        }
        ok, message, form_data = data_update_service.submit_update_request(
            cedula_asociado,
            form_data,
            session.get("user_id", ""),
        )
        flash(message, "success" if ok else "error")
        if ok:
            has_pending = True

    requests = data_update_service.list_associate_requests(cedula_asociado)

    return render_template(
        "asociado/actualizar_datos.html",
        associate=associate,
        form_data=form_data,
        requests=requests,
        has_pending=has_pending,
        active_page="actualizar_datos",
    )


@app.route("/asociado/descargar-extractos")
@role_required(ROLES["ASOCIADO"])
def asociado_descargar_extractos():
    cedula_asociado = session.get("cedula_asociado")
    _flash_associate_notifications(cedula_asociado)
    associate_accounts = statement_service.list_associate_accounts(cedula_asociado)
    _, _, active_credits = associate_credit_service.list_active_credits(cedula_asociado)
    associate = associate_service.search_associate(cedula_asociado) if cedula_asociado else None

    form_data = {
        "tipo_documento": request.args.get("tipo_documento", "ahorro").strip().lower(),
        "numero_cuenta": request.args.get("numero_cuenta", "").strip().upper(),
        "numero_radicado": request.args.get("numero_radicado", "").strip().upper(),
        "fecha_desde": request.args.get("fecha_desde", "").strip(),
        "fecha_hasta": request.args.get("fecha_hasta", "").strip(),
    }

    if not form_data["numero_cuenta"] and associate_accounts:
        form_data["numero_cuenta"] = associate_accounts[0]["numero_cuenta"]
    if not form_data["numero_radicado"] and active_credits:
        form_data["numero_radicado"] = active_credits[0]["numero_radicado"]

    return render_template(
        "asociado/descargar_extractos.html",
        form_data=form_data,
        associate_accounts=associate_accounts,
        active_credits=active_credits,
        associate=associate,
        download_history=session.get("download_history", []),
        active_page="descargar_extractos",
    )


@app.route("/asociado/descargar-extractos/csv")
@role_required(ROLES["ASOCIADO"])
def asociado_descargar_extracto_csv():
    params = _associate_export_params()
    ok, message, report = associate_export_service.build_report(
        session.get("cedula_asociado"),
        params,
    )
    if not ok or report is None:
        flash(message, "error")
        return redirect(url_for("asociado_descargar_extractos", **params))

    _record_associate_download(report, "CSV")
    csv_content = associate_export_service.export_csv(report)
    filename = associate_export_service.build_filename(report, "csv")

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/asociado/descargar-extractos/pdf")
@role_required(ROLES["ASOCIADO"])
def asociado_descargar_extracto_pdf():
    params = _associate_export_params()
    ok, message, report = associate_export_service.build_report(
        session.get("cedula_asociado"),
        params,
    )
    if not ok or report is None:
        flash(message, "error")
        return redirect(url_for("asociado_descargar_extractos", **params))

    _record_associate_download(report, "PDF")
    pdf_bytes = associate_export_service.export_pdf(report)
    filename = associate_export_service.build_filename(report, "pdf")

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/asesor/pagos-cuotas", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_pagos_cuotas():
    form_data = {"numero_radicado": request.args.get("numero_radicado", "").strip().upper()}
    credit_summary = None

    if request.method == "POST":
        action = request.form.get("action", "register")

        if action == "search":
            form_data = {
                "numero_radicado": request.form.get("numero_radicado", "").strip().upper(),
                "numero_cuota": request.form.get("numero_cuota", "").strip(),
                "valor_pagado": request.form.get("valor_pagado", "").strip(),
                "fecha_pago": request.form.get("fecha_pago", "").strip(),
            }
            credit_summary = payment_service.get_credit_payment_summary(form_data["numero_radicado"])
            if credit_summary is None:
                flash("No se encontró el crédito indicado.", "error")
            else:
                flash("Crédito consultado.", "success")
        else:
            ok, message, form_data, id_pago = payment_service.register_installment_payment(
                request.form
            )
            if ok:
                audit_service.log_operation(
                    session["user_id"],
                    "registro_pago_cuota",
                    f"Pago {id_pago} — crédito {form_data.get('numero_radicado')} "
                    f"cuota {form_data.get('numero_cuota')} — ${form_data.get('valor_pagado')} "
                    f"— {form_data.get('estado_pago')}",
                )
            flash(message, "success" if ok else "error")
            if form_data.get("numero_radicado"):
                credit_summary = payment_service.get_credit_payment_summary(
                    form_data["numero_radicado"]
                )

    elif form_data.get("numero_radicado"):
        credit_summary = payment_service.get_credit_payment_summary(form_data["numero_radicado"])

    return render_template(
        "asesor/pagos_cuotas.html",
        form_data=form_data,
        credit_summary=credit_summary,
        credits_with_plan=db.get_credits_with_installments(),
        active_page="pagos_cuotas",
    )


@app.route("/asesor/movimientos", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_movimientos():
    form_data = {"numero_cuenta": request.args.get("numero_cuenta", "").strip().upper()}
    account_summary = None

    if request.method == "POST":
        action = request.form.get("action", "register")

        if action == "search":
            form_data = {
                "numero_cuenta": request.form.get("numero_cuenta", "").strip().upper(),
                "tipo_movimiento": request.form.get("tipo_movimiento", "").strip(),
                "valor": request.form.get("valor", "").strip(),
                "fecha_movimiento": request.form.get("fecha_movimiento", "").strip(),
                "hora_movimiento": request.form.get("hora_movimiento", "").strip(),
                "cuenta_contraparte": request.form.get("cuenta_contraparte", "").strip().upper(),
                "canal": request.form.get("canal", "").strip(),
            }
            account_summary = movement_service.get_account_summary(form_data["numero_cuenta"])
            if account_summary is None:
                flash("No se encontró la cuenta o no está activa.", "error")
            else:
                flash("Cuenta consultada. Saldo calculado dinámicamente.", "success")
        else:
            ok, message, form_data, numero_transaccion = movement_service.register_movement(
                request.form
            )
            if ok:
                audit_service.log_operation(
                    session["user_id"],
                    "registro_movimiento",
                    f"Transacción {numero_transaccion} — cuenta {form_data.get('numero_cuenta')} "
                    f"— {form_data.get('tipo_movimiento')} ${form_data.get('valor')}",
                )
            flash(message, "success" if ok else "error")
            if form_data.get("numero_cuenta"):
                account_summary = movement_service.get_account_summary(form_data["numero_cuenta"])

    elif form_data.get("numero_cuenta"):
        account_summary = movement_service.get_account_summary(form_data["numero_cuenta"])

    return render_template(
        "asesor/movimientos.html",
        form_data=form_data,
        account_summary=account_summary,
        tipos_movimiento=TIPOS_MOVIMIENTO_ASESOR,
        canales_movimiento=CANALES_MOVIMIENTO,
        active_accounts=db.get_active_savings_accounts(),
        active_page="movimientos",
    )


@app.route("/asesor/cuentas-ahorro", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_cuentas_ahorro():
    form_data = {"cedula_asociado": request.args.get("cedula_asociado", "").strip()}
    found_associate = None
    registered_accounts = []

    if request.method == "POST":
        action = request.form.get("action", "open")

        if action == "search":
            form_data = {
                "cedula_asociado": request.form.get("cedula_asociado", "").strip(),
                "codigo_agencia": request.form.get("codigo_agencia", "").strip().upper(),
                "fecha_apertura": request.form.get("fecha_apertura", "").strip(),
            }
            found_associate = associate_service.search_associate(form_data["cedula_asociado"])
            if found_associate is None:
                flash("No se encontró un asociado con esa cédula.", "error")
            else:
                registered_accounts = savings_account_service.list_associate_accounts(
                    form_data["cedula_asociado"]
                )
                flash("Asociado encontrado.", "success")
        else:
            ok, message, form_data, numero_cuenta = savings_account_service.open_savings_account(
                request.form
            )
            if ok:
                audit_service.log_operation(
                    session["user_id"],
                    "apertura_cuenta_ahorro",
                    f"Cuenta {numero_cuenta} — asociado {form_data.get('cedula_asociado')} "
                    f"— agencia {form_data.get('codigo_agencia')}",
                )
            flash(message, "success" if ok else "error")
            if form_data.get("cedula_asociado"):
                found_associate = associate_service.search_associate(form_data["cedula_asociado"])
                registered_accounts = savings_account_service.list_associate_accounts(
                    form_data["cedula_asociado"]
                )

    elif form_data.get("cedula_asociado"):
        found_associate = associate_service.search_associate(form_data["cedula_asociado"])
        registered_accounts = savings_account_service.list_associate_accounts(
            form_data["cedula_asociado"]
        )

    return render_template(
        "asesor/cuentas_ahorro.html",
        form_data=form_data,
        found_associate=found_associate,
        registered_accounts=registered_accounts,
        agencies=agency_service.list_agencies(),
        active_page="cuentas_ahorro",
    )


@app.route("/asesor/asociados/registrar", methods=["GET", "POST"])
@role_required(ROLES["ASESOR"])
def asesor_registrar_asociado():
    form_data = {}

    if request.method == "POST":
        ok, message, form_data = associate_service.register_associate_by_asesor(request.form)
        if ok:
            audit_service.log_operation(
                session["user_id"],
                "registro_asociado",
                f"Asociado {form_data.get('nombre')} {form_data.get('apellido')} "
                f"({form_data.get('cedula')}) — estado activo",
            )
        flash(message, "success" if ok else "error")

    return render_template(
        "asesor/registrar_asociado.html",
        form_data=form_data,
        active_page="registrar_asociado",
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
