"""套图卖点 / 痛点 / 需求可视化：按职能镜分配转化叙事，放大购买理由。"""

from __future__ import annotations

from generation.services.listing_bundle import is_listing_ecommerce_plan, listing_image_count
from generation.services.product_listing_narrative import product_summary_for_story

FRAME_STORY_ROLE: dict[str, str] = {
    "hero_hook": "Scroll-stopper: dramatize #1 purchase motivation and strongest USP at thumbnail scale.",
    "white_bg_catalog": "Compliance product truth — no story overlay.",
    "pain_empathy": "Visualize the pain relieved OR credible product detail proving quality.",
    "usp_primary": "Before→after transformation: make the core pain→outcome contrast obvious without comparison captions.",
    "usp_secondary": "Secondary proof: specs, compare, steps, kit, or functions — support objections.",
    "trust_quality": "Usage benefit: show what the user gains after using the product (felt payoff, not before/after split).",
    "ease_objection": "Social proof: target buyer like me is using it now — product in active use.",
    "value_stack": "Value: show kit contents, quantity, gift-worth — what I get for money.",
    "lifestyle_payoff": "Conversion close: after-use mood, routine essential, or gift — purchase confidence.",
}


def _text_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _pick(items: list[str], index: int, default: str) -> str:
    if not items:
        return default
    return items[index % len(items)]


def apply_listing_conversion_story(plan: dict) -> dict:
    if not is_listing_ecommerce_plan(plan):
        return plan

    analysis = plan.get("product_analysis") or {}
    strategy = plan.get("ecommerce_strategy") or {}

    pains = _text_list(analysis.get("pain_points") or strategy.get("pain_points"))
    usps = _text_list(analysis.get("key_selling_points") or strategy.get("core_usps"))
    motivations = _text_list(analysis.get("purchase_motivations") or strategy.get("purchase_motivations"))
    objections = _text_list(analysis.get("objections") or strategy.get("objections"))
    buyer = (strategy.get("target_buyer_zh") or analysis.get("target_buyer_zh") or "").strip()
    summary = product_summary_for_story(analysis, plan.get("user_prompt") or "", strategy)

    pain_txt = " | ".join(pains[:5]) if pains else "daily frustration before using the product"
    usp_txt = " | ".join(usps[:6]) if usps else "quality, easy to use, worth buying"
    mot_txt = " | ".join(motivations[:4]) if motivations else "solve problem, save time, feel confident"

    zone_en = (analysis.get("application_zone_en") or "").strip()
    zone_note = f" Application zone (non-negotiable): {zone_en}." if zone_en else ""

    plan["listing_conversion_master_en"] = (
        f"CONVERSION MASTER STORY — Buyer: {buyer or 'Mexico TikTok shopper'}. "
        f"Product: {summary}.{zone_note} "
        f"Core pains to empathize: {pain_txt}. "
        f"Core USPs to amplify visually (lighting, props, skin/smile/state, layout): {usp_txt}. "
        f"Purchase motivations: {mot_txt}. "
        f"Objections to ease in later frames: {' | '.join(objections[:4]) if objections else 'trust, ease, value'}. "
        "Every non-white frame must SHOW not tell — exaggerate benefit read at mobile size; "
        "do not dilute with generic lifestyle filler."
    )

    n = listing_image_count(plan)
    plan["listing_usp_roster_en"] = (
        f"USP ROSTER — Spread these angles across {n} frames without repeating headline text: {usp_txt}."
    )

    for shot in plan.get("shots") or []:
        role = (shot.get("role") or "").strip()
        if not role:
            continue
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            idx = 0
        if role == "white_bg_catalog" or idx == 2:
            shot["conversion_visual_lock_en"] = (
                "Compliance frame — product only; pains/USPs only via packaging print."
            )
            continue

        if role == "usp_primary":
            anchor = (analysis.get("product_efficacy_anchor_en") or "")[:700]
            auth4 = (analysis.get("frame4_authoritative_en") or "")[:900]
            shot["conversion_visual_lock_en"] = (
                "FRAME 4 CONVERSION — Visual before→after only (same product efficacy as hero Spanish copy). "
                f"{anchor} {auth4}".strip()
            )[:2200]
            continue

        story = FRAME_STORY_ROLE.get(role, "Support conversion with distinct visual story beat.")
        pain_pick = _pick(pains, idx, "unresolved daily pain")
        usp_pick = _pick(usps, idx, "core benefit")
        shot["conversion_visual_lock_en"] = (
            f"FRAME {idx} CONVERSION — {story} "
            f"Pick ONE pain facet: «{pain_pick}» OR ONE benefit: «{usp_pick}» — not both in equal weight. "
            "Single visual idea only; make it obvious at mobile thumbnail — no extra side stories."
        )
        if role == "ease_objection" and buyer:
            shot["conversion_visual_lock_en"] += f" Model matches target buyer: {buyer[:120]}."

    plan["listing_matrix_obey_en"] = (
        "LISTING MATRIX CONTRACT — Generate each frame ONLY per its fixed role "
        "(hero / white catalog / flex variants / trust / social proof / value / close). "
        "Do not swap frame duties; obey frame_contract and role on this index."
    )
    return plan