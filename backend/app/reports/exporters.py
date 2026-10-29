"""Export engines for CSV, XLSX, and PDF reports."""

from __future__ import annotations

import csv
import io
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
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

from app.brand import PRODUCT_NAME
from app.reports.fonts import get_font_names, register_noto_fonts
from app.reports.schemas import ReportData
from app.reports.tokens import (
    NEUTRAL_100,
    NEUTRAL_200,
    NEUTRAL_300,
    NEUTRAL_500,
    NEUTRAL_700,
    NEUTRAL_900,
    PRIMARY_50,
    PRIMARY_100,
    PRIMARY_600,
    PRIMARY_800,
    WHITE,
    XLSX_CARD_FILL,
    XLSX_HEADER_FILL,
    XLSX_SUBHEADER_FILL,
    XLSX_TOTALS_FILL,
    XLSX_ZEBRA_FILL,
)

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
        fonts = get_font_names()
        self.setFont(fonts["regular"], 8)
        self.setFillColor(NEUTRAL_500)

        # Footer: Demo data notice on left, page count on right (REBRAND_TASKS R14)
        footer_text = (
            f"Demo data • {PRODUCT_NAME} Platform • Simulated APAAR Registry • "
            "Confidential & Privacy Protected under DPDP Principles"
        )
        self.drawString(36, 20, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(self._pagesize[0] - 36, 20, page_str)

        # Thin rule above footer
        self.setStrokeColor(NEUTRAL_200)
        self.setLineWidth(0.5)
        self.line(36, 32, self._pagesize[0] - 36, 32)

        self.restoreState()


# CSV Exporter


def export_to_csv(data: ReportData) -> bytes:
    """Generate RFC 4180 compliant CSV encoded in UTF-8 with BOM."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header comments / Title metadata
    writer.writerow([f"# {PRODUCT_NAME} - {data.title}"])
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
    """Generate styled OpenPyXL workbook with official UX4G token palette and formatting."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = data.report_type.value[:31]  # Excel sheet title limit is 31 chars

    # Palette aliased from UX4G tokens
    brand_header_fill = XLSX_HEADER_FILL
    table_header_fill = XLSX_SUBHEADER_FILL
    zebra_light_fill = XLSX_ZEBRA_FILL
    totals_fill = XLSX_TOTALS_FILL
    card_fill = XLSX_CARD_FILL

    font_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="404040")
    font_tbl_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="171717")
    font_totals = Font(name="Calibri", size=10, bold=True, color="171717")
    font_card_val = Font(name="Calibri", size=12, bold=True, color="4A2BC2")
    font_card_lbl = Font(name="Calibri", size=9, color="737373")

    thin_border_side = Side(style="thin", color="D9D9D9")
    double_border_side = Side(style="double", color="171717")
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

    # 1. Main Title Banner with EduTrace brand name
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    cell_title = ws.cell(row=1, column=1, value=f"{PRODUCT_NAME} - {data.title}")
    cell_title.font = font_title
    cell_title.fill = brand_header_fill
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
            c.font = Font(name="Calibri", size=9, italic=True, color="737373")
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
    """Generate high-fidelity PDF report adhering to EduTrace UX4G token styling."""
    register_noto_fonts()
    fonts = get_font_names()
    font_reg = fonts["regular"]
    font_bold = fonts["bold"]
    font_italic = fonts["italic"]

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

    # Custom typography styles strictly aliasing UX4G semantic tokens & Noto Sans
    brand_style = ParagraphStyle(
        "EduTraceBrand",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=16,
        leading=19,
        textColor=PRIMARY_600,
    )
    brand_sub_style = ParagraphStyle(
        "EduTraceBrandSub",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=7.5,
        leading=9.5,
        textColor=NEUTRAL_500,
    )
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=13,
        leading=16,
        textColor=NEUTRAL_900,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubTitle",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8,
        leading=11,
        textColor=NEUTRAL_700,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_700,
        alignment=2,  # Right aligned
    )
    tbl_header_style = ParagraphStyle(
        "TblHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=WHITE,
        alignment=1,  # Center aligned
    )
    tbl_cell_style = ParagraphStyle(
        "TblCell",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=7.5,
        leading=9,
        textColor=NEUTRAL_900,
    )
    tbl_cell_right_style = ParagraphStyle(
        "TblCellRight",
        parent=tbl_cell_style,
        alignment=2,  # Right aligned
    )
    tbl_total_style = ParagraphStyle(
        "TblTotal",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_900,
    )
    tbl_total_right_style = ParagraphStyle(
        "TblTotalRight",
        parent=tbl_total_style,
        alignment=2,
    )
    card_label_style = ParagraphStyle(
        "CardLabel",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=7.5,
        leading=9,
        textColor=NEUTRAL_700,
        alignment=1,
    )
    card_value_style = ParagraphStyle(
        "CardValue",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=11,
        leading=13,
        textColor=PRIMARY_600,
        alignment=1,
    )

    story: list[Any] = []

    # 1. EduTrace Wordmark Header (No official emblem or unauthorized government seals)
    header_data = [
        [
            [
                Paragraph(f"<b>{PRODUCT_NAME}</b>", brand_style),
                Paragraph("Student Data Management &amp; Verification System", brand_sub_style),
            ],
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
    story.append(Spacer(1, 4))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=PRIMARY_600,
            spaceBefore=0,
            spaceAfter=6,
        )
    )

    # 2. Report Title & Subtitle
    story.append(Paragraph(f"<b>{data.title}</b>", title_style))
    story.append(Spacer(1, 2))
    filter_desc = ""
    if data.filters_applied:
        f_list = [f"{k}: {v}" for k, v in data.filters_applied.items() if v]
        if f_list:
            filter_desc = f" | Filters: {', '.join(f_list)}"
    story.append(
        Paragraph(
            f"{data.subtitle}{filter_desc}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))

    # 3. Summary Metric Boxes (if any)
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
                    ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_50),
                    ("BOX", (0, 0), (-1, -1), 1, NEUTRAL_300),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, NEUTRAL_300),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 10))

    # 4. Main Data Table
    num_cols = len(data.columns)
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
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_600),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, NEUTRAL_300),
    ]

    # Alternating row colors
    for r_idx in range(1, len(data.rows) + 1):
        if r_idx % 2 == 0:
            table_style_list.append(
                ("BACKGROUND", (0, r_idx), (-1, r_idx), NEUTRAL_100)
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
                    PRIMARY_100,
                ),
                (
                    "LINEABOVE",
                    (0, total_row_idx),
                    (-1, total_row_idx),
                    1,
                    PRIMARY_600,
                ),
                (
                    "LINEBELOW",
                    (0, total_row_idx),
                    (-1, total_row_idx),
                    1.5,
                    PRIMARY_800,
                ),
            ]
        )

    pdf_table.setStyle(TableStyle(table_style_list))
    story.append(pdf_table)

    # 5. Notes
    if data.notes:
        story.append(Spacer(1, 8))
        note_style = ParagraphStyle(
            "NoteStyle",
            parent=styles["Normal"],
            fontName=font_italic,
            fontSize=7.5,
            leading=10,
            textColor=NEUTRAL_500,
        )
        for note in data.notes:
            story.append(Paragraph(f"&bull; <i>{note}</i>", note_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
