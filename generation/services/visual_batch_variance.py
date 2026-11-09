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

_BEAUTY_KW = re.compile(
    r"(mud\s*mask|clay\s*mask|mud\s*stick|face\s*mask|stick|acne\s*patch|pimple\s*patch|"
    r"hydrocolloid|skincare|serum|cleanser|toner|moisturizer|sunscreen|"
    r"泥膜|泥膜棒|面膜|痘痘贴|痘贴|护肤|精华|洁面|水乳|防晒|美妆)",
    re.I,
)


def is_beauty_skincare_plan(plan: dict) -> bool:
    analysis = plan.get("product_analysis") or {}
    blob = " ".join(
        [
            str(analysis.get("category") or ""),
            str(analysis.get("product_name_en") or ""),
            str(analysis.get("primary_function") or ""),
            str(plan.get("user_prompt") or ""),
        ]
    )
    return bool(_BEAUTY_KW.search(blob))

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
                "action_code": "trust_stick_texture",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Product-only macro: mud stick tip texture, swirl on glass palette, clinical white surface. "
                    "No face, no hands applying."
                ),
                "camera_short": "macro 30° product",
            },
            7: {
                "action_code": "usage_stick_cheek_swipe",
                "density": "balanced",
                "human": "hands",
                "action_en": (
                    "Single action: glide stick directly on cheek in one stroke; other hand holds hair back. "
                    "Side angle 45°, not front mirror duplicate of frame 3."
                ),
                "camera_short": "table 3/4 side apply",
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
                "action_code": "trust_cross_section",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Minimal cutaway-style clay core close-up on neutral gray; scientific trust, no bathroom."
                ),
                "camera_short": "macro label corner alt",
            },
            7: {
                "action_code": "usage_twist_open",
                "density": "balanced",
                "human": "hands",
                "action_en": (
                    "Hands twist-open stick cap on plain desk — show mechanism, NOT on-face application."
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
                "action_code": "trust_ingredient_icons",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Clean graphic-minimal shelf shot: stick plus 3 ingredient callout cards, lots of whitespace."
                ),
                "camera_short": "front catalog variant",
            },
            7: {
                "action_code": "usage_spot_dab",
                "density": "balanced",
                "human": "hands",
                "action_en": (
                    "Finger dabs product from stick onto one small spot — patch-test gesture, not full-face mask."
                ),
                "camera_short": "table 3/4 opposite frame1",
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
                "action_code": "trust_seal_cert",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Packaging back label / certification zone macro, cool neutral light."
                ),
                "camera_short": "macro side",
            },
            7: {
                "action_code": "usage_forehead_glide",
                "density": "balanced",
                "human": "hands",
                "action_en": (
                    "Glide stick across forehead line — different body zone than cheek demo packs."
                ),
                "camera_short": "elevated 3/4 front-left",
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
                "action_code": "trust_weight_size",
                "density": "minimal",
                "human": "none",
                "action_en": (
                    "Stick beside ruler/coin for size reference — infographic minimalism."
                ),
                "camera_short": "side profile 90°",
            },
            7: {
                "action_code": "usage_double_hand_cap",
                "density": "balanced",
                "human": "hands",
                "action_en": (
                    "Both hands uncap stick over sink — preparatory step only, no face in frame."
                ),
                "camera_short": "table level 3/4",
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

_GENERIC_BATCH_PACKS: list[dict] = [
    {
        "name": "generic_pack_a",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 1, "max_human_touch_frames": 2},
        "frames": {},
    },
    {
        "name": "generic_pack_b",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 0, "max_human_touch_frames": 1},
        "frames": {},
    },
    {
        "name": "generic_pack_c",
        "hero_human": False,
        "human_budget_override": {"max_face_frames": 2, "max_human_touch_frames": 3},
        "frames": {},
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
    if product_key:
        key = f"u{uid}|sku:{product_key}"
    elif prompt_key and len(prompt_key) >= 36:
        key = f"u{uid}|brief:{prompt_key}"
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
    """同一用户 + 同一 SKU/brief 指纹下，第几次成功/进行中的套图任务。"""
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
        if j.status in (
            GenerationJob.Status.SUCCEEDED,
            GenerationJob.Status.RUNNING,
            GenerationJob.Status.QUEUED,
        ):
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
        roster = plan.get("detail_action_roster") or {}
        human = plan.get("human_presence_summary") or ""
        return (
            f"MANDATORY — Previous listing batch #{j.id} used visual pack '{name}'. "
            f"Actions were {roster}. Human presence pattern: {human}. "
            "This batch MUST use different poses, layouts, camera distances, and human/no-human mix. "
            "Do NOT replicate bathroom mirror stick swipe if that was used before."
        )
    return ""


def _pick_pack(plan: dict, batch_index: int) -> dict:
    if is_beauty_skincare_plan(plan):
        packs = _BEAUTY_BATCH_PACKS
    else:
        packs = _GENERIC_BATCH_PACKS
    return packs[batch_index % len(packs)]


def apply_visual_batch_variance(plan: dict, *, job=None) -> dict:
    if plan.get("plan_template") != "tk_mx_ecommerce_9":
        return plan

    batch_index = int(plan.get("visual_batch_index") or 0)
    pack = _pick_pack(plan, batch_index)
    plan["visual_batch_index"] = batch_index
    plan["visual_batch_pack_name"] = pack.get("name", f"pack_{batch_index}")

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
            hero_human = bool(pack.get("hero_human", True))
            shot["human_cast_mode"] = "full" if hero_human else "none"
            human_summary.append(f"#1={'human' if hero_human else 'product-only'}")
            if not hero_human:
                shot.setdefault(
                    "diversity_lock",
                    "Hero — product-only scroll stopper, no model face; bold layout and Spanish headline space.",
                )
            continue

        if role in FIXED_FRAME_ROLES and idx not in CREATIVE_DETAIL_INDICES:
            continue

        if idx not in CREATIVE_DETAIL_INDICES:
            continue

        spec = dict(frames.get(idx) or {})
        if not spec.get("action_en"):
            spec = dict(CREATIVE_DETAIL_SPECS.get(idx) or {})
            scene_hints = [
                "cool studio minimal props",
                "warm home bathroom narrative",
                "outdoor natural light context",
            ]
            base = spec.get("action_code") or f"detail_{idx}"
            spec.setdefault(
                "action_en",
                f"Creative detail variant — {scene_hints[batch_index % len(scene_hints)]}; "
                f"unique layout vs prior batches for this SKU.",
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
            shot["camera_angle_code"] = cam_short.replace(" ", "_")
        elif cam_short:
            shot["composition_mandate"] = (
                f"CAMERA NOTE for this batch: {cam_short} — override default TK matrix angle; "
                "not the same as prior batch for this product."
            )

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
    return plan
