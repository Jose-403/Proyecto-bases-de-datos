"""Reportes administrativos adicionales."""

import csv
import io
from datetime import datetime

from fpdf import FPDF

from config import ESTADOS_VINCULACION
from db_mappers import ESTADOS_CREDITO_LABELS
import database as db

COOPERATIVE_NAME = "COOVALLUNA"


def _normalize_associate_filters(
    estado: str = "",
    codigo_agencia: str = "",
) -> dict:
    return {
        "estado": estado.strip().lower(),
        "codigo_agencia": codigo_agencia.strip().upper(),
    }


def _normalize_productivity_filters(
    codigo_agencia: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> dict:
    return {
        "codigo_agencia": codigo_agencia.strip().upper(),
        "fecha_desde": fecha_desde.strip(),
        "fecha_hasta": fecha_hasta.strip(),
    }


def generate_associates_report(estado: str = "", codigo_agencia: str = "") -> dict:
    filters = _normalize_associate_filters(estado, codigo_agencia)
    if filters["estado"] and filters["estado"] not in ESTADOS_VINCULACION:
        return {"filters": filters, "rows": [], "error": "El estado seleccionado no es válido."}

    rows = db.get_associates_by_status_agency_report(
        estado=filters["estado"] or None,
        codigo_agencia=filters["codigo_agencia"] or None,
    )
    for row in rows:
        row["estado_label"] = ESTADOS_VINCULACION.get(row["estado"], row["estado"])
        row["tipo_label"] = "Fundador" if row["tipo_asociado"] == "fundador" else "Regular"
        row["fecha_ingreso"] = str(row["fecha_ingreso"])

    return {
        "filters": filters,
        "rows": rows,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_advisor_productivity_report(
    codigo_agencia: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> dict:
    filters = _normalize_productivity_filters(codigo_agencia, fecha_desde, fecha_hasta)
    rows = db.get_advisor_productivity_report(
        codigo_agencia=filters["codigo_agencia"] or None,
        fecha_desde=filters["fecha_desde"] or None,
        fecha_hasta=filters["fecha_hasta"] or None,
    )
    for row in rows:
        row["valor_total_creditos"] = float(row["valor_total_creditos"] or 0)
        row["nombre_completo"] = f"{row['primer_nombre']} {row['apellido']}".strip()

    return {
        "filters": filters,
        "rows": rows,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_cosigner_report() -> dict:
    rows = db.get_active_cosigner_report()
    for row in rows:
        row["vlr_aprobado"] = float(row["vlr_aprobado"])
        row["fecha_firma"] = str(row["fecha_firma"])
        row["estado_label"] = ESTADOS_CREDITO_LABELS.get(
            row["estado_credito"],
            row["estado_credito"],
        )
        row["titular_nombre"] = (
            f"{row['titular_primer_nombre']} {row['titular_apellido']}".strip()
        )
        row["codeudor_nombre"] = (
            f"{row['codeudor_primer_nombre']} {row['codeudor_apellido']}".strip()
        )

    return {
        "rows": rows,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def export_associates_csv(report: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([COOPERATIVE_NAME, "Listado de asociados por estado y agencia"])
    writer.writerow(["Generado", report["generated_at"]])
    filters = report["filters"]
    writer.writerow(["Estado", filters["estado"] or "Todos"])
    writer.writerow(["Agencia", filters["codigo_agencia"] or "Todas"])
    writer.writerow([])
    writer.writerow([
        "Cédula",
        "Nombre",
        "Apellido",
        "Estado",
        "Fecha afiliación",
        "Tipo",
        "Nº cuentas",
        "Nº créditos",
    ])
    for row in report["rows"]:
        writer.writerow([
            row["cedula_asociado"],
            row["primer_nombre"],
            row["apellido"],
            row["estado_label"],
            row["fecha_ingreso"],
            row["tipo_label"],
            row["nro_cuentas"],
            row["nro_creditos"],
        ])
    return output.getvalue()


def export_productivity_csv(report: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([COOPERATIVE_NAME, "Productividad de asesores por agencia"])
    writer.writerow(["Generado", report["generated_at"]])
    filters = report["filters"]
    writer.writerow(["Agencia", filters["codigo_agencia"] or "Todas"])
    writer.writerow(["Desde", filters["fecha_desde"] or "—"])
    writer.writerow(["Hasta", filters["fecha_hasta"] or "—"])
    writer.writerow([])
    writer.writerow([
        "Cédula",
        "Asesor",
        "Agencia",
        "Asociados atendidos",
        "Créditos radicados",
        "Valor total créditos",
    ])
    for row in report["rows"]:
        writer.writerow([
            row["cedula_empleado"],
            row["nombre_completo"],
            row["agencia_nombre"],
            row["asociados_atendidos"],
            row["creditos_radicados"],
            f"{row['valor_total_creditos']:.2f}",
        ])
    return output.getvalue()


def export_cosigner_csv(report: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([COOPERATIVE_NAME, "Asociados con codeudoría activa"])
    writer.writerow(["Generado", report["generated_at"]])
    writer.writerow([])
    writer.writerow([
        "Cédula titular",
        "Titular",
        "Cédula codeudor",
        "Codeudor",
        "Radicado",
        "Valor aprobado",
        "Estado crédito",
        "Fecha firma",
    ])
    for row in report["rows"]:
        writer.writerow([
            row["cedula_titular"],
            row["titular_nombre"],
            row["cedula_codeudor"],
            row["codeudor_nombre"],
            row["numero_radicado"],
            f"{row['vlr_aprobado']:.2f}",
            row["estado_label"],
            row["fecha_firma"],
        ])
    return output.getvalue()


def export_associates_pdf(report: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"{COOPERATIVE_NAME} - Asociados por estado y agencia", ln=True)
    pdf.set_font("Helvetica", "", 10)
    filters = report["filters"]
    pdf.cell(0, 8, f"Estado: {filters['estado'] or 'Todos'}", ln=True)
    pdf.cell(0, 8, f"Agencia: {filters['codigo_agencia'] or 'Todas'}", ln=True)
    pdf.cell(0, 8, f"Generado: {report['generated_at']}", ln=True)
    pdf.ln(4)

    col_widths = [22, 28, 28, 18, 22, 16, 14, 14]
    headers = ["Cédula", "Nombre", "Apellido", "Estado", "Afiliación", "Tipo", "Ctas", "Créd"]
    pdf.set_font("Helvetica", "B", 7)
    for index, header in enumerate(headers):
        pdf.cell(col_widths[index], 8, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for row in report["rows"]:
        pdf.cell(col_widths[0], 8, row["cedula_asociado"][:10], border=1)
        pdf.cell(col_widths[1], 8, row["primer_nombre"][:14], border=1)
        pdf.cell(col_widths[2], 8, row["apellido"][:14], border=1)
        pdf.cell(col_widths[3], 8, row["estado"][:10], border=1)
        pdf.cell(col_widths[4], 8, row["fecha_ingreso"], border=1)
        pdf.cell(col_widths[5], 8, row["tipo_asociado"][:8], border=1)
        pdf.cell(col_widths[6], 8, str(row["nro_cuentas"]), border=1)
        pdf.cell(col_widths[7], 8, str(row["nro_creditos"]), border=1)
        pdf.ln()

    return pdf.output()
