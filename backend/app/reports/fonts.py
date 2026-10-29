"""Font registration for ReportLab PDF documents using Noto Sans.

Registers Noto Sans (Regular, Bold, Italic, BoldItalic) and Noto Sans Devanagari
(Regular, Bold) TrueType fonts for PDF generation across reports, receipts,
and certificates.
"""

from __future__ import annotations

import logging
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Font directory located inside backend/app/assets/fonts
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Font names
FONT_REGULAR = "NotoSans"
FONT_BOLD = "NotoSans-Bold"
FONT_ITALIC = "NotoSans-Italic"
FONT_BOLD_ITALIC = "NotoSans-BoldItalic"
FONT_DEVANAGARI = "NotoSansDevanagari"
FONT_DEVANAGARI_BOLD = "NotoSansDevanagari-Bold"

_FONTS_INITIALIZED = False


def register_noto_fonts() -> bool:
    """Register Noto Sans and Noto Sans Devanagari TTF fonts in ReportLab.

    Returns True if Noto fonts are successfully registered, or False if
    fallback fonts (Helvetica) remain active.
    """
    global _FONTS_INITIALIZED
    if _FONTS_INITIALIZED:
        return True

    registered = pdfmetrics.getRegisteredFontNames()
    if "NotoSans" in registered and "NotoSansDevanagari" in registered:
        _FONTS_INITIALIZED = True
        return True

    regular_path = FONTS_DIR / "NotoSans-Regular.ttf"
    bold_path = FONTS_DIR / "NotoSans-Bold.ttf"
    italic_path = FONTS_DIR / "NotoSans-Italic.ttf"
    bold_italic_path = FONTS_DIR / "NotoSans-BoldItalic.ttf"
    devanagari_regular_path = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
    devanagari_bold_path = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"

    if not regular_path.exists():
        logger.warning(
            "Noto Sans font files not found at %s. Falling back to Helvetica.",
            FONTS_DIR,
        )
        return False

    try:
        # Register individual fonts
        pdfmetrics.registerFont(TTFont("NotoSans", str(regular_path)))
        if bold_path.exists():
            pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bold_path)))
        if italic_path.exists():
            pdfmetrics.registerFont(TTFont("NotoSans-Italic", str(italic_path)))
        if bold_italic_path.exists():
            pdfmetrics.registerFont(TTFont("NotoSans-BoldItalic", str(bold_italic_path)))

        if devanagari_regular_path.exists():
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(devanagari_regular_path)))
        if devanagari_bold_path.exists():
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(devanagari_bold_path)))

        # Register font families for automatic <b> / <i> tag resolution
        registerFontFamily(
            "NotoSans",
            normal="NotoSans",
            bold="NotoSans-Bold" if bold_path.exists() else "NotoSans",
            italic="NotoSans-Italic" if italic_path.exists() else "NotoSans",
            boldItalic="NotoSans-BoldItalic" if bold_italic_path.exists() else "NotoSans",
        )

        if devanagari_regular_path.exists():
            dev_bold = (
                "NotoSansDevanagari-Bold" if devanagari_bold_path.exists() else "NotoSansDevanagari"
            )
            registerFontFamily(
                "NotoSansDevanagari",
                normal="NotoSansDevanagari",
                bold=dev_bold,
                italic="NotoSansDevanagari",
                boldItalic=dev_bold,
            )

        _FONTS_INITIALIZED = True
        return True
    except Exception as exc:
        logger.error("Failed to register Noto Sans fonts in ReportLab: %s", exc)
        return False


def get_font_names() -> dict[str, str]:
    """Get active font name mappings (Noto Sans if registered, Helvetica fallback)."""
    if register_noto_fonts():
        return {
            "regular": FONT_REGULAR,
            "bold": FONT_BOLD,
            "italic": FONT_ITALIC,
            "bold_italic": FONT_BOLD_ITALIC,
            "devanagari": FONT_DEVANAGARI,
            "devanagari_bold": FONT_DEVANAGARI_BOLD,
        }
    return {
        "regular": "Helvetica",
        "bold": "Helvetica-Bold",
        "italic": "Helvetica-Oblique",
        "bold_italic": "Helvetica-BoldOblique",
        "devanagari": "Helvetica",
        "devanagari_bold": "Helvetica-Bold",
    }
