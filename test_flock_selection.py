# -*- coding: utf-8 -*-
"""
tests/test_flock_selection.py — اختبارات ربط القطيع/العنبر بالفئة التنظيمية
================================================================================
تُثبت هذه الاختبارات أن القطيع/العنبر (تسمية تشغيلية حرة كما يعرفها فريق المزرعة) لا
يمكنه أبدًا الوصول إلى محرك الحسابات إلا بعد تُرجمَ إلى أحد المفاتيح الخمسة المعتمدة في
constants.SPECIES_REGULATORY_LIMITS — سواء كان قطيعًا افتراضيًا (FLOCK_TO_SPECIES_MAP)
أو قطيعًا مخصصًا أضافه المستخدم خلال الجلسة (custom_flocks). أي محاولة لإدخال فئة غير
معتمدة (Swine، Equine، أو أي قيمة أخرى) تُرفَض صراحةً — لا تُمرَّر بصمت لمحرك الحسابات.

⚠️ v3.0.0: اختبارات الواجهة هنا تستخدم الشاشة الأولى (🧪 سموم فقط، مفاتيح tab1_*) كممثل
عن الشاشات الثلاث — القطيع/العنبر يعمل بنفس المنطق في الشاشات الأخرى (render_species_
flock_age_selector مشتركة)، راجع test_integration.py لاختبارات متعددة الشاشات.
"""

import os

import pytest
from streamlit.testing.v1 import AppTest

import app
import constants as c

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")
STRUCTURED_TEXT = "أفلا 10 ppb - دون 2 ppm - رطوبة 15% - حرارة المخزن 25 درجة - 10 أيام تخزين - 20 طن"


# ==============================================================================
# constants.FLOCK_TO_SPECIES_MAP — سلامة بنيوية
# ==============================================================================
class TestFlockToSpeciesMapStructure:
    def test_flock_to_species_map_covers_all_constants_categories(self):
        """كل قيمة في FLOCK_TO_SPECIES_MAP يجب أن تنتمي فعليًا إلى SPECIES_REGULATORY_LIMITS —
        لا فئة مخترعة (Swine/Equine/...) ولا مفتاح مكتوب خطأ."""
        valid_species_keys = set(c.SPECIES_REGULATORY_LIMITS.keys())
        for flock_name, species_key in c.FLOCK_TO_SPECIES_MAP.items():
            assert species_key in valid_species_keys, f"'{flock_name}' -> '{species_key}' غير معتمد"

    def test_all_default_flocks_map_to_existing_species(self):
        """كل الأسماء السبعة المذكورة في المتطلبات موجودة فعليًا، وتُرجع مفتاحًا صالحًا."""
        expected_flocks = {
            "قطيع A - عنبر التسمين 1", "قطيع B - عنبر التسمين 2", "قطيع الأمهات",
            "قطيع البياض", "قطيع الحلاب", "ماشية التسمين", "حوض الاستزراع السمكي",
        }
        assert expected_flocks == set(c.FLOCK_TO_SPECIES_MAP.keys())
        for flock_name in expected_flocks:
            assert c.FLOCK_TO_SPECIES_MAP[flock_name] in c.SPECIES_REGULATORY_LIMITS

    def test_only_the_five_approved_categories_appear_as_values(self):
        """توقف تام عن أي فئة جديدة (Swine/Equine/...) — القيم الفعلية تساوي بالضبط
        الخمس فئات المعتمدة، لا أكثر ولا أقل."""
        assert set(c.FLOCK_TO_SPECIES_MAP.values()) <= {
            "poultry_broiler", "poultry_layer", "cattle_dairy", "cattle_beef", "aquaculture",
        }

    @pytest.mark.parametrize("flock_name,expected_species", [
        ("قطيع A - عنبر التسمين 1", "poultry_broiler"),
        ("قطيع B - عنبر التسمين 2", "poultry_broiler"),
        ("قطيع الأمهات", "poultry_layer"),
        ("قطيع البياض", "poultry_layer"),
        ("قطيع الحلاب", "cattle_dairy"),
        ("ماشية التسمين", "cattle_beef"),
        ("حوض الاستزراع السمكي", "aquaculture"),
    ])
    def test_each_default_flock_maps_to_its_documented_species(self, flock_name, expected_species):
        assert c.FLOCK_TO_SPECIES_MAP[flock_name] == expected_species


# ==============================================================================
# app.resolve_flock_species_key() — القرار الحاسم في الحل
# ==============================================================================
class TestResolveFlockSpeciesKey:
    def test_default_flock_resolves_via_constants_map(self):
        assert app.resolve_flock_species_key("قطيع الحلاب") == "cattle_dairy"

    def test_custom_flock_resolves_via_session_dict(self):
        custom = {"قطيعي الخاص": "aquaculture"}
        assert app.resolve_flock_species_key("قطيعي الخاص", custom) == "aquaculture"

    def test_default_map_takes_priority_over_custom_flocks_with_same_name(self):
        """[سلوك موثَّق] لو تعارض اسم قطيع مخصص مع اسم افتراضي، الخريطة الثابتة
        (constants.py) هي المرجع الحاسم أولًا — تمنع أي التفاف حول المرجع الحتمي."""
        custom = {"قطيع الحلاب": "aquaculture"}  # محاولة "تخريب" اسم افتراضي معروف
        assert app.resolve_flock_species_key("قطيع الحلاب", custom) == "cattle_dairy"

    def test_unknown_flock_name_returns_none(self):
        assert app.resolve_flock_species_key("قطيع غير موجود إطلاقًا") is None

    def test_none_flock_name_returns_none(self):
        assert app.resolve_flock_species_key(None) is None

    def test_empty_flock_name_returns_none(self):
        assert app.resolve_flock_species_key("") is None

    def test_no_custom_flocks_dict_provided_still_resolves_default_flocks(self):
        assert app.resolve_flock_species_key("ماشية التسمين", custom_flocks=None) == "cattle_beef"


# ==============================================================================
# app.add_custom_flock() — القطيع المخصص يُرفَض إن كانت فئته غير معتمدة
# ==============================================================================
class TestCustomFlockRequiresValidSpecies:
    def test_custom_flock_requires_valid_species(self):
        """إضافة قطيع مخصص بفئة صالحة (من الخمس المعتمدة) تنجح وتُحفَظ بشكلها الصحيح."""
        custom = {}
        result = app.add_custom_flock(custom, "مزرعتي الجديدة", "poultry_layer")
        assert custom == {"مزرعتي الجديدة": "poultry_layer"}
        assert result is custom  # يُعدَّل في مكانه ويُعاد للتسلسل

    @pytest.mark.parametrize("invalid_species", ["swine", "equine", "goat", "SWINE", "Poultry_Broiler", "  "])
    def test_invalid_species_in_custom_flock_rejected(self, invalid_species):
        """[إلزامي] أي فئة غير موجودة حرفيًا في SPECIES_REGULATORY_LIMITS تُرفَض — بما فيها
        فئات مخترعة كليًا (Swine/Equine) ومطابقات شبه صحيحة (حساسية لحالة الأحرف)."""
        custom = {}
        with pytest.raises(ValueError, match="غير معتمد"):
            app.add_custom_flock(custom, "قطيع بفئة خاطئة", invalid_species)
        assert custom == {}  # لا يُحفَظ شيء عند الرفض

    def test_none_species_rejected(self):
        with pytest.raises(ValueError):
            app.add_custom_flock({}, "قطيع", None)

    def test_empty_flock_name_rejected_even_with_valid_species(self):
        with pytest.raises(ValueError, match="فارغًا"):
            app.add_custom_flock({}, "", "cattle_dairy")

    def test_whitespace_only_flock_name_rejected(self):
        with pytest.raises(ValueError, match="فارغًا"):
            app.add_custom_flock({}, "   ", "cattle_dairy")

    def test_flock_name_is_stripped_before_saving(self):
        custom = {}
        app.add_custom_flock(custom, "  قطيع بمسافات  ", "cattle_beef")
        assert custom == {"قطيع بمسافات": "cattle_beef"}

    def test_every_approved_species_key_is_individually_accepted(self):
        """كل مفتاح من الخمسة المعتمدة فعليًا يُقبَل — لا نسيان لأي فئة."""
        for species_key in c.SPECIES_REGULATORY_LIMITS:
            custom = {}
            app.add_custom_flock(custom, f"قطيع تجريبي لـ {species_key}", species_key)
            assert custom[f"قطيع تجريبي لـ {species_key}"] == species_key


# ==============================================================================
# تمرير species_key الصحيح لمحرك الحسابات (Math Engine)
# ==============================================================================
class TestFlockSelectionPassesCorrectSpeciesToMathEngine:
    def test_flock_species_key_drives_build_full_analysis_not_a_guess(self):
        """المفتاح المُستخرَج من القطيع (وليس أي استنتاج آخر) هو ما يصل فعليًا لمحرك
        الحسابات — يُتحقَّق من ذلك عبر رؤية الحدود التنظيمية الفعلية المستخدَمة."""
        parsed = {
            "shipment_meta": {}, "parsing_audit": {},
            "normalized_inputs": {
                "lab_results": {"aflatoxin_ppb": 12.0, "ochratoxin_ppb": None, "don_ppm": None,
                                "zearalenone_ppm": None, "fumonisin_ppm": None},
                "storage": {}, "parameters": {},
            },
        }
        flock_species_key = app.resolve_flock_species_key("حوض الاستزراع السمكي")
        assert flock_species_key == "aquaculture"

        analysis = app.build_full_analysis(parsed, 1.6, 25.0, flock_species_key)
        # حد أفلاتوكسين الاستزراع السمكي accept=10 (أضيق خصيصًا من 20 للدواجن) — 12/10 = 1.2x
        assert analysis["species_key"] == "aquaculture"
        assert analysis["risk_ratios"]["aflatoxin_ppb"] == pytest.approx(12.0 / 10.0)

    def test_different_flocks_of_same_broad_category_still_share_the_species_row(self):
        """قطيعا التسمين المختلفان (A وB) كلاهما poultry_broiler — نفس صف الحدود
        التنظيمية بالضبط، رغم كونهما تسميتين تشغيليتين مختلفتين."""
        key_a = app.resolve_flock_species_key("قطيع A - عنبر التسمين 1")
        key_b = app.resolve_flock_species_key("قطيع B - عنبر التسمين 2")
        assert key_a == key_b == "poultry_broiler"

    def test_end_to_end_ui_flock_choice_overrides_main_dropdown_species(self):
        """[تكامل] اختيار قطيع في الواجهة يتخطى القطاع العام المختار في القائمة الرئيسية —
        المصدر الفعلي المستخدَم في التحليل هو القطاع المرتبط بالقطيع، لا القطاع العام."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab1_species_select").select("دواجن تسمين (Broiler)").run()  # القطاع العام
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("قطيع الحلاب").run()  # القطيع المختار: مواشي حلاب (فئة مختلفة تمامًا)
        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        assert not at.exception
        assert at.session_state["tab1_last_analysis"]["species_key"] == "cattle_dairy"


# ==============================================================================
# التوافق الخلفي — عدم اختيار قطيع يعني الاعتماد على القائمة الرئيسية
# ==============================================================================
class TestBackwardsCompatibilityNoFlockUsesMainDropdown:
    def test_backwards_compatibility_no_flock_uses_main_dropdown(self):
        """[إلزامي] بلا أي تفاعل مع قائمة القطيع، species_key يبقى مطابقًا تمامًا للقطاع
        المختار من القائمة الرئيسية وحدها."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab1_species_select").select("مواشي تسمين (Beef)").run()
        # لا تفاعل إطلاقًا مع قائمة القطيع — تبقى على قيمتها الافتراضية "بلا قطيع محدد"
        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        assert not at.exception
        assert at.session_state["tab1_last_analysis"]["species_key"] == "cattle_beef"
        assert at.session_state["tab1_last_analysis"]["shipment_meta"].get("flock_name") is None

    def test_flock_dropdown_defaults_to_no_flock_placeholder(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        assert flock_box.value == "— الاعتماد على القطاع الأساسي فقط —"

    def test_main_species_dropdown_still_required_even_with_flock_chosen(self):
        """اختيار القطيع لا يُلغي الحراسة على القائمة الرئيسية — لا تزال إجبارية."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("قطيع الحلاب").run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        assert any("القطاع المستهدف" in w.value for w in at.warning)
        assert "tab1_last_analysis" not in at.session_state

    def test_main_species_selectbox_is_still_the_first_tab1_selectbox(self):
        """[ارتداد بنيوي] تصميم التبويب يعتمد على tab1_species_select كأول عنصر اختيار
        قطاع في الشاشة الأولى — يجب أن يبقى كذلك."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        tab1_selectboxes = [sb for sb in at.selectbox if sb.key and sb.key.startswith("tab1_")]
        assert "القطاع المستهدف" in tab1_selectboxes[0].label


# ==============================================================================
# ظهور اسم القطيع في رأس التقرير (render_dashboard)
# ==============================================================================
class TestFlockNameAppearsInReportHeader:
    def test_flock_name_appears_in_report_header(self):
        """[إلزامي] السطر "القطيع: ... | القطاع التنظيمي: ..." يظهر فقط عند اختيار قطيع."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab1_species_select").select("دواجن تسمين (Broiler)").run()
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("قطيع البياض").run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        header_captions = [c.value for c in at.caption if "القطيع:" in c.value]
        assert len(header_captions) == 1
        assert "قطيع البياض" in header_captions[0]
        assert "دواجن بياض (Layer)" in header_captions[0]

    def test_no_flock_header_line_when_no_flock_chosen(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab1_species_select").select("دواجن تسمين (Broiler)").run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        assert not any("القطيع:" in c.value for c in at.caption)

    def test_flock_name_and_species_key_used_appear_in_analysis_shipment_meta(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab1_species_select").select("دواجن تسمين (Broiler)").run()
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("ماشية التسمين").run()
        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        meta = at.session_state["tab1_last_analysis"]["shipment_meta"]
        assert meta["flock_name"] == "ماشية التسمين"
        assert meta["species_key_used"] == "cattle_beef"


# ==============================================================================
# واجهة إضافة قطيع مخصص (➕ إضافة قطيع جديد) — Custom Flock UI
# ==============================================================================
class TestCustomFlockUiFlow:
    def test_choosing_add_new_flock_reveals_name_and_species_inputs(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()

        assert not at.exception
        assert any("اسم القطيع الجديد" in ti.label for ti in at.text_input)
        assert any(sb.key == "tab1_new_flock_species_select" for sb in at.selectbox)

    def test_custom_flock_species_dropdown_only_offers_the_five_approved_categories(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()

        species_select = [sb for sb in at.selectbox if sb.key == "tab1_new_flock_species_select"][0]
        offered_labels = set(species_select.options) - {"— اختر القطاع المستهدف —"}
        assert offered_labels == set(c.SPECIES_LABELS_AR.values())

    def test_saving_a_valid_custom_flock_adds_it_without_exception(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()
        at.text_input(key="tab1_new_flock_name_input").input("قطيع اختبار الحفظ").run()
        species_select = [sb for sb in at.selectbox if sb.key == "tab1_new_flock_species_select"][0]
        species_select.select("مواشي حلاب (Dairy)").run()
        [b for b in at.button if b.key == "tab1_save_new_flock_button"][0].click().run(timeout=30)

        assert not at.exception
        assert at.session_state["custom_flocks"] == {"قطيع اختبار الحفظ": "cattle_dairy"}
        assert at.session_state["tab1_flock_selector"] == "قطيع اختبار الحفظ"
        assert any("تم حفظ القطيع" in s.value for s in at.success)

    def test_saving_without_a_name_shows_warning_and_saves_nothing(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()
        [b for b in at.button if b.key == "tab1_save_new_flock_button"][0].click().run(timeout=30)

        assert not at.exception
        assert at.session_state["custom_flocks"] == {}
        assert any("اسم" in w.value for w in at.warning)

    def test_saving_without_a_species_shows_warning_and_saves_nothing(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()
        at.text_input(key="tab1_new_flock_name_input").input("قطيع بلا فئة").run()
        [b for b in at.button if b.key == "tab1_save_new_flock_button"][0].click().run(timeout=30)

        assert not at.exception
        assert at.session_state["custom_flocks"] == {}
        assert any("القطاع" in w.value for w in at.warning)

    def test_newly_saved_custom_flock_can_immediately_be_used_for_analysis(self):
        """[تكامل كامل] إضافة قطيع مخصص ثم استخدامه فورًا لتحليل شحنة في نفس الجلسة."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab1_species_select").select("دواجن تسمين (Broiler)").run()
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()
        at.text_input(key="tab1_new_flock_name_input").input("عنبر تجريبي جديد").run()
        species_select = [sb for sb in at.selectbox if sb.key == "tab1_new_flock_species_select"][0]
        species_select.select("استزراع سمكي (Aquaculture)").run()
        [b for b in at.button if b.key == "tab1_save_new_flock_button"][0].click().run(timeout=30)

        at.number_input(key="tab1_aflatoxin_ppb").set_value(10.0).run()
        at.button(key="tab1_analyze").click().run(timeout=30)

        assert not at.exception
        assert at.session_state["tab1_last_analysis"]["species_key"] == "aquaculture"
        assert at.session_state["tab1_last_analysis"]["shipment_meta"]["flock_name"] == "عنبر تجريبي جديد"

    def test_custom_flock_appears_in_flock_dropdown_after_saving(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        flock_box = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        flock_box.select("إضافة قطيع جديد").run()
        at.text_input(key="tab1_new_flock_name_input").input("قطيع يظهر بالقائمة").run()
        species_select = [sb for sb in at.selectbox if sb.key == "tab1_new_flock_species_select"][0]
        species_select.select("دواجن بياض (Layer)").run()
        [b for b in at.button if b.key == "tab1_save_new_flock_button"][0].click().run(timeout=30)

        flock_box_after = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        assert "قطيع يظهر بالقائمة" in flock_box_after.options


# ==============================================================================
# القطيع يعمل بنفس المنطق في الشاشات الأخرى (Tab 2/Tab 3) — تغطية عبر الشاشات
# ==============================================================================
class TestFlockSelectorWorksAcrossAllThreeTabs:
    def test_flock_override_works_identically_in_tab2(self):
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        at.selectbox(key="tab2_species_select").select("دواجن تسمين (Broiler)").run()
        flock_box = [sb for sb in at.selectbox if sb.key == "tab2_flock_selector"][0]
        flock_box.select("حوض الاستزراع السمكي").run()
        at.number_input(key="tab2_aflatoxin_ppb").set_value(5.0).run()
        at.button(key="tab2_analyze").click().run(timeout=30)
        assert at.session_state["tab2_last_analysis"]["species_key"] == "aquaculture"

    def test_each_tab_has_an_independent_flock_selector_not_shared_state(self):
        """[ارتداد بنيوي حرج] اختيار قطيع في شاشة واحدة يجب ألا يؤثر على شاشة أخرى —
        كل شاشة تملك مفتاح session_state مستقلًا تمامًا (tab1_flock_selector مقابل
        tab2_flock_selector مقابل tab3 — التي لا تملك قطيعًا أصلًا)."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        tab1_flock = [sb for sb in at.selectbox if sb.key == "tab1_flock_selector"][0]
        tab1_flock.select("قطيع الحلاب").run()

        tab2_flock = [sb for sb in at.selectbox if sb.key == "tab2_flock_selector"][0]
        assert tab2_flock.value == "— الاعتماد على القطاع الأساسي فقط —"