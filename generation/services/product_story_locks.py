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
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if not is_listing_ecommerce_plan(plan):
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
                "TRUST / REAL-LIFE CONTEXT — " + material + " "
                "Place SKU in a believable Mexican daily environment (home, bathroom, bedroom, kitchen, "
                "street café, or office); natural light, lived-in but tidy props; product legible and premium. "
                "Convey quality through authentic setting — NOT sterile white macro; NO dominant portrait "
                "(frame 7 owns creator crowd); differ from frame 3 problem still."
            )
            shot.setdefault("content_density", "balanced")

        if role == "pain_empathy" or idx == 3:
            if not (shot.get("story_beat_lock") or "").strip():
                shot["story_beat_lock"] = (
                    f"FRAME 3 — Benefit solve or SKU detail (batch variant); product analysis: "
                    f"{before or 'core pain points'} / usps from analysis. "
                    "Set by frame3_flex when applied."
                )

        if role == "ease_objection" or idx == 7:
            shot["story_beat_lock"] = (
                "SOCIAL PROOF BEAT — Target buyer sees someone like them using the product naturally; "
                "TikTok-style authentic seeding; eases 'not for me / too hard' objections; product in active use."
            )

        if (role == "lifestyle_payoff" or idx == 9) and not (shot.get("conversion_story_lock") or "").strip():
            shot["story_beat_lock"] = (
                f"CONVERSION CLOSE — {after or 'purchase-ready mood'}; "
                "daily/gift/family/worth-buy atmosphere; NOT packshot-only; "
                "avoid duplicating frame 3 problem still or frame 7 crowd-use pose."
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
        "each frame distinct camera distance (macro vs wide vs table-level) and product rotation; "
        "never nine similar front-facing packshots."
    )
    plan["shots"] = shots
    return plan
