"""产品用法语义：应用领域（发/肤/口腔）、前后对比主体、步骤图禁止错用上手演示。"""

from __future__ import annotations

import re

HAIR_KW = re.compile(
    r"shampoo|conditioner|hair\s*mask|hair\s*oil|hair\s*serum|leave[\s-]?in|"
    r"capilar|cabello|pelo|tratamiento\s*capilar|hair\s*treatment|anti[\s-]?frizz|"
    r"alisador|alisad[oa]|spray\s+alisador|hair\s+spray|straightening\s+spray|"
    r"liso\s+diamante|baño\s+de\s+brillo|bano\s+de\s+brillo|uso\s+con\s+secador|"
    r"protección\s+térmica|secador|brillo\s+pulido|"
    r"护发|洗发|发膜|润发|护发素|头发|发油|发用|定型|护发喷雾|喷发",
    re.I,
)
# 「浴/沐浴」类误触：西语 baño de brillo = 发丝光泽浴，不是 body wash
NOT_BODY_WASH_KW = re.compile(
    r"baño\s+de\s+brillo|bano\s+de\s+brillo|alisador|capilar|cabello|secador|hair\s+spray",
    re.I,
)
HAIR_STRONG_KW = re.compile(
    r"capilar|cabello|alisador|anti[\s-]?frizz|\bfrizz\b|pelo|hair\s+care|hair\s+spray|"
    r"secador|spray\s+alisador|liso\s+diamante|ba[nñ]o\s+de\s+brillo|"
    r"protecci[oó]n\s+t[eé]rmica|t[eé]rmica\s*230|"
    r"护发|洗发|发膜|护发素|头发|straightening\s+spray|tratamiento\s+capilar",
    re.I,
)
BODY_WASH_STRONG_KW = re.compile(
    r"body\s*wash|shower\s*gel|gel\s*de\s*ducha|沐浴露|沐浴啫喱",
    re.I,
)
# 发丝转化描述（故意不含裸词 "hair"，避免沐浴露淋浴文案误伤）
HAIR_TRANSFORM_KW = re.compile(
    r"hair\s+(strand|strands|care|mask|oil|serum|frizz|shine|texture)|\bstrands?\b|"
    r"frizz|frizzy|scalp|cabello|pelo|毛躁|发丝|发质|发梢|护发|干枯发|damaged\s+hair",
    re.I,
)
SKIN_TRANSFORM_KW = re.compile(
    r"facial|cheek|forehead|face\s*skin|complexion|glowing\s*skin|暗沉|面部|脸颊|洁面(?!发)",
    re.I,
)
BODY_SKIN_TRANSFORM_KW = re.compile(
    r"shower\s*skin|body\s*skin|arm\s*skin|foam\s*lather|dry\s*skin|沐浴露|淋浴",
    re.I,
)
ORAL_KW = re.compile(r"toothpaste|tooth\s*brush|(?<![A-Za-z])oral\b|dental|牙膏|美白牙|口腔", re.I)
BODY_BATH_KW = re.compile(
    r"body\s*wash|shower\s*gel|bath\s*gel|shower\s*cream|gel\s*de\s*ducha|"
    r"jab[oó]n\s*l[ií]quido|body\s*cleanser|沐浴露|沐浴|洗浴|淋浴",
    re.I,
)
HAND_WASH_KW = re.compile(
    r"洗手液|洗手皂|hand\s*wash|hand\s*soap|liquid\s*hand\s*soap|"
    r"jab[oó]n\s+(de|para)\s+manos|jab[oó]n\s+l[ií]quido\s+de\s+manos",
    re.I,
)
HAND_BODY_KW = re.compile(
    r"hand\s*cream|hand\s*lotion|body\s*lotion|body\s*milk|护手霜|身体乳", re.I
)
NAIL_FUNGUS_KW = re.compile(
    r"甲癣|甲癖|灰指甲|灰甲|onycho|nail\s*fungus|fungal\s*nail|toenail|"
    r"hongo\s+de\s+la\s+u[nñ]a|u[nñ]a\s+con\s+hongo|antimic",
    re.I,
)
DEODORANT_KW = re.compile(
    r"deodorant|anti[\s-]?perspirant|desodorante|antitranspirante|"
    r"odor\s*protection|odor\s*control|anti[\s-]?odor|"
    r"underarm|armpit|axila|除臭|止汗|腋下|腋窝",
    re.I,
)
SPRAY_FORM_KW = re.compile(
    r"\bspray\b|aerosol|喷雾|bruma|atomizador|\bmist\b",
    re.I,
)
SKIN_FACE_KW = re.compile(
    r"(?<!hair\s)(?<!hair-)serum|facial\s*cleanser|face\s*cleanser|moisturizer|face\s*cream|"
    r"洁面(?!发)|精华(?!发)|面霜|护肤|facial(?!\s*hair)",
    re.I,
)
FACE_EXFOL_KW = re.compile(
    r"exfoli|cutis|piel\s+radiante|去角质|角质",
    re.I,
)
BODY_SCRUB_KW = re.compile(
    r"corporal|body\s*scrub|身体磨砂|磨砂沐浴",
    re.I,
)
WEARABLE_KW = re.compile(
    r"围巾|丝巾|披肩|围脖|头巾|scarf|shawl|bufanda|pa[nñ]uelo|hijab|pashmina",
    re.I,
)
HOME_CLEAN_KW = re.compile(
    r"toilet|toilet\s*bowl|bathroom\s*clean|bowl\s*clean|drain\s*clean|"
    r"bleach\s*clean|sanitiz|disinfect|rim\s*block|洁厕|马桶|厕所清洁剂|卫生间清洁|"
    r"limpieza\s*de\s*baño|wc\s*clean",
    re.I,
)

ZONES_REQUIRE_MODEL: frozenset[str] = frozenset(
    {"hair", "body_bath", "oral", "skin_face", "body_hand", "body_deo", "nail_fungus", "hand_wash"}
)


def is_facial_exfoliation(text: str) -> bool:
    """去角质且部位是脸。身体磨砂和除臭不走这条。"""
    blob = text or ""
    if BODY_SCRUB_KW.search(blob) or DEODORANT_KW.search(blob):
        return False
    return bool(FACE_EXFOL_KW.search(blob))


def is_body_scrub(text: str) -> bool:
    blob = text or ""
    if DEODORANT_KW.search(blob):
        return False
    return bool(BODY_SCRUB_KW.search(blob))


def attach_package_hints(analysis: dict, attachments) -> dict:
    """识图失败时仍用上传文件名，避免护发喷雾被当成未知产品。"""
    if not isinstance(analysis, dict):
        analysis = {}
    else:
        analysis = dict(analysis)
    names: list[str] = []
    for att in attachments or []:
        if att is None:
            continue
        original = str(getattr(att, "original_name", "") or "").strip()
        file_obj = getattr(att, "file", None)
        stored = str(getattr(file_obj, "name", "") or "").strip() if file_obj is not None else ""
        if original:
            names.append(original)
        if stored and stored not in original:
            names.append(stored.rsplit("/", 1)[-1])
    hint = " ".join(names).strip()
    if hint:
        analysis["upload_name_hint"] = hint[:300]
    return analysis


def zone_requires_model(zone: str) -> bool:
    z = (zone or "").strip()
    if z == "home_clean":
        return False
    if z == "generic":
        return True
    return z in ZONES_REQUIRE_MODEL


FRAME4_MODEL_MANDATE_BASE = (
    "FRAME 4 MODEL REQUIRED — A photorealistic person must appear showing the before→after "
    "transformation while using or right after using the hero SKU (same application zone). "
    "Single photograph with visible problem state vs improved state on the person — NOT product-only still life. "
    "Zero comparison text labels on image."
)

FRAME4_MODEL_BY_ZONE: dict[str, str] = {
    "hair": (
        "Model from back or 3/4 side — transformation ON HAIR STRANDS ONLY: dull frizzy hair vs smooth shiny hair; "
        "SKU in hand or on vanity; FORBIDDEN cheek/forehead skin glow compare, facial serum skincare, face cream demo."
    ),
    "body_bath": "Model in shower — dull dry skin vs smooth skin with foam lather; torso/shoulders visible; SKU on shelf.",
    "oral": "Model smile close-up — dull/yellowed teeth vs brighter smile; toothpaste SKU visible.",
    "skin_face": "Model face — tired dull skin vs glowing hydrated skin; skincare SKU on vanity.",
    "body_hand": "Model hands/forearms — dry rough skin vs soft moisturized skin; lotion SKU visible.",
    "hand_wash": (
        "Close-up of the SAME hands. LEFT: many small visible germ specks on the skin. "
        "RIGHT: those specks are gone and the hands look clear. "
        "The bottle is an exact copy of the reference on BOTH halves: same outline, pump, cap, and label. "
        "Do not stretch or melt the bottle."
    ),
    "nail_fungus": (
        "Hand or foot close enough to read the NAIL. Product touches the nail plate. "
        "Before: yellowed, stained, rough-looking nail. After: the same nail looks clearer and more cared for. "
        "FORBIDDEN: face cream, spraying the face, hair application, and any promise that the fungus is cured."
    ),
    "body_deo": (
        "Model torso and raised arm — product touches the UNDERARM only; "
        "before: odor-worry / damp underarm feel; after: fresh protected underarm. "
        "FORBIDDEN: cream or spray on cheeks, forehead, or any facial-mist pose."
    ),
    "generic": (
        "Before and after of the RESULT of use on the surface or body part this product treats. "
        "The same package is visible on both sides. "
        "FORBIDDEN: one side without the product and the other side holding it."
    ),
}

FRAME4_OBJECT_MANDATE_BASE = (
    "FRAME 4 OBJECT/SURFACE COMPARISON — NO human model required. "
    "Show before→after on the target surface or object the product cleans/treats (toilet bowl, sink, floor, etc.). "
    "Hero SKU visible; single-photo visual contrast only; zero comparison text labels."
)

FRAME4_OBJECT_BY_ZONE: dict[str, str] = {
    "home_clean": (
        "Toilet or bathroom surface: left/stained dirty bowl or tile vs right/sparkling clean white sanitary result; "
        "cleaner bottle on rim or shelf — NO person, NO skin compare, NO hair compare."
    ),
}

ZONE_PROFILES: dict[str, dict] = {
    "hair": {
        "label_en": "hair care (scalp and hair strands)",
        "before": "frizzy, dry, dull, tangled or damaged hair",
        "after": "smooth, shiny, manageable, healthier-looking hair",
        "before_after_visual_en": (
            "ONE photograph with visible hair transformation: left/muted side shows dull frizzy damaged hair; "
            "right/brighter side shows smooth glossy hair; same hero hair-care SKU on bathroom shelf or in hand "
            "near hair — NOT hand-skin moisturization demo, NOT spraying product on palms only."
        ),
        "usage_steps_en": [
            "wet hair in shower or damp towel-dried hair",
            "dispense product onto palm then work through mid-lengths to ends (or apply directly to hair)",
            "massage into hair; rinse or leave-in per product type",
        ],
        "in_use_en": (
            "Model applies product to HAIR only (strands, ends, or scalp). "
            "If it is a spray, the nozzle points at the hair and the mist lands on the strands. "
            "A face may appear in profile, but the product never touches the face."
        ),
        "forbidden_en": (
            "facial mist, spraying cheeks or forehead, face cream, closed-eye face spray, "
            "hand moisturizer demo, product sprayed only on the back of the hand"
        ),
        "frame4_split_en": (
            "Zone HAIR — frizzy dull hair vs glossy smooth hair with hero hair SKU; "
            "NOT body shower foam, NOT arm skin lotion compare."
        ),
    },
    "oral": {
        "label_en": "oral care (teeth and mouth)",
        "before": "yellowed teeth, dull smile, bad breath worry",
        "after": "brighter smile, fresher breath confidence",
        "before_after_visual_en": (
            "Smile/teeth or mouth freshness transformation with SAME toothpaste tube visible; "
            "split lighting dull vs bright — NOT kitchen gadgets."
        ),
        "usage_steps_en": [
            "squeeze pea-size on brush",
            "brush teeth thoroughly",
            "rinse and smile",
        ],
        "in_use_en": "Brushing teeth with toothpaste; mouth/smile visible; product on brush.",
        "forbidden_en": "hair application, body lotion, spray on hands",
        "frame4_split_en": "Zone ORAL — dull yellowed smile vs brighter whiter teeth with toothpaste SKU.",
    },
    "skin_face": {
        "label_en": "facial skincare",
        "before": "dull tired skin, uneven tone",
        "after": "glowing hydrated skin",
        "before_after_visual_en": "Facial skin before/after with SKU on vanity; same person cheek texture contrast.",
        "usage_steps_en": ["cleanse", "apply serum/cream to face", "pat until absorbed"],
        "in_use_en": "Applying to face skin zones — cheeks, forehead — not hair.",
        "forbidden_en": "applying to hair or teeth",
        "frame4_split_en": "Zone FACE — dull tired facial skin vs glowing hydrated cheeks with skincare SKU.",
    },
    "body_bath": {
        "label_en": "body wash / shower gel (skin in shower)",
        "before": "dull dry tired skin, flat wash without rich lather, not feeling fresh",
        "after": "smooth radiant clean skin, rich foam lather, fresh hydrated after-shower glow",
        "before_after_visual_en": (
            "ONE shower/bathroom photograph: left/muted side shows dull dry skin on arm, shoulder or back "
            "with weak flat soap; right/bright side shows smooth hydrated skin with rich white foam lather "
            "and hero body-wash bottle on shower shelf or in hand — NOT hair frizz transformation, "
            "NOT shampoo on scalp, NOT face-only skincare jar."
        ),
        "frame4_split_en": (
            "Zone BODY BATH — visible skin transformation in shower context: dull dry arm/shoulder/back "
            "vs smooth clean skin with rich foam lather; hero body-wash SKU visible; "
            "FORBIDDEN hair-strand before/after or scalp demo."
        ),
        "usage_steps_en": [
            "wet skin under shower",
            "dispense gel on puff or palm, lather on body",
            "rinse — skin feels fresh and soft",
        ],
        "in_use_en": (
            "Lather on BODY skin (arms, shoulders, back, legs) in shower or bath; foam visible on skin; "
            "product bottle on shelf or in hand; NOT applying to hair scalp as shampoo."
        ),
        "forbidden_en": (
            "hair frizz before/after, shampoo scalp routine, hair styling, dental smile compare, "
            "face cream on cheeks only without body context"
        ),
    },
    "nail_fungus": {
        "label_en": "nail care for a discolored or fungus-prone nail",
        "before": "yellowed, stained, rough-looking nail the customer wants to hide",
        "after": "the nail looks clearer, cleaner, and more cared for",
        "before_after_visual_en": (
            "ONE photograph of the nail: dull yellowed nail versus a clearer, more even-looking nail. "
            "Hero product applied on the nail plate. Not the face, not the hair."
        ),
        "frame4_split_en": (
            "Zone NAIL — the nail is the only subject. No face cream, no hair, no cure claim."
        ),
        "usage_steps_en": [
            "clean the nail",
            "apply the product on the nail plate",
            "the nail looks more cared for",
        ],
        "in_use_en": (
            "Apply on the NAIL only. Show the nail plate, a hand or a foot. "
            "The customer wants the nail to look clearer and less stained. "
            "Do not promise a medical cure."
        ),
        "forbidden_en": (
            "face cream, facial mist, hair spray, spraying the face, "
            "cure claim, guaranteed fungus removal"
        ),
    },
    "body_deo": {
        "label_en": "deodorant for underarms / body",
        "before": "underarm odor worry, damp unprotected underarm",
        "after": "fresh protected underarm, confident all day",
        "before_after_visual_en": (
            "ONE photograph: raised arm, deodorant stick or cream on the UNDERARM. "
            "Same person, product visible at the armpit — NOT a face-cream close-up, NOT a facial mist."
        ),
        "frame4_split_en": (
            "Zone DEODORANT — underarm only. Product touches the armpit. "
            "FORBIDDEN face, cheeks, forehead, facial spray."
        ),
        "usage_steps_en": [
            "raise the arm",
            "apply stick or cream to the underarm",
            "lower the arm — fresh and protected",
        ],
        "in_use_en": (
            "Apply the deodorant to the UNDERARM or inner upper arm. "
            "The stick, cream, or spray touches body skin at the armpit. "
            "A face may be in frame, but the product is never on the face."
        ),
        "forbidden_en": (
            "face cream, cheek application, forehead application, facial mist, "
            "spraying the face, skincare on the face"
        ),
    },
    "body_hand": {
        "label_en": "body or hand care",
        "before": "dry rough hands or dry body skin",
        "after": "soft moisturized skin",
        "before_after_visual_en": "Hand or arm skin texture before/after with lotion bottle.",
        "frame4_split_en": (
            "Zone BODY/HAND — dry rough skin texture vs soft moisturized skin on hands or arm "
            "with lotion bottle visible; NOT hair transformation."
        ),
        "usage_steps_en": ["dispense", "massage into hands or body skin", "daily use"],
        "in_use_en": "Massage into hands or body skin — appropriate for this category.",
        "forbidden_en": "shampoo on hair if product is hand cream",
    },
    "home_clean": {
        "label_en": "home/bathroom cleaning (toilet, surfaces)",
        "before": "stained dirty toilet bowl, limescale, dull unsanitary bathroom surface",
        "after": "sparkling clean white toilet, fresh sanitary bathroom, visible cleanliness",
        "before_after_visual_en": (
            "ONE bathroom photograph: stained/discolored toilet bowl or tile (muted) vs gleaming clean white "
            "sanitary result (bright); hero cleaner SKU on toilet tank or floor — NO human model, "
            "NO skin lotion compare, NO hair transformation."
        ),
        "frame4_split_en": FRAME4_OBJECT_BY_ZONE["home_clean"],
        "usage_steps_en": [
            "apply cleaner to bowl or surface",
            "wait and scrub/brush",
            "rinse — sparkling clean result",
        ],
        "in_use_en": "Product applied to toilet bowl or bathroom surface; brush/bottle in scene; no face needed.",
        "forbidden_en": (
            "human model portrait, skin before/after on body, hair shampoo demo, face skincare"
        ),
    },
    "hand_wash": {
        "label_en": "hand wash on the hands",
        "before": "hands covered with many small visible germ specks",
        "after": "the same hands clear, with those germ specks gone",
        "before_after_visual_en": (
            "ONE photo, same hands and the same unaltered bottle. "
            "LEFT: germ specks on the skin. RIGHT: the specks are gone. "
            "Copy the reference bottle outline, pump, cap, and label. Do not stretch or melt it."
        ),
        "frame4_split_en": (
            "Hand wash: germ specks present versus germ specks gone. "
            "Bottle shape matches the reference on both sides."
        ),
        "usage_steps_en": ["show germ specks on the hands", "use this hand wash", "the specks are gone"],
        "in_use_en": "The bottle matches the reference. The contrast is germ specks on the hands versus clear hands.",
        "forbidden_en": "stretched bottle, melted pump, redesigned label, hair treatment, face cream",
    },
    "wearable": {
        "label_en": "scarf, shawl, or clothing worn on the outfit",
        "before": "the outfit without this scarf or garment",
        "after": "the same outfit wearing this exact item",
        "before_after_visual_en": (
            "ONE photo: left, neck and outfit without the item; right, the same person wearing "
            "the scarf or garment from the reference. Not a hair-smoothing treatment."
        ),
        "frame4_split_en": "Wearable item on the outfit. Forbidden: frizzy hair versus smooth hair.",
        "usage_steps_en": ["show the item", "wear it on the outfit"],
        "in_use_en": "The scarf or garment is worn. Hair may be visible but is not the product.",
        "forbidden_en": "frizzy hair versus smooth hair, shampoo, hair serum, face cream",
    },
    "generic": {
        "label_en": "the object shown in the reference photos",
        "before": "the condition of the body part or surface named on the package, before use",
        "after": "that same body part or surface after use",
        "before_after_visual_en": (
            "ONE photo of the attached product. The comparison is the use of this exact product. "
            "The background and the package shape stay the same."
        ),
        "usage_steps_en": ["show the attached product", "use it for the purpose on its package"],
        "in_use_en": "Use the attached product for the purpose shown on its package.",
        "forbidden_en": "a second product category in the same comparison",
        "frame4_split_en": "One comparison only: the use of the attached product.",
    },
}


def _packaging_truth_blob(analysis: dict) -> str:
    """瓶身/品名/品类/主功效——判定「本品到底是什么」时优先于场景叙述。"""
    return " ".join(
        [
            str(analysis.get("label_text_exact") or ""),
            str(analysis.get("product_name_en") or ""),
            str(analysis.get("product_name_es") or ""),
            str(analysis.get("product_name_zh") or ""),
            str(analysis.get("category") or ""),
            str(analysis.get("primary_function") or "")[:500],
            str(analysis.get("upload_name_hint") or ""),
            str(analysis.get("package_ocr_text") or "")[:800],
        ]
    )


def _marketing_truth_blob(analysis: dict) -> str:
    """与首图/图3 同源：识图卖点 + 西语标题（识图漏抄包装时仍能判品类）。"""
    return " ".join(
        [
            _packaging_truth_blob(analysis),
            " ".join(_text_list(analysis.get("spanish_headlines"))[:10]),
            " ".join(_text_list(analysis.get("key_selling_points"))[:10]),
            str(analysis.get("identity_lock_en") or "")[:500],
        ]
    )


def _analysis_evidence_blob(analysis: dict, user_prompt: str = "") -> str:
    from generation.services.product_listing_narrative import is_meta_listing_instruction

    prompt_slice = user_prompt[:500] if not is_meta_listing_instruction(user_prompt) else ""
    return " ".join(
        [
            str(analysis.get("category") or ""),
            str(analysis.get("product_name_en") or ""),
            str(analysis.get("product_name_es") or ""),
            str(analysis.get("primary_function") or ""),
            str(analysis.get("visual_identity") or "")[:800],
            str(analysis.get("label_text_exact") or "")[:600],
            str(analysis.get("identity_lock_en") or "")[:400],
            str(analysis.get("before_use_state") or ""),
            str(analysis.get("after_use_state") or ""),
            str(analysis.get("transformation_subject_en") or ""),
            " ".join(str(x) for x in (analysis.get("key_selling_points") or [])[:8]),
            " ".join(str(x) for x in (analysis.get("pain_points") or [])[:6]),
            " ".join(str(x) for x in (analysis.get("usage_scenarios") or [])[:6]),
            prompt_slice,
        ]
    )


def _packaging_implies_hair(pack: str) -> bool:
    return bool(HAIR_KW.search(pack) or HAIR_STRONG_KW.search(pack))


def _decisive_zone_from_marketing(analysis: dict) -> str | None:
    """强信号一票否决：护发喷雾不会被「piel/brillo」拐到护肤。"""
    market = _marketing_truth_blob(analysis)
    if DEODORANT_KW.search(market):
        return "body_deo"
    hair = _packaging_implies_hair(market)
    bath = bool(BODY_WASH_STRONG_KW.search(market)) and not NOT_BODY_WASH_KW.search(market)
    if hair and not bath:
        return "hair"
    if bath and not hair:
        return "body_bath"
    if hair and bath:
        if HAIR_STRONG_KW.search(market):
            return "hair"
        return "body_bath"
    return None


def reconcile_application_zone(analysis: dict, user_prompt: str = "") -> str:
    """包装 + 营销文案优先于识图 application_zone 与淋浴场景叙述。"""
    wearable_text = " ".join(
        [
            _marketing_truth_blob(analysis),
            _packaging_truth_blob(analysis),
            user_prompt or "",
        ]
    )
    if WEARABLE_KW.search(wearable_text):
        return "wearable"
    if HAND_WASH_KW.search(wearable_text):
        return "hand_wash"
    if DEODORANT_KW.search(wearable_text):
        return "body_deo"
    if is_facial_exfoliation(wearable_text) and not _packaging_implies_hair(wearable_text):
        return "skin_face"
    decisive = _decisive_zone_from_marketing(analysis)
    if decisive:
        return decisive
    market = _marketing_truth_blob(analysis)
    pack_zone = _zone_from_packaging_truth(analysis)
    if pack_zone:
        return pack_zone
    if _packaging_implies_hair(market):
        return "hair"
    pack = _packaging_truth_blob(analysis)
    if _packaging_implies_body_wash(pack) or (
        BODY_BATH_KW.search(pack) and not NOT_BODY_WASH_KW.search(market)
    ):
        return "body_bath"
    return resolve_application_zone(analysis, user_prompt)


def _packaging_implies_body_wash(pack: str) -> bool:
    if NOT_BODY_WASH_KW.search(pack):
        return False
    return bool(BODY_BATH_KW.search(pack)) and not _packaging_implies_hair(pack)


def _zone_from_packaging_truth(analysis: dict) -> str | None:
    """包装 + 西语卖点优先：本品功效类别（不读淋浴场景叙述）。"""
    pack = _marketing_truth_blob(analysis)
    if WEARABLE_KW.search(pack):
        return "wearable"
    if HAND_WASH_KW.search(pack):
        return "hand_wash"
    if (
        BODY_WASH_STRONG_KW.search(pack)
        and not NOT_BODY_WASH_KW.search(pack)
        and not _packaging_implies_hair(pack)
    ):
        return "body_bath"
    if HOME_CLEAN_KW.search(pack):
        return "home_clean"
    if NAIL_FUNGUS_KW.search(pack):
        return "nail_fungus"
    if DEODORANT_KW.search(pack):
        return "body_deo"
    if is_facial_exfoliation(pack) and not _packaging_implies_hair(pack):
        return "skin_face"
    has_hair = _packaging_implies_hair(pack)
    has_bath = _packaging_implies_body_wash(pack) or (
        bool(BODY_BATH_KW.search(pack)) and not has_hair and not NOT_BODY_WASH_KW.search(pack)
    )
    if has_bath and not has_hair:
        return "body_bath"
    if has_hair and not has_bath:
        return "hair"
    if has_bath and has_hair:
        if re.search(r"shampoo|conditioner|发膜|护发素|护发|capilar", pack, re.I):
            return "hair"
        return "body_bath"
    if ORAL_KW.search(pack):
        return "oral"
    if HAND_BODY_KW.search(pack):
        return "body_hand"
    if SKIN_FACE_KW.search(pack) and not has_hair:
        return "skin_face"
    return None


def _score_zones_from_evidence(blob: str, *, pack: str = "") -> dict[str, int]:
    scores = {z: 0 for z in ZONE_PROFILES if z != "generic"}
    pack = pack or blob
    hair_product = _packaging_implies_hair(pack)
    bath_product = _packaging_implies_body_wash(pack) or (
        bool(BODY_BATH_KW.search(pack)) and not hair_product and not NOT_BODY_WASH_KW.search(pack)
    )

    if HAND_WASH_KW.search(pack) or HAND_WASH_KW.search(blob):
        scores["hand_wash"] = 8
        scores["hair"] = 0
        scores["skin_face"] = 0
        scores["body_bath"] = 0
    if NAIL_FUNGUS_KW.search(pack) or NAIL_FUNGUS_KW.search(blob):
        scores["nail_fungus"] = 8
        scores["skin_face"] = 0
        scores["hair"] = 0
    if DEODORANT_KW.search(pack):
        scores["body_deo"] = scores.get("body_deo", 0) + 8
        scores["skin_face"] = 0
        scores["hair"] = 0
    if hair_product and not DEODORANT_KW.search(pack):
        scores["hair"] = scores.get("hair", 0) + 6
    if bath_product:
        scores["body_bath"] = scores.get("body_bath", 0) + 6
    if hair_product and HAIR_TRANSFORM_KW.search(blob):
        scores["hair"] = scores.get("hair", 0) + 2
    if bath_product and BODY_SKIN_TRANSFORM_KW.search(blob):
        scores["body_bath"] = scores.get("body_bath", 0) + 2
    if not hair_product and HAIR_TRANSFORM_KW.search(blob):
        pass
    if (
        not bath_product
        and not hair_product
        and not NOT_BODY_WASH_KW.search(blob)
        and (BODY_BATH_KW.search(blob) or BODY_SKIN_TRANSFORM_KW.search(blob))
    ):
        scores["body_bath"] = scores.get("body_bath", 0) + 2
    if hair_product:
        scores["body_bath"] = 0
        scores["skin_face"] = max(0, scores.get("skin_face", 0) - 2)

    if SKIN_TRANSFORM_KW.search(blob) and not HAIR_TRANSFORM_KW.search(blob):
        scores["skin_face"] = scores.get("skin_face", 0) + 3
    if ORAL_KW.search(pack) or ORAL_KW.search(blob):
        scores["oral"] = scores.get("oral", 0) + 4
    if HAND_BODY_KW.search(pack):
        scores["body_hand"] = scores.get("body_hand", 0) + 3
    if HOME_CLEAN_KW.search(pack):
        scores["home_clean"] = scores.get("home_clean", 0) + 5
    if SKIN_FACE_KW.search(pack) and not hair_product and not DEODORANT_KW.search(pack):
        scores["skin_face"] = scores.get("skin_face", 0) + 3
    if DEODORANT_KW.search(pack) or DEODORANT_KW.search(blob):
        scores["body_deo"] = max(scores.get("body_deo", 0), 8)
        scores["skin_face"] = 0

    if bath_product and not hair_product:
        scores["hair"] = 0
    if hair_product and not bath_product:
        scores["body_bath"] = max(0, scores.get("body_bath", 0) - 3)
    return scores


def _pick_zone_from_scores(scores: dict[str, int], pack: str) -> str | None:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked or ranked[0][1] < 3:
        return None
    top_zone, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0

    bath_s, hair_s = scores.get("body_bath", 0), scores.get("hair", 0)
    if bath_s >= 3 and hair_s >= 3:
        if BODY_BATH_KW.search(pack) and not HAIR_KW.search(pack):
            return "body_bath"
        if HAIR_KW.search(pack) and not BODY_BATH_KW.search(pack):
            return "hair"
        if bath_s > hair_s:
            return "body_bath"
        if hair_s > bath_s:
            return "hair"

    if top_score == second:
        hair_s = scores.get("hair", 0)
        skin_s = scores.get("skin_face", 0)
        if hair_s == skin_s and hair_s >= 3 and HAIR_KW.search(pack):
            return "hair"
    return top_zone


def resolve_application_zone(analysis: dict, user_prompt: str = "") -> str:
    """包装功效优先 → 全量证据打分；图4对比主体跟本品真实功能走。"""
    pack_zone = _zone_from_packaging_truth(analysis)
    pack = _marketing_truth_blob(analysis)
    blob = _analysis_evidence_blob(analysis, user_prompt)
    if pack_zone:
        return pack_zone

    scores = _score_zones_from_evidence(blob, pack=pack)
    vision_zone = (analysis.get("application_zone") or "").strip()
    if vision_zone in scores and vision_zone != "generic":
        scores[vision_zone] = scores.get(vision_zone, 0) + 1

    picked = _pick_zone_from_scores(scores, pack)
    if picked:
        return picked
    if pack_zone:
        return pack_zone

    return detect_application_zone(analysis, user_prompt)


def detect_application_zone(analysis: dict, user_prompt: str = "") -> str:
    pack = _packaging_truth_blob(analysis)
    zt = _zone_from_packaging_truth(analysis)
    if zt:
        return zt
    blob = _analysis_evidence_blob(analysis, user_prompt)
    if HAND_WASH_KW.search(pack) or HAND_WASH_KW.search(blob) or HAND_WASH_KW.search(user_prompt or ""):
        return "hand_wash"
    if NAIL_FUNGUS_KW.search(pack) or NAIL_FUNGUS_KW.search(blob) or NAIL_FUNGUS_KW.search(user_prompt or ""):
        return "nail_fungus"
    if DEODORANT_KW.search(pack) or DEODORANT_KW.search(user_prompt or ""):
        return "body_deo"
    if (BODY_WASH_STRONG_KW.search(blob) or BODY_WASH_STRONG_KW.search(user_prompt or "")) and not NOT_BODY_WASH_KW.search(
        blob
    ):
        return "body_bath"
    if HOME_CLEAN_KW.search(blob) or HOME_CLEAN_KW.search(user_prompt or ""):
        return "home_clean"
    if BODY_BATH_KW.search(blob) or BODY_BATH_KW.search(user_prompt or ""):
        return "body_bath"
    if HAIR_KW.search(pack) or HAIR_KW.search(user_prompt or ""):
        return "hair"
    if ORAL_KW.search(blob):
        return "oral"
    if HAND_BODY_KW.search(blob):
        return "body_hand"
    if SKIN_FACE_KW.search(blob):
        return "skin_face"
    return "generic"


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _vision_visual_trusted(zone: str, visual: str) -> bool:
    v = (visual or "").strip()
    if len(v) < 35:
        return False
    vl = v.lower()
    if zone == "hair":
        if SKIN_TRANSFORM_KW.search(vl) and not HAIR_TRANSFORM_KW.search(vl):
            return False
        return bool(HAIR_TRANSFORM_KW.search(vl) or "发" in v)
    if zone == "skin_face":
        return bool(SKIN_TRANSFORM_KW.search(vl)) and not HAIR_TRANSFORM_KW.search(vl)
    if zone == "body_bath":
        return bool(BODY_SKIN_TRANSFORM_KW.search(vl) or "shower" in vl or "foam" in vl)
    if zone == "home_clean":
        return bool(HOME_CLEAN_KW.search(vl) or "toilet" in vl or "bowl" in vl)
    if zone == "body_deo":
        return bool(DEODORANT_KW.search(vl) or "underarm" in vl or "axila" in vl or "腋" in v)
    return True


def build_frame4_authoritative_en(analysis: dict, profile: dict) -> str:
    before = (analysis.get("before_use_state") or profile["before"]).strip()
    after = (analysis.get("after_use_state") or profile["after"]).strip()
    visual = (analysis.get("before_after_visual_en") or "").strip()
    subject = (analysis.get("transformation_subject_en") or analysis.get("frame4_comparison_en") or "").strip()
    func = (analysis.get("primary_function") or analysis.get("category") or "").strip()[:320]
    zone = (analysis.get("application_zone_en") or profile.get("label_en") or "").strip()
    chunks = [
        "FRAME 4 COMPARISON AUTHORITY — NON-NEGOTIABLE: match THIS uploaded SKU's real function from packaging "
        "and vision analysis only; do NOT swap body wash vs hair care vs facial skincare.",
        f"Product application zone: {zone}.",
    ]
    if func:
        chunks.append(f"Primary function (source of truth): {func}")
    chunks.append(f"Transform: «{before}» → «{after}».")
    if subject:
        chunks.append(f"Comparison subject (non-negotiable): {subject}.")
    if visual:
        chunks.append(f"How to show it in one photo: {visual[:500]}.")
    chunks.append(f"Never depict: {profile['forbidden_en']}.")
    return " ".join(chunks)


def build_core_function_line_en(analysis: dict, user_prompt: str = "") -> str:
    """全套共用的一句功效。只写作用对象，不写各张图的卖点。包装判断优先于已存的错误分区。"""
    zone = reconcile_application_zone(analysis, user_prompt)
    evidence = " ".join(
        [
            _marketing_truth_blob(analysis),
            _packaging_truth_blob(analysis),
            user_prompt or "",
        ]
    )
    if zone == "skin_face" and is_facial_exfoliation(evidence):
        return (
            "CORE FUNCTION — Gentle facial exfoliation. "
            "The action clears dull surface buildup on the face. "
            "The result is smoother, more luminous facial skin."
        )
    lines = {
        "body_bath": (
            "CORE FUNCTION — Body wash. It cleans body skin in the shower. "
            "Any comparison changes the skin only. The wall, tiles, and floor stay the same."
        ),
        "hand_wash": (
            "CORE FUNCTION — Hand wash. It clears visible germ specks on the hands. "
            "The bottle keeps the reference shape."
        ),
        "hair": "CORE FUNCTION — Hair care. It acts on the hair strands.",
        "wearable": "CORE FUNCTION — A wearable item. The change is wearing this exact item.",
        "nail_fungus": (
            "CORE FUNCTION — Nail care on the nail plate. The nail looks clearer and more cared for. "
            "No medical cure claim."
        ),
        "body_deo": "CORE FUNCTION — Deodorant. It is applied on the underarm.",
        "skin_face": "CORE FUNCTION — Facial skincare. It acts on the face.",
        "oral": "CORE FUNCTION — Oral care. It acts on the teeth.",
        "body_hand": "CORE FUNCTION — Lotion. It acts on the hands or body skin.",
        "home_clean": "CORE FUNCTION — Bathroom cleaner. It acts on the fixture or tile it is made to clean.",
    }
    if zone in lines:
        return lines[zone]
    if is_body_scrub(evidence):
        return (
            "CORE FUNCTION — Body scrub. The action exfoliates body skin. "
            "The result is smoother body skin."
        )
    func = (analysis.get("primary_function") or "").strip()
    lowered = func.lower()
    if func and len(func) <= 180 and "tiktok" not in lowered and "9张" not in func:
        return (
            f"CORE FUNCTION — {func[:160]}. "
            "Show this use. Keep the background the same wherever a comparison appears."
        )
    return (
        "CORE FUNCTION — Read the words printed on the attached package. "
        "Those words are the product type and the claim. "
        "Text on the image repeats that product type and one claim from the package. "
        "Show the result those words describe."
    )


def build_product_efficacy_anchor_en(analysis: dict) -> str:
    """与首图/图3 同源：包装 + 主功效 + 西语卖点，图4 必须与这些一致。"""
    pack = _marketing_truth_blob(analysis)
    label = (analysis.get("label_text_exact") or "").strip()[:450]
    func = (analysis.get("primary_function") or analysis.get("category") or "").strip()[:300]
    usps = " | ".join(_text_list(analysis.get("key_selling_points"))[:6])
    heads = " | ".join(_text_list(analysis.get("spanish_headlines"))[:6])
    zone = (analysis.get("application_zone") or "").strip()
    zone_en = (analysis.get("application_zone_en") or "").strip()
    chunks = [
        "PRODUCT EFFICACY ANCHOR (same SKU truth as hero frame 1 / pain frame 3 Spanish messaging) — "
        "Frame 4 visual before→after must prove THESE benefits on the correct body part; "
        "ignore any generic hair/skin template that conflicts with this block.",
    ]
    if label:
        chunks.append(f"Packaging label text: «{label}».")
    if pack.strip():
        chunks.append(f"SKU naming/category: {pack[:380]}.")
    if func:
        chunks.append(f"Primary function: {func}.")
    if usps:
        chunks.append(f"Key selling points (used on other frames): {usps[:450]}.")
    if heads:
        chunks.append(f"Spanish headlines (used on other frames): {heads[:350]}.")
    if zone_en:
        chunks.append(f"Application zone: {zone_en} ({zone}).")
    if zone == "body_bath":
        chunks.append(
            "Frame 4 MUST show shower BODY skin (arm/shoulder/back) dull→bright with rich foam and moisturized "
            "clean feel — matching brightening/body-wash claims. FORBIDDEN: hair frizz/gloss compare, conditioner, "
            "hair mask narrative, scalp close-up transformation."
        )
    elif zone == "hair":
        chunks.append(
            "Frame 4 MUST show HAIR strand transformation only — not body-wash skin foam, not facial skincare."
        )
    return " ".join(chunks)


def normalize_product_usage_analysis(analysis: dict, user_prompt: str = "") -> dict:
    if not isinstance(analysis, dict):
        return analysis or {}
    zone = reconcile_application_zone(analysis, user_prompt)
    profile = ZONE_PROFILES.get(zone, ZONE_PROFILES["generic"])
    analysis["application_zone"] = zone
    analysis["application_zone_en"] = profile["label_en"]

    if not (analysis.get("transformation_subject_en") or "").strip():
        tf = (analysis.get("frame4_comparison_en") or "").strip()
        if tf:
            analysis["transformation_subject_en"] = tf[:200]
        elif zone == "hair":
            analysis["transformation_subject_en"] = "hair strands (not facial skin, not shower body foam)"
        elif zone == "body_bath":
            analysis["transformation_subject_en"] = "shower body skin with cleansing foam (not hair frizz compare)"
        elif zone == "skin_face":
            analysis["transformation_subject_en"] = "facial skin"
        elif zone == "home_clean":
            analysis["transformation_subject_en"] = "toilet/sanitary surface cleanliness"

    before = (analysis.get("before_use_state") or "").strip()
    after = (analysis.get("after_use_state") or "").strip()
    hair_like = zone == "hair"
    skin_wrong = hair_like and any(x in (before + after).lower() for x in ("skin", "hand", "face cream", "手"))
    hair_wrong = zone != "hair" and any(
        x in (before + after).lower() for x in ("hair", "frizz", "scalp", "cabello", "发")
    )
    if not before or skin_wrong or hair_wrong:
        analysis["before_use_state"] = profile["before"]
    if not after or skin_wrong or hair_wrong:
        analysis["after_use_state"] = profile["after"]

    visual = (analysis.get("before_after_visual_en") or "").strip()
    visual_bad = hair_like and any(
        x in visual.lower() for x in ("hand", "palm", "manos", "手背", "喷手", "skin cream")
    )
    hair_in_visual = zone != "hair" and any(
        x in visual.lower() for x in ("hair", "frizz", "frizzy", "scalp", "cabello", "发质")
    )
    skin_in_visual = zone == "hair" and any(
        x in visual.lower()
        for x in (
            "skin",
            "arm",
            "cheek",
            "facial",
            "complexion",
            "glowing skin",
            "face cream",
            "piel",
            "body lotion",
            "沐浴",
            "shower gel",
            "foam on arm",
        )
    )
    bath_in_visual = zone == "body_bath" and any(
        x in visual.lower() for x in ("frizz", "frizzy", "hair strand", "cabello", "发质", "发丝", "scalp")
    )
    vision_ok = _vision_visual_trusted(zone, visual)
    if (
        not visual
        or visual_bad
        or hair_in_visual
        or skin_in_visual
        or bath_in_visual
        or _scenario_suspect_hands_only(analysis)
        or (hair_like and not vision_ok and "hair" not in visual.lower() and "发" not in visual)
        or (not vision_ok and len(visual) < 50)
    ):
        pref = (analysis.get("frame4_comparison_en") or "").strip()
        if pref and _vision_visual_trusted(zone, pref):
            analysis["before_after_visual_en"] = pref
        else:
            analysis["before_after_visual_en"] = profile["before_after_visual_en"]
    elif vision_ok:
        analysis["before_after_visual_en"] = visual

    analysis["frame4_visual_split_en"] = (
        (analysis.get("frame4_comparison_en") or "").strip()
        or analysis.get("before_after_visual_en")
        or profile.get("frame4_split_en")
        or profile["before_after_visual_en"]
    )
    analysis["frame4_authoritative_en"] = build_frame4_authoritative_en(analysis, profile)
    analysis["product_efficacy_anchor_en"] = build_product_efficacy_anchor_en(analysis)

    steps = _text_list(analysis.get("correct_usage_steps_en")) or _text_list(analysis.get("usage_steps_en"))
    if not steps or _scenario_suspect_hands_only(analysis):
        analysis["correct_usage_steps_en"] = list(profile["usage_steps_en"])

    analysis["usage_forbidden_en"] = profile["forbidden_en"]
    analysis["in_use_visual_en"] = profile["in_use_en"]

    pains = _text_list(analysis.get("pain_points"))
    if zone == "hair":
        hand_pain = any(
            x in " ".join(pains).lower() for x in ("hand", "mano", "手背", "护手", "喷手", "palm")
        )
        if not pains or hand_pain:
            analysis["pain_points"] = [
                "frizzy dry tangled hair hard to comb",
                "dull damaged ends lacking shine",
                "post-color/heat damage needing repair",
            ]
    elif zone == "oral" and not pains:
        analysis["pain_points"] = [
            "yellowed teeth dull smile",
            "bad breath social worry",
        ]
    elif zone == "body_bath" and not pains:
        analysis["pain_points"] = [
            "dry tight skin after shower",
            "body wash that does not foam or rinse clean",
            "skin does not feel fresh all day",
        ]
    elif zone == "home_clean" and not pains:
        analysis["pain_points"] = [
            "toilet bowl stains and limescale hard to remove",
            "bathroom smells unsanitary",
            "scrubbing takes too long with weak cleaners",
        ]

    return analysis


def _pack_blob(analysis: dict) -> str:
    return " ".join(
        [
            str(analysis.get("label_text_exact") or ""),
            str(analysis.get("product_name_en") or ""),
            str(analysis.get("product_name_es") or ""),
            str(analysis.get("product_name_zh") or ""),
            str(analysis.get("category") or ""),
            str(analysis.get("primary_function") or ""),
        ]
    )


def application_target_en(zone: str, analysis: dict) -> str:
    """每张图都要看见的涂抹部位，避免喷雾喷脸、除臭膏涂脸。"""
    spray = bool(SPRAY_FORM_KW.search(_pack_blob(analysis)))
    if zone == "hair" and spray:
        return (
            "APPLICATION TARGET — This is a HAIR SPRAY. Aim the nozzle at the HAIR "
            "(crown, lengths, or ends). The mist lands on hair strands. "
            "A face may show in profile, but it is NOT the target. "
            "FORBIDDEN: facial mist, spraying cheeks, forehead, or closed eyes."
        )
    if zone == "hair":
        return (
            "APPLICATION TARGET — HAIR only. The product touches strands, ends, or scalp. "
            "FORBIDDEN: spraying or rubbing it on the face."
        )
    if zone == "nail_fungus":
        return (
            "APPLICATION TARGET — THE NAIL. Apply on the nail plate of a hand or foot. "
            "The customer wants that nail to look clearer and less stained. "
            "FORBIDDEN: face, hair, and any sentence that says the fungus is cured."
        )
    if zone == "body_deo":
        return (
            "APPLICATION TARGET — DEODORANT for the BODY. "
            "The stick, cream, or spray touches the UNDERARM. "
            "A face may be visible, but the product is never on the face. "
            "FORBIDDEN: face cream, cheek application, facial mist."
        )
    if zone == "body_bath":
        return (
            "APPLICATION TARGET — BODY SKIN in the shower (arms, shoulders, back, legs). "
            "FORBIDDEN: shampoo on the scalp, face-cream close-up."
        )
    if zone == "skin_face":
        return "APPLICATION TARGET — FACE skin only (cheeks, forehead). Not hair, not underarms."
    if zone == "oral":
        return "APPLICATION TARGET — TEETH and mouth. Not face cream, not hair."
    if zone == "hand_wash":
        return (
            "APPLICATION TARGET — THE HANDS. Left shows germ specks on the skin. "
            "Right shows those specks gone. "
            "The bottle keeps the reference outline, pump, cap, and label."
        )
    if zone == "body_hand":
        return "APPLICATION TARGET — HANDS or body skin. Not the face, not hair."
    if zone == "home_clean":
        return "APPLICATION TARGET — the surface being cleaned (toilet, tile). No person, no face."
    return (
        "APPLICATION TARGET — follow the packaging category. "
        "Do not default a spray or cream onto the face unless this product is facial skincare."
    )


def _scenario_suspect_hands_only(analysis: dict) -> bool:
    blob = " ".join(_text_list(analysis.get("usage_scenarios"))).lower()
    if not blob:
        return False
    hair_zone = analysis.get("application_zone") == "hair"
    if not hair_zone:
        return False
    hand_only = any(
        x in blob
        for x in ("on hand", "on hands", "palm", "手背", "喷手", "手上", "spray hand", "manos")
    )
    no_hair = "hair" not in blob and "发" not in blob and "头发" not in blob
    return hand_only and no_hair


def apply_product_usage_locks(plan: dict) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan

    user = (plan.get("user_prompt") or plan.get("subject_lock") or "")[:800]
    analysis = dict(plan.get("product_analysis") or {})
    analysis = normalize_product_usage_analysis(analysis, user)
    plan["product_analysis"] = analysis

    zone = analysis.get("application_zone") or "generic"
    profile = ZONE_PROFILES.get(zone, ZONE_PROFILES["generic"])

    auth4 = (analysis.get("frame4_authoritative_en") or build_frame4_authoritative_en(analysis, profile)).strip()
    anchor = (
        analysis.get("product_efficacy_anchor_en") or build_product_efficacy_anchor_en(analysis)
    ).strip()
    plan["listing_product_efficacy_anchor_en"] = anchor
    plan["listing_core_function_en"] = build_core_function_line_en(analysis, user)
    target = application_target_en(zone, analysis)
    if zone == "hair" and SPRAY_FORM_KW.search(_pack_blob(analysis)):
        analysis["correct_usage_steps_en"] = [
            "aim the nozzle at dry or styled hair",
            "mist the crown and lengths",
            "hair looks smoother — never spray the face",
        ]
        plan["product_analysis"] = analysis
    elif zone == "body_deo":
        analysis["correct_usage_steps_en"] = list(profile["usage_steps_en"])
        plan["product_analysis"] = analysis
    plan["product_usage_master_en"] = (
        f"{target} "
        f"PRODUCT USAGE TRUTH — Category zone: {profile['label_en']}. "
        f"Primary function from vision: {(analysis.get('primary_function') or '')[:220]}. "
        f"In-use visual: {profile['in_use_en']} "
        f"FORBIDDEN across all frames: {profile['forbidden_en']}. "
        f"{auth4}"
    )

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()
        shot["product_usage_zone_en"] = profile["label_en"]
        prior_usage = (shot.get("product_usage_frame_lock_en") or "").strip()
        if "APPLICATION TARGET" not in prior_usage:
            shot["product_usage_frame_lock_en"] = f"{target} {prior_usage}".strip()

        if idx == 4 or role == "usp_primary":
            shot["frame4_authoritative_en"] = auth4
            shot["frame4_efficacy_anchor_en"] = anchor
            shot["product_usage_frame_lock_en"] = (
                f"{target} {anchor} {auth4} "
                f"Never: {profile['forbidden_en']}."
            )
            shot["conversion_visual_lock_en"] = (
                f"FRAME 4 CONVERSION LOCK — Pure visual before→after; overrides generic story beats. "
                f"{anchor} {auth4}"
            )[:2200]
            shot["transformation_story_lock"] = auth4[:1200]
            needs_model = zone_requires_model(zone)
            analysis["frame4_requires_model"] = needs_model
            ba_vis = (analysis.get("before_after_visual_en") or profile.get("before_after_visual_en") or "")[:500]
            subj_en = (analysis.get("transformation_subject_en") or "").strip()
            subject_tpl = (
                f"FRAME 4 TRANSFORMATION SUBJECT — {subj_en or profile['label_en']}; "
                f"fills ≥45% of frame; {ba_vis}"
            )
            if not needs_model:
                subject_tpl = (
                    f"FRAME 4 SURFACE/OBJECT — Before→after on the cleaned object ({profile['label_en']}); "
                    f"NO human model; {FRAME4_OBJECT_BY_ZONE.get(zone, profile.get('frame4_split_en', ''))}"
                )
            shot["frame4_subject_lock_en"] = subject_tpl
            split = analysis.get("frame4_visual_split_en") or profile.get("frame4_split_en") or ""
            shot["frame4_visual_split_en"] = split
            if zone == "home_clean":
                shot["frame4_scene_lock_en"] = (
                    "FRAME 4 SCENE — Real bathroom/toilet interior; stained vs clean bowl or tile; "
                    "NO human, NO skin/hair demo."
                )
            elif zone == "body_bath":
                shot["frame4_scene_lock_en"] = (
                    "FRAME 4 SCENE — Modern shower stall / bathroom tile with steam-soft light; "
                    "shower shelf with SKU; NOT kitchen, NOT hair salon mirror."
                )
            elif zone == "hair":
                shot["frame4_scene_lock_en"] = (
                    "FRAME 4 SCENE — Bathroom vanity or salon mirror area; HAIR is the transformation subject; "
                    "NOT shower body-skin foam compare. If it is a spray, the nozzle points at the hair."
                )
            elif zone == "body_deo":
                shot["frame4_scene_lock_en"] = (
                    "FRAME 4 SCENE — Bathroom or bedroom. The product touches the UNDERARM only, never the face."
                )
            else:
                shot["frame4_scene_lock_en"] = (
                    f"FRAME 4 SCENE — Environment must match product use: "
                    f"{'modern bathroom vanity or shower shelf' if zone in ('hair', 'oral', 'skin_face', 'body_bath') else 'authentic use context'}; "
                    f"NOT unrelated family kitchen dining unless product is food/kitchen."
                )
            shot["frame4_no_text_lock_en"] = (
                "INDEX 4 TEXT LOCK — Pure visual before/after; ZERO overlay Spanish/English marketing lines; "
                "no antes/después/before/after labels."
            )
            shot.pop("frame4_typography_lock_en", None)
            if needs_model:
                model_detail = FRAME4_MODEL_BY_ZONE.get(zone, FRAME4_MODEL_BY_ZONE["generic"])
                if zone == "hand_wash":
                    shot["human_cast_mode"] = "hands"
                else:
                    shot["human_cast_mode"] = "full" if zone in ("body_bath", "body_deo", "nail_fungus") else "face"
                shot["human_cast_mandatory"] = True
                shot["human_cast_mandatory_en"] = f"{FRAME4_MODEL_MANDATE_BASE} {model_detail}"
                shot["frame4_model_lock_en"] = shot["human_cast_mandatory_en"]
            else:
                obj = FRAME4_OBJECT_BY_ZONE.get(zone, profile.get("frame4_split_en", ""))
                shot["human_cast_mode"] = "none"
                shot["human_cast_mandatory"] = False
                shot.pop("human_cast_mandatory_en", None)
                shot["frame4_model_lock_en"] = f"{FRAME4_OBJECT_MANDATE_BASE} {obj}"
            shot.pop("human_cast_hair_en", None)
            shot.pop("human_cast_body_en", None)
        v5 = (shot.get("frame5_variant") or "").strip()
        if idx == 5 and v5 == "usage_steps":
            shot["product_usage_frame_lock_en"] = (
                f"{target} FRAME 5 IN USE — {profile['in_use_en']} "
                f"Forbidden: {profile['forbidden_en']}. Do not draw a numbered step chart."
            )
        if idx == 6:
            shot["product_usage_frame_lock_en"] = (
                f"{target} FRAME 6 USAGE BENEFIT — {profile['in_use_en']} "
                f"Forbidden: {profile['forbidden_en']}."
            )
            if zone == "body_deo":
                shot["human_cast_mode"] = "full"
                shot["human_cast_mandatory"] = True
                extra6 = (shot.get("negative_extra") or "").strip()
                shot["negative_extra"] = (
                    f"{extra6}, face cream on cheeks, facial mist, spraying the face"
                ).strip(", ")
        if idx == 7 or role == "ease_objection":
            shot["product_usage_frame_lock_en"] = (
                f"{target} FRAME 7 IN-USE DEMO — {profile['in_use_en']} "
                f"Forbidden: {profile['forbidden_en']}."
            )

        if idx == 4:
            extra = (shot.get("negative_extra") or "").strip()
            if zone == "hair":
                shot["human_cast_mode"] = "hair"
                shot["human_cast_hair_en"] = (
                    "HAIR TRANSFORMATION CAST — Before→after visible on HAIR (frizz/dull vs smooth/shiny strands). "
                    "Face may appear in 3/4 but contrast is HAIR not facial skin; NOT cheek skincare glow."
                )
                shot["negative_extra"] = (
                    f"{extra}, facial skincare before after, cheek skin transformation, glowing face compare, "
                    f"serum on face, moisturizer on skin, arm skin shower compare, body wash foam on skin"
                ).strip(", ")
            elif zone == "body_bath":
                shot["negative_extra"] = (
                    f"{extra}, frizzy hair transformation, hair before after, shampoo on scalp"
                ).strip(", ")
            elif zone == "body_deo":
                shot["negative_extra"] = (
                    f"{extra}, face cream, cheek application, facial mist, spraying the face, "
                    f"skincare on the face"
                ).strip(", ")
            elif zone == "home_clean":
                shot["negative_extra"] = (
                    f"{extra}, human model, face portrait, skin before after, hair transformation"
                ).strip(", ")

        extra = (shot.get("negative_extra") or "").strip()
        wrong = f"wrong application zone, {profile['forbidden_en']}"
        if wrong[:30] not in extra.lower():
            shot["negative_extra"] = f"{extra}, {wrong}".strip(", ")

    neg = (plan.get("negative_prompt") or "").strip()
    if "wrong application zone" not in neg.lower():
        plan["negative_prompt"] = f"{neg}, wrong application zone, {profile['forbidden_en']}".strip(", ")

    return plan


def finalize_frame4_product_truth(plan: dict) -> dict:
    """生图前最后一道：图4 必须与首图同源功效；清掉沐浴/护发冲突残留。"""
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
        return plan
    if (plan.get("plan_template") or "") != "tk_mx_ecommerce_9":
        return plan

    from generation.services.listing_frame4_contract import apply_frame4_comparison_contract

    plan = apply_product_usage_locks(plan)
    plan = apply_frame4_comparison_contract(plan)
    analysis = plan.get("product_analysis") or {}
    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if idx != 4:
            continue
        shot.pop("frame4_content_lock", None)
        anchor = (shot.get("frame4_efficacy_anchor_en") or plan.get("listing_product_efficacy_anchor_en") or "").strip()
        auth = (shot.get("frame4_authoritative_en") or analysis.get("frame4_authoritative_en") or "").strip()
        if anchor or auth:
            shot["transformation_story_lock"] = f"{anchor} {auth}".strip()[:2000]
        zone = (analysis.get("application_zone") or "").strip()
        if zone == "hair":
            extra = (shot.get("negative_extra") or "").strip()
            bath_neg = "body wash foam on skin, shower skin compare, arm skin before after, facial skincare compare"
            if "body wash" not in extra.lower():
                shot["negative_extra"] = f"{extra}, {bath_neg}".strip(", ")
        elif zone == "body_bath":
            extra = (shot.get("negative_extra") or "").strip()
            if "frizzy hair" not in extra.lower():
                shot["negative_extra"] = (
                    f"{extra}, frizzy hair transformation, hair strand before after, conditioner on hair"
                ).strip(", ")
    return plan