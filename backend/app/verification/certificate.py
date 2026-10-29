"""Degree Certificate PDF Generator with side-by-side College ID, APAAR ID, and QR code."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import reportlab.rl_config
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
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
from app.reports.fonts import get_font_names, register_noto_fonts
from app.reports.tokens import (
    ACCENT_GOLD,
    NEUTRAL_100,
    NEUTRAL_300,
    NEUTRAL_500,
    NEUTRAL_700,
    NEUTRAL_900,
    PRIMARY_50,
    PRIMARY_600,
    PRIMARY_800,
)
from app.verification.service import (
    generate_qr_code_png,
    issue_verified_record,
)

reportlab.rl_config.pageCompression = 0

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Student, User


def format_apaar_display(apaar_id: str) -> str:
    """Format a 12-digit APAAR ID into grouped 4-digit chunks (e.g. 1234 5678 9012)."""
    clean = apaar_id.replace(" ", "").strip()
    if len(clean) == 12 and clean.isdigit():
        return f"{clean[0:4]} {clean[4:8]} {clean[8:12]}"
    return clean


def resolve_degree_details(
    level: str | None, course_name: str | None, branch: str | None
) -> tuple[str, str]:
    """Resolve formal degree title and branch representation for certificate."""
    lvl = (level or "").strip().upper()
    c_name = (course_name or "Technical Engineering").strip()
    br = (branch or c_name).strip()

    if lvl == "UG":
        degree_title = "Bachelor of Technology"
    elif lvl == "PG":
        degree_title = "Master of Technology"
    elif lvl == "DIPLOMA":
        degree_title = "Diploma in Engineering"
    elif lvl == "PGDM":
        degree_title = "Post Graduate Diploma in Management"
    else:
        # Check if course_name already specifies degree
        lower_c = c_name.lower()
        if "bachelor" in lower_c or "b.tech" in lower_c or "b.e" in lower_c:
            degree_title = "Bachelor of Technology"
        elif "master" in lower_c or "m.tech" in lower_c or "m.e" in lower_c:
            degree_title = "Master of Technology"
        elif "diploma" in lower_c:
            degree_title = "Diploma in Engineering"
        else:
            degree_title = "Degree of Technical Education"

    return degree_title, br


def draw_certificate_decorations(canvas_obj: canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Draw ornate borders, background security watermark, and statutory demo notice."""
    canvas_obj.saveState()
    fonts = get_font_names()
    font_reg = fonts["regular"]
    font_bold = fonts["bold"]
    width, height = doc.pagesize

    # 1. Outer Deep Brand Primary Border (3.5 pt)
    canvas_obj.setStrokeColor(PRIMARY_800)
    canvas_obj.setLineWidth(3.5)
    canvas_obj.rect(16, 16, width - 32, height - 32, stroke=1, fill=0)

    # 2. Inner Warm Gold Border (1.5 pt)
    canvas_obj.setStrokeColor(ACCENT_GOLD)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.rect(22, 22, width - 44, height - 44, stroke=1, fill=0)

    # 3. Fine Slate Hairline Frame (0.5 pt)
    canvas_obj.setStrokeColor(NEUTRAL_300)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.rect(26, 26, width - 52, height - 52, stroke=1, fill=0)

    # 4. Corner Ornamental Accents (Gold squares at 4 corners)
    canvas_obj.setFillColor(ACCENT_GOLD)
    canvas_obj.setStrokeColor(PRIMARY_800)
    canvas_obj.setLineWidth(0.75)
    corner_size = 5
    for cx, cy in [
        (19, 19),
        (width - 19 - corner_size, 19),
        (19, height - 19 - corner_size),
        (width - 19 - corner_size, height - 19 - corner_size),
    ]:
        canvas_obj.rect(cx, cy, corner_size, corner_size, fill=1, stroke=1)

    # 5. Background Security Watermark (EduTrace Verified Credential)
    canvas_obj.saveState()
    canvas_obj.translate(width / 2.0, height / 2.0)
    canvas_obj.rotate(28)
    canvas_obj.setFont(font_bold, 38)
    canvas_obj.setFillColor(PRIMARY_50)  # Soft, faint watermark
    canvas_obj.drawCentredString(0, 0, f"{PRODUCT_NAME.upper()} • VERIFIED ACADEMIC CREDENTIAL")
    canvas_obj.restoreState()

    # 6. Bottom Statutory & Demo Mode Notice (REBRAND_TASKS R14: Demo data footer, Page 1 of 1)
    canvas_obj.setFont(font_reg, 6.5)
    canvas_obj.setFillColor(NEUTRAL_500)
    footer_text = (
        f"Demo data • APAAR registry is simulated • {PRODUCT_NAME} is a prototype and not an "
        "official government service • Ed25519 Cryptographic Proof • Page 1 of 1"
    )
    canvas_obj.drawCentredString(width / 2.0, 11, footer_text)

    canvas_obj.restoreState()


def generate_certificate_pdf(
    student: Student,
    db: Session,
    base_url: str | None = None,
    actor: User | None = None,
    client_ip: str = "127.0.0.1",
) -> bytes:
    """Generate a high-resolution, landscape A4 sample degree certificate PDF.

    Spec: Section 17 & TASKS.md T35, REBRAND_TASKS R14:
    - Side-by-side College Student ID (enrolment_no) and APAAR ID.
    - Embedded verification QR code encoding the `/verify?vid=...` endpoint.
    - Ed25519 signed proof reference.
    - EduTrace wordmark header, Noto Sans embedded, UX4G semantic tokens, Demo data footer.
    - No emblem or official government seals.
    """
    register_noto_fonts()
    fonts = get_font_names()
    font_reg = fonts["regular"]
    font_bold = fonts["bold"]
    font_italic = fonts["italic"]

    settings = get_settings()
    root_url = (base_url or settings.FRONTEND_URL).rstrip("/")

    # Ensure a cryptographically signed VerifiedRecord exists for this student
    vr = student.verified_record
    if not vr or vr.status != "active":
        vr = issue_verified_record(
            db=db,
            student=student,
            actor=actor,
            client_ip=client_ip,
        )

    # Generate QR Code PNG (encodes ${FRONTEND_URL}/verify?vid={verification_id})
    qr_png_bytes = generate_qr_code_png(vr.verification_id, base_url=root_url)

    # Extract institutional and curriculum details
    inst = student.institution
    inst_name = inst.name if inst else "All India Technical Institution"
    aicte_id = inst.aicte_id if inst else "1-0000000000"
    affiliating_univ = (
        inst.affiliating_university
        if inst and inst.affiliating_university
        else "State Technical University"
    )
    location = f"{inst.district or 'Pune'}, {inst.state or 'Maharashtra'}" if inst else "India"

    course = student.course
    course_level = course.level if course else "UG"
    course_name = (
        course.name
        if course
        else (getattr(student, "course_name", None) or "Computer Science and Engineering")
    )
    branch = course.branch if course else course_name
    degree_title, discipline = resolve_degree_details(course_level, course_name, branch)

    # Setup ReportLab document in Landscape A4 (841.89 x 595.27)
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=30,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_center = ParagraphStyle("CenterBase", parent=styles["Normal"], alignment=1)
    style_wordmark = ParagraphStyle(
        "BrandWordmark",
        parent=style_center,
        fontName=font_bold,
        fontSize=12,
        leading=14,
        textColor=PRIMARY_600,
    )
    style_cert_header_sub = ParagraphStyle(
        "BrandSub",
        parent=style_center,
        fontName=font_reg,
        fontSize=7.5,
        leading=9.5,
        textColor=NEUTRAL_500,
    )
    style_inst_name = ParagraphStyle(
        "InstName",
        parent=style_center,
        fontName=font_bold,
        fontSize=18,
        leading=21,
        textColor=NEUTRAL_900,
    )
    style_inst_meta = ParagraphStyle(
        "InstMeta",
        parent=style_center,
        fontName=font_reg,
        fontSize=8,
        leading=10,
        textColor=NEUTRAL_700,
    )
    style_cert_title = ParagraphStyle(
        "CertTitle",
        parent=style_center,
        fontName=font_bold,
        fontSize=15,
        leading=17,
        textColor=PRIMARY_800,
    )
    style_preamble = ParagraphStyle(
        "Preamble",
        parent=style_center,
        fontName=font_italic,
        fontSize=9,
        leading=11,
        textColor=NEUTRAL_700,
    )
    style_degree_awarded = ParagraphStyle(
        "DegreeAwarded",
        parent=style_center,
        fontName=font_bold,
        fontSize=13.5,
        leading=16,
        textColor=NEUTRAL_900,
    )
    style_student_name = ParagraphStyle(
        "StudentName",
        parent=style_center,
        fontName=font_bold,
        fontSize=18,
        leading=21,
        textColor=PRIMARY_800,
    )
    style_conferral_note = ParagraphStyle(
        "ConferralNote",
        parent=style_center,
        fontName=font_reg,
        fontSize=8.5,
        leading=11,
        textColor=NEUTRAL_700,
    )

    story: list[object] = []

    # 1. EduTrace Wordmark Header (REBRAND_TASKS R14: No emblem or official logos)
    story.append(Paragraph(f"<b>{PRODUCT_NAME}</b>", style_wordmark))
    story.append(
        Paragraph(
            "Verifiable Academic Credential • "
            "Student Data Management &amp; Verification Architecture",
            style_cert_header_sub,
        )
    )
    story.append(Spacer(1, 4))

    # 2. Institution Details
    story.append(Paragraph(inst_name.upper(), style_inst_name))
    inst_meta_text = (
        f"AICTE Approved Institution (AICTE ID: {aicte_id}) • "
        f"Affiliated to {affiliating_univ} • {location}"
    )
    story.append(Paragraph(inst_meta_text, style_inst_meta))
    story.append(Spacer(1, 4))

    # Decorative Gold Divider
    story.append(
        HRFlowable(
            width="80%",
            thickness=1.5,
            color=ACCENT_GOLD,
            spaceBefore=1,
            spaceAfter=4,
        )
    )

    # 3. Certificate Title & Award Statement
    story.append(Paragraph("PROVISIONAL DEGREE CERTIFICATE", style_cert_title))
    story.append(Spacer(1, 3))
    confer_intro = (
        "On the recommendation of the Academic Council, "
        "the Institution hereby confers the degree of"
    )
    story.append(Paragraph(confer_intro, style_preamble))
    story.append(Spacer(1, 3))
    story.append(Paragraph(f"{degree_title} in {discipline}", style_degree_awarded))
    story.append(Spacer(1, 3))
    story.append(Paragraph("upon", style_preamble))
    story.append(Spacer(1, 3))
    story.append(Paragraph(student.name.upper(), style_student_name))
    story.append(Spacer(1, 3))
    confer_body = (
        "who has successfully completed the prescribed curriculum and fulfilled "
        f"all academic requirements in the Academic Year <b>{student.academic_year}</b>."
    )
    story.append(Paragraph(confer_body, style_conferral_note))
    story.append(Spacer(1, 7))

    # 4. Side-by-Side Academic Identity Block (TASKS.md T35 / SPEC §17 Key Requirement)
    # College Student ID and APAAR ID presented in prominent parallel callouts
    col_id_cell = Paragraph(
        "<b><font size='8' color='#737373'>COLLEGE STUDENT ID / ENROLMENT NO</font></b><br/>"
        f"<font size='12' face='Courier-Bold' color='#171717'>{student.enrolment_no}</font><br/>"
        "<font size='6.5' color='#737373'>Institutional Student Academic Identifier</font>",
        style_center,
    )
    apaar_disp = format_apaar_display(student.apaar_id)
    col_apaar_cell = Paragraph(
        "<b><font size='8' color='#737373'>APAAR ID (ACADEMIC IDENTITY)</font></b><br/>"
        f"<font size='12' face='Courier-Bold' color='#171717'>{apaar_disp}</font><br/>"
        "<font size='6.5' color='#737373'>Automated Permanent Academic Account Registry</font>",
        style_center,
    )

    identity_table = Table([[col_id_cell, col_apaar_cell]], colWidths=[315, 315])
    identity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NEUTRAL_100),
                ("BOX", (0, 0), (-1, -1), 1, NEUTRAL_300),
                ("INNERGRID", (0, 0), (-1, -1), 1, NEUTRAL_300),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(identity_table)
    story.append(Spacer(1, 7))

    # 5. Verification QR Code & Signatures Section (3 Columns)
    issued_date_str = (
        vr.issued_at.strftime("%B %d, %Y")
        if isinstance(vr.issued_at, datetime)
        else datetime.now(UTC).strftime("%B %d, %Y")
    )

    status_str = vr.status.upper()
    sig_left_cell = Paragraph(
        f"<font size='7.5' color='#404040'>Date of Issue: <b>{issued_date_str}</b></font><br/>"
        f"<font size='7' color='#00522C'>Credential Status: <b>{status_str}</b></font><br/><br/>"
        f"<font size='8' color='#CBD5E1'>_______________________________</font><br/>"
        f"<b><font size='8.5' color='#171717'>Controller of Examinations</font></b><br/>"
        f"<font size='6.5' color='#737373'>{inst_name}</font>",
        style_center,
    )

    qr_image = Image(io.BytesIO(qr_png_bytes), width=62, height=62)
    sig_center_cell = [
        qr_image,
        Spacer(1, 2),
        Paragraph(
            f"<b><font size='7' face='Courier-Bold' color='#171717'>{vr.verification_id}</font></b>"
            "<br/><b><font size='7' color='#4A2BC2'>Scan QR to verify credential</font></b><br/>"
            f"<font size='6' color='#737373'>Ed25519 Cryptographic Proof • {PRODUCT_NAME}</font>",
            style_center,
        ),
    ]

    sig_right_cell = Paragraph(
        f"<b><font size='7.5' color='#B45309'>INSTITUTIONAL ACADEMIC SEAL</font></b><br/>"
        f"<font size='6.5' color='#737373'>Verified &amp; Sealed Record</font><br/><br/>"
        f"<font size='8' color='#CBD5E1'>_______________________________</font><br/>"
        f"<b><font size='8.5' color='#171717'>Director / Principal</font></b><br/>"
        f"<font size='6.5' color='#737373'>{inst_name}</font>",
        style_center,
    )

    footer_table = Table(
        [[sig_left_cell, sig_center_cell, sig_right_cell]], colWidths=[205, 220, 205]
    )
    footer_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(footer_table)

    # Build document with ornamental decoration canvas callback
    doc.build(story, onFirstPage=draw_certificate_decorations)

    return pdf_buffer.getvalue()
