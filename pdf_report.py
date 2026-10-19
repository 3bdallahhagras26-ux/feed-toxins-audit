# -*- coding: utf-8 -*-
"""
================================================================================
pdf_report.py — توليد شهادة PDF رسمية للشحنة (صك الأمان لمهندس الجودة)
================================================================================
وحدة مستقلة (نفس مبدأ feed_optimizer.py وproximate_engine.py): لا تستورد
Streamlit، قابلة للاختبار بمعزل تمامًا. تأخذ dict ناتج جاهز من build_full_analysis()
و/أو build_full_proximate_analysis() + بصمة الشحنة الرسمية، وتُعيد bytes PDF خام.

VERSION: 1.1.0
LAST ENGINEERING REVIEW: 2026-10-19

--------------------------------------------------------------------------------
⚠️ قرار هندسي حرج: دعم اللغة العربية في ReportLab
--------------------------------------------------------------------------------
ReportLab لا يدعم تشكيل الحروف العربية (Contextual Shaping) ولا ترتيب النص ثنائي
الاتجاه (Bidi Reordering) أصلًا — نص عربي خام يُرسَم كحروف منفصلة غير متصلة
وبترتيب معكوس بصريًا. الحل (مُتحقَّق منه عمليًا، لا نظريًا، بمقارنة صورة فعلية
مُصيَّرة من PDF تجريبي قبل اعتماد هذا الأسلوب):
  ١) `arabic_reshaper.reshape(text)` يحوّل كل حرف عربي إلى صيغة العرض السياقية
     الصحيحة (معزولة/بداية/وسط/نهاية كلمة) — المعروفة كـ Presentation Forms.
  ٢) `bidi.algorithm.get_display(reshaped)` يُعيد ترتيب النص بصريًا من اليمين
     لليسار مع الحفاظ على الأرقام/الكلمات اللاتينية بترتيبها الصحيح داخل الجملة.
  ٣) خط يغطي فعليًا الكتل العربية الأساسية + أشكال العرض (Presentation Forms،
     U+FE70–FEFF) في جدول (3,1) القياسي — DejaVu/Vera (الخطوط الافتراضية في
     ReportLab) **لا تغطي العربية إطلاقًا**؛ FreeSerif/FreeSerifBold (GNU
     FreeFont، متوفر على نظام Linux القياسي ومُثبَّت افتراضيًا في هذه البيئة)
     أو خطوط Windows القياسية (Arial/Times) تغطيها بالكامل.

⚠️ نقطة فشل تشغيلية حقيقية: إن نُشر هذا التطبيق على بيئة لا تحتوي خطاً عربياً
مدعوماً في المسار الموثّق أدناه (FONT_SEARCH_PATHS)، توليد PDF سيفشل بوضوح
(RuntimeError برسالة تشخيصية) بدل كراش غامض أو ملف PDF صامت بمربعات فارغة (Tofu
Boxes) — الفشل الواضح هنا أفضل من ملف "ناجح" ظاهريًا لكن غير قابل للقراءة.
"""

import io
import os

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# مسارات بحث الخط — دعم شامل لأنظمة Windows و Linux/Debian.
FONT_SEARCH_PATHS = {
    "regular": [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\times.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/opentype/freefont/FreeSerif.otf",
    ],
    "bold": [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\timesbd.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        "/usr/share/fonts/opentype/freefont/FreeSerifBold.otf",
    ],
}
FONT_NAME_REGULAR = "PDFReportArabic"
FONT_NAME_BOLD = "PDFReportArabicBold"

_fonts_registered = False


def _register_fonts() -> None:
    """يسجّل خطوط العربية في ReportLab مرة واحدة فقط لكل عملية — idempotent."""
    global _fonts_registered
    if _fonts_registered:
        return

    def _first_existing(paths):
        for path in paths:
            if os.path.isfile(path):
                return path
        return None

    regular_path = _first_existing(FONT_SEARCH_PATHS["regular"])
    bold_path = _first_existing(FONT_SEARCH_PATHS["bold"])

    if not regular_path or not bold_path:
        raise RuntimeError(
            "تعذّر توليد PDF: لم يُعثر على خط يدعم الحروف العربية في أي من "
            f"المسارات المتوقعة: {FONT_SEARCH_PATHS}. "
            "يرجى التأكد من توفر خط عربي صالح في النظام أو تعديل pdf_report.FONT_SEARCH_PATHS."
        )

    pdfmetrics.registerFont(TTFont(FONT_NAME_REGULAR, regular_path))
    pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, bold_path))
    _fonts_registered = True


def _strip_leading_emoji(text: str) -> str:
    """
    يحذف الرمز التعبيري (Emoji) من بداية نص قرار/حالة قبل إدراجه في PDF — لا خط نصي
    يغطي الرموز التعبيرية، فتظهر كمربع فارغ (Tofu Box) بدل الرمز نفسه.
    """
    if not text:
        return text
    parts = text.split(" ", 1)
    if parts and parts[0] and not parts[0].isascii() and len(parts[0]) <= 2:
        return parts[1] if len(parts) > 1 else ""
    return text


def ar(text) -> str:
    """
    يحوّل نص عربي (أو مختلط عربي/إنجليزي/أرقام) إلى الصيغة الصحيحة للعرض في
    ReportLab: تشكيل سياقي (reshape) ثم ترتيب بصري ثنائي الاتجاه (bidi).
    """
    if text is None:
        return ""
    text = str(text)
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(text))


# ألوان متوافقة مع DECISION_STYLE/compute_traffic_light في بقية التطبيق
_COLOR_GREEN = colors.HexColor("#1e7e34")
_COLOR_YELLOW = colors.HexColor("#b8860b")
_COLOR_RED = colors.HexColor("#b02a2a")
_COLOR_HEADER_BG = colors.HexColor("#1f2d3d")
_COLOR_SUBHEADER_BG = colors.HexColor("#f0f0f0")


def _styles():
    _register_fonts()
    return {
        "title": ParagraphStyle(
            "ar_title", fontName=FONT_NAME_BOLD, fontSize=18, alignment=TA_CENTER,
            textColor=colors.white, leading=22,
        ),
        "subtitle": ParagraphStyle(
            "ar_subtitle", fontName=FONT_NAME_REGULAR, fontSize=11, alignment=TA_CENTER,
            textColor=colors.white, leading=14,
        ),
        "section_header": ParagraphStyle(
            "ar_section", fontName=FONT_NAME_BOLD, fontSize=13, alignment=TA_RIGHT,
            textColor=_COLOR_HEADER_BG, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ar_body", fontName=FONT_NAME_REGULAR, fontSize=10.5, alignment=TA_RIGHT, leading=15,
        ),
        "body_bold": ParagraphStyle(
            "ar_body_bold", fontName=FONT_NAME_BOLD, fontSize=10.5, alignment=TA_RIGHT, leading=15,
        ),
        "footer": ParagraphStyle(
            "ar_footer", fontName=FONT_NAME_REGULAR, fontSize=8, alignment=TA_CENTER,
            textColor=colors.grey, leading=11,
        ),
        "table_header": ParagraphStyle(
            "ar_table_header", fontName=FONT_NAME_BOLD, fontSize=10, alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "ar_table_cell", fontName=FONT_NAME_REGULAR, fontSize=10, alignment=TA_CENTER,
        ),
    }


def _fingerprint_table(fingerprint: dict, styles: dict) -> Table:
    """جدول البصمة الرسمية للشحنة — نوع الخامة/العلف، المورد، رقم التشغيلة/التاريخ."""
    rows = [
        [ar("القيمة"), ar("الحقل")],
        [ar(fingerprint.get("feed_type") or "—"), ar("نوع الخامة / العلف")],
        [ar(fingerprint.get("supplier_name") or "—"), ar("اسم المورد / الشركة")],
        [ar(fingerprint.get("batch_number") or "—"), ar("رقم التشغيلة / السيارة")],
        [ar(fingerprint.get("shipment_date") or "—"), ar("تاريخ الشحنة")],
        [ar(fingerprint.get("species_label") or "—"), ar("القطاع / القطيع")],
    ]
    table = Table(rows, colWidths=[9 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME_REGULAR),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
        ("BACKGROUND", (0, 0), (-1, 0), _COLOR_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_SUBHEADER_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _toxin_results_table(toxin_analysis: dict, styles: dict) -> Table:
    """جدول نتائج المعمل الحقيقية بالملي + الحدود التنظيمية + النسبة لكل سم."""
    header = [ar("النسبة"), ar("الحد المسموح"), ar("القيمة المقاسة"), ar("السم")]
    rows = [header]
    lab_results = toxin_analysis.get("lab_results", {})
    risk_ratios = toxin_analysis.get("risk_ratios", {})
    species_key = toxin_analysis.get("species_key")

    from constants import TOXIN_KEYS, TOXIN_METADATA, get_species_limit

    for toxin_key in TOXIN_KEYS:
        meta = TOXIN_METADATA.get(toxin_key, {})
        measured = lab_results.get(toxin_key)
        limit = get_species_limit(species_key, toxin_key, "accept_limit")
        ratio = risk_ratios.get(toxin_key)
        rows.append([
            ar(f"{ratio}×" if ratio is not None else "—"),
            ar(f"{limit} {meta.get('unit', '')}" if limit is not None else "—"),
            ar(f"{measured} {meta.get('unit', '')}" if measured is not None else "غير مقاس"),
            ar(meta.get("label_ar", toxin_key)),
        ])

    table = Table(rows, colWidths=[3 * cm, 4 * cm, 4 * cm, 4 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME_REGULAR),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
        ("BACKGROUND", (0, 0), (-1, 0), _COLOR_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_SUBHEADER_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _proximate_results_table(proximate_analysis: dict, styles: dict) -> Table:
    """جدول نتائج البروكسيمات + المعايير المرجعية لكل عنصر."""
    header = [ar("الحالة"), ar("المعيار المرجعي"), ar("القيمة المقاسة"), ar("العنصر")]
    rows = [header]
    inputs = proximate_analysis.get("inputs", {})
    standard = proximate_analysis.get("standard_used", {})

    from proximate_engine import PROXIMATE_PARAMETER_LABELS_AR

    status_ar = {
        "below_min": "أقل من الحد الأدنى", "above_max": "أعلى من الحد الأقصى",
        "within_range": "ضمن المدى", "no_limit_documented": "— لا حد موثَّق",
    }

    param_rows = [
        ("crude_protein_pct", inputs.get("crude_protein_pct"),
         proximate_analysis.get("kpi_1_protein_deficit", {}).get("status")),
        ("ether_extract_pct", inputs.get("ether_extract_pct"), None),
        ("crude_fiber_pct", inputs.get("crude_fiber_pct"),
         proximate_analysis.get("kpi_2_fiber_adulteration", {}).get("status")),
        ("ash_pct", inputs.get("ash_pct"), proximate_analysis.get("kpi_4_ash_purity", {}).get("status")),
    ]
    for param_key, value, status in param_rows:
        std_row = standard.get(param_key, {}) or {}
        bounds = []
        if std_row.get("min") is not None:
            bounds.append(f"≥ {std_row['min']}%")
        if std_row.get("max") is not None:
            bounds.append(f"≤ {std_row['max']}%")
        if not bounds and std_row.get("reference") is not None:
            bounds.append(f"مرجعي: {std_row['reference']}%")
        bounds_text = " / ".join(bounds) if bounds else "—"
        rows.append([
            ar(status_ar.get(status, "—")),
            ar(bounds_text),
            ar(f"{value}%" if value is not None else "—"),
            ar(PROXIMATE_PARAMETER_LABELS_AR.get(param_key, param_key)),
        ])

    moisture = inputs.get("moisture_pct")
    nfe = proximate_analysis.get("nfe_pct")
    rows.append([ar("—"), ar("—"), ar(f"{moisture}%" if moisture is not None else "—"), ar("الرطوبة (Moisture)")])
    rows.append([ar("—"), ar("محسوبة: 100 − الباقي"), ar(f"{nfe}%" if nfe is not None else "—"), ar("NFE (كربوهيدرات)")])

    table = Table(rows, colWidths=[3.5 * cm, 4.5 * cm, 3.5 * cm, 3.5 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME_REGULAR),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME_BOLD),
        ("BACKGROUND", (0, 0), (-1, 0), _COLOR_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_SUBHEADER_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _decision_banner(label_ar: str, reason_ar: str, code: str, styles: dict):
    """بانر القرار الحتمي — لون الخلفية يعتمد على شدة القرار."""
    color_map = {
        "APPROVE": _COLOR_GREEN, "GREEN": _COLOR_GREEN,
        "BLEND_REQUIRED": _COLOR_YELLOW, "BINDER_REQUIRED": _COLOR_YELLOW, "YELLOW": _COLOR_YELLOW,
        "REJECT": _COLOR_RED, "RED": _COLOR_RED,
    }
    bg = color_map.get(code, colors.grey)
    decision_style = ParagraphStyle(
        "decision", fontName=FONT_NAME_BOLD, fontSize=13, alignment=TA_RIGHT,
        textColor=colors.white, leading=17, backColor=bg, borderPadding=10,
    )
    reason_style = ParagraphStyle(
        "decision_reason", fontName=FONT_NAME_REGULAR, fontSize=10, alignment=TA_RIGHT,
        textColor=colors.white, leading=14, backColor=bg, borderPadding=(0, 10, 10, 10),
    )
    return [Paragraph(ar(f"القرار المعتمد: {label_ar}"), decision_style),
            Paragraph(ar(reason_ar or ""), reason_style)]


def _header_block(title: str, subtitle: str, styles: dict):
    return [
        Table(
            [[Paragraph(ar(title), styles["title"])], [Paragraph(ar(subtitle), styles["subtitle"])]],
            colWidths=[19 * cm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_HEADER_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        Spacer(1, 0.6 * cm),
    ]


def build_mycotoxin_certificate_pdf(fingerprint: dict, toxin_analysis: dict) -> bytes:
    """شهادة PDF لشاشة تأمين القطيع والسموم الفطرية (Tab 1)."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.2 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.3 * cm, rightMargin=1.3 * cm)
    story = []
    story += _header_block("شهادة تدقيق السموم الفطرية", "Feed Toxins Audit — Official Certificate", styles)
    story.append(Paragraph(ar("البصمة الرسمية للشحنة"), styles["section_header"]))
    story.append(_fingerprint_table(fingerprint, styles))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(ar("نتائج المعمل والحدود التنظيمية"), styles["section_header"]))
    story.append(_toxin_results_table(toxin_analysis, styles))
    story.append(Spacer(1, 0.5 * cm))

    decision = toxin_analysis.get("final_decision", {})
    story += _decision_banner(
        {"APPROVE": "اعتماد", "BLEND_REQUIRED": "خلط مطلوب",
         "BINDER_REQUIRED": "إضافة مضاد سموم", "REJECT": "رفض"}.get(decision.get("code"), decision.get("code", "—")),
        decision.get("reason_ar", ""), decision.get("code"), styles,
    )
    story.append(Spacer(1, 0.4 * cm))

    mri = toxin_analysis.get("mri", {})
    story.append(Paragraph(ar(f"مؤشر الخطورة MRI: {mri.get('score', '—')} / 100"), styles["body_bold"]))

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", color=colors.grey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        ar("هذا التقرير مُولَّد آليًا عبر محرك حسابي حتمي (Deterministic Python Engine) استنادًا "
           "إلى الحدود التنظيمية الموثَّقة في constants.py. لا يُغني عن الرجوع لفريق الجودة "
           "المختص عند الشك. Feed Toxins Audit Platform."),
        styles["footer"],
    ))

    doc.build(story)
    return buffer.getvalue()


def build_proximate_certificate_pdf(fingerprint: dict, proximate_analysis: dict) -> bytes:
    """شهادة PDF لشاشة التحليل التقريبي (Tab 3)."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.2 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.3 * cm, rightMargin=1.3 * cm)
    story = []
    story += _header_block("شهادة التحليل التقريبي", "Proximate Analysis — Official Certificate", styles)
    story.append(Paragraph(ar("البصمة الرسمية للشحنة"), styles["section_header"]))
    story.append(_fingerprint_table(fingerprint, styles))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(ar("نتائج التركيب الغذائي والمعايير المرجعية"), styles["section_header"]))
    story.append(_proximate_results_table(proximate_analysis, styles))
    story.append(Spacer(1, 0.5 * cm))

    traffic_light = proximate_analysis.get("kpi_7_traffic_light", {})
    story += _decision_banner(
        _strip_leading_emoji(traffic_light.get("label_ar", "—")),
        " | ".join(traffic_light.get("reasons", [])) or "لا مخالفات مسجَّلة.",
        traffic_light.get("code"), styles,
    )
    story.append(Spacer(1, 0.4 * cm))

    perf = proximate_analysis.get("kpi_6_performance_index", {})
    deduction = proximate_analysis.get("kpi_1_protein_deficit", {}).get("deduction_egp")
    story.append(Paragraph(ar(f"مؤشر الأداء المتوقع: {perf.get('score_pct', '—')}%"), styles["body_bold"]))
    if deduction:
        story.append(Paragraph(ar(f"الخصم المالي المقترح لعجز البروتين: {deduction:,.0f} ج.م"), styles["body_bold"]))

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", color=colors.grey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        ar("هذا التقرير مُولَّد آليًا عبر محرك حسابي حتمي (proximate_engine.py) استنادًا إلى "
           "معايير التركيب الغذائي الموثَّقة في constants.py. Feed Toxins Audit Platform."),
        styles["footer"],
    ))

    doc.build(story)
    return buffer.getvalue()


def build_combined_certificate_pdf(fingerprint: dict, toxin_analysis: dict, proximate_analysis: dict) -> bytes:
    """شهادة PDF موحَّدة لشاشة التدقيق الكامل والشامل (Tab 2)."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.2 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.3 * cm, rightMargin=1.3 * cm)
    story = []
    story += _header_block("شهادة التدقيق الكامل والشامل", "Full Audit — Mycotoxins + Proximates", styles)
    story.append(Paragraph(ar("البصمة الرسمية للشحنة"), styles["section_header"]))
    story.append(_fingerprint_table(fingerprint, styles))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(ar("أولًا: نتائج السموم الفطرية"), styles["section_header"]))
    story.append(_toxin_results_table(toxin_analysis, styles))
    story.append(Spacer(1, 0.3 * cm))
    toxin_decision = toxin_analysis.get("final_decision", {})
    story += _decision_banner(
        {"APPROVE": "اعتماد", "BLEND_REQUIRED": "خلط مطلوب",
         "BINDER_REQUIRED": "إضافة مضاد سموم", "REJECT": "رفض"}.get(
            toxin_decision.get("code"), toxin_decision.get("code", "—")),
        toxin_decision.get("reason_ar", ""), toxin_decision.get("code"), styles,
    )

    story.append(PageBreak())
    story.append(Paragraph(ar("ثانيًا: نتائج التركيب الغذائي (البروكسيمات)"), styles["section_header"]))
    story.append(_proximate_results_table(proximate_analysis, styles))
    story.append(Spacer(1, 0.3 * cm))
    traffic_light = proximate_analysis.get("kpi_7_traffic_light", {})
    story += _decision_banner(
        _strip_leading_emoji(traffic_light.get("label_ar", "—")),
        " | ".join(traffic_light.get("reasons", [])) or "لا مخالفات مسجَّلة.",
        traffic_light.get("code"), styles,
    )

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", color=colors.grey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        ar("تقرير مُدمَج يجمع محرك السموم الفطرية الحتمي ومحرك البروكسيمات الحتمي معًا — "
           "قراران مستقلان، كل منهما له مرجعه الخاص في constants.py. Feed Toxins Audit Platform."),
        styles["footer"],
    ))

    doc.build(story)
    return buffer.getvalue()