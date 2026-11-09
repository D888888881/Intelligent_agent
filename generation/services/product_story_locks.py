"""从 product_analysis 抽取材质/成分/故事，写入各帧 prompt 锁。"""

from __future__ import annotations


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _analysis_blob(analysis: dict) -> str:
    parts: list[str] = []
    for key in (
        "primary_function",
        "visual_identity",
        "material_texture_en",
        "texture_description",
        "formula_description_en",
    ):
        v = analysis.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    parts.extend(_text_list(analysis.get("key_selling_points")))
    parts.extend(_text_list(analysis.get("key_ingredients")))
    parts.extend(_text_list(analysis.get("ingredients")))
    parts.extend(_text_list(analysis.get("trust_signals")))
    return " ".join(parts)[:1200]


def build_material_story_en(analysis: dict) -> str:
    ingredients = _text_list(analysis.get("key_ingredients")) or _text_list(
        analysis.get("ingredients")
    )
    texture = (
        (analysis.get("material_texture_en") or analysis.get("texture_description") or "")
        .strip()
    )
    if not texture:
        texture = (analysis.get("visual_identity") or "")[:280]
    ing_txt = ", ".join(ingredients[:5]) if ingredients else "hero active ingredients visible on label"
    return (
        f"Tangible material focus: {texture or 'show real product surface finish'}. "
        f"Ingredient story (visual, not dense text wall): {ing_txt}."
    )


def apply_product_story_locks(plan: dict) -> dict:
    if plan.get("plan_template") != "tk_mx_ecommerce_9":
        return plan

    analysis = plan.get("product_analysis") or {}
    if not analysis:
        return plan

    material = build_material_story_en(analysis)
    before = (analysis.get("before_use_state") or "").strip()
    after = (analysis.get("after_use_state") or "").strip()
    motivations = _text_list(analysis.get("purchase_motivations"))
    story_arc = (
        f"CONVERSION STORY — Motivation: {motivations[0] if motivations else 'solve skin concern'}. "
        f"Before: {before or 'problem state'}. After: {after or 'desired outcome'}. "
        "Each frame must advance ONE beat; avoid repeating the same bathroom mirror or flat-lay grid."
    )
    plan["conversion_story_lock_en"] = story_arc

    shots = plan.get("shots") or []
    for shot in shots:
        role = (shot.get("role") or "").strip()
        idx = int(shot.get("index") or 0)

        if role == "trust_quality" or idx == 6:
            shot["material_story_lock"] = (
                "TRUST / MATERIAL — " + material + " "
                "Macro or clinical product-only; show paste/stick/cream texture, grain, smear, or cross-section. "
                "Minimal typography; generous negative space; NO portrait face."
            )
            shot.setdefault("content_density", "minimal")

        if role == "pain_empathy" or idx == 3:
            shot["story_beat_lock"] = (
                f"PAIN BEAT — {before or 'pre-use problem'} — environmental or symbolic still; "
                "prefer product-in-context or skin texture crop without full face when budget is tight."
            )

        if role == "lifestyle_payoff" or idx == 9:
            shot["story_beat_lock"] = (
                f"PAYOFF BEAT — {after or 'post-use confidence'} — aspirational scene; "
                "product visible; avoid duplicating frame 3 pose or frame 7 hand gesture."
            )

        if role == "value_stack" or idx == 8:
            includes = _text_list(analysis.get("package_includes"))
            if includes:
                shot["story_beat_lock"] = (
                    "VALUE BEAT — Kit contents story: "
                    + "; ".join(includes[:6])
                    + ". One clear layout; not the same top-down grid as user's last batch."
                )

        if role == "hero_hook" or idx == 1:
            usps = _text_list(analysis.get("key_selling_points"))
            if usps:
                shot.setdefault(
                    "story_beat_lock",
                    f"HOOK — Lead with benefit '{usps[0]}' via product hero or single symbolic prop, not a model lineup.",
                )

    plan["layout_diversity_lock_en"] = (
        "LAYOUT DIVERSITY — No more than TWO top-down flat-lays in the full 9-frame set; "
        "no more than ONE bathroom mirror composition; alternate studio / outdoor / macro / infographic; "
        "each frame distinct camera distance (macro vs wide vs table-level)."
    )
    plan["shots"] = shots
    return plan
