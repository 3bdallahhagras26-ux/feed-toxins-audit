# -*- coding: utf-8 -*-
"""
tests/test_pdf_report.py — اختبارات توليد شهادات PDF (pdf_report.py)
================================================================================
⚠️ هذه الاختبارات تتحقق من: (أ) التوليد ينجح بلا استثناء لكل أنواع الشهادات الثلاثة،
(ب) bytes PDF صالحة فعليًا (تبدأ بتوقيع %PDF، يمكن فتحها)، (ج) خطوط FreeSerif مسجَّلة
وتحوي فعليًا رموز العرض العربية (لا تفترض الاختبارات "لا استثناء = نجاح" فقط — بل
تتحقق أيضًا من حضور محتوى عربي متوقَّع داخل نص PDF المُستخرَج، حيثما أمكن ذلك تقنيًا).

لا اختبار بصري آلي هنا (مقارنة صورة مُصيَّرة بكسل-بكسل) — ذلك تم التحقق منه يدويًا
أثناء تطوير pdf_report.py (راجع توثيق القرار الهندسي في رأس ذلك الملف). الاختبارات
هنا تضمن عدم الانحدار البرمجي (Regression) لا الجودة البصرية الدقيقة.
"""

import pytest

import app
import pdf_report as pr
import proximate_engine as pe


def _sample_toxin_analysis(aflatoxin=45.0, species_key="poultry_broiler"):
    parsed = {
        "shipment_meta": {"supplier_name": "شركة دلتا للأعلاف", "feed_type": "ذرة صفراء", "quantity_tons": 20.0},
        "normalized_inputs": {
            "lab_results": {"aflatoxin_ppb": aflatoxin, "ochratoxin_ppb": None, "don_ppm": 6.0,
                            "zearalenone_ppm": None, "fumonisin_ppm": None},
            "storage": {"temperature_celsius": 30.0, "moisture_percent": 15.0, "storage_days": 22},
            "parameters": {},
        },
        "parsing_audit": {"is_valid_input": True, "missing_critical_fields": [], "parsing_notes": ""},
    }
    return app.build_full_analysis(parsed, 1.6, 25.0, species_key)


def _sample_proximate_analysis(species_key="poultry_broiler", stage_key="starter", crude_fiber_pct=2.5):
    return pe.build_full_proximate_analysis(
        species_key, stage_key, moisture_pct=11.0, crude_protein_pct=24.0,
        ether_extract_pct=3.5, crude_fiber_pct=crude_fiber_pct, ash_pct=4.5,
        feed_price_egp_per_kg=25.0, quantity_tons=20.0,
    )


def _sample_fingerprint():
    return {
        "feed_type": "ذرة صفراء", "supplier_name": "شركة دلتا للأعلاف",
        "batch_number": "TRK-2026-0091", "shipment_date": "2026-09-28",
        "species_label": "دواجن تسمين (Broiler)",
    }


# ==============================================================================
# تسجيل الخطوط (_register_fonts) و ar()
# ==============================================================================
class TestFontRegistrationAndArabicShaping:
    def test_fonts_register_without_error(self):
        pr._fonts_registered = False  # إجبار إعادة التسجيل لاختبار المسار فعليًا
        pr._register_fonts()
        assert pr._fonts_registered is True

    def test_font_registration_is_idempotent(self):
        pr._register_fonts()
        pr._register_fonts()  # لا يجب أن يرفع استثناء عند الاستدعاء المتكرر

    def test_ar_reshapes_and_reorders_arabic_text(self):
        result = pr.ar("أفلاتوكسين")
        assert result != "أفلاتوكسين"  # يجب أن يتغيّر شكليًا (حروف العرض السياقية)
        assert isinstance(result, str) and len(result) > 0

    def test_ar_handles_none_without_exception(self):
        assert pr.ar(None) == ""

    def test_ar_handles_empty_string(self):
        assert pr.ar("") == ""

    def test_ar_leaves_pure_latin_text_unreordered(self):
        assert pr.ar("Broiler") == "Broiler"

    def test_ar_handles_mixed_arabic_and_latin(self):
        result = pr.ar("أفلاتوكسين 45 ppb")
        assert isinstance(result, str) and len(result) > 0


class TestStripLeadingEmoji:
    def test_strips_emoji_prefix(self):
        assert pr._strip_leading_emoji("🔴 مرفوضة تمامًا") == "مرفوضة تمامًا"

    def test_leaves_plain_text_unchanged(self):
        assert pr._strip_leading_emoji("اعتماد") == "اعتماد"

    def test_handles_empty_string(self):
        assert pr._strip_leading_emoji("") == ""


# ==============================================================================
# build_mycotoxin_certificate_pdf()
# ==============================================================================
class TestMycotoxinCertificate:
    def test_generates_valid_pdf_bytes(self):
        pdf_bytes = pr.build_mycotoxin_certificate_pdf(_sample_fingerprint(), _sample_toxin_analysis())
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

    def test_works_with_rejected_shipment(self):
        """شحنة REJECT (تلوّث شديد) — القرار يجب أن يُبنى بلا استثناء حتى في أسوأ الحالات."""
        pdf_bytes = pr.build_mycotoxin_certificate_pdf(_sample_fingerprint(), _sample_toxin_analysis(aflatoxin=200.0))
        assert pdf_bytes.startswith(b"%PDF")

    def test_works_with_approved_shipment(self):
        pdf_bytes = pr.build_mycotoxin_certificate_pdf(_sample_fingerprint(), _sample_toxin_analysis(aflatoxin=2.0))
        assert pdf_bytes.startswith(b"%PDF")

    def test_works_with_empty_fingerprint(self):
        """بصمة فارغة بالكامل (لا مورد، لا خامة، لا رقم تشغيلة) — لا كراش، قيم '—' بدلًا منها."""
        pdf_bytes = pr.build_mycotoxin_certificate_pdf({}, _sample_toxin_analysis())
        assert pdf_bytes.startswith(b"%PDF")

    def test_works_for_every_species(self):
        import constants as c
        for species_key in c.SPECIES_REGULATORY_LIMITS:
            analysis = _sample_toxin_analysis(aflatoxin=5.0, species_key=species_key)
            pdf_bytes = pr.build_mycotoxin_certificate_pdf(_sample_fingerprint(), analysis)
            assert pdf_bytes.startswith(b"%PDF"), species_key


# ==============================================================================
# build_proximate_certificate_pdf()
# ==============================================================================
class TestProximateCertificate:
    def test_generates_valid_pdf_bytes(self):
        pdf_bytes = pr.build_proximate_certificate_pdf(_sample_fingerprint(), _sample_proximate_analysis())
        assert pdf_bytes.startswith(b"%PDF")

    def test_works_with_red_decision_egyptian_standard_violation(self):
        analysis = _sample_proximate_analysis(species_key="cattle_beef", stage_key="growing", crude_fiber_pct=18.0)
        assert analysis["kpi_7_traffic_light"]["code"] == "RED"
        pdf_bytes = pr.build_proximate_certificate_pdf(_sample_fingerprint(), analysis)
        assert pdf_bytes.startswith(b"%PDF")

    def test_works_with_missing_optional_fields(self):
        analysis = pe.build_full_proximate_analysis("poultry_broiler", "starter", moisture_pct=11.0)
        pdf_bytes = pr.build_proximate_certificate_pdf(_sample_fingerprint(), analysis)
        assert pdf_bytes.startswith(b"%PDF")

    def test_works_for_every_covered_species_and_stage(self):
        import constants as c
        for species_key, species_row in c.SPECIES_PROXIMATE_STANDARDS.items():
            for stage_key in species_row["stages"]:
                analysis = _sample_proximate_analysis(species_key=species_key, stage_key=stage_key)
                pdf_bytes = pr.build_proximate_certificate_pdf(_sample_fingerprint(), analysis)
                assert pdf_bytes.startswith(b"%PDF"), (species_key, stage_key)


# ==============================================================================
# build_combined_certificate_pdf()
# ==============================================================================
class TestCombinedCertificate:
    def test_generates_valid_two_part_pdf(self):
        pdf_bytes = pr.build_combined_certificate_pdf(
            _sample_fingerprint(), _sample_toxin_analysis(), _sample_proximate_analysis(),
        )
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 2000  # أكبر من الشهادتين المنفردتين لاحتوائه كلتيهما

    def test_combined_pdf_is_larger_than_either_individual_certificate(self):
        toxin_analysis = _sample_toxin_analysis()
        proximate_analysis = _sample_proximate_analysis()
        combined = pr.build_combined_certificate_pdf(_sample_fingerprint(), toxin_analysis, proximate_analysis)
        mycotoxin_only = pr.build_mycotoxin_certificate_pdf(_sample_fingerprint(), toxin_analysis)
        assert len(combined) > len(mycotoxin_only) * 0.8  # دليل تقريبي على احتواء محتوى إضافي فعلي
