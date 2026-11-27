"""TK Shop México Listing 主图体系：① 分层主图契约、西语排版、⑧⑨ 版式子类型。"""

from __future__ import annotations

from django.conf import settings

from generation.services.ecommerce_strategy import TK_MX_NINE_FRAME_MATRIX, strategy_brief_by_index

LISTING_IMAGE_DOCTRINE_ZH = (
    "全套 9 张均为 TikTok Shop México Listing 主图（1 场景引流主图 + 1 白底合规 + 7 职能详情），"
    "非简单换角度。SKU 颜色包装 Logo 与参考图一致；单张照片禁九宫格拼图；"
    "画面上文案仅西语墨西哥或包装原标签字，默认禁止中文；合规无医疗夸大。"
)

AMAZON_LISTING_IMAGE_DOCTRINE_ZH = (
    "Amazon Listing 7 图：①白底主图 ②核心卖点 ③规格参数 ④痛点前后对比↔场景代入(轮换) "
    "⑤细节品质(轮换细节/成分) ⑥功能演示 ⑦包装配件；单张照片禁拼图；SKU 与参考一致。"
)

AMAZON_ARTICLE_MATRIX_HINT_ZH = (
    "职能映射：①white_bg=Amazon 主图合规白底；②hero_hook=核心卖点价值主图；"
    "③usp_secondary=固定规格尺寸；④轮换(使用前→使用后纯视觉禁对比字|真实场景代入)；"
    "⑤pain_empathy=细节特写/成分整图轮换；⑥ease_objection=功能效果演示；⑦value_stack=盒内清单配件。"
)

ARTICLE_MATRIX_HINT_ZH = (
    "职能映射（每镜单一焦点）：①hero_hook=场景分层主图(非白底)；②white_bg=合规白底；③pain_empathy=轮换(卖点解决|细节特写|成分无瓶)；"
    "④usp_primary=使用前→使用后痛点对比(纯视觉·禁对比文字)；⑤usp_secondary=批次轮换(品类对比|规格|套装|步骤|核心功能|成分整图无产品)；"
    "⑦ease_objection=人群场景种草(真人使用中·TikTok真实感)；⑧value_stack=规格或套装(value_bundle/specs_features)；"
    "⑨lifestyle_payoff=强转化收尾(日常/送礼/家庭/值得购买/卖点总结/愿景生活·轮换；营造购买氛围，非纯产品复刻)。"
)

USP_PRIMARY_PAIN_VISUAL = (
    "FRAME 4 — Before→after pain transformation for core USP in ONE photograph (not collage). "
    "Visual contrast only via lighting, color, product/skin state — NOT generic-product vs hero layout "
    "(category compare belongs on frame 5 when rotated). "
    "NO on-image comparison words (before/after/antes/después/使用前/使用后/vs banners)."
)

TRUST_QUALITY_REAL_LIFE_MX = (
    "FRAME 6 — Usage benefit payoff: what the user gains from using the product daily "
    "(comfort, freshness, softness, confidence — from product_analysis). "
    "Model may appear (face or half-body) with product in use or post-use satisfaction. "
    "MANDATORY Spanish benefit headline on image. "
    "NOT frame-4 before/after split; NOT frame-7 crowd UGC duplicate."
)

EASE_OBJECTION_TIKTOK_SOCIAL_PROOF = (
    "FRAME 7 — Target-audience crowd scene (TikTok Shop seeding): show the ideal buyer actively "
    "using the SKU in a believable Mexican daily-life context. UGC-meets-commerce: natural or "
    "window light, candid mid-use moment, relatable half-body or 3/4 framing, product clearly visible; "
    "warm, scroll-friendly, not over-lit studio glamour. NOT hands-only step tutorial; NOT the same "
    "mirror/problem still as frame 3; NOT the same post-use payoff gesture as frame 9."
)

HERO_VISUAL_IMPACT_EN = (
    "HERO SCROLL-STOPPER — Index 1 must WIN the TikTok feed thumbnail at ~120px: "
    "high contrast, strong color accent in background, cinematic depth (foreground product vs blurred scene), "
    "directional key light + rim light on SKU, dynamic asymmetry — NOT centered flat packshot, NOT dull catalog. "
    "Product occupies 40–52% of frame with bold 35–50° hero angle showing depth, material, and structure."
)

HERO_LAYERED_MX_COMPOSITION = (
    "HERO LISTING IMAGE (INDEX 1 ONLY) — TikTok Shop México layered scroll-stopper (NOT white seamless). "
    f"{HERO_VISUAL_IMPACT_EN} "
    "Three layers: (1) BACKGROUND — vivid Mexican lifestyle scene or color-accent environment, "
    "bright natural light, shallow DOF bokeh, authentic context that pops on mobile. "
    "(2) FOREGROUND PRODUCT — dominant hero SKU with commercial clarity, soft grounding shadow; "
    "background color grade MUST match the locked listing palette/temperature used on frames 3–9. "
    "(3) INFO PANEL — a large Spanish block covering about one third: bold headline, a two-line introduction, "
    "and three proof lines about the same benefit. Type is big enough to read on a phone. "
    "If human present: hands/partial only; face must NOT overpower product. "
    "No collage, no nine-grid, no Chinese text, no exaggerated medical claims."
)

WHITE_BG_NO_TEXT_EN = (
    "INDEX 2 WHITE CATALOG — Pure #FFFFFF seamless compliance shot ONLY. "
    "FORBIDDEN: any added marketing text, stickers, headlines, captions, icons, or Spanish callouts. "
    "Only the product and its authentic factory packaging/label as photographed — no designed overlay text."
)

WHITE_BG_SCENE_PROMPT_EN = (
    "Pure #FFFFFF seamless studio catalog photograph of the hero SKU only. "
    "Straight-on front, eye-level, perfectly centered, symmetrical, soft even softbox lighting, "
    "Product MUST stand UPRIGHT vertical front-facing — 0° roll, 0° tilt, cap/lid up, label plane "
    "parallel to camera; FORBIDDEN diagonal lean, lying on side, 25–45° art angle, or dynamic tilt. "
    "no props, no lifestyle environment, no people, no secondary products, no marketing graphics. "
    "NOT a scroll-stopper hero, NOT before/after, NOT comparison layout, NOT ingredient flat-lay."
)

WHITE_BG_UPRIGHT_POSE_LOCK_EN = (
    "INDEX 2 POSE LOCK — Upright compliance catalog ONLY: vertical standing packshot on white, "
    "front label to camera, zero tilt/slant/roll; overrides any other-frame diagonal product staging rules."
)

LAYOUT_MANDATES = {
    "specs_features": (
        "LAYOUT — Specs & functions frame: show size/capacity/color/kit contents or step sequence "
        "in one filled 1:1 photo; product plus a large Spanish text panel; not a white catalog clone."
    ),
    "value_bundle": (
        "LAYOUT — Value bundle frame: kit contents, quantity, gift-worth narrative; "
        "warm premium styling, distinct from index 2 white catalog."
    ),
    "benefit_summary": (
        "LAYOUT — Benefit summary frame: filled scene plus a large Spanish text panel that explains "
        "this frame's one benefit (headline, two-line introduction, three proof lines); product visible."
    ),
    "conversion_close": (
        "LAYOUT — Conversion closing frame: PURCHASE ATMOSPHERE first (daily routine / gift moment / "
        "family home / smart-buy confidence / lifestyle aspiration) — product supports the story, "
        "not a lone packshot repeat of frame 1. Large Spanish text panel; the scene fills the frame."
    ),
}

BRIEF_FIELDS_TO_SHOT = (
    "image_goal_zh",
    "composition_zh",
    "scene_zh",
    "headline_es",
    "subhead_es",
    "icon_bullets_es",
    "layout_subtype",
    "key_message_es",
)


def _copy_brief_fields(shot: dict, brief: dict) -> None:
    for key in BRIEF_FIELDS_TO_SHOT:
        val = brief.get(key)
        if val is not None and val != "":
            shot[key] = val
    bullets = brief.get("icon_bullets_es")
    if isinstance(bullets, list) and bullets:
        shot["icon_bullets_es"] = bullets
    elif isinstance(bullets, str) and bullets.strip():
        shot["icon_bullets_es"] = [s.strip() for s in bullets.replace("，", "|").split("|") if s.strip()]


def _default_layout_subtype(role: str, index: int) -> str:
    if role == "value_stack" or index == 8:
        return "value_bundle"
    if role == "lifestyle_payoff" or index == 9:
        return "conversion_close"
    return ""


def apply_amazon_listing_plan(plan: dict) -> dict:
    from generation.services.listing_bundle import strategy_brief_index_for_shot

    plan.setdefault("listing_image_doctrine", AMAZON_LISTING_IMAGE_DOCTRINE_ZH)
    plan["article_matrix_hint"] = AMAZON_ARTICLE_MATRIX_HINT_ZH
    strategy = plan.get("ecommerce_strategy") or {}
    briefs = strategy_brief_by_index(strategy)
    geo = (plan.get("scene_geo_en") or "United States").strip()
    adj = (plan.get("scene_geo_adj_en") or geo).strip()

    TRUST_SCENE_AMAZON = (
        f"Real-life trust / scene — SKU in authentic {adj} daily environment; natural light; "
        "product readable; no dominant face."
    )
    FEATURE_DEMO = (plan.get("amazon_feature_demo_summary_en") or "").strip() or (
        "Active function demonstration — prove effect in use; hands allowed; not crowd portrait."
    )

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()
        brief = briefs.get(strategy_brief_index_for_shot(plan, idx)) or {}
        _copy_brief_fields(shot, brief)

        if role == "white_bg_catalog" or idx == 1:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            shot["composition_mandate"] = (
                f"{existing_comp} {WHITE_BG_NO_TEXT_EN}".strip()
                if existing_comp
                else WHITE_BG_NO_TEXT_EN
            )
            shot["white_bg_text_lock"] = WHITE_BG_NO_TEXT_EN
            shot["human_cast_mode"] = "none"
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["key_message_es"] = ""
            shot["prompt_es"] = ""
            shot["icon_bullets_es"] = []

        if role == "hero_hook" or idx == 2:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            if "HERO" not in existing_comp.upper():
                shot["composition_mandate"] = (
                    f"{existing_comp} {HERO_VISUAL_IMPACT_EN}".strip()
                    if existing_comp
                    else HERO_VISUAL_IMPACT_EN
                )
            shot.setdefault("human_cast_mode", "none")
            shot["hero_visual_impact_lock"] = HERO_VISUAL_IMPACT_EN.replace("TikTok", "Amazon")

        if role == "usp_primary" and idx == 4:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            if "FRAME 4" not in existing_comp and "before/after" not in existing_comp.lower():
                shot["composition_mandate"] = (
                    f"{existing_comp} {USP_PRIMARY_PAIN_VISUAL}".strip()
                    if existing_comp
                    else USP_PRIMARY_PAIN_VISUAL
                )
            shot.setdefault("human_cast_mode", "none")

        if role == "trust_quality" and idx == 4:
            extra = (shot.get("composition_mandate") or "").strip()
            if TRUST_SCENE_AMAZON not in extra:
                shot["composition_mandate"] = f"{extra} {TRUST_SCENE_AMAZON}".strip() if extra else TRUST_SCENE_AMAZON
            shot.setdefault("human_cast_mode", "none")

        if role == "ease_objection" and idx == 6:
            extra = (shot.get("composition_mandate") or "").strip()
            if FEATURE_DEMO not in extra:
                shot["composition_mandate"] = f"{extra} {FEATURE_DEMO}".strip() if extra else FEATURE_DEMO
            shot.setdefault("human_cast_mode", "hands")

        if role == "value_stack" and idx == 7:
            mandate = LAYOUT_MANDATES.get("value_bundle", "")
            if mandate:
                extra = (shot.get("composition_mandate") or "").strip()
                shot["composition_mandate"] = f"{extra} {mandate}".strip() if extra else mandate
            shot.setdefault("human_cast_mode", "none")

        subtype = (shot.get("layout_subtype") or brief.get("layout_subtype") or "").strip()
        if not subtype and role == "value_stack" and idx == 7:
            subtype = "kit_contents"
        if subtype:
            shot["layout_subtype"] = subtype
            mandate = LAYOUT_MANDATES.get(subtype)
            if mandate:
                extra = (shot.get("composition_mandate") or "").strip()
                shot["composition_mandate"] = f"{extra} {mandate}".strip() if extra else mandate

    return plan


def apply_tk_mx_listing_plan(plan: dict) -> dict:
    from generation.services.listing_bundle import is_listing_ecommerce_plan, strategy_brief_index_for_shot

    if not is_listing_ecommerce_plan(plan):
        return plan

    if (plan.get("plan_template") or "") == "amazon_listing_7":
        return apply_amazon_listing_plan(plan)

    plan.setdefault("listing_image_doctrine", LISTING_IMAGE_DOCTRINE_ZH)
    plan["article_matrix_hint"] = ARTICLE_MATRIX_HINT_ZH
    strategy = plan.get("ecommerce_strategy") or {}
    briefs = strategy_brief_by_index(strategy)

    hero_px = getattr(settings, "TK_MX_HERO_OUTPUT_SIZE", 1280)
    try:
        hero_px = max(512, min(2048, int(hero_px)))
    except (TypeError, ValueError):
        hero_px = 1280
    plan["tk_mx_hero_output_pixels"] = hero_px

    fixed_by_index = {int(f["index"]): f for f in TK_MX_NINE_FRAME_MATRIX}

    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        frame_fix = fixed_by_index.get(idx) or {}
        if frame_fix.get("frame_contract") == "fixed":
            shot["role"] = frame_fix["role"]
            shot["frame_contract"] = "fixed"
            shot["marketing_pillar"] = frame_fix.get("marketing_pillar", shot.get("marketing_pillar"))
            shot["visual_archetype"] = frame_fix.get("visual_archetype", shot.get("visual_archetype"))
            shot["scene_family"] = frame_fix.get("scene_family", shot.get("scene_family"))
        role = (shot.get("role") or "").strip()
        brief = briefs.get(strategy_brief_index_for_shot(plan, idx)) or {}
        _copy_brief_fields(shot, brief)

        if role == "hero_hook" or idx == 1:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            if "HERO LISTING IMAGE" not in existing_comp:
                shot["composition_mandate"] = (
                    f"{existing_comp} {HERO_LAYERED_MX_COMPOSITION}".strip()
                    if existing_comp
                    else HERO_LAYERED_MX_COMPOSITION
                )
            shot["hero_output_size"] = hero_px
            shot.setdefault("human_cast_mode", "none")
            shot["hero_visual_impact_lock"] = HERO_VISUAL_IMPACT_EN
            harmony = (plan.get("listing_color_temperature_lock_en") or "").strip()
            if harmony:
                shot["hero_color_harmony_en"] = (
                    f"HERO must share the same color temperature and palette as the full 9-frame set. {harmony[:500]}"
                )

        if role == "white_bg_catalog" or idx == 2:
            shot["role"] = "white_bg_catalog"
            shot["frame_contract"] = "fixed"
            existing_comp = (shot.get("composition_mandate") or "").strip()
            shot["composition_mandate"] = (
                f"{existing_comp} {WHITE_BG_NO_TEXT_EN}".strip()
                if existing_comp
                else WHITE_BG_NO_TEXT_EN
            )
            shot["white_bg_text_lock"] = WHITE_BG_NO_TEXT_EN
            shot["prompt_en"] = WHITE_BG_SCENE_PROMPT_EN
            shot["product_pose_lock_en"] = WHITE_BG_UPRIGHT_POSE_LOCK_EN
            shot["orientation_lock"] = (
                "front orthographic catalog, product vertical upright, no yaw/pitch/roll on package"
            )
            shot["scene_zh"] = "纯白底合规产品图"
            shot["composition_zh"] = "正面直立居中纯白底，无场景无文案"
            shot["human_cast_mode"] = "none"
            extra_neg = (shot.get("negative_extra") or "").strip()
            shot["negative_extra"] = (
                f"{extra_neg}, tilted product, diagonal lean, lying flat, 30 degree angle, dynamic hero tilt"
            ).strip(", ")
            shot["headline_es"] = ""
            shot["subhead_es"] = ""
            shot["key_message_es"] = ""
            shot["prompt_es"] = ""
            shot["icon_bullets_es"] = []
            shot["diversity_lock"] = (
                "Fixed compliance white catalog — NOT marketing hero, NOT lifestyle, NOT comparison."
            )

        if role == "usp_primary" or idx == 4:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            if "FRAME 4" not in existing_comp:
                shot["composition_mandate"] = (
                    f"{existing_comp} {USP_PRIMARY_PAIN_VISUAL}".strip()
                    if existing_comp
                    else USP_PRIMARY_PAIN_VISUAL
                )
            analysis = plan.get("product_analysis") or {}
            zone = (analysis.get("application_zone") or "").strip()
            from generation.services.product_usage_semantics import zone_requires_model

            if zone_requires_model(zone):
                shot.setdefault("human_cast_mandatory", True)
                if (shot.get("human_cast_mode") or "").lower() in ("none", ""):
                    shot["human_cast_mode"] = "full" if zone == "body_bath" else "face"
            else:
                shot["human_cast_mandatory"] = False
                shot["human_cast_mode"] = "none"

        if role == "trust_quality" or idx == 6:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            if "FRAME 6" not in existing_comp:
                shot["composition_mandate"] = (
                    f"{existing_comp} {TRUST_QUALITY_REAL_LIFE_MX}".strip()
                    if existing_comp
                    else TRUST_QUALITY_REAL_LIFE_MX
                )
            shot.setdefault("human_cast_mode", "face")

        if role == "ease_objection" or idx == 7:
            existing_comp = (shot.get("composition_mandate") or "").strip()
            if "FRAME 7" not in existing_comp:
                shot["composition_mandate"] = (
                    f"{existing_comp} {EASE_OBJECTION_TIKTOK_SOCIAL_PROOF}".strip()
                    if existing_comp
                    else EASE_OBJECTION_TIKTOK_SOCIAL_PROOF
                )
            shot["human_cast_mode"] = "full"
            shot["human_cast_mandatory"] = True

        subtype = (shot.get("layout_subtype") or brief.get("layout_subtype") or "").strip()
        if not subtype:
            subtype = _default_layout_subtype(role, idx)
        if subtype:
            shot["layout_subtype"] = subtype
            mandate = LAYOUT_MANDATES.get(subtype)
            if mandate:
                extra = (shot.get("composition_mandate") or "").strip()
                shot["composition_mandate"] = f"{extra} {mandate}".strip() if extra else mandate

    return plan


def reassert_white_bg_catalog_shots(plan: dict) -> dict:
    """机位多样性之后仍强制图2直立白底，避免 reference/九图斜放文案覆盖。"""
    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        role = (shot.get("role") or "").strip()
        if idx != 2 and role != "white_bg_catalog":
            continue
        shot["role"] = "white_bg_catalog"
        shot["product_pose_lock_en"] = WHITE_BG_UPRIGHT_POSE_LOCK_EN
        shot["orientation_lock"] = (
            "front orthographic catalog, product vertical upright, no yaw/pitch/roll on package"
        )
        shot["prompt_en"] = WHITE_BG_SCENE_PROMPT_EN
        shot["human_cast_mode"] = "none"
        shot.pop("product_action_lock_en", None)
        extra_neg = (shot.get("negative_extra") or "").strip()
        tilt_neg = "tilted product, diagonal lean, lying flat, 30 degree angle, dynamic hero tilt"
        if tilt_neg not in extra_neg.lower():
            shot["negative_extra"] = f"{extra_neg}, {tilt_neg}".strip(", ")

    return plan


def reassert_tk_mx_invariants(plan: dict) -> dict:
    """确认生图最后一轮：图4固定前后对比无字、图7强制模特。"""
    from generation.services.frame4_flex import FRAME_4_VARIANT_ID, apply_frame4_flex_variant

    if (plan.get("plan_template") or "") != "tk_mx_ecommerce_9":
        return plan
    plan = apply_frame4_flex_variant(plan)
    from generation.services.listing_frame6_benefit import apply_tk_frame6_benefit

    plan = apply_tk_frame6_benefit(plan)
    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if idx == 4:
            shot["role"] = "usp_primary"
            shot["frame4_variant"] = FRAME_4_VARIANT_ID
            shot["layout_subtype"] = FRAME_4_VARIANT_ID
        if idx == 7:
            shot["role"] = "ease_objection"
            shot["human_cast_mode"] = "full"
            shot["human_cast_mandatory"] = True
    plan["shots"] = plan.get("shots") or []
    return plan


def format_step1_preview_markdown(plan: dict) -> str:
    """步骤一可读策划摘要（9 镜完整字段）。"""
    from generation.services.listing_bundle import listing_image_count

    n = listing_image_count(plan) or len(plan.get("shots") or []) or 9
    site = (plan.get("marketplace_label_zh") or "").strip()
    header = f"【Listing · {n} 张策划预览" + (f" · {site}" if site else "") + "】"
    lines = [
        header,
        plan.get("listing_image_doctrine") or LISTING_IMAGE_DOCTRINE_ZH,
        "",
    ]
    from generation.services.creative_engine.preview_zh import format_creative_preview_markdown

    creative_block = format_creative_preview_markdown(plan)
    if creative_block:
        lines.append(creative_block)
        lines.append("")
    from generation.services.action_planning.preview_zh import format_action_preview_markdown

    action_block = format_action_preview_markdown(plan)
    if action_block:
        lines.append(action_block)
        lines.append("")
    if plan.get("article_matrix_hint"):
        lines.append(plan["article_matrix_hint"])
        lines.append("")

    for shot in sorted(plan.get("shots") or [], key=lambda s: int(s.get("index") or 0)):
        idx = shot.get("index")
        role = shot.get("role", "")
        lines.append(f"### 第 {idx} 张 · {role}")
        if shot.get("action_master_zh") or shot.get("primary_action_id"):
            lines.append(
                f"- 产品动作：{shot.get('action_master_zh') or shot.get('primary_action_id')}"
            )
        if shot.get("ingredient_composition_only"):
            lines.append("- 成分镜：整图展示原料/质地细节，画面中不出现产品瓶或包装")
        if shot.get("image_goal_zh"):
            lines.append(f"- 目标：{shot['image_goal_zh']}")
        if shot.get("composition_zh"):
            lines.append(f"- 构图：{shot['composition_zh']}")
        if shot.get("scene_zh"):
            lines.append(f"- 场景：{shot['scene_zh']}")
        hl = shot.get("headline_es") or ""
        sh = shot.get("subhead_es") or ""
        if hl or sh:
            lines.append(f"- 西语标题：{hl}" + (f" / {sh}" if sh else ""))
        bullets = shot.get("icon_bullets_es") or []
        if bullets:
            lines.append("- ICON卖点：" + " · ".join(str(b) for b in bullets[:3]))
        elif shot.get("key_message_es"):
            lines.append(f"- 西语文案：{shot['key_message_es']}")
        elif shot.get("assigned_primary_message_es"):
            lines.append(f"- 本镜主卖点（西语）：{shot['assigned_primary_message_es']}")
        if shot.get("frame3_variant") or (shot.get("index") == 3 and shot.get("layout_subtype")):
            fv = shot.get("frame3_variant") or shot.get("layout_subtype")
            label = plan.get("frame3_variant_label_zh") if int(shot.get("index") or 0) == 3 else ""
            if not label and fv:
                from generation.services.frame3_flex import VARIANT_BY_ID

                label = (VARIANT_BY_ID.get(fv) or {}).get("label_zh", fv)
            lines.append(f"- 图3版式：{fv}" + (f"（{label}）" if label else ""))
        elif shot.get("frame4_variant") or (shot.get("index") == 4 and shot.get("layout_subtype")):
            fv = shot.get("frame4_variant") or shot.get("layout_subtype")
            label = plan.get("frame4_variant_label_zh") if int(shot.get("index") or 0) == 4 else ""
            if not label and fv:
                from generation.services.frame4_flex import VARIANT_BY_ID

                label = (VARIANT_BY_ID.get(fv) or {}).get("label_zh", fv)
            lines.append(f"- 图4版式：{fv}" + (f"（{label}）" if label else ""))
        elif int(shot.get("index") or 0) == 3 and (shot.get("frame5_variant") or "") == "specs_features":
            lines.append("- 图3版式：规格与尺寸（固定）")
        elif int(shot.get("index") or 0) == 5 and (shot.get("frame3_variant") or shot.get("layout_subtype")):
            fv = shot.get("frame3_variant") or shot.get("layout_subtype")
            from generation.services.frame3_flex import VARIANT_BY_ID as F3

            label = (F3.get(fv) or {}).get("label_zh", fv)
            lines.append(f"- 图5版式（细节）：{fv}" + (f"（{label}）" if label else ""))
        elif shot.get("frame9_variant") or (shot.get("index") == 9 and shot.get("layout_subtype")):
            fv = shot.get("frame9_variant") or shot.get("layout_subtype")
            label = plan.get("frame9_variant_label_zh") if int(shot.get("index") or 0) == 9 else ""
            try:
                from generation.services.frame9_conversion import VARIANT_BY_ID

                label = label or VARIANT_BY_ID.get(fv, {}).get("label_zh", "")
            except Exception:
                pass
            lines.append(f"- 图9版式：{fv}" + (f"（{label}）" if label else ""))
        elif shot.get("frame5_variant") or (shot.get("index") == 5 and shot.get("layout_subtype")):
            fv = shot.get("frame5_variant") or shot.get("layout_subtype")
            label = plan.get("frame5_variant_label_zh") if int(shot.get("index") or 0) == 5 else ""
            if not label and fv:
                from generation.services.frame5_flex import VARIANT_BY_ID

                label = (VARIANT_BY_ID.get(fv) or {}).get("label_zh", fv)
            lines.append(f"- 图5版式：{fv}" + (f"（{label}）" if label else ""))
        elif shot.get("layout_subtype"):
            lines.append(f"- 版式：{shot['layout_subtype']}")
        pe = (shot.get("prompt_en") or "")[:500]
        if pe:
            lines.append(f"- 生图提示词（摘要）：{pe}…" if len(shot.get("prompt_en") or "") > 500 else f"- 生图提示词：{pe}")
        lines.append("")
    return "\n".join(lines).strip()
