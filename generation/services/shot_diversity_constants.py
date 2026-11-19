"""TK 九图差异化共享常量（避免 detail_shot / visual_batch 循环 import）。"""

from __future__ import annotations

FIXED_FRAME_ROLES = frozenset(
    {
        "hero_hook",
        "white_bg_catalog",
    }
)

CREATIVE_DETAIL_INDICES = (3, 6, 7, 8, 9)

AMAZON_CREATIVE_DETAIL_SPECS: dict[int, dict] = {
    4: {
        "action_code": "amazon_frame4_creative",
        "density": "balanced",
        "human": "none",
        "action_en": (
            "Amazon frame 4 — rotates before/after visual OR real-life scene immersion per batch; "
            "unique camera vs other six frames."
        ),
        "camera_short": "wide env 3/4",
    },
    5: {
        "action_code": "frame5_benefit_or_detail",
        "density": "balanced",
        "human": "none",
        "action_en": (
            "Amazon frame 5 — product detail macro, benefit visual, or full-frame ingredients; "
            "no duplicate white main or specs frame."
        ),
        "camera_short": "macro or env 3/4",
    },
    6: {
        "action_code": "amazon_feature_demo",
        "density": "balanced",
        "human": "hands",
        "action_en": (
            "Amazon frame 6 — active function demo: pour, spray, apply, open, assemble, or visible output; "
            "proves effect in one photo; hands allowed; not crowd portrait."
        ),
        "camera_short": "3/4 action",
    },
}

CREATIVE_DETAIL_SPECS: dict[int, dict] = {
    3: {
        "action_code": "frame3_benefit_or_detail",
        "density": "balanced",
        "human": "none",
        "action_en": (
            "Frame 3 flex fallback — either benefit-solve visual (comfort/space/storage/convenience) "
            "or product detail macro (material, label, craft); no portrait; differs from frame 4 and 6."
        ),
        "camera_short": "wide env 3/4",
    },
    6: {
        "action_code": "trust_real_life_scene",
        "density": "balanced",
        "human": "none",
        "action_en": (
            "Authentic Mexico daily-life trust scene: SKU naturally placed in a real room "
            "(bathroom shelf, kitchen counter, bedroom dresser, home sofa table, street café, or office desk); "
            "natural window light, subtle lived-in props, product readable and premium; "
            "NOT clinical white macro; NOT frame-3 problem clutter; no dominant face."
        ),
        "camera_short": "wide env 3/4",
    },
    7: {
        "action_code": "social_proof_in_use",
        "density": "balanced",
        "human": "full",
        "action_en": (
            "Target consumer using product in relatable Mexico lifestyle scene — TikTok organic seeding: "
            "natural light, candid half-body or 3/4, authentic expression, SKU in active use; "
            "NOT hands-only tutorial; NOT duplicate pain frame 3 or payoff frame 9 pose."
        ),
        "camera_short": "wide lifestyle 3/4",
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
    "duplicate pose as other listing frames, frame 6 collapsed to sterile clinical white macro only, "
    "frame 7 collapsed to hands-only macro, stiff catalog glamour pose, "
    "repeated applying-product action same as frame 9, identical problem-clutter bathroom as frame 3, "
    "third top-down flat lay, dense infographic text wall, generic stock model face repeated"
)
