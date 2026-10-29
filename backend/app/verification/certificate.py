"""Degree Certificate PDF Generator with side-by-side College ID, APAAR ID, and QR code."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import reportlab.rl_config
from reportlab.lib import colors
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

from app.config import get_settings
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
    """Draw ornate borders, background security watermark, and statutory footer."""
    canvas_obj.saveState()
    width, height = doc.pagesize

    # 1. Outer Deep Navy Ornamental Border (3.5 pt)
    canvas_obj.setStrokeColor(colors.HexColor("#0F2942"))
    canvas_obj.setLineWidth(3.5)
    canvas_obj.rect(16, 16, width - 32, height - 32, stroke=1, fill=0)

    # 2. Inner Warm Gold Border (1.5 pt)
    canvas_obj.setStrokeColor(colors.HexColor("#C89D35"))
    canvas_obj.setLineWidth(1.5)
    canvas_obj.rect(22, 22, width - 44, height - 44, stroke=1, fill=0)

    # 3. Fine Slate Hairline Frame (0.5 pt)
    canvas_obj.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.rect(26, 26, width - 52, height - 52, stroke=1, fill=0)

    # 4. Corner Ornamental Accents (Gold squares at 4 corners)
    canvas_obj.setFillColor(colors.HexColor("#C89D35"))
    canvas_obj.setStrokeColor(colors.HexColor("#0F2942"))
    canvas_obj.setLineWidth(0.75)
    corner_size = 5
    for cx, cy in [
        (19, 19),
        (width - 19 - corner_size, 19),
        (19, height - 19 - corner_size),
        (width - 19 - corner_size, height - 19 - corner_size),
    ]:
        canvas_obj.rect(cx, cy, corner_size, corner_size, fill=1, stroke=1)

    # 5. Background Security Watermark
    canvas_obj.saveState()
    canvas_obj.translate(width / 2.0, height / 2.0)
    canvas_obj.rotate(28)
    canvas_obj.setFont("Helvetica-Bold", 42)
    canvas_obj.setFillColor(colors.HexColor("#F1F5F9"))  # Soft, faint watermark
    canvas_obj.drawCentredString(0, 0, "APAAR • AICTE SECURE CREDENTIAL")
    canvas_obj.restoreState()

    # 6. Bottom Statutory & Demo Mode Notice
    canvas_obj.setFont("Helvetica", 6.5)
    canvas_obj.setFillColor(colors.HexColor("#64748B"))
    footer_text = (
        "National Academic Identity & Verification Registry | AICTE APAAR Platform | "
        "Tamper-Evident Ed25519 Cryptographic Proof | Demo Mode (SIH 2026)"
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

    Spec: Section 17 & TASKS.md T35:
    - Side-by-side College Student ID (enrolment_no) and APAAR ID.
    - Embedded verification QR code encoding the `/verify?vid=...` endpoint.
    - Ed25519 signed proof reference.
    - DPDP Act compliant with zero extraneous PII leakage.
    """
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
    style_aicte_title = ParagraphStyle(
        "AicteTitle",
        parent=style_center,
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11.5,
        textColor=colors.HexColor("#1E3A8A"),
    )
    style_aicte_sub = ParagraphStyle(
        "AicteSub",
        parent=style_center,
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#64748B"),
    )
    style_inst_name = ParagraphStyle(
        "InstName",
        parent=style_center,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=colors.HexColor("#0F2942"),
    )
    style_inst_meta = ParagraphStyle(
        "InstMeta",
        parent=style_center,
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )
    style_cert_title = ParagraphStyle(
        "CertTitle",
        parent=style_center,
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=17,
        textColor=colors.HexColor("#0F2942"),
    )
    style_preamble = ParagraphStyle(
        "Preamble",
        parent=style_center,
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    style_degree_awarded = ParagraphStyle(
        "DegreeAwarded",
        parent=style_center,
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=16,
        textColor=colors.HexColor("#0F2942"),
    )
    style_student_name = ParagraphStyle(
        "StudentName",
        parent=style_center,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=colors.HexColor("#0F2942"),
    )
    style_conferral_note = ParagraphStyle(
        "ConferralNote",
        parent=style_center,
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    story: list[object] = []

    # 1. Authority Insignia Header
    story.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)", style_aicte_title))
    story.append(
        Paragraph(
            "Statutory Authority • Ministry of Education, Government of India",
            style_aicte_sub,
        )
    )
    story.append(Spacer(1, 4))

    # 2. Institution Details
    story.append(Paragraph(inst_name.upper(), style_inst_name))
    inst_meta_text = (
        f"Approved by AICTE (AICTE ID: {aicte_id}) • "
        f"Affiliated to {affiliating_univ} • {location}"
    )
    story.append(Paragraph(inst_meta_text, style_inst_meta))
    story.append(Spacer(1, 4))

    # Decorative Gold Divider
    story.append(
        HRFlowable(
            width="80%",
            thickness=1.5,
            color=colors.HexColor("#C89D35"),
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

    # 4. Side-by-Side Academic Identity Block (TASKS.md T35 Key Requirement)
    # College Student ID and APAAR ID presented in prominent parallel callouts
    col_id_cell = Paragraph(
        "<b><font size='8' color='#475569'>COLLEGE STUDENT ID / ENROLMENT NO</font></b><br/>"
        f"<font size='12' face='Courier-Bold' color='#0F2942'>{student.enrolment_no}</font><br/>"
        "<font size='6.5' color='#64748B'>Institutional Student Academic Identifier</font>",
        style_center,
    )
    apaar_disp = format_apaar_display(student.apaar_id)
    col_apaar_cell = Paragraph(
        "<b><font size='8' color='#475569'>APAAR ID (ACADEMIC IDENTITY)</font></b><br/>"
        f"<font size='12' face='Courier-Bold' color='#0F2942'>{apaar_disp}</font><br/>"
        "<font size='6.5' color='#64748B'>Automated Permanent Academic Account Registry</font>",
        style_center,
    )

    identity_table = Table([[col_id_cell, col_apaar_cell]], colWidths=[315, 315])
    identity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
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
        f"<font size='7.5' color='#475569'>Date of Issue: <b>{issued_date_str}</b></font><br/>"
        f"<font size='7' color='#16A34A'>Credential Status: <b>{status_str}</b></font><br/><br/>"
        f"<font size='8' color='#94A3B8'>_______________________________</font><br/>"
        f"<b><font size='8.5' color='#0F2942'>Controller of Examinations</font></b><br/>"
        f"<font size='6.5' color='#64748B'>{inst_name}</font>",
        style_center,
    )

    qr_image = Image(io.BytesIO(qr_png_bytes), width=62, height=62)
    sig_center_cell = [
        qr_image,
        Spacer(1, 2),
        Paragraph(
            f"<b><font size='7' face='Courier-Bold' color='#0F2942'>{vr.verification_id}</font></b>"
            "<br/><b><font size='7' color='#0284C7'>Scan QR to verify credential</font></b><br/>"
            "<font size='6' color='#64748B'>Ed25519 Cryptographic Proof • National APAAR</font>",
            style_center,
        ),
    ]

    sig_right_cell = Paragraph(
        f"<b><font size='7.5' color='#B45309'>AICTE ACCREDITED INSTITUTION</font></b><br/>"
        f"<font size='6.5' color='#64748B'>Official Institutional Academic Seal</font><br/><br/>"
        f"<font size='8' color='#94A3B8'>_______________________________</font><br/>"
        f"<b><font size='8.5' color='#0F2942'>Director / Principal</font></b><br/>"
        f"<font size='6.5' color='#64748B'>{inst_name}</font>",
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
