"""同一 SKU 多次套图：轮换视觉方案包，避免动作/排版/人物频率与上一批雷同。"""

from __future__ import annotations

import hashlib
import re

from generation.services.shot_diversity_constants import (
    CREATIVE_DETAIL_INDICES,
    CREATIVE_DETAIL_SPECS,
    DETAIL_SHOT_NEGATIVE as _DETAIL_NEGATIVE,
    FIXED_FRAME_ROLES,
)

from generation.services.beauty_personal_care import (
    BEAUTY_PERSONAL_CARE_PATTERN as _BEAUTY_KW,
    plan_uses_beauty_action_pool,
)


def is_beauty_skincare_plan(plan: dict) -> bool:
    return plan_uses_beauty_action_pool(plan)

# 每套包：五张创意详情 + 主图是否出人 + 命名（写入 plan 供下一批避让）
_BEAUTY_BATCH_PACKS: list[dict] = [
    {
        "name": "batch_mirror_stick_swipe",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {
            3: {
                "action_code": "pain_sink_still",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Sink-side still-life 'before routine' — tired mood via cool light and clutter, "
                    "NO mirror selfie, NO full face; product sealed on counter."
                ),
                "camera_short": "wide env back-left",
            },
            6: {
                "action_code": "trust_bathroom_vanity",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Bright Mexican bathroom vanity — SKU on marble shelf beside folded towel and plant; "
                    "steam-soft window light, clean premium routine vibe; product hero, no face."
                ),
                "camera_short": "wide env 3/4",
            },
            7: {
                "action_code": "social_vanity_grwm",
                "density": "balanced",
                "human": "full",
                "action_en": (
                    "Young Latina creator at bright vanity — mid-routine applying stick on cheek, soft smile, "
                    "phone-on-stand bokeh optional; TikTok GRWM authenticity; half-body 3/4; not frame-3 clutter still."
                ),
                "camera_short": "wide lifestyle 3/4",
            },
            8: {
                "action_code": "value_marble_flatlay",
                "density": "rich",
                "human": "none",
                "action_en": (
                    "Top-down flat lay on marble: stick + box + 2 bonus sachets + Spanish qty labels; "
                    "organized grid, no person."
                ),
                "camera_short": "90° top-down kit",
            },
            9: {
                "action_code": "payoff_window_glow",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Morning window sill — product open cap visible, soft glow on packaging, "
                    "fresh towel prop, NO person in frame."
                ),
                "camera_short": "wide lifestyle window",
            },
        },
    },
    {
        "name": "batch_studio_no_face_demo",
        "hero_human": False,
        "frames": {
            3: {
                "action_code": "pain_product_clutter",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Still-life 'before routine' — cluttered sink with generic tubes, hero SKU unopened in front, "
                    "no human face."
                ),
                "camera_short": "wide env back-left",
            },
            6: {
                "action_code": "trust_kitchen_counter",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Sunny kitchen counter — product beside ceramic mug and fruit bowl, tiled backsplash "
                    "typical of Mexico City home; morning light, trustworthy daily-use context."
                ),
                "camera_short": "wide env back-left",
            },
            7: {
                "action_code": "social_desk_creator",
                "density": "balanced",
                "human": "full",
                "action_en": (
                    "Creator at home desk with ring-light off — candid unboxing then first use toward camera; "
                    "casual Mexico City apartment, natural window light, relatable eye contact; product in hand."
                ),
                "camera_short": "elevated 3/4 front-left",
            },
            8: {
                "action_code": "value_gym_pouch",
                "density": "rich",
                "human": "none",
                "action_en": (
                    "Flat lay inside open gym pouch: stick, wipes, headband — travel value story, no face."
                ),
                "camera_short": "top-down 90°",
            },
            9: {
                "action_code": "payoff_cafe_table",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Product standing on café table with coffee cup bokeh — lifestyle without model face."
                ),
                "camera_short": "wide back-right lifestyle",
            },
        },
    },
    {
        "name": "batch_chin_macro_hands_only",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {
            3: {
                "action_code": "pain_texture_crop",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Abstract skin texture crop on neutral card or magnifier prop — concern metaphor, "
                    "no identifiable face, no mirror."
                ),
                "camera_short": "macro skin crop",
            },
            6: {
                "action_code": "trust_bedroom_nightstand",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Calm bedroom nightstand — product with book, lamp glow, linen texture; "
                    "evening wind-down trust scene, warm intimate, no portrait."
                ),
                "camera_short": "wide lifestyle indoor",
            },
            7: {
                "action_code": "social_friend_pov",
                "density": "balanced",
                "human": "full",
                "action_en": (
                    "Friend-POV over-shoulder: model applies product laughing in kitchen breakfast nook; "
                    "imperfect framing, TikTok phone-capture feel; waist-up, SKU visible, warm morning light."
                ),
                "camera_short": "wide lifestyle 3/4",
            },
            8: {
                "action_code": "value_retail_shelf",
                "density": "rich",
                "human": "none",
                "action_en": (
                    "Multiple sticks on retail shelf perspective — abundance, price-value, no portrait."
                ),
                "camera_short": "wide env shelf",
            },
            9: {
                "action_code": "payoff_outdoor_product",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Outdoor park bench — stick beside water bottle, sun flare, travel-ready story, zero portrait."
                ),
                "camera_short": "wide lifestyle outdoor",
            },
        },
    },
    {
        "name": "batch_evening_vanity_routine",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {
            3: {
                "action_code": "pain_tired_evening",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Evening vanity lamp still — melted candle, used cotton pads, sealed product, moody light, no face."
                ),
                "camera_short": "env 3/4 back-left",
            },
            6: {
                "action_code": "trust_home_living",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Family living room coffee table — SKU among remote, coaster, sunlight through curtains; "
                    "relatable Mexican home comfort, product sharp in foreground."
                ),
                "camera_short": "wide env 3/4",
            },
            7: {
                "action_code": "social_evening_routine",
                "density": "balanced",
                "human": "full",
                "action_en": (
                    "Evening skincare moment — woman in robe at vanity lamp, applying product calmly; "
                    "cozy intimate TikTok vibe, side profile showing face + product; not the frame-3 still-life."
                ),
                "camera_short": "wide lifestyle indoor",
            },
            8: {
                "action_code": "value_gift_box",
                "density": "rich",
                "human": "none",
                "action_en": (
                    "Gift box unopened with stick visible through window — premium bundle layout."
                ),
                "camera_short": "top-down kit",
            },
            9: {
                "action_code": "payoff_nightstand",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Nightstand calm — product, book, warm lamp, silk fabric prop; post-routine implied, no model."
                ),
                "camera_short": "wide lifestyle indoor",
            },
        },
    },
    {
        "name": "batch_color_pop_editorial",
        "hero_human": False,
        "frames": {
            3: {
                "action_code": "pain_split_tone",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Split-color background still — stick casting shadow, 'problem vs solution' metaphor without face."
                ),
                "camera_short": "low 3/4 front-right",
            },
            6: {
                "action_code": "trust_street_or_office",
                "density": "balanced",
                "human": "none",
                "action_en": (
                    "Alternate batch: outdoor street café table OR tidy home-office desk with laptop edge — "
                    "urban Mexico daylight, product ready-for-day trust; no full-face model."
                ),
                "camera_short": "wide lifestyle outdoor",
            },
            7: {
                "action_code": "social_urban_outdoor",
                "density": "balanced",
                "human": "full",
                "action_en": (
                    "Outdoor Mexico urban sidewalk — creator uses product before going out, golden hour, "
                    "streetwear casual, dynamic 3/4 walking pause; authentic TikTok street seeding, not studio."
                ),
                "camera_short": "wide lifestyle outdoor",
            },
            8: {
                "action_code": "value_family_multi",
                "density": "rich",
                "human": "none",
                "action_en": (
                    "Three sticks different shades lined up — family lineup, bold colors, no model."
                ),
                "camera_short": "top-down 90°",
            },
            9: {
                "action_code": "payoff_product_hero_outdoor",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Stick upright in sand/grass macro — outdoor freshness, zero human."
                ),
                "camera_short": "wide back-right",
            },
        },
    },
]

def _generic_frame(
    action_code: str,
    action_en: str,
    *,
    camera_short: str = "",
    density: str = "balanced",
    human: str = "none",
) -> dict:
    return {
        "action_code": action_code,
        "action_en": action_en,
        "camera_short": camera_short,
        "density": density,
        "human": human,
    }


_GENERIC_BATCH_PACKS: list[dict] = [
    {
        "name": "theme_studio_editorial",
        "story_theme_en": (
            "STORY THEME — Cool studio editorial: crisp side light, graphite/slate props, "
            "Mexico City design-apartment mood; rational buyer — quality and specs first."
        ),
        "color_mood_en": "cool neutrals, silver highlights",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {
            3: _generic_frame(
                "studio_benefit_still",
                "Studio still — solved pain via neat organization and premium material cues; cool gradient backdrop.",
                camera_short="wide env back-left",
            ),
            6: _generic_frame(
                "trust_desk_setup",
                "Home office desk trust: product beside laptop and plant; tidy executive daily use.",
                camera_short="wide env shelf",
            ),
            7: _generic_frame(
                "social_creator_desk",
                "Creator at desk unboxing — candid TikTok vibe, natural window light, half-body.",
                human="full",
                camera_short="elevated 3/4 front-left",
            ),
            8: _generic_frame(
                "value_studio_flatlay",
                "Studio flat lay on concrete — kit items grid, qty labels, no person.",
                camera_short="90° top-down kit",
                density="rich",
            ),
            9: _generic_frame(
                "payoff_window_minimal",
                "Minimal window sill payoff — product + mug, soft morning glow, zero people.",
                camera_short="wide lifestyle window",
                density="minimal",
            ),
        },
    },
    {
        "name": "theme_warm_home",
        "story_theme_en": (
            "STORY THEME — Warm Mexican home: terracotta, woven textiles, golden indoor light; "
            "family routine narrative — comfort, trust, daily ritual."
        ),
        "color_mood_en": "warm beige, terracotta, soft gold",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {
            3: _generic_frame(
                "home_pain_relief",
                "Living room side table — before/after metaphor via lighting only; cozy sofa bokeh.",
                camera_short="low 3/4 front-right",
            ),
            6: _generic_frame(
                "trust_bedroom_dresser",
                "Bedroom dresser trust scene — folded linens, candle, product centered.",
                camera_short="wide lifestyle indoor",
            ),
            7: _generic_frame(
                "social_family_couch",
                "Young adult on couch mid-use — warm lamp light, relatable Latina/Latino, product in hand.",
                human="full",
                camera_short="wide lifestyle 3/4",
            ),
            8: _generic_frame(
                "value_basket_kit",
                "Woven basket kit spread — angled shelf, gift-worthy styling.",
                camera_short="wide env shelf",
                density="rich",
            ),
            9: _generic_frame(
                "payoff_balcony_sunset",
                "Balcony sunset — product on railing, city glow, aspirational calm.",
                camera_short="wide lifestyle outdoor",
                density="minimal",
            ),
        },
    },
    {
        "name": "theme_outdoor_urban",
        "story_theme_en": (
            "STORY THEME — Outdoor urban Mexico: street café, park bench, sidewalk energy; "
            "active lifestyle buyer — portability, freshness, on-the-go."
        ),
        "color_mood_en": "natural greens, concrete, sun flare",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 0, "max_human_touch_frames": 1},
        "frames": {
            3: _generic_frame(
                "outdoor_problem_solved",
                "Park bench scene — benefit solved outdoors; product with tote and sunglasses props.",
                camera_short="wide lifestyle outdoor",
            ),
            6: _generic_frame(
                "trust_cafe_table",
                "Street café table — product beside coffee cup; Mexico City sidewalk bokeh.",
                camera_short="wide env 3/4",
            ),
            7: _generic_frame(
                "social_park_walk",
                "Consumer walking in park holding product — candid 3/4, no studio.",
                human="full",
                camera_short="wide lifestyle outdoor",
            ),
            8: _generic_frame(
                "value_backpack_spread",
                "Backpack spill flatlay on grass — travel kit narrative.",
                camera_short="top-down 90°",
                density="rich",
            ),
            9: _generic_frame(
                "payoff_rooftop",
                "Rooftop golden hour — product silhouette + city skyline.",
                camera_short="wide back-right",
                density="minimal",
            ),
        },
    },
    {
        "name": "theme_premium_gift",
        "story_theme_en": (
            "STORY THEME — Premium gift / gifting moment: marble, ribbon, soft box light; "
            "buyer motivation — present for family, perceived value, unboxing delight."
        ),
        "color_mood_en": "ivory marble, soft rose gold accents",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {
            3: _generic_frame(
                "gift_detail_macro",
                "Ribbon + packaging detail macro — craft texture, premium materials.",
                camera_short="macro skin crop",
                density="minimal",
            ),
            6: _generic_frame(
                "trust_entry_console",
                "Entry console gift-ready styling — mirror, plant, product as centerpiece.",
                camera_short="elevated 3/4 front-left",
            ),
            7: _generic_frame(
                "social_gift_exchange",
                "Hands passing gift box — warm smile crop, no stiff studio; product visible.",
                human="hands",
                camera_short="table-level 3/4 front-left",
            ),
            8: _generic_frame(
                "value_marble_unbox",
                "Marble unboxing spread — all kit pieces, premium flat lay.",
                camera_short="90° top-down kit",
                density="rich",
            ),
            9: _generic_frame(
                "payoff_fireplace_glow",
                "Fireplace / warm interior glow — product on side table, holiday mood.",
                camera_short="wide lifestyle indoor",
            ),
        },
    },
    {
        "name": "theme_minimal_scandi",
        "story_theme_en": (
            "STORY THEME — Minimal Scandi-meets-LATAM: white wood, negative space, calm; "
            "story of simplicity, less clutter, honest product."
        ),
        "color_mood_en": "white oak, pale sage, airy",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 0, "max_human_touch_frames": 1},
        "frames": {
            3: _generic_frame(
                "minimal_benefit_space",
                "Sparse shelf — one hero SKU, single plant; benefit = space saving.",
                camera_short="env 3/4 back-left",
                density="minimal",
            ),
            6: _generic_frame(
                "trust_minimal_bath",
                "Minimal bathroom niche — white tile, single towel, product only.",
                camera_short="wide env 3/4",
            ),
            7: _generic_frame(
                "social_hands_apply",
                "Hands-only ritual — clean nails, soft light, no face; TikTok macro tutorial feel.",
                human="hands",
                camera_short="macro skin crop",
            ),
            8: _generic_frame(
                "value_lineup_shelf",
                "Linear shelf lineup — qty emphasis, no clutter.",
                camera_short="wide env shelf",
            ),
            9: _generic_frame(
                "payoff_white_curtain",
                "Sheer curtain backlight — product silhouette, zen payoff.",
                camera_short="wide lifestyle window",
                density="minimal",
            ),
        },
    },
    {
        "name": "theme_bold_color_pop",
        "story_theme_en": (
            "STORY THEME — Bold color-pop retail: saturated backdrops, playful props, youth energy; "
            "impulse TikTok shopper — fun, contrast, scroll-stop patterns."
        ),
        "color_mood_en": "cobalt, coral, high saturation",
        "hero_human": True,
        "human_budget_override": {"max_face_frames": 2, "max_human_touch_frames": 3},
        "frames": {
            3: _generic_frame(
                "pop_benefit_props",
                "Color-block backdrop — exaggerated props showing benefit; playful shadows.",
                camera_short="dutch tilt 3/4 front",
            ),
            6: _generic_frame(
                "trust_color_kitchen",
                "Bright painted kitchen — tiles + product; authentic Mexico home color.",
                camera_short="low 3/4 front-right",
            ),
            7: _generic_frame(
                "social_dance_hold",
                "Creator holding product mid-movement — motion blur background, energetic TikTok.",
                human="full",
                camera_short="ugc phone capture height",
            ),
            8: _generic_frame(
                "value_color_grid",
                "Colorful grid flat lay — stickers, qty, gifts on solid hue surface.",
                camera_short="top-down 90°",
                density="rich",
            ),
            9: _generic_frame(
                "payoff_neon_night",
                "Neon-accent night shelf — product pop against dark wall.",
                camera_short="night city bokeh",
            ),
        },
    },
]

_CAMERA_ALT_ORIENTATION: dict[str, str] = {
    "macro skin crop": (
        "Extreme close crop on skin texture; shallow DOF; no full product silhouette."
    ),
    "wide env shelf": (
        "Wide shot from slight high angle; multiple units on shelf; environmental context."
    ),
    "wide lifestyle outdoor": (
        "28mm outdoor lifestyle; subject small in frame; golden hour Mexico urban park."
    ),
    "elevated 3/4 front-left": (
        "Camera 45° above, front-left quarter; asymmetric product placement."
    ),
    "wide env back-left": (
        "Wide environmental from back-left quarter; product partly turned from front."
    ),
    "90° top-down kit": "Strict 90° bird's-eye kit layout on textured surface.",
    "wide lifestyle window": "Window-side lifestyle; soft backlight; product on sill or table.",
    "low 3/4 front-right": "Low knee-height 3/4 from front-right; dramatic product depth.",
    "wide lifestyle indoor": "28mm indoor lifestyle; natural window light; lived-in Mexico home.",
    "wide lifestyle 3/4": "Three-quarter lifestyle portrait distance; product in active context.",
    "wide back-right": "Wide from back-right quarter; product in lower third; deep background.",
    "top-down 90°": "Top-down 90° flat lay — only when mandated for this frame batch.",
    "wide env 3/4": "Chest-height wide 3/4 environmental product-in-scene.",
    "env 3/4 back-left": "Environmental back-left 3/4; asymmetric props.",
    "table-level 3/4 front-left": "Table-height 3/4 from front-left; usage props on same plane.",
    "dutch tilt 3/4 front": "Slight dutch angle 3/4 from front; dynamic editorial energy.",
    "ugc phone capture height": "Handheld phone height ~1.1m; candid off-center TikTok framing.",
    "night city bokeh": "Night urban bokeh; product sharp foreground.",
}


def _normalize_prompt_for_fingerprint(prompt: str) -> str:
    return re.sub(r"\s+", " ", (prompt or "").strip().lower())[:200]


def _normalize_category_bucket(category: str) -> str:
    c = (category or "").strip().lower()
    if not c:
        return ""
    if _BEAUTY_KW.search(c):
        return "beauty_skincare"
    return c[:48]


def _analysis_product_key(analysis: dict | None) -> str:
    """仅用 vision 里较稳定的品名字段；visual_identity 每次分析会变，不能进指纹。"""
    if not analysis:
        return ""
    parts: list[str] = []
    for key in ("product_name_en", "product_name_es"):
        val = analysis.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip().lower()[:96])
    cat = _normalize_category_bucket(str(analysis.get("category") or ""))
    if cat:
        parts.append(cat)
    return "|".join(parts)


def product_fingerprint(job, *, product_analysis: dict | None = None) -> str:
    """
    同一 SKU 批次计数键：优先 vision 分析里的品名/品类，其次用户套图 brief 文案。
    不用 attachment id —— 每次重新上传参考图会得到新 id，但仍是同一商品。
    """
    analysis = product_analysis
    if not analysis:
        analysis = (job.plan_json or {}).get("product_analysis") or {}
    product_key = _analysis_product_key(analysis)
    prompt_key = _normalize_prompt_for_fingerprint(job.prompt)
    uid = int(job.user_id or 0)
    brief_tail = f"|brief:{prompt_key}" if prompt_key else ""
    if product_key:
        key = f"u{uid}|sku:{product_key}{brief_tail}"
    elif prompt_key:
        key = f"u{uid}|brief:{prompt_key}"
    else:
        ids: list[int] = []
        raw = job.reference_attachment_ids or []
        if isinstance(raw, list):
            ids.extend(int(x) for x in raw if str(x).isdigit())
        if job.reference_attachment_id:
            ids.append(int(job.reference_attachment_id))
        ids = sorted(set(ids))
        key = f"u{uid}|att:{','.join(map(str, ids))}|{prompt_key}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def resolve_visual_batch_index(job, *, product_analysis: dict | None = None) -> int:
    """同一用户 + 同一 SKU/brief 指纹下，第几次套图任务（含已策划过的任务）。"""
    from generation.models import GenerationJob

    fp = product_fingerprint(job, product_analysis=product_analysis)
    qs = (
        GenerationJob.objects.filter(user_id=job.user_id)
        .exclude(pk=job.pk)
        .order_by("-created_at")
    )
    count = 0
    for j in qs[:80]:
        if product_fingerprint(j) != fp:
            continue
        if j.status == GenerationJob.Status.CANCELLED:
            continue
        plan = j.plan_json or {}
        from generation.services.listing_bundle import LISTING_PLAN_TEMPLATES

        if not (plan.get("shots") or plan.get("plan_template") in LISTING_PLAN_TEMPLATES):
            continue
        count += 1
    return count


def _load_previous_plan_summary(job, *, product_analysis: dict | None = None) -> str:
    from generation.models import GenerationJob

    fp = product_fingerprint(job, product_analysis=product_analysis)
    prev = (
        GenerationJob.objects.filter(
            user_id=job.user_id,
            status=GenerationJob.Status.SUCCEEDED,
        )
        .exclude(pk=job.pk)
        .order_by("-finished_at")[:30]
    )
    for j in prev:
        if product_fingerprint(j, product_analysis=product_analysis) != fp:
            continue
        plan = j.plan_json or {}
        name = plan.get("visual_batch_pack_name") or "unknown"
        theme = (plan.get("listing_story_theme_en") or "")[:400]
        roster = plan.get("detail_action_roster") or {}
        cam = plan.get("camera_roster") or {}
        human = plan.get("human_presence_summary") or ""
        v3 = plan.get("frame3_variant_id") or "?"
        v5 = plan.get("frame5_variant_id") or "?"
        cam_preset = plan.get("camera_batch_preset_id") or "?"
        return (
            f"MANDATORY — Previous listing job #{j.id} used pack '{name}', camera preset '{cam_preset}', "
            f"story theme excerpt: {theme}. "
            f"Frame3/5 variants were {v3}/{v5}. Detail actions: {roster}. "
            f"Per-frame cameras: {cam}. Human pattern: {human}. "
            "This NEW batch MUST change story theme, color mood, scene family, hero layout, "
            "camera preset, and creative detail actions — not a reskin of the prior set."
        )
    return ""


def _pick_pack(plan: dict, batch_index: int) -> dict:
    if is_beauty_skincare_plan(plan):
        packs = _BEAUTY_BATCH_PACKS
    else:
        packs = _GENERIC_BATCH_PACKS
    hint = (plan.get("creative_concept_pack_name") or "").strip()
    if hint:
        for pack in packs:
            if pack.get("name") == hint:
                return pack
    concept = plan.get("creative_concept_id")
    if concept and is_beauty_skincare_plan(plan):
        from generation.services.creative_engine.concepts import concept_by_id

        c = concept_by_id(str(concept))
        if c:
            off = int(c.get("beauty_pack_offset") or 0)
            return packs[off % len(packs)]
    return packs[batch_index % len(packs)]


def apply_visual_batch_variance(plan: dict, *, job=None) -> dict:
    from generation.services.listing_bundle import (
        is_listing_ecommerce_plan,
        listing_creative_detail_indices,
        listing_creative_detail_specs,
        listing_payoff_shot_index,
    )

    if not is_listing_ecommerce_plan(plan):
        return plan

    creative_idxs = listing_creative_detail_indices(plan)

    batch_index = int(plan.get("visual_batch_index") or 0)
    pack = _pick_pack(plan, batch_index)
    plan["visual_batch_index"] = batch_index
    plan["visual_batch_pack_name"] = pack.get("name", f"pack_{batch_index}")
    if not (plan.get("listing_story_theme_en") or "").strip():
        plan["listing_story_theme_en"] = (pack.get("story_theme_en") or "").strip()
    if not (plan.get("listing_color_mood_en") or "").strip():
        plan["listing_color_mood_en"] = (pack.get("color_mood_en") or "").strip()
    if plan.get("listing_story_theme_en"):
        from generation.services.creative_engine.cohesion import build_conversion_story_lock_en

        plan["conversion_story_lock_en"] = build_conversion_story_lock_en(plan)
        if "Every frame must support" not in plan["conversion_story_lock_en"]:
            plan["conversion_story_lock_en"] += (
                " Every frame must support this narrative — do not default to generic catalog shots."
            )

    if job:
        analysis = plan.get("product_analysis") or (job.plan_json or {}).get("product_analysis")
        avoid = _load_previous_plan_summary(job, product_analysis=analysis)
        if avoid:
            plan["previous_batch_avoidance_en"] = avoid

    frames = pack.get("frames") or {}
    human_summary: list[str] = []
    action_roster: dict[int, str] = {}

    shots = plan.get("shots") or []
    for shot in shots:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()

        if role == "hero_hook":
            hero_human = bool(pack.get("hero_human", False))
            shot["human_cast_mode"] = "full" if hero_human else "none"
            human_summary.append(f"#1={'human' if hero_human else 'product-only'}")
            if not hero_human:
                shot.setdefault(
                    "diversity_lock",
                    "Hero — product-only scroll stopper, no model face; bold layout and Spanish headline space.",
                )
            continue

        if role in FIXED_FRAME_ROLES and idx not in creative_idxs:
            continue

        if idx not in creative_idxs:
            continue

        spec = dict(frames.get(idx) or {})
        if not spec.get("action_en"):
            detail_specs = listing_creative_detail_specs(plan)
            spec_idx = idx
            payoff = listing_payoff_shot_index(plan)
            if payoff and idx == payoff and idx != 9:
                spec_idx = 9
            spec = dict(detail_specs.get(spec_idx) or detail_specs.get(idx) or {})
            palette = (plan.get("listing_unified_palette_en") or plan.get("listing_color_mood_en") or "").strip()
            temp = (plan.get("listing_color_temperature_lock_en") or "")[:160]
            base = spec.get("action_code") or f"detail_{idx}"
            spec.setdefault(
                "action_en",
                "Creative detail — "
                + (f"same set palette ({palette}); " if palette else "")
                + (f"{temp} " if temp else "")
                + "unique camera/layout vs other frames; background may be solid, studio, or real interior per frame mandate.",
            )
            spec.setdefault("action_code", base)
            spec.setdefault("human", spec.get("human") or "balanced")

        human_mode = (spec.get("human") or "balanced").lower()
        if human_mode in ("none", "no", "product"):
            shot["human_cast_mode"] = "none"
            human_summary.append(f"#{idx}=no-human")
        elif human_mode == "hands":
            shot["human_cast_mode"] = "hands"
            human_summary.append(f"#{idx}=hands-only")
        elif human_mode == "face":
            shot["human_cast_mode"] = "face"
            human_summary.append(f"#{idx}=face/crop")
        else:
            shot["human_cast_mode"] = "full"
            human_summary.append(f"#{idx}=full-body")

        shot["frame_contract"] = "creative_detail"
        shot["content_density"] = spec.get("density", "balanced")
        code = spec.get("action_code", "")
        shot["action_code"] = code
        action_roster[idx] = code

        action_block = spec.get("action_en", "")
        batch_tag = f"VISUAL BATCH {batch_index + 1} — pack '{pack.get('name')}'. "
        shot["action_lock"] = (
            f"{batch_tag}CREATIVE DETAIL — Must differ from other frames AND from user's previous "
            f"listing batches for this SKU. {action_block}"
        )

        cam_short = spec.get("camera_short") or ""
        if cam_short and cam_short in _CAMERA_ALT_ORIENTATION:
            shot["orientation_lock"] = _CAMERA_ALT_ORIENTATION[cam_short]
            shot["camera_angle_code"] = cam_short.replace(" ", "_").replace("°", "deg")
        elif cam_short:
            shot["orientation_lock"] = (
                f"Batch camera '{cam_short}' — distinct from other frames and from user's previous listing batch."
            )
            shot["camera_angle_code"] = cam_short.replace(" ", "_").replace("°", "deg")

        density = spec.get("density", "balanced")
        if density == "minimal":
            shot["composition_density_lock"] = (
                "COMPOSITION DENSITY — Minimal: 1–2 elements, generous negative space."
            )
        elif density == "rich":
            shot["composition_density_lock"] = (
                "COMPOSITION DENSITY — Rich: multiple props/SKU units allowed."
            )
        else:
            shot["composition_density_lock"] = (
                "COMPOSITION DENSITY — Balanced hero plus context."
            )

        extra = (shot.get("negative_extra") or "").strip()
        shot["negative_extra"] = f"{extra}, {_DETAIL_NEGATIVE}".strip(", ")

    plan["detail_action_roster"] = action_roster
    plan["human_presence_summary"] = ", ".join(human_summary)
    plan["shots"] = shots

    neg = (plan.get("negative_prompt") or "").strip()
    cross = (
        "duplicate listing set as previous generation, same stick swipe pose, same mirror layout, "
        "same flat lay arrangement, same model action sequence"
    )
    plan["negative_prompt"] = f"{neg}, {_DETAIL_NEGATIVE}, {cross}".strip(", ")

    from generation.services.product_story_locks import apply_product_story_locks
    from generation.services.human_presence_policy import apply_human_presence_policy

    plan = apply_product_story_locks(plan)
    plan = apply_human_presence_policy(plan, pack=pack, batch_index=batch_index)
    from generation.services.listing_human_cast import apply_mandated_human_casts

    plan = apply_mandated_human_casts(plan)
    return plan
