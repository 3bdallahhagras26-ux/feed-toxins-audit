# -*- coding: utf-8 -*-
"""
tests/test_structured_input.py — اختبارات الإدخال اليدوي المنظم (v3.0.0)
================================================================================
منذ v3.0.0، الإدخال اليدوي المنظم هو **المسار الوحيد** لكل الشاشات الثلاث (لا نص
حر، لا ملفات، لا LLM، لا Regex). هذا الملف يركّز على الشاشة الأولى (🧪 سموم فقط،
مفاتيح tab1_*) كممثل كامل للآلية — راجع test_integration.py لتغطية الشاشتين
الأخريين (2 و3) بنفس الآلية.
"""

import os

from streamlit.testing.v1 import AppTest

import app

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")
BROILER_LABEL = "دواجن تسمين (Broiler)"


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    return at


# ==============================================================================
# build_structured_parsed_json() — بناء الـ Schema من الحقول الرقمية مباشرة
# ==============================================================================
class TestBuildStructuredParsedJson:
    def test_schema_keys_are_stable(self):
        lab = {k: None for k in app.TOXIN_KEYS}
        storage = {"temperature_celsius": None, "moisture_percent": None, "storage_days": None}
        result = app.build_structured_parsed_json(lab, storage)
        assert set(result.keys()) == {"shipment_meta", "normalized_inputs", "parsing_audit"}
        assert set(result["shipment_meta"].keys()) == {
            "supplier_name", "feed_type", "shipment_date", "quantity_tons", "flock_name", "species_key_used",
        }

    def test_all_none_lab_results_reported_as_missing(self):
        lab = {k: None for k in app.TOXIN_KEYS}
        storage = {"temperature_celsius": None, "moisture_percent": None, "storage_days": None}
        result = app.build_structured_parsed_json(lab, storage)
        assert set(result["parsing_audit"]["missing_critical_fields"]) == set(app.TOXIN_KEYS)

    def test_parsing_notes_document_no_llm_no_regex(self):
        lab = {k: None for k in app.TOXIN_KEYS}
        result = app.build_structured_parsed_json(lab, {})
        notes = result["parsing_audit"]["parsing_notes"]
        assert "no LLM" in notes
        assert "no regex" in notes

    def test_flock_name_and_species_key_used_are_passed_through(self):
        lab = {k: None for k in app.TOXIN_KEYS}
        result = app.build_structured_parsed_json(lab, {}, flock_name="قطيع الحلاب", species_key_used="cattle_dairy")
        assert result["shipment_meta"]["flock_name"] == "قطيع الحلاب"
        assert result["shipment_meta"]["species_key_used"] == "cattle_dairy"

    def test_feeds_build_full_analysis_without_error(self):
        lab = {"aflatoxin_ppb": 12.0, "ochratoxin_ppb": None, "don_ppm": None,
               "zearalenone_ppm": None, "fumonisin_ppm": None}
        storage = {"temperature_celsius": 28.0, "moisture_percent": 13.0, "storage_days": 5}
        parsed = app.build_structured_parsed_json(lab, storage, quantity_tons=15.0)
        analysis = app.build_full_analysis(parsed, 1.6, 25.0, "poultry_broiler")
        assert analysis["species_key"] == "poultry_broiler"
        assert analysis["risk_ratios"]["aflatoxin_ppb"] == 12.0 / 20.0


# ==============================================================================
# التحقق والتثبيت (Tab 1 كممثل للآلية)
# ==============================================================================
class TestAllEmptyToxinsShowsValidationError:
    def test_all_empty_toxins_shows_validation_error(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not at.exception
        assert any("سم واحدة على الأقل" in e.value for e in at.error)
        assert "tab1_last_analysis" not in at.session_state


class TestOneToxinFilledPassesValidation:
    def test_one_toxin_filled_passes_validation(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_don_ppm").set_value(2.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not at.exception
        assert len(at.metric) == 8
        assert not any("سم واحدة على الأقل" in e.value for e in at.error)


class TestPartialInputParsedCorrectly:
    def test_partial_input_parsed_correctly(self):
        """بعض السموم None، بعضها مُدخَل — القيم الناقصة تبقى None، لا 0.0."""
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(45.0).run()
        at.number_input(key="tab1_don_ppm").set_value(6.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        lab_results = at.session_state["tab1_last_analysis"]["lab_results"]
        assert lab_results["aflatoxin_ppb"] == 45.0
        assert lab_results["don_ppm"] == 6.0
        assert lab_results["ochratoxin_ppb"] is None
        assert lab_results["zearalenone_ppm"] is None
        assert lab_results["fumonisin_ppm"] is None


class TestStructuredInputFeedsSameBuildFullAnalysis:
    def test_structured_input_feeds_same_build_full_analysis(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(45.0).run()
        at.number_input(key="tab1_don_ppm").set_value(6.0).run()
        at.number_input(key="tab1_temperature_celsius").set_value(30.0).run()
        at.number_input(key="tab1_moisture_percent").set_value(15.0).run()
        at.number_input(key="tab1_storage_days").set_value(22).run()
        at.number_input(key="tab1_quantity_tons").set_value(20.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        lab = {"aflatoxin_ppb": 45.0, "ochratoxin_ppb": None, "don_ppm": 6.0,
               "zearalenone_ppm": None, "fumonisin_ppm": None}
        storage = {"temperature_celsius": 30.0, "moisture_percent": 15.0, "storage_days": 22}
        expected_parsed = app.build_structured_parsed_json(
            lab, storage, quantity_tons=20.0, flock_name=None, species_key_used="poultry_broiler",
        )
        expected_analysis = app.build_full_analysis(expected_parsed, 1.6, 25.0, "poultry_broiler")

        actual = at.session_state["tab1_last_analysis"]
        assert actual["final_decision"]["code"] == expected_analysis["final_decision"]["code"]
        assert actual["risk_ratios"] == expected_analysis["risk_ratios"]
        assert actual["mri"]["score"] == expected_analysis["mri"]["score"]


class TestNoLlmOrRegexCodeRemainsInApp:
    def test_no_llm_or_regex_identifiers_remain_in_app_executable_code(self):
        """[إلزامي v3.0.0] ضمان بنيوي بفحص ساكن لشجرة الكود (AST) — لا الملف النصي الخام
        (الذي يحوي عمدًا هذه الأسماء داخل تعليق CHANGELOG التاريخي الموثِّق للحذف نفسه،
        وهذا توثيق مقصود لا بقايا كود). يفحص فقط: تعريفات الدوال/الثوابت، واستدعاءات
        الدوال، واستيراد الموديولات — لا نص docstring/تعليقات حرة."""
        import ast

        source = open(os.path.join(os.path.dirname(__file__), "..", "app.py"), encoding="utf-8").read()
        tree = ast.parse(source)

        forbidden_identifiers = {
            "call_openrouter_llm", "parse_shipment_text", "extract_parameters_regex",
            "clean_llm_json_response", "parse_llm_json_response", "MASTER_SYSTEM_PROMPT",
            "ENGINE_REGEX", "ENGINE_LLM", "ENGINE_FALLBACK_CHAIN", "openai",
            "FALLBACK_FREE_MODELS", "fetch_openrouter_free_models",
        }
        found_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                found_names.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                found_names.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    found_names.add(alias.name)
                if isinstance(node, ast.ImportFrom) and node.module:
                    found_names.add(node.module)

        collision = forbidden_identifiers & found_names
        assert not collision, f"forbidden identifiers found as real code (not just comments): {collision}"

    def test_no_api_key_or_model_selection_sidebar_elements(self):
        at = _fresh_app()
        api_fields = [ti for ti in at.sidebar.text_input if "API" in (ti.label or "") or "موديل" in (ti.label or "")]
        assert api_fields == []


class TestStructuredInputQuantityNoneDoesNotCrashFinancial:
    def test_structured_input_quantity_none_does_not_crash_financial(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_fumonisin_ppm").set_value(3.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not at.exception
        assert at.session_state["tab1_last_analysis"]["shipment_meta"]["quantity_tons"] is None
        financial = at.session_state["tab1_last_analysis"]["financial"]
        assert financial["loss_egp"] is None
        assert financial["wasted_feed_tons"] is None


class TestStructuredInputNegativeTemperatureAccepted:
    def test_structured_input_negative_temperature_accepted(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_don_ppm").set_value(2.0).run()
        at.number_input(key="tab1_temperature_celsius").set_value(-10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not at.exception
        storage_inputs = at.session_state["tab1_last_analysis"]["storage_inputs"]
        assert storage_inputs["temperature_c"] == -10.0

    def test_temperature_field_allows_down_to_minus_twenty(self):
        at = _fresh_app()
        temp_field = at.number_input(key="tab1_temperature_celsius")
        assert temp_field.min == -20.0
        assert temp_field.max == 60.0


class TestStructuredInputGuardClauses:
    def test_no_species_selected_warns_before_toxin_check(self):
        at = _fresh_app()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert any("القطاع المستهدف" in w.value for w in at.warning)
        assert "tab1_last_analysis" not in at.session_state

    def test_species_selected_but_all_toxins_empty_shows_toxin_error_not_species_warning(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert not any("القطاع المستهدف" in w.value for w in at.warning)
        assert any("سم واحدة على الأقل" in e.value for e in at.error)


class TestResetClearsStructuredFields:
    def test_reset_button_clears_all_structured_number_inputs(self):
        at = _fresh_app()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(45.0).run()
        at.number_input(key="tab1_quantity_tons").set_value(20.0).run()
        at.button(key="tab1_reset").click().run(timeout=30)
        assert at.number_input(key="tab1_aflatoxin_ppb").value is None
        assert at.number_input(key="tab1_quantity_tons").value is None

    def test_reset_clears_last_analysis(self):
        at = _fresh_app()
        at.selectbox(key="tab1_species_select").select(BROILER_LABEL).run()
        at.number_input(key="tab1_don_ppm").set_value(2.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)
        assert "tab1_last_analysis" in at.session_state

        at.button(key="tab1_reset").click().run(timeout=30)
        assert "tab1_last_analysis" not in at.session_state
        assert len(at.metric) == 0


class TestStructuredTabPresenceAndFields:
    def test_all_five_toxin_fields_present_and_default_to_none(self):
        at = _fresh_app()
        for key in ("tab1_aflatoxin_ppb", "tab1_ochratoxin_ppb", "tab1_don_ppm",
                    "tab1_zearalenone_ppm", "tab1_fumonisin_ppm"):
            field = at.number_input(key=key)
            assert field.value is None

    def test_storage_and_quantity_fields_default_to_none(self):
        at = _fresh_app()
        for key in ("tab1_temperature_celsius", "tab1_moisture_percent", "tab1_storage_days", "tab1_quantity_tons"):
            assert at.number_input(key=key).value is None