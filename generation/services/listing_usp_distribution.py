"""套图卖点互不重复：每张图只讲自己的具体卖点，禁止整套重复空泛口号。"""

from __future__ import annotations

import re
import unicodedata

# 每镜允许的图上文案密度
TEXT_DENSITY_BY_INDEX: dict[int, str] = {
    1: "rich",
    2: "none",  # 纯白底：无任何营销文案
    3: "rich",
    4: "none",  # 图4：纯视觉前后对比，无任何叠加文案
    5: "rich",
    6: "rich",
    7: "rich",
    8: "rich",
    9: "rich",
}

FRAME4_NO_TEXT_LOCK_EN = (
    "INDEX 4 TEXT LOCK — Before/after transformation is PURE VISUAL ONLY: "
    "ZERO added headlines, captions, icon bullets, or Spanish callouts on the image "
    "(forbidden also: antes, después, before, after, 使用前, 使用后). Packaging print only if on SKU."
)

TYPOGRAPHY_MANDATE_EN = (
    "ON-IMAGE TYPOGRAPHY — Index 2 and Index 4: ZERO added marketing text. "
    "Every other frame: a designed title group covering part of the image — "
    "bold headline, a two-line introduction explaining that same benefit, and three proof lines. "
    "Follow THIS set's TITLE TREATMENT exactly. Do not swap a color block for a thin line, or a thin line for a color block. "
    "Type must be big enough to read on a phone. The photo fills the rest edge to edge. "
    "A tiny corner title or a mostly empty photo is invalid. "
    "No Chinese except packaging from reference. No English marketing. No Step 1 / Step 2."
)

FILLED_FRAME_LOCK_EN = (
    "COMPOSITION DENSITY — Fill the frame. A large readable title group "
    "(bold headline, two-line introduction, three proof lines) is designed into the frame. "
    "Follow THIS set's TITLE TREATMENT exactly. "
    "The photograph fills the rest edge to edge: product, setting, light, and several related props "
    "in the set theme color. No wide empty margins, no lone product on a blank card, no tiny one-word label."
)

TEXT_REQUIRED_NEGATIVE = (
    "missing on-image Spanish text, blank marketing frame with no typography, "
    "silent art-only listing slide with no readable callouts"
)

USP_DIVERSITY_LOCK_EN = (
    "USP DIVERSITY — Each frame owns ONE distinct selling point taken from this product. "
    "Never repeat Calidad premium, Fácil de usar, Resultado visible, Vale la pena, "
    "or any other headline, subhead, or icon across frames."
)

_GENERIC_USP_KEYS = frozenset(
    {
        "calidad premium",
        "facil de usar",
        "resultado visible",
        "vale la pena",
        "para tu dia",
        "uso facil",
        "beneficio real",
        "dia a dia",
        "hecho para ti",
        "bienestar diario",
        "siente la diferencia",
        "compra ya",
        "gran valor",
        "detalle premium",
        "tu mejor opcion",
        "acabado uniforme",
        "formula estable",
        "textura clara",
        "detalle de cerca",
        "envase firme",
        "dosis justa",
        "aplicacion limpia",
        "efecto concreto",
        "presentacion clara",
        "toque ligero",
        "aroma propio",
        "listo al momento",
        "premium quality",
        "easy to use",
        "visible results",
        "worth it",
    }
)


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _locale_default_pool(locale: str) -> list[str]:
    loc = (locale or "es-MX").lower()
    if loc.startswith("pt"):
        return [
            "Qualidade premium",
            "Fácil de usar",
            "Resultado visível",
            "Para o dia a dia",
            "Vale a pena",
        ]
    if loc.startswith("de"):
        return [
            "Premium-Qualität",
            "Einfach zu nutzen",
            "Sichtbares Ergebnis",
            "Für jeden Tag",
            "Lohnt sich",
        ]
    if loc.startswith("en"):
        return [
            "Premium quality",
            "Easy to use",
            "Visible results",
            "Everyday essential",
            "Worth it",
        ]
    return [
        "Calidad premium",
        "Fácil de usar",
        "Resultado visible",
        "Para tu día",
        "Vale la pena",
    ]


def _norm_key(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text or "")
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()
    return raw[:48]


_GENERIC_FRAGMENTS = (
    "calidad premium",
    "facil de usar",
    "resultado visible",
    "vale la pena",
    "uso facil",
    "beneficio real",
    "dia a dia",
    "premium quality",
    "easy to use",
    "visible results",
    "acabado uniforme",
    "formula estable",
    "textura clara",
    "detalle de cerca",
    "envase firme",
)


def _is_generic_claim(text: str) -> bool:
    key = _norm_key(text)
    if not key:
        return False
    if key in _GENERIC_USP_KEYS:
        return True
    return any(frag in key for frag in _GENERIC_FRAGMENTS)


def _is_on_image_language(text: str) -> bool:
    return bool(text) and not re.search(r"[\u4e00-\u9fff]", text)


def _product_seed(analysis: dict) -> int:
    parts = [
        analysis.get("product_name_es"),
        analysis.get("product_name_en"),
        analysis.get("product_name_zh"),
        analysis.get("primary_function"),
        str(analysis.get("label_text_exact") or "")[:120],
    ]
    total = 0
    for ch in "|".join(str(p or "") for p in parts):
        total = (total * 33 + ord(ch)) % 1000003
    return total or 1


def _rotate(items: list[str], seed: int) -> list[str]:
    if not items:
        return []
    cut = seed % len(items)
    return list(items[cut:]) + list(items[:cut])


def _need_lines(analysis: dict) -> list[str]:
    lines: list[str] = []
    for key in ("spanish_customer_needs", "purchase_motivations", "pain_points", "after_use_state"):
        value = analysis.get(key)
        bits = [value] if isinstance(value, str) else _text_list(value)
        for bit in bits:
            text = str(bit).strip()
            if text and _is_on_image_language(text) and not _is_filler(text) and not _is_usage_instruction(text):
                lines.append(text[:80])
    return lines


_CUSTOMER_INTENTS: tuple[tuple[re.Pattern[str], tuple[str, ...], tuple[str, ...]], ...] = (
    (
        re.compile(
            r"甲癣|甲癖|灰指甲|灰甲|onycho|nail\s*fungus|fungal\s*nail|toenail|"
            r"hongo\s+de\s+la\s+u[nñ]a|u[nñ]a\s+con\s+hongo|antimic",
            re.I,
        ),
        (
            "Uña con mejor aspecto",
            "Menos aspecto amarillo",
            "Cuidado en la uña",
            "Uña de aspecto más limpio",
            "Para la uña manchada",
            "La uña se ve más clara",
            "Aspecto de uña cuidada",
            "Puedes mostrar la uña",
            "La uña se ve más pareja",
            "Rutina sobre la uña",
        ),
        (
            "Le preocupa la uña amarilla",
            "Quiere una uña de mejor aspecto",
            "Busca cuidar la uña afectada",
            "No quiere esconder la uña",
            "Quiere verse la uña más limpia",
            "Le molesta la mancha en la uña",
            "Busca un aspecto más parejo",
            "Quiere cuidar la uña cada día",
        ),
    ),
    (
        re.compile(
            r"deodorant|anti[\s-]?perspirant|desodorante|antitranspirante|"
            r"odor\s*protection|odor\s*control|"
            r"underarm|armpit|axila|除臭|止汗|腋下",
            re.I,
        ),
        (
            "Axila fresca todo el día",
            "Protección bajo la axila",
            "Fresco al vestirte",
            "Confianza al salir",
            "Sin marcas en la ropa",
            "Olor bajo control",
            "Listo en segundos",
            "Axila cómoda",
        ),
        (
            "Le preocupa el sudor en la axila",
            "Quiere oler bien todo el día",
            "No quiere marcas en la ropa",
            "Busca frescura al salir",
            "Quiere sentirse segura con la axila",
        ),
    ),
)


def _analysis_blob(analysis: dict, usps: list[str]) -> str:
    parts = [
        analysis.get("primary_function"),
        analysis.get("product_name_zh"),
        analysis.get("product_name_en"),
        analysis.get("product_name_es"),
        analysis.get("category"),
        analysis.get("label_text_exact"),
        analysis.get("after_use_state"),
        analysis.get("before_use_state"),
    ]
    parts.extend(usps)
    for key in ("key_selling_points", "pain_points", "spanish_headlines", "purchase_motivations"):
        parts.extend(_text_list(analysis.get(key)))
    return " ".join(str(p or "") for p in parts)


def _customer_claims(analysis: dict, usps: list[str]) -> tuple[list[str], list[str]]:
    blob = _analysis_blob(analysis, usps)
    claims: list[str] = []
    needs: list[str] = []
    for pattern, claim_bank, need_bank in _CUSTOMER_INTENTS:
        if pattern.search(blob):
            claims.extend(claim_bank)
            needs.extend(need_bank)
            if pattern.pattern.startswith(r"甲癣|甲癖") and (
                analysis.get("application_zone") or "generic"
            ) in ("", "generic", "skin_face"):
                analysis["application_zone"] = "nail_fungus"
            if "desodorante" in pattern.pattern and (analysis.get("application_zone") or "generic") in (
                "",
                "generic",
                "skin_face",
            ):
                analysis["application_zone"] = "body_deo"
    return claims, needs


def _marketing_text_pool(plan: dict, analysis: dict, usps_cn: list[str]) -> list[str]:
    locale = (plan.get("locale") or analysis.get("locale") or "es-MX").lower()
    keys = ["spanish_headlines", "spanish_callouts", "key_selling_points_es"]
    if locale.startswith("pt"):
        keys = [
            "portuguese_headlines",
            "portuguese_callouts",
            "key_selling_points_pt",
            *keys,
        ]
    elif locale.startswith("en"):
        keys = ["english_headlines", "english_callouts", "key_selling_points_en", *keys]
    elif locale.startswith("de"):
        keys = ["german_headlines", "german_callouts", "key_selling_points_de", *keys]
    customer_claims, customer_needs = _customer_claims(analysis, usps_cn)
    if customer_needs:
        existing = _text_list(analysis.get("spanish_customer_needs"))
        analysis["spanish_customer_needs"] = customer_needs + existing
    pool: list[str] = list(customer_claims)
    for key in keys:
        pool.extend(_text_list(analysis.get(key)))
    for u in usps_cn:
        if u and _is_on_image_language(u):
            pool.append(u[:48])
    for key in ("ingredients", "active_ingredients", "key_ingredients"):
        pool.extend(_text_list(analysis.get(key)))
    label = str(analysis.get("label_text_exact") or "")
    for piece in re.split(r"[\n|;/•]+", label):
        piece = piece.strip()
        if 3 <= len(piece) <= 42:
            pool.append(piece)
    from generation.services.product_listing_narrative import default_spanish_usps_for_zone

    zone = (analysis.get("application_zone") or "generic").strip()
    pool.extend(_rotate(default_spanish_usps_for_zone(zone), _product_seed(analysis)))
    specific: list[str] = []
    generic: list[str] = []
    seen: set[str] = set()
    for item in pool:
        text = str(item).strip()
        if not _is_on_image_language(text) or _is_usage_instruction(text):
            continue
        key = _norm_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        if _is_generic_claim(text):
            generic.append(text)
        else:
            specific.append(text)
    if specific:
        return specific
    if generic:
        return generic
    return _locale_default_pool(locale)


def _benefit_from_pains(pains: list[str]) -> list[str]:
    out: list[str] = []
    for p in pains[:4]:
        p = p[:60]
        out.append(f"Sin {p}" if len(p) < 20 else f"Resuelve: {p}")
    return out


_FRAME9_TEXT_HINTS: dict[str, str] = {
    "daily_essential": "Spanish CTA + daily-life props; product embedded in routine scene.",
    "gift_worthy": "Spanish gift CTA + ribbon/bag/hands presenting.",
    "family_must_have": "Spanish family CTA + shared home staging.",
    "smart_buy": "Spanish worth-buying CTA + confident purchase mood.",
    "benefit_summary": "3–4 unique Spanish advantage bullets + visible product; closing slide.",
    "lifestyle_aspiration": "Spanish aspiration CTA + scenic environment payoff.",
}


def _pick_unique(
    pool: list[str],
    used: set[str],
    idx: int,
    fallback: str,
    *,
    allow_synthetic: bool = True,
) -> str:
    specifics_left = any(
        _norm_key(item) not in used and not _is_generic_claim(item) for item in pool
    )
    n = len(pool)
    if n:
        for i in range(n):
            candidate = pool[(idx + i) % n].strip()
            key = _norm_key(candidate)
            if not key or key in used:
                continue
            if _is_generic_claim(candidate) and specifics_left:
                continue
            used.add(key)
            return candidate[:48]
    for candidate in pool:
        key = _norm_key(candidate)
        if key and key not in used and not (_is_generic_claim(candidate) and specifics_left):
            used.add(key)
            return candidate[:48]
    if not allow_synthetic:
        return ""
    base = (fallback or "").strip()
    if not base or _is_filler(base) or _is_generic_claim(base):
        return ""
    n = 1
    while True:
        label = base if n == 1 and _norm_key(base) not in used else f"{base} {n}"
        key = _norm_key(label)
        if key and key not in used and not _is_generic_claim(label):
            used.add(key)
            return label[:48]
        n += 1


def _overlay_blocked(plan: dict, shot: dict) -> bool:
    try:
        index = int(shot.get("index") or 0)
    except (TypeError, ValueError):
        index = 0
    role = (shot.get("role") or "").strip()
    tpl = (plan.get("plan_template") or "").strip()
    if index == 2 or role == "white_bg_catalog":
        return True
    if tpl == "tk_mx_ecommerce_9" and index == 4:
        return True
    return (shot.get("on_image_text_density") or "") == "none" and not (
        shot.get("headline_es") or shot.get("subhead_es") or shot.get("icon_bullets_es")
    )


def _is_usage_instruction(text: str) -> bool:
    """使用步骤不是卖点，不能写到图上当标题。"""
    key = _norm_key(text)
    if not key:
        return False
    if re.match(r"^(step|paso|etapa|schritt|步骤)\s*\d+", key):
        return True
    if re.search(r"\b(step|paso)\s*\d+\b", key):
        return True
    if key in {
        "open",
        "apply",
        "enjoy result",
        "apply as label instructs",
        "apply to correct body zone per category",
    }:
        return True
    if key.startswith(("open ", "apply ", "enjoy result", "how to use", "modo de uso")):
        return True
    return False


def _is_filler(text: str) -> bool:
    key = _norm_key(text)
    if not key or _is_generic_claim(text) or _is_usage_instruction(text):
        return True
    return (
        key.startswith("detalle propio")
        or key.startswith("uso concreto")
        or key.startswith("beneficio ")
        or key.startswith("punto ")
        or key == "dato"
        or key.startswith("dato ")
    )


def _remember_or_replace(text: str, pool: list[str], used: set[str], idx: int, *, allow_synthetic: bool) -> str:
    raw = (text or "").strip()
    key = _norm_key(raw)
    if raw and key and key not in used and not _is_filler(raw):
        used.add(key)
        return raw[:48]
    replacement = _pick_unique(pool, used, idx, "Detalle propio", allow_synthetic=allow_synthetic)
    if replacement and not _is_filler(replacement):
        return replacement
    if raw and key and key not in used and not _is_filler(raw):
        used.add(key)
        return raw[:48]
    return ""


_INTRO_BY_VOICE: tuple[tuple[str, ...], ...] = (
    (
        "{c}. {need}",
        "{c}. {need}",
        "{c}. {need}",
        "{c}. {need}",
    ),
)

_EXTRA_PROOFS = (
    "Se ve al usarlo",
    "Queda en el acabado",
    "Detalle de cerca",
    "En la rutina diaria",
    "Textura que acompaña",
    "Resultado que se queda",
    "Listo para el día",
    "Cuidado visible",
    "Toque agradable",
    "Acabado uniforme",
    "Uso de verdad",
    "Se siente al momento",
    "Aspecto más limpio",
    "Mejor de cerca",
    "Para todos los días",
    "Sin complicarte",
    "Efecto en la mano",
    "Calidad que se ve",
    "Bienestar al momento",
    "Acabado que acompaña",
    "Rutina más simple",
    "Detalle que se queda",
    "Uso cómodo de verdad",
    "Se entiende de inmediato",
)

_HEADLINE_TAILS = (
    "que se nota",
    "en cada uso",
    "de verdad",
    "desde hoy",
    "sin esfuerzo",
    "para verte bien",
    "que se siente",
    "en tu rutina",
    "con buen acabado",
)

_SUPPORT_BY_ZONE = {
    "hair": [
        "Luz en el cabello",
        "Peine que desliza",
        "Tacto sedoso",
        "Sin resecar",
        "Acabado pulido",
        "Mas manejable",
        "Raiz con cuerpo",
        "Puntas con vida",
        "Brillo de salon",
        "Sin apelmazar",
        "Cabello disciplinado",
        "Suave al paso",
        "Definido sin rigidez",
        "Olor limpio",
        "Listo para salir",
        "Brillo al moverte",
        "Cabello con cuerpo",
        "Sedoso de verdad",
        "Puntas selladas",
        "Sin electricidad",
        "Movimiento con brillo",
        "Cabello que cae bien",
        "Tacto después del lavado",
    ],
    "oral": [
        "Sonrisa mas limpia",
        "Frescura que dura",
        "Cepillado comodo",
        "Boca con frescura",
        "Esmalte cuidado",
        "Aliento de cerca",
        "Limpieza suave",
        "Brillo al sonreir",
        "Boca fresca al hablar",
        "Cepillo que desliza",
        "Sensación de limpio",
        "Sonrisa de cerca",
        "Aliento más neutro",
        "Cuidado al cepillar",
    ],
    "skin_face": [
        "Piel con luz",
        "Tacto comodo",
        "Se absorbe bien",
        "Aspecto descansado",
        "Hidrata sin grasa",
        "Tono mas parejo",
        "Sensacion ligera",
        "Piel con vida",
        "Rostro más descansado",
        "Toque que se absorbe",
        "Piel suave al tacto",
        "Luz en el rostro",
        "Acabado sin brillo graso",
        "Cuidado de mañana",
    ],
    "body_hand": [
        "Piel nutrida",
        "Toque comodo",
        "Se absorbe pronto",
        "Manos suaves",
        "Sin film graso",
        "Cuidado al momento",
        "Manos listas al momento",
        "Piel que no tira",
        "Toque seco y suave",
        "Cuidado entre tareas",
        "Acabado cómodo",
        "Piel flexible",
    ],
    "body_bath": [
        "Espuma que limpia",
        "Piel fresca",
        "Aroma en la ducha",
        "Enjuague limpio",
        "Piel comoda",
        "Sensacion ligera",
        "Piel limpia al salir",
        "Ducha que refresca",
        "Aroma que se queda",
        "Toalla y piel suave",
        "Enjuague sin velo",
        "Cuerpo más ligero",
    ],
    "home_clean": [
        "Brillo en la superficie",
        "Grasa que sale",
        "Olor a limpio",
        "Sin velo",
        "Accion en minutos",
        "Deja la zona lista",
        "Espuma que trabaja",
        "Acabado claro",
        "Superficie sin marcas",
        "Cocina que brilla",
        "Limpieza que se ve",
        "Zona lista al momento",
        "Toque sin residuo",
        "Brillo sin esfuerzo",
    ],
    "nail_fungus": [
        "Menos mancha a la vista",
        "Uña menos opaca",
        "Borde más prolijo",
        "Tono más parejo",
        "Se ve más cuidada",
        "Menos tono amarillo",
        "Cuidado visible en la uña",
        "Para mostrar las uñas",
        "La mancha se nota menos",
        "Aspecto más fresco",
        "El borde se ve mejor",
        "Rutina directa en la uña",
        "Se nota en la uña",
        "Deja de verse descuidada",
        "Tono más claro a la vista",
        "Cuidado del día en la uña",
        "Aspecto más limpio al mirar",
        "Sin esconder los dedos",
        "Uña más presentable",
        "Menos aspecto descuidado",
        "Cuidado constante de la uña",
        "La mancha pierde presencia",
        "Uña con aspecto más fresco",
        "Se puede enseñar la uña",
    ],
    "body_deo": [
        "Axila fresca",
        "Protección del día",
        "Toque que seca",
        "Sin residuo blanco",
        "Fresco al vestirte",
        "Axila cómoda",
        "Aplicación precisa",
        "Confianza al salir",
        "Olor bajo control",
        "Listo en segundos",
    ],
    "generic": [
        "Se ve en el acabado",
        "Textura que se siente",
        "Detalle que importa",
        "Acabado prolijo",
        "Para el uso real",
        "Se nota de cerca",
        "Queda uniforme",
        "Cuidado concreto",
        "Listo al usarlo",
        "Efecto en la rutina",
        "Detalle del empaque",
        "Uso que se entiende",
        "Acabado de primera",
        "Cuidado del material",
        "Presentación clara",
        "Beneficio en la mano",
    ],
}


def _uses_spanish_copy(plan: dict) -> bool:
    loc = (plan.get("locale") or "").lower().replace("_", "-")
    lang = (plan.get("on_image_language") or "").lower()
    if loc.startswith("es") or "spanish" in lang or "mexic" in lang:
        return True
    return False


def _filled_panel_mandate(plan: dict) -> str:
    tpl = (plan.get("plan_template") or "").strip()
    if tpl == "amazon_listing_7":
        zero = "The white-catalog frame has ZERO added marketing text."
    else:
        zero = "Index 2 (white catalog) and Index 4 (before/after) have ZERO added marketing text."
    return (
        "ON-IMAGE TEXT — CRITICAL: no Chinese characters. "
        f"{zero} "
        "Every other frame carries a designed title group: "
        "a bold headline, a two-line introduction that explains that same benefit, and three proof lines. "
        "Follow THIS set's TITLE TREATMENT exactly. A color block and a thin underline are different treatments; use only the one named for this set. "
        "Letters are big enough to read on a phone. "
        "The photograph fills the rest of the frame edge to edge, with the product, the setting, and related props. "
        "A tiny corner title or a mostly empty photo is invalid. "
        "One benefit only. Do not print Step 1 or Step 2."
    )


def _intro_sentence(
    claim: str,
    used: set[str],
    index: int,
    *,
    seed: int = 0,
    needs: list[str] | None = None,
) -> str:
    c = (claim or "").strip().rstrip(".")
    if not c:
        return ""
    need = ""
    while needs:
        cand = needs.pop(0).strip().rstrip(".")
        if cand and _norm_key(cand) not in used and not _is_filler(cand):
            need = cand
            break
    voice = _INTRO_BY_VOICE[seed % len(_INTRO_BY_VOICE)]
    n = len(voice)
    for i in range(n):
        pattern = voice[(index + i) % n]
        if "{need}" in pattern and not need:
            continue
        line = pattern.format(c=c, need=need)[:120]
        key = "intro " + _norm_key(line)
        if key and key not in used and not _is_filler(line):
            used.add(key)
            if need:
                used.add(_norm_key(need))
            return line
    return ""


_TITLE_SHAPES = (
    "{c}",
    "{c}",
    "{c}",
)


def _variation_nonce(plan: dict) -> int:
    try:
        nonce = int(plan.get("listing_variation_nonce") or 0)
    except (TypeError, ValueError):
        nonce = 0
    if nonce:
        return nonce
    from generation.services.listing_visual_cohesion import ensure_listing_variation

    ensure_listing_variation(plan)
    return int(plan["listing_variation_nonce"])


def _fuller_headline(claim: str, used: set[str], index: int = 0, nonce: int = 0) -> str:
    text = (claim or "").strip().rstrip(".")
    if not text:
        return ""
    n = len(_TITLE_SHAPES)
    for step in range(n):
        shape = _TITLE_SHAPES[(nonce + index + step) % n]
        line = shape.format(c=text)[:56]
        key = _norm_key(line)
        if key and key not in used and not _is_filler(line):
            used.add(key)
            used.add(_norm_key(text))
            return line
    used.add(_norm_key(text))
    return text[:56]


def _support_lines(zone: str, claims: list[str], used: set[str], seed: int = 0) -> list[str]:
    bank = list(claims)
    bank.extend(_rotate(list(_SUPPORT_BY_ZONE.get(zone) or _SUPPORT_BY_ZONE["generic"]), seed))
    out: list[str] = []
    seen: set[str] = set()
    for item in bank:
        text = str(item).strip()
        key = _norm_key(text)
        if not key or key in used or key in seen or _is_filler(text) or _is_usage_instruction(text):
            continue
        seen.add(key)
        out.append(text[:40])
    return out


_PLACEHOLDER_WORD = re.compile(
    r"detalle propio(?:\s*\d+)?|uso concreto(?:\s*\d+)?|punto\s*\d+",
    re.I,
)


def _scrub_placeholder_copy(shot: dict) -> None:
    """占位编号不是卖点，不能留在任何会画到图上的字段里。"""
    for key in (
        "headline_es",
        "subhead_es",
        "assigned_primary_message_es",
        "prompt_es",
        "key_message_es",
    ):
        if _is_filler(str(shot.get(key) or "")):
            shot[key] = ""
    bullets = shot.get("icon_bullets_es") or []
    if isinstance(bullets, list):
        shot["icon_bullets_es"] = [b for b in bullets if str(b).strip() and not _is_filler(str(b))]
    for key in (
        "on_image_text_non_negotiable_en",
        "on_image_text_required_en",
        "usp_message_lock",
        "exclusive_usp_en",
    ):
        if _PLACEHOLDER_WORD.search(str(shot.get(key) or "")):
            shot[key] = ""
    diversity = str(shot.get("diversity_lock") or "")
    diversity = re.sub(r"USP exclusivity — this frame owns: '[^']*';?", "", diversity)
    diversity = _PLACEHOLDER_WORD.sub("", diversity).strip()
    headline = (shot.get("headline_es") or "").strip()
    if headline and not _is_filler(headline):
        diversity = (
            f"{diversity} USP exclusivity — this frame owns: '{headline}'; "
            "do not repeat other frames' callouts."
        ).strip()
    shot["diversity_lock"] = diversity


def _take_support(lines: list[str], used: set[str]) -> str:
    while lines:
        text = lines.pop(0).strip()
        key = _norm_key(text)
        if not key or key in used or _is_filler(text):
            continue
        used.add(key)
        return text
    return ""


def enforce_unique_selling_copy(plan: dict, pool: list[str] | None = None, *, fill_gaps: bool = False) -> dict:
    """每张图一个核心卖点，并用两行介绍和三个要点把这个卖点写完整。"""
    analysis = plan.get("product_analysis") or {}
    claims = list(pool or _marketing_text_pool(plan, analysis, _text_list(analysis.get("key_selling_points"))))
    nonce = _variation_nonce(plan)
    claims = _rotate(claims, nonce)
    used: set[str] = set()

    shots = []
    for shot in plan.get("shots") or []:
        if _overlay_blocked(plan, shot):
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["icon_bullets_es"] = []
            shot["assigned_primary_message_es"] = ""
            shot["prompt_es"] = ""
            shot["key_message_es"] = ""
            continue
        had_copy = any(
            (
                (shot.get("headline_es") or "").strip(),
                (shot.get("subhead_es") or "").strip(),
                shot.get("icon_bullets_es"),
                (shot.get("assigned_primary_message_es") or "").strip(),
            )
        )
        if fill_gaps or had_copy:
            shots.append(shot)

    for shot in shots:
        try:
            index = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            index = 0
        bits = [
            shot.get("headline_es") or "",
            shot.get("assigned_primary_message_es") or "",
            shot.get("subhead_es") or "",
        ]
        bullets = shot.get("icon_bullets_es") or []
        if isinstance(bullets, str):
            bullets = [s.strip() for s in bullets.split("|") if s.strip()]
        bits.extend(str(b) for b in bullets)

        def _claim_rank(text: str) -> int:
            key = _norm_key(text)
            for i, claim in enumerate(claims):
                if _norm_key(claim) == key:
                    return i
            return 1000

        ordered = sorted(
            [str(b).strip() for b in bits if str(b).strip() and not _is_filler(str(b))],
            key=_claim_rank,
        )
        best_bit = ""
        for cand in ordered:
            if _norm_key(cand) not in used:
                best_bit = cand.strip()
                break
        pool_next = ""
        for claim in claims:
            if _norm_key(claim) not in used and not _is_filler(claim):
                pool_next = claim.strip()
                break
        headline = best_bit
        if fill_gaps and pool_next and (not best_bit or _claim_rank(pool_next) < _claim_rank(best_bit)):
            headline = pool_next
        if headline:
            used.add(_norm_key(headline))
        elif fill_gaps:
            headline = _remember_or_replace("", claims, used, index, allow_synthetic=False)
        shot["headline_es"] = (headline or "")[:56]
        shot["assigned_primary_message_es"] = shot["headline_es"]

    zone = (analysis.get("application_zone") or "generic").strip()
    supports = _support_lines(zone, claims, used, nonce)
    extras = [] if (analysis.get("application_zone") or "") == "nail_fungus" else _rotate(list(_EXTRA_PROOFS), nonce)
    needs = _rotate(_need_lines(analysis), nonce)
    spanish = _uses_spanish_copy(plan)
    for shot in shots:
        raw = (shot.get("headline_es") or "").strip()
        if not raw or _is_filler(raw):
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["icon_bullets_es"] = []
            shot["assigned_primary_message_es"] = ""
            shot["prompt_es"] = ""
            shot["key_message_es"] = ""
            shot["exclusive_usp_en"] = ""
            shot["usp_message_lock"] = ""
            _scrub_placeholder_copy(shot)
            continue
        try:
            index = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            index = 0
        h = _fuller_headline(raw, used, index, nonce)
        sub = _intro_sentence(raw, used, index, seed=nonce + index, needs=needs) if spanish else ""
        if not sub:
            sub = _take_support(supports, used)
        icons = []
        for _ in range(3):
            tag = _take_support(supports, used) or _take_support(extras, used)
            if not tag:
                break
            icons.append(tag[:42])
        shot["headline_es"] = h
        shot["assigned_primary_message_es"] = h
        shot["subhead_es"] = (sub or "")[:120]
        shot["icon_bullets_es"] = icons
        shot["prompt_es"] = h
        shot["key_message_es"] = h
        shot["on_image_text_density"] = "rich"
        shot["composition_density_lock"] = FILLED_FRAME_LOCK_EN
        shot["exclusive_usp_en"] = (
            f"This frame sells only «{raw}», with a large text panel: headline, a two-line introduction, and three proof lines."
        )
        shot["on_image_text_layout_en"] = (
            "DESIGNED TITLE — bold headline, a two-line introduction, and three proof lines "
            "for this frame's one benefit. Follow the set TITLE TREATMENT. "
            "Render THIS set's TITLE TREATMENT exactly. "
            "The photo fills the rest edge to edge. Not a tiny corner title. Not an empty card."
        )
        tags = " | ".join(icons)
        shot["on_image_text_non_negotiable_en"] = (
            "Render a designed title, not a small label. Obey THIS set's TITLE TREATMENT, including a color block when that is the named treatment. "
            f"Render this product's own headline exactly, not a stock slogan: «{h}». "
            f"Two-line introduction: «{sub}». Three proof lines: {tags or 'none'}. "
            "All of that copy explains this one benefit. "
            "Do not print Step 1 / Step 2, and do not reuse another frame's wording. "
            "Fill the photograph edge to edge. A sparse image is invalid."
        )
        shot["on_image_text_required_en"] = shot["on_image_text_non_negotiable_en"]
        shot["usp_message_lock"] = shot["on_image_text_non_negotiable_en"]
        _scrub_placeholder_copy(shot)
    mandate = _filled_panel_mandate(plan)
    plan["listing_usp_diversity_lock_en"] = (
        "USP DIVERSITY — Each text frame owns one benefit. "
        "Headline, two-line introduction, and three proof lines stay unique across the set "
        "and explain that benefit inside a filled frame."
    )
    plan["on_image_text_density_mandate_en"] = mandate
    plan["on_image_text_mandate_en"] = mandate
    plan["listing_typography_mandate_en"] = mandate
    return plan


def _message_for_frame(
    index: int,
    role: str,
    *,
    es_pool: list[str],
    usps_cn: list[str],
    pains: list[str],
    trust: list[str],
    used: set[str],
) -> tuple[str, str, str]:
    """返回 (exclusive_usp_en, primary_message_es, text_layout_hint_en)."""
    fb = es_pool[index % len(es_pool)] if es_pool else "Calidad"

    if index == 1:
        h = _pick_unique(es_pool, used, 0, "Tu mejor opción")
        bullets = []
        for bi in range(3):
            bullets.append(_pick_unique(es_pool, used, bi + 1, f"Beneficio {bi + 1}"))
        en = (
            f"Hero scroll-stopper: {h}; icon bullets: {', '.join(bullets)}. "
            "Visual punch (contrast, depth, lighting, color) dominates thumbnail."
        )
        return (
            en,
            h,
            "MAX visual impact for TikTok feed + two-line Spanish headline + 3 icon bullets; product hero 40–52% frame.",
        )

    if index == 2:
        return (
            "White catalog — no marketing copy",
            "",
            "NO on-image marketing text — product on pure white only; factory packaging print allowed.",
        )

    if role == "pain_empathy":
        v3 = "product_detail_macro"  # caller sets via shot - check shot
        es = _pick_unique(es_pool, used, index, fb)
        en = f"Frame 3 benefit/detail angle: {es}"
        return en, es, "One short Spanish callout (2–5 words) OR minimal label near macro detail."

    if role == "usp_primary":
        es = _pick_unique(es_pool, used, index, "Resultado visible")
        en = "Frame 4 visual before/after — no on-image text"
        return (
            en,
            "",
            "No on-image typography — pure visual contrast only.",
        )

    if role == "usp_secondary":
        es = _pick_unique(es_pool, used, index + 3, fb)
        en = f"Secondary info frame: {es}"
        return (
            en,
            es,
            "1–3 short Spanish tags or step numbers as required by frame-5 variant; keep scannable.",
        )

    if role == "trust_quality":
        es = _pick_unique(es_pool, used, index, "Bienestar diario")
        return (
            f"Frame 6 usage benefit: {es}",
            es,
            "ONE bold Spanish benefit headline (4–8 words) REQUIRED on image + optional 1–2 short tags.",
        )

    if role == "ease_objection":
        es = _pick_unique(es_pool, used, index + 2, "Hecho para ti")
        return (
            f"Social proof audience: {es}",
            es,
            "REQUIRED Spanish UGC-style headline or sticker (3–6 words); clearly readable on image.",
        )

    if role == "value_stack":
        es = _pick_unique(es_pool, used, index + 1, "Gran valor")
        return (
            f"Value/kit message: {es}",
            es,
            "Short Spanish qty/value callouts near kit items (2 words each).",
        )

    es = _pick_unique(es_pool, used, index, fb)
    return f"Frame {index} message: {es}", es, "One short Spanish callout (2–5 words)."


def apply_listing_usp_distribution(plan: dict) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan, listing_image_count

    if not is_listing_ecommerce_plan(plan):
        enforce_unique_selling_copy(plan, fill_gaps=False)
        return plan

    analysis = plan.get("product_analysis") or {}
    usps_cn = _text_list(analysis.get("key_selling_points"))
    pains = _text_list(analysis.get("pain_points"))
    trust = _text_list(analysis.get("trust_signals"))
    es_pool = _marketing_text_pool(plan, analysis, usps_cn)
    # 去重保序
    seen: set[str] = set()
    deduped: list[str] = []
    for s in es_pool:
        k = s.lower()[:40]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(s)
    es_pool = deduped

    used_keys: set[str] = set()
    roster_es: dict[int, str] = {}
    roster_en: dict[int, str] = {}

    for shot in plan.get("shots") or []:
        try:
            index = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()

        if index == 3 and (shot.get("frame3_variant") or "") == "product_detail_macro":
            role = "pain_empathy_detail"

        tpl = (plan.get("plan_template") or "").strip()
        if tpl == "tk_mx_ecommerce_9" and index == 4:
            shot["on_image_text_density"] = "none"
            shot["assigned_primary_message_es"] = ""
            shot["exclusive_usp_en"] = "Frame 4 visual before/after — no overlay text"
            shot["on_image_text_layout_en"] = FRAME4_NO_TEXT_LOCK_EN
            shot["key_message_es"] = ""
            shot["prompt_es"] = ""
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["icon_bullets_es"] = []
            shot["frame4_no_text_lock_en"] = FRAME4_NO_TEXT_LOCK_EN
            shot["usp_message_lock"] = FRAME4_NO_TEXT_LOCK_EN
            shot.pop("on_image_text_required_en", None)
            roster_es[index] = "(sin texto)"
            roster_en[index] = "frame4_visual_only"
            continue

        if index == 2 or role == "white_bg_catalog":
            shot["on_image_text_density"] = "none"
            shot["assigned_primary_message_es"] = ""
            shot["exclusive_usp_en"] = "Compliance white background — zero overlay text"
            shot["on_image_text_layout_en"] = (
                "No headlines, captions, icons, or callouts — SKU on #FFFFFF seamless only."
            )
            shot["key_message_es"] = ""
            shot["prompt_es"] = ""
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["icon_bullets_es"] = []
            shot["usp_message_lock"] = (
                "INDEX 2 TEXT LOCK — Do not add any marketing typography; packaging label from product only."
            )
            roster_es[index] = "(sin texto)"
            roster_en[index] = "white_bg_no_text"
            continue

        if role == "lifestyle_payoff":
            v9 = (shot.get("frame9_variant") or "daily_essential").strip()
            cta = (shot.get("conversion_cta_es") or "").strip()
            es = cta if cta else _pick_unique(es_pool, used_keys, index + 4, "Compra ya")
            exclusive_en = (
                f"Frame 9 conversion close «{v9}» — purchase atmosphere, not packshot-only hero"
            )
            hint = _FRAME9_TEXT_HINTS.get(v9, _FRAME9_TEXT_HINTS["daily_essential"])
        elif role == "pain_empathy_detail":
            es = _pick_unique(es_pool, used_keys, index, "Detalle premium")
            exclusive_en = f"Craft/detail story: {es}"
            hint = "One Spanish craft keyword (Material / Calidad / Diseño) near macro."
        else:
            exclusive_en, es, hint = _message_for_frame(
                index,
                role,
                es_pool=es_pool,
                usps_cn=usps_cn,
                pains=pains,
                trust=trust,
                used=used_keys,
            )

        shot["exclusive_usp_en"] = exclusive_en
        shot["assigned_primary_message_es"] = es
        shot["on_image_text_layout_en"] = hint
        shot.setdefault("key_message_es", es)
        if not (shot.get("prompt_es") or "").strip():
            shot["prompt_es"] = es

        density = TEXT_DENSITY_BY_INDEX.get(index, "light")
        shot["on_image_text_density"] = density

        if index == 1:
            from generation.services.tk_mx_listing import HERO_VISUAL_IMPACT_EN

            shot["hero_visual_impact_lock"] = HERO_VISUAL_IMPACT_EN
            shot.setdefault("headline_es", es)
            if not (shot.get("subhead_es") or "").strip() or _is_generic_claim(shot.get("subhead_es") or ""):
                shot["subhead_es"] = _pick_unique(es_pool, used_keys, index + 8, "Detalle propio")[:50]
            bullets = shot.get("icon_bullets_es") or []
            if not bullets:
                shot["icon_bullets_es"] = [
                    _pick_unique(es_pool, used_keys, index + i, f"Punto {i}")[:24]
                    for i in range(1, 4)
                ]

        roster_es[index] = es
        roster_en[index] = exclusive_en

        lock = (shot.get("diversity_lock") or "").strip()
        shot["diversity_lock"] = (
            f"{lock} USP exclusivity — this frame owns: '{es}'; "
            "do not repeat other frames' callouts."
        ).strip()

        shot["usp_message_lock"] = (
            f"USP MESSAGE LOCK — Primary Spanish line for this frame only: «{es}». "
            f"{hint} Typography must be readable and dominant vs background."
        )
        shot["on_image_text_required_en"] = (
            f"MANDATORY ON-IMAGE SPANISH — You MUST render visible marketing typography in the output: "
            f"primary line «{es}» ({hint}). Image without readable Spanish text is incorrect."
        )
        extra_neg = (shot.get("negative_extra") or "").strip()
        if TEXT_REQUIRED_NEGATIVE.split(",")[0] not in extra_neg:
            shot["negative_extra"] = f"{extra_neg}, {TEXT_REQUIRED_NEGATIVE}".strip(", ")

    plan["listing_message_roster_es"] = roster_es
    plan["listing_message_roster_en"] = roster_en
    n_frames = listing_image_count(plan)
    plan["listing_usp_diversity_lock_en"] = (
        f"USP DIVERSITY — All {n_frames} frames carry DIFFERENT primary selling angles. "
        "Never repeat the same benefit headline, icon bullet, or callout wording across frames."
    )
    plan["on_image_text_density_mandate_en"] = (
        plan.get("listing_typography_mandate_en") or TYPOGRAPHY_MANDATE_EN
    )
    from generation.services.listing_tk_frame_role import MEDIUM_RICH_LAYOUT_EN

    tpl = (plan.get("plan_template") or "").strip()
    for shot in plan.get("shots") or []:
        try:
            index = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if tpl == "tk_mx_ecommerce_9" and index in (2, 4):
            continue
        if index == 2:
            continue
        es = (shot.get("assigned_primary_message_es") or shot.get("key_message_es") or "").strip()
        if not es or _is_generic_claim(es):
            es = _pick_unique(es_pool, used_keys, index + 3, "Detalle propio")
            shot["assigned_primary_message_es"] = es
        if not (shot.get("headline_es") or "").strip() or _is_generic_claim(shot.get("headline_es") or ""):
            shot["headline_es"] = es[:56]
        if not (shot.get("subhead_es") or "").strip() or _is_generic_claim(shot.get("subhead_es") or ""):
            shot["subhead_es"] = _pick_unique(es_pool, used_keys, index + 11, "Uso concreto")[:48]
        bullets = [str(b).strip() for b in (shot.get("icon_bullets_es") or []) if str(b).strip()]
        fresh: list[str] = []
        local_keys = {_norm_key(shot.get("headline_es") or ""), _norm_key(shot.get("subhead_es") or "")}
        for i, bullet in enumerate(bullets):
            key = _norm_key(bullet)
            if not key or _is_generic_claim(bullet) or key in local_keys or key in used_keys:
                nxt = _pick_unique(es_pool, used_keys, index + 20 + i, "Detalle propio", allow_synthetic=False)
                if nxt:
                    fresh.append(nxt[:22])
            else:
                used_keys.add(key)
                local_keys.add(key)
                fresh.append(bullet[:22])
        while len(fresh) < 2:
            nxt = _pick_unique(
                es_pool,
                used_keys,
                index + 30 + len(fresh),
                "Detalle propio",
                allow_synthetic=False,
            )
            if not nxt:
                break
            fresh.append(nxt[:22])
        shot["icon_bullets_es"] = fresh[:3]
        if not (shot.get("prompt_es") or "").strip():
            shot["prompt_es"] = f"{shot['headline_es']} — {shot.get('subhead_es', '')}".strip(" —")
        h, s, b = shot["headline_es"], shot.get("subhead_es") or "", shot.get("icon_bullets_es") or []
        if not (h or "").strip() or _is_filler(h) or _is_filler(s):
            if _is_filler(h):
                shot["headline_es"] = ""
            if _is_filler(s):
                shot["subhead_es"] = ""
            shot["on_image_text_non_negotiable_en"] = ""
            shot["on_image_text_required_en"] = ""
            _scrub_placeholder_copy(shot)
        else:
            shot["on_image_text_non_negotiable_en"] = (
                f"PRIORITY RICH TYPOGRAPHY — Headline: «{h}»; Subhead: «{s}»; "
                f"Icon tags: {', '.join(str(x) for x in b[:3])}. "
                f"{MEDIUM_RICH_LAYOUT_EN} Single-title-only output is INVALID."
            )
            shot["on_image_text_required_en"] = shot["on_image_text_non_negotiable_en"]

    enforce_unique_selling_copy(plan, es_pool, fill_gaps=True)
    plan["shots"] = plan.get("shots") or []
    return plan
