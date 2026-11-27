"""投放站点：图数、语言、场景地理、图上文案政策。"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_MARKETPLACE_ID = "tk_shop_mx"

ON_IMAGE_TEXT_MANDATE_ES_MX = (
    "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) anywhere. "
    "Marketing typography must be Spanish (México) and high-contrast. "
    "Except the white catalog and the before/after frame, each image needs a designed title: "
    "bold headline, a two-line introduction, and three proof lines about one benefit. "
    "Follow THIS set's TITLE TREATMENT exactly. Color block, thin line, side bar, outline type, and open margin are different sets, not one fixed look. "
    "Reproduce packaging label text EXACTLY from reference only. No English marketing unless user asked."
)

ON_IMAGE_TEXT_MANDATE_PT_BR = (
    "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) anywhere. "
    "Marketing typography must be Portuguese (Brazil), SHORT and high-contrast — each frame needs "
    "a focal message (not pure visual-only art). Hero: up to 2 headline lines + 3 icon bullets; "
    "other frames: 1–3 short callouts (2–6 words) OR compact spec/step tags. "
    "Reproduce packaging label text EXACTLY from reference only. No English marketing unless user asked."
)

ON_IMAGE_TEXT_MANDATE_EN = (
    "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) anywhere. "
    "Marketing typography must be English, SHORT and high-contrast — each frame needs "
    "a focal message (not pure visual-only art). Hero: up to 2 headline lines + 3 icon bullets; "
    "other frames: 1–3 short callouts (2–6 words) OR compact spec/step tags. "
    "Reproduce packaging label text EXACTLY from reference only."
)

MARKETPLACE_PROFILES: dict[str, dict[str, Any]] = {
    "tk_shop_mx": {
        "label_zh": "TikTok Shop · 墨西哥",
        "platform": "tiktok_shop",
        "plan_template": "tk_mx_ecommerce_9",
        "image_count": 9,
        "locale": "es-MX",
        "on_image_language": "Spanish (Mexico)",
        "on_image_text_mandate_en": ON_IMAGE_TEXT_MANDATE_ES_MX,
        "scene_geo_en": "Mexico",
        "scene_geo_adj_en": "Mexican",
        "scene_geo_display": "México",
        "listing_typography_mandate_en": (
            "ON-IMAGE TYPOGRAPHY — Index 2 and Index 4: ZERO added marketing text. "
            "Every other frame: a LARGE Spanish panel (headline, two-line introduction, three proof lines) "
            "covering about one third of the image, readable on a phone. The photo fills the rest. "
            "No Chinese except exact packaging from reference. No English marketing. No tiny one-line label."
        ),
        "doctrine_zh": (
            "全套 9 张均为 TikTok Shop México Listing 主图（1 场景分层主图 + 1 白底合规 + 7 职能详情）。"
        ),
        "listing_prompt_zh": (
            "分析该商品的作用，帮我制作9张商品主图，包括1张商品主图、1张商品白底图、7张商品详情图；"
            "面向 TikTok Shop 墨西哥站点，图中文字使用西班牙语，多视角展示商品，不要拼图。"
        ),
        "listing_prompt_chip_zh": "TK 墨西哥 · 9图",
    },
    "tk_shop_br": {
        "label_zh": "TikTok Shop · 巴西",
        "platform": "tiktok_shop",
        "plan_template": "tk_mx_ecommerce_9",
        "image_count": 9,
        "locale": "pt-BR",
        "on_image_language": "Portuguese (Brazil)",
        "on_image_text_mandate_en": ON_IMAGE_TEXT_MANDATE_PT_BR,
        "scene_geo_en": "Brazil",
        "scene_geo_adj_en": "Brazilian",
        "scene_geo_display": "Brasil",
        "listing_typography_mandate_en": (
            "ON-IMAGE TYPOGRAPHY — Index 1: bold Portuguese headline + icons BUT visual scroll-stop impact is primary. "
            "Index 2: ZERO added marketing text (white catalog — packaging label from product only). "
            "Frames 3–9: short Portuguese (Brazil) selling messages (2–6 words focal lines). "
            "No Chinese except exact packaging from reference. No English marketing. "
            "No paragraph walls — mobile TikTok legibility."
        ),
        "doctrine_zh": (
            "全套 9 张均为 TikTok Shop Brasil Listing 主图（职能与墨西哥站一致，场景为巴西日常生活，文案为葡语）。"
        ),
        "listing_prompt_zh": (
            "分析该商品的作用，帮我制作9张商品主图，包括1张商品主图、1张商品白底图、7张商品详情图；"
            "面向 TikTok Shop 巴西站点，图中文字使用葡萄牙语（巴西），多视角展示商品，不要拼图。"
        ),
        "listing_prompt_chip_zh": "TK 巴西 · 9图",
    },
    "amazon_us": {
        "label_zh": "Amazon · 美国",
        "platform": "amazon",
        "plan_template": "amazon_listing_7",
        "image_count": 7,
        "locale": "en-US",
        "on_image_language": "English",
        "on_image_text_mandate_en": ON_IMAGE_TEXT_MANDATE_EN,
        "scene_geo_en": "United States",
        "scene_geo_adj_en": "American",
        "scene_geo_display": "U.S.",
        "listing_typography_mandate_en": (
            "ON-IMAGE TYPOGRAPHY — Index 1: ZERO added marketing text (white main catalog). "
            "Index 2: bold English value headline + icons. Frames 3–7: short English callouts (2–6 words). "
            "No Chinese. Mobile legibility."
        ),
        "doctrine_zh": "Amazon Listing 7 图（白底主图→卖点→规格→对比/场景轮换→细节→演示→盒内）。",
        "listing_prompt_zh": (
            "分析该商品，制作 7 张 Amazon Listing 图：①白底主图 ②核心卖点 ③尺寸规格 ④痛点对比或场景代入(轮换) "
            "⑤细节品质 ⑥功能演示 ⑦包装配件；美国站，英文图上文案，多视角，不要拼图。"
        ),
        "listing_prompt_chip_zh": "Amazon 美国 · 7图",
    },
    "amazon_uk": {
        "label_zh": "Amazon · 英国",
        "platform": "amazon",
        "plan_template": "amazon_listing_7",
        "image_count": 7,
        "locale": "en-GB",
        "on_image_language": "English (UK)",
        "on_image_text_mandate_en": ON_IMAGE_TEXT_MANDATE_EN,
        "scene_geo_en": "United Kingdom",
        "scene_geo_adj_en": "British",
        "scene_geo_display": "UK",
        "listing_typography_mandate_en": (
            "ON-IMAGE TYPOGRAPHY — Index 1: ZERO added marketing text (white main). "
            "Index 2: bold English value headline. Frames 3–7: short callouts (2–6 words). No Chinese."
        ),
        "doctrine_zh": "Amazon Listing 7 图（白底主图→卖点→规格→对比/场景轮换→细节→演示→盒内）。",
    },
    "amazon_de": {
        "label_zh": "Amazon · 德国",
        "platform": "amazon",
        "plan_template": "amazon_listing_7",
        "image_count": 7,
        "locale": "de-DE",
        "on_image_language": "German",
        "on_image_text_mandate_en": (
            "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) anywhere. "
            "Marketing typography must be German, SHORT and high-contrast. "
            "Hero: up to 2 headline lines + 3 icon bullets; other frames: 1–3 short callouts (2–6 words). "
            "Packaging label from reference only."
        ),
        "scene_geo_en": "Germany",
        "scene_geo_adj_en": "German",
        "scene_geo_display": "Deutschland",
        "listing_typography_mandate_en": (
            "ON-IMAGE TYPOGRAPHY — Index 1: ZERO overlay marketing text (white main). "
            "Index 2: bold German value headline. Frames 3–7: short German callouts (2–6 words). No Chinese."
        ),
        "doctrine_zh": "Amazon Listing 7 图（白底主图→卖点→规格→对比/场景轮换→细节→演示→盒内）。",
    },
}


LISTING_PROMPT_PRESET_ORDER = ("tk_shop_mx", "tk_shop_br", "amazon_us")


def marketplace_catalog() -> list[dict[str, Any]]:
    rows = []
    for mid, p in MARKETPLACE_PROFILES.items():
        row = {
            "id": mid,
            "label": p["label_zh"],
            "platform": p["platform"],
            "image_count": p["image_count"],
            "plan_template": p.get("plan_template"),
        }
        prompt = (p.get("listing_prompt_zh") or "").strip()
        if prompt:
            row["listing_prompt_zh"] = prompt
            row["listing_prompt_chip_zh"] = (p.get("listing_prompt_chip_zh") or p["label_zh"]).strip()
        rows.append(row)
    return rows


def listing_prompt_presets() -> list[dict[str, Any]]:
    """输入框快捷话术（顺序固定，仅含已配置文案的站点）。"""
    out = []
    for mid in LISTING_PROMPT_PRESET_ORDER:
        p = MARKETPLACE_PROFILES.get(mid)
        if not p:
            continue
        prompt = (p.get("listing_prompt_zh") or "").strip()
        if not prompt:
            continue
        out.append(
            {
                "marketplace_id": mid,
                "chip_label": (p.get("listing_prompt_chip_zh") or p["label_zh"]).strip(),
                "prompt_zh": prompt,
                "plan_template": p.get("plan_template"),
                "image_count": p.get("image_count"),
            }
        )
    return out


def normalize_marketplace_id(marketplace_id: str | None) -> str:
    mid = (marketplace_id or "").strip()
    if mid in MARKETPLACE_PROFILES:
        return mid
    return DEFAULT_MARKETPLACE_ID


def resolve_effective_marketplace_id(
    *,
    request_marketplace: str | None = None,
    conversation=None,
    user=None,
) -> str:
    req = (request_marketplace or "").strip()
    if req in MARKETPLACE_PROFILES:
        return req

    if conversation is not None:
        cmid = (getattr(conversation, "marketplace_id", "") or "").strip()
        if cmid in MARKETPLACE_PROFILES:
            return cmid

    if user is not None and getattr(user, "is_authenticated", True):
        try:
            from accounts.models import UserProfile

            profile = UserProfile.objects.filter(user=user).first()
            if profile and (profile.preferred_marketplace_id or "").strip():
                return normalize_marketplace_id(profile.preferred_marketplace_id)
        except Exception:
            pass
    return DEFAULT_MARKETPLACE_ID


def coerce_generation_for_marketplace(
    marketplace_id: str,
    plan_template: str,
    image_count: int,
) -> tuple[int, str]:
    prof = MARKETPLACE_PROFILES.get(normalize_marketplace_id(marketplace_id))
    if not prof:
        return image_count, plan_template
    tpl = (plan_template or "auto").strip()
    locked = {"reference_guided", "photo_refine"}
    if tpl in locked:
        return image_count, tpl
    if tpl in ("auto", "generic", "") or tpl in ("tk_mx_ecommerce_9", "amazon_listing_7"):
        return int(prof["image_count"]), str(prof["plan_template"])
    return image_count, tpl


_GEO_REPLACEMENTS = (
    ("Mexican daily environment", "{adj} daily environment"),
    ("authentic Mexican daily", "authentic {adj} daily"),
    ("Mexico lifestyle", "{geo} lifestyle"),
    ("in Mexico", "in {geo}"),
    ("México", "{display}"),
    ("Mexico", "{geo}"),
    ("Mexican", "{adj}"),
    ("Spanish (México)", "{lang}"),
    ("Spanish (Mexico)", "{lang}"),
    ("Spanish headline", "{lang_short} headline"),
    ("Spanish ", "{lang_short} "),
    ("西语", "{lang_short}"),
)


def _substitute_geo_text(text: str, prof: dict[str, Any]) -> str:
    if not text:
        return text
    out = text
    lang = str(prof.get("on_image_language") or "Spanish")
    lang_short = lang.split("(")[0].strip() or lang
    tpl_vars = {
        "geo": prof.get("scene_geo_en") or "Mexico",
        "adj": prof.get("scene_geo_adj_en") or "Mexican",
        "display": prof.get("scene_geo_display") or prof.get("scene_geo_en") or "Mexico",
        "lang": lang,
        "lang_short": lang_short,
    }
    for pattern, repl_tpl in _GEO_REPLACEMENTS:
        repl = repl_tpl.format(**tpl_vars) if "{" in repl_tpl else repl_tpl
        out = out.replace(pattern, repl)
    for key, val in tpl_vars.items():
        out = out.replace(f"{{{key}}}", str(val))
    return out


def apply_marketplace_profile(plan: dict, marketplace_id: str | None) -> dict:
    mid = normalize_marketplace_id(marketplace_id)
    prof = MARKETPLACE_PROFILES[mid]
    plan["marketplace_id"] = mid
    plan["marketplace_label_zh"] = prof["label_zh"]
    plan["listing_platform"] = prof["platform"]
    plan["locale"] = prof["locale"]
    plan["on_image_language"] = prof["on_image_language"]
    plan["on_image_text_mandate_en"] = prof["on_image_text_mandate_en"]
    plan["listing_typography_mandate_en"] = prof["listing_typography_mandate_en"]
    plan["scene_geo_en"] = prof["scene_geo_en"]
    plan["scene_geo_adj_en"] = prof["scene_geo_adj_en"]
    if prof.get("doctrine_zh"):
        plan["listing_image_doctrine"] = prof["doctrine_zh"]

    text_fields = (
        "prompt_en",
        "action_lock",
        "composition_mandate_en",
        "scene_mandate_en",
        "diversity_lock",
        "usp_message_lock",
        "on_image_text_layout_en",
        "hero_visual_impact_lock",
        "conversion_story_lock_en",
        "listing_story_theme_en",
    )
    for shot in plan.get("shots") or []:
        for field in text_fields:
            if shot.get(field):
                shot[field] = _substitute_geo_text(str(shot[field]), prof)
        for field in ("headline_es", "subhead_es", "key_message_es", "prompt_es"):
            # 字段名历史沿用；巴西/英语站点仍写入对应语言文案
            if shot.get(field):
                shot[field] = _substitute_geo_text(str(shot[field]), prof)

    if (plan.get("negative_prompt") or "").strip():
        plan["negative_prompt"] = _substitute_geo_text(plan["negative_prompt"], prof)
        plan["negative_prompt"] = re.sub(
            r"misspelled Spanish",
            f"misspelled {prof['on_image_language']}",
            plan["negative_prompt"],
            flags=re.I,
        )

    return plan
