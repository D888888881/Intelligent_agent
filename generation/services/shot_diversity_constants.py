"""TK 九图差异化共享常量（避免 detail_shot / visual_batch 循环 import）。"""

from __future__ import annotations

FIXED_FRAME_ROLES = frozenset(
    {
        "hero_hook",
        "white_bg_catalog",
        "usp_primary",
        "usp_secondary",
    }
)

CREATIVE_DETAIL_INDICES = (3, 6, 7, 8, 9)

CREATIVE_DETAIL_SPECS: dict[int, dict] = {
    3: {
        "action_code": "pain_env_story",
        "density": "balanced",
        "human": "none",
        "action_en": (
            "Problem-state still-life or skin-texture crop (no full face): cluttered routine, dull lighting, "
            "hero SKU small or unopened — empathy without portrait."
        ),
    },
    6: {
        "action_code": "trust_material_macro",
        "density": "minimal",
        "human": "none",
        "action_en": (
            "Material science macro: smear, grain, stick tip, or ingredient texture on neutral background; "
            "clinical trust, no model."
        ),
    },
    7: {
        "action_code": "usage_one_clear_step",
        "density": "balanced",
        "human": "hands",
        "action_en": (
            "Single usage step — hands only, one clear gesture; no duplicate mirror or cheek swipe from other frames."
        ),
    },
    8: {
        "action_code": "value_story_layout",
        "density": "balanced",
        "human": "none",
        "action_en": (
            "Value story with kit props — angled or shelf layout preferred over another identical top-down grid."
        ),
    },
    9: {
        "action_code": "payoff_product_lifestyle",
        "density": "minimal",
        "human": "none",
        "action_en": (
            "Post-use aspiration WITHOUT portrait: product in lifestyle context (window sill, café, gym bag), "
            "golden light, no application gesture."
        ),
    },
}

DETAIL_SHOT_NEGATIVE = (
    "duplicate pose as other listing frames, same hand gesture as frame 3 and 7, "
    "repeated applying-product action, identical bathroom mirror composition, "
    "third top-down flat lay, dense infographic text wall, generic stock model face repeated"
)
