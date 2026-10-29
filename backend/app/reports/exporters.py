"""Export engines for CSV, XLSX, and PDF reports."""

from __future__ import annotations

import csv
import io
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reports.schemas import ReportData

# Numbered Canvas for "Page X of Y" in ReportLab


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute total page counts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Footer: Notice on left, page count on right
        footer_text = (
            "APAAR Portal - Official Regulatory Report | Demo Mode (AICTE SIH 2026) | "
            "Confidential & Privacy Protected under DPDP Principles"
        )
        self.drawString(36, 20, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(self._pagesize[0] - 36, 20, page_str)

        # Thin rule above footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 32, self._pagesize[0] - 36, 32)

        self.restoreState()


# CSV Exporter


def export_to_csv(data: ReportData) -> bytes:
    """Generate RFC 4180 compliant CSV encoded in UTF-8 with BOM."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header comments / Title metadata
    writer.writerow([f"# {data.title}"])
    writer.writerow([f"# Subtitle: {data.subtitle}"])
    writer.writerow([f"# Academic Year: {data.academic_year}"])
    writer.writerow([f"# Generated At: {data.generated_at}"])
    if data.filters_applied:
        filter_str = ", ".join(f"{k}={v}" for k, v in data.filters_applied.items() if v is not None)
        writer.writerow([f"# Filters: {filter_str}"])
    writer.writerow([])  # blank separator

    # Summary metrics (if any)
    if data.summary_boxes:
        writer.writerow(["# Summary Metrics:"])
        for box in data.summary_boxes:
            detail_part = f" ({box.detail})" if box.detail else ""
            writer.writerow([f"#   - {box.label}: {box.value}{detail_part}"])
        writer.writerow([])

    # Table columns
    writer.writerow(data.columns)

    # Table rows
    for row in data.rows:
        writer.writerow([str(v) if v is not None else "" for v in row])

    # Totals row
    if data.totals_row:
        writer.writerow([str(v) if v is not None else "" for v in data.totals_row])

    # Notes
    if data.notes:
        writer.writerow([])
        for note in data.notes:
            writer.writerow([f"# Note: {note}"])

    csv_text = output.getvalue()
    # Prepend UTF-8 BOM (\xef\xbb\xbf) for standard Excel compatibility
    return csv_text.encode("utf-8-sig")


# XLSX Exporter


def export_to_xlsx(data: ReportData) -> bytes:
    """Generate styled OpenPyXL workbook with official palette and formatting."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = data.report_type.value[:31]  # Excel sheet title limit is 31 chars

    # Palette
    navy_header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    table_header_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    zebra_light_fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    totals_fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
    card_fill = PatternFill(start_color="EBF8FF", end_color="EBF8FF", fill_type="solid")

    font_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="4A5568")
    font_tbl_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="2D3748")
    font_totals = Font(name="Calibri", size=10, bold=True, color="1A202C")
    font_card_val = Font(name="Calibri", size=12, bold=True, color="2B6CB0")
    font_card_lbl = Font(name="Calibri", size=9, color="718096")

    thin_border_side = Side(style="thin", color="CBD5E0")
    double_border_side = Side(style="double", color="1A202C")
    thin_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side,
    )
    totals_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=double_border_side,
    )

    num_cols = max(len(data.columns), 4)

    # 1. Main Title Banner
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    cell_title = ws.cell(row=1, column=1, value=f"AICTE - {data.title}")
    cell_title.font = font_title
    cell_title.fill = navy_header_fill
    cell_title.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 32

    # 2. Subtitle & Metadata
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    meta_desc = (
        f"{data.subtitle} | Academic Year: {data.academic_year} | Generated: {data.generated_at}"
    )
    if data.filters_applied:
        filters_str = ", ".join(f"{k}: {v}" for k, v in data.filters_applied.items() if v)
        if filters_str:
            meta_desc += f" | Filters: {filters_str}"
    cell_sub = ws.cell(row=2, column=1, value=meta_desc)
    cell_sub.font = font_subtitle
    cell_sub.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20

    current_row = 4

    # 3. Summary Metric Boxes (if present)
    if data.summary_boxes:
        box_col = 1
        for box in data.summary_boxes[:6]:  # Show up to 6 summary cards
            ws.cell(row=current_row, column=box_col, value=box.label).font = font_card_lbl
            ws.cell(row=current_row, column=box_col).fill = card_fill
            ws.cell(row=current_row, column=box_col).border = thin_border
            ws.cell(row=current_row, column=box_col).alignment = Alignment(horizontal="center")

            val_cell = ws.cell(row=current_row + 1, column=box_col, value=box.value)
            val_cell.font = font_card_val
            val_cell.fill = card_fill
            val_cell.border = thin_border
            val_cell.alignment = Alignment(horizontal="center")
            box_col += 1
        current_row += 3

    # 4. Table Headers
    ws.row_dimensions[current_row].height = 26
    for col_idx, col_name in enumerate(data.columns, start=1):
        c = ws.cell(row=current_row, column=col_idx, value=col_name)
        c.font = font_tbl_header
        c.fill = table_header_fill
        c.border = thin_border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    current_row += 1

    # 5. Table Rows
    for row_idx, row_values in enumerate(data.rows):
        ws.row_dimensions[current_row].height = 20
        is_zebra = row_idx % 2 == 1
        for col_idx, val in enumerate(row_values, start=1):
            c = ws.cell(row=current_row, column=col_idx, value=val)
            c.font = font_data
            c.border = thin_border
            if is_zebra:
                c.fill = zebra_light_fill

            # Numeric formatting
            if isinstance(val, (int, float)):
                c.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(val, float):
                    c.number_format = "#,##0.0"
                else:
                    c.number_format = "#,##0"
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        current_row += 1

    # 6. Totals Row
    if data.totals_row:
        ws.row_dimensions[current_row].height = 24
        for col_idx, val in enumerate(data.totals_row, start=1):
            c = ws.cell(row=current_row, column=col_idx, value=val)
            c.font = font_totals
            c.fill = totals_fill
            c.border = totals_border
            if isinstance(val, (int, float)):
                c.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(val, float):
                    c.number_format = "#,##0.0"
                else:
                    c.number_format = "#,##0"
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        current_row += 2

    # 7. Notes & Disclaimer
    if data.notes:
        for note in data.notes:
            c = ws.cell(row=current_row, column=1, value=f"* {note}")
            c.font = Font(name="Calibri", size=9, italic=True, color="718096")
            current_row += 1

    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Skip title merged row in length calculation
            if cell.row in (1, 2):
                continue
            if cell.value:
                val_str = str(cell.value)
                max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# PDF Exporter (ReportLab)


def export_to_pdf(data: ReportData) -> bytes:
    """Generate high-fidelity PDF report adhering to AICTE official styling."""
    buf = io.BytesIO()

    # Use landscape A4 for reports with >= 6 columns, portrait otherwise
    is_landscape = len(data.columns) >= 6
    page_size = landscape(A4) if is_landscape else A4
    page_width, _ = page_size

    # Margins: 36 points (0.5 inch)
    margin = 36
    usable_width = page_width - (margin * 2)

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=36,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "AicteTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1B365D"),
    )
    subtitle_style = ParagraphStyle(
        "AicteSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
    )
    meta_style = ParagraphStyle(
        "AicteMeta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#2B6CB0"),
        alignment=2,  # Right aligned
    )
    tbl_header_style = ParagraphStyle(
        "TblHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,  # Center aligned
    )
    tbl_cell_style = ParagraphStyle(
        "TblCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#2D3748"),
    )
    tbl_cell_right_style = ParagraphStyle(
        "TblCellRight",
        parent=tbl_cell_style,
        alignment=2,  # Right aligned
    )
    tbl_total_style = ParagraphStyle(
        "TblTotal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1A202C"),
    )
    tbl_total_right_style = ParagraphStyle(
        "TblTotalRight",
        parent=tbl_total_style,
        alignment=2,
    )
    card_label_style = ParagraphStyle(
        "CardLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#718096"),
        alignment=1,
    )
    card_value_style = ParagraphStyle(
        "CardValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=colors.HexColor("#2B6CB0"),
        alignment=1,
    )

    story: list[Any] = []

    # 1. Official Header
    header_data = [
        [
            Paragraph(f"<b>AICTE - {data.title}</b>", title_style),
            Paragraph(
                f"Academic Year: <b>{data.academic_year}</b><br/>"
                f"Generated: {data.generated_at}",
                meta_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[usable_width * 0.70, usable_width * 0.30])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)

    # Subtitle
    story.append(Spacer(1, 3))
    filter_desc = ""
    if data.filters_applied:
        f_list = [f"{k}: {v}" for k, v in data.filters_applied.items() if v]
        if f_list:
            filter_desc = f" | Filters: {', '.join(f_list)}"
    story.append(
        Paragraph(
            f"{data.subtitle}{filter_desc} &bull; "
            "All India Council for Technical Education (Ministry of Education)",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#1B365D"),
            spaceBefore=0,
            spaceAfter=8,
        )
    )

    # 2. Summary Metric Boxes (if any)
    if data.summary_boxes:
        num_boxes = min(len(data.summary_boxes), 5)
        card_w = usable_width / num_boxes
        box_headers = [Paragraph(b.label, card_label_style) for b in data.summary_boxes[:num_boxes]]
        box_values = [
            Paragraph(str(b.value), card_value_style) for b in data.summary_boxes[:num_boxes]
        ]
        summary_table = Table([box_headers, box_values], colWidths=[card_w] * num_boxes)
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 10))

    # 3. Main Data Table
    num_cols = len(data.columns)
    # Estimate proportional column widths
    col_width = usable_width / num_cols

    # Prepare table elements wrapped in Paragraph for autowrap
    table_content: list[list[Any]] = []

    # Header
    header_row = [Paragraph(col, tbl_header_style) for col in data.columns]
    table_content.append(header_row)

    # Data Rows
    for row in data.rows:
        row_cells = []
        for val in row:
            if isinstance(val, (int, float)):
                cell_text = f"{val:,.1f}" if isinstance(val, float) else f"{val:,}"
                row_cells.append(Paragraph(cell_text, tbl_cell_right_style))
            else:
                cell_text = str(val) if val is not None else ""
                row_cells.append(Paragraph(cell_text, tbl_cell_style))
        table_content.append(row_cells)

    # Totals Row
    if data.totals_row:
        total_cells = []
        for val in data.totals_row:
            if isinstance(val, (int, float)):
                cell_text = f"{val:,.1f}" if isinstance(val, float) else f"{val:,}"
                total_cells.append(Paragraph(cell_text, tbl_total_right_style))
            else:
                cell_text = str(val) if val is not None else ""
                total_cells.append(Paragraph(cell_text, tbl_total_style))
        table_content.append(total_cells)

    pdf_table = Table(table_content, colWidths=[col_width] * num_cols, repeatRows=1)

    table_style_list = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
    ]

    # Alternating row colors
    for r_idx in range(1, len(data.rows) + 1):
        if r_idx % 2 == 0:
            table_style_list.append(
                ("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor("#F7FAFC"))
            )

    # Totals row style
    if data.totals_row:
        total_row_idx = len(table_content) - 1
        table_style_list.extend(
            [
                (
                    "BACKGROUND",
                    (0, total_row_idx),
                    (-1, total_row_idx),
                    colors.HexColor("#EDF2F7"),
                ),
                (
                    "LINEABOVE",
                    (0, total_row_idx),
                    (-1, total_row_idx),
                    1,
                    colors.HexColor("#2D3748"),
                ),
                (
                    "LINEBELOW",
                    (0, total_row_idx),
                    (-1, total_row_idx),
                    1.5,
                    colors.HexColor("#1B365D"),
                ),
            ]
        )

    pdf_table.setStyle(TableStyle(table_style_list))
    story.append(pdf_table)

    # 4. Notes
    if data.notes:
        story.append(Spacer(1, 8))
        for note in data.notes:
            story.append(
                Paragraph(
                    f"&bull; <i>{note}</i>",
                    ParagraphStyle(
                        "NoteStyle",
                        parent=styles["Normal"],
                        fontName="Helvetica-Oblique",
                        fontSize=7.5,
                        leading=10,
                        textColor=colors.HexColor("#718096"),
                    ),
                )
            )

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
