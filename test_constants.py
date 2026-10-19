# -*- coding: utf-8 -*-
"""
tests/test_constants.py — اختبارات constants.py (المرجع الحتمي الوحيد)
================================================================================
تُثبت هذه الاختبارات أن كل رقم في constants.py متسق بنيويًا مع نفسه (لا قطاع منسي،
لا سم بدون حد، كل reject_limit أعلى من accept_limit)، وأن دوال الوصول (get_species_limit،
get_reject_multiple، get_stage_for_age، is_blending_allowed، get_synergy_factor) تُرجع
القيم الصحيحة تمامًا للمدخلات الحقيقية المستخدَمة في app.py — بما فيها حالات الحافة
(Boundary Conditions) وحالات الاستزراع السمكي ذات المضاعف المختلف عمدًا عن بقية الأنواع.
"""

import pytest

import constants as c


# ==============================================================================
# سلامة بنيوية عامة (Structural Integrity)
# ==============================================================================
class TestStructuralIntegrity:
    def test_species_keys_identical_across_all_three_structures(self):
        """SPECIES_LABELS_AR وSPECIES_REGULATORY_LIMITS وFEED_STAGES_CONFIG يجب أن يحملوا
        نفس قائمة القطاعات بالضبط — أي انحراف يعني قطاعًا نُسي في أحدها."""
        labels_keys = set(c.SPECIES_LABELS_AR.keys())
        limits_keys = set(c.SPECIES_REGULATORY_LIMITS.keys())
        stages_keys = set(c.FEED_STAGES_CONFIG.keys())
        assert labels_keys == limits_keys == stages_keys
        assert labels_keys == {
            "poultry_broiler", "poultry_layer", "cattle_dairy", "cattle_beef", "aquaculture",
        }

    def test_every_species_has_all_five_toxins(self):
        for species, toxins in c.SPECIES_REGULATORY_LIMITS.items():
            assert set(toxins.keys()) == set(c.TOXIN_KEYS), f"{species} missing a toxin row"

    def test_every_toxin_row_has_accept_and_reject_limit(self):
        for species, toxins in c.SPECIES_REGULATORY_LIMITS.items():
            for toxin, row in toxins.items():
                assert "accept_limit" in row and row["accept_limit"] > 0, (species, toxin)
                assert "reject_limit" in row and row["reject_limit"] > 0, (species, toxin)

    def test_reject_limit_always_stricter_than_or_equal_multiple_of_accept(self):
        """reject_limit يجب أن يكون دائمًا أكبر من accept_limit (هامش رفض حقيقي موجود)."""
        for species, toxins in c.SPECIES_REGULATORY_LIMITS.items():
            for toxin, row in toxins.items():
                assert row["reject_limit"] > row["accept_limit"], (species, toxin)

    def test_toxin_severity_weights_sum_to_one(self):
        total = sum(v["mri_severity_weight"] for v in c.TOXIN_METADATA.values())
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_toxin_reject_multiples_all_greater_than_one(self):
        for toxin, multiple in c.TOXIN_REJECT_MULTIPLES.items():
            assert multiple > 1.0, f"{toxin} reject multiple must exceed 1.0"

    def test_synergy_trigger_ratio_is_a_fraction(self):
        assert 0.0 < c.SYNERGY_TRIGGER_RATIO < 1.0

    def test_universal_min_blending_age_is_positive(self):
        assert c.UNIVERSAL_MIN_BLENDING_AGE_DAYS > 0


# ==============================================================================
# get_species_limit()
# ==============================================================================
class TestGetSpeciesLimit:
    def test_known_species_and_toxin(self):
        assert c.get_species_limit("poultry_broiler", "aflatoxin_ppb", "accept_limit") == 20.0
        assert c.get_species_limit("poultry_broiler", "aflatoxin_ppb", "reject_limit") == 50.0

    def test_unknown_species_returns_none(self):
        assert c.get_species_limit("dragon", "aflatoxin_ppb") is None

    def test_unknown_toxin_returns_none(self):
        assert c.get_species_limit("poultry_broiler", "unobtainium") is None

    def test_default_kind_is_accept_limit(self):
        assert c.get_species_limit("cattle_beef", "don_ppm") == c.get_species_limit(
            "cattle_beef", "don_ppm", "accept_limit"
        )


# ==============================================================================
# get_reject_multiple() — تحديدًا حالة الاستزراع السمكي ذات المضاعف المختلف عمدًا
# ==============================================================================
class TestGetRejectMultiple:
    def test_aquaculture_aflatoxin_has_tighter_custom_multiple(self):
        """أُدخل عمدًا: أفلاتوكسين الاستزراع السمكي = 1.5× (أضيق من 2.5× العام)."""
        assert c.get_reject_multiple("aquaculture", "aflatoxin_ppb") == pytest.approx(1.5)

    def test_aquaculture_ochratoxin_has_tighter_custom_multiple(self):
        """أُدخل عمدًا: أوكراتوكسين الاستزراع السمكي = 2.0× (أضيق من 3.0× العام)."""
        assert c.get_reject_multiple("aquaculture", "ochratoxin_ppb") == pytest.approx(2.0)

    def test_other_species_use_the_toxin_level_default(self):
        """قطاعات أخرى غير الاستزراع السمكي يجب أن تستخدم نفس المضاعف الافتراضي — لم
        تتأثر بتضييق الاستزراع السمكي إطلاقًا."""
        assert c.get_reject_multiple("poultry_broiler", "aflatoxin_ppb") == pytest.approx(2.5)
        assert c.get_reject_multiple("poultry_layer", "aflatoxin_ppb") == pytest.approx(2.5)
        assert c.get_reject_multiple("cattle_dairy", "ochratoxin_ppb") == pytest.approx(3.0)
        assert c.get_reject_multiple("cattle_beef", "ochratoxin_ppb") == pytest.approx(3.0)

    def test_multiple_matches_actual_stored_ratio_for_every_species_and_toxin(self):
        """اختبار شامل: المضاعف المُعاد يجب أن يساوي دائمًا reject_limit/accept_limit
        الفعليين المخزَّنين — بصرف النظر عن كون القيمة مطابقة للعام أو مختلفة عنه عمدًا."""
        for species, toxins in c.SPECIES_REGULATORY_LIMITS.items():
            for toxin, row in toxins.items():
                expected = row["reject_limit"] / row["accept_limit"]
                assert c.get_reject_multiple(species, toxin) == pytest.approx(expected)


# ==============================================================================
# get_stage_for_age() — حالات الحافة (Boundary Conditions)
# ==============================================================================
class TestGetStageForAge:
    @pytest.mark.parametrize(
        "age_days,expected_stage",
        [
            (0, "starter"), (5, "starter"), (10, "starter"),   # نهاية مرحلة البادي بالضبط
            (11, "grower"), (18, "grower"), (24, "grower"),    # نهاية مرحلة النامي بالضبط
            (25, "finisher"), (42, "finisher"), (500, "finisher"),  # لا حد أقصى للناهي
        ],
    )
    def test_broiler_stage_boundaries(self, age_days, expected_stage):
        assert c.get_stage_for_age("poultry_broiler", age_days) == expected_stage

    def test_species_with_single_unified_stage_ignores_age(self):
        """cattle_dairy له مرحلة واحدة مجمّعة (age_days_min/max = None) — أي عمر يُعيدها."""
        assert c.get_stage_for_age("cattle_dairy", 5) == "lactating"
        assert c.get_stage_for_age("cattle_dairy", 9000) == "lactating"

    def test_none_age_returns_none(self):
        assert c.get_stage_for_age("poultry_broiler", None) is None

    def test_unknown_species_returns_none(self):
        assert c.get_stage_for_age("dragon", 5) is None


# ==============================================================================
# is_blending_allowed() — القاعدة القاطعة (Hard Override)
# ==============================================================================
class TestIsBlendingAllowed:
    def test_age_below_universal_floor_always_blocks_regardless_of_species(self):
        for species in c.SPECIES_REGULATORY_LIMITS:
            result = c.is_blending_allowed(species, age_days=c.UNIVERSAL_MIN_BLENDING_AGE_DAYS - 1)
            assert result["allowed"] is False

    def test_age_at_exactly_the_floor_is_allowed_from_age_perspective(self):
        """>= الحد الأدنى مسموح (الشرط الصارم هو age < floor، وليس <=)."""
        result = c.is_blending_allowed("poultry_broiler", age_days=c.UNIVERSAL_MIN_BLENDING_AGE_DAYS)
        # يوم 14 يقع في مرحلة "grower" (11-24) التي allow_blending=True، فلا مانع مزدوج هنا
        assert result["allowed"] is True

    def test_broiler_starter_stage_blocked_even_though_subsumed_by_universal_floor(self):
        """البادي (0-10 يوم) محظور صراحة allow_blending=False، وأيضًا < 14 يوم عالميًا —
        الحالتان تتفقان هنا، لكن يجب التأكد أن القرار لا يزال REJECT بغض النظر عن أيهما."""
        result = c.is_blending_allowed("poultry_broiler", age_days=5)
        assert result["allowed"] is False

    def test_broiler_grower_stage_at_valid_age_is_allowed(self):
        result = c.is_blending_allowed("poultry_broiler", age_days=20)
        assert result["allowed"] is True

    def test_stage_level_block_independent_of_age_floor(self):
        """يعزل آلية حظر المرحلة (allow_blending=False) عن آلية حظر العمر العالمية، عبر
        تمرير stage_key صراحةً بعمر لا يقع أصلًا ضمن مرحلة البادي — يثبت أن حظر المرحلة
        نفسه (وليس فقط تصادفه مع حظر العمر) هو ما يُنتج القرار."""
        result = c.is_blending_allowed("poultry_broiler", age_days=20, stage_key="starter")
        assert result["allowed"] is False

    def test_none_age_with_default_stage_is_allowed(self):
        """لا عمر محدَّد ولا قطاع له قيود مرحلية صارمة (dairy) => مسموح من ناحية العمر."""
        result = c.is_blending_allowed("cattle_dairy", age_days=None)
        assert result["allowed"] is True


# ==============================================================================
# normalize_species_key()
# ==============================================================================
class TestNormalizeSpeciesKey:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("poultry_broiler", "poultry_broiler"), ("Broiler", "poultry_broiler"),
            ("broiler", "poultry_broiler"), ("تسمين", "poultry_broiler"),
            ("بياض", "poultry_layer"), ("Layer", "poultry_layer"),
            ("Dairy", "cattle_dairy"), ("حلاب", "cattle_dairy"), ("ألبان", "cattle_dairy"),
            ("Beef", "cattle_beef"), ("مواشي تسمين", "cattle_beef"),
            ("Aquaculture", "aquaculture"), ("أسماك", "aquaculture"), ("fish", "aquaculture"),
        ],
    )
    def test_valid_variants(self, raw, expected):
        assert c.normalize_species_key(raw) == expected

    def test_none_input(self):
        assert c.normalize_species_key(None) is None

    def test_empty_string(self):
        assert c.normalize_species_key("") is None

    def test_garbage_input_returns_none(self):
        assert c.normalize_species_key("spaceship") is None

    def test_case_insensitive(self):
        assert c.normalize_species_key("BROILER") == "poultry_broiler"


# ==============================================================================
# get_synergy_factor()
# ==============================================================================
class TestGetSynergyFactor:
    def test_documented_pair_returns_data(self):
        result = c.get_synergy_factor("don_ppm", "zearalenone_ppm")
        assert result["engineering_multiplier"] == pytest.approx(1.25)

    def test_documented_pair_is_order_independent(self):
        forward = c.get_synergy_factor("don_ppm", "zearalenone_ppm")
        backward = c.get_synergy_factor("zearalenone_ppm", "don_ppm")
        assert forward == backward

    def test_undocumented_pair_returns_empty_dict(self):
        result = c.get_synergy_factor("zearalenone_ppm", "ochratoxin_ppb")
        assert result == {}

    def test_all_documented_multipliers_exceed_one(self):
        for pair, data in c.MYCOTOXIN_SYNERGY_MATRIX.items():
            assert data["engineering_multiplier"] > 1.0, pair