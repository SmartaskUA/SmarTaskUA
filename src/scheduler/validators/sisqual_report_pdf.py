from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def write_pdf_report(path: Path, report: dict[str, Any]) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
            wordWrap="CJK",
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6B7280"),
            wordWrap="CJK",
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#111827"),
            spaceBefore=10,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#374151"),
            wordWrap="CJK",
        )
        muted_style = ParagraphStyle(
            "Muted",
            parent=body_style,
            textColor=colors.HexColor("#6B7280"),
        )
        label_style = ParagraphStyle(
            "Label",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
        )
        issue_title_style = ParagraphStyle(
            "IssueTitle",
            parent=body_style,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#111827"),
            wordWrap="CJK",
        )

        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=18 * mm,
            bottomMargin=16 * mm,
            title=f"Sisqual Feasibility Report - {report.get('taskId')}",
            author="SmarTaskUA",
        )
        story = []

        status = report.get("status") or "UNKNOWN"
        status_color = colors.HexColor("#DC3545") if status == "FAILED_VALIDATION" else colors.HexColor("#28A745")
        failure_type = report.get("failureType") or "N/A"
        generated_at = report.get("generatedAt") or "N/A"

        status_badge = Table(
            [[Paragraph(escape(status.replace("_", " ")), ParagraphStyle(
                "StatusBadge",
                parent=label_style,
                alignment=1,
                fontSize=8,
                leading=10,
                textColor=colors.white,
            ))]],
            colWidths=[50 * mm],
        )
        status_badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), status_color),
            ("BOX", (0, 0), (-1, -1), 0, status_color),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        header = Table(
            [[
                [
                    Paragraph("Sisqual Feasibility Report", title_style),
                    Paragraph(f"Task {escape(str(report.get('taskId') or 'N/A'))}", subtitle_style),
                ],
                status_badge,
            ]],
            colWidths=[116 * mm, 50 * mm],
        )
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (1, 0), (1, 0), 0),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.extend([header, Spacer(1, 10)])

        story.append(_summary_box(report, body_style, label_style))
        story.append(Spacer(1, 10))

        metadata_rows = [
            ["Failure type", failure_type],
            ["Algorithm", report.get("algorithm") or "N/A"],
            ["Problem", report.get("problemPath") or "N/A"],
            ["Generated at", generated_at],
            ["Errors", str(report.get("errorCount", 0))],
            ["Warnings", str(report.get("warningCount", 0))],
        ]
        story.append(Paragraph("Run Metadata", section_style))
        story.append(_metadata_table(metadata_rows, label_style, body_style))

        story.append(Paragraph("Detected Issues", section_style))
        issues = report.get("issues", [])
        if not issues:
            story.append(Paragraph("No blocking issues were detected.", body_style))
        else:
            for index, issue in enumerate(issues, start=1):
                story.append(_issue_card(index, issue, issue_title_style, body_style, label_style, muted_style))
                story.append(Spacer(1, 8))

        doc.build(story, onFirstPage=_pdf_page_decor, onLaterPages=_pdf_page_decor)
    except Exception:
        _write_minimal_pdf(path, report)


def _summary_box(report: dict[str, Any], body_style: Any, label_style: Any) -> Any:
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    summary = report.get("summary") or "No summary available."
    data = [[
        Paragraph("Summary", label_style),
        Paragraph(escape(str(summary)), body_style),
    ]]
    table = Table(data, colWidths=[30 * mm, 136 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#FDBA74")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def _metadata_table(rows: list[list[str]], label_style: Any, body_style: Any) -> Any:
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    data = [
        [Paragraph(escape(str(label)), label_style), Paragraph(escape(str(value)), body_style)]
        for label, value in rows
    ]
    table = Table(data, colWidths=[34 * mm, 132 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F9FAFB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _issue_card(
    index: int,
    issue: dict[str, Any],
    issue_title_style: Any,
    body_style: Any,
    label_style: Any,
    muted_style: Any,
) -> Any:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

    severity = str(issue.get("severity") or "unknown").upper()
    severity_color = colors.HexColor("#DC3545") if severity == "ERROR" else colors.HexColor("#F59E0B")
    title = issue.get("title") or "Untitled issue"
    code = issue.get("code") or "UNKNOWN"

    details = [
        ("Message", issue.get("message")),
        ("Employee", issue.get("employeeId")),
        ("Period", _issue_period(issue)),
        ("Suggested fix", issue.get("suggestedFix")),
    ]
    detail_rows = [
        [Paragraph(escape(label), label_style), Paragraph(escape(str(value)), body_style)]
        for label, value in details
        if value
    ]

    header = Table(
        [[
            Paragraph(f"{index}. {escape(str(title))}", issue_title_style),
            Paragraph(escape(severity), ParagraphStyle(
                "IssueSeverity",
                parent=label_style,
                alignment=1,
                fontSize=8,
                leading=10,
                textColor=colors.white,
            )),
        ]],
        colWidths=[134 * mm, 32 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (1, 0), (1, 0), severity_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    code_line = Paragraph(f"Code: {escape(str(code))}", muted_style)
    detail_table = Table(detail_rows, colWidths=[30 * mm, 136 * mm], hAlign="LEFT") if detail_rows else None
    if detail_table:
        detail_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#EEF2F7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

    parts = [header, Spacer(1, 4), code_line]
    if detail_table:
        parts.extend([Spacer(1, 5), detail_table])
    return KeepTogether(parts)


def _issue_period(issue: dict[str, Any]) -> str | None:
    start = issue.get("startDate")
    end = issue.get("endDate")
    if start and end:
        return f"{start} to {end}"
    return start or end


def _pdf_page_decor(canvas: Any, doc: Any) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    width, _ = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.setLineWidth(0.5)
    canvas.line(16 * mm, 12 * mm, width - 16 * mm, 12 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(16 * mm, 7 * mm, "SmarTaskUA validation report")
    canvas.drawRightString(width - 16 * mm, 7 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _write_minimal_pdf(path: Path, report: dict[str, Any]) -> None:
    text = [
        f"Sisqual Feasibility Report - {report.get('taskId')}",
        f"Status: {report.get('status')}",
        f"Failure type: {report.get('failureType')}",
        f"Summary: {report.get('summary')}",
    ]
    for issue in report.get("issues", [])[:10]:
        text.append(f"- {issue.get('title')}: {issue.get('message')}")
    stream = "BT /F1 10 Tf 50 780 Td "
    escaped_lines = [_pdf_escape(line) for line in text]
    stream += " T* ".join(f"({line}) Tj" for line in escaped_lines)
    stream += " ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream.encode('latin-1', 'replace'))} >> stream\n{stream}\nendstream endobj\n",
    ]
    content = "%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(content.encode("latin-1")))
        content += obj
    xref_start = len(content.encode("latin-1"))
    content += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        content += f"{offset:010d} 00000 n \n"
    content += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    path.write_bytes(content.encode("latin-1", "replace"))


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
