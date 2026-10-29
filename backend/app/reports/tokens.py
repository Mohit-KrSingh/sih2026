"""ReportLab and OpenPyXL export color palette strictly aliased from UX4G semantic tokens.

Values correspond to UX4G Design System 3.0 tokens (--ux4g-color-*).
"""

from __future__ import annotations

from openpyxl.styles import PatternFill
from reportlab.lib import colors

# Brand colors (UX4G Primary ramp)
PRIMARY_900 = colors.HexColor("#22135C")
PRIMARY_800 = colors.HexColor("#2E1A7A")
PRIMARY_700 = colors.HexColor("#3C22A0")
PRIMARY_600 = colors.HexColor("#4A2BC2")  # Main brand color
PRIMARY_500 = colors.HexColor("#6748D8")
PRIMARY_200 = colors.HexColor("#C9BDCD")
PRIMARY_100 = colors.HexColor("#E4DEFE")
PRIMARY_50 = colors.HexColor("#F2EFFF")  # Brand surface soft

# Neutrals (UX4G Neutral ramp)
NEUTRAL_950 = colors.HexColor("#0A0A0A")
NEUTRAL_900 = colors.HexColor("#171717")  # Text primary
NEUTRAL_700 = colors.HexColor("#404040")  # Text secondary
NEUTRAL_500 = colors.HexColor("#737373")  # Text tertiary / muted
NEUTRAL_400 = colors.HexColor("#A1A1A1")
NEUTRAL_300 = colors.HexColor("#D9D9D9")  # Border default
NEUTRAL_200 = colors.HexColor("#E5E5E5")  # Border subtle / rules
NEUTRAL_100 = colors.HexColor("#F5F5F5")  # Background soft / zebra
NEUTRAL_50 = colors.HexColor("#FAFAFA")   # Background subtle
WHITE = colors.HexColor("#FFFFFF")

# Status / Feedback (UX4G Status colors)
STATUS_ERROR = colors.HexColor("#8A1A16")    # Red 700 / WCAG AAA on white
STATUS_ERROR_BG = colors.HexColor("#FFF8F8") # Red 50
STATUS_WARNING = colors.HexColor("#AD4E00")  # Orange 800 / WCAG AA on white
STATUS_WARNING_BG = colors.HexColor("#FFF7E6") # Orange 50
STATUS_SUCCESS = colors.HexColor("#00522C")  # Green 700 / WCAG AAA on white
STATUS_SUCCESS_BG = colors.HexColor("#F2FCEF") # Green 50
STATUS_INFO = colors.HexColor("#006D75")     # Cyan 700
STATUS_INFO_BG = colors.HexColor("#E6FFFB")  # Cyan 50

# Accent Gold (used for certificate borders and seal)
ACCENT_GOLD = colors.HexColor("#C89D35")
ACCENT_GOLD_DARK = colors.HexColor("#B45309")

# OpenPyXL PatternFills (hex values without #)
XLSX_HEADER_FILL = PatternFill(start_color="4A2BC2", end_color="4A2BC2", fill_type="solid")
XLSX_SUBHEADER_FILL = PatternFill(start_color="3C22A0", end_color="3C22A0", fill_type="solid")
XLSX_ZEBRA_FILL = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
XLSX_TOTALS_FILL = PatternFill(start_color="E4DEFE", end_color="E4DEFE", fill_type="solid")
XLSX_CARD_FILL = PatternFill(start_color="F2EFFF", end_color="F2EFFF", fill_type="solid")
