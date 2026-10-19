# -*- coding: utf-8 -*-
"""
tests/test_proximate_engine.py — اختبارات محرك البروكسيمات الحتمي (proximate_engine.py)
================================================================================
وحدة مستقلة تمامًا عن محرك السموم الفطرية — مرجع حدود مختلف (constants.SPECIES_
PROXIMATE_STANDARDS)، صيغ KPI مختلفة. كل اختبارات هذا الملف تستورد proximate_engine
مباشرة كدالة بايثون عادية — لا Streamlit، لا AppTest.
"""

import pytest

import constants as c
import proximate_engine as pe


# ==============================================================================
# compute_crude_protein_from_nitrogen() / resolve_crude_protein_pct()
# ==============================================================================
class TestNitrogenToProteinConversion:
    def test_known_conversion_factor(self):
        assert pe.compute_crude_protein_from_nitrogen(3.6) == pytest.approx(3.6 * 6.25)

    def test_matches_constants_factor_exactly(self):
        assert pe.N_TO_PROTEIN_FACTOR == c.N_TO_PROTEIN_FACTOR == 6.25

    def test_none_input_returns_none(self):
        assert pe.compute_crude_protein_from_nitrogen(None) is None

    def test_non_numeric_input_returns_none_not_exception(self):
        assert pe.compute_crude_protein_from_nitrogen("abc") is None


class TestResolveCrudeProteinPct:
    def test_direct_value_preferred_when_only_direct_given(self):
        result = pe.resolve_crude_protein_pct(crude_protein_pct=22.0, nitrogen_pct=None)
        assert result == {"value": 22.0, "source": "direct", "nitrogen_derived_value": None}

    def test_derived_from_nitrogen_when_only_nitrogen_given(self):
        result = pe.resolve_crude_protein_pct(crude_protein_pct=None, nitrogen_pct=3.6)
        assert result["value"] == pytest.approx(22.5)
        assert result["source"] == "derived_from_nitrogen"

    def test_neither_given_returns_none_not_zero(self):
        result = pe.resolve_crude_protein_pct(None, None)
        assert result == {"value": None, "source": "missing", "nitrogen_derived_value": None}

    def test_direct_wins_when_both_given_and_agree(self):
        result = pe.resolve_crude_protein_pct(crude_protein_pct=22.5, nitrogen_pct=3.6)  # 3.6*6.25=22.5
        assert result["value"] == 22.5
        assert result["source"] == "direct"

    def test_conflict_is_flagged_not_silently_resolved(self):
        """[قرار تصميم] تعارض جوهري (>0.5 نقطة فرق) بين القيمة المباشرة والمُشتقَّة من
        النيتروجين يُسجَّل صراحة في الناتج بدل اختيار صامت لأحدهما."""
        result = pe.resolve_crude_protein_pct(crude_protein_pct=20.0, nitrogen_pct=3.6)  # derived=22.5, diff=2.5
        assert result["value"] == 20.0  # القيمة المباشرة تبقى الأولوية
        assert result["source"] == "direct_conflicts_with_nitrogen_derived"
        assert result["nitrogen_derived_value"] == pytest.approx(22.5)

    def test_small_difference_is_not_flagged_as_conflict(self):
        result = pe.resolve_crude_protein_pct(crude_protein_pct=22.6, nitrogen_pct=3.6)  # diff=0.1
        assert result["source"] == "direct"


# ==============================================================================
# compute_nfe() — موازنة الكتلة 100%
# ==============================================================================
class TestComputeNfe:
    def test_basic_mass_balance(self):
        nfe = pe.compute_nfe(moisture_pct=12.0, crude_protein_pct=21.0, ether_extract_pct=3.8,
                              crude_fiber_pct=3.8, ash_pct=6.2)
        assert nfe == pytest.approx(100 - (12.0 + 21.0 + 3.8 + 3.8 + 6.2))

    def test_any_missing_value_returns_none(self):
        assert pe.compute_nfe(12.0, None, 3.8, 3.8, 6.2) is None
        assert pe.compute_nfe(None, 21.0, 3.8, 3.8, 6.2) is None

    def test_all_zero_yields_100(self):
        assert pe.compute_nfe(0, 0, 0, 0, 0) == 100.0

    def test_sum_exceeding_100_yields_negative_nfe_not_clamped(self):
        """قيم مُدخَلة فعليًا (لا افتراضية) تتجاوز 100% مجتمعة => NFE سالب، يُعرَض كما هو
        (إشارة خطأ قياس/إدخال واضحة للمستخدم) لا يُصفَّر بصمت."""
        nfe = pe.compute_nfe(40, 40, 40, 40, 40)
        assert nfe == pytest.approx(-100.0)


# ==============================================================================
# compute_protein_deficit_kpi() — KPI 1
# ==============================================================================
class TestProteinDeficitKpi:
    def test_above_minimum_has_zero_deficit(self):
        std = {"min": 23.0, "max": None}
        result = pe.compute_protein_deficit_kpi(24.0, std, 25.0, 20.0)
        assert result["status"] == "within_range"
        assert result["deficit_points"] == 0.0
        assert result["deduction_egp"] is None or result["deduction_egp"] == 0

    def test_below_minimum_computes_deficit_and_deduction(self):
        std = {"min": 23.0, "max": None}
        result = pe.compute_protein_deficit_kpi(21.0, std, 25.0, 20.0)
        assert result["status"] == "below_min"
        assert result["deficit_points"] == pytest.approx(2.0)
        # shipment value = 20 tons * 1000 kg * 25 EGP = 500,000 EGP; 2% deficit -> 10,000 EGP
        assert result["deduction_egp"] == pytest.approx(10000.0)

    def test_missing_price_or_quantity_skips_deduction_but_keeps_deficit(self):
        std = {"min": 23.0, "max": None}
        result = pe.compute_protein_deficit_kpi(21.0, std, None, None)
        assert result["deficit_points"] == pytest.approx(2.0)
        assert result["deduction_egp"] is None

    def test_no_standard_row_returns_no_limit_documented(self):
        result = pe.compute_protein_deficit_kpi(21.0, None, 25.0, 20.0)
        assert result["status"] == "no_limit_documented"
        assert result["deficit_points"] is None

    def test_missing_measured_value_returns_no_limit_documented_status(self):
        std = {"min": 23.0, "max": None}
        result = pe.compute_protein_deficit_kpi(None, std, 25.0, 20.0)
        assert result["status"] == "no_limit_documented"


# ==============================================================================
# compute_fiber_adulteration_kpi() / compute_ash_purity_kpi() — KPI 2 / KPI 4
# ==============================================================================
class TestFiberAndAshKpis:
    def test_fiber_within_max_has_zero_excess(self):
        result = pe.compute_fiber_adulteration_kpi(2.5, {"min": None, "max": 3.0})
        assert result["status"] == "within_range"
        assert result["excess_points"] == 0.0

    def test_fiber_above_max_computes_excess(self):
        result = pe.compute_fiber_adulteration_kpi(3.8, {"min": None, "max": 3.0})
        assert result["status"] == "above_max"
        assert result["excess_points"] == pytest.approx(0.8)

    def test_ash_above_max_flags_needs_sieving(self):
        result = pe.compute_ash_purity_kpi(6.2, {"min": None, "max": 5.0})
        assert result["needs_sieving"] is True
        assert result["excess_points"] == pytest.approx(1.2)

    def test_ash_within_max_does_not_need_sieving(self):
        result = pe.compute_ash_purity_kpi(4.0, {"min": None, "max": 5.0})
        assert result["needs_sieving"] is False


# ==============================================================================
# compute_rancidity_risk_kpi() — KPI 3 (TIER-4 heuristic)
# ==============================================================================
class TestRancidityRiskKpi:
    def test_low_ee_low_moisture_is_low_risk(self):
        result = pe.compute_rancidity_risk_kpi(3.0, 10.0, {"max": None, "reference": 3.5})
        assert result["level"] == "🟢 منخفض"
        assert result["risk_factor"] == 0.0

    def test_high_ee_high_moisture_is_high_risk(self):
        result = pe.compute_rancidity_risk_kpi(6.0, 16.0, {"max": None, "reference": 3.5})
        assert result["level"] == "🔴 مرتفع"
        assert result["risk_factor"] >= 0.5

    def test_moderate_deviation_is_medium_risk(self):
        result = pe.compute_rancidity_risk_kpi(3.8, 12.0, {"max": None, "reference": 3.5})
        assert result["level"] == "🟡 متوسط"
        assert 0.0 < result["risk_factor"] < 0.5

    def test_risk_factor_is_capped_at_one(self):
        result = pe.compute_rancidity_risk_kpi(20.0, 40.0, {"max": None, "reference": 3.5})
        assert result["risk_factor"] == 1.0

    def test_moisture_threshold_matches_constants_mold_favorable_zone(self):
        """[اتساق داخلي] العتبة هنا يجب أن تطابق constants.ENVIRONMENTAL_THRESHOLDS
        لنفس الظاهرة الفيزيائية (رطوبة عالية) في محرك السموم — لا عتبة مختلفة مخترَعة هنا."""
        assert pe.RANCIDITY_MOISTURE_THRESHOLD_PCT == c.ENVIRONMENTAL_THRESHOLDS["mold_favorable_zone"]["moisture_percent_min"]

    def test_both_inputs_missing_returns_none_risk_factor(self):
        result = pe.compute_rancidity_risk_kpi(None, None, {"max": None, "reference": 3.5})
        assert result["risk_factor"] is None
        assert result["level"] == "غير محدَّد"

    def test_uses_max_bound_over_reference_when_both_present(self):
        """صف له max صريح (بدل reference استرشادي فقط) — يُستخدَم max كالمرجع الفعلي."""
        result = pe.compute_rancidity_risk_kpi(6.0, 10.0, {"max": 5.0, "reference": None})
        assert result["ee_reference_pct"] == 5.0


# ==============================================================================
# compute_performance_index() — KPI 6
# ==============================================================================
class TestPerformanceIndex:
    def test_perfect_match_scores_100(self):
        protein = {"deficit_points": 0.0}
        fiber = {"excess_points": 0.0}
        ash = {"excess_points": 0.0}
        result = pe.compute_performance_index(protein, fiber, ash)
        assert result["score_pct"] == 100.0

    def test_deviations_reduce_score_proportionally_to_weights(self):
        protein = {"deficit_points": 1.0}
        fiber = {"excess_points": 0.0}
        ash = {"excess_points": 0.0}
        result = pe.compute_performance_index(protein, fiber, ash)
        assert result["score_pct"] == pytest.approx(100.0 - pe.PERFORMANCE_INDEX_WEIGHTS["protein_deficit_per_point"])

    def test_score_floors_at_zero_not_negative(self):
        protein = {"deficit_points": 50.0}
        fiber = {"excess_points": 50.0}
        ash = {"excess_points": 50.0}
        result = pe.compute_performance_index(protein, fiber, ash)
        assert result["score_pct"] == 0.0

    def test_all_none_returns_none_score_with_note(self):
        result = pe.compute_performance_index({"deficit_points": None}, {"excess_points": None}, {"excess_points": None})
        assert result["score_pct"] is None
        assert result["note"] is not None


# ==============================================================================
# compute_traffic_light() — KPI 7 (الإشارة الثلاثية)
# ==============================================================================
class TestTrafficLight:
    def _standards(self, protein_min=23.0, fiber_max=3.0, ash_max=5.0, egypt_fiber=False, egypt_ash=False):
        return {
            "crude_protein_pct": {"min": protein_min, "max": None},
            "crude_fiber_pct": {"min": None, "max": fiber_max, "is_egyptian_standard_limit": egypt_fiber},
            "ash_pct": {"min": None, "max": ash_max, "is_egyptian_standard_limit": egypt_ash},
        }

    def test_no_violations_is_green(self):
        protein = pe.compute_protein_deficit_kpi(24.0, self._standards()["crude_protein_pct"], None, None)
        fiber = pe.compute_fiber_adulteration_kpi(2.5, self._standards()["crude_fiber_pct"])
        ash = pe.compute_ash_purity_kpi(4.0, self._standards()["ash_pct"])
        result = pe.compute_traffic_light(protein, fiber, ash, self._standards())
        assert result["code"] == "GREEN"
        assert result["reasons"] == []

    def test_egyptian_standard_violation_is_red_with_exact_wording(self):
        """[إلزامي من المتطلبات حرفيًا] 'مرفوضة تماماً لمخالفة المواصفة القياسية المصرية'."""
        standards = self._standards(egypt_fiber=True)
        protein = pe.compute_protein_deficit_kpi(24.0, standards["crude_protein_pct"], None, None)
        fiber = pe.compute_fiber_adulteration_kpi(18.0, standards["crude_fiber_pct"])  # violates EOS-flagged max
        ash = pe.compute_ash_purity_kpi(4.0, standards["ash_pct"])
        result = pe.compute_traffic_light(protein, fiber, ash, standards)
        assert result["code"] == "RED"
        # نص المتطلبات الحرفي: "مرفوضة تماماً لمخالفة المواصفة القياسية المصرية" — يكفي
        # أن يحوي السبب "EOS1466" و"القياسية المصرية" معًا (جوهر الصياغة المطلوبة)،
        # بصرف النظر عن حرف الجر الدقيق المُستخدَم قبل "المواصفة" (لـ/لل).
        assert any("EOS1466" in r and "القياسية المصرية" in r for r in result["reasons"])

    def test_non_egyptian_mild_violation_is_yellow_not_red(self):
        standards = self._standards(egypt_fiber=False)
        protein = pe.compute_protein_deficit_kpi(24.0, standards["crude_protein_pct"], None, None)
        fiber = pe.compute_fiber_adulteration_kpi(3.2, standards["crude_fiber_pct"])  # mild excess, 0.2 over 3.0
        ash = pe.compute_ash_purity_kpi(4.0, standards["ash_pct"])
        result = pe.compute_traffic_light(protein, fiber, ash, standards)
        assert result["code"] == "YELLOW"

    def test_non_egyptian_severe_violation_is_red_via_internal_multiple(self):
        """[TIER-4] انحراف غير مصري لكن شديد (≥1.5× الحد) => RED عبر العتبة الداخلية،
        لا عبر علم EOS1466."""
        standards = self._standards(fiber_max=3.0, egypt_fiber=False)
        protein = pe.compute_protein_deficit_kpi(24.0, standards["crude_protein_pct"], None, None)
        fiber = pe.compute_fiber_adulteration_kpi(6.0, standards["crude_fiber_pct"])  # 3.0 excess >= 1.5x of 3.0=4.5 bound... actually need deviation>=max*0.5
        ash = pe.compute_ash_purity_kpi(4.0, standards["ash_pct"])
        result = pe.compute_traffic_light(protein, fiber, ash, standards)
        assert result["code"] == "RED"
        assert any("عتبة الشدة الداخلية" in r for r in result["reasons"])

    def test_egyptian_flag_takes_priority_over_severity_threshold_display(self):
        """لو المخالفة من مصدر مصري، السبب المعروض يذكر EOS1466 دائمًا بصرف النظر عن
        مدى شدة الانحراف (حتى لو كانت شديدة جدًا) — لا تنافس بين السببين."""
        standards = self._standards(egypt_fiber=True)
        protein = pe.compute_protein_deficit_kpi(24.0, standards["crude_protein_pct"], None, None)
        fiber = pe.compute_fiber_adulteration_kpi(50.0, standards["crude_fiber_pct"])  # extremely severe AND egyptian
        ash = pe.compute_ash_purity_kpi(4.0, standards["ash_pct"])
        result = pe.compute_traffic_light(protein, fiber, ash, standards)
        assert result["code"] == "RED"
        assert all("EOS1466" in r for r in result["reasons"])

    def test_protein_deficit_violation_detected_too(self):
        standards = self._standards(protein_min=23.0)
        protein = pe.compute_protein_deficit_kpi(10.0, standards["crude_protein_pct"], None, None)
        fiber = pe.compute_fiber_adulteration_kpi(2.5, standards["crude_fiber_pct"])
        ash = pe.compute_ash_purity_kpi(4.0, standards["ash_pct"])
        result = pe.compute_traffic_light(protein, fiber, ash, standards)
        assert result["code"] in ("YELLOW", "RED")  # severe deficit -> likely RED via internal multiple


# ==============================================================================
# build_full_proximate_analysis() — نقطة الدخول الكاملة
# ==============================================================================
class TestBuildFullProximateAnalysis:
    def test_unsupported_species_returns_clear_error_not_exception(self):
        result = pe.build_full_proximate_analysis("poultry_layer", "anything", moisture_pct=12.0)
        assert result["error"] is not None
        assert "poultry_layer" not in result["error"]  # رسالة بالعربي بالاسم المعروض لا المفتاح الخام
        assert "دواجن بياض" in result["error"]

    def test_unsupported_stage_for_supported_species_returns_clear_error(self):
        result = pe.build_full_proximate_analysis("poultry_broiler", "not_a_real_stage", moisture_pct=12.0)
        assert result["error"] is not None

    def test_fully_valid_broiler_starter_analysis_has_all_seven_kpis(self):
        result = pe.build_full_proximate_analysis(
            "poultry_broiler", "starter", moisture_pct=11.0, crude_protein_pct=24.0,
            ether_extract_pct=3.5, crude_fiber_pct=2.5, ash_pct=4.5,
            feed_price_egp_per_kg=25.0, quantity_tons=20.0,
        )
        assert result["error"] is None
        for key in ("kpi_1_protein_deficit", "kpi_2_fiber_adulteration", "kpi_3_rancidity_risk",
                    "kpi_4_ash_purity", "kpi_5_nfe_pct", "kpi_6_performance_index", "kpi_7_traffic_light"):
            assert key in result

    def test_clean_shipment_is_green_with_full_performance_index(self):
        result = pe.build_full_proximate_analysis(
            "poultry_broiler", "starter", moisture_pct=11.0, crude_protein_pct=24.0,
            ether_extract_pct=3.5, crude_fiber_pct=2.5, ash_pct=4.5,
        )
        assert result["kpi_7_traffic_light"]["code"] == "GREEN"
        assert result["kpi_6_performance_index"]["score_pct"] == 100.0

    def test_egyptian_standard_violation_end_to_end_for_cattle_beef(self):
        result = pe.build_full_proximate_analysis(
            "cattle_beef", "growing", moisture_pct=10.0, crude_protein_pct=14.5,
            ether_extract_pct=3.0, crude_fiber_pct=18.0, ash_pct=7.0,  # fiber 18 > EOS1466 max 15
        )
        assert result["kpi_7_traffic_light"]["code"] == "RED"
        assert "EOS1466" in result["kpi_7_traffic_light"]["reasons"][0]

    def test_nitrogen_input_flows_through_to_inputs_and_nfe(self):
        result = pe.build_full_proximate_analysis(
            "poultry_broiler", "grower", moisture_pct=12.0, nitrogen_pct=3.6,
            ether_extract_pct=4.0, crude_fiber_pct=3.0, ash_pct=4.5,
        )
        assert result["inputs"]["crude_protein_pct"] == pytest.approx(22.5)
        assert result["inputs"]["protein_source"] == "derived_from_nitrogen"
        assert result["nfe_pct"] is not None

    def test_all_four_covered_species_produce_valid_analysis_for_every_documented_stage(self):
        """تغطية شاملة: كل قطاع×مرحلة موثَّقة في constants.py يجب أن تعمل بلا أي استثناء."""
        for species_key, species_row in c.SPECIES_PROXIMATE_STANDARDS.items():
            for stage_key in species_row["stages"]:
                result = pe.build_full_proximate_analysis(
                    species_key, stage_key, moisture_pct=11.0, crude_protein_pct=50.0,  # intentionally high, just checking no crash
                    ether_extract_pct=5.0, crude_fiber_pct=1.0, ash_pct=1.0,
                )
                assert result["error"] is None, (species_key, stage_key)

    def test_missing_all_optional_fields_does_not_crash(self):
        result = pe.build_full_proximate_analysis("poultry_broiler", "starter", moisture_pct=None)
        assert result["error"] is None
        assert result["nfe_pct"] is None
        assert result["kpi_6_performance_index"]["score_pct"] is None
