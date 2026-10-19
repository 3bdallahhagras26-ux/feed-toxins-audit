# -*- coding: utf-8 -*-
"""
tests/test_integration.py — اختبارات تكاملية عبر Streamlit AppTest الرسمي (v3.0.0)
================================================================================
يستخدم هذا الملف streamlit.testing.v1.AppTest لتشغيل app.py فعليًا عبر محاكي تشغيل
حقيقي. ⚠️ إعادة بناء كاملة لـ v3.0.0: الشاشات الثلاث الجديدة (🧪 سموم فقط،
🔬 تدقيق كامل، 📋 بروكسيمات فقط) حلّت محل تبويبات طرق الإدخال القديمة (نص حر/ملف/
منظَّم) — لا LLM، لا Regex، لا نص حر في أي مسار الآن. كل مفاتيح الـ widgets مُسبوقة
بلاحقة الشاشة (tab1_/tab2_/tab3_) لأن كل شاشة تملك محدِّد قطاع/قطيع/عمر مستقلًا تمامًا.

⚠️ لا mock لاستدعاء شبكة هنا — لا حاجة له أصلًا: لا مسار في v3.0.0 يستدعي أي API
خارجي إطلاقًا (الملاحظة القديمة حول عزل AppTest عن sys.modules لم تعد ذات صلة).
"""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")
BROILER_LABEL = "دواجن تسمين (Broiler)"


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    return at


# ==============================================================================
# تحميل التطبيق وعناصر الواجهة الأساسية
# ==============================================================================
class TestAppLoadsCleanly:
    def test_app_runs_without_exception_on_first_load(self):
        at = _fresh_app()
        assert not at.exception

    def test_exactly_three_tabs_exist(self):
        at = _fresh_app()
        prefixes_present = {sb.key.split("_")[0] for sb in at.selectbox if sb.key and sb.key.startswith("tab")}
        assert prefixes_present == {"tab1", "tab2", "tab3"}

    def test_no_dashboard_metrics_before_any_analysis(self):
        at = _fresh_app()
        assert len(at.metric) == 0

    def test_no_sidebar_api_key_or_model_fields_remain(self):
        """[v3.0.0] حُذف الاتصال بـ LLM بالكامل — لا حقل مفتاح API ولا اختيار موديل
        في الشريط الجانبي بعد الآن."""
        at = _fresh_app()
        api_key_fields = [ti for ti in at.sidebar.text_input if "API" in (ti.label or "")]
        assert api_key_fields == []
        model_dropdowns = [sb for sb in at.sidebar.selectbox if "نموذج" in (sb.label or "")]
        assert model_dropdowns == []

    def test_sidebar_still_has_financial_inputs(self):
        at = _fresh_app()
        assert len(at.sidebar.number_input) >= 2


# ==============================================================================
# Tab 1 — تأمين القطيع والسموم الفطرية
# ==============================================================================
class TestTab1MycotoxinOnly:
    def test_species_dropdown_present_with_all_five_sectors_plus_placeholder(self):
        at = _fresh_app()
        species_box = [sb for sb in at.selectbox if sb.key == "tab1_species_select"][0]
        assert len(species_box.options) == 6

    def test_analyze_and_reset_buttons_present(self):
        at = _fresh_app()
        labels = {b.key: b.label for b in at.button}
        assert labels.get("tab1_analyze") == "تحليل الشحنة الآن"
        assert labels.get("tab1_reset") == "شحنة جديدة"

    def test_clicking_analyze_with_nothing_filled_warns_about_species_first(self):
        at = _fresh_app()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not at.exception
        assert any("القطاع المستهدف" in w.value for w in at.warning)

    def test_species_selected_but_no_toxin_values_shows_toxin_error(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert any("سم واحدة على الأقل" in e.value for e in at.error)

    def test_full_analysis_renders_eight_metrics(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(45.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not at.exception
        assert len(at.metric) == 8

    def test_approved_shipment_shows_approve_decision(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(2.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        decision = next(m for m in at.metric if "القرار" in m.label)
        assert "اعتماد" in decision.value

    def test_rejected_shipment_shows_reject_decision(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(100.0).run()  # 5x accept_limit
        at.button(key="tab1_analyze").click().run(timeout=30)
        decision = next(m for m in at.metric if "القرار" in m.label)
        assert "رفض" in decision.value

    def test_pdf_generation_button_appears_after_analysis_not_before(self):
        at = _fresh_app()
        assert not any((b.key or "").startswith("tab1") and "generate_pdf" in b.key for b in at.button)
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(5.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert any(b.key == "tab1_mycotoxin_generate_pdf" for b in at.button)

    def test_pdf_download_button_appears_after_generate_click(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(5.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        at.button(key="tab1_mycotoxin_generate_pdf").click().run(timeout=30)
        assert not at.exception
        assert len(at.download_button) == 1

    def test_reset_clears_analysis_and_fields(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(45.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert len(at.metric) == 8

        at.button(key="tab1_reset").click().run(timeout=30)
        assert len(at.metric) == 0
        assert at.number_input(key="tab1_aflatoxin_ppb").value is None

    def test_reset_does_not_clear_supplier_history(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(5.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        at.number_input(key="tab1_aflatoxin_ppb").set_value(8.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        at.button(key="tab1_reset").click().run(timeout=30)
        assert len(at.session_state.get("supplier_history", {})) >= 1

    def test_shipment_fingerprint_fields_present(self):
        at = _fresh_app()
        fingerprint_fields = {ti.key for ti in at.text_input if ti.key and ti.key.startswith("tab1_")}
        assert "tab1_feed_type" in fingerprint_fields
        assert "tab1_supplier_name" in fingerprint_fields
        assert "tab1_batch_number" in fingerprint_fields

    def test_fingerprint_batch_number_appears_in_report_header_when_filled(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.text_input(key="tab1_supplier_name").input("شركة دلتا للأعلاف").run()
        at.text_input(key="tab1_batch_number").input("TRK-0091").run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(5.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert any("TRK-0091" in c.value for c in at.caption)


# ==============================================================================
# Tab 3 — التحليل التقريبي فقط
# ==============================================================================
class TestTab3ProximateOnly:
    def test_species_and_analyze_button_present(self):
        at = _fresh_app()
        assert any(sb.key == "tab3_species_select" for sb in at.selectbox)
        assert any(b.key == "tab3_analyze" for b in at.button)

    def test_stage_selector_appears_only_after_species_chosen(self):
        at = _fresh_app()
        assert not any(sb.key == "tab3_prox_stage_select" for sb in at.selectbox)
        at.selectbox(key="tab3_species_select").select(BROILER_LABEL).run()
        assert any(sb.key == "tab3_prox_stage_select" for sb in at.selectbox)

    def test_unsupported_species_shows_warning_no_stage_selector(self):
        at = _fresh_app()
        at.selectbox(key="tab3_species_select").select("دواجن بياض (Layer)").run()
        assert any("لا تتوفر معايير بروكسيمات" in w.value for w in at.warning)
        assert not any(sb.key == "tab3_prox_stage_select" for sb in at.selectbox)

    def test_full_proximate_analysis_renders_seven_metrics(self):
        at = _fresh_app()
        at.selectbox(key="tab3_species_select").select(BROILER_LABEL).run()
        at.selectbox(key="tab3_prox_stage_select").select("بادي (Starter)").run()
        at.number_input(key="tab3_prox_moisture_pct").set_value(11.0).run()
        at.number_input(key="tab3_prox_cp_pct").set_value(24.0).run()
        at.number_input(key="tab3_prox_ee_pct").set_value(3.5).run()
        at.number_input(key="tab3_prox_cf_pct").set_value(2.5).run()
        at.number_input(key="tab3_prox_ash_pct").set_value(4.5).run()
        at.button(key="tab3_analyze").click().run(timeout=30)
        assert not at.exception
        assert len(at.metric) == 7

    def test_missing_moisture_shows_error(self):
        at = _fresh_app()
        at.selectbox(key="tab3_species_select").select(BROILER_LABEL).run()
        at.selectbox(key="tab3_prox_stage_select").select("بادي (Starter)").run()
        at.number_input(key="tab3_prox_cp_pct").set_value(24.0).run()
        at.button(key="tab3_analyze").click().run(timeout=30)
        assert any("الرطوبة" in e.value for e in at.error)

    def test_nitrogen_mode_toggle_switches_input_field(self):
        at = _fresh_app()
        at.selectbox(key="tab3_species_select").select(BROILER_LABEL).run()
        radio = [r for r in at.radio if r.key == "tab3_protein_mode"][0]
        radio.set_value("نسبة النيتروجين (يُحسَب تلقائيًا ×6.25)").run()
        assert any(ni.key == "tab3_prox_n_pct" for ni in at.number_input)
        assert not any(ni.key == "tab3_prox_cp_pct" for ni in at.number_input)

    def test_reset_clears_proximate_fields(self):
        at = _fresh_app()
        at.selectbox(key="tab3_species_select").select(BROILER_LABEL).run()
        at.selectbox(key="tab3_prox_stage_select").select("بادي (Starter)").run()
        at.number_input(key="tab3_prox_moisture_pct").set_value(11.0).run()
        at.button(key="tab3_reset").click().run(timeout=30)
        assert at.number_input(key="tab3_prox_moisture_pct").value is None


# ==============================================================================
# Tab 2 — التدقيق الكامل والشامل
# ==============================================================================
class TestTab2CombinedAudit:
    def test_both_toxin_and_proximate_fields_present(self):
        at = _fresh_app()
        assert any(ni.key == "tab2_aflatoxin_ppb" for ni in at.number_input)
        assert any(ni.key == "tab2_prox_moisture_pct" for ni in at.number_input)

    def test_toxins_only_produces_only_toxin_metrics(self):
        at = _fresh_app()
        at.selectbox(key="tab2_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab2_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab2_analyze").click().run(timeout=30)
        assert not at.exception
        assert len(at.metric) == 8

    def test_proximates_only_produces_only_proximate_metrics(self):
        at = _fresh_app()
        at.selectbox(key="tab2_species_select").select(BROILER_LABEL).run()
        at.selectbox(key="tab2_prox_stage_select").select("بادي (Starter)").run()
        at.number_input(key="tab2_prox_moisture_pct").set_value(11.0).run()
        at.number_input(key="tab2_prox_cp_pct").set_value(24.0).run()
        at.number_input(key="tab2_prox_ee_pct").set_value(3.5).run()
        at.number_input(key="tab2_prox_cf_pct").set_value(2.5).run()
        at.number_input(key="tab2_prox_ash_pct").set_value(4.5).run()
        at.button(key="tab2_analyze").click().run(timeout=30)
        assert not at.exception
        assert len(at.metric) == 7

    def test_both_provided_produces_fifteen_combined_metrics(self):
        at = _fresh_app()
        at.selectbox(key="tab2_species_select").select(BROILER_LABEL).run()
        at.selectbox(key="tab2_prox_stage_select").select("بادي (Starter)").run()
        at.number_input(key="tab2_aflatoxin_ppb").set_value(10.0).run()
        at.number_input(key="tab2_prox_moisture_pct").set_value(11.0).run()
        at.number_input(key="tab2_prox_cp_pct").set_value(24.0).run()
        at.number_input(key="tab2_prox_ee_pct").set_value(3.5).run()
        at.number_input(key="tab2_prox_cf_pct").set_value(2.5).run()
        at.number_input(key="tab2_prox_ash_pct").set_value(4.5).run()
        at.button(key="tab2_analyze").click().run(timeout=30)
        assert not at.exception
        assert len(at.metric) == 15

    def test_neither_provided_shows_clear_error(self):
        at = _fresh_app()
        at.selectbox(key="tab2_species_select").select(BROILER_LABEL).run()
        at.button(key="tab2_analyze").click().run(timeout=30)
        assert any("بيانات سموم" in e.value or "بروكسيمات" in e.value for e in at.error)

    def test_combined_pdf_button_appears_after_analysis(self):
        at = _fresh_app()
        at.selectbox(key="tab2_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab2_aflatoxin_ppb").set_value(5.0).run()
        at.button(key="tab2_analyze").click().run(timeout=30)
        assert any(b.key == "tab2_combined_generate_pdf" for b in at.button)


# ==============================================================================
# حراسة ترتيب الأزرار — لا تصادم substring بين الشاشات الثلاث
# ==============================================================================
class TestButtonLabelsDoNotCollideAcrossTabs:
    def test_each_analyze_button_has_a_unique_distinguishable_label(self):
        at = _fresh_app()
        analyze_buttons = {b.key: b.label for b in at.button if b.key and b.key.endswith("_analyze")}
        assert len(analyze_buttons) == 3
        assert len(set(analyze_buttons.values())) == 3  # لا تسميتان متطابقتان

    def test_tab1_analyze_label_unaffected_by_other_tabs_buttons(self):
        at = _fresh_app()
        matches = [b for b in at.button if "تحليل" in b.label and b.key == "tab1_analyze"]
        assert len(matches) == 1