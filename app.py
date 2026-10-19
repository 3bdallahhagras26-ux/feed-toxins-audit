# -*- coding: utf-8 -*-
"""
================================================================================
Feed Toxins Audit  |  منصة تدقيق جودة الأعلاف (سموم فطرية + بروكسيمات)
================================================================================
B2B SaaS Engineering Prototype — 100% Deterministic Python Risk Engine
Architecture: Streamlit (UI) + Python (Deterministic Math Core) — لا LLM، لا Regex،
              لا نص حر. كل إدخال — في كل الشاشات الثلاث — يدوي منظَّم (Structured
              Manual Input) حصرًا: حقول رقمية مباشرة (st.number_input) فقط.

VERSION: 3.0.0
LAST ENGINEERING REVIEW: 2026-09-28

CHANGELOG:
- v3.0.0 — إعادة هيكلة جذرية: 3 شاشات تحليل جديدة بدل تبويبات طرق الإدخال القديمة.
  ⚠️ استبدال كامل (بقرار صريح من الطلب، لا تدرّج): التبويبات الثلاثة القديمة
  (📝 نص حر / 📁 رفع ملف / 🧮 إدخال منظم — طرق إدخال لنفس شاشة السموم) حُذفت
  بالكامل، واستُبدلت بثلاث شاشات تحليل بمعنى مختلف تمامًا:
    Tab 1 "🧪 تأمين القطيع والسموم الفطرية" — شاشة السموم الأصلية كما هي 100%
      (نفس compute_risk_ratios/compute_mri/compute_final_decision/compute_blending_ratio/
      .../build_full_analysis بلا أي تعديل حسابي)، لكن بإدخال يدوي منظم فقط الآن
      (لا نص حر، لا رفع ملف) — نفس حقول Tab "إدخال يدوي منظم" القديم حرفيًا.
    Tab 2 "🔬 التدقيق الكامل والشامل" — سموم + بروكسيمات معًا في شاشة واحدة: نفس الـ 5
      سموم + 3 تخزين + الـ 5 بروكسيمات، تُشغِّل المحركين المستقلين (app.py للسموم،
      proximate_engine.py للبروكسيمات) بالتوازي على نفس بيانات الشحنة، وتعرض
      لوحتين منفصلتين + تقرير PDF موحَّد واحد.
    Tab 3 "📋 التحليل التقريبي فقط" — بروكسيمات فقط (بلا سموم إطلاقًا)، لمن يملك
      تقرير تغذية عادي بلا بيانات سموم: 5 مدخلات (رطوبة + بروتين/نيتروجين + دهن +
      ألياف + رماد) → 7 مؤشرات (راجع proximate_engine.py للتوثيق الكامل).
  ▸ حذف كامل لمحرك الذكاء الاصطناعي ولمسارات التفريغ النصي (قرار صريح من الطلب —
    "حذف محرك الذكاء الاصطناعي (No OpenRouter / No LLM API)" و"إلغاء الإدخال النصي
    الحر ورفع ملفات الإكسل" حرفيًا): أُزيلت MASTER_SYSTEM_PROMPT،
    clean_llm_json_response/parse_llm_json_response (طبقتا تنظيف/إصلاح JSON)،
    call_openrouter_llm (ونموذج OpenAI client المرتبط به)، fetch_openrouter_free_models/
    FALLBACK_FREE_MODELS، extract_parameters_regex (والمحلل الحتمي السريع بكل أنماطه)،
    parse_shipment_text (المنسّق الهجين)، ENGINE_REGEX/ENGINE_LLM/ENGINE_FALLBACK_CHAIN
    ومؤشراتها. حقل مفتاح OpenRouter API واختيار الموديل حُذفا من الشريط الجانبي —
    لا حاجة لهما في نظام بلا أي استدعاء شبكة لأي LLM. حزمتا `openai` و`json-repair`
    لم تعودا تبعيتين مطلوبتين لتشغيل app.py (قد تبقيان في requirements-dev.txt فقط
    إذا استُخدمتا في اختبارات تاريخية قديمة — راجع README.md).
  ▸ ⚠️ تبسيط مرتبط: species_mismatch/llm_parsed_species_key (في build_full_analysis
    وrender_dashboard) أُزيلا بالكامل — كانا تدقيقًا تقاطعيًا لما "يستخرجه النموذج
    اللغوي من النص" مقابل اختيار المستخدم اليدوي؛ بلا LLM لم يعد target_species
    يُملأ إطلاقًا، فالتدقيق التقاطعي أصبح كودًا ميتًا دائم القيمة False. حقل
    normalize_species_key في constants.py بقي كما هو (غير ضار، قد يُستخدم لاحقًا
    إن أُعيد أي مسار تفريغ نصي يومًا) لكن app.py توقف عن استدعائه.
  ▸ الجديد: proximate_engine.py (محرك بروكسيمات حتمي مستقل بالكامل، 7 KPIs — راجع
    توثيقه الخاص) وpdf_report.py (توليد شهادات PDF رسمية بـ ReportLab + دعم عربي
    كامل عبر arabic-reshaper + python-bidi + خط FreeSerif، راجع توثيقه الخاص لتفاصيل
    القرار الهندسي واختباره البصري). constants.py أُضيف له SPECIES_PROXIMATE_STANDARDS
    وN_TO_PROTEIN_FACTOR (راجع constants.py v1.3.0).
  ▸ خانات البصمة الرسمية للشحنة (نوع الخامة/العلف، اسم المورد/الشركة، رقم
    التشغيلة/السيارة، تاريخ الشحنة) أُضيفت لكل الشاشات الثلاث — تُستخدَم في رأس
    التقرير وفي شهادة الـ PDF؛ اختيارية (None إن تُركت فارغة)، لا تؤثر في أي حساب.
  ▸ زر "📄 توليد شهادة PDF رسمية" في كل شاشة بعد ظهور النتيجة — يبني الشهادة عبر
    pdf_report.py ويعرضها كـ st.download_button (لا حفظ تلقائي على القرص، التحميل
    بيد المستخدم). الزر يظهر فقط بعد تحليل ناجح (لا قبل وجود نتيجة لتصديرها).
  ▸ القطيع/العنبر (v2.3.0) بقي يعمل بلا أي تعديل حسابي — لكل شاشة الآن نسخة مستقلة
    من محدِّد القطاع/القطيع/العمر (نفس render_species_flock_age_selector() المشتركة،
    بمفاتيح session_state مُسبوقة بلاحقة الشاشة key_prefix لمنع أي تصادم).
  ▸ الاختبارات: أُعيد بناء مجموعة الاختبارات بالكامل لتعكس الهيكل الجديد — راجع
    README.md وCHANGELOG.md للتفصيل الكامل (ملفات اختبار أُزيلت لأنها تستهدف كودًا
    حُذف، أخرى أُضيفت للشاشات الجديدة، test_math_engine.py/test_constants.py/
    test_feed_optimizer.py بقيت كما هي لأن الكود الذي تغطيه لم يتغيّر إطلاقًا).

(للتاريخ الكامل لإصدارات v2.x — المحلل الهجين Regex/LLM، ربط القطيع، الإدخال
المنظَّم الأول — راجع CHANGELOG.md؛ أُزيل من هنا لأنه يوثّق كودًا لم يعد موجودًا.)
"""

import os
import re
import sys
from math import gcd

# ⚠️ ضمان دفاعي: يضيف مجلد app.py نفسه إلى sys.path قبل استيراد الموديولات المحلية
# (constants، feed_optimizer، proximate_engine، pdf_report). Streamlit يضيف هذا المجلد
# تلقائيًا في الحالة الطبيعية (streamlit run app.py من نفس المجلد)، لكن هذا يحمي من حالات
# بيئية نادرة (اختصارات تشغيل، بعض إعدادات IDE، أو تشغيل من مسار مختلف) قد لا يحدث فيها ذلك تلقائيًا.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

# ⚠️ فحص تشخيصي فوري وواضح — بدل الانتظار حتى يفشل "from constants import (...)" أدناه
# برسالة ModuleNotFoundError عامة لا تحدد أين بحث بايثون فعليًا ولا أين يجب أن يكون الملف.
# هذا يحوّل "خطأ غامض يحتاج تخمينًا" إلى "رسالة تخبرك بالمسار الدقيق المفحوص والحل المباشر" —
# إذا ظهر هذا الخطأ، فالسبب مؤكَّد 100% أن constants.py غير موجود في نفس مجلد app.py، وليس
# مشكلة sys.path (التي عالجها الكود أعلاه فعلًا قبل الوصول لهذا الفحص).
_CONSTANTS_PATH = os.path.join(_APP_DIR, "constants.py")
if not os.path.isfile(_CONSTANTS_PATH):
    raise FileNotFoundError(
        f"لم يُعثر على constants.py في المسار المتوقَّع بالضبط:\n  {_CONSTANTS_PATH}\n\n"
        f"مجلد app.py الحالي هو:\n  {_APP_DIR}\n\n"
        "الحل: تأكد من نسخ constants.py وproximate_engine.py وpdf_report.py "
        "(وfeed_optimizer.py إن كنت تستخدم ميزة صياغة العلف) إلى نفس هذا المجلد بالضبط — "
        "بجانب app.py مباشرة، ليس في مجلد فرعي ولا في مكان آخر — ثم أعد تشغيل التطبيق."
    )

import streamlit as st

from constants import (
    ENVIRONMENTAL_THRESHOLDS,
    FEED_STAGES_CONFIG,
    FLOCK_TO_SPECIES_MAP,
    SPECIES_LABELS_AR,
    SPECIES_REGULATORY_LIMITS,
    SYNERGY_TRIGGER_RATIO,
    TILAPIA_AFLATOXIN_LITERATURE_CEILING_PPB,
    TOXIN_KEYS,
    TOXIN_METADATA,
    UNIVERSAL_MIN_BLENDING_AGE_DAYS,
    get_reject_multiple,
    get_species_limit,
    get_stage_for_age,
    get_synergy_factor,
    is_blending_allowed,
)
import proximate_engine as prox
import pdf_report

# ==============================================================================
# 2) ثوابت سلوك هندسي على مستوى التطبيق (App-Level Behavior Parameters)
# ==============================================================================
# ⚠️ فرق جوهري عن constants.py: كل ما هنا هو "كيف يتصرف محرك العرض/القرار"، وليس
# "ما هو الحد التنظيمي" — الحدود التنظيمية وحدود الرفض ومصفوفة التآزر ومراحل العمر
# كلها الآن تُقرأ حصريًا من constants.py (SPECIES_REGULATORY_LIMITS، TOXIN_REJECT_MULTIPLES،
# MYCOTOXIN_SYNERGY_MATRIX، FEED_STAGES_CONFIG) — لا يوجد أي رقم تنظيمي مكتوب هنا بعد الآن.
BINDER_TRIGGER_RATIO = 0.60  # عتبة تفعيل توصية "مضاد السموم" الوقائي كنسبة من الحد التنظيمي — سلوك قرار، وليس حدًا تنظيميًا

# ⚠️ مزامنة العرض (Display Sync): لو القرار الحتمي أصبح REJECT صراحةً، يُفرض حد أدنى
# لمؤشر MRI حتى لا يظهر كارت "خطورة منخفضة/متوسطة" بجانب كارت "قرار: رفض" — تعارض بصري
# بين كارتين يعرضان نفس الشحنة. لا يُطبَّق هذا الحد الأدنى على BLEND_REQUIRED: شحنة قابلة
# للمعالجة بالخلط يُحسب MRI لها بالمعادلة الطبيعية الكاملة بدون فرض أي حد أدنى.
MRI_HARD_FLOOR = 75.0
RATIO_SATURATION_CAP = 3.0  # أي تجاوز أكبر من 3× الحد لا يزيد درجة الخطورة أكثر (Saturation) — سقف سلوك عرض

# ثوابت نموذج التخزين (Storage Decay Model) — هيوريستيك هندسي موثّق، وليس رقمًا تنظيميًا رسميًا
STORAGE_BASE_SAFE_DAYS = 120
STORAGE_WORST_CASE_LIFESPAN_FRACTION = 0.15  # في أسوأ الأحوال يتبقى 15% فقط من العمر الافتراضي الآمن

# ثوابت نموذج تدهور FCR — نموذج تقديري مبني على الأدبيات البيطرية، قابل للمعايرة على بيانات المزرعة الفعلية
FCR_MAX_PENALTY_BY_SPECIES = {
    "poultry_broiler": 0.35,
    "poultry_layer": 0.22,
    "cattle_dairy": 0.18,
    "cattle_beef": 0.20,
    "aquaculture": 0.30,
}
FCR_CURVE_EXPONENT = 1.2  # تقعّر بسيط: الضرر يتصاعد بشكل غير خطي مع ازدياد MRI


# ==============================================================================
# 3) أدوات مساعدة عامة (Generic Helpers)
# ==============================================================================
def _safe_float(value):
    """تحويل آمن لأي قيمة إلى float، مع إرجاع None عند الفشل بدلاً من رمي استثناء."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value, low, high):
    return max(low, min(high, value))


_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    """
    يحذف أي رمز تعبيري (Emoji) من نص قادم من طبقة أخرى (مثل proximate_engine.py،
    الذي لا يزال يُرجع قيمًا نصية مثل "level"/"label_ar" محمَّلة برموز تعبيرية في
    بياناته الخاصة ولاختباراته الخاصة — لم تُعدَّل عمدًا لبقاء proximate_engine.py
    خارج نطاق تنظيف واجهة app.py). يُطبَّق هذا الحذف فقط عند لحظة العرض في app.py،
    فلا تتأثر proximate_engine.py ولا اختباراتها القائمة بسياسة "صفر إيموجي" في الواجهة.
    """
    if not text:
        return text
    return _EMOJI_PATTERN.sub("", text).strip()


def build_structured_parsed_json(
    lab_results: dict, storage: dict, quantity_tons=None, flock_name=None, species_key_used=None,
) -> dict:
    """
    يبني Schema الـ JSON القياسي (shipment_meta / normalized_inputs / parsing_audit)
    من حقول رقمية مُدخَلة مباشرة — المسار الوحيد المتبقي لتغذية build_full_analysis()
    (لا نص حر، لا Regex، لا LLM؛ راجع ملاحظة v3.0.0 أعلى الملف).

    ⚠️ value=None في حقول الواجهة يعني "غير مُدخَل" (مجهول) — يمر هنا كما هو None، لا 0.0.
    missing_critical_fields تُحسَب من lab_results فقط (لا تشمل حقول التخزين/الشحنة
    الاختيارية).
    """
    missing = [k for k in TOXIN_KEYS if lab_results.get(k) is None]
    return {
        "shipment_meta": {
            "supplier_name": None, "feed_type": None, "shipment_date": None,
            "quantity_tons": quantity_tons, "flock_name": flock_name, "species_key_used": species_key_used,
        },
        "normalized_inputs": {
            "lab_results": dict(lab_results),
            "storage": dict(storage),
            "parameters": {
                "target_species": None, "flock_age_days": None,
                "toxin_binder_added": False, "binder_type": None,
            },
        },
        "parsing_audit": {
            "is_valid_input": True,
            "missing_critical_fields": missing,
            "parsing_notes": "Structured manual input (no LLM, no regex, no free text).",
        },
    }


# ==============================================================================
# 6) المحرك الحسابي الحتمي — Deterministic Python Math Core
# ==============================================================================
def compute_risk_ratios(lab_results: dict, species_key: str) -> dict:
    """
    لكل سم من TOXIN_KEYS (constants.py): القيمة المقاسة ÷ accept_limit التنظيمي لهذا
    القطاع = نسبة الخطورة. القيم الناقصة أو غير القابلة للتحويل تُستبعد (None). الحد
    التنظيمي نفسه يُقرأ حصريًا من constants.SPECIES_REGULATORY_LIMITS عبر get_species_limit —
    لا يوجد أي رقم حد مكتوب هنا.
    """
    ratios = {}
    for toxin_key in TOXIN_KEYS:
        accept_limit = get_species_limit(species_key, toxin_key, "accept_limit")
        measured = _safe_float(lab_results.get(toxin_key))
        if measured is None or not accept_limit:
            ratios[toxin_key] = None
        else:
            ratios[toxin_key] = round(measured / accept_limit, 3)
    return ratios


def compute_storage_risk(temperature_c, moisture_pct) -> dict:
    """
    Card 4 — Storage Risk.
    منطقة الخطورة الفطرية المعروفة: حرارة ≥27°م + رطوبة ≥14% (أدبيات تخزين الحبوب والأعلاف).
    نموذج ثنائي المتغيرات (AND logic عبر الضرب) لأن نمو الفطريات يتطلب الحرارة والرطوبة معًا.
    """
    temperature_c = _safe_float(temperature_c)
    moisture_pct = _safe_float(moisture_pct)
    if temperature_c is None or moisture_pct is None:
        return {"level": "غير محدد", "combined_risk_factor": 0.0, "temp_factor": 0.0, "moisture_factor": 0.0}

    temp_bounds = ENVIRONMENTAL_THRESHOLDS["temperature_c"]
    moisture_bounds = ENVIRONMENTAL_THRESHOLDS["moisture_percent"]
    temp_factor = _clamp(
        (temperature_c - temp_bounds["risk_floor"]) / (temp_bounds["risk_ceiling"] - temp_bounds["risk_floor"]),
        0.0, 1.0,
    )
    moist_factor = _clamp(
        (moisture_pct - moisture_bounds["risk_floor"]) / (moisture_bounds["risk_ceiling"] - moisture_bounds["risk_floor"]),
        0.0, 1.0,
    )
    combined = temp_factor * moist_factor

    if combined >= 0.66:
        level = "حرج — بيئة حاضنة نشطة للفطريات"
    elif combined >= 0.33:
        level = "متوسط — مراقبة لازمة"
    elif combined > 0:
        level = "منخفض"
    else:
        level = "آمن"

    return {
        "level": level,
        "combined_risk_factor": round(combined, 3),
        "temp_factor": round(temp_factor, 2),
        "moisture_factor": round(moist_factor, 2),
    }


def compute_mri(risk_ratios: dict, temperature_c, moisture_pct, final_decision: dict) -> dict:
    """
    Card 1 — Mycotoxin Risk Index (0-100).
    مؤشر مركّب مرجّح حسب شدة كل سم (TOXIN_METADATA.mri_severity_weight من constants.py)،
    مع إعادة توزيع الأوزان تلقائيًا عند غياب أي سم من نتائج المعمل، بالإضافة إلى:
      (أ) مضاعف التآزر الفطري (MYCOTOXIN_SYNERGY_MATRIX من constants.py): إذا تعايش سمّان
          موثّق تآزرهما معًا وكلاهما ≥ SYNERGY_TRIGGER_RATIO من حده التنظيمي الخاص، يُطبَّق
          أعلى مضاعف تآزر موثّق منطبق على المجموع المرجّح — أعلى مضاعف فقط (وليس ضرب كل
          الأزواج المنطبقة معًا) تفاديًا لتضخّم غير واقعي عند تعايش أكثر من زوجين في آن واحد.
      (ب) جزاء إضافي (حتى 10 نقاط) عن ظروف التخزين الحاضنة للفطريات — الخطر لا يتوقف عند
          لحظة التحليل بل يستمر في التصاعد أثناء التخزين.

    ⚠️ حد أدنى إجباري (Hard Floor): يُطبَّق فقط عندما يكون القرار الحتمي المعتمد REJECT
    صراحةً — لا يمكن للمؤشر أن يقل عن MRI_HARD_FLOOR (75/100) في هذه الحالة، لمنع تعارض
    بصري بين كارت "الخطورة" وكارت "القرار المعتمد" لنفس الشحنة. لا يُطبَّق هذا الحد على
    BLEND_REQUIRED أو BINDER_REQUIRED أو APPROVE — تلك الحالات تُحسب بالمعادلة الطبيعية
    الكاملة (شاملة مضاعف التآزر إن وُجد) دون أي حد أدنى مفروض.
    """
    available = {k: v for k, v in risk_ratios.items() if v is not None}
    storage_risk = compute_storage_risk(temperature_c, moisture_pct)

    if not available:
        return {
            "score": None, "breakdown": {}, "storage_penalty": 0.0,
            "note": "لا توجد نتائج معملية كافية لحساب المؤشر",
        }

    total_weight_available = sum(TOXIN_METADATA[k]["mri_severity_weight"] for k in available)
    breakdown, weighted_sum = {}, 0.0
    for toxin_key, ratio in available.items():
        weight = TOXIN_METADATA[toxin_key]["mri_severity_weight"] / total_weight_available
        capped_ratio = min(ratio, RATIO_SATURATION_CAP)
        contribution = (capped_ratio / RATIO_SATURATION_CAP) * 100 * weight
        breakdown[toxin_key] = round(contribution, 1)
        weighted_sum += contribution

    synergy_multiplier = 1.0
    synergy_pairs_triggered = []
    toxin_list = list(available.keys())
    for i in range(len(toxin_list)):
        for j in range(i + 1, len(toxin_list)):
            toxin_a, toxin_b = toxin_list[i], toxin_list[j]
            if available[toxin_a] >= SYNERGY_TRIGGER_RATIO and available[toxin_b] >= SYNERGY_TRIGGER_RATIO:
                synergy_data = get_synergy_factor(toxin_a, toxin_b)
                if synergy_data:
                    synergy_pairs_triggered.append((toxin_a, toxin_b, synergy_data["engineering_multiplier"]))
                    synergy_multiplier = max(synergy_multiplier, synergy_data["engineering_multiplier"])

    weighted_sum *= synergy_multiplier

    storage_penalty = storage_risk["combined_risk_factor"] * 10
    final_score = weighted_sum + storage_penalty

    floor_applied = final_decision.get("code") == "REJECT"
    if floor_applied:
        final_score = max(final_score, MRI_HARD_FLOOR)
    final_score = min(100.0, final_score)

    return {
        "score": round(final_score, 1),
        "breakdown": breakdown,
        "storage_penalty": round(storage_penalty, 1),
        "floor_applied": floor_applied,
        "synergy_multiplier": round(synergy_multiplier, 3),
        "synergy_pairs_triggered": [(a, b) for a, b, _ in synergy_pairs_triggered],
    }


def compute_safe_storage_lifespan(temperature_c, moisture_pct, storage_days_elapsed) -> dict:
    """
    Card 5 — Safe Storage Lifespan.
    نموذج تناقص خطي مبسّط: كلما اقتربت ظروف الحرارة/الرطوبة من "المنطقة الحاضنة"، كلما
    تقلّص العمر الافتراضي الآمن للتخزين (حتى 15% فقط منه في أسوأ الحالات).
    """
    storage_risk = compute_storage_risk(temperature_c, moisture_pct)
    combined = storage_risk["combined_risk_factor"]
    effective_lifespan = STORAGE_BASE_SAFE_DAYS * (1 - (1 - STORAGE_WORST_CASE_LIFESPAN_FRACTION) * combined)
    elapsed = _safe_float(storage_days_elapsed) or 0.0
    remaining = max(0, round(effective_lifespan - elapsed))
    return {
        "effective_total_lifespan_days": round(effective_lifespan),
        "days_elapsed": round(elapsed),
        "days_remaining": remaining,
        "is_overdue": remaining == 0 and elapsed > 0,
    }


def compute_fcr_deterioration(mri_score, species_key) -> dict:
    """
    Card 2 — FCR Deterioration.
    ⚠️ نموذج هندسي تقديري (Heuristic Model) وليس رقمًا تنظيميًا رسميًا: يربط مؤشر الخطورة
    المركّب MRI بمقدار تدهور معامل التحويل الغذائي المتوقع، بمنحنى غير خطي بسيط (تقعّر
    خفيف) يعكس تصاعد الضرر البيولوجي مع زيادة التلوث. يُنصح بمعايرة FCR_MAX_PENALTY_BY_SPECIES
    دوريًا على بيانات الأداء الفعلية للمزرعة (Real FCR/Mortality Data) كلما توفرت.
    """
    if mri_score is None:
        return {"delta_fcr": None, "max_possible_penalty": None}
    max_penalty = FCR_MAX_PENALTY_BY_SPECIES.get(species_key, 0.25)
    normalized_mri = mri_score / 100.0
    delta = max_penalty * (normalized_mri ** FCR_CURVE_EXPONENT)
    return {"delta_fcr": round(delta, 3), "max_possible_penalty": max_penalty}


def compute_blending_ratio(
    risk_ratios: dict, lab_results: dict, species_key: str, final_decision: dict,
    clean_feed_toxin_levels: dict = None,
) -> dict:
    """
    Card 6 — Blending Guide (معادلة الخلط الدقيق / Pearson Square Two-Point Mixing Formula).
        F = 100 × (C − L) / (H − L)
    C = الحد التنظيمي المستهدف | H = تركيز السم في الشحنة الملوثة | L = تركيز السم في العلف النظيف
    المرجع: University of Nebraska–Lincoln Extension, "Use of Mycotoxin-Contaminated Feed for
    Animals" (EC3066) — نفس الصيغة القياسية المستخدمة صناعيًا لحساب نسب الخلط.

    ⚠️ L قابل للتهيئة الآن (لم يعد مثبَّتًا على صفر): `clean_feed_toxin_levels` قاموس
    اختياري {toxin_key: تركيز فعلي في العلف النظيف المقترح للخلط} — يأتي من "إعدادات
    الخلط المتقدمة" في الواجهة، حيث يمكن للمستخدم إدخال نتيجة معملية فعلية للعلف النظيف
    إن كانت متاحة (نادرًا ما يكون العلف "النظيف" خاليًا 100%). عند عدم توفير قيمة لسم
    معيّن (أو عدم تمرير القاموس إطلاقًا)، يُستخدَم L=0.0 كافتراض احترازي "متفائل" (Best-case)
    كما كان الحال سابقًا — لا تغيير في السلوك الافتراضي، فقط إمكانية دقة أعلى عند توفر بيانات.

    ⚠️ مزامنة مع القرار الحتمي: إذا كان القرار المعتمد REJECT، فالخلط غير مطروح كخيار
    إطلاقًا مهما كانت نتيجة معادلة بيرسون — تُعرض 0:1 (صفر% علف ملوث) لضمان ألا يتعارض
    هذا الكارت بصريًا مع كارت "القرار المعتمد" لنفس الشحنة.
    """
    if final_decision.get("code") == "REJECT":
        return {
            "needed": False,
            "rejected": True,
            "ratio_text_contaminated_to_clean": "0:1",
            "note": "الشحنة مرفوضة بالكامل (تجاوزت عتبة الرفض) — الخلط غير مطروح كخيار؛ لا تُستخدم أي نسبة من هذه الشحنة.",
        }

    worst_toxin, worst_ratio = None, 0.0
    for toxin_key, ratio in risk_ratios.items():
        if ratio is not None and ratio > worst_ratio:
            worst_toxin, worst_ratio = toxin_key, ratio

    if worst_toxin is None or worst_ratio <= 1.0:
        return {"needed": False, "rejected": False, "note": "الشحنة ضمن الحدود التنظيمية المسموحة — لا حاجة للخلط"}

    H = _safe_float(lab_results.get(worst_toxin))
    C = get_species_limit(species_key, worst_toxin, "accept_limit")
    L = _safe_float((clean_feed_toxin_levels or {}).get(worst_toxin)) or 0.0
    if H is None or C is None:
        return {"needed": False, "rejected": False, "note": "بيانات غير كافية لحساب نسبة الخلط بدقة"}
    if H <= L:
        return {
            "needed": False, "rejected": False,
            "note": "العلف 'النظيف' المحدَّد ليس أقل تلوّثًا فعليًا من الشحنة نفسها لهذا السم "
                    "(L ≥ H) — لا يمكن حساب نسبة خلط مجدية بهذين المصدرين؛ استخدم علفًا نظيفًا "
                    "بتركيز أقل، أو راجع القيمة المُدخَلة في إعدادات الخلط المتقدمة.",
        }

    F = _clamp(100.0 * (C - L) / (H - L), 0.0, 100.0)
    contaminated_parts, clean_parts = round(F), round(100 - F)
    divisor = gcd(contaminated_parts, clean_parts) or 1
    ratio_text = f"{contaminated_parts // divisor}:{clean_parts // divisor}"

    return {
        "needed": True,
        "rejected": False,
        "worst_toxin": worst_toxin,
        "contaminated_feed_percent": round(F, 1),
        "clean_feed_percent": round(100 - F, 1),
        "ratio_text_contaminated_to_clean": ratio_text,
        "clean_feed_level_used": L,
    }


def compute_financial_loss(fcr_delta, baseline_fcr, quantity_tons, feed_price_egp_per_kg) -> dict:
    """
    Card 7 — Financial Loss Estimator.
    يقدّر قيمة العلف "المهدر" (المستهلك دون أن يقابله وزن مكتسب) الناتج عن تدهور FCR:
        الطن المهدر = إجمالي كمية الشحنة (طن) × (ΔFCR ÷ FCR الأساسي)
        الخسارة (ج.م) = الطن المهدر × 1000 (كجم/طن) × سعر الكيلوجرام الواحد
    """
    baseline_fcr = _safe_float(baseline_fcr)
    quantity_tons = _safe_float(quantity_tons)
    feed_price_egp_per_kg = _safe_float(feed_price_egp_per_kg)

    if fcr_delta is None or not quantity_tons or not feed_price_egp_per_kg or not baseline_fcr:
        return {"loss_egp": None, "wasted_feed_tons": None, "wasted_fraction_pct": None}

    wasted_fraction = fcr_delta / baseline_fcr
    wasted_tons = quantity_tons * wasted_fraction
    loss_egp = wasted_tons * 1000 * feed_price_egp_per_kg

    return {
        "wasted_feed_tons": round(wasted_tons, 2),
        "loss_egp": round(loss_egp, 0),
        "wasted_fraction_pct": round(wasted_fraction * 100, 1),
    }


def compute_supplier_score(mri_score, storage_risk_factor) -> dict:
    """Card 8 — Supplier Scorecard: درجة جودة الشحنة الحالية للمورد (0-100) + تصنيف حرفي A-F."""
    if mri_score is None:
        return {"score": None, "grade": "—"}
    score = max(0.0, 100 - mri_score - (storage_risk_factor * 15))
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"
    return {"score": round(score, 1), "grade": grade}


def compute_final_decision(risk_ratios: dict, binder_already_added: bool, age_gate: dict, species_key: str) -> dict:
    """
    منطق القرار الإداري الحاسم (Deterministic Decision Tree) — السلطة الوحيدة المعتمدة
    لتحديد القرار النهائي (code). النموذج اللغوي لا يشارك في هذا القرار إطلاقًا —
    لا يُطلب منه اقتراح قرار ولا تُقرأ منه أي إشارة له.

    ⚠️ عتبة الرفض لكل سم × كل قطاع على حدة (get_reject_multiple() من constants.py) بدل
    عتبة عامة واحدة لكل السموم عبر كل الأنواع — الأفلاتوكسين (IARC Group 1، أضيق هامش
    أمان) يُرفض افتراضيًا عند تجاوز 2.5× حده الخاص، لكن قطاعًا بعينه (مثل الاستزراع
    السمكي) قد يحمل مضاعفًا أضيق صراحةً (1.5× للأفلاتوكسين، 2.0× للأوكراتوكسين) بحسب
    القيم الفعلية المخزّنة في SPECIES_REGULATORY_LIMITS لهذا القطاع تحديدًا — راجع
    get_reject_multiple() في constants.py لتفاصيل آلية الحساب.

    ⚠️ قاعدة العمر/المرحلة القاطعة (age_gate، من constants.is_blending_allowed) تتخطى
    (Override) نتيجة الحساب: لو الخلط ممنوع عمريًا (بادي/أقل من UNIVERSAL_MIN_BLENDING_AGE_DAYS)،
    فأي تجاوز فوق الحد التنظيمي => REJECT مباشرة (لا يوجد مسار BLEND_REQUIRED متاح أصلًا
    لهذه الدفعة، فلا معنى لاقتراحه).
    """
    available = {k: v for k, v in risk_ratios.items() if v is not None}
    if not available:
        return {
            "code": "REJECT",
            "reason_ar": "تعذّر اتخاذ قرار موثوق لعدم كفاية بيانات التحليل المعملي — "
                         "يوصى برفض الاستخدام حتى استكمال الفحص المعملي الكامل.",
        }

    breached_reject = [
        toxin_key for toxin_key, ratio in available.items()
        if ratio > get_reject_multiple(species_key, toxin_key)
    ]
    if breached_reject:
        worst_toxin = max(breached_reject, key=lambda k: available[k])
        toxin_label = TOXIN_METADATA.get(worst_toxin, {}).get("label_ar", worst_toxin)
        multiple = get_reject_multiple(species_key, worst_toxin)
        return {
            "code": "REJECT",
            "reason_ar": f"تلوث {toxin_label} يتجاوز {multiple:.1f}× الحد التنظيمي الخاص به "
                         f"لهذا القطاع — الخلط يصبح غير اقتصادي وغير آمن. يُوصى بالإعدام أو "
                         "الإرجاع للمورد فورًا.",
        }

    max_ratio = max(available.values())

    if max_ratio > 1.0:
        if not age_gate.get("allowed", True):
            return {
                "code": "REJECT",
                "reason_ar": "تجاوز الحد التنظيمي، لكن الخلط غير مسموح لهذه الدفعة: "
                             f"{age_gate.get('reason_ar', '')}",
            }
        return {
            "code": "BLEND_REQUIRED",
            "reason_ar": "تجاوز الحد التنظيمي ضمن نطاق قابل للمعالجة عبر الخلط الدقيق "
                         "(راجع كارت 'دليل الخلط' لمعرفة النسبة الآمنة).",
        }
    if max_ratio >= BINDER_TRIGGER_RATIO and not binder_already_added:
        return {
            "code": "BINDER_REQUIRED",
            "reason_ar": "التركيز يقترب من الحد التنظيمي دون تجاوزه — يوصى بإضافة مضاد "
                         "سموم وقائي (Mycotoxin Binder) قبل الاستخدام كإجراء احترازي.",
        }
    return {"code": "APPROVE", "reason_ar": "جميع السموم المفحوصة ضمن الحدود التنظيمية الآمنة."}


# ==============================================================================
# 6B) ربط القطيع/العنبر بالفئة التنظيمية — Flock-to-Species Resolution
# ==============================================================================
# ⚠️ القطيع/العنبر تسمية تشغيلية (كما يعرفها فريق المزرعة)، وليس فئة تنظيمية بديلة.
# كل دالة هنا تُترجم التسمية التشغيلية دائمًا إلى أحد المفاتيح الخمسة المعتمدة في
# constants.SPECIES_REGULATORY_LIMITS قبل أن تصل لمحرك الحسابات — أي قطيع (افتراضي أو
# مخصص) لا يملك مفتاحًا صالحًا من هذه الخمسة لا يمكنه إطلاقًا الوصول إلى build_full_analysis.
ADD_NEW_FLOCK_OPTION = "إضافة قطيع جديد"

# نفس تسميات SPECIES_LABELS_AR حرفيًا (لا قائمة قطاعات موازية) — القائمة المنسدلة
# الفرعية عند إضافة قطيع مخصص تُبنى من هذا القاموس مباشرة فيستحيل بنيويًا اختيار فئة
# سادسة، حتى لو أُضيف قطاع جديد لـ FLOCK_TO_SPECIES_MAP لاحقًا دون تحديث هذه القائمة.
def get_custom_flock_species_options() -> dict:
    """{تسمية عربية معروضة: مفتاح قطاع معتمد} — مصدرها الوحيد SPECIES_LABELS_AR."""
    return dict(SPECIES_LABELS_AR)


def resolve_flock_species_key(flock_name: str, custom_flocks: dict = None) -> str | None:
    """
    يحل مفتاح القطاع التنظيمي لاسم قطيع معيَّن:
      ١) يبحث أولًا في FLOCK_TO_SPECIES_MAP (المرجع الحتمي الثابت في constants.py).
      ٢) وإلا يبحث في custom_flocks (session_state["custom_flocks"] — قطعان أضافها
         المستخدم خلال الجلسة، بنفس الشكل: {اسم: species_key معتمد}).
      ٣) وإلا يُعيد None — لا قطاع يُخمَّن أبدًا.

    ⚠️ حتى لو كان custom_flocks يحوي مفتاحًا غير معتمد (خطأ في الاستدعاء، لا في الواجهة
    نفسها التي تمنعه أصلًا — راجع add_custom_flock)، هذه الدالة لا تتحقق من صحته هنا؛
    التحقق مسؤولية add_custom_flock() عند الإضافة، فلا تُضاف قيمة غير صالحة للقاموس أصلًا.
    """
    if not flock_name:
        return None
    if flock_name in FLOCK_TO_SPECIES_MAP:
        return FLOCK_TO_SPECIES_MAP[flock_name]
    if custom_flocks and flock_name in custom_flocks:
        return custom_flocks[flock_name]
    return None


def add_custom_flock(custom_flocks: dict, flock_name: str, species_key: str) -> dict:
    """
    يضيف قطيعًا مخصصًا إلى custom_flocks (يعدّله في مكانه ويُعيده أيضًا للتسلسل).

    ⚠️ حارس الأمان الجوهري لهذا البند: species_key **يجب** أن يكون أحد المفاتيح الخمسة
    الموجودة فعليًا في SPECIES_REGULATORY_LIMITS — نفس القيد المطبَّق على FLOCK_TO_SPECIES_MAP
    نفسها. أي مفتاح آخر (بما فيه فئات مثل "swine"/"equine" غير المعتمدة، أو خطأ إملائي) يُرفَض
    برفع ValueError صريح بدل حفظه بصمت — قطيع بفئة تنظيمية غير موجودة يعني حدودًا تنظيمية
    غير موجودة، فيفشل build_full_analysis لاحقًا بطريقة أقل وضوحًا لو سُمح بالمرور هنا.
    اسم فارغ يُرفَض لنفس السبب — لا قطيع بلا اسم يُعرَض في القائمة المنسدلة.
    """
    flock_name = (flock_name or "").strip()
    if not flock_name:
        raise ValueError("اسم القطيع المخصص لا يمكن أن يكون فارغًا.")
    if species_key not in SPECIES_REGULATORY_LIMITS:
        raise ValueError(
            f"القطاع التنظيمي '{species_key}' غير معتمد — يجب أن يكون أحد المفاتيح الخمسة "
            f"في constants.SPECIES_REGULATORY_LIMITS: {sorted(SPECIES_REGULATORY_LIMITS)}"
        )
    custom_flocks[flock_name] = species_key
    return custom_flocks


# ==============================================================================
# 7) المنسّق الرئيسي لمحرك السموم الفطرية — build_full_analysis()
# ==============================================================================
def build_full_analysis(
    parsed: dict, baseline_fcr: float, feed_price: float, forced_species_key: str, manual_flock_age_days=None,
    clean_feed_toxin_levels: dict = None,
) -> dict:
    """
    المنسّق الرئيسي (Orchestrator): يجمّع كل الحسابات في هيكل واحد جاهز للعرض.

    ⚠️ قرار معماري (١): `forced_species_key` (اختيار المستخدم اليدوي الإجباري من الواجهة) هو
    المصدر الوحيد المعتمد لتحديد أي صف من constants.SPECIES_REGULATORY_LIMITS تُستخدم في كل
    الحسابات. v3.0.0: لا مصدر نصي بديل (لا LLM) يمكن أن يتعارض مع هذا الاختيار أصلًا —
    target_species في normalized_inputs.parameters لا يُملأ أبدًا في المسار المنظَّم الوحيد
    المتبقي، فأُزيل التدقيق التقاطعي القديم (species_mismatch/llm_parsed_species_key) بالكامل
    بدل إبقائه كودًا ميتًا دائم القيمة False.

    ⚠️ قرار معماري (٢): `final_decision` يُحسب هنا أولًا (مباشرة بعد risk_ratios) ويُمرَّر
    صراحةً إلى compute_mri() و compute_blending_ratio() — بدل أن يحسب كل كارت شرط "رفض"
    خاص به بمعزل عن غيره. هذا يضمن مصدر حقيقة واحد لا يمكن لكارتين أن يتناقضا بصريًا حول
    نفس الشحنة (مثال: MRI منخفض بجانب قرار REJECT، أو نسبة خلط مقترحة لشحنة مرفوضة بالكامل).

    ⚠️ قرار معماري (٣): عمر القطيع (flock_age_days، إن أُدخل يدويًا) يُمرَّر إلى
    constants.is_blending_allowed() لتحديد age_gate **قبل** حساب القرار النهائي — قاعدة
    حظر الخلط تحت UNIVERSAL_MIN_BLENDING_AGE_DAYS أو لمرحلة allow_blending=False (مثل
    البادي) هي قاعدة قاطعة تتخطى أي نتيجة حسابية أخرى.

    ⚠️ قرار معماري (٤): `clean_feed_toxin_levels` (اختياري، من "إعدادات الخلط المتقدمة" في
    الواجهة) يُمرَّر إلى compute_blending_ratio() ليحل محل افتراض L=0 الأمثل (Best-case) عند
    توفر نتيجة معملية فعلية للعلف النظيف المقترح للخلط — بدون تعديل أي حساب آخر في الـ pipeline.
    """
    normalized_inputs = parsed.get("normalized_inputs") or {}
    lab_results = normalized_inputs.get("lab_results") or {}
    storage = normalized_inputs.get("storage") or {}
    parameters = normalized_inputs.get("parameters") or {}
    shipment_meta = parsed.get("shipment_meta") or {}
    parsing_audit = parsed.get("parsing_audit") or {}

    species_key = forced_species_key

    temperature_c = _safe_float(storage.get("temperature_celsius"))
    moisture_pct = _safe_float(storage.get("moisture_percent"))
    storage_days = _safe_float(storage.get("storage_days"))
    quantity_tons = _safe_float(shipment_meta.get("quantity_tons"))
    binder_added = bool(parameters.get("toxin_binder_added"))
    flock_age_days_raw = _safe_float(parameters.get("flock_age_days"))
    llm_parsed_flock_age_days = int(flock_age_days_raw) if flock_age_days_raw is not None else None
    flock_age_days = manual_flock_age_days if manual_flock_age_days is not None else llm_parsed_flock_age_days
    flock_age_is_manual_override = manual_flock_age_days is not None

    risk_ratios = compute_risk_ratios(lab_results, species_key)
    age_gate = is_blending_allowed(species_key, age_days=flock_age_days)
    stage_key = get_stage_for_age(species_key, flock_age_days)
    final_decision = compute_final_decision(risk_ratios, binder_added, age_gate, species_key)  # ← مصدر الحقيقة الوحيد
    mri = compute_mri(risk_ratios, temperature_c, moisture_pct, final_decision)
    storage_risk = compute_storage_risk(temperature_c, moisture_pct)
    storage_lifespan = compute_safe_storage_lifespan(temperature_c, moisture_pct, storage_days)
    fcr = compute_fcr_deterioration(mri["score"], species_key)
    blending = compute_blending_ratio(risk_ratios, lab_results, species_key, final_decision, clean_feed_toxin_levels)
    financial = compute_financial_loss(fcr["delta_fcr"], baseline_fcr, quantity_tons, feed_price)
    supplier = compute_supplier_score(mri["score"], storage_risk["combined_risk_factor"])

    return {
        "shipment_meta": shipment_meta,
        "species_key": species_key,
        "lab_results": lab_results,
        "storage_inputs": {"temperature_c": temperature_c, "moisture_pct": moisture_pct, "storage_days": storage_days},
        "flock_age_days": flock_age_days,
        "flock_age_is_manual_override": flock_age_is_manual_override,
        "stage_key": stage_key,
        "age_gate": age_gate,
        "parsing_audit": parsing_audit,
        "risk_ratios": risk_ratios,
        "mri": mri,
        "storage_risk": storage_risk,
        "storage_lifespan": storage_lifespan,
        "fcr": fcr,
        "blending": blending,
        "financial": financial,
        "supplier_score": supplier,
        "final_decision": final_decision,
    }


DECISION_STYLE = {
    "APPROVE": ("اعتماد", "success"),
    "BLEND_REQUIRED": ("خلط مطلوب", "warning"),
    "BINDER_REQUIRED": ("إضافة مضاد سموم", "warning"),
    "REJECT": ("رفض", "error"),
}


def _shipment_fingerprint_inputs(key_prefix: str) -> dict:
    """
    البصمة الرسمية للشحنة (نوع الخامة/العلف، اسم المورد/الشركة، رقم التشغيلة/السيارة،
    تاريخ الشحنة) — ثلاث حقول نصية + حقل تاريخ، كلها اختيارية بالكامل (None إن تُركت
    فارغة)، لا تؤثر في أي حساب في أي محرك. تُستخدَم فقط في رأس لوحة النتائج وفي شهادة
    الـ PDF (راجع pdf_report.py) — "شهادة ميلاد" رسمية تُعرِّف الشحنة بوضوح عند الأرشفة
    أو المشاركة مع المورد، حسب طلب الميزة صراحةً.
    """
    st.markdown("##### البصمة الرسمية للشحنة (اختياري)")
    col1, col2 = st.columns(2)
    with col1:
        feed_type = st.text_input(
            "نوع الخامة / العلف", key=f"{key_prefix}_feed_type",
            placeholder="مثال: ذرة صفراء، كسب صويا، علف مركّز جاهز",
        )
        batch_number = st.text_input(
            "رقم التشغيلة / السيارة", key=f"{key_prefix}_batch_number",
            placeholder="مثال: TRK-2026-0091",
        )
    with col2:
        supplier_name = st.text_input(
            "اسم المورد / الشركة", key=f"{key_prefix}_supplier_name",
            placeholder="مثال: شركة دلتا للأعلاف",
        )
        shipment_date = st.date_input(
            "تاريخ الشحنة", key=f"{key_prefix}_shipment_date", value=None,
        )
    return {
        "feed_type": feed_type.strip() or None,
        "supplier_name": supplier_name.strip() or None,
        "batch_number": batch_number.strip() or None,
        "shipment_date": shipment_date.isoformat() if shipment_date else None,
    }


def render_dashboard(a: dict, supplier_history: dict, fingerprint: dict = None):
    st.divider()
    meta = a["shipment_meta"]
    fingerprint = fingerprint or {}
    supplier_display = fingerprint.get("supplier_name") or meta.get("supplier_name") or "مورد غير محدد"
    feed_type_display = fingerprint.get("feed_type") or meta.get("feed_type") or "نوع علف غير محدد"
    st.subheader(
        f"{supplier_display} — {feed_type_display} "
        f"({SPECIES_LABELS_AR.get(a['species_key'], a['species_key'])})"
    )
    if fingerprint.get("batch_number") or fingerprint.get("shipment_date"):
        bits = []
        if fingerprint.get("batch_number"):
            bits.append(f"رقم التشغيلة/السيارة: {fingerprint['batch_number']}")
        if fingerprint.get("shipment_date"):
            bits.append(f"التاريخ: {fingerprint['shipment_date']}")
        st.caption(" | ".join(bits))

    # ⚠️ يظهر فقط عند اختيار قطيع/عنبر فعلي لهذه الشحنة (flock_name موجود في shipment_meta) —
    # القطاع التنظيمي المعروض هنا هو species_key_used الفعلي (نفسه a['species_key']، لأن
    # effective_species_key هو ما مُرِّر لـ build_full_analysis أصلًا)، وليس القطاع العام وحده.
    if meta.get("flock_name"):
        species_key_used = meta.get("species_key_used") or a["species_key"]
        st.caption(
            f"القطيع: {meta['flock_name']} | "
            f"القطاع التنظيمي: {SPECIES_LABELS_AR.get(species_key_used, species_key_used)}"
        )

    if a["parsing_audit"].get("missing_critical_fields"):
        st.warning(
            "حقول ناقصة رصدها التحليل: "
            + "، ".join(a["parsing_audit"]["missing_critical_fields"])
        )

    if a.get("stage_key"):
        stage_row = FEED_STAGES_CONFIG.get(a["species_key"], {}).get("stages", {}).get(a["stage_key"], {})
        age_source = "إدخال يدوي" if a.get("flock_age_is_manual_override") else "غير محدَّد"
        st.caption(
            f"المرحلة العمرية المكتشفة: {stage_row.get('label_ar', a['stage_key'])} "
            f"(عمر القطيع: {a.get('flock_age_days')} يوم — {age_source})"
        )
    if not a["age_gate"].get("allowed", True):
        st.warning(f"قاعدة عمرية قاطعة: {a['age_gate'].get('reason_ar', '')}")

    row1 = st.columns(4)
    row2 = st.columns(4)

    with row1[0]:
        score = a["mri"]["score"]
        st.metric("مؤشر الخطورة MRI", f"{score} / 100" if score is not None else "—")

    with row1[1]:
        delta = a["fcr"]["delta_fcr"]
        st.metric(
            "تدهور FCR المتوقع",
            f"+{delta}" if delta is not None else "—",
            delta=f"+{delta} نقطة" if delta is not None else None,
            delta_color="inverse",
        )

    with row1[2]:
        code = a["final_decision"]["code"]
        label, _ = DECISION_STYLE.get(code, (code, "info"))
        st.metric("القرار المعتمد", label)

    with row1[3]:
        st.metric("خطورة التخزين", a["storage_risk"]["level"])

    with row2[0]:
        remaining = a["storage_lifespan"]["days_remaining"]
        st.metric(
            "أيام التخزين الآمنة المتبقية",
            f"{remaining} يوم",
            delta="منتهية" if a["storage_lifespan"]["is_overdue"] else None,
            delta_color="inverse",
        )

    with row2[1]:
        if a["blending"]["needed"]:
            st.metric("نسبة الخلط (ملوّث : نظيف)", a["blending"]["ratio_text_contaminated_to_clean"])
        elif a["blending"].get("rejected"):
            st.metric("نسبة الخلط (ملوّث : نظيف)", "0:1")
        else:
            st.metric("نسبة الخلط", "لا حاجة")

    with row2[2]:
        loss = a["financial"]["loss_egp"]
        st.metric("الخسارة المالية المقدَّرة", f"{loss:,.0f} ج.م" if loss is not None else "—")

    with row2[3]:
        sup = a["supplier_score"]
        st.metric("تقييم المورد", f"{sup['grade']}  ({sup['score']})" if sup["score"] is not None else "—")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("تفاصيل مؤشر الخطورة MRI (لكل سم)", expanded=False):
            for toxin_key, ratio in a["risk_ratios"].items():
                label = TOXIN_METADATA.get(toxin_key, {}).get("label_ar", toxin_key)
                if ratio is None:
                    st.write(f"- {label}: بيانات غير متوفرة")
                else:
                    status = "تجاوز" if ratio > 1.0 else "ضمن الحد"
                    st.write(f"- {label}: نسبة {ratio}× من الحد المسموح ({status})")
            st.caption(f"جزاء ظروف التخزين المضاف إلى MRI: {a['mri'].get('storage_penalty', 0)} نقطة من 10")
            if a["mri"].get("synergy_multiplier", 1.0) > 1.0:
                pairs_txt = "، ".join(
                    f"{TOXIN_METADATA.get(x, {}).get('label_ar', x)} + {TOXIN_METADATA.get(y, {}).get('label_ar', y)}"
                    for x, y in a["mri"].get("synergy_pairs_triggered", [])
                )
                st.caption(f"مصفوفة التآزر الفطري فعّالة (×{a['mri']['synergy_multiplier']}): {pairs_txt}")
            if a["mri"].get("floor_applied"):
                st.caption(f"طُبِّق حد أدنى إجباري = {MRI_HARD_FLOOR:.0f}/100 لأن القرار المعتمد REJECT.")

    with col_b:
        with st.expander("تفاصيل الخلط الدقيق (Precision Blending)", expanded=False):
            if a["blending"]["needed"]:
                worst_label = TOXIN_METADATA.get(a["blending"]["worst_toxin"], {}).get("label_ar", a["blending"]["worst_toxin"])
                st.write(f"أسوأ سم مسجَّل: **{worst_label}**")
                st.write(
                    f"النسبة الآمنة: **{a['blending']['contaminated_feed_percent']}%** علف ملوّث "
                    f"+ **{a['blending']['clean_feed_percent']}%** علف نظيف"
                )
                clean_level_used = a["blending"].get("clean_feed_level_used", 0.0)
                if clean_level_used > 0:
                    unit = TOXIN_METADATA.get(a["blending"]["worst_toxin"], {}).get("unit", "")
                    st.caption(f"تركيز العلف النظيف المستخدَم في الحساب: {clean_level_used} {unit}")
                else:
                    st.caption("الحساب يفترض أن العلف النظيف خالٍ تمامًا من السموم.")
            else:
                st.write(a["blending"]["note"])

    st.subheader("تبرير القرار الحتمي")
    decision_label, decision_style = DECISION_STYLE.get(a["final_decision"]["code"], ("—", "info"))
    getattr(st, decision_style)(f"**القرار المعتمد: {decision_label}**\n\n{a['final_decision']['reason_ar']}")

    history_series = supplier_history.get(supplier_display, [])
    if len(history_series) > 1:
        with st.expander(f"سجل تقييم المورد '{supplier_display}' خلال هذه الجلسة"):
            st.line_chart(history_series)

    with st.expander("عرض حزمة الـ JSON الكاملة (Raw Parsed Data) — لأغراض التدقيق"):
        st.json(
            {
                "shipment_meta": a["shipment_meta"],
                "normalized_lab_results": a["lab_results"],
                "storage_inputs": a["storage_inputs"],
                "parsing_audit": a["parsing_audit"],
                "risk_ratios": a["risk_ratios"],
            }
        )


def render_proximate_dashboard(p: dict):
    """
    يعرض لوحة نتائج محرك البروكسيمات (proximate_engine.build_full_proximate_analysis).
    ⚠️ p["error"] غير None => القطاع/المرحلة غير مغطاة (مثال: poultry_layer) — تُعرض
    رسالة واضحة بلا أي محاولة عرض بيانات جزئية أو مُخمَّنة.
    """
    if p.get("error"):
        st.error(p["error"])
        return

    st.divider()
    st.subheader(f"التركيب الغذائي — {p['species_label_ar']} ({p['stage_label_ar']})")

    traffic = p["kpi_7_traffic_light"]
    banner_style = {"GREEN": "success", "YELLOW": "warning", "RED": "error"}.get(traffic["code"], "info")
    getattr(st, banner_style)(f"**القرار: {_strip_emoji(traffic['label_ar'])}**")
    if traffic["reasons"]:
        for reason in traffic["reasons"]:
            st.caption(f"- {reason}")

    row1 = st.columns(4)
    row2 = st.columns(3)

    with row1[0]:
        deficit = p["kpi_1_protein_deficit"]
        st.metric(
            "عجز البروتين",
            f"{deficit['deficit_points']} نقطة" if deficit.get("deficit_points") else "لا عجز",
            delta=f"خصم {deficit['deduction_egp']:,.0f} ج.م" if deficit.get("deduction_egp") else None,
            delta_color="inverse",
        )
    with row1[1]:
        fiber = p["kpi_2_fiber_adulteration"]
        st.metric(
            "غش الألياف/القشور",
            f"+{fiber['excess_points']} نقطة" if fiber.get("excess_points") else "ضمن الحد",
        )
    with row1[2]:
        rancidity = p["kpi_3_rancidity_risk"]
        st.metric("خطر التزنخ والأكسدة", _strip_emoji(rancidity["level"]))
    with row1[3]:
        ash = p["kpi_4_ash_purity"]
        st.metric(
            "نقاء الشحنة (الرماد)",
            "يلزم غربلة" if ash.get("needs_sieving") else "نقي",
        )

    with row2[0]:
        st.metric("الكربوهيدرات الذائبة (NFE)", f"{p['nfe_pct']}%" if p["nfe_pct"] is not None else "—")
    with row2[1]:
        perf = p["kpi_6_performance_index"]
        st.metric("مؤشر الأداء المتوقع", f"{perf['score_pct']}%" if perf.get("score_pct") is not None else "—")
    with row2[2]:
        st.metric("الإشارة الثلاثية", _strip_emoji(traffic["label_ar"]))

    with st.expander("تفاصيل القيم المقاسة مقابل المعايير المرجعية", expanded=False):
        inputs = p["inputs"]
        standard = p["standard_used"]
        for param_key in prox.PROXIMATE_PARAMETER_ORDER:
            label = prox.PROXIMATE_PARAMETER_LABELS_AR.get(param_key, param_key)
            value = inputs.get(param_key)
            std_row = standard.get(param_key, {}) if param_key != "moisture_pct" else {}
            bounds = []
            if std_row.get("min") is not None:
                bounds.append(f"≥ {std_row['min']}%")
            if std_row.get("max") is not None:
                bounds.append(f"≤ {std_row['max']}%")
            bounds_text = " / ".join(bounds) if bounds else (
                f"مرجعي: {std_row.get('reference')}%" if std_row.get("reference") is not None else "لا حد موثَّق"
            )
            st.write(f"- {label}: **{value}%**" if value is not None else f"- {label}: غير مُدخَل" ,
                     f"({bounds_text})" if param_key != "moisture_pct" else "")
        if inputs.get("protein_source") == "derived_from_nitrogen":
            st.caption(f"ℹ️ البروتين الخام حُسب من نسبة النيتروجين المُدخَلة (×{prox.N_TO_PROTEIN_FACTOR}).")
        elif inputs.get("protein_source") == "direct_conflicts_with_nitrogen_derived":
            st.warning(
                f"أُدخلت كل من نسبة البروتين الخام والنيتروجين، وقيمتاهما متعارضتان "
                f"(البروتين المباشر: {inputs['crude_protein_pct']}% مقابل المُشتَق من النيتروجين: "
                f"{inputs['nitrogen_derived_value']}%). اعتُمد البروتين المباشر المُدخَل — راجع "
                "صحة القيمتين."
            )


# ==============================================================================
# 9) محدِّد القطاع/القطيع/العمر المشترك — Shared Species/Flock/Age Selector
# ==============================================================================
SPECIES_PLACEHOLDER = "— اختر القطاع المستهدف —"
FLOCK_PLACEHOLDER = "— الاعتماد على القطاع الأساسي فقط —"


def render_species_flock_age_selector(key_prefix: str) -> dict:
    """
    عنصر واجهة مشترك تستدعيه كل شاشة من الشاشات الثلاث بشكل مستقل (كل شاشة تملك
    شحنتها الخاصة، فلا تتشارك اختيار القطاع/القطيع فيما بينها) — كل مفاتيح
    session_state للـ widgets هنا مُسبوقة بـ key_prefix (مثال: "tab1_species_select")
    لمنع أي تصادم بين الشاشات الثلاث نفسها.

    يُعيد dict: {"selected_species_key", "manual_flock_age_days", "resolved_flock_name",
                 "effective_species_key"} — effective_species_key هو ما يجب تمريره فعليًا
    لأي محرك حسابي (القطيع يتخطى القطاع العام عند اختياره، تمامًا كالسلوك القديم).
    """
    species_display_options = [SPECIES_PLACEHOLDER] + [SPECIES_LABELS_AR[k] for k in SPECIES_REGULATORY_LIMITS]
    species_label_to_key = {v: k for k, v in SPECIES_LABELS_AR.items()}

    col_species, col_age = st.columns([2, 1])
    with col_species:
        selected_species_label = st.selectbox(
            "القطاع المستهدف لهذه الشحنة (إجباري)",
            options=species_display_options, index=0, key=f"{key_prefix}_species_select",
        )
    selected_species_key = species_label_to_key.get(selected_species_label)

    with col_age:
        manual_flock_age_input = st.number_input(
            "عمر القطيع/الدفعة (يوم) — اختياري", min_value=0, value=0, step=1,
            key=f"{key_prefix}_flock_age_input",
        )
    manual_flock_age_days = int(manual_flock_age_input) if manual_flock_age_input > 0 else None

    st.session_state.setdefault("custom_flocks", {})
    flock_display_options = (
        [FLOCK_PLACEHOLDER] + list(FLOCK_TO_SPECIES_MAP) + list(st.session_state["custom_flocks"]) + [ADD_NEW_FLOCK_OPTION]
    )
    selected_flock_name = st.selectbox(
        "القطيع / العنبر (اختياري)",
        options=flock_display_options, index=0, key=f"{key_prefix}_flock_selector",
    )

    saved_name_key = f"{key_prefix}_new_flock_saved_name"
    if st.session_state.get(saved_name_key):
        st.success(f"تم حفظ القطيع '{st.session_state[saved_name_key]}' لهذه الجلسة.")
        st.session_state[saved_name_key] = None

    resolved_flock_name = None
    if selected_flock_name == ADD_NEW_FLOCK_OPTION:
        col_new_name, col_new_species = st.columns([2, 1])
        with col_new_name:
            new_flock_name_input = st.text_input(
                "اسم القطيع الجديد", key=f"{key_prefix}_new_flock_name_input",
            )
        species_display_to_key = get_custom_flock_species_options()
        with col_new_species:
            new_flock_species_label = st.selectbox(
                "القطاع التنظيمي المقابل (إجباري)",
                options=[SPECIES_PLACEHOLDER] + list(species_display_to_key.values()),
                index=0, key=f"{key_prefix}_new_flock_species_select",
            )
        new_flock_species_key = {v: k for k, v in species_display_to_key.items()}.get(new_flock_species_label)

        def _save_new_flock_callback(flock_name, species_key, flock_selector_key, error_key, saved_key):
            flock_name = (flock_name or "").strip()
            if not flock_name:
                st.session_state[error_key] = "الرجاء إدخال اسم للقطيع الجديد."
                return
            if not species_key:
                st.session_state[error_key] = "الرجاء اختيار القطاع التنظيمي المقابل للقطيع الجديد."
                return
            try:
                add_custom_flock(st.session_state["custom_flocks"], flock_name, species_key)
                st.session_state[flock_selector_key] = flock_name
                st.session_state[error_key] = None
                st.session_state[saved_key] = flock_name
            except ValueError as flock_error:
                st.session_state[error_key] = str(flock_error)

        error_key = f"{key_prefix}_new_flock_error"
        st.button(
            "حفظ القطيع الجديد", key=f"{key_prefix}_save_new_flock_button",
            on_click=_save_new_flock_callback,
            args=(new_flock_name_input, new_flock_species_key, f"{key_prefix}_flock_selector",
                  error_key, saved_name_key),
        )
        if st.session_state.get(error_key):
            st.warning(st.session_state[error_key])
            st.session_state[error_key] = None
    elif selected_flock_name != FLOCK_PLACEHOLDER:
        resolved_flock_name = selected_flock_name

    flock_species_key = resolve_flock_species_key(resolved_flock_name, st.session_state["custom_flocks"])
    effective_species_key = flock_species_key or selected_species_key

    return {
        "selected_species_key": selected_species_key,
        "manual_flock_age_days": manual_flock_age_days,
        "resolved_flock_name": resolved_flock_name,
        "effective_species_key": effective_species_key,
    }


def render_clean_feed_blending_expander(key_prefix: str) -> dict:
    """نفس إعدادات الخلط المتقدمة القديمة — مفاتيح مُسبوقة بـ key_prefix لتفادي أي تصادم
    بين الشاشات الثلاث (كل شاشة قد تحلل شحنة مختلفة بافتراضات خلط مختلفة)."""
    with st.expander("إعدادات الخلط المتقدمة (اختياري)"):
        clean_feed_toxin_levels = {}
        clean_cols = st.columns(len(TOXIN_KEYS))
        for col, toxin_key in zip(clean_cols, TOXIN_KEYS):
            with col:
                meta = TOXIN_METADATA[toxin_key]
                entered = st.number_input(
                    f"{meta['label_ar']} ({meta['unit']})", min_value=0.0, value=0.0, step=0.1,
                    format="%.2f", key=f"{key_prefix}_clean_feed_level_{toxin_key}",
                )
                if entered > 0:
                    clean_feed_toxin_levels[toxin_key] = entered
    return clean_feed_toxin_levels


def render_toxin_lab_inputs(key_prefix: str) -> dict:
    """حقول نتائج المعمل الخمسة (نفس تبويب 'إدخال يدوي منظم' القديم حرفيًا) — تُعاد
    كـ dict جاهز للتمرير إلى build_structured_parsed_json()."""
    st.markdown("##### نتائج المعمل (Toxin Lab Results)")
    col_afla, col_ochra = st.columns(2)
    with col_afla:
        aflatoxin = st.number_input("أفلاتوكسين (ppb)", min_value=0.0, step=0.1, value=None,
                                     key=f"{key_prefix}_aflatoxin_ppb")
    with col_ochra:
        ochratoxin = st.number_input("أوكراتوكسين (ppb)", min_value=0.0, step=0.1, value=None,
                                      key=f"{key_prefix}_ochratoxin_ppb")
    col_don, col_zea = st.columns(2)
    with col_don:
        don = st.number_input("دون (ppm)", min_value=0.0, step=0.1, value=None, key=f"{key_prefix}_don_ppm")
    with col_zea:
        zea = st.number_input("زيارالينون (ppm)", min_value=0.0, step=0.01, value=None,
                               key=f"{key_prefix}_zearalenone_ppm")
    fumonisin = st.number_input("فيومونيسين (ppm)", min_value=0.0, step=0.1, value=None,
                                 key=f"{key_prefix}_fumonisin_ppm")
    return {
        "aflatoxin_ppb": aflatoxin, "ochratoxin_ppb": ochratoxin, "don_ppm": don,
        "zearalenone_ppm": zea, "fumonisin_ppm": fumonisin,
    }


def render_storage_and_quantity_inputs(key_prefix: str) -> dict:
    """حقول ظروف التخزين الثلاثة + الكمية بالطن — نفس حقول الإدخال المنظَّم القديمة حرفيًا."""
    st.markdown("##### ظروف التخزين (Storage Conditions)")
    col_temp, col_moist, col_days = st.columns(3)
    with col_temp:
        temperature = st.number_input("حرارة المخزن (°C)", min_value=-20.0, max_value=60.0, value=None,
                                       key=f"{key_prefix}_temperature_celsius")
    with col_moist:
        moisture = st.number_input("الرطوبة (%)", min_value=0.0, max_value=100.0, value=None,
                                    key=f"{key_prefix}_moisture_percent")
    with col_days:
        storage_days = st.number_input("أيام التخزين", min_value=0, value=None, key=f"{key_prefix}_storage_days")

    st.markdown("##### بيانات الشحنة (Shipment Info)")
    quantity_tons = st.number_input("الكمية (طن)", min_value=0.0, value=None, key=f"{key_prefix}_quantity_tons")

    return {
        "storage": {
            "temperature_celsius": temperature, "moisture_percent": moisture,
            "storage_days": int(storage_days) if storage_days is not None else None,
        },
        "quantity_tons": quantity_tons,
    }


def render_proximate_inputs(key_prefix: str) -> dict:
    """حقول البروكسيمات الخمسة: رطوبة + (بروتين خام أو نيتروجين) + دهن + ألياف + رماد."""
    st.markdown("##### التركيب الغذائي (Proximate Composition)")
    moisture = st.number_input("رطوبة العينة/الخامة (%)", min_value=0.0, max_value=100.0, step=0.1,
                                value=None, key=f"{key_prefix}_prox_moisture_pct")

    protein_mode = st.radio(
        "إدخال البروتين عبر:", options=["البروتين الخام مباشرة", "نسبة النيتروجين (يُحسَب تلقائيًا ×6.25)"],
        key=f"{key_prefix}_protein_mode", horizontal=True,
    )
    crude_protein_pct = nitrogen_pct = None
    if protein_mode == "البروتين الخام مباشرة":
        crude_protein_pct = st.number_input("البروتين الخام (Crude Protein %)", min_value=0.0, max_value=100.0,
                                             step=0.1, value=None, key=f"{key_prefix}_prox_cp_pct")
    else:
        nitrogen_pct = st.number_input("نسبة النيتروجين (Nitrogen %)", min_value=0.0, max_value=100.0,
                                        step=0.01, value=None, key=f"{key_prefix}_prox_n_pct")
        if nitrogen_pct is not None:
            st.caption(f"البروتين الخام المحسوب: {prox.compute_crude_protein_from_nitrogen(nitrogen_pct)}%")

    col_ee, col_cf, col_ash = st.columns(3)
    with col_ee:
        ether_extract = st.number_input("الدهن الخام (Ether Extract %)", min_value=0.0, max_value=100.0,
                                         step=0.1, value=None, key=f"{key_prefix}_prox_ee_pct")
    with col_cf:
        crude_fiber = st.number_input("الألياف الخام (Crude Fiber %)", min_value=0.0, max_value=100.0,
                                       step=0.1, value=None, key=f"{key_prefix}_prox_cf_pct")
    with col_ash:
        ash = st.number_input("الرماد الخام (Ash %)", min_value=0.0, max_value=100.0, step=0.1,
                               value=None, key=f"{key_prefix}_prox_ash_pct")

    return {
        "moisture_pct": moisture, "crude_protein_pct": crude_protein_pct, "nitrogen_pct": nitrogen_pct,
        "ether_extract_pct": ether_extract, "crude_fiber_pct": crude_fiber, "ash_pct": ash,
    }


def render_proximate_stage_selector(species_key: str, key_prefix: str):
    """يبني قائمة اختيار المرحلة العمرية/الإنتاجية الخاصة ببروكسيمات القطاع المختار —
    dict فارغ (poultry_layer مثلًا) => تحذير واضح بدل قائمة فارغة صامتة."""
    stage_options = prox.get_proximate_stage_options(species_key) if species_key else {}
    if not species_key:
        st.info("اختر القطاع المستهدف أولًا لعرض المراحل المتاحة.")
        return None
    if not stage_options:
        st.warning(
            f"لا تتوفر معايير بروكسيمات موثَّقة لقطاع "
            f"'{SPECIES_LABELS_AR.get(species_key, species_key)}' حتى الآن."
        )
        return None
    stage_label_to_key = {v: k for k, v in stage_options.items()}
    selected_stage_label = st.selectbox(
        "المرحلة العمرية/الإنتاجية", options=list(stage_options.values()),
        key=f"{key_prefix}_prox_stage_select",
    )
    return stage_label_to_key.get(selected_stage_label)


# ==============================================================================
# 10) الواجهة الرئيسية — Main Layout (3 شاشات تحليل مستقلة)
# ==============================================================================
def main() -> None:
    st.set_page_config(
        page_title="Feed Toxins Audit | تدقيق جودة الأعلاف",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
        html, body, [class*="css"], .stMarkdown, .stMetric, .stTextArea, .stButton { font-family: 'Cairo', sans-serif; }
        .rtl-note { direction: rtl; text-align: right; }
        div[data-testid="stMetric"] {
            background-color: rgba(120, 120, 120, 0.06);
            border: 1px solid rgba(120, 120, 120, 0.18);
            border-radius: 10px;
            padding: 12px 14px 8px 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ==========================================================================
    # الشريط الجانبي — Sidebar (مدخلات مالية وتشغيلية فقط؛ لا إعدادات اتصال LLM)
    # ==========================================================================
    with st.sidebar:
        st.markdown("## مدخلات مالية وتشغيلية")
        feed_price = st.number_input(
            "سعر الكيلوجرام الواحد من العلف (ج.م)", min_value=0.0, value=25.0, step=0.5,
        )
        baseline_fcr = st.number_input(
            "معامل التحويل الغذائي المرجعي (Baseline FCR)", min_value=0.5, value=1.60, step=0.01,
        )
    st.title("Feed Toxins Audit")

    tab1, tab2, tab3 = st.tabs([
        "تأمين القطيع والسموم الفطرية", "التدقيق الكامل والشامل", "التحليل التقريبي فقط",
    ])

    with tab1:
        _render_mycotoxin_only_tab(feed_price, baseline_fcr)

    with tab2:
        _render_combined_tab(feed_price, baseline_fcr)

    with tab3:
        _render_proximate_only_tab()


def _render_mycotoxin_only_tab(feed_price: float, baseline_fcr: float) -> None:
    """Tab 1 — تأمين القطيع والسموم الفطرية (الشاشة الأصلية، بلا أي تعديل حسابي)."""
    KEY = "tab1"
    selector = render_species_flock_age_selector(KEY)
    clean_feed_toxin_levels = render_clean_feed_blending_expander(KEY)
    fingerprint = _shipment_fingerprint_inputs(KEY)
    lab_results = render_toxin_lab_inputs(KEY)
    storage_and_qty = render_storage_and_quantity_inputs(KEY)

    analyze_clicked = st.button("تحليل الشحنة الآن", type="primary", use_container_width=True, key=f"{KEY}_analyze")
    st.button(
        "شحنة جديدة", key=f"{KEY}_reset", use_container_width=True,
        on_click=_make_reset_callback(KEY, extra_number_input_keys=(
            f"{KEY}_aflatoxin_ppb", f"{KEY}_ochratoxin_ppb", f"{KEY}_don_ppm",
            f"{KEY}_zearalenone_ppm", f"{KEY}_fumonisin_ppm", f"{KEY}_temperature_celsius",
            f"{KEY}_moisture_percent", f"{KEY}_storage_days", f"{KEY}_quantity_tons",
        )),
    )

    if analyze_clicked:
        if not selector["selected_species_key"]:
            st.warning("الرجاء اختيار القطاع المستهدف من القائمة أعلاه قبل بدء التحليل.")
        elif all(v is None for v in lab_results.values()):
            st.error("لازم تدخل قيمة سم واحدة على الأقل.")
        else:
            parsed = build_structured_parsed_json(
                lab_results, storage_and_qty["storage"], quantity_tons=storage_and_qty["quantity_tons"],
                flock_name=selector["resolved_flock_name"], species_key_used=selector["effective_species_key"],
            )
            try:
                analysis = build_full_analysis(
                    parsed, baseline_fcr, feed_price, selector["effective_species_key"],
                    selector["manual_flock_age_days"], clean_feed_toxin_levels,
                )
                st.session_state[f"{KEY}_last_analysis"] = analysis
                st.session_state[f"{KEY}_last_fingerprint"] = fingerprint
                _record_supplier_history(analysis, fingerprint)
            except Exception as build_error:  # noqa: BLE001
                st.error(f"حدث خطأ أثناء تنفيذ الحسابات: {build_error}")
                with st.expander("عرض بيانات الـ JSON المبنية من الحقول المُدخَلة"):
                    st.json(parsed)

    if f"{KEY}_last_analysis" in st.session_state:
        analysis = st.session_state[f"{KEY}_last_analysis"]
        render_dashboard(analysis, st.session_state.get("supplier_history", {}),
                          st.session_state.get(f"{KEY}_last_fingerprint"))
        _render_pdf_download_button(
            KEY, "mycotoxin", lambda: pdf_report.build_mycotoxin_certificate_pdf(
                _build_pdf_fingerprint(st.session_state.get(f"{KEY}_last_fingerprint"), analysis), analysis,
            ),
        )



# ==============================================================================
# 11) أدوات مشتركة بين الشاشات الثلاث — Shared Tab Utilities
# ==============================================================================
def _make_reset_callback(key_prefix: str, extra_number_input_keys: tuple = ()):
    """
    يبني callback لزر "➕ شحنة جديدة" خاص بشاشة مُحدَّدة (key_prefix). نفس نمط
    reset_shipment_form القديم بالضبط (on_click إجباري — أي تعديل مباشر لـ
    session_state لعنصر واجهة بعد إنشائه في نفس الدورة يفشل بـ
    StreamlitAPIException). لا يمسح supplier_history ولا اختيار القطاع/القطيع/العمر
    (تجربة تشغيلية شائعة أن يُحلِّل المصنع عدة شحنات متتالية لنفس القطيع).
    """
    def _callback():
        st.session_state.pop(f"{key_prefix}_last_analysis", None)
        st.session_state.pop(f"{key_prefix}_last_fingerprint", None)
        st.session_state.pop(f"{key_prefix}_last_proximate_analysis", None)
        for number_key in extra_number_input_keys:
            st.session_state[number_key] = None
    return _callback


def _record_supplier_history(analysis: dict, fingerprint: dict) -> None:
    """يسجّل درجة تقييم المورد في سجل الجلسة — مصدر اسم المورد: البصمة الرسمية أولًا،
    وإلا shipment_meta (توافقًا مع أي بيانات تاريخية)."""
    supplier_name = (fingerprint or {}).get("supplier_name") or analysis["shipment_meta"].get("supplier_name") or "غير محدد"
    history = st.session_state.setdefault("supplier_history", {})
    score_value = analysis["supplier_score"]["score"]
    if score_value is not None:
        history.setdefault(supplier_name, []).append(score_value)


def _build_pdf_fingerprint(fingerprint: dict, analysis: dict) -> dict:
    """يحوّل مخرجات _shipment_fingerprint_inputs + species_key الفعلي إلى الشكل الذي
    يتوقعه pdf_report.py (يضيف species_label المُشتَق)."""
    fingerprint = dict(fingerprint or {})
    species_key = analysis.get("species_key")
    fingerprint["species_label"] = SPECIES_LABELS_AR.get(species_key, species_key)
    return fingerprint


def _build_pdf_fingerprint_proximate(fingerprint: dict, proximate_analysis: dict) -> dict:
    fingerprint = dict(fingerprint or {})
    fingerprint["species_label"] = (
        f"{proximate_analysis.get('species_label_ar')} ({proximate_analysis.get('stage_label_ar')})"
    )
    return fingerprint


def _render_pdf_download_button(key_prefix: str, pdf_kind: str, build_pdf_fn) -> None:
    """
    زر "📄 توليد شهادة PDF رسمية" — يظهر فقط بعد تحليل ناجح (الشرط مضمون من المستدعي،
    يُستدعى فقط داخل كتلة "if last_analysis in session_state"). التوليد الفعلي يحدث
    عند الضغط على الزر لا عند كل إعادة رسم (st.session_state cache بسيط لتفادي إعادة
    بناء PDF متطابق على كل rerun غير ضروري).
    """
    cache_key = f"{key_prefix}_{pdf_kind}_pdf_bytes"
    if st.button("توليد شهادة PDF رسمية", key=f"{key_prefix}_{pdf_kind}_generate_pdf"):
        try:
            st.session_state[cache_key] = build_pdf_fn()
        except RuntimeError as pdf_error:
            st.error(str(pdf_error))
            st.session_state.pop(cache_key, None)

    if st.session_state.get(cache_key):
        st.download_button(
            "تحميل الشهادة (PDF)", data=st.session_state[cache_key],
            file_name=f"feed_audit_certificate_{pdf_kind}.pdf", mime="application/pdf",
            key=f"{key_prefix}_{pdf_kind}_download_pdf",
        )


def _render_proximate_only_tab() -> None:
    """Tab 3 — التحليل التقريبي فقط (Proximate Analysis Only Module)، 5 مدخلات أساسية."""
    KEY = "tab3"
    col_species, col_stage = st.columns(2)
    with col_species:
        species_display_options = [SPECIES_PLACEHOLDER] + [SPECIES_LABELS_AR[k] for k in SPECIES_REGULATORY_LIMITS]
        species_label_to_key = {v: k for k, v in SPECIES_LABELS_AR.items()}
        selected_species_label = st.selectbox(
            "القطاع المستهدف (إجباري)", options=species_display_options, index=0,
            key=f"{KEY}_species_select",
        )
        selected_species_key = species_label_to_key.get(selected_species_label)
    with col_stage:
        selected_stage_key = render_proximate_stage_selector(selected_species_key, KEY)

    fingerprint = _shipment_fingerprint_inputs(KEY)
    proximate_inputs = render_proximate_inputs(KEY)

    analyze_clicked = st.button(
        "احسب نتيجة التحليل التقريبي", type="primary", use_container_width=True, key=f"{KEY}_analyze",
    )
    st.button(
        "شحنة جديدة", key=f"{KEY}_reset", use_container_width=True,
        on_click=_make_reset_callback(KEY, extra_number_input_keys=(
            f"{KEY}_prox_moisture_pct", f"{KEY}_prox_cp_pct", f"{KEY}_prox_n_pct",
            f"{KEY}_prox_ee_pct", f"{KEY}_prox_cf_pct", f"{KEY}_prox_ash_pct",
        )),
    )

    if analyze_clicked:
        if not selected_species_key:
            st.warning("الرجاء اختيار القطاع المستهدف من القائمة أعلاه قبل بدء التحليل.")
        elif not selected_stage_key:
            st.warning("الرجاء اختيار المرحلة العمرية/الإنتاجية (أو أن القطاع غير مدعوم بعد).")
        elif proximate_inputs["moisture_pct"] is None:
            st.error("الرجاء إدخال نسبة الرطوبة على الأقل — إلزامية لحساب NFE ولخطر التزنخ.")
        else:
            proximate_analysis = prox.build_full_proximate_analysis(
                selected_species_key, selected_stage_key, **proximate_inputs,
            )
            st.session_state[f"{KEY}_last_proximate_analysis"] = proximate_analysis
            st.session_state[f"{KEY}_last_fingerprint"] = fingerprint

    if f"{KEY}_last_proximate_analysis" in st.session_state:
        proximate_analysis = st.session_state[f"{KEY}_last_proximate_analysis"]
        render_proximate_dashboard(proximate_analysis)
        if not proximate_analysis.get("error"):
            _render_pdf_download_button(
                KEY, "proximate", lambda: pdf_report.build_proximate_certificate_pdf(
                    _build_pdf_fingerprint_proximate(st.session_state.get(f"{KEY}_last_fingerprint"), proximate_analysis),
                    proximate_analysis,
                ),
            )



def _render_combined_tab(feed_price: float, baseline_fcr: float) -> None:
    """
    Tab 2 — التدقيق الكامل والشامل: يُشغِّل محرك السموم (app.py) ومحرك البروكسيمات
    (proximate_engine.py) بالتوازي على نفس بيانات الشحنة الواحدة — قراران مستقلان
    تمامًا (كل منهما له مرجع حدود خاص في constants.py)، يُعرَضان كلوحتين منفصلتين
    تحت بعضهما، مع شهادة PDF واحدة موحَّدة تجمعهما.

    ⚠️ ملاحظة مهمة: نجاح/فشل أحد المحركين مستقل تمامًا عن الآخر. لو أُدخلت بيانات
    سموم فقط بلا بروكسيمات (أو العكس)، تُعرض لوحة واحدة فقط مع رسالة توضيحية بدل
    الأخرى — لا فشل كامل للشاشة بسبب نقص بيانات محرك واحد فقط.
    """
    KEY = "tab2"
    selector = render_species_flock_age_selector(KEY)
    selected_stage_key = render_proximate_stage_selector(selector["effective_species_key"], KEY)
    clean_feed_toxin_levels = render_clean_feed_blending_expander(KEY)
    fingerprint = _shipment_fingerprint_inputs(KEY)

    lab_results = render_toxin_lab_inputs(KEY)
    storage_and_qty = render_storage_and_quantity_inputs(KEY)
    proximate_inputs = render_proximate_inputs(KEY)

    analyze_clicked = st.button(
        "تحليل الشحنة الكامل (سموم + بروكسيمات)", type="primary", use_container_width=True,
        key=f"{KEY}_analyze",
    )
    st.button(
        "شحنة جديدة", key=f"{KEY}_reset", use_container_width=True,
        on_click=_make_reset_callback(KEY, extra_number_input_keys=(
            f"{KEY}_aflatoxin_ppb", f"{KEY}_ochratoxin_ppb", f"{KEY}_don_ppm",
            f"{KEY}_zearalenone_ppm", f"{KEY}_fumonisin_ppm", f"{KEY}_temperature_celsius",
            f"{KEY}_moisture_percent", f"{KEY}_storage_days", f"{KEY}_quantity_tons",
            f"{KEY}_prox_moisture_pct", f"{KEY}_prox_cp_pct", f"{KEY}_prox_n_pct",
            f"{KEY}_prox_ee_pct", f"{KEY}_prox_cf_pct", f"{KEY}_prox_ash_pct",
        )),
    )

    if analyze_clicked:
        if not selector["selected_species_key"]:
            st.warning("الرجاء اختيار القطاع المستهدف من القائمة أعلاه قبل بدء التحليل.")
        else:
            toxins_provided = not all(v is None for v in lab_results.values())
            proximates_provided = proximate_inputs["moisture_pct"] is not None
            if not toxins_provided and not proximates_provided:
                st.error("أدخل بيانات سموم واحدة على الأقل، أو بيانات بروكسيمات (رطوبة على الأقل) — أو كليهما.")
            else:
                toxin_analysis = None
                if toxins_provided:
                    parsed = build_structured_parsed_json(
                        lab_results, storage_and_qty["storage"], quantity_tons=storage_and_qty["quantity_tons"],
                        flock_name=selector["resolved_flock_name"], species_key_used=selector["effective_species_key"],
                    )
                    try:
                        toxin_analysis = build_full_analysis(
                            parsed, baseline_fcr, feed_price, selector["effective_species_key"],
                            selector["manual_flock_age_days"], clean_feed_toxin_levels,
                        )
                        _record_supplier_history(toxin_analysis, fingerprint)
                    except Exception as build_error:  # noqa: BLE001
                        st.error(f"حدث خطأ أثناء حساب جزء السموم: {build_error}")

                proximate_analysis = None
                if proximates_provided:
                    if not selected_stage_key:
                        st.warning(
                            "أُدخلت بيانات بروكسيمات لكن لم تُختر مرحلة عمرية/إنتاجية صالحة — "
                            "جزء البروكسيمات لن يُحسَب."
                        )
                    else:
                        proximate_analysis = prox.build_full_proximate_analysis(
                            selector["effective_species_key"], selected_stage_key, **proximate_inputs,
                        )

                st.session_state[f"{KEY}_last_analysis"] = toxin_analysis
                st.session_state[f"{KEY}_last_proximate_analysis"] = proximate_analysis
                st.session_state[f"{KEY}_last_fingerprint"] = fingerprint

    toxin_analysis = st.session_state.get(f"{KEY}_last_analysis")
    proximate_analysis = st.session_state.get(f"{KEY}_last_proximate_analysis")

    if toxin_analysis is not None:
        render_dashboard(toxin_analysis, st.session_state.get("supplier_history", {}),
                          st.session_state.get(f"{KEY}_last_fingerprint"))
    if proximate_analysis is not None:
        render_proximate_dashboard(proximate_analysis)

    if toxin_analysis is not None or (proximate_analysis is not None and not proximate_analysis.get("error")):
        def _build_combined_pdf():
            fingerprint_data = st.session_state.get(f"{KEY}_last_fingerprint")
            if toxin_analysis is not None and proximate_analysis is not None and not proximate_analysis.get("error"):
                fp = _build_pdf_fingerprint(fingerprint_data, toxin_analysis)
                return pdf_report.build_combined_certificate_pdf(fp, toxin_analysis, proximate_analysis)
            if toxin_analysis is not None:
                fp = _build_pdf_fingerprint(fingerprint_data, toxin_analysis)
                return pdf_report.build_mycotoxin_certificate_pdf(fp, toxin_analysis)
            fp = _build_pdf_fingerprint_proximate(fingerprint_data, proximate_analysis)
            return pdf_report.build_proximate_certificate_pdf(fp, proximate_analysis)

        _render_pdf_download_button(KEY, "combined", _build_combined_pdf)




if __name__ == "__main__":
    main()