"""TK 九图：每镜单一视觉焦点，禁止「又要又要」导致画面杂乱。"""

from __future__ import annotations

from generation.services.listing_bundle import is_listing_ecommerce_plan, listing_image_count

FOCUS_DISCIPLINE_EN = (
    "FRAME FOCUS — Each image sells ONE benefit, but the frame itself is a full commercial photo: "
    "setting, light, related props, and a large text panel that explains that one benefit. "
    "Forbidden: an empty backdrop, a lone bottle with one tiny word, a wide blank margin, "
    "a numbered step chart, or dumping every benefit of the set into one image."
)

CLUTTER_NEGATIVE = (
    "empty backdrop, lone product on a blank card, tiny one-word label only, "
    "numbered step chart, collage grid, every benefit crammed into one frame"
)

_VARIANT_FOCUS: dict[tuple[int, str], str] = {
    (3, "benefit_solve_visual"): (
        "FRAME 3 — BENEFIT SOLVE (single beat): pick ONE pain→relief idea from analysis; "
        "fill the frame with the product, the setting, and several related props; "
        "add a large Spanish text panel that explains that one benefit."
    ),
    (3, "product_detail_macro"): (
        "FRAME 3 — PRODUCT DETAIL: ONE large crop — cap seam, label edge, texture, or packaging print. "
        "Fill the frame with that detail plus a large Spanish text panel explaining this frame's benefit. "
        "NO before/after; no blank margin around a tiny crop."
    ),
    (3, "ingredient_composition"): (
        "FRAME 3 — INGREDIENT ONLY: ingredients and textures fill the frame; ZERO product bottle/tube; "
        "add a large Spanish text panel for this frame's one benefit; no SKU packshot."
    ),
    (4, "before_after_visual"): (
        "FRAME 4 — BEFORE→AFTER (one transformation): ONE visual contrast (lighting/hair/skin/smile/state); "
        "transformation subject ≥45% of frame; ONE Spanish benefit headline OK (not antes/después); "
        "FORBIDDEN comparison labels; do NOT add specs, kit items, or crowd scene; SKU visible once."
    ),
    (5, "category_compare"): (
        "FRAME 5 — CATEGORY COMPARE: side-by-side our SKU vs same-category generic ONLY; "
        "filled shared surface; a large Spanish text panel for this frame's one benefit."
    ),
    (5, "specs_features"): (
        "FRAME 5 — SPECS: product plus readable size/capacity cues, and a large Spanish text panel "
        "for this frame's one benefit. NOT a white catalog clone; no model."
    ),
    (5, "kit_contents"): (
        "FRAME 5 — KIT LIST: show what's included in ONE angled layout; inventory clarity; "
        "not a value price story (frame 8 owns value narrative when rotated)."
    ),
    (5, "usage_steps"): (
        "FRAME 5 — IN USE: one real use moment for this product; cropped hands OK; no face; "
        "do not draw a numbered step chart or Step 1 / Step 2 labels."
    ),
    (5, "core_functions"): (
        "FRAME 5 — CORE FUNCTIONS: one hero product in a filled scene, plus a large Spanish text panel "
        "for this frame's one benefit; not a second hero frame 1."
    ),
    (5, "ingredient_composition"): (
        "FRAME 5 — INGREDIENT FULL BLEED: ingredients only; no packaging."
    ),
}

_ROLE_FOCUS: dict[str, str] = {
    "hero_hook": (
        "FRAME 1 — HERO: ONE scroll-stopper idea, product large in a filled scene, plus a large Spanish "
        "text panel (headline, two-line introduction, three proof lines). NOT white catalog; "
        "NOT packing frame 4/5 jobs into hero."
    ),
    "white_bg_catalog": (
        "FRAME 2 — WHITE CATALOG: product only on #FFFFFF; zero marketing overlay; "
        "no props, no story, no people."
    ),
    "trust_quality": (
        "FRAME 6 — USAGE BENEFIT: show payoff the user feels after use; model optional; "
        "large Spanish text panel required — NOT frame-4 split before/after, NOT frame-7 UGC clone."
    ),
    "ease_objection": (
        "FRAME 7 — SOCIAL PROOF: ONE candid in-use moment; target buyer + product; "
        "UGC realism — NOT tutorial step grid, NOT white catalog."
    ),
    "value_stack": (
        "FRAME 8 — VALUE / KIT / SPECS: quantity, contents, or specs emphasis (per layout_subtype); "
        "NOT repeating frame 5's job; fill the frame and add this frame's large text panel."
    ),
    "lifestyle_payoff": (
        "FRAME 9 — CONVERSION CLOSE: ONE closing mood (daily/gift/family/smart buy/summary/aspiration); "
        "product and setting fill the frame; large text panel for this closing benefit; not a second hero."
    ),
}

_AMAZON_ROLE_INDEX: dict[int, str] = {
    1: "white_bg_catalog",
    2: "hero_hook",
}


def _variant_keys(shot: dict) -> list[str]:
    keys: list[str] = []
    for k in ("frame3_variant", "frame4_variant", "frame5_variant", "frame9_variant"):
        v = (shot.get(k) or "").strip()
        if v:
            keys.append(v)
    return keys


def _apply_density(shot: dict, level: str) -> None:
    locks = {
        "minimal": (
            "COMPOSITION DENSITY — Minimal: ONE visual subject; 1–2 props max; generous negative space; "
            "no visual noise."
        ),
        "balanced": (
            "COMPOSITION DENSITY — Full ad frame: hero product, a real use setting, "
            "2–4 related props, depth and light. Not an empty backdrop."
        ),
        "rich": (
            "COMPOSITION DENSITY — Fill the frame for this one benefit: "
            "a large text panel plus foreground, product, and background, all readable; several related props. "
            "Every prop and surface stays in the set theme color. Not a sparse card, not a new accent hue."
        ),
    }
    shot["composition_density_lock"] = locks.get(level, locks["balanced"])
    shot["on_image_text_density"] = "none" if level == "minimal" else shot.get("on_image_text_density") or "light"


def apply_listing_frame_focus(plan: dict) -> dict:
    if not is_listing_ecommerce_plan(plan):
        return plan
    tpl = (plan.get("plan_template") or "").strip()
    if tpl != "tk_mx_ecommerce_9" and tpl != "amazon_listing_7":
        pass

    plan["listing_frame_focus_discipline_en"] = FOCUS_DISCIPLINE_EN
    neg = (plan.get("negative_prompt") or "").strip()
    if "busy cluttered composition" not in neg:
        plan["negative_prompt"] = f"{neg}, {CLUTTER_NEGATIVE}".strip(", ")

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()
        focus: str | None = None

        for vk in _variant_keys(shot):
            focus = _VARIANT_FOCUS.get((idx, vk)) or _VARIANT_FOCUS.get((idx, vk.replace("-", "_")))
            if focus:
                break
        if tpl == "tk_mx_ecommerce_9" and idx == 4:
            focus = _VARIANT_FOCUS.get((4, "before_after_visual"))
        if not focus and role in _ROLE_FOCUS:
            focus = _ROLE_FOCUS[role]
        if tpl == "amazon_listing_7" and not focus:
            amz_role = _AMAZON_ROLE_INDEX.get(idx)
            if amz_role and amz_role in _ROLE_FOCUS:
                focus = _ROLE_FOCUS[amz_role]

        if focus:
            shot["frame_single_focus_en"] = focus
        else:
            shot["frame_single_focus_en"] = (
                f"FRAME {idx} — Execute only this slot's marketing role; one clear visual idea."
            )

        v3 = (shot.get("frame3_variant") or "").strip()
        v5 = (shot.get("frame5_variant") or "").strip()
        if role == "white_bg_catalog" or idx == 2:
            _apply_density(shot, "minimal")
            shot["on_image_text_density"] = "none"
        elif idx == 4:
            shot["on_image_text_density"] = "none"
        elif v3 == "product_detail_macro":
            _apply_density(shot, "minimal")
            shot.setdefault("on_image_text_density", "medium")
        elif v3 == "ingredient_composition" or v5 == "ingredient_composition":
            _apply_density(shot, "minimal")
        elif role in ("usp_primary",) or v3 == "benefit_solve_visual":
            _apply_density(shot, "rich")
        elif role in ("hero_hook", "trust_quality", "ease_objection", "value_stack", "lifestyle_payoff"):
            _apply_density(shot, "rich")

        extra = (shot.get("negative_extra") or "").strip()
        if CLUTTER_NEGATIVE.split(",")[0] not in extra:
            shot["negative_extra"] = f"{extra}, {CLUTTER_NEGATIVE}".strip(", ")

    n = listing_image_count(plan)
    plan["listing_nine_frame_doctrine_zh"] = (
        "墨西哥 TK 九图职能：①场景主图 ②白底合规 ③轮换(卖点对比/细节特写/成分) "
        "④前后对比纯视觉 ⑤轮换对比/规格/套装/步骤/功能/成分 ⑥真实生活信任 ⑦人群UGC ⑧规格或套装价值 ⑨强转化收尾。"
        f"共{n}张；每镜只突出一个职能焦点，禁止杂乱堆砌。"
    )
    return plan