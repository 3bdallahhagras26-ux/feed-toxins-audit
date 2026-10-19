# -*- coding: utf-8 -*-
"""
tests/test_math_engine.py — اختبارات المحرك الحسابي الحتمي في app.py
================================================================================
تختبر compute_risk_ratios، compute_mri، compute_final_decision, compute_blending_ratio،
compute_storage_risk، compute_safe_storage_lifespan، compute_fcr_deterioration،
compute_financial_loss، compute_supplier_score، وbuild_full_analysis — الدوال الحتمية
البحتة التي لا تستدعي أي واجهة Streamlit ولا أي نموذج لغوي، فتُختبر بمعزل تام وبسرعة.

⚠️ عدة اختبارات هنا هي اختبارات ارتداد (Regression Tests) مباشرة لأخطاء حقيقية اكتُشفت
واختُبرت يدويًا أثناء بناء المشروع عبر عدة جلسات (مؤشَّرة صراحةً في اسم كل اختبار):
  - MRI Hard Floor يجب أن يُطبَّق فقط عند REJECT الصريح، لا لمجرد تجاوز سم لضعف الحد.
  - كارت الخلط يجب أن يعرض 0:1 تلقائيًا عند REJECT، لا نسبة خلط محسوبة تتعارض مع القرار.
  - عتبة الرفض لكل سم × قطاع (get_reject_multiple) وليست عتبة عامة واحدة.
تحويل هذه الاكتشافات اليدوية إلى اختبارات آلية دائمة هو بالضبط ما يمنع تكرارها مستقبلًا.
"""

import pytest

import app


# ==============================================================================
# compute_risk_ratios()
# ==============================================================================
class TestComputeRiskRatios:
    def test_basic_ratio_calculation(self):
        lab = {"aflatoxin_ppb": 40.0, "ochratoxin_ppb": None, "don_ppm": None,
               "zearalenone_ppm": None, "fumonisin_ppm": None}
        ratios = app.compute_risk_ratios(lab, "poultry_broiler")
        assert ratios["aflatoxin_ppb"] == pytest.approx(2.0)  # 40/20
        assert ratios["ochratoxin_ppb"] is None

    def test_missing_lab_value_yields_none_not_zero(self):
        ratios = app.compute_risk_ratios({}, "poultry_broiler")
        assert all(v is None for v in ratios.values())

    def test_non_numeric_value_yields_none_not_exception(self):
        lab = {"aflatoxin_ppb": "not a number"}
        ratios = app.compute_risk_ratios(lab, "poultry_broiler")
        assert ratios["aflatoxin_ppb"] is None

    def test_aquaculture_uses_its_own_tighter_accept_limit(self):
        """أفلاتوكسين أكوا accept_limit=10 (وليس 20 كالدواجن) — نفس التركيز يعطي نسبة أعلى."""
        lab = {"aflatoxin_ppb": 15.0, "ochratoxin_ppb": None, "don_ppm": None,
               "zearalenone_ppm": None, "fumonisin_ppm": None}
        broiler_ratio = app.compute_risk_ratios(lab, "poultry_broiler")["aflatoxin_ppb"]
        aqua_ratio = app.compute_risk_ratios(lab, "aquaculture")["aflatoxin_ppb"]
        assert aqua_ratio > broiler_ratio
        assert aqua_ratio == pytest.approx(1.5)  # 15/10


# ==============================================================================
# compute_final_decision() — بما فيها عتبة الرفض الخاصة بكل سم × قطاع
# ==============================================================================
class TestComputeFinalDecision:
    def _allowed_age_gate(self):
        return {"allowed": True, "reason_ar": ""}

    def _blocked_age_gate(self):
        return {"allowed": False, "reason_ar": "عمر أقل من الحد الأدنى"}

    def test_no_lab_data_rejects(self):
        decision = app.compute_final_decision({}, False, self._allowed_age_gate(), "poultry_broiler")
        assert decision["code"] == "REJECT"

    def test_all_within_limits_approves(self):
        ratios = {"aflatoxin_ppb": 0.3, "ochratoxin_ppb": 0.2, "don_ppm": 0.1,
                  "zearalenone_ppm": 0.1, "fumonisin_ppm": 0.1}
        decision = app.compute_final_decision(ratios, True, self._allowed_age_gate(), "poultry_broiler")
        assert decision["code"] == "APPROVE"

    def test_approaching_limit_without_binder_requires_binder(self):
        ratios = {"aflatoxin_ppb": 0.7, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        decision = app.compute_final_decision(ratios, False, self._allowed_age_gate(), "poultry_broiler")
        assert decision["code"] == "BINDER_REQUIRED"

    def test_approaching_limit_with_binder_already_added_approves(self):
        ratios = {"aflatoxin_ppb": 0.7, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        decision = app.compute_final_decision(ratios, True, self._allowed_age_gate(), "poultry_broiler")
        assert decision["code"] == "APPROVE"

    def test_moderate_breach_requires_blend(self):
        ratios = {"aflatoxin_ppb": 1.5, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        decision = app.compute_final_decision(ratios, False, self._allowed_age_gate(), "poultry_broiler")
        assert decision["code"] == "BLEND_REQUIRED"

    def test_severe_breach_rejects_broiler(self):
        """أفلاتوكسين دواجن: عتبة الرفض 2.5×. عند 2.6× يجب REJECT."""
        ratios = {"aflatoxin_ppb": 2.6, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        decision = app.compute_final_decision(ratios, False, self._allowed_age_gate(), "poultry_broiler")
        assert decision["code"] == "REJECT"

    def test_per_species_reject_multiple_aquaculture_stricter_than_broiler(self):
        """[ارتداد] أفلاتوكسين 1.6× لا يرفض في الدواجن (عتبة 2.5×) لكنه يرفض في الاستزراع
        السمكي (عتبة 1.5× المُضيَّقة عمدًا) — نفس النسبة الرقمية، قرار مختلف حسب القطاع."""
        ratios = {"aflatoxin_ppb": 1.6, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        broiler_decision = app.compute_final_decision(ratios, False, self._allowed_age_gate(), "poultry_broiler")
        aqua_decision = app.compute_final_decision(ratios, False, self._allowed_age_gate(), "aquaculture")
        assert broiler_decision["code"] != "REJECT"
        assert aqua_decision["code"] == "REJECT"
        assert "1.5" in aqua_decision["reason_ar"]

    def test_age_gate_forces_reject_even_for_moderate_breach(self):
        """[ارتداد] لو الخلط ممنوع عمريًا، أي تجاوز فوق الحد => REJECT مباشرة، حتى لو
        النسبة نفسها كانت ستُصنَّف BLEND_REQUIRED مع عمر مسموح."""
        ratios = {"aflatoxin_ppb": 1.5, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        decision = app.compute_final_decision(ratios, False, self._blocked_age_gate(), "poultry_broiler")
        assert decision["code"] == "REJECT"

    def test_age_gate_does_not_affect_already_approved_shipments(self):
        ratios = {"aflatoxin_ppb": 0.3, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        decision = app.compute_final_decision(ratios, True, self._blocked_age_gate(), "poultry_broiler")
        assert decision["code"] == "APPROVE"


# ==============================================================================
# compute_mri() — بما فيه الحد الأدنى الإجباري (Hard Floor) المُقيَّد بـ REJECT فقط
# ==============================================================================
class TestComputeMri:
    def test_no_data_returns_none_score(self):
        result = app.compute_mri({}, None, None, {"code": "REJECT", "reason_ar": ""})
        assert result["score"] is None

    def test_floor_applied_only_on_explicit_reject(self):
        """[ارتداد لباجّ حقيقي] الحد الأدنى (75) يجب أن يُطبَّق فقط عندما code == REJECT،
        وليس لمجرد تجاوز سم لضعف الحد بينما القرار النهائي لا يزال BLEND_REQUIRED."""
        ratios = {"aflatoxin_ppb": 2.2, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}  # >2x لكن <2.5x (عتبة الرفض)
        blend_decision = {"code": "BLEND_REQUIRED", "reason_ar": ""}
        result = app.compute_mri(ratios, None, None, blend_decision)
        assert result["floor_applied"] is False
        assert result["score"] < 75.0  # المعادلة الطبيعية فقط، بلا فرض حد أدنى

    def test_floor_applied_on_reject(self):
        ratios = {"aflatoxin_ppb": 3.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        reject_decision = {"code": "REJECT", "reason_ar": ""}
        result = app.compute_mri(ratios, None, None, reject_decision)
        assert result["floor_applied"] is True
        assert result["score"] >= 75.0

    def test_score_never_exceeds_100(self):
        ratios = {k: 10.0 for k in ["aflatoxin_ppb", "ochratoxin_ppb", "don_ppm", "zearalenone_ppm", "fumonisin_ppm"]}
        result = app.compute_mri(ratios, 35, 19, {"code": "REJECT", "reason_ar": ""})
        assert result["score"] <= 100.0

    def test_synergy_multiplier_triggers_when_both_toxins_cross_trigger_ratio(self):
        """DON وZEA كلاهما موثّق تآزرهما (×1.25) عند تجاوز كل منهما SYNERGY_TRIGGER_RATIO."""
        ratios = {"aflatoxin_ppb": None, "ochratoxin_ppb": None, "don_ppm": 0.6,
                  "zearalenone_ppm": 0.6, "fumonisin_ppm": None}
        result = app.compute_mri(ratios, None, None, {"code": "BINDER_REQUIRED", "reason_ar": ""})
        assert result["synergy_multiplier"] == pytest.approx(1.25)
        assert len(result["synergy_pairs_triggered"]) >= 1

    def test_no_synergy_multiplier_when_only_one_toxin_present(self):
        ratios = {"aflatoxin_ppb": 0.9, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        result = app.compute_mri(ratios, None, None, {"code": "BINDER_REQUIRED", "reason_ar": ""})
        assert result["synergy_multiplier"] == pytest.approx(1.0)


# ==============================================================================
# compute_blending_ratio() — بما فيه المزامنة مع القرار الحتمي (0:1 عند REJECT)
# ==============================================================================
class TestComputeBlendingRatio:
    def test_within_limits_needs_no_blending(self):
        ratios = {"aflatoxin_ppb": 0.5, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 10.0}
        result = app.compute_blending_ratio(ratios, lab, "poultry_broiler",
                                             {"code": "APPROVE", "reason_ar": ""})
        assert result["needed"] is False
        assert result.get("rejected", False) is False

    def test_reject_decision_forces_zero_one_regardless_of_math(self):
        """[ارتداد لباجّ حقيقي] حتى لو معادلة بيرسون تحسب نسبة خلط رياضيًا ممكنة، القرار
        REJECT يجب أن يفرض 0:1 — لا يجوز اقتراح خلط لشحنة مرفوضة بالكامل."""
        ratios = {"aflatoxin_ppb": 5.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 100.0}
        result = app.compute_blending_ratio(ratios, lab, "poultry_broiler",
                                             {"code": "REJECT", "reason_ar": ""})
        assert result["needed"] is False
        assert result["rejected"] is True
        assert result["ratio_text_contaminated_to_clean"] == "0:1"

    def test_moderate_breach_computes_valid_pearson_square_ratio(self):
        """أفلاتوكسين دواجن accept=20؛ H=40 (2×) => F = 100*20/40 = 50% ملوّث."""
        ratios = {"aflatoxin_ppb": 2.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 40.0}
        result = app.compute_blending_ratio(ratios, lab, "poultry_broiler",
                                             {"code": "BLEND_REQUIRED", "reason_ar": ""})
        assert result["needed"] is True
        assert result["contaminated_feed_percent"] == pytest.approx(50.0, abs=0.5)

    def test_default_l_is_zero_when_not_provided(self):
        """التوافق الخلفي: عدم تمرير clean_feed_toxin_levels إطلاقًا يجب أن يعطي نفس نتيجة
        L=0 القديمة تمامًا — لا تغيير في السلوك الافتراضي لأي مستخدم قائم."""
        ratios = {"aflatoxin_ppb": 2.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 40.0}
        decision = {"code": "BLEND_REQUIRED", "reason_ar": ""}
        without_param = app.compute_blending_ratio(ratios, lab, "poultry_broiler", decision)
        with_empty_dict = app.compute_blending_ratio(ratios, lab, "poultry_broiler", decision, {})
        assert without_param["contaminated_feed_percent"] == with_empty_dict["contaminated_feed_percent"]
        assert without_param.get("clean_feed_level_used", 0.0) == 0.0

    def test_nonzero_clean_feed_level_reduces_the_safe_blend_percentage(self):
        """[الميزة الجديدة] علف نظيف بتلوّث فعلي (لا صفر مطلق) يجب أن يعطي نسبة خلط آمنة
        أقل (أكثر تحفظًا) من افتراض L=0 — منطقيًا: كلما كان "النظيف" أقل نظافة، قلّت
        النسبة المسموح بها من الملوَّث الأصلي."""
        ratios = {"aflatoxin_ppb": 2.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 40.0}  # accept_limit=20 للدواجن => C=20, H=40
        decision = {"code": "BLEND_REQUIRED", "reason_ar": ""}

        best_case = app.compute_blending_ratio(ratios, lab, "poultry_broiler", decision, {"aflatoxin_ppb": 0.0})
        realistic = app.compute_blending_ratio(ratios, lab, "poultry_broiler", decision, {"aflatoxin_ppb": 5.0})

        assert realistic["contaminated_feed_percent"] < best_case["contaminated_feed_percent"]
        assert realistic["clean_feed_level_used"] == 5.0

    def test_clean_feed_level_matches_manual_pearson_square_calculation(self):
        """F = 100×(C−L)/(H−L). C=20 (accept_limit دواجن)، H=40، L=5 => F=100*15/35≈42.86%."""
        ratios = {"aflatoxin_ppb": 2.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 40.0}
        result = app.compute_blending_ratio(
            ratios, lab, "poultry_broiler", {"code": "BLEND_REQUIRED", "reason_ar": ""},
            {"aflatoxin_ppb": 5.0},
        )
        assert result["contaminated_feed_percent"] == pytest.approx(42.857, abs=0.1)

    def test_clean_feed_as_contaminated_as_shipment_fails_gracefully(self):
        """[حالة حافة] لو 'العلف النظيف' المُدخَل تركيزه أعلى من أو يساوي الشحنة نفسها
        لنفس السم (L >= H)، لا يوجد حل خلط منطقي — يجب رسالة واضحة، لا قسمة على صفر
        ولا نسبة سالبة/فوق 100%."""
        ratios = {"aflatoxin_ppb": 2.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 40.0}
        result = app.compute_blending_ratio(
            ratios, lab, "poultry_broiler", {"code": "BLEND_REQUIRED", "reason_ar": ""},
            {"aflatoxin_ppb": 40.0},  # L == H بالضبط
        )
        assert result["needed"] is False
        assert "ليس أقل تلوّثًا" in result["note"]

    def test_clean_feed_level_for_a_different_toxin_than_the_worst_one_is_ignored(self):
        """قيمة L محدَّدة لسم غير 'أسوأ سم' في هذه الشحنة يجب ألا تؤثر إطلاقًا — المعادلة
        تستخدم فقط L الخاص بالسم الفعلي المسبِّب للخلط."""
        ratios = {"aflatoxin_ppb": 2.0, "ochratoxin_ppb": None, "don_ppm": None,
                  "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab = {"aflatoxin_ppb": 40.0}
        decision = {"code": "BLEND_REQUIRED", "reason_ar": ""}
        without_irrelevant = app.compute_blending_ratio(ratios, lab, "poultry_broiler", decision, {})
        with_irrelevant = app.compute_blending_ratio(
            ratios, lab, "poultry_broiler", decision, {"don_ppm": 3.0}  # ليس أسوأ سم هنا
        )
        assert without_irrelevant["contaminated_feed_percent"] == with_irrelevant["contaminated_feed_percent"]


# ==============================================================================
# compute_storage_risk() و compute_safe_storage_lifespan()
# ==============================================================================
class TestStorageRisk:
    def test_missing_data_returns_undetermined(self):
        result = app.compute_storage_risk(None, None)
        assert result["combined_risk_factor"] == 0.0

    def test_cool_dry_storage_is_safe(self):
        result = app.compute_storage_risk(15, 8)
        assert result["combined_risk_factor"] == 0.0

    def test_hot_humid_storage_is_critical(self):
        result = app.compute_storage_risk(35, 19)
        assert result["combined_risk_factor"] == pytest.approx(1.0)

    def test_lifespan_shrinks_as_risk_increases(self):
        safe = app.compute_safe_storage_lifespan(15, 8, 0)
        risky = app.compute_safe_storage_lifespan(35, 19, 0)
        assert risky["effective_total_lifespan_days"] < safe["effective_total_lifespan_days"]

    def test_overdue_flag_when_elapsed_exceeds_lifespan(self):
        result = app.compute_safe_storage_lifespan(35, 19, 999)
        assert result["is_overdue"] is True
        assert result["days_remaining"] == 0


# ==============================================================================
# build_full_analysis() — اختبار تكاملي للـ Pipeline الكامل بمدخلات JSON اصطناعية
# ==============================================================================
class TestBuildFullAnalysis:
    def _minimal_parsed(self, **lab_overrides):
        lab_results = {"aflatoxin_ppb": None, "ochratoxin_ppb": None, "don_ppm": None,
                        "zearalenone_ppm": None, "fumonisin_ppm": None}
        lab_results.update(lab_overrides)
        return {
            "shipment_meta": {"supplier_name": "Test Supplier", "feed_type": "Corn",
                               "shipment_date": None, "quantity_tons": 20.0},
            "normalized_inputs": {
                "lab_results": lab_results,
                "storage": {"temperature_celsius": 25, "moisture_percent": 12, "storage_days": 5},
                "parameters": {"target_species": None, "flock_age_days": None,
                               "toxin_binder_added": False, "binder_type": None},
            },
            "parsing_audit": {"is_valid_input": True, "missing_critical_fields": [], "parsing_notes": ""},
        }

    def test_clean_shipment_approves(self):
        parsed = self._minimal_parsed(aflatoxin_ppb=5.0)
        analysis = app.build_full_analysis(parsed, baseline_fcr=1.6, feed_price=25.0,
                                            forced_species_key="poultry_broiler")
        assert analysis["final_decision"]["code"] == "APPROVE"
        assert analysis["species_key"] == "poultry_broiler"

    def test_manual_species_is_the_sole_source_of_truth_regardless_of_other_parameters(self):
        """[v3.0.0] لا LLM يُفسِّر نصًا حرًّا بعد الآن — forced_species_key (اختيار المستخدم
        اليدوي الإجباري من الواجهة) هو المصدر الوحيد لتحديد species_key دائمًا، بصرف النظر
        عن أي قيمة أخرى موجودة في parameters.target_species (حقل تاريخي من Schema القديم،
        لم يعد أي مسار إدخال حالي يملأه، لكن يبقى متوافقًا لو مُرِّر صراحة)."""
        parsed = self._minimal_parsed(aflatoxin_ppb=5.0)
        parsed["normalized_inputs"]["parameters"]["target_species"] = "aquaculture"
        analysis = app.build_full_analysis(parsed, 1.6, 25.0, forced_species_key="poultry_broiler")
        assert analysis["species_key"] == "poultry_broiler"
        assert "species_mismatch" not in analysis
        assert "llm_parsed_species_key" not in analysis

    def test_manual_flock_age_overrides_parsed_dict_age(self):
        parsed = self._minimal_parsed(aflatoxin_ppb=30.0)
        parsed["normalized_inputs"]["parameters"]["flock_age_days"] = 20
        analysis = app.build_full_analysis(parsed, 1.6, 25.0, "poultry_broiler", manual_flock_age_days=5)
        assert analysis["flock_age_days"] == 5
        assert analysis["flock_age_is_manual_override"] is True
        # عمر 5 أيام (بادي) => الخلط ممنوع => REJECT رغم أن النسبة (1.5×) كانت ستُصنَّف BLEND_REQUIRED
        assert analysis["final_decision"]["code"] == "REJECT"
        assert analysis["blending"]["ratio_text_contaminated_to_clean"] == "0:1"

    def test_no_manual_age_falls_back_to_parsed_dict_age(self):
        parsed = self._minimal_parsed(aflatoxin_ppb=5.0)
        parsed["normalized_inputs"]["parameters"]["flock_age_days"] = 20
        analysis = app.build_full_analysis(parsed, 1.6, 25.0, "poultry_broiler", manual_flock_age_days=None)
        assert analysis["flock_age_days"] == 20
        assert analysis["flock_age_is_manual_override"] is False

    def test_financial_loss_scales_with_quantity(self):
        parsed_small = self._minimal_parsed(aflatoxin_ppb=35.0)
        parsed_small["shipment_meta"]["quantity_tons"] = 10.0
        parsed_large = self._minimal_parsed(aflatoxin_ppb=35.0)
        parsed_large["shipment_meta"]["quantity_tons"] = 100.0

        small = app.build_full_analysis(parsed_small, 1.6, 25.0, "poultry_broiler")
        large = app.build_full_analysis(parsed_large, 1.6, 25.0, "poultry_broiler")
        assert large["financial"]["loss_egp"] > small["financial"]["loss_egp"]

    def test_missing_quantity_does_not_crash_financial_calc(self):
        parsed = self._minimal_parsed(aflatoxin_ppb=5.0)
        parsed["shipment_meta"]["quantity_tons"] = None
        analysis = app.build_full_analysis(parsed, 1.6, 25.0, "poultry_broiler")
        assert analysis["financial"]["loss_egp"] is None