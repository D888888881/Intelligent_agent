"""TK 九图：开跑前写入每镜职能最高优先级文案，成图时置于 prompt 最前。"""

from __future__ import annotations

from generation.services.ecommerce_strategy import TK_MX_NINE_FRAME_MATRIX

_FRAME_BY_INDEX = {int(f["index"]): f for f in TK_MX_NINE_FRAME_MATRIX}

FRAME4_ROLE_SUPREMACY_EN = (
    "TK FRAME 4 ROLE SUPREMACY — This image is INDEX 4 ONLY: usp_primary, before_after_visual. "
    "Deliver ONE photo: MODEL + visible before→after transformation on the correct application zone + hero SKU. "
    "FORBIDDEN OUTPUT: trust lifestyle (frame 6), category compare (frame 5), hero-only poster (frame 1), "
    "white packshot (frame 2), step tutorial, generic product on counter with NO contrast. "
    "Ignore any other-frame instructions below that conflict with this role."
)

MEDIUM_RICH_LAYOUT_EN = (
    "DESIGNED TITLE — One core benefit, written out so the frame does not look empty: "
    "(1) a bold Spanish headline; "
    "(2) a two-line introduction that explains that same benefit in a full sentence; "
    "(3) three proof lines about that benefit only. "
    "Follow THIS set's TITLE TREATMENT exactly. Do not turn every set into a thin line, and do not drop the color block when this set asks for it. "
    "The type is large enough to read on a phone. "
    "The photo fills the rest edge to edge: setting, light, product, and several related props. "
    "Not an empty backdrop, not a tiny corner word, not a second selling point, not Step 1 / Step 2."
)

ROLE_PREAMBLE: dict[int, str] = {
    1: (
        "TK INDEX 1 — hero_hook: filled scroll-stopper scene plus a large Spanish text panel for ONE claim."
    ),
    2: "TK INDEX 2 — white_bg_catalog: pure white compliance, zero added text.",
    3: (
        "TK INDEX 3 — pain_empathy (batch variant): a filled benefit scene plus a large Spanish text panel for ONE claim."
    ),
    4: FRAME4_ROLE_SUPREMACY_EN,
    5: (
        "TK INDEX 5 — usp_secondary (flex variant): specs/compare/steps/kit/functions — "
        "one flex job only, with a filled scene and a large Spanish text panel for ONE claim."
    ),
    6: (
        "TK INDEX 6 — usage benefit: what the user gains after use; model allowed; "
        "a lived-in payoff scene that fills the frame; this frame's benefit as headline, two-line introduction, and three proof lines."
    ),
    7: (
        "TK INDEX 7 — ease_objection: MANDATORY model face + half/3/4 body using SKU in Mexico daily UGC; "
        "a real daily scene that fills the frame and a large Spanish text panel for ONE claim; NOT frame-4 compare."
    ),
    8: (
        "TK INDEX 8 — value_stack: a filled kit/spec scene plus a large Spanish text panel for ONE value claim."
    ),
    9: (
        "TK INDEX 9 — lifestyle_payoff: a filled closing scene plus a large Spanish text panel for ONE closing claim."
    ),
}


def apply_tk_frame_role_preambles(plan: dict) -> dict:
    if (plan.get("plan_template") or "") != "tk_mx_ecommerce_9":
        return plan

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        frame = _FRAME_BY_INDEX.get(idx) or {}
        shot["role"] = frame.get("role", shot.get("role"))
        shot["marketing_pillar"] = frame.get("marketing_pillar", shot.get("marketing_pillar"))
        shot["consumer_question"] = frame.get("consumer_question", shot.get("consumer_question"))

        pre = ROLE_PREAMBLE.get(idx, f"TK INDEX {idx} — execute fixed matrix role only.")
        shot["tk_frame_role_preamble_en"] = pre
        shot["tk_frame_role_supremacy_en"] = (
            f"MATRIX LOCK index={idx} role={shot.get('role')} pillar={shot.get('marketing_pillar')}. "
            f"{pre}"
        )

        if idx == 4:
            shot["ignore_non_role_plan_hints"] = True
            from generation.services.product_usage_semantics import zone_requires_model

            zone = (plan.get("product_analysis") or {}).get("application_zone") or ""
            if zone_requires_model(zone):
                shot["tk_frame_role_preamble_en"] = FRAME4_ROLE_SUPREMACY_EN
            else:
                shot["tk_frame_role_preamble_en"] = (
                    "TK FRAME 4 ROLE SUPREMACY — INDEX 4 ONLY: usp_primary, before_after_visual on "
                    "the cleaned OBJECT/SURFACE (e.g. toilet bowl, tile) — NO human model. "
                    "Hero cleaner SKU visible; pure visual stained→sparkling contrast; "
                    "zero antes/después/marketing overlay text. "
                    "FORBIDDEN: skin lotion compare, hair transform, trust lifestyle (frame 6)."
                )
            shot["tk_frame_role_supremacy_en"] = (
                f"MATRIX LOCK index={idx} role={shot.get('role')} pillar={shot.get('marketing_pillar')}. "
                f"{shot['tk_frame_role_preamble_en']}"
            )
        elif idx not in (2, 4):
            if not (shot.get("on_image_text_layout_en") or "").find("RICH TIKTOK") >= 0:
                shot["on_image_text_layout_en"] = (
                    f"{shot.get('on_image_text_layout_en') or ''} {MEDIUM_RICH_LAYOUT_EN}".strip()
                )

    plan["listing_tk_matrix_obey_en"] = (
        "TK NINE-FRAME CONTRACT — Generate each index ONLY per its matrix role; "
        "do not swap frame duties; conflicting instructions yield to tk_frame_role_preamble on that index."
    )
    return plan