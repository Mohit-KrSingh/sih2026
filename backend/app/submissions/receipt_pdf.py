"""Official Submission Receipt PDF Generator for EduTrace."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.brand import PRODUCT_NAME
from app.config import get_settings
from app.reports.exporters import NumberedCanvas
from app.reports.fonts import get_font_names, register_noto_fonts
from app.reports.tokens import (
    NEUTRAL_100,
    NEUTRAL_300,
    NEUTRAL_500,
    NEUTRAL_700,
    NEUTRAL_900,
    PRIMARY_50,
    PRIMARY_100,
    PRIMARY_600,
    PRIMARY_800,
    STATUS_SUCCESS,
    WHITE,
)

if TYPE_CHECKING:
    from app.submissions.schemas import SubmissionReceiptResponse


def generate_submission_receipt_pdf(
    receipt: SubmissionReceiptResponse,
    base_url: str | None = None,
) -> bytes:
    """Generate high-fidelity A4 submission receipt PDF adhering to UX4G token styling.

    Spec Section 17 & REBRAND_TASKS R14:
    - EduTrace wordmark header
    - Noto Sans embedded
    - UX4G token colors
    - Page numbers via NumberedCanvas
    - "Demo data" footer
    - No emblem or official government seals
    """
    register_noto_fonts()
    fonts = get_font_names()
    font_reg = fonts["regular"]
    font_bold = fonts["bold"]
    font_italic = fonts["italic"]

    settings = get_settings()
    root_url = (base_url or settings.FRONTEND_URL).rstrip("/")

    # Generate QR Code encoding receipt verification URL
    verify_url = f"{root_url}/college/submissions/{receipt.submission_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#171717", back_color="#FFFFFF")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_png_bytes = qr_buf.getvalue()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45,
    )
    usable_width = A4[0] - 72

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        "ReceiptBrand",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=16,
        leading=19,
        textColor=PRIMARY_600,
    )
    brand_sub_style = ParagraphStyle(
        "ReceiptBrandSub",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=7.5,
        leading=9.5,
        textColor=NEUTRAL_500,
    )
    meta_style = ParagraphStyle(
        "ReceiptMeta",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_700,
        alignment=2,
    )
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=13,
        leading=16,
        textColor=NEUTRAL_900,
        alignment=1,
    )
    token_label_style = ParagraphStyle(
        "TokenLabel",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_700,
        alignment=1,
    )
    token_val_style = ParagraphStyle(
        "TokenVal",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=15,
        leading=18,
        textColor=PRIMARY_600,
        alignment=1,
    )
    status_badge_style = ParagraphStyle(
        "StatusBadge",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=STATUS_SUCCESS,
        alignment=1,
    )
    cell_label_style = ParagraphStyle(
        "CellLabel",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_700,
    )
    cell_val_style = ParagraphStyle(
        "CellVal",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_900,
    )
    tbl_header_style = ParagraphStyle(
        "TblHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=WHITE,
        alignment=1,
    )
    tbl_cell_style = ParagraphStyle(
        "TblCell",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_900,
    )
    tbl_cell_center = ParagraphStyle(
        "TblCellCenter",
        parent=tbl_cell_style,
        alignment=1,
    )
    tbl_cell_bold = ParagraphStyle(
        "TblCellBold",
        parent=tbl_cell_style,
        fontName=font_bold,
        alignment=1,
    )
    decl_heading_style = ParagraphStyle(
        "DeclHeading",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8.5,
        leading=11,
        textColor=PRIMARY_800,
    )
    decl_text_style = ParagraphStyle(
        "DeclText",
        parent=styles["Normal"],
        fontName=font_italic,
        fontSize=8,
        leading=11,
        textColor=NEUTRAL_700,
    )

    story: list[object] = []

    # 1. EduTrace Wordmark Header
    header_data = [
        [
            [
                Paragraph(f"<b>{PRODUCT_NAME}</b>", brand_style),
                Paragraph("Student Data Management &amp; Verification System", brand_sub_style),
            ],
            Paragraph(
                f"Receipt Reference: <b>{receipt.receipt_no}</b><br/>"
                f"Academic Year: <b>{receipt.academic_year}</b>",
                meta_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[usable_width * 0.65, usable_width * 0.35])
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

    # 2. Receipt Banner Title & Status Box
    story.append(Paragraph("OFFICIAL ANNUAL DATA SUBMISSION RECEIPT", title_style))
    story.append(Spacer(1, 6))

    token_box_data = [
        [
            Paragraph("OFFICIAL RECEIPT TOKEN", token_label_style),
        ],
        [
            Paragraph(receipt.receipt_no, token_val_style),
        ],
        [
            Paragraph(
                f"LOCKED &amp; SUBMITTED • STATUS: {receipt.status.upper()}",
                status_badge_style,
            ),
        ],
    ]
    token_table = Table(token_box_data, colWidths=[usable_width])
    token_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_50),
                ("BOX", (0, 0), (-1, -1), 1, PRIMARY_100),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(token_table)
    story.append(Spacer(1, 10))

    # 3. Institution Details Grid
    submitted_date_str = (
        receipt.submitted_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if isinstance(receipt.submitted_at, datetime)
        else datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    inst_details = [
        [
            Paragraph("Institution Name:", cell_label_style),
            Paragraph(receipt.institution_name, cell_val_style),
            Paragraph("AICTE ID:", cell_label_style),
            Paragraph(receipt.aicte_id, cell_val_style),
        ],
        [
            Paragraph("Academic Year:", cell_label_style),
            Paragraph(receipt.academic_year, cell_val_style),
            Paragraph("Submission ID:", cell_label_style),
            Paragraph(f"#{receipt.submission_id}", cell_val_style),
        ],
        [
            Paragraph("Submitted By:", cell_label_style),
            Paragraph(receipt.submitted_by_email, cell_val_style),
            Paragraph("Submitted At:", cell_label_style),
            Paragraph(submitted_date_str, cell_val_style),
        ],
    ]
    inst_table = Table(
        inst_details,
        colWidths=[
            usable_width * 0.22,
            usable_width * 0.38,
            usable_width * 0.18,
            usable_width * 0.22,
        ],
    )
    inst_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NEUTRAL_100),
                ("BOX", (0, 0), (-1, -1), 0.5, NEUTRAL_300),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, NEUTRAL_300),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(inst_table)
    story.append(Spacer(1, 10))

    # 4. Verified Enrolment & Seat Metrics Table
    metrics_data = [
        [
            Paragraph("Category", tbl_header_style),
            Paragraph("Count", tbl_header_style),
            Paragraph("Compliance State", tbl_header_style),
        ],
        [
            Paragraph("Regular Sanctioned Admissions", tbl_cell_style),
            Paragraph(str(receipt.regular_students), tbl_cell_bold),
            Paragraph("Within Sanctioned Quota", tbl_cell_center),
        ],
        [
            Paragraph("Supernumerary Admissions", tbl_cell_style),
            Paragraph(str(receipt.supernumerary_students), tbl_cell_bold),
            Paragraph("Supernumerary Quota", tbl_cell_center),
        ],
        [
            Paragraph("Total Students Enrolled", tbl_cell_style),
            Paragraph(str(receipt.total_students), tbl_cell_bold),
            Paragraph("Central Repository Locked", tbl_cell_center),
        ],
        [
            Paragraph("Approved Programmes / Courses", tbl_cell_style),
            Paragraph(str(receipt.courses_count), tbl_cell_bold),
            Paragraph("Active Affiliation", tbl_cell_center),
        ],
        [
            Paragraph("Justified Policy Exceptions", tbl_cell_style),
            Paragraph(str(receipt.justified_exceptions_count), tbl_cell_bold),
            Paragraph(
                "Documented &amp; Under Review"
                if receipt.justified_exceptions_count > 0
                else "Zero Exceptions",
                tbl_cell_center,
            ),
        ],
    ]
    metrics_table = Table(
        metrics_data,
        colWidths=[usable_width * 0.50, usable_width * 0.22, usable_width * 0.28],
    )
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_600),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, NEUTRAL_300),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, NEUTRAL_100]),
            ]
        )
    )
    story.append(metrics_table)
    story.append(Spacer(1, 10))

    # 5. Affirmed Statutory Declaration Callout
    decl_content = [
        [
            Paragraph("Affirmed Statutory Declaration", decl_heading_style),
        ],
        [
            Paragraph(f'"{receipt.declaration_text}"', decl_text_style),
        ],
        [
            Paragraph(
                f"Digitally affirmed with OTP confirmation by {receipt.submitted_by_name} "
                f"({receipt.submitted_by_email}).",
                ParagraphStyle(
                    "DeclSub",
                    parent=styles["Normal"],
                    fontName=font_reg,
                    fontSize=7,
                    leading=9,
                    textColor=NEUTRAL_500,
                ),
            )
        ]
    ]
    decl_table = Table(decl_content, colWidths=[usable_width])
    decl_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NEUTRAL_100),
                ("BOX", (0, 0), (-1, -1), 0.75, NEUTRAL_300),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(decl_table)
    story.append(Spacer(1, 12))

    # 6. Verification QR & Signatures Section
    qr_image = Image(io.BytesIO(qr_png_bytes), width=65, height=65)
    sig_center_cell = [
        qr_image,
        Spacer(1, 2),
        Paragraph(
            "<b><font size='7' color='#4A2BC2'>Scan QR to verify receipt</font></b><br/>"
            f"<font size='6' color='#737373'>{PRODUCT_NAME} Platform Verification</font>",
            ParagraphStyle("QrLbl", parent=styles["Normal"], alignment=1),
        ),
    ]

    sig_left_cell = Paragraph(
        f"<font size='7.5' color='#404040'>Submitted: <b>{submitted_date_str}</b></font><br/>"
        "<font size='7' color='#00522C'>Repository Status: <b>LOCKED</b></font><br/><br/>"
        "<font size='8' color='#CBD5E1'>_______________________________</font><br/>"
        "<b><font size='8.5' color='#171717'>Authorised College Officer</font></b><br/>"
        f"<font size='6.5' color='#737373'>{receipt.institution_name}</font>",
        ParagraphStyle("SigLeft", parent=styles["Normal"], alignment=1),
    )

    sig_right_cell = Paragraph(
        "<b><font size='7.5' color='#B45309'>AICTE CENTRAL REPOSITORY</font></b><br/>"
        "<font size='6.5' color='#737373'>Automated Intake &amp; Enrolment Audit</font><br/><br/>"
        "<font size='8' color='#CBD5E1'>_______________________________</font><br/>"
        "<b><font size='8.5' color='#171717'>AICTE Compliance Officer</font></b><br/>"
        "<font size='6.5' color='#737373'>Regulatory Review Authority</font>",
        ParagraphStyle("SigRight", parent=styles["Normal"], alignment=1),
    )

    sig_table = Table(
        [[sig_left_cell, sig_center_cell, sig_right_cell]],
        colWidths=[usable_width * 0.38, usable_width * 0.24, usable_width * 0.38],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
