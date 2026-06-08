"""Lógica de negocio para el reporte de estado de cartera."""

import csv
import io
from datetime import datetime

from fpdf import FPDF

import database as db


def _normalize_filters(
    agency_codigo: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> dict:
    return {
        "agency_codigo": agency_codigo.strip().upper(),
        "fecha_desde": fecha_desde.strip(),
        "fecha_hasta": fecha_hasta.strip(),
    }


def generate_portfolio_report(
    agency_codigo: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
) -> dict:
    filters = _normalize_filters(agency_codigo, fecha_desde, fecha_hasta)
    raw_groups = db.get_portfolio_report(
        agency_codigo=filters["agency_codigo"] or None,
        fecha_desde=filters["fecha_desde"] or None,
        fecha_hasta=filters["fecha_hasta"] or None,
    )

    total_valor = sum(float(group["valor_total"]) for group in raw_groups)
    total_creditos = sum(int(group["num_creditos"]) for group in raw_groups)

    groups = []
    for group in raw_groups:
        valor = float(group["valor_total"])
        porcentaje = (valor / total_valor * 100) if total_valor > 0 else 0
        groups.append({
            "linea_credito": group["linea_credito"],
            "estado": group["estado"],
            "num_creditos": int(group["num_creditos"]),
            "valor_total": valor,
            "porcentaje": round(porcentaje, 2),
        })

    return {
        "filters": filters,
        "groups": groups,
        "total_valor": total_valor,
        "total_creditos": total_creditos,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def export_report_csv(report: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Línea de crédito",
        "Estado",
        "Número de créditos",
        "Valor total aprobado",
        "Porcentaje (%)",
    ])

    for group in report["groups"]:
        writer.writerow([
            group["linea_credito"],
            group["estado"],
            group["num_creditos"],
            f"{group['valor_total']:.2f}",
            f"{group['porcentaje']:.2f}",
        ])

    writer.writerow([])
    writer.writerow([
        "TOTAL",
        "",
        report["total_creditos"],
        f"{report['total_valor']:.2f}",
        "100.00" if report["total_valor"] > 0 else "0.00",
    ])

    return output.getvalue()


def export_report_pdf(report: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "COOVALLUNA - Estado de cartera", ln=True)
    pdf.set_font("Helvetica", "", 10)

    filters = report["filters"]
    filter_text = "Filtros: "
    parts = []
    if filters["agency_codigo"]:
        parts.append(f"Agencia {filters['agency_codigo']}")
    if filters["fecha_desde"]:
        parts.append(f"Desde {filters['fecha_desde']}")
    if filters["fecha_hasta"]:
        parts.append(f"Hasta {filters['fecha_hasta']}")
    filter_text += ", ".join(parts) if parts else "Ninguno"
    pdf.cell(0, 8, filter_text, ln=True)
    pdf.cell(0, 8, f"Generado: {report['generated_at']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 9)
    col_widths = [40, 30, 35, 45, 30]
    headers = ["Línea", "Estado", "Créditos", "Valor total", "%"]
    for index, header in enumerate(headers):
        pdf.cell(col_widths[index], 8, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for group in report["groups"]:
        pdf.cell(col_widths[0], 8, group["linea_credito"][:18], border=1)
        pdf.cell(col_widths[1], 8, group["estado"][:14], border=1)
        pdf.cell(col_widths[2], 8, str(group["num_creditos"]), border=1)
        pdf.cell(col_widths[3], 8, f"${group['valor_total']:,.0f}", border=1)
        pdf.cell(col_widths[4], 8, f"{group['porcentaje']:.2f}%", border=1)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(col_widths[0], 8, "TOTAL", border=1)
    pdf.cell(col_widths[1], 8, "", border=1)
    pdf.cell(col_widths[2], 8, str(report["total_creditos"]), border=1)
    pdf.cell(col_widths[3], 8, f"${report['total_valor']:,.0f}", border=1)
    pdf.cell(col_widths[4], 8, "100%" if report["total_valor"] > 0 else "0%", border=1)

    return pdf.output()
