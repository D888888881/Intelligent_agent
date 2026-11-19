"""全局 Creative Concept 模板（8 维差异化矩阵）。"""

from __future__ import annotations

from typing import Any

# 8 维键名（全库统一）
DIMENSION_KEYS = (
    "visual_style",
    "scene_environment",
    "color_palette",
    "lighting",
    "camera_language",
    "composition",
    "human_presence",
    "info_layout",
)

CREATIVE_CONCEPTS: list[dict[str, Any]] = [
    {
        "id": "minimalist_premium",
        "label_zh": "极简高级",
        "label_en": "Minimalist Premium",
        "generic_pack_name": "theme_minimal_scandi",
        "beauty_pack_offset": 0,
        "story_theme_en": (
            "CREATIVE CONCEPT — Minimalist Premium: negative space, calm premium staging, "
            "material honesty; NOT centered packshot on colored kitchen — asymmetric hero, breathing room."
        ),
        "color_mood_en": "off-white, pale sage, soft wood, airy highlights",
        "dimensions": {
            "visual_style": "minimalist premium",
            "scene_environment": "modern sparse home / scandi shelf",
            "color_palette": "off-white and pale sage",
            "lighting": "soft natural diffuse",
            "camera_language": "45° hero, clean wide details",
            "composition": "negative space, asymmetric balance",
            "human_presence": "minimal / none",
            "info_layout": "clean sparse callouts",
        },
        "hero_mandate_en": (
            "HERO — Minimalist premium scroll-stop: asymmetric product placement, generous negative space, "
            "single accent color block (not busy kitchen); depth via soft shadow and material close-up."
        ),
        "category_affinity": ("", "home", "kitchen", "generic"),
    },
    {
        "id": "vibrant_lifestyle",
        "label_zh": "活力生活",
        "label_en": "Vibrant Lifestyle",
        "generic_pack_name": "theme_bold_color_pop",
        "beauty_pack_offset": 1,
        "story_theme_en": (
            "CREATIVE CONCEPT — Vibrant Lifestyle: saturated produce, lived-in family kitchen, "
            "motion and warmth; emphasize in-use energy — NOT static product centered on empty counter."
        ),
        "color_mood_en": "citrus orange, fresh green, sun-washed yellows",
        "dimensions": {
            "visual_style": "vibrant lifestyle",
            "scene_environment": "busy family kitchen / dining",
            "color_palette": "green and orange accents",
            "lighting": "bright daylight, high key",
            "camera_language": "eye-level dynamic, 3/4 action",
            "composition": "visual impact, diagonal energy",
            "human_presence": "hands or half-body in use",
            "info_layout": "playful short callouts",
        },
        "hero_mandate_en": (
            "HERO — Vibrant lifestyle: ingredients splash color, diagonal composition, product in active context; "
            "avoid sterile catalog centering."
        ),
        "category_affinity": ("kitchen", "home", "generic", "beauty_skincare"),
    },
    {
        "id": "professional_studio",
        "label_zh": "专业棚拍",
        "label_en": "Professional Studio",
        "generic_pack_name": "theme_studio_editorial",
        "beauty_pack_offset": 2,
        "story_theme_en": (
            "CREATIVE CONCEPT — Professional Studio: controlled graphite/carbon environment, "
            "structure and engineering story; dramatic rim — NOT lifestyle kitchen reskin."
        ),
        "color_mood_en": "charcoal, gunmetal, crisp white rim light",
        "dimensions": {
            "visual_style": "professional tech studio",
            "scene_environment": "photo studio / dark sweep",
            "color_palette": "deep gray and steel",
            "lighting": "dramatic rim and specular",
            "camera_language": "macro structure, low angle hero",
            "composition": "structure showcase, technical",
            "human_presence": "none",
            "info_layout": "spec-driven tags",
        },
        "hero_mandate_en": (
            "HERO — Studio tech: dark gradient or graphite sweep, rim light on edges, 35° low-angle shows structure; "
            "no domestic kitchen background."
        ),
        "category_affinity": ("electronics", "kitchen", "generic", ""),
    },
    {
        "id": "warm_home_narrative",
        "label_zh": "温馨家居叙事",
        "label_en": "Warm Home Narrative",
        "generic_pack_name": "theme_warm_home",
        "beauty_pack_offset": 3,
        "story_theme_en": (
            "CREATIVE CONCEPT — Warm Home Narrative: sofa, family living, evening lamp glow; "
            "trust and daily ritual — distinct from bright kitchen or dark studio."
        ),
        "color_mood_en": "warm beige, soft amber lamp, cozy textiles",
        "dimensions": {
            "visual_style": "warm domestic editorial",
            "scene_environment": "living room / bedroom ritual",
            "color_palette": "beige and amber",
            "lighting": "warm practical lamps + window fill",
            "camera_language": "environmental wide, intimate medium",
            "composition": "layered foreground / background",
            "human_presence": "optional soft hands",
            "info_layout": "warm reassuring bullets",
        },
        "hero_mandate_en": (
            "HERO — Cozy home story: product on side table with lamp bokeh; layered depth; "
            "not white-center kitchen template."
        ),
        "category_affinity": ("home", "beauty_skincare", "generic", ""),
    },
    {
        "id": "outdoor_active",
        "label_zh": "户外动感",
        "label_en": "Outdoor Active",
        "generic_pack_name": "theme_outdoor_urban",
        "beauty_pack_offset": 4,
        "story_theme_en": (
            "CREATIVE CONCEPT — Outdoor Active: street, park, café patio; portability and fresh air; "
            "must read outdoor — NOT indoor kitchen with plants."
        ),
        "color_mood_en": "natural green, concrete, sun flare",
        "dimensions": {
            "visual_style": "outdoor active lifestyle",
            "scene_environment": "urban park / street café",
            "color_palette": "green and concrete neutral",
            "lighting": "natural sun, open shade",
            "camera_language": "wide lifestyle, walking motion",
            "composition": "environmental context dominant",
            "human_presence": "candid 3/4 using product",
            "info_layout": "short energetic CTAs",
        },
        "hero_mandate_en": (
            "HERO — Outdoor energy: sky or street bokeh, product in tote/hand context; wide crop; "
            "forbidden: identical indoor kitchen swap."
        ),
        "category_affinity": ("generic", "kitchen", "home", ""),
    },
    {
        "id": "premium_gift",
        "label_zh": "礼盒质感",
        "label_en": "Premium Gift",
        "generic_pack_name": "theme_premium_gift",
        "beauty_pack_offset": 5,
        "story_theme_en": (
            "CREATIVE CONCEPT — Premium Gift: marble, ribbon, unboxing delight; "
            "gifting motivation — distinct from daily kitchen or outdoor."
        ),
        "color_mood_en": "ivory marble, rose gold accent",
        "dimensions": {
            "visual_style": "premium gift editorial",
            "scene_environment": "marble console / unboxing",
            "color_palette": "ivory and rose gold",
            "lighting": "soft box, gentle specular",
            "camera_language": "elevated 3/4, flatlay kit",
            "composition": "gift staging, value spread",
            "human_presence": "hands exchange optional",
            "info_layout": "value and gift bullets",
        },
        "hero_mandate_en": (
            "HERO — Gift-worthy: marble or ribbon accent, premium elevation; "
            "not plain kitchen center product."
        ),
        "category_affinity": ("beauty_skincare", "home", "generic", ""),
    },
]


def concept_by_id(concept_id: str) -> dict | None:
    cid = (concept_id or "").strip()
    for c in CREATIVE_CONCEPTS:
        if c["id"] == cid:
            return c
    return None
