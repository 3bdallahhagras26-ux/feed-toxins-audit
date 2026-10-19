# -*- coding: utf-8 -*-
"""
================================================================================
proximate_engine.py — Deterministic Proximate (Nutritional Composition) Engine
================================================================================
محرك حسابي حتمي 100% لتحليل التركيب الغذائي التقريبي (Proximate Analysis) لعلف
مُصنَّع — مستقل تمامًا عن محرك السموم الفطرية في app.py (مدخلات مختلفة، مخرجات
مختلفة، مرجع حدود مختلف في constants.py). لا LLM، لا Regex، لا نص حر — خمسة
مدخلات رقمية مباشرة (رطوبة/نيتروجين أو بروتين/دهن/ألياف/رماد) تُنتج 7 مؤشرات.

VERSION: 1.0.0
LAST ENGINEERING REVIEW: 2026-09-28

--------------------------------------------------------------------------------
ARCHITECTURAL PRINCIPLE (consistent with feed_optimizer.py وapp.py)
--------------------------------------------------------------------------------
وحدة مستقلة قابلة للاستيراد المباشر دون أي تأثير جانبي (لا Streamlit، لا أي
واجهة) — كل دالة هنا قابلة للاختبار بمعزل تمامًا. كل حد تنظيمي/مرجعي يُقرأ من
constants.SPECIES_PROXIMATE_STANDARDS حصرًا عبر get_proximate_standard() — لا رقم
مكتوب يدويًا داخل أي دالة حسابية هنا.

--------------------------------------------------------------------------------
⚠️ TIER-4 داخلي صريح: صيغ لا تحمل مرجعًا تنظيميًا مباشرًا
--------------------------------------------------------------------------------
الحدود التنظيمية نفسها (بروتين/دهن/ألياف/رماد لكل قطاع×مرحلة) موثَّقة بالكامل في
constants.py مع تصنيف Evidence Tier صريح لكل رقم (راجع ذلك الملف). لكن طريقة
"تحويل مجموعة انحرافات عن عدة حدود إلى KPI واحد مُقارَن" (الخصم المالي للبروتين،
خطر التزنخ المركَّب، مؤشر الأداء العام، عتبة الإشارة الثلاثية للمخالفات غير
المصرية) هي بحد ذاتها **قرارات هندسة مخاطر داخلية** لهذه المنصة — TIER-4 — لا
توجد لها صيغة قياسية واحدة متفق عليها عالميًا. كل صيغة من هذا النوع موثَّقة بوضوح
في docstring الدالة الخاصة بها، وتتطلب اعتماد فريق الجودة/التغذية المختص قبل
استخدامها في قرارات خصم مالي فعلية مع الموردين — تمامًا كبنود TIER-4 في
constants.py (راجع MRI/compute_supplier_score في app.py كسابقة لنفس المبدأ).
"""

from constants import (
    N_TO_PROTEIN_FACTOR,
    SPECIES_LABELS_AR,
    get_proximate_stage_options,
    get_proximate_standard,
)

# ترتيب ثابت لعرض عناصر التركيب الغذائي في الواجهة والتقرير — لا يُشتق من ترتيب
# dict عشوائي.
PROXIMATE_PARAMETER_ORDER = (
    "moisture_pct", "crude_protein_pct", "ether_extract_pct", "crude_fiber_pct", "ash_pct",
)
PROXIMATE_PARAMETER_LABELS_AR = {
    "moisture_pct": "الرطوبة (Moisture)",
    "crude_protein_pct": "البروتين الخام (Crude Protein)",
    "ether_extract_pct": "الدهن الخام (Ether Extract)",
    "crude_fiber_pct": "الألياف الخام (Crude Fiber)",
    "ash_pct": "الرماد الخام (Ash)",
    "nfe_pct": "الكربوهيدرات الذائبة (NFE)",
}

# ⚠️ عتبة الرطوبة "الرطبة" لحساب خطر التزنخ/الأكسدة (KPI 3) — نفس القيمة المستخدَمة
# بالفعل في constants.ENVIRONMENTAL_THRESHOLDS["mold_favorable_zone"]["moisture_percent_min"]
# لمحرك السموم الفطرية، معاد استخدامها هنا عمدًا للاتساق الداخلي بدل اختراع عتبة
# منفصلة غير مبررة لنفس الظاهرة الفيزيائية (رطوبة عالية تُسرّع تفاعلات الأكسدة
# والنشاط الميكروبي في آنٍ واحد). TIER-3 (نفس تصنيف المصدر الأصلي في constants.py).
RANCIDITY_MOISTURE_THRESHOLD_PCT = 14.0

# ⚠️ TIER-4: أوزان مؤشر الأداء المركَّب (Performance Index) — نقاط تُخصَم لكل نقطة
# مئوية انحراف عن الحد المرجعي، موزَّعة حسب الأثر الإنتاجي المباشر المُقدَّر هندسيًا:
# عجز البروتين يضرب معدل الزيادة الوزنية مباشرة (أعلى وزن)، الرماد الزائد (رمل/أتربة
# خاملة) يُبطل جزءًا من العليقة دون أي قيمة غذائية، الألياف الزائدة تُخفِّف الكثافة
# الغذائية وتُعسِّر الامتصاص (كلاهما وزن متوسط). لا معيار خارجي موحَّد لهذا التوزيع.
PERFORMANCE_INDEX_WEIGHTS = {
    "protein_deficit_per_point": 8.0,
    "fiber_excess_per_point": 4.0,
    "ash_excess_per_point": 5.0,
}

# ⚠️ TIER-4: عتبة "الشدة الداخلية" لتصنيف 🔴 عند مخالفة حد غير مصري المصدر (Ross
# 308/NRC/NASEM) — المضاعِف الذي عنده تُصبح المخالفة مرفوضة تمامًا رغم عدم وجود
# نص EOS1466 عليها. مثال: حد أقصى 3.0% ألياف × 1.5 = 4.5% يعني تجاوز 50% فوق الحد
# يُصنَّف 🔴 بدل 🟡. اختير 1.5× تماشيًا مع نفس فلسفة TOXIN_REJECT_MULTIPLES العامة
# في constants.py (معظمها 2.0-3.0×، لكن البروكسيمات أكثر حساسية تشغيليًا فاعتُمد
# حد أضيق 1.5× احترازيًا).
NON_EGYPTIAN_SEVERE_DEVIATION_MULTIPLE = 1.5


def _safe_float(value):
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:  # NaN guard
        return None
    return result


def compute_crude_protein_from_nitrogen(nitrogen_pct) -> float:
    """
    CP% = Nitrogen% × N_TO_PROTEIN_FACTOR (6.25، ثابت كيميائي عام TIER-1).
    يُستخدم فقط عندما يُدخِل المهندس "نسبة النيتروجين" بدل البروتين الخام مباشرة.
    """
    nitrogen_pct = _safe_float(nitrogen_pct)
    if nitrogen_pct is None:
        return None
    return round(nitrogen_pct * N_TO_PROTEIN_FACTOR, 3)


def resolve_crude_protein_pct(crude_protein_pct=None, nitrogen_pct=None):
    """
    يحل قيمة البروتين الخام النهائية من أحد مصدرين حصريين لا كليهما معًا بثقة:
      - إن أُدخل crude_protein_pct مباشرة => يُستخدَم كما هو (التفضيل الافتراضي).
      - وإلا إن أُدخل nitrogen_pct => يُحسَب CP = N × 6.25 تلقائيًا.
      - لا شيء منهما => None (لا قيمة مخترَعة).
    ⚠️ إن أُدخل الاثنان معًا بقيمتين متعارضتين، crude_protein_pct المباشر يُعطى
    الأولوية (القيمة المعملية المباشرة أوثق من قيمة مُشتقَّة حسابيًا من النيتروجين) —
    لكن هذا القرار يُسجَّل في الناتج (`protein_source`) للشفافية الكاملة، وليس
    صامتًا، حتى يلاحظ المستخدم التعارض إن وُجد.
    """
    direct_cp = _safe_float(crude_protein_pct)
    derived_cp = compute_crude_protein_from_nitrogen(nitrogen_pct)

    if direct_cp is not None:
        source = "direct"
        if derived_cp is not None and abs(direct_cp - derived_cp) > 0.5:
            source = "direct_conflicts_with_nitrogen_derived"
        return {"value": direct_cp, "source": source, "nitrogen_derived_value": derived_cp}

    if derived_cp is not None:
        return {"value": derived_cp, "source": "derived_from_nitrogen", "nitrogen_derived_value": derived_cp}

    return {"value": None, "source": "missing", "nitrogen_derived_value": None}


def compute_nfe(moisture_pct, crude_protein_pct, ether_extract_pct, crude_fiber_pct, ash_pct):
    """
    NFE (الكربوهيدرات الذائبة/عديمة الآزوت) = 100 − مجموع العناصر الخمسة الأخرى.
    صيغة حسابية بحتة (موازنة كتلة 100%) — لا تصنيف Evidence Tier مطلوب لها، فهي
    متطابقة جبريًا بصرف النظر عن القطاع أو المصدر. تتطلب الخمسة مُدخلة جميعًا
    (لا قيمة ناقصة)، وإلا يُعاد None صراحةً بدل توازن كتلة كاذب غير مكتمل.
    """
    values = [moisture_pct, crude_protein_pct, ether_extract_pct, crude_fiber_pct, ash_pct]
    safe_values = [_safe_float(v) for v in values]
    if any(v is None for v in safe_values):
        return None
    nfe = 100.0 - sum(safe_values)
    return round(nfe, 3)


def _deviation_from_standard(measured, standard_row):
    """
    يقارن قيمة مقاسة بصف حد مرجعي واحد ({"min":, "max":, ...}) ويُعيد:
      {"status": "below_min" | "above_max" | "within_range" | "no_limit_documented",
       "deviation_points": float أو None}  (نقاط مئوية خارج المدى، 0.0 إن داخل المدى)
    """
    if measured is None or standard_row is None:
        return {"status": "no_limit_documented", "deviation_points": None}

    min_bound = standard_row.get("min")
    max_bound = standard_row.get("max")

    if min_bound is not None and measured < min_bound:
        return {"status": "below_min", "deviation_points": round(min_bound - measured, 3)}
    if max_bound is not None and measured > max_bound:
        return {"status": "above_max", "deviation_points": round(measured - max_bound, 3)}
    if min_bound is None and max_bound is None:
        return {"status": "no_limit_documented", "deviation_points": None}
    return {"status": "within_range", "deviation_points": 0.0}


def compute_protein_deficit_kpi(measured_cp_pct, standard_row, feed_price_egp_per_kg, quantity_tons):
    """
    KPI 1 — مؤشر عجز البروتين والخصم المالي.
    ⚠️ TIER-4: صيغة الخصم المالي داخلية (لا معيار تجاري موحَّد عالميًا لـ "قيمة
    نقطة بروتين واحدة بالجنيه") — تفترض خصمًا تناسبيًا بسيطًا: كل 1% عجز بروتين
    عن الحد الأدنى يُخصَم بنسبة مكافئة من قيمة الشحنة الكاملة (deficit_pct / 100 ×
    القيمة الإجمالية)، كتقدير معقول لفقدان القيمة الغذائية النسبية — وليس نتيجة
    تحليل اقتصادي دقيق لسعر البروتين منفردًا في سوق المكوّنات. يتطلب اعتماد فريق
    الشراء/الجودة قبل استخدامه في مفاوضات خصم فعلية مع مورد.
    """
    measured_cp_pct = _safe_float(measured_cp_pct)
    feed_price_egp_per_kg = _safe_float(feed_price_egp_per_kg)
    quantity_tons = _safe_float(quantity_tons)

    deviation = _deviation_from_standard(measured_cp_pct, standard_row)
    deficit_points = deviation["deviation_points"] if deviation["status"] == "below_min" else 0.0
    if deviation["status"] == "no_limit_documented":
        deficit_points = None

    deduction_egp = None
    if deficit_points is not None and feed_price_egp_per_kg and quantity_tons:
        shipment_value_egp = quantity_tons * 1000 * feed_price_egp_per_kg
        deduction_egp = round(shipment_value_egp * (deficit_points / 100.0), 0)

    return {
        "measured_pct": measured_cp_pct,
        "standard_min_pct": (standard_row or {}).get("min"),
        "status": deviation["status"],
        "deficit_points": deficit_points,
        "deduction_egp": deduction_egp,
    }


def compute_fiber_adulteration_kpi(measured_cf_pct, standard_row):
    """KPI 2 — مؤشر حركة الأمعاء وغش القشور (الألياف). تجاوز الحد الأقصى يُشير
    لاحتمال غش بقشور/نخالة رخيصة بدل مكوّنات مُصنَّعة بجودة أعلى، ويزيد عبء الهضم."""
    measured_cf_pct = _safe_float(measured_cf_pct)
    deviation = _deviation_from_standard(measured_cf_pct, standard_row)
    excess_points = deviation["deviation_points"] if deviation["status"] == "above_max" else 0.0
    if deviation["status"] == "no_limit_documented":
        excess_points = None
    return {
        "measured_pct": measured_cf_pct,
        "standard_max_pct": (standard_row or {}).get("max"),
        "status": deviation["status"],
        "excess_points": excess_points,
    }


def compute_rancidity_risk_kpi(measured_ee_pct, measured_moisture_pct, standard_row):
    """
    KPI 3 — عداد أمان التزنخ والأكسدة (الدهون × الرطوبة).
    ⚠️ TIER-4 صريح: لا معيار مخبري واحد يُحوِّل "نسبة دهن + نسبة رطوبة" مباشرة إلى
    "درجة خطر تزنخ" رقمية — القياس المرجعي الحقيقي لهذا هو رقم البيروكسيد
    (Peroxide Value) المعملي، غير متوفر هنا. هذا مؤشر فرز أولي (Screening) فقط:
    يرتفع كلما زاد الدهن عن المرجع (الركيزة الكيميائية للتزنخ التأكسدي) وزادت
    الرطوبة عن عتبة النشاط الميكروبي/الكيميائي (RANCIDITY_MOISTURE_THRESHOLD_PCT) —
    وكلاهما عامل مستقل يُسهم بنصف وزن الدرجة. صيغة: نقاط الدهن الزائد ÷ 2.0 × 0.5
    + نقاط الرطوبة الزائدة ÷ 5.0 × 0.5، محدودة بـ[0, 1]. لا يُغني إطلاقًا عن فحص
    معملي فعلي للزنخ عند الشك الجاد.
    """
    measured_ee_pct = _safe_float(measured_ee_pct)
    measured_moisture_pct = _safe_float(measured_moisture_pct)
    standard_row = standard_row or {}

    ee_reference = standard_row.get("max")
    if ee_reference is None:
        ee_reference = standard_row.get("reference")

    ee_excess = 0.0
    if measured_ee_pct is not None and ee_reference is not None:
        ee_excess = max(0.0, measured_ee_pct - ee_reference)

    moisture_excess = 0.0
    if measured_moisture_pct is not None:
        moisture_excess = max(0.0, measured_moisture_pct - RANCIDITY_MOISTURE_THRESHOLD_PCT)

    if measured_ee_pct is None and measured_moisture_pct is None:
        risk_factor = None
    else:
        risk_factor = min(1.0, (ee_excess / 2.0) * 0.5 + (moisture_excess / 5.0) * 0.5)

    if risk_factor is None:
        level = "غير محدَّد"
    elif risk_factor >= 0.5:
        level = "🔴 مرتفع"
    elif risk_factor > 0.0:
        level = "🟡 متوسط"
    else:
        level = "🟢 منخفض"

    return {
        "measured_ee_pct": measured_ee_pct,
        "measured_moisture_pct": measured_moisture_pct,
        "ee_reference_pct": ee_reference,
        "risk_factor": round(risk_factor, 3) if risk_factor is not None else None,
        "level": level,
    }


def compute_ash_purity_kpi(measured_ash_pct, standard_row):
    """KPI 4 — مؤشر نقاء الشحنة والغربلة (الرماد). رماد زائد عن الحد = مادة
    معدنية خاملة غير عضوية (رمل/أتربة في الأغلب) بلا قيمة غذائية — إشارة غربلة فورية."""
    measured_ash_pct = _safe_float(measured_ash_pct)
    deviation = _deviation_from_standard(measured_ash_pct, standard_row)
    excess_points = deviation["deviation_points"] if deviation["status"] == "above_max" else 0.0
    if deviation["status"] == "no_limit_documented":
        excess_points = None
    needs_sieving = bool(excess_points) and excess_points > 0
    return {
        "measured_pct": measured_ash_pct,
        "standard_max_pct": (standard_row or {}).get("max"),
        "status": deviation["status"],
        "excess_points": excess_points,
        "needs_sieving": needs_sieving,
    }


def compute_performance_index(protein_kpi: dict, fiber_kpi: dict, ash_kpi: dict) -> dict:
    """
    KPI 6 — التغير المتوقع في الأداء (Performance Index %)، TIER-4 (راجع توثيق
    PERFORMANCE_INDEX_WEIGHTS أعلى الملف للصيغة والمبرر الكامل). 100% = مطابقة
    تامة للحدود الثلاثة المُرجَّحة (بروتين/ألياف/رماد)؛ ينخفض بخصم نقاط لكل نقطة
    مئوية انحراف. لا يُحتسَب الدهن هنا (مرجعي/استرشادي في أغلب الصفوف، لا حدّي).
    """
    w = PERFORMANCE_INDEX_WEIGHTS
    deficit = protein_kpi.get("deficit_points")
    fiber_excess = fiber_kpi.get("excess_points")
    ash_excess = ash_kpi.get("excess_points")

    if deficit is None and fiber_excess is None and ash_excess is None:
        return {"score_pct": None, "note": "لا بيانات كافية لحساب المؤشر"}

    penalty = ((deficit or 0.0) * w["protein_deficit_per_point"]
               + (fiber_excess or 0.0) * w["fiber_excess_per_point"]
               + (ash_excess or 0.0) * w["ash_excess_per_point"])
    score = max(0.0, 100.0 - penalty)
    return {"score_pct": round(score, 1), "note": None}


def compute_traffic_light(protein_kpi: dict, fiber_kpi: dict, ash_kpi: dict, standards_used: dict) -> dict:
    """
    KPI 7 — إشارة المرور الثلاثية.
    🔴 مرفوضة تمامًا: أي مخالفة (above_max/below_min) على صف مُعلَّم صراحةً
        is_egyptian_standard_limit=True في constants.py (نص المتطلبات حرفيًا:
        "مرفوضة تماماً لمخالفة المواصفة القياسية المصرية"). أو: أي مخالفة على صف
        غير مصري لكن بشدة ≥ NON_EGYPTIAN_SEVERE_DEVIATION_MULTIPLE × الحد (TIER-4،
        راجع توثيق الثابت أعلى الملف).
    🟡 مقبولة بشرط مالي أو تشغيلي: توجد مخالفة واحدة أو أكثر، لا تصل لعتبة 🔴.
    🟢 مطابقة: لا مخالفات إطلاقًا على أي من الحدود الثلاثة المفحوصة هنا.
    """
    checks = [
        ("crude_protein_pct", protein_kpi.get("status"), protein_kpi.get("deficit_points"),
         (standards_used.get("crude_protein_pct") or {}).get("min")),
        ("crude_fiber_pct", fiber_kpi.get("status"), fiber_kpi.get("excess_points"),
         (standards_used.get("crude_fiber_pct") or {}).get("max")),
        ("ash_pct", ash_kpi.get("status"), ash_kpi.get("excess_points"),
         (standards_used.get("ash_pct") or {}).get("max")),
    ]

    any_violation = False
    red_reasons = []
    yellow_reasons = []

    for param_key, status, deviation_points, bound in checks:
        if status not in ("below_min", "above_max"):
            continue
        any_violation = True
        is_egypt = bool((standards_used.get(param_key) or {}).get("is_egyptian_standard_limit"))
        label = PROXIMATE_PARAMETER_LABELS_AR.get(param_key, param_key)
        if is_egypt:
            red_reasons.append(f"{label}: مخالفة مباشرة للمواصفة القياسية المصرية [EOS1466]")
            continue
        severe = False
        if bound and deviation_points is not None and bound > 0:
            severe = deviation_points >= bound * (NON_EGYPTIAN_SEVERE_DEVIATION_MULTIPLE - 1.0)
        if severe:
            red_reasons.append(f"{label}: انحراف شديد ({deviation_points} نقطة) يتجاوز عتبة "
                                f"الشدة الداخلية {NON_EGYPTIAN_SEVERE_DEVIATION_MULTIPLE}×")
        else:
            yellow_reasons.append(f"{label}: خارج المدى المرجعي")

    if red_reasons:
        return {"code": "RED", "label_ar": "🔴 مرفوضة تمامًا", "reasons": red_reasons}
    if any_violation:
        return {"code": "YELLOW", "label_ar": "🟡 مقبولة بشرط مالي أو تشغيلي", "reasons": yellow_reasons}
    return {"code": "GREEN", "label_ar": "🟢 مطابقة", "reasons": []}


def build_full_proximate_analysis(
    species_key: str, stage_key: str, moisture_pct, crude_protein_pct=None, nitrogen_pct=None,
    ether_extract_pct=None, crude_fiber_pct=None, ash_pct=None,
    feed_price_egp_per_kg=None, quantity_tons=None,
) -> dict:
    """
    نقطة الدخول الوحيدة الموصى بها لتشغيل محرك البروكسيمات الكامل — توازي
    build_full_analysis() في app.py من حيث الدور (تجميع كل الـ KPIs في dict واحد).

    ⚠️ species_key/stage_key يجب أن يكونا من SPECIES_PROXIMATE_STANDARDS — إن لم
    تكن التركيبة موثَّقة (مثال: species_key="poultry_layer")، يُعاد dict بالمفتاح
    "error" موضِّحًا السبب، بلا أي حساب أو تخمين لاحق. هذا الفحص يحدث هنا (نقطة
    دخول واحدة) لا داخل كل دالة KPI منفردة.
    """
    standard = get_proximate_standard(species_key, stage_key)
    if standard is None:
        species_label = SPECIES_LABELS_AR.get(species_key, species_key)
        available_stages = get_proximate_stage_options(species_key)
        if not available_stages:
            reason = f"لا تتوفر معايير بروكسيمات موثَّقة لقطاع '{species_label}' حتى الآن."
        else:
            reason = f"المرحلة '{stage_key}' غير موثَّقة لقطاع '{species_label}'."
        return {"error": reason, "species_key": species_key, "stage_key": stage_key}

    protein_resolution = resolve_crude_protein_pct(crude_protein_pct, nitrogen_pct)
    resolved_cp = protein_resolution["value"]

    moisture_pct = _safe_float(moisture_pct)
    ether_extract_pct = _safe_float(ether_extract_pct)
    crude_fiber_pct = _safe_float(crude_fiber_pct)
    ash_pct = _safe_float(ash_pct)

    nfe = compute_nfe(moisture_pct, resolved_cp, ether_extract_pct, crude_fiber_pct, ash_pct)

    protein_kpi = compute_protein_deficit_kpi(
        resolved_cp, standard.get("crude_protein_pct"), feed_price_egp_per_kg, quantity_tons,
    )
    fiber_kpi = compute_fiber_adulteration_kpi(crude_fiber_pct, standard.get("crude_fiber_pct"))
    rancidity_kpi = compute_rancidity_risk_kpi(ether_extract_pct, moisture_pct, standard.get("ether_extract_pct"))
    ash_kpi = compute_ash_purity_kpi(ash_pct, standard.get("ash_pct"))
    performance_kpi = compute_performance_index(protein_kpi, fiber_kpi, ash_kpi)
    traffic_light = compute_traffic_light(protein_kpi, fiber_kpi, ash_kpi, standard)

    return {
        "error": None,
        "species_key": species_key, "stage_key": stage_key,
        "species_label_ar": SPECIES_LABELS_AR.get(species_key, species_key),
        "stage_label_ar": standard.get("label_ar", stage_key),
        "inputs": {
            "moisture_pct": moisture_pct, "crude_protein_pct": resolved_cp,
            "nitrogen_pct": _safe_float(nitrogen_pct), "protein_source": protein_resolution["source"],
            "ether_extract_pct": ether_extract_pct, "crude_fiber_pct": crude_fiber_pct, "ash_pct": ash_pct,
        },
        "nfe_pct": nfe,
        "standard_used": standard,
        "kpi_1_protein_deficit": protein_kpi,
        "kpi_2_fiber_adulteration": fiber_kpi,
        "kpi_3_rancidity_risk": rancidity_kpi,
        "kpi_4_ash_purity": ash_kpi,
        "kpi_5_nfe_pct": nfe,
        "kpi_6_performance_index": performance_kpi,
        "kpi_7_traffic_light": traffic_light,
    }
