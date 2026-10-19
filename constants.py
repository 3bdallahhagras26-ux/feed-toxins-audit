# -*- coding: utf-8 -*-
"""
================================================================================
constants.py — Feed Toxins Audit: المرجع الحتمي الوحيد (Single Source of Truth)
================================================================================
هذا الملف هو المصدر الوحيد لكل رقم تنظيمي أو حاسم يُستخدم في محرك الحسابات.
الذكاء الاصطناعي (LLM) لا يقرأ هذا الملف ولا يعرف بوجوده — دوره يقتصر على استخراج
الأرقام الخام من النص (Parsing) فقط. أي حد، أي عتبة، وأي قرار حاسم في التطبيق
يُسحب من هنا حصريًا وبنسبة 100% — لا تخمين، لا قيمة مكتوبة يدويًا داخل أي دالة حسابية.

VERSION: 1.3.0
LAST ENGINEERING REVIEW: 2026-09-28

CHANGELOG:
- v1.3.0 — أُضيف SPECIES_PROXIMATE_STANDARDS: مرجع حتمي ثانٍ مستقل عن
  SPECIES_REGULATORY_LIMITS، لمعايير التركيب الغذائي (بروتين/دهن/ألياف/رماد) بدلالة
  المرحلة العمرية/الإنتاجية لكل قطاع — يغذّي محرك بروكسيمات جديد (proximate_engine.py)
  منفصل تمامًا عن محرك السموم الفطرية. ⚠️ تغطية جزئية مقصودة: 4 قطاعات فقط
  (poultry_broiler، cattle_dairy، cattle_beef، aquaculture) — "poultry_layer" غير
  مُدرَج لعدم توفر بيانات مرجعية موثَّقة له عند إعداد هذا القسم؛ get_proximate_standard()
  تُعيد None صراحةً لهذا القطاع بدل تخمين أو استعارة من قطاع آخر. أُضيف أيضًا
  N_TO_PROTEIN_FACTOR = 6.25 (ثابت كيميائي عام، TIER-1) لتحويل نسبة النيتروجين إلى
  بروتين خام (CP% = N% × 6.25) في proximate_engine.py. مصادر جديدة في السجل أعلاه:
  [ROSS308]، [COBB500-N]، [NASEM2021]، [NRC2016]، [EOS1466]، [NRC2011].
- v1.2.0 — أُضيف FLOCK_TO_SPECIES_MAP: مرجع حتمي يربط تسميات القطيع/العنبر التشغيلية
  (كما يعرفها فريق المزرعة، مثل "قطيع A - عنبر التسمين 1") بمفاتيح القطاعات التنظيمية
  الخمسة الموجودة أصلًا في SPECIES_REGULATORY_LIMITS. ⚠️ لا فئة تنظيمية جديدة أُضيفت —
  القطيع تسمية تشغيلية فقط، تُترجَم دائمًا إلى أحد المفاتيح الخمسة المعتمدة قبل الوصول
  لأي حد تنظيمي (يُطبَّق هذا القيد في app.py عبر add_custom_flock() التي ترفض أي مفتاح
  غير موجود في SPECIES_REGULATORY_LIMITS بـ ValueError صريح). راجع app.py v2.3.0.
- v1.1.0 — تشديد حدود الاستزراع السمكي (Aquaculture) كسياسة عمل داخلية أكثر تحفظًا:
  أفلاتوكسين accept_limit 20→10 ppb، reject_limit 50→15 ppb (مضاعف رفض 1.5× بدل 2.5×
  الافتراضي)؛ أوكراتوكسين accept_limit 100→5 ppb، reject_limit 300→10 ppb (مضاعف رفض
  2.0× بدل 3.0× الافتراضي). أُضيفت دالة get_reject_multiple(species_key, toxin_key) التي
  تحسب المضاعف الفعلي من accept_limit/reject_limit الحقيقيين لكل قطاع بدل قراءة قيمة
  TOXIN_REJECT_MULTIPLES العامة مباشرة — هذا ما يسمح لقطاع بعينه بهامش أمان أضيق من بقية
  الأنواع لنفس السم دون التأثير عليها. app.py (compute_final_decision) عُدِّل ليستدعي هذه
  الدالة بدل القراءة المباشرة من القاموس العام (راجع app.py v1.6.0).

--------------------------------------------------------------------------------
مستويات الأدلة العلمية (EVIDENCE TIER LEGEND) — كل رقم في هذا الملف مُصنَّف صراحةً:
--------------------------------------------------------------------------------
TIER-1  : اقتباس تنظيمي مباشر من مصدر رسمي منشور (FDA CPG / FDA Guidance / EU
          Commission Recommendation) — رقم مذكور حرفيًا في الوثيقة الرسمية.
TIER-2  : رقم TIER-1 لكنه مُشتق بحساب موثّق (تحويل % من العليقة، أو تعميم على نوع
          مقارب لا يوجد له نص رسمي مباشر — مثال: تطبيق حد الجراد سمك القط الرسمي
          على الاستزراع السمكي عمومًا لغياب نص خاص بالبلطي/الدنيس).
TIER-3  : تقدير هندسي مبني على أدبيات علمية محكّمة (Peer-Reviewed) — ليس رقمًا
          تنظيميًا رسميًا، ولا يوجد له نص قانوني منشور، لكنه مُستمَد من دراسات/
          مراجعات علمية موثّقة بالمصدر.
TIER-4  : قيمة إدارة مخاطر داخلية (Internal Risk-Management Default) — قرار هندسي
          للمنصة نفسها (مثال: "بعد كام ضعف من الحد يصبح الخلط غير اقتصادي؟"). هذا
          النوع من الأرقام **يتطلب اعتماد فريق الجودة/الامتثال والطبيب البيطري
          المسؤول قبل اعتماده في قرارات تشغيلية فعلية** — مُعلَّم بوضوح أينما ورد.

⚠️ لا يوجد في هذا الملف أي رقم TIER-4 مموَّه على أنه TIER-1. الشفافية الكاملة حول
مصدر كل رقم هي جوهر تصميم هذا الملف لأنظمة تُتَّخذ عليها قرارات مالية بالملايين.

--------------------------------------------------------------------------------
المصادر الأساسية المرجعية (Primary Sources Referenced Throughout This File):
--------------------------------------------------------------------------------
[FDA-AFLA]  FDA Compliance Policy Guide Sec. 683.100, "Action Levels for Aflatoxins
            in Animal Feeds".
[FDA-FUM]   FDA "Guidance for Industry: Fumonisin Levels in Human Foods and Animal
            Feeds; Final Guidance", November 2001 (Table 1 — recommended maximum
            levels in corn/corn by-products and in the total ration, by species).
[FDA-DON]   FDA Advisory levels for deoxynivalenol (vomitoxin) in grains and grain
            by-products for animal feed (per NGFA Industry Notification on FDA
            Mycotoxin Guidance).
[EU-2016]   Commission Recommendation (EU) 2016/1319 amending Recommendation
            2006/576/EC — guidance values for deoxynivalenol, zearalenone, and
            ochratoxin A in products intended for animal feed.
[COBB500]   Cobb 500 Broiler Performance & Nutrition Supplement — official breeder
            feeding-period table (Starter/Grower/Finisher 1/Finisher 2).
[LIT-SYN]   مراجعات علمية محكّمة حول التآزر/التراكم بين السموم الفطرية عند التعايش
            (انظر التوثيق التفصيلي أسفل MYCOTOXIN_SYNERGY_MATRIX).
[ROSS308]   Aviagen Ross 308 Broiler: Nutrition Specifications, 2022 edition —
            كتالوج تغذية السلالة الرسمي من Aviagen.
[COBB500-N] Cobb-Vantress Cobb 500 Broiler Performance & Nutrition Supplement —
            جداول متطلبات التغذية الرسمية للسلالة (مختلف عن [COBB500] أعلاه الذي
            يوثّق المراحل العمرية فقط، لا نسب العناصر الغذائية).
[NASEM2021] National Academies of Sciences, Engineering, and Medicine (2021),
            "Nutrient Requirements of Dairy Cattle", 8th Revised Edition.
[NRC2016]   National Research Council (2016), "Nutrient Requirements of Beef
            Cattle", 8th Revised Edition.
[EOS1466]   الهيئة المصرية العامة للمواصفات والجودة — المواصفة القياسية المصرية
            EOS 1466 للأعلاف الحيوانية المصنَّعة المركَّزة.
[NRC2011]   National Research Council (2011), "Nutrient Requirements of Fish and
            Shrimp" — بيانات أسماك المياه الدافئة والبلطي النيلي (Nile Tilapia).

هذا الملف لا يغني عن المراجعة الدورية من طبيب بيطري/فريق امتثال مرخّص، خصوصًا بنود
TIER-3 و TIER-4، ولا يعكس بالضرورة اشتراطات هيئة الرقابة على الصادرات والواردات
المصرية (GOEIC) أو أي جهة رقابية محلية أخرى قد تفرض حدودًا أكثر صرامة.
================================================================================
"""

# ==============================================================================
# SECTION 1 — قائمة السموم المدعومة والبيانات الوصفية (Toxin Metadata)
# ==============================================================================
# مصدر وحيد لاسم كل سم، وحدته، وزنه في مؤشر MRI، ومسمّاه بالعربي — تُقرأ منه كل
# الدوال والواجهة، فلا يوجد اسم سم مكتوب حرفيًا "Hardcoded" في أي مكان آخر بالنظام.
TOXIN_METADATA = {
    "aflatoxin_ppb": {
        "label_ar": "أفلاتوكسين (إجمالي B1+B2+G1+G2)",
        "unit": "ppb",
        "mri_severity_weight": 0.35,
        "carcinogen_class": "IARC Group 1 (مادة مسرطنة مؤكدة للإنسان)",
    },
    "ochratoxin_ppb": {
        "label_ar": "أوكراتوكسين A",
        "unit": "ppb",
        "mri_severity_weight": 0.15,
        "carcinogen_class": "IARC Group 2B (مادة مسرطنة محتملة)",
    },
    "don_ppm": {
        "label_ar": "دون / فوميتوكسين (Deoxynivalenol)",
        "unit": "ppm",
        "mri_severity_weight": 0.20,
        "carcinogen_class": "غير مصنَّف كمسرطن — سمّية حادة (رفض علف/تقيؤ) أبرز من التسرطن",
    },
    "zearalenone_ppm": {
        "label_ar": "زيارالينون (Zearalenone)",
        "unit": "ppm",
        "mri_severity_weight": 0.15,
        "carcinogen_class": "غير مصنَّف كمسرطن — تأثيرات هرمونية/تناسلية استروجينية",
    },
    "fumonisin_ppm": {
        "label_ar": "فيومونيسين (إجمالي FB1+FB2+FB3)",
        "unit": "ppm",
        "mri_severity_weight": 0.15,
        "carcinogen_class": "IARC Group 2B (مادة مسرطنة محتملة)",
    },
}
# ⚠️ التحقق الهندسي: مجموع mri_severity_weight لكل السموم أعلاه = 1.00 بالضبط
# (0.35 + 0.15 + 0.20 + 0.15 + 0.15 = 1.00). أي تعديل لوزن سم واحد يتطلب إعادة
# توزيع الفارق على باقي السموم يدويًا حفاظًا على هذا الثابت.
TOXIN_KEYS = tuple(TOXIN_METADATA.keys())


# ==============================================================================
# SECTION 1B — أسماء القطاعات ومرادفاتها (Species Labels & Synonyms)
# ==============================================================================
# مصدر وحيد لقائمة القطاعات الخمسة المدعومة. أي قطاع جديد يُضاف مستقبلًا يُضاف
# هنا وفي SPECIES_REGULATORY_LIMITS و FEED_STAGES_CONFIG معًا — لا مكان آخر
# بالنظام يجب أن يحمل قائمة قطاعات منفصلة قد تنحرف عن هذه القائمة.
SPECIES_LABELS_AR = {
    "poultry_broiler": "دواجن تسمين (Broiler)",
    "poultry_layer": "دواجن بياض (Layer)",
    "cattle_dairy": "مواشي حلاب (Dairy)",
    "cattle_beef": "مواشي تسمين (Beef)",
    "aquaculture": "استزراع سمكي (Aquaculture)",
}

# ==============================================================================
# SECTION 1C — ربط القطيع/العنبر بالفئة التنظيمية (Flock-to-Species Mapping)
# ==============================================================================
# مرجع حتمي: أسماء قطعان/عنابر تشغيلية فعلية (كما يعرفها فريق المزرعة) => مفتاح
# القطاع التنظيمي المقابل. ⚠️ كل قيمة هنا يجب أن تكون مفتاحًا موجودًا فعليًا في
# SPECIES_REGULATORY_LIMITS — لا فئة جديدة تُخترع هنا (لا Swine، لا Equine، ...):
# القطاعات الخمسة المعتمدة فقط. القطيع نفسه ليس فئة تنظيمية بديلة، بل تسمية تشغيلية
# تُترجَم دائمًا إلى أحد المفاتيح الخمسة قبل الوصول لأي حد تنظيمي في SPECIES_REGULATORY_LIMITS.
FLOCK_TO_SPECIES_MAP = {
    "قطيع A - عنبر التسمين 1": "poultry_broiler",
    "قطيع B - عنبر التسمين 2": "poultry_broiler",
    "قطيع الأمهات": "poultry_layer",
    "قطيع البياض": "poultry_layer",
    "قطيع الحلاب": "cattle_dairy",
    "ماشية التسمين": "cattle_beef",
    "حوض الاستزراع السمكي": "aquaculture",
}

# يُستخدم فقط في التدقيق التقاطعي لما يستخرجه النموذج اللغوي من النص الحر —
# لا يُستخدم أبدًا كمصدر لتحديد القطاع الفعلي في الحسابات (ذلك يأتي حصريًا من
# اختيار المستخدم اليدوي في الواجهة).
SPECIES_SYNONYM_MAP = {
    "poultry_broiler": "poultry_broiler", "broiler": "poultry_broiler", "تسمين": "poultry_broiler",
    "دواجن تسمين": "poultry_broiler",
    "poultry_layer": "poultry_layer", "layer": "poultry_layer", "بياض": "poultry_layer", "بياضة": "poultry_layer",
    "cattle_dairy": "cattle_dairy", "dairy": "cattle_dairy", "حلاب": "cattle_dairy", "الالبان": "cattle_dairy",
    "ألبان": "cattle_dairy", "مواشي حلاب": "cattle_dairy",
    "cattle_beef": "cattle_beef", "beef": "cattle_beef", "مواشي تسمين": "cattle_beef",
    "aquaculture": "aquaculture", "fish": "aquaculture", "أسماك": "aquaculture", "استزراع": "aquaculture",
    "استزراع سمكي": "aquaculture",
}


def normalize_species_key(raw_species):
    """يحوّل أي مسمّى قطاع (عربي/إنجليزي/عامي) إلى مفتاح موحّد — للتدقيق التقاطعي فقط."""
    if not raw_species:
        return None
    return SPECIES_SYNONYM_MAP.get(str(raw_species).strip().lower())


# ==============================================================================
# SECTION 2 — SPECIES_REGULATORY_LIMITS
# ==============================================================================
# لكل قطاع × لكل سم: accept_limit (الحد التنظيمي الرسمي = بداية عدم الامتثال) و
# reject_limit (عتبة الرفض الاقتصادي/التشغيلي الصريحة — القيمة التي فوقها يصبح
# الخلط غير مجدٍ اقتصاديًا أو غير آمن بيولوجيًا مهما كانت نسبة التخفيف الحسابية).
#
# ⚠️ فرق جوهري يجب فهمه: accept_limit **دائمًا** TIER-1 أو TIER-2 (رقم تنظيمي
# رسمي أو مُشتق منه مباشرة). أما reject_limit فهو **دائمًا TIER-4** — لا FDA ولا
# EU ينشران "حد رفض" منفصل عن حد الامتثال نفسه؛ أي تجاوز لـ accept_limit هو
# مخالفة تنظيمية بالفعل. reject_limit هنا هو حد إدارة مخاطر داخلي للمنصة يحدد
# متى يصبح "الخلط لإعادة الشحنة للامتثال" غير عملي أو غير مسؤول بيولوجيًا،
# محسوب كمضاعف (Reject Multiple) لكل سم حسب شدته النسبية (انظر TOXIN_REJECT_MULTIPLES
# أسفل الجدول) — **يتطلب اعتماد الطبيب البيطري المسؤول وفريق الامتثال قبل
# الاعتماد التشغيلي الكامل**.
SPECIES_REGULATORY_LIMITS = {
    "poultry_broiler": {
        "aflatoxin_ppb": {
            "accept_limit": 20.0,
            "reject_limit": 50.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-AFLA] حد عام/حيوانات غير ناضجة 20 ppb؛ يتوافق مع [EU-2016] "
                      "أعلاف دواجن كاملة 20 ppb.",
        },
        "ochratoxin_ppb": {
            "accept_limit": 100.0,
            "reject_limit": 300.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] قيمة إرشادية لأعلاف الدواجن الكاملة = 100 ppb.",
        },
        "don_ppm": {
            "accept_limit": 5.0,
            "reject_limit": 20.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] دواجن = 5 ppm (أشد تحفظًا من [FDA-DON] الاسترشادي 10 ppm "
                      "لـ ≤50% من العليقة) — اعتُمدت القيمة الأكثر تحفظًا.",
        },
        "zearalenone_ppm": {
            "accept_limit": 0.25,
            "reject_limit": 0.875,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] دواجن = 0.25 ppm.",
        },
        "fumonisin_ppm": {
            "accept_limit": 50.0,
            "reject_limit": 200.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-FUM] دواجن تُربّى للذبح: 100 ppm في الذرة ومنتجاتها "
                      "(بحد أقصى 50% من العليقة) ≈ 50 ppm في العليقة الكاملة.",
        },
    },
    "poultry_layer": {
        "aflatoxin_ppb": {
            "accept_limit": 20.0,
            "reject_limit": 50.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "نفس أساس poultry_broiler — القيمة الأكثر تحفظًا (20 ppb) اعتُمدت "
                      "للبياض أيضًا رغم أن [FDA-AFLA] يسمح بـ 100 ppb للدواجن الناضجة/التربية، "
                      "احترازًا لبقايا الأفلاتوكسين المحتملة في البيض.",
        },
        "ochratoxin_ppb": {
            "accept_limit": 100.0,
            "reject_limit": 300.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] دواجن = 100 ppb.",
        },
        "don_ppm": {
            "accept_limit": 5.0,
            "reject_limit": 20.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] دواجن = 5 ppm.",
        },
        "zearalenone_ppm": {
            "accept_limit": 0.25,
            "reject_limit": 0.875,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] دواجن = 0.25 ppm.",
        },
        "fumonisin_ppm": {
            "accept_limit": 15.0,
            "reject_limit": 60.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-FUM] فئة 'قطيع التربية' (Breeding Stock) تشمل نصًا 'دجاج البياض' "
                      "(laying hens) — 30 ppm في الذرة (≤50% من العليقة) ≈ 15 ppm في العليقة الكاملة.",
        },
    },
    "cattle_dairy": {
        "aflatoxin_ppb": {
            "accept_limit": 20.0,
            "reject_limit": 50.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-AFLA] حيوانات الألبان = 20 ppb (بسبب انتقال AFM1 إلى اللبن).",
        },
        "ochratoxin_ppb": {
            "accept_limit": 250.0,
            "reject_limit": 750.0,
            "evidence_tier": "TIER-3 (accept) / TIER-4 (reject)",
            "source": "لا يوجد نص [EU-2016] مباشر لأبقار الألبان تحديدًا. تقدير احترازي "
                      "مبني على قدرة المجترات الجزئية على تحليل الأوكراتوكسين بالكرش "
                      "(Rumen Degradation) — يتطلب تحققًا محليًا قبل الاعتماد الكامل.",
        },
        "don_ppm": {
            "accept_limit": 10.0,
            "reject_limit": 40.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-DON] أبقار حلوب >4 أشهر (≤50% من العليقة) = 10 ppm.",
        },
        "zearalenone_ppm": {
            "accept_limit": 0.50,
            "reject_limit": 1.75,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] أبقار ألبان/أغنام = 0.5 ppm.",
        },
        "fumonisin_ppm": {
            "accept_limit": 15.0,
            "reject_limit": 60.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-FUM] فئة 'قطيع التربية' تشمل نصًا 'أبقار الألبان الحلوب' "
                      "(lactating dairy cows) — 30 ppm في الذرة (≤50%) ≈ 15 ppm في العليقة الكاملة.",
        },
    },
    "cattle_beef": {
        "aflatoxin_ppb": {
            "accept_limit": 100.0,
            "reject_limit": 250.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-AFLA] أبقار تربية (Breeding Beef) = 100 ppb — القيمة الأكثر "
                      "تحفظًا لعموم قطيع اللحم (أبقار التسمين النهائي تصل رسميًا حتى 300 ppb "
                      "لكن اعتُمدت 100 ppb احترازيًا لتغطية كل الأعمار داخل هذا القطاع).",
        },
        "ochratoxin_ppb": {
            "accept_limit": 250.0,
            "reject_limit": 750.0,
            "evidence_tier": "TIER-3 (accept) / TIER-4 (reject)",
            "source": "نفس تقدير cattle_dairy الاحترازي — لا نص [EU-2016] مباشر لأبقار اللحم.",
        },
        "don_ppm": {
            "accept_limit": 10.0,
            "reject_limit": 40.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-DON] أبقار تسمين/لاحمة (feedlot) >4 أشهر (≤50% من العليقة) = 10 ppm.",
        },
        "zearalenone_ppm": {
            "accept_limit": 0.50,
            "reject_limit": 1.75,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[EU-2016] أبقار/أغنام = 0.5 ppm.",
        },
        "fumonisin_ppm": {
            "accept_limit": 30.0,
            "reject_limit": 120.0,
            "evidence_tier": "TIER-1 (accept) / TIER-4 (reject)",
            "source": "[FDA-FUM] مجترات ≥3 أشهر تُربّى للذبح: 60 ppm في الذرة (≤50% من "
                      "العليقة) ≈ 30 ppm في العليقة الكاملة.",
        },
    },
    "aquaculture": {
        "aflatoxin_ppb": {
            "accept_limit": 10.0,
            "reject_limit": 15.0,
            "evidence_tier": "TIER-4 (accept) / TIER-4 (reject)",
            "source": "لا يوجد حد [FDA-AFLA]/[EU-2016] رسمي خاص بالاستزراع السمكي. القيمة "
                      "الافتراضية الهندسية السابقة كانت 20 ppb (TIER-2، حد FDA العام "
                      "لـ'الأنواع غير المدرجة'). عُدِّلت بقرار سياسة داخلي (2026-09) إلى 10 "
                      "ppb accept / 15 ppb reject — أضيق من الحد العام عمدًا، تحفظًا إضافيًا "
                      "لحساسية الأسماك المعروفة للأفلاتوكسين (سمك السلمون المرقّط/Rainbow "
                      "Trout هو نموذج الحيوانات الأكثر استخدامًا عالميًا في دراسات تسرطن "
                      "الأفلاتوكسين الكبدي). ⚠️ هذا مضاعف رفض خاص بهذا القطاع فقط (1.5×،  "
                      "أضيق من TOXIN_REJECT_MULTIPLES العام 2.5×) — راجع get_reject_multiple().",
        },
        "ochratoxin_ppb": {
            "accept_limit": 5.0,
            "reject_limit": 10.0,
            "evidence_tier": "TIER-4 (accept) / TIER-4 (reject)",
            "source": "لا يوجد نص رسمي خاص بالاستزراع السمكي. القيمة الافتراضية السابقة "
                      "كانت 100 ppb (TIER-3، بنفس مستوى الدواجن). عُدِّلت بقرار سياسة داخلي "
                      "(2026-09) إلى 5 ppb accept / 10 ppb reject — أضيق بكثير من أي نظير "
                      "بري موثّق (أدنى حد EU معروف هو 50 ppb للخنازير)، كإجراء احترازي "
                      "إضافي صريح لأسواق تصدير الاستزراع السمكي عالية الحساسية. ⚠️ هذا "
                      "مضاعف رفض خاص بهذا القطاع فقط (2.0×، أضيق من TOXIN_REJECT_MULTIPLES "
                      "العام 3.0×) — راجع get_reject_multiple().",
        },
        "don_ppm": {
            "accept_limit": 5.0,
            "reject_limit": 20.0,
            "evidence_tier": "TIER-3 (accept) / TIER-4 (reject)",
            "source": "لا يوجد نص رسمي خاص بالاستزراع السمكي — تقدير احترازي.",
        },
        "zearalenone_ppm": {
            "accept_limit": 0.25,
            "reject_limit": 0.875,
            "evidence_tier": "TIER-3 (accept) / TIER-4 (reject)",
            "source": "لا يوجد نص رسمي خاص بالاستزراع السمكي — تقدير احترازي.",
        },
        "fumonisin_ppm": {
            "accept_limit": 10.0,
            "reject_limit": 40.0,
            "evidence_tier": "TIER-2 (accept) / TIER-4 (reject)",
            "source": "[FDA-FUM] فئة 'القط الرقطي/سمك القط' (Catfish) = 20 ppm في الذرة "
                      "(≤50% من العليقة) ≈ 10 ppm في العليقة الكاملة — أقرب نظير رسمي "
                      "متاح للاستزراع السمكي، عُمِّم على القطاع بالكامل لغياب نص خاص بالبلطي/الدنيس.",
        },
    },
}

# سقف إرشادي إضافي (وليس تنظيميًا) خاص بالبلطي النيلي فقط — TIER-3
TILAPIA_AFLATOXIN_LITERATURE_CEILING_PPB = 100.0
# ⚠️ ملاحظة اتساق (2026-09): هذا السقف الأدبي (100 ppb) أعلى الآن من accept_limit الجديد
# للاستزراع السمكي في SPECIES_REGULATORY_LIMITS (10 ppb). هذا ليس تناقضًا: TILAPIA_..._CEILING
# يمثّل أقصى ما أثبتته الأدبيات كسقف تحمّل بيولوجي (Biological Tolerance) للبلطي تحديدًا،
# بينما accept_limit الجديد هو سياسة عمل داخلية أكثر تحفظًا (Commercial Risk Policy) تطبَّق
# على كل قطاع الاستزراع السمكي ولا تقتصر على البلطي وحده. الفرق بينهما متعمَّد ومقصود.

# مضاعفات الرفض *الافتراضية* لكل سم — تُستخدم كخط أساس (Baseline) عند اشتقاق reject_limit
# لمعظم الأنواع، وكقيمة احتياطية (Fallback) في get_reject_multiple() إن غاب accept/reject_limit
# لسبب ما. ⚠️ هذه ليست بالضرورة القيمة الفعلية المستخدَمة وقت التشغيل لكل الأنواع — أي قطاع
# يمكن أن يكون له مضاعف مختلف صراحةً عبر accept_limit/reject_limit الخاصين به (مثال: الاستزراع
# السمكي أعلاه: أفلاتوكسين 1.5× وأوكراتوكسين 2.0× بدل 2.5×/3.0× الافتراضيين). القيمة الحقيقية
# المعتمدة دائمًا هي reject_limit ÷ accept_limit المحسوبة ديناميكيًا — استخدم get_reject_multiple()
# ولا تقرأ من هذا القاموس مباشرة في أي منطق قرار.
TOXIN_REJECT_MULTIPLES = {
    "aflatoxin_ppb": 2.5,   # الأضيق افتراضيًا: مادة مسرطنة IARC Group 1 — أقل هامش أمان مقبول
    "ochratoxin_ppb": 3.0,  # IARC Group 2B + توثيق تآزر مع الأفلاتوكسين (انظر SYNERGY_MATRIX)
    "zearalenone_ppm": 3.5, # تأثيرات هرمونية غالبًا قابلة للعكس بإزالة المصدر
    "don_ppm": 4.0,         # سمّية حادة (رفض علف) أكثر من تراكمية؛ صناعيًا الأكثر قبولًا للتخفيف
    "fumonisin_ppm": 4.0,   # نفس منطق DON — [FDA-FUM] نفسه مبني على منهجية %-من-العليقة القابلة للتخفيف
}


def get_reject_multiple(species_key: str, toxin_key: str) -> float:
    """
    يحسب مضاعف الرفض *الفعلي* (reject_limit ÷ accept_limit) لسم مُحدَّد ضمن قطاع مُحدَّد،
    مباشرة من القيمتين الحقيقيتين المخزّنتين في SPECIES_REGULATORY_LIMITS لهذا القطاع بالذات
    — بدل قراءة قيمة عامة واحدة من TOXIN_REJECT_MULTIPLES تُطبَّق على كل الأنواع بلا تمييز.

    هذا هو ما يسمح لقطاع بعينه (الاستزراع السمكي هنا) أن يكون له هامش أمان أضيق من باقي
    الأنواع لنفس السم (مثال: أفلاتوكسين 1.5× للاستزراع السمكي مقابل 2.5× افتراضيًا لبقية
    الأنواع) دون أي تأثير جانبي على أي قطاع آخر. محرك القرار في app.py (compute_final_decision)
    يستدعي هذه الدالة حصريًا — لا يقرأ TOXIN_REJECT_MULTIPLES مباشرة أبدًا.

    يسقط احتياطيًا (Fallback) إلى TOXIN_REJECT_MULTIPLES العام فقط إذا غاب accept_limit أو
    reject_limit لهذا الزوج قطاع/سم تمامًا (حالة بيانات ناقصة، وليست سلوكًا طبيعيًا متوقعًا).
    """
    accept_limit = get_species_limit(species_key, toxin_key, "accept_limit")
    reject_limit = get_species_limit(species_key, toxin_key, "reject_limit")
    if not accept_limit or not reject_limit:
        return TOXIN_REJECT_MULTIPLES.get(toxin_key, 3.0)
    return reject_limit / accept_limit


# ==============================================================================
# SECTION 3 — FEED_STAGES_CONFIG
# ==============================================================================
# قواعد المراحل العمرية لكل قطاع. الحقل allow_blending هو التوصية الافتراضية
# لهذه المرحلة، لكن UNIVERSAL_MIN_BLENDING_AGE_DAYS أدناه هو قاعدة قاطعة تتخطى
# (Override) أي إعداد هنا — أي عمر أقل من هذا الرقم يُمنع فيه الخلط نهائيًا بصرف
# النظر عن المرحلة المُختارة أو نتيجة معادلة الخلط الحسابية.
FEED_STAGES_CONFIG = {
    "poultry_broiler": {
        "stages": {
            "starter": {
                "label_ar": "بادي",
                "age_days_min": 0,
                "age_days_max": 10,
                "allow_blending": False,
                "source": "[COBB500] فترة التغذية Starter = 0-10 يوم؛ يتوافق مع دلائل "
                          "إدارة Ross 308 (Starter 0-10 يوم في عدة برامج تغذية منشورة).",
            },
            "grower": {
                "label_ar": "نامي",
                "age_days_min": 11,
                "age_days_max": 24,
                "allow_blending": True,
                "source": "[COBB500] فترة Grower = 11-22 يوم؛ دلائل Ross 308 تمتد Grower "
                          "حتى يوم 24 في بعض البرامج — اعتُمد المدى الأوسع (11-24) احترازيًا.",
            },
            "finisher": {
                "label_ar": "ناهي",
                "age_days_min": 25,
                "age_days_max": None,
                "allow_blending": True,
                "source": "[COBB500] فترات Finisher 1 (23-42 يوم) وFinisher 2 (43+ يوم) "
                          "دُمجتا في مرحلة 'ناهي' واحدة لتبسيط تصنيف المخاطر.",
            },
        },
    },
    "poultry_layer": {
        "stages": {
            "production": {
                "label_ar": "بياض إنتاجي",
                "age_days_min": None,
                "age_days_max": None,
                "allow_blending": True,
                "source": "مرحلة واحدة مجمّعة كما هو مطلوب بنطاق العمل الحالي — لا تفريع "
                          "لمراحل تحضين/نمو منفصلة قبل بداية الإنتاج في هذا الإصدار.",
            },
        },
    },
    "cattle_dairy": {
        "stages": {
            "lactating": {
                "label_ar": "حلاّب",
                "age_days_min": None,
                "age_days_max": None,
                "allow_blending": True,
                "source": "مرحلة واحدة مجمّعة كما هو مطلوب بنطاق العمل الحالي.",
            },
        },
    },
    "cattle_beef": {
        "stages": {
            "production": {
                "label_ar": "تسمين",
                "age_days_min": None,
                "age_days_max": None,
                "allow_blending": True,
                "source": "لم يُطلَب تفريع مراحل عمرية لهذا القطاع في نطاق العمل الحالي — "
                          "مرحلة واحدة مجمّعة؛ يمكن تفصيلها لاحقًا (عجول رضيعة/نمو/تسمين "
                          "نهائي) بنفس بنية FEED_STAGES_CONFIG دون تعديل أي دالة حسابية.",
            },
        },
    },
    "aquaculture": {
        "stages": {
            "production": {
                "label_ar": "إنتاج سمكي",
                "age_days_min": None,
                "age_days_max": None,
                "allow_blending": True,
                "source": "لم يُطلَب تفريع مراحل عمرية لهذا القطاع في نطاق العمل الحالي.",
            },
        },
    },
}

# ⚠️ قاعدة قاطعة (Hard Override): حظر الخلط تمامًا لأي عمر أقل من هذا الرقم، بصرف
# النظر عن المرحلة المختارة أو النوع — TIER-4 (قرار سلامة بيطرية داخلي: القدرة
# الأيضية/الكبدية على إزالة السموم غير مكتملة النضج في الأيام الأولى من العمر
# في كل الأنواع تقريبًا، فلا يصح الاعتماد على تخفيف حسابي وحده).
UNIVERSAL_MIN_BLENDING_AGE_DAYS = 14


# ==============================================================================
# SECTION 4 — ENVIRONMENTAL_THRESHOLDS
# ==============================================================================
# عتبات الحرارة/الرطوبة الحرجة المستخدمة في حساب خطورة التخزين وعمر التخزين الآمن.
ENVIRONMENTAL_THRESHOLDS = {
    "temperature_c": {
        "risk_floor": 20.0,
        "risk_ceiling": 35.0,
        "evidence_tier": "TIER-3",
        "source": "أدبيات تخزين الحبوب والأعلاف — النشاط الفطري المُنتِج للسموم يتسارع "
                  "بشكل ملحوظ عند حرارة ≥27°م تقريبًا؛ 20°-35°م نطاق تدرّج هندسي محافظ "
                  "يغلّف هذه العتبة من الجانبين لتفادي قفزة حادة غير واقعية عند نقطة واحدة.",
    },
    "moisture_percent": {
        "risk_floor": 11.0,
        "risk_ceiling": 19.0,
        "evidence_tier": "TIER-3",
        "source": "نفس المرجع أعلاه — رطوبة أعلى من ~14% مع حرارة دافئة هي بيئة حاضنة "
                  "نشطة شائعة الاستشهاد بها في أدبيات تخزين الحبوب.",
    },
    "mold_favorable_zone": {
        "temperature_c_min": 27.0,
        "moisture_percent_min": 14.0,
        "evidence_tier": "TIER-3",
        "source": "عتبة مجمعة شائعة في مراجع تخزين الأعلاف لبدء النشاط الفطري النشط "
                  "المُنتِج للسموم (كلا الشرطين معًا: حرارة + رطوبة).",
    },
}


# ==============================================================================
# SECTION 5 — MYCOTOXIN_SYNERGY_MATRIX (مصفوفة التآزر الفطري)
# ==============================================================================
# ⚠️ تنويه علمي جوهري: التوثيق العلمي أدناه يثبت **اتجاه واتجاهية** التفاعل
# (تآزري/تراكمي) بين كل زوج من السموم — أي أن التعايش المتزامن أسوأ من مجموع
# التأثيرين منفصلين. لا يوجد في الأدبيات المنشورة حتى تاريخ كتابة هذا الملف
# "معامل رقمي معياري" واحد متفق عليه عالميًا لأي زوج من هذه الأزواج. لذلك فإن
# engineering_multiplier في كل بند أدناه هو **تقدير احترازي هندسي (TIER-4)**
# يعكس فقط الاتجاه الموثّق علميًا (تآزري > تراكمي > تعايش شائع)، وليس رقمًا
# مقتبسًا حرفيًا من أي دراسة بعينها. **يتطلب اعتماد الطبيب البيطري/فريق السموم
# المختص قبل استخدامه في قرارات REJECT/APPROVE الفعلية.**
#
# المفاتيح Frozenset (غير مرتّبة) — استخدم get_synergy_factor() أدناه للاستعلام
# بدل الوصول المباشر للقاموس لتفادي مشاكل ترتيب المفتاح.
MYCOTOXIN_SYNERGY_MATRIX = {
    frozenset({"don_ppm", "zearalenone_ppm"}): {
        "interaction": "synergistic",
        "engineering_multiplier": 1.25,
        "evidence": "توثيق نوعي لتآزر DON+ZEN في الخنازير (مخطط التآزر/التراكم المنشور من "
                    "DSM-Firmenich استنادًا لأدبيات Fusarium spp.) وأدلة إضافية من دراسة "
                    "تعرّض متعدد السموم (T-2/DON/FB1) عند جرعات حد EU في دجاج البياض "
                    "أظهرت تأثيرًا تآزريًا على إجهاد الأكسدة (PMC10222800).",
    },
    frozenset({"aflatoxin_ppb", "ochratoxin_ppb"}): {
        "interaction": "additive_to_synergistic",
        "engineering_multiplier": 1.20,
        "evidence": "مراجعة علمية مخصصة لتركيبات الأوكراتوكسين (PMC3847710) توثّق أن أغلب "
                    "خلطات السموم المختبرة التي تشمل OTA مع الأفلاتوكسين أنتجت تأثيرات "
                    "تراكمية إلى تآزرية عبر نماذج تجريبية متعددة.",
    },
    frozenset({"don_ppm", "fumonisin_ppm"}): {
        "interaction": "co-occurrence_common",
        "engineering_multiplier": 1.15,
        "evidence": "تعايش شائع التوثيق في أعلاف الدواجن مع تأثيرات مناعية/معوية إضافية "
                    "عند التعرض المشترك حتى تحت الحدود التنظيمية الفردية لكل سم على حدة "
                    "(Toxins 2025 — broiler subclinical co-exposure study).",
    },
    frozenset({"aflatoxin_ppb", "fumonisin_ppm"}): {
        "interaction": "additive_to_synergistic",
        "engineering_multiplier": 1.20,
        "evidence": "تعايش موثّق بارتباط إحصائي قوي بين الفيومونيسين B1/B3 والأفلاتوكسين "
                    "B1 في مسح واسع لأعلاف أبقار الألبان الصينية (PMC11945585)، ضمن نمط "
                    "عام موثّق لتعايش ≥3 سموم في نفس العينة بمعدل مرتفع.",
    },
}

# العتبة التي يجب أن يبلغها **كلا** السمّين (كنسبة من حده التنظيمي الخاص) قبل
# تفعيل مضاعف التآزر — لا يُفعَّل التآزر لمجرد وجود أثر ضئيل لسم ثانوي. TIER-4.
SYNERGY_TRIGGER_RATIO = 0.5


def get_synergy_factor(toxin_a: str, toxin_b: str) -> dict:
    """
    استعلام آمن عن بيانات التآزر بين سمّين بصرف النظر عن ترتيبهما.
    يُعيد dict فارغ (لا تآزر موثّق) إذا لم يوجد الزوج في المصفوفة، بدل رمي استثناء —
    غياب التوثيق لا يعني بالضرورة غياب الخطر، لكنه لا يبرر افتراض معامل غير موثّق.
    """
    return MYCOTOXIN_SYNERGY_MATRIX.get(frozenset({toxin_a, toxin_b}), {})


# ==============================================================================
# SECTION 6 — دوال وصول حتمية (Deterministic Accessor Helpers)
# ==============================================================================
# دوال بسيطة تفرض قراءة الحدود عبر واجهة موحّدة بدل الوصول المباشر للقواميس في
# أكثر من مكان بالنظام — أي تعديل مستقبلي لبنية القاموس يحتاج تعديل هنا فقط.

def get_species_limit(species_key: str, toxin_key: str, kind: str = "accept_limit"):
    """
    يُعيد accept_limit أو reject_limit لسم مُحدَّد ضمن قطاع مُحدَّد.
    `kind` يجب أن تكون "accept_limit" أو "reject_limit". يُعيد None إذا لم يوجد
    القطاع أو السم في SPECIES_REGULATORY_LIMITS (بدل قيمة افتراضية صامتة قد تُخفي خطأ إدخال).
    """
    species_row = SPECIES_REGULATORY_LIMITS.get(species_key)
    if species_row is None:
        return None
    toxin_row = species_row.get(toxin_key)
    if toxin_row is None:
        return None
    return toxin_row.get(kind)


def get_stage_for_age(species_key: str, age_days) -> str:
    """
    يُعيد مفتاح المرحلة العمرية (مثال: "starter") المطابقة لعمر مُحدَّد بالأيام
    ضمن قطاع مُحدَّد. يُعيد None إذا كان العمر غير معروف أو القطاع غير موجود أو
    لا تُوجد مرحلة مطابقة (نطاقات age_days_min/max التي بها None تُعامَل كمرحلة
    وحيدة تغطي كل الأعمار — راجع بنية FEED_STAGES_CONFIG أعلاه).
    """
    if age_days is None:
        return None
    species_stages = FEED_STAGES_CONFIG.get(species_key, {}).get("stages", {})
    for stage_key, stage_row in species_stages.items():
        stage_min = stage_row.get("age_days_min")
        stage_max = stage_row.get("age_days_max")
        if stage_min is None and stage_max is None:
            return stage_key  # مرحلة واحدة مجمّعة تغطي كل الأعمار لهذا القطاع
        lower_ok = stage_min is None or age_days >= stage_min
        upper_ok = stage_max is None or age_days <= stage_max
        if lower_ok and upper_ok:
            return stage_key
    return None


def is_blending_allowed(species_key: str, age_days=None, stage_key: str = None) -> dict:
    """
    القاعدة القاطعة الوحيدة لأهلية الخلط بناءً على العمر/المرحلة (مستقلة تمامًا
    عن نتيجة معادلة بيرسون الحسابية في محرك الرياضيات — انظر compute_blending_ratio
    في app.py، الذي يستدعي هذه الدالة **قبل** أي حساب نسبة خلط).

    يُعيد: {"allowed": bool, "reason_ar": str}
    منطق الأولوية:
      1) عمر أقل من UNIVERSAL_MIN_BLENDING_AGE_DAYS => ممنوع دائمًا (قاعدة قاطعة).
      2) مرحلة صريحة (stage_key) أو مُستنتَجة من العمر تحمل allow_blending=False => ممنوع.
      3) غير ذلك => مسموح من ناحية العمر/المرحلة (لا يعني هذا وحده اعتماد الخلط —
         باقي شروط الحدود التنظيمية للسموم تُفحص بمعزل عن هذه الدالة).
    """
    if age_days is not None and age_days < UNIVERSAL_MIN_BLENDING_AGE_DAYS:
        return {
            "allowed": False,
            "reason_ar": f"العمر ({age_days} يوم) أقل من الحد الأدنى المطلق للخلط "
                         f"({UNIVERSAL_MIN_BLENDING_AGE_DAYS} يوم) — قاعدة قاطعة بصرف "
                         "النظر عن نتيجة الحساب الرياضي.",
        }

    resolved_stage_key = stage_key or get_stage_for_age(species_key, age_days)
    if resolved_stage_key is not None:
        stage_row = FEED_STAGES_CONFIG.get(species_key, {}).get("stages", {}).get(resolved_stage_key)
        if stage_row is not None and not stage_row.get("allow_blending", True):
            return {
                "allowed": False,
                "reason_ar": f"مرحلة '{stage_row.get('label_ar', resolved_stage_key)}' محظور "
                             "فيها الخلط صراحةً بغض النظر عن العمر بالأيام.",
            }

    return {"allowed": True, "reason_ar": "لا يوجد مانع عمري/مرحلي — الأهلية النهائية للخلط "
                                           "لا تزال تعتمد على فحص الحدود التنظيمية للسموم."}


# ==============================================================================
# SECTION 7 — معايير التحليل التقريبي (Proximate Analysis Standards)
# ==============================================================================
# مرجع حتمي ثانٍ مستقل عن SPECIES_REGULATORY_LIMITS: بينما الأخير يحدد حدود السموم
# الفطرية (مخاطر سلامة حيوية/حدّية Accept/Reject)، هذا القسم يحدد "نسب التركيب
# الغذائي" (Proximate Composition) المرجعية لكل قطاع — ما تحتاجه العليقة من بروتين
# ودهن وألياف ورماد لتحقيق الأداء الإنتاجي المستهدف، بصرف النظر تمامًا عن وجود
# تلوث بالسموم من عدمه. التطبيقان (تدقيق السموم وتدقيق البروكسيمات) يستخدمان نفس
# القطاعات الخمسة (SPECIES_LABELS_AR) لكن بجدولَي حدود منفصلين تمامًا.
#
# ⚠️ تغطية جزئية مقصودة: هذا القسم يغطي 4 من القطاعات الخمسة فقط — poultry_broiler،
# cattle_dairy، cattle_beef، aquaculture. "poultry_layer" (دواجن بياض) غير مُدرَج هنا
# عمدًا: لم تُقدَّم أي بيانات مرجعية موثّقة لمتطلبات البروكسيمات الخاصة بالبياض عند
# إعداد هذا القسم. أي محاولة لاستخدام مفتاح "poultry_layer" في هذا القاموس يجب أن
# تُعامَل في proximate_engine.py كـ "غير مدعوم بعد" بوضوح — لا قيمة افتراضية ولا
# تخمين بالاستعارة من مرحلة أخرى. راجع get_proximate_standard() أدناه.
#
# بنية كل صف مرحلة: نفس حقول SPECIES_REGULATORY_LIMITS من حيث الانضباط (accept/
# reject/evidence_tier/source)، لكن بدلالة مختلفة هنا: "min"/"max" يحددان المدى
# المرجعي المقبول للعنصر الغذائي (لا حدًّا للرفض الصحي كما في السموم)؛ غياب "min"
# يعني "لا حد أدنى إلزامي موثَّق" وغياب "max" يعني العكس — لا يُفترض صفر أو ما
# لا نهاية ضمنيًا في أي من الحالتين.
#
# ⚠️ "is_egyptian_standard_limit": True (حقل اختياري، غيابه يعني False) يُعلَّم به
# حصريًا الصفوف المُشتقة مباشرة من [EOS1466] (المواصفة القياسية المصرية الرسمية).
# هذا الحقل — لا مطابقة نصية على كلمة "EOS1466" داخل "source" — هو ما يقرر في
# proximate_engine.py متى تُصنَّف مخالفة حد ما كـ"🔴 مرفوضة تمامًا لمخالفة المواصفة
# القياسية المصرية" حرفيًا (النص المطلوب)، تمييزًا عن مخالفة حد من مصدر آخر (NRC/Ross
# 308/NASEM) التي تُصنَّف 🟡 ما لم تتجاوز عتبة شدة داخلية صريحة (راجع التوثيق في
# proximate_engine.py لمنطق الإشارة الثلاثية الكامل).
SPECIES_PROXIMATE_STANDARDS = {
    "poultry_broiler": {
        "stages": {
            "starter": {  # 0-10 يوم — يطابق حدود starter في FEED_STAGES_CONFIG
                "label_ar": "بادي (Starter)",
                "crude_protein_pct": {
                    "min": 23.0, "max": None, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أدنى صارم 23% للبادي. [COBB500-N] يقبل "
                              "21.5%-22% لنفس المرحلة — اعتُمدت قيمة Ross 308 الأكثر "
                              "تحفظًا كحد أدنى مرجعي موحّد.",
                },
                "ether_extract_pct": {
                    "min": None, "max": None, "reference": 3.5, "evidence_tier": "TIER-3",
                    "source": "[ROSS308] لا حد أدنى إلزامي في الكتالوج الرسمي؛ 3.5% قيمة "
                              "استرشادية شائعة في علائق البادي التجارية — تُعرَض كمرجع "
                              "لا كحد يُحتسَب عليه قرار 🔴/🟡/🟢.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 3.0, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أقصى 3.0% لمرحلة البادي.",
                },
                "ash_pct": {
                    "min": None, "max": 5.0, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أقصى 5.0%؛ يرتفع لـ 6.0% فقط عند إضافة مسحوق "
                              "اللحم والعظام — العليقة النباتية بالكامل تقف عند 5.0%.",
                },
            },
            "grower": {  # 11-24 يوم
                "label_ar": "نامي (Grower)",
                "crude_protein_pct": {
                    "min": 21.5, "max": None, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أدنى 21.5%. [COBB500-N] يكتفي بـ 20% — اعتُمدت "
                              "قيمة Ross 308 الأكثر تحفظًا.",
                },
                "ether_extract_pct": {
                    "min": None, "max": None, "reference": 4.0, "evidence_tier": "TIER-3",
                    "source": "[ROSS308] قيمة استرشادية 4.0% — مرجعية لا حدّية.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 3.5, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أقصى 3.5% لمرحلة النامي.",
                },
                "ash_pct": {
                    "min": None, "max": 5.0, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أقصى 5.0% لمرحلة النامي.",
                },
            },
            "finisher": {  # 25 يوم فأكثر
                "label_ar": "ناهي (Finisher)",
                "crude_protein_pct": {
                    "min": 19.5, "max": None, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أدنى 19.5%. [COBB500-N] يكتفي بـ 18.5% — اعتُمدت "
                              "قيمة Ross 308 الأكثر تحفظًا.",
                },
                "ether_extract_pct": {
                    "min": None, "max": None, "reference": 4.5, "evidence_tier": "TIER-3",
                    "source": "[ROSS308] قيمة استرشادية 4.5% — مرجعية لا حدّية.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 4.0, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أقصى 4.0% لمرحلة الناهي.",
                },
                "ash_pct": {
                    "min": None, "max": 4.5, "evidence_tier": "TIER-1",
                    "source": "[ROSS308] حد أقصى 4.5% لمرحلة الناهي.",
                },
            },
        },
    },
    "cattle_beef": {
        "stages": {
            "growing": {
                "label_ar": "نمو (Growing)",
                "crude_protein_pct": {
                    "min": 14.0, "max": None, "evidence_tier": "TIER-1",
                    "source": "[NRC2016] 14% على أساس المادة الجافة 100% DM لمرحلة النمو.",
                },
                "ether_extract_pct": {
                    "min": 2.5, "max": 5.0, "evidence_tier": "TIER-2",
                    "source": "[NRC2016] حد أدنى 2.5% في العليقة المركزة؛ حد أقصى آمن 5.0% "
                              "لحماية ميكروبات الكرش من اضطراب الهضم الدهني — قيمة إدارة "
                              "مخاطر مبنية على ممارسات تغذية الأبقار القياسية.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 15.0, "evidence_tier": "TIER-1",
                    "is_egyptian_standard_limit": True,
                    "source": "[EOS1466] حد أقصى صارم 15% للأعلاف المصنَّعة المركَّزة.",
                },
                "ash_pct": {
                    "min": None, "max": 9.0, "evidence_tier": "TIER-1",
                    "is_egyptian_standard_limit": True,
                    "source": "[EOS1466] حد أقصى 9.0%.",
                },
            },
            "finishing": {
                "label_ar": "تسمين نهائي (Finishing)",
                "crude_protein_pct": {
                    "min": 12.0, "max": None, "evidence_tier": "TIER-1",
                    "source": "[NRC2016] 12% على أساس المادة الجافة 100% DM لمرحلة التسمين "
                              "النهائي — أقل من مرحلة النمو (14%) لأن معدل الزيادة الوزنية "
                              "اليومية المستهدف أقل نسبيًا من البروتين وأعلى من الطاقة.",
                },
                "ether_extract_pct": {
                    "min": 2.5, "max": 5.0, "evidence_tier": "TIER-2",
                    "source": "[NRC2016] نفس مدى مرحلة النمو — لا تمييز موثَّق بالمصدر بين "
                              "المرحلتين لهذا العنصر تحديدًا.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 15.0, "evidence_tier": "TIER-1",
                    "is_egyptian_standard_limit": True,
                    "source": "[EOS1466] حد أقصى 15% — نفس حد مرحلة النمو (المواصفة المصرية "
                              "لا تفرّق بين مراحل اللحم بالنسبة لهذا الحد).",
                },
                "ash_pct": {
                    "min": None, "max": 9.0, "evidence_tier": "TIER-1",
                    "is_egyptian_standard_limit": True,
                    "source": "[EOS1466] حد أقصى 9.0%.",
                },
            },
        },
    },
    "cattle_dairy": {
        "stages": {
            "lactating": {  # مرحلة واحدة مجمّعة — يطابق بنية FEED_STAGES_CONFIG لنفس القطاع
                "label_ar": "حلاّب (High Lactation)",
                "crude_protein_pct": {
                    "min": 16.5, "max": 17.5, "evidence_tier": "TIER-1",
                    "source": "[NASEM2021] 16.5%-17.5% حسب كمية إدرار اللبن المستهدفة — "
                              "اعتُمد المدى كاملًا (لا رقم واحد) لأن القيمة الدقيقة تتبع "
                              "مستوى الإنتاج الفردي للقطيع، وهذا خارج نطاق هذه الأداة.",
                },
                "ether_extract_pct": {
                    "min": 3.0, "max": 5.5, "evidence_tier": "TIER-1",
                    "source": "[NASEM2021] حد أدنى 3.0%، حد أقصى 5.5% في العلف المركز.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 12.0, "evidence_tier": "TIER-1",
                    "is_egyptian_standard_limit": True,
                    "source": "[EOS1466] حد أقصى 12% في العلف المركز لتسمين الحليب.",
                },
                "ash_pct": {
                    "min": None, "max": 8.5, "evidence_tier": "TIER-1",
                    "is_egyptian_standard_limit": True,
                    "source": "[EOS1466] حد أقصى 8.5%.",
                },
            },
        },
    },
    "aquaculture": {
        "stages": {
            "fingerlings": {  # حتى وزن 20 جرام
                "label_ar": "إصبعيات (Fingerlings، حتى 20 جم)",
                "crude_protein_pct": {
                    "min": 35.0, "max": None, "evidence_tier": "TIER-1",
                    "source": "[NRC2011] 35% كحد أدنى للإصبعيات؛ يرتفع حتى 40% في العلائق "
                              "البادئة جدًا لأوزان أقل من 1 جرام (حالة خاصة غير مُفعَّلة هنا "
                              "افتراضيًا).",
                },
                "ether_extract_pct": {
                    "min": 6.0, "max": 8.0, "evidence_tier": "TIER-1",
                    "source": "[NRC2011] 6.0%-8.0% — الأسماك تعتمد على الدهون كمصدر رئيسي "
                              "للطاقة أكثر من الدواجن/المجترات.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 4.0, "evidence_tier": "TIER-1",
                    "source": "[NRC2011] حد أقصى 4.0% لمرحلة الإصبعيات.",
                },
                "ash_pct": {
                    "min": None, "max": 8.5, "evidence_tier": "TIER-1",
                    "source": "[NRC2011] حد أقصى 8.5%.",
                },
            },
            "grow_out": {  # من 20 جرام حتى التسويق
                "label_ar": "تسمين (Grow-out، من 20 جم حتى التسويق)",
                "crude_protein_pct": {
                    "min": 30.0, "max": 32.0, "evidence_tier": "TIER-2",
                    "source": "[NRC2011] 30%-32% حسب كثافة التربية — مدى وليس رقمًا واحدًا "
                              "لأن الكثافة عامل تشغيلي لا تضبطه هذه الأداة.",
                },
                "ether_extract_pct": {
                    "min": 5.0, "max": 6.0, "evidence_tier": "TIER-1",
                    "source": "[NRC2011] 5.0%-6.0% لمرحلة التسمين.",
                },
                "crude_fiber_pct": {
                    "min": None, "max": 5.0, "evidence_tier": "TIER-2",
                    "source": "[NRC2011] حد أقصى أساسي 5.0%؛ بعض التراكيب التجارية تسمح "
                              "حتى 6% — اعتُمدت القيمة الأكثر تحفظًا (5.0%) كحد مرجعي "
                              "افتراضي لقرار 🟡/🔴.",
                },
                "ash_pct": {
                    "min": None, "max": 7.0, "evidence_tier": "TIER-1",
                    "source": "[NRC2011] حد أقصى 7.0%.",
                },
            },
        },
    },
    # "poultry_layer": غير مُدرَج عمدًا — راجع الملاحظة أعلى هذا القاموس.
}

# معامل تحويل نسبة النيتروجين إلى بروتين خام: CP% = Nitrogen% × 6.25 — المعامل
# القياسي العام المستخدم في كيمياء الأعلاف (يفترض أن البروتين النموذجي ~16% نيتروجين
# بالوزن؛ 1/0.16 = 6.25). TIER-1: ثابت كيميائي عام متفق عليه عالميًا، وليس رقمًا
# خاصًا بقطاع أو مصدر تنظيمي بعينه.
N_TO_PROTEIN_FACTOR = 6.25


def get_proximate_standard(species_key: str, stage_key: str) -> dict:
    """
    يُعيد صف معايير البروكسيمات (بروتين/دهن/ألياف/رماد) لمرحلة مُحدَّدة ضمن قطاع
    مُحدَّد من SPECIES_PROXIMATE_STANDARDS، أو None إذا لم تكن هذه التركيبة
    (قطاع × مرحلة) موثَّقة بعد — بما في ذلك القطاعات غير المغطاة إطلاقًا مثل
    "poultry_layer" حاليًا. لا قيمة افتراضية صامتة ولا استعارة من مرحلة أخرى.
    """
    species_row = SPECIES_PROXIMATE_STANDARDS.get(species_key)
    if species_row is None:
        return None
    return species_row.get("stages", {}).get(stage_key)


def get_proximate_stage_options(species_key: str) -> dict:
    """
    يُعيد {stage_key: label_ar} لكل المراحل الموثَّقة لقطاع مُحدَّد — تُستخدم لبناء
    قائمة اختيار المرحلة في الواجهة. dict فارغ لقطاع غير مغطى (مثل poultry_layer).
    """
    species_row = SPECIES_PROXIMATE_STANDARDS.get(species_key)
    if species_row is None:
        return {}
    return {key: row.get("label_ar", key) for key, row in species_row.get("stages", {}).items()}