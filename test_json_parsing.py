# -*- coding: utf-8 -*-
"""
tests/test_json_parsing.py — اختبارات طبقة تحليل استجابة النموذج اللغوي
================================================================================
تُثبت هذه الاختبارات إصلاح فئتين حقيقيتين من الأخطاء رُصدتا ميدانيًا في هذا المشروع:
  1. "Expecting ',' delimiter" — فاصلة ناقصة/اقتباس غير مهروب (JSON غير سليم نحويًا لكنه
     غير فارغ) — يُصلَح عبر json_repair.
  2. "Expecting value: line 1 column 1 (char 0)" — استجابة فارغة تمامًا (Empty Completion)
     — لا يمكن إصلاحها نصيًا، يُعالَج عبر إعادة محاولة استدعاء الـ API نفسه (call_openrouter_llm).
"""

from unittest.mock import MagicMock, patch

import app


# ==============================================================================
# clean_llm_json_response() — تقطيع جسم JSON من الرغي المحيط
# ==============================================================================
class TestCleanLlmJsonResponse:
    def test_strips_markdown_fences(self):
        raw = '```json\n{"a": 1}\n```'
        assert app.clean_llm_json_response(raw) == '{"a": 1}'

    def test_strips_preamble_and_trailing_text(self):
        raw = 'Sure, here is the JSON:\n{"a": 1}\nHope this helps!'
        assert app.clean_llm_json_response(raw) == '{"a": 1}'

    def test_handles_none_input_without_exception(self):
        assert app.clean_llm_json_response(None) == ""

    def test_handles_empty_string(self):
        assert app.clean_llm_json_response("") == ""

    def test_leaves_clean_json_unchanged(self):
        raw = '{"a": 1, "b": 2}'
        assert app.clean_llm_json_response(raw) == raw


# ==============================================================================
# parse_llm_json_response() — الدفاع بطبقتين (json.loads ثم json_repair)
# ==============================================================================
class TestParseLlmJsonResponse:
    def test_valid_json_takes_the_fast_strict_path(self):
        result = app.parse_llm_json_response('{"a": 1}')
        assert result["data"] == {"a": 1}
        assert result["was_repaired"] is False

    def test_missing_comma_between_fields_is_repaired(self):
        """[ارتداد] فئة الخطأ الفعلية المرصودة: "Expecting ',' delimiter"."""
        broken = '{"a": 1 "b": 2}'
        result = app.parse_llm_json_response(broken)
        assert result["data"] == {"a": 1, "b": 2}
        assert result["was_repaired"] is True

    def test_trailing_comma_is_repaired(self):
        broken = '{"a": 1, "b": 2,}'
        result = app.parse_llm_json_response(broken)
        assert result["data"] == {"a": 1, "b": 2}
        assert result["was_repaired"] is True

    def test_unescaped_quote_inside_arabic_string_is_repaired(self):
        broken = '{"note": "استخرجت قيمة "أفلا" بنجاح"}'
        result = app.parse_llm_json_response(broken)
        assert result["data"] is not None
        assert result["was_repaired"] is True

    def test_completely_empty_string_fails_gracefully(self):
        """[ارتداد] فئة الخطأ الفعلية المرصودة: "Expecting value: line 1 column 1 (char 0)".
        يجب ألا يُرفع استثناء — فقط dict فشل واضح."""
        result = app.parse_llm_json_response("")
        assert result["data"] is None
        assert result["error"] is not None

    def test_total_garbage_fails_gracefully_not_with_exception(self):
        result = app.parse_llm_json_response("I cannot process this request.")
        assert result["data"] is None
        assert result["error"] is not None


# ==============================================================================
# call_openrouter_llm() — منطق إعادة المحاولة (بدون شبكة حقيقية، عبر محاكاة OpenAI)
# ==============================================================================
def _fake_openai_client(content_sequence):
    """يُنشئ عميل OpenAI مزيَّف يُعيد عناصر content_sequence بالترتيب مع كل استدعاء create()
    (استثناء في القائمة يُرفَع بدل إرجاعه). لا يلمس الشبكة إطلاقًا."""
    mock_client = MagicMock()
    responses = []
    for item in content_sequence:
        if isinstance(item, Exception):
            responses.append(item)
        else:
            fake_response = MagicMock()
            fake_response.choices = [MagicMock(message=MagicMock(content=item))]
            responses.append(fake_response)

    def side_effect(**kwargs):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    mock_client.chat.completions.create.side_effect = side_effect
    return mock_client


class TestCallOpenrouterLlmRetryLogic:
    def test_empty_then_success_recovers_on_second_attempt(self):
        """[ارتداد] استجابة فارغة أولاً، ثم نجاح — يجب أن يتعافى تلقائيًا."""
        with patch("app.OpenAI", return_value=_fake_openai_client(["", '{"a": 1}'])):
            result = app.call_openrouter_llm("fake-key", "fake/model", "text", max_retries=2)
        assert result["success"] is True
        assert result["data"] == {"a": 1}
        assert result["attempts"] == 2

    def test_connection_exception_then_success_recovers(self):
        with patch("app.OpenAI", return_value=_fake_openai_client([ConnectionError("timeout"), '{"a": 2}'])):
            result = app.call_openrouter_llm("fake-key", "fake/model", "text", max_retries=2)
        assert result["success"] is True
        assert result["attempts"] == 2

    def test_all_attempts_empty_fails_gracefully_with_clear_message(self):
        with patch("app.OpenAI", return_value=_fake_openai_client(["", "", ""])):
            result = app.call_openrouter_llm("fake-key", "fake/model", "text", max_retries=2)
        assert result["success"] is False
        assert "فارغ" in result["error"]
        assert result["attempts"] == 3

    def test_all_attempts_malformed_fails_gracefully(self):
        with patch("app.OpenAI", return_value=_fake_openai_client(["not json", "still not", "nope"])):
            result = app.call_openrouter_llm("fake-key", "fake/model", "text", max_retries=2)
        assert result["success"] is False
        assert result["attempts"] == 3

    def test_immediate_success_needs_no_retry(self):
        with patch("app.OpenAI", return_value=_fake_openai_client(['{"a": 1, "b": 2}'])):
            result = app.call_openrouter_llm("fake-key", "fake/model", "text", max_retries=2)
        assert result["success"] is True
        assert result["attempts"] == 1

    def test_last_raw_content_retained_for_diagnostics_on_total_failure(self):
        with patch("app.OpenAI", return_value=_fake_openai_client(["one", "two", "the last one"])):
            result = app.call_openrouter_llm("fake-key", "fake/model", "text", max_retries=2)
        assert result["raw"] == "the last one"


# ==============================================================================
# extract_parameters_regex() — المحلل الحتمي السريع (Fast Path)
# ==============================================================================
import pytest


def _lab(text):
    """اختصار: قيم السموم المُستخرَجة غير None فقط."""
    result = app.extract_parameters_regex(text)
    return {k: v for k, v in result["lab_results"].items() if v is not None}


class TestRegexParserEachToxinWithCorrectUnit:
    """[إلزامي] Test لكل سم بوحدته الصحيحة."""

    @pytest.mark.parametrize("text,key,expected", [
        ("Aflatoxin 45 ppb", "aflatoxin_ppb", 45.0),
        ("أفلاتوكسين 45 ppb", "aflatoxin_ppb", 45.0),
        ("أفلا 12.5 ppb", "aflatoxin_ppb", 12.5),
        ("AFB1 30 ppb", "aflatoxin_ppb", 30.0),
        ("Ochratoxin 80 ppb", "ochratoxin_ppb", 80.0),
        ("OTA 80 ppb", "ochratoxin_ppb", 80.0),
        ("أوركاتوكسين 80 ppb", "ochratoxin_ppb", 80.0),
        ("DON 6 ppm", "don_ppm", 6.0),
        ("Deoxynivalenol 6 ppm", "don_ppm", 6.0),
        ("دون 6 ppm", "don_ppm", 6.0),
        ("فوميتوكسين 6 ppm", "don_ppm", 6.0),
        ("Zearalenone 0.3 ppm", "zearalenone_ppm", 0.3),
        ("ZEA 0.3 ppm", "zearalenone_ppm", 0.3),
        ("زيرالينون 0.3 ppm", "zearalenone_ppm", 0.3),
        ("Fumonisin 12 ppm", "fumonisin_ppm", 12.0),
        ("FUM 12 ppm", "fumonisin_ppm", 12.0),
        ("FB1 12 ppm", "fumonisin_ppm", 12.0),
        ("فيومونيسين 12 ppm", "fumonisin_ppm", 12.0),
    ])
    def test_each_toxin_extracts_with_its_scientific_unit(self, text, key, expected):
        result = app.extract_parameters_regex(text)
        assert result["accepted"] is True
        assert result["lab_results"][key] == pytest.approx(expected)
        assert result["toxins_found"] == [key]

    def test_alternative_valid_unit_spellings_are_accepted(self):
        assert _lab("Aflatoxin 20 µg/kg") == {"aflatoxin_ppb": 20.0}
        assert _lab("Aflatoxin 20 ug/kg") == {"aflatoxin_ppb": 20.0}
        assert _lab("DON 3 mg/kg") == {"don_ppm": 3.0}

    def test_arabic_indic_digits_are_normalized(self):
        assert _lab("أفلا ٤٥ ppb دون ٦ ppm") == {"aflatoxin_ppb": 45.0, "don_ppm": 6.0}

    def test_all_five_toxins_in_one_message(self):
        text = "Aflatoxin 10 ppb, OTA 50 ppb, DON 2 ppm, ZEA 0.1 ppm, Fumonisin 5 ppm"
        assert _lab(text) == {
            "aflatoxin_ppb": 10.0, "ochratoxin_ppb": 50.0, "don_ppm": 2.0,
            "zearalenone_ppm": 0.1, "fumonisin_ppm": 5.0,
        }

    def test_arabic_and_english_names_are_case_insensitive(self):
        assert _lab("AFLATOXIN 45 PPB") == {"aflatoxin_ppb": 45.0}
        assert _lab("aflatoxin 45 ppb") == {"aflatoxin_ppb": 45.0}


class TestRegexParserZearalenoneUnitConversion:
    """[ارتداد أمان] الزيارالينون مخزَّن ppm (constants.py) لكن المعامل تكتبه غالبًا ppb —
    يجب التحويل ÷1000، وإلا تُضخَّم القيمة ١٠٠٠× وتُقلب شحنة سليمة إلى REJECT."""

    def test_ppb_is_converted_to_ppm(self):
        assert _lab("Zearalenone 250 ppb") == {"zearalenone_ppm": pytest.approx(0.25)}

    def test_ug_per_kg_is_converted_to_ppm(self):
        assert _lab("ZEA 500 µg/kg") == {"zearalenone_ppm": pytest.approx(0.5)}

    def test_ppm_passes_through_unchanged(self):
        assert _lab("ZEA 0.25 ppm") == {"zearalenone_ppm": pytest.approx(0.25)}

    def test_ppb_input_yields_the_same_math_engine_ratio_as_equivalent_ppm(self):
        parsed_ppb = app.build_parsed_json_from_regex(app.extract_parameters_regex("ZEA 250 ppb"))
        parsed_ppm = app.build_parsed_json_from_regex(app.extract_parameters_regex("ZEA 0.25 ppm"))
        a_ppb = app.build_full_analysis(parsed_ppb, 1.6, 25.0, "poultry_broiler")
        a_ppm = app.build_full_analysis(parsed_ppm, 1.6, 25.0, "poultry_broiler")
        assert a_ppb["risk_ratios"]["zearalenone_ppm"] == a_ppm["risk_ratios"]["zearalenone_ppm"] == 1.0
        assert a_ppb["final_decision"]["code"] != "REJECT"


class TestRegexParserRejectsWrongUnits:
    """[إلزامي] Test لرفض وحدة غلط — يجب accepted=False وبلا أي قيمة مُستخرَجة للسم الخاطئ."""

    @pytest.mark.parametrize("text", [
        "أفلاتوكسين 45 ppm",     # المثال الحرفي من المتطلبات — خطأ ١٠٠٠×
        "Aflatoxin 45 ppm",
        "Aflatoxin 0.02 mg/kg",
        "OTA 80 ppm",
        "DON 6 ppb",
        "دون 6 ppb",
        "Fumonisin 12 ppb",
        "Fumonisin 12 µg/kg",
    ])
    def test_scientifically_wrong_unit_is_rejected(self, text):
        result = app.extract_parameters_regex(text)
        assert result["accepted"] is False
        assert result["toxins_found"] == []
        assert any("وحدة غير مطابقة" in reason for reason in result["rejection_reasons"])

    def test_percent_sign_is_not_a_valid_toxin_unit(self):
        assert app.extract_parameters_regex("Aflatoxin 45 %")["accepted"] is False

    def test_wrong_unit_on_one_toxin_rejects_the_whole_message_even_if_others_are_fine(self):
        """رفض جزئي صامت خطير: لو قُبل الدون وأُسقط الأفلاتوكسين الخاطئ وحدته، يُعامَل
        الأفلاتوكسين كـ"غير مقاس" لا كـ"قيمة مشبوهة" — لذلك تُرفض الرسالة كاملة."""
        result = app.extract_parameters_regex("أفلاتوكسين 45 ppm - دون 6 ppm")
        assert result["accepted"] is False


class TestRegexParserConservativeGate:
    """أي شك => accepted=False (فيذهب النص للـ LLM)."""

    def test_toxin_named_without_a_value_rejects_whole_message(self):
        """[ارتداد] بدون هذه البوابة كان يُقبل الدون وحده ويُعامَل الأفلا "غير مقاس"."""
        result = app.extract_parameters_regex("أفلا عالي جدا و دون 6 ppm")
        assert result["accepted"] is False

    def test_number_without_unit_is_rejected(self):
        assert app.extract_parameters_regex("أفلا 45")["accepted"] is False

    def test_ambiguous_comma_number_is_rejected(self):
        assert app.extract_parameters_regex("أفلا 4,5 ppb")["accepted"] is False
        assert app.extract_parameters_regex("أفلا 1,200 ppb")["accepted"] is False

    def test_conflicting_duplicate_values_are_rejected(self):
        assert app.extract_parameters_regex("أفلا 10 ppb ... أفلا 50 ppb")["accepted"] is False

    def test_identical_duplicate_values_are_accepted(self):
        assert _lab("أفلا 10 ppb ... Aflatoxin 10 ppb") == {"aflatoxin_ppb": 10.0}

    @pytest.mark.parametrize("text", [
        "Aflatoxin <5 ppb", "Aflatoxin ND", "Aflatoxin 20-30 ppb", "45 ppb aflatoxin", "Aflatoxin ppb 45",
    ])
    def test_non_trivial_value_formats_fall_back_safely(self, text):
        assert app.extract_parameters_regex(text)["accepted"] is False

    def test_no_toxin_at_all_is_rejected_even_with_valid_environment_fields(self):
        result = app.extract_parameters_regex("شحنة ذرة رطوبة 15% حرارة 30 درجة")
        assert result["accepted"] is False
        assert result["storage"]["moisture_percent"] == 15.0  # تُستخرج لكن لا تكفي وحدها

    @pytest.mark.parametrize("text", ["", "   ", "\n\n"])
    def test_empty_or_whitespace_is_rejected(self, text):
        assert app.extract_parameters_regex(text)["accepted"] is False

    def test_garbage_text_is_rejected_without_exception(self):
        assert app.extract_parameters_regex("I cannot process this request.")["accepted"] is False

    def test_none_input_does_not_raise(self):
        assert app.extract_parameters_regex(None)["accepted"] is False


class TestRegexParserFalsePositiveGuards:
    """[ارتداد] أسماء السموم القصيرة لا تُطابَق داخل كلمات أخرى."""

    def test_arabic_bedon_without_is_not_read_as_don(self):
        """"بدون تخزين" = without storage — تحتوي حرفيًا "دون" لكنها ليست السم."""
        result = app.extract_parameters_regex("بدون 6 ppm أفلا 10 ppb")
        assert result["lab_results"]["don_ppm"] is None

    @pytest.mark.parametrize("word", ["London", "abandon", "citizen", "perfume", "total", "zealous"])
    def test_short_toxin_abbreviations_do_not_match_inside_english_words(self, word):
        result = app.extract_parameters_regex(f"{word} 3 ppm Aflatoxin 10 ppb")
        assert result["accepted"] is True
        assert result["toxins_found"] == ["aflatoxin_ppb"]


class TestRegexParserEnvironmentFields:
    def test_moisture_temperature_storage_and_quantity_extracted(self):
        result = app.extract_parameters_regex(
            "أفلا 45 ppb - رطوبة 15% - حرارة المخزن 30 درجة - 22 يوم تخزين - 20 طن"
        )
        assert result["storage"] == {"temperature_celsius": 30.0, "moisture_percent": 15.0, "storage_days": 22}
        assert result["quantity_tons"] == 20.0

    def test_english_environment_fields(self):
        result = app.extract_parameters_regex("Aflatoxin 45 ppb, Moisture: 14.5%, Temp 27 C, storage 10 days, 25 tons")
        assert result["storage"]["moisture_percent"] == 14.5
        assert result["storage"]["temperature_celsius"] == 27.0
        assert result["storage"]["storage_days"] == 10
        assert result["quantity_tons"] == 25.0

    def test_negative_temperature_keeps_its_sign(self):
        """[ارتداد] باج حقيقي: "temp -5 C" كانت تُقرأ +5 لأن الفاصل ابتلع علامة الناقص."""
        assert app.extract_parameters_regex("afla 10 ppb temp -5 C")["storage"]["temperature_celsius"] == -5.0

    def test_missing_environment_fields_are_none_not_zero(self):
        result = app.extract_parameters_regex("Aflatoxin 45 ppb")
        assert result["storage"] == {"temperature_celsius": None, "moisture_percent": None, "storage_days": None}
        assert result["quantity_tons"] is None


class TestRegexParserNoneNotZeroPrinciple:
    """[قرار تصميم مقصود] القيم غير المذكورة None (مجهولة) وليست 0.0 (آمنة)."""

    def test_unmentioned_toxins_are_none_never_zero(self):
        result = app.extract_parameters_regex("Aflatoxin 45 ppb")
        for key in ("ochratoxin_ppb", "don_ppm", "zearalenone_ppm", "fumonisin_ppm"):
            assert result["lab_results"][key] is None

    def test_explicit_measured_zero_is_preserved_as_zero(self):
        """صفر مقاس فعليًا (المعمل أبلغ 0 ppb) يختلف عن "غير مقاس" — يُحفَظ كما هو."""
        assert _lab("Aflatoxin 0 ppb") == {"aflatoxin_ppb": 0.0}

    def test_result_has_all_five_toxin_keys(self):
        assert set(app.extract_parameters_regex("Aflatoxin 45 ppb")["lab_results"]) == set(app.TOXIN_KEYS)

    def test_numeric_values_are_float_and_storage_days_is_int(self):
        result = app.extract_parameters_regex("Aflatoxin 45 ppb storage 22 days moisture 15%")
        assert isinstance(result["lab_results"]["aflatoxin_ppb"], float)
        assert isinstance(result["storage"]["storage_days"], int)
        assert isinstance(result["storage"]["moisture_percent"], float)


# ==============================================================================
# build_parsed_json_from_regex() — تطابق Schema الـ LLM حرفيًا (بند 5: لا Regression)
# ==============================================================================
def _flatten_keys(d, prefix=""):
    keys = set()
    for k, v in d.items():
        keys.add(prefix + k)
        if isinstance(v, dict):
            keys |= _flatten_keys(v, prefix + k + ".")
    return keys


class TestRegexJsonSchemaMatchesLlmSchema:
    LLM_SCHEMA = {
        "shipment_meta": {"supplier_name": None, "feed_type": None, "shipment_date": None, "quantity_tons": None},
        "normalized_inputs": {
            "lab_results": {k: None for k in ("aflatoxin_ppb", "ochratoxin_ppb", "don_ppm", "zearalenone_ppm", "fumonisin_ppm")},
            "storage": {"temperature_celsius": None, "moisture_percent": None, "storage_days": None},
            "parameters": {"target_species": None, "flock_age_days": None, "toxin_binder_added": False, "binder_type": None},
        },
        "parsing_audit": {"is_valid_input": True, "missing_critical_fields": [], "parsing_notes": ""},
    }

    def _regex_json(self):
        return app.build_parsed_json_from_regex(app.extract_parameters_regex("Aflatoxin 45 ppb DON 6 ppm"))

    def test_keys_are_exactly_the_llm_schema_keys(self):
        assert _flatten_keys(self._regex_json()) == _flatten_keys(self.LLM_SCHEMA)

    def test_feeds_build_full_analysis_without_error_and_matches_llm_shaped_input(self):
        regex_json = self._regex_json()
        llm_shaped = {**regex_json}
        a1 = app.build_full_analysis(regex_json, 1.6, 25.0, "poultry_broiler")
        a2 = app.build_full_analysis(llm_shaped, 1.6, 25.0, "poultry_broiler")
        assert a1 == a2
        assert a1["risk_ratios"]["aflatoxin_ppb"] == pytest.approx(2.25)
        assert a1["final_decision"]["code"] == "BLEND_REQUIRED"

    def test_missing_critical_fields_lists_every_unmeasured_toxin(self):
        audit = self._regex_json()["parsing_audit"]
        assert set(audit["missing_critical_fields"]) == {"ochratoxin_ppb", "zearalenone_ppm", "fumonisin_ppm"}
        assert audit["is_valid_input"] is True

    def test_unextractable_metadata_is_none_not_invented(self):
        regex_json = self._regex_json()
        meta = regex_json["shipment_meta"]
        assert meta["supplier_name"] is None and meta["feed_type"] is None and meta["shipment_date"] is None
        assert regex_json["normalized_inputs"]["parameters"]["target_species"] is None
        assert regex_json["normalized_inputs"]["parameters"]["flock_age_days"] is None


# ==============================================================================
# parse_shipment_text() — سلسلة الـ Hybrid: Regex أولًا ثم LLM كـ Fallback
# ==============================================================================
def _spy_llm(payload=None, success=True):
    """LLM مزيَّف يسجّل استدعاءاته — يُحقَن عبر llm_caller بدل mock.patch (أبسط وأوضح)."""
    calls = []
    payload = payload if payload is not None else {
        "shipment_meta": {}, "parsing_audit": {},
        "normalized_inputs": {"lab_results": {"aflatoxin_ppb": 9.0}, "storage": {}, "parameters": {}},
    }

    def caller(api_key, model, text):
        calls.append({"api_key": api_key, "model": model, "text": text})
        if success:
            return {"success": True, "data": payload, "raw": "{}", "was_repaired": False, "attempts": 1}
        return {"success": False, "error": "boom", "raw": None, "attempts": 3}

    caller.calls = calls
    return caller


class TestHybridChainFastPath:
    def test_structured_text_uses_regex_and_never_calls_the_llm(self):
        spy = _spy_llm()
        result = app.parse_shipment_text("أفلا 45 ppb - دون 6 ppm", "sk-key", "openrouter/free", llm_caller=spy)
        assert result["success"] is True
        assert result["engine"] == app.ENGINE_REGEX
        assert spy.calls == []
        assert result["attempts"] == 0

    def test_fast_path_works_with_no_api_key_at_all(self):
        spy = _spy_llm()
        result = app.parse_shipment_text("Aflatoxin 45 ppb", "", "openrouter/free", llm_caller=spy)
        assert result["success"] is True
        assert result["engine"] == app.ENGINE_REGEX
        assert spy.calls == []

    def test_fast_path_data_drives_math_engine_end_to_end(self):
        result = app.parse_shipment_text("أفلا 100 ppb", "", "m", llm_caller=_spy_llm())
        analysis = app.build_full_analysis(result["data"], 1.6, 25.0, "poultry_broiler")
        assert analysis["final_decision"]["code"] == "REJECT"  # 100/20 = 5x > 2.5x


class TestHybridChainFallback:
    """[إلزامي] Test للـ Fallback لما الـ Regex يفشل."""

    def test_unstructured_text_falls_back_to_llm_with_original_text(self):
        spy = _spy_llm()
        text = "الشحنة فيها أفلا عالي جدا"
        result = app.parse_shipment_text(text, "sk-key", "openrouter/free", llm_caller=spy)
        assert result["success"] is True
        assert result["engine"] == app.ENGINE_FALLBACK_CHAIN
        assert len(spy.calls) == 1
        assert spy.calls[0]["text"] == text                       # النص الأصلي بلا أي تعديل
        assert spy.calls[0]["model"] == "openrouter/free"          # الموديل الرسمي المطلوب

    def test_wrong_unit_falls_back_to_llm_instead_of_being_trusted(self):
        spy = _spy_llm()
        result = app.parse_shipment_text("أفلاتوكسين 45 ppm", "sk-key", "m", llm_caller=spy)
        assert result["engine"] == app.ENGINE_FALLBACK_CHAIN
        assert len(spy.calls) == 1
        assert any("وحدة غير مطابقة" in r for r in result["regex_rejection_reasons"])

    def test_fallback_preserves_regex_rejection_reasons_for_transparency(self):
        result = app.parse_shipment_text("أفلا 45", "sk-key", "m", llm_caller=_spy_llm())
        assert result["regex_rejection_reasons"]  # غير فارغة — سبب التحويل موثَّق للواجهة

    def test_fallback_propagates_llm_repair_flag_and_attempts(self):
        def caller(api_key, model, text):
            return {"success": True, "data": {"normalized_inputs": {"lab_results": {}}}, "raw": "x",
                    "was_repaired": True, "attempts": 2}
        result = app.parse_shipment_text("نص غير منظم", "sk-key", "m", llm_caller=caller)
        assert result["was_repaired"] is True
        assert result["attempts"] == 2

    def test_llm_failure_after_fallback_returns_none_data_not_a_safe_default(self):
        """[قرار مقصود] لا Safe Default Dict: عند الفشل الكامل data=None وليست قيمًا موهومة."""
        result = app.parse_shipment_text("نص غير منظم", "sk-key", "m", llm_caller=_spy_llm(success=False))
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "boom"

    def test_fallback_needed_but_no_api_key_fails_clearly_without_calling_llm(self):
        spy = _spy_llm()
        result = app.parse_shipment_text("الشحنة فيها أفلا عالي جدا", "", "m", llm_caller=spy)
        assert result["success"] is False
        assert result["data"] is None
        assert "مفتاح" in result["error"]
        assert spy.calls == []


class TestHybridChainFileSource:
    def test_file_source_goes_straight_to_llm_and_skips_regex(self):
        spy = _spy_llm()
        result = app.parse_shipment_text("aflatoxin_ppb,45 ppb", "sk-key", "m", source="file", llm_caller=spy)
        assert result["engine"] == app.ENGINE_LLM
        assert len(spy.calls) == 1
        assert result["regex_rejection_reasons"] == []

    def test_file_source_without_key_fails_clearly(self):
        result = app.parse_shipment_text("a,b", "", "m", source="file", llm_caller=_spy_llm())
        assert result["success"] is False


class TestEngineIndicators:
    def test_three_indicators_defined_with_required_colors(self):
        assert app.ENGINE_INDICATORS[app.ENGINE_REGEX] == ("⚡ Extracted via Fast Deterministic Engine", "green")
        assert app.ENGINE_INDICATORS[app.ENGINE_LLM] == ("🤖 Extracted via LLM Engine", "blue")
        assert app.ENGINE_INDICATORS[app.ENGINE_FALLBACK_CHAIN] == ("⚠️ Fallback Chain: Regex → LLM", "orange")

    def test_default_llm_caller_is_call_openrouter_llm_when_none_injected(self):
        """يثبت أن الافتراضي الحقيقي (وليس فقط المحقون) هو الذي يُستدعى — عبر patch مباشر."""
        with patch("app.OpenAI", return_value=_fake_openai_client(['{"a": 1, "b": 2}'])):
            result = app.parse_shipment_text("نص غير منظم", "sk-key", "fake/model")
        assert result["engine"] == app.ENGINE_FALLBACK_CHAIN
        assert result["data"] == {"a": 1, "b": 2}


class TestRegexParserArabicPunctuationAndFormatting:
    """[ارتداد] الفاصلة العربية "،" (U+060C) كانت تُعامَل كحرف عربي فتكسر حد الكلمة بعد الوحدة،
    فتُحوَّل أشيع صيغة عربية طبيعية للـ LLM البطيء بلا داعٍ."""

    @pytest.mark.parametrize("text", [
        "أفلا 10 ppb، دون 6 ppm",     # فاصلة عربية U+060C
        "أفلا 10 ppb؛ دون 6 ppm",     # فاصلة منقوطة عربية U+061B
        "أفلا 10 ppb\nدون 6 ppm",     # سطر جديد
        "أفلا 10 ppb - دون 6 ppm",    # شرطة
        "أفلا 10ppb دون 6ppm",        # بلا مسافة بين الرقم والوحدة
        "أفلا: 10 ppb | دون: 6 ppm",  # نقطتان رأسيتان وخط عمودي
    ])
    def test_common_arabic_list_separators_parse_on_the_fast_path(self, text):
        result = app.extract_parameters_regex(text)
        assert result["accepted"] is True
        assert result["lab_results"]["aflatoxin_ppb"] == 10.0
        assert result["lab_results"]["don_ppm"] == 6.0

    def test_arabic_punctuation_is_not_in_the_letter_class(self):
        import re as _re
        for punctuation in ("،", "؛", "؟"):
            assert not _re.match(f"[{app._AR_LETTER}]", punctuation)


class TestRegexParserCommaHandling:
    """يغطّي فجوة كشفها اختبار الطفرات: فحص الفاصلة العام يحمي حقولًا غير السموم أيضًا."""

    def test_decimal_comma_in_an_environment_field_rejects_instead_of_silently_dropping_it(self):
        """بدون الفحص العام: الرطوبة "14,5%" تُقرأ None بصمت بينما يُقبل الأفلا — فقدان قيمة
        بلا أي إشارة. الرفض يحوّل النص للـ LLM فيُقرأ كاملًا."""
        result = app.extract_parameters_regex("الرطوبة 14,5% أفلا 10 ppb")
        assert result["accepted"] is False
        assert any("فاصلة" in reason for reason in result["rejection_reasons"])

    def test_thousands_style_comma_number_is_rejected(self):
        assert app.extract_parameters_regex("أفلا 1,200 ppb")["accepted"] is False

    def test_plain_english_comma_between_items_is_not_mistaken_for_a_number_comma(self):
        """"ppb, DON" — فاصلة بين عنصرين وليست داخل رقم؛ يجب ألا تُرفض."""
        assert app.extract_parameters_regex("Aflatoxin 10 ppb, DON 6 ppm")["accepted"] is True


class TestRegexParserArabicDonProseFailsSafe:
    """`دون` تعني أيضًا "بدون/أقل من" — تُثبَّت هنا حالات النثر التي **يجب** أن تفشل بأمان
    (تذهب للـ LLM) بدل أن تُقرأ كقياس DON. الحالة الوحيدة غير القابلة للفصل نصيًا
    (`دون 6 ppm` حرفيًا) موثّقة كقيد معروف في CHANGELOG.md وليست مختبَرة كسلوك مرغوب."""

    @pytest.mark.parametrize("text", [
        "دون 3 أيام تخزين أفلا 10 ppb",        # رقم بلا وحدة
        "تم الشحن دون 5 طن أفلا 10 ppb",       # وحدة الكمية ليست وحدة سم
        "رطوبة دون 2 % أفلا 10 ppb",            # % ليست وحدة سم
        "دون أي مشاكل 6 ppm أفلا 10 ppb",      # رقم غير ملاصق للاسم
    ])
    def test_don_as_a_prose_word_never_becomes_a_don_measurement(self, text):
        result = app.extract_parameters_regex(text)
        assert result["lab_results"]["don_ppm"] is None
        assert result["accepted"] is False  # الشك => الرسالة كلها للـ LLM