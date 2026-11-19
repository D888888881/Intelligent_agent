"""电商主图策略：卖点 / 痛点 / 购买动机 → 9 张差异化视觉矩阵。"""

import json

from django.conf import settings

# 9 张图固定「营销职能」，避免只做角度微调
TK_MX_NINE_FRAME_MATRIX = [
    {
        "index": 1,
        "role": "hero_hook",
        "frame_contract": "fixed",
        "marketing_pillar": "购买动机",
        "consumer_question": "3 秒内抓住注意力：这对我有什么用？",
        "visual_archetype": "scroll_stopper_hero",
        "scene_family": "studio_hero",
    },
    {
        "index": 2,
        "role": "white_bg_catalog",
        "frame_contract": "fixed",
        "marketing_pillar": "平台合规",
        "consumer_question": "看清商品本体、规格与包装",
        "visual_archetype": "catalog_white_seamless",
        "scene_family": "pure_white",
    },
    {
        "index": 3,
        "role": "pain_empathy",
        "frame_contract": "creative_detail",
        "marketing_pillar": "卖点呈现",
        "consumer_question": "解决了什么痛点？细节是否靠谱？（批次轮换两种画面）",
        "visual_archetype": "frame3_flex_rotation",
        "scene_family": "benefit_or_detail_macro",
    },
    {
        "index": 4,
        "role": "usp_primary",
        "frame_contract": "flex_variant",
        "marketing_pillar": "痛点对比",
        "consumer_question": "用了以后改善有多明显？（纯视觉，无对比文字）",
        "visual_archetype": "pain_before_after_single_photo",
        "scene_family": "transformation_visual_only",
    },
    {
        "index": 5,
        "role": "usp_secondary",
        "frame_contract": "flex_variant",
        "marketing_pillar": "对比/规格/功能",
        "consumer_question": "对比、规格、步骤或核心功能中，本帧展示哪一类信息？",
        "visual_archetype": "frame5_flex_rotation",
        "scene_family": "specs_compare_or_steps",
    },
    {
        "index": 6,
        "role": "trust_quality",
        "frame_contract": "creative_detail",
        "marketing_pillar": "信任背书",
        "consumer_question": "在真实日常生活里，品质是否靠谱、值得信赖？",
        "visual_archetype": "real_life_trust_context",
        "scene_family": "mexico_daily_environment",
    },
    {
        "index": 7,
        "role": "ease_objection",
        "frame_contract": "creative_detail",
        "marketing_pillar": "人群种草",
        "consumer_question": "和我类似的人也在用吗？画面真实、适合我吗？",
        "visual_archetype": "tiktok_social_proof_in_use",
        "scene_family": "target_audience_lifestyle",
    },
    {
        "index": 8,
        "role": "value_stack",
        "frame_contract": "creative_detail",
        "marketing_pillar": "性价比/套装",
        "consumer_question": "买到什么、是否划算？",
        "visual_archetype": "bundle_flatlay_value",
        "scene_family": "topdown_kit",
    },
    {
        "index": 9,
        "role": "lifestyle_payoff",
        "frame_contract": "creative_detail",
        "marketing_pillar": "强转化收尾",
        "consumer_question": "值得买吗？适合日常/送礼/家人吗？（购买氛围而非再一次纯产品特写）",
        "visual_archetype": "frame9_conversion_rotation",
        "scene_family": "purchase_atmosphere_close",
    },
]

# Amazon 7 图（卖家叙事顺序，独立矩阵 — 非 TikTok 九图压缩）
AMAZON_LISTING_7_FRAME_MATRIX = [
    {
        "index": 1,
        "role": "white_bg_catalog",
        "frame_contract": "fixed",
        "marketing_pillar": "主图合规",
        "consumer_question": "看清商品本体，符合 Amazon 主图规范",
        "visual_archetype": "amazon_main_white_catalog",
        "scene_family": "pure_white",
    },
    {
        "index": 2,
        "role": "hero_hook",
        "frame_contract": "fixed",
        "marketing_pillar": "核心卖点",
        "consumer_question": "为什么值得买？核心购买价值是什么？",
        "visual_archetype": "amazon_core_value_hero",
        "scene_family": "studio_value_hero",
    },
    {
        "index": 3,
        "role": "usp_secondary",
        "frame_contract": "flex_variant",
        "marketing_pillar": "规格参数",
        "consumer_question": "尺寸、容量、颜色等规格疑问能否一眼看懂？",
        "visual_archetype": "specs_callout_single_photo",
        "scene_family": "infographic_product_hero",
    },
    {
        "index": 4,
        "role": "usp_primary",
        "frame_contract": "flex_variant",
        "marketing_pillar": "对比或场景",
        "consumer_question": "痛点前后变化明显吗？或真实使用场景能否代入？（批次轮换）",
        "visual_archetype": "amazon_frame4_dual_rotation",
        "scene_family": "transformation_or_real_life_scene",
    },
    {
        "index": 5,
        "role": "pain_empathy",
        "frame_contract": "creative_detail",
        "marketing_pillar": "细节品质",
        "consumer_question": "材质做工、细节特写或成分是否可信？",
        "visual_archetype": "frame3_flex_rotation",
        "scene_family": "benefit_or_detail_macro",
    },
    {
        "index": 6,
        "role": "ease_objection",
        "frame_contract": "creative_detail",
        "marketing_pillar": "功能演示",
        "consumer_question": "功能/效果如何被直观证明？",
        "visual_archetype": "feature_demonstration_in_use",
        "scene_family": "proof_of_function",
    },
    {
        "index": 7,
        "role": "value_stack",
        "frame_contract": "creative_detail",
        "marketing_pillar": "包装配件",
        "consumer_question": "盒内有什么、买到什么？",
        "visual_archetype": "whats_in_the_box",
        "scene_family": "kit_layout_angled",
    },
]


def build_marketing_strategy(product_analysis: dict, user_prompt: str) -> dict:
    """基于商品分析 + 用户需求，生成 9 帧营销策略（优先 LLM）。"""
    from chat.services.openai_client import is_chat_configured, get_openai_client

    base = _strategy_fallback(product_analysis, user_prompt)
    if product_analysis.get("pain_points"):
        base["pain_points"] = product_analysis["pain_points"]
    if product_analysis.get("purchase_motivations"):
        base["purchase_motivations"] = product_analysis["purchase_motivations"]
    if not is_chat_configured():
        return base

    matrix_json = json.dumps(TK_MX_NINE_FRAME_MATRIX, ensure_ascii=False)
    system = (
        "你是 TikTok Shop 墨西哥站「电商主图分析大师」：全套 9 张均为 Listing 主图（1 场景分层主图 + 1 白底 + 7 职能详情），"
        "先解剖商品再策划视觉。输出单个 JSON，无 markdown。"
        "顶层字段：product_summary_zh, target_buyer_zh, purchase_motivations[], pain_points[], "
        "core_usps[], objections[], trust_signals[], mexico_angle_zh, conversion_story_zh。"
        "shot_briefs：长度必须 9，与 matrix 的 index/role 一一对应；每项除 matrix 字段外还必须含："
        "image_goal_zh, composition_zh, scene_zh, headline_es（index1 必填主标题，8 词内）, subhead_es（index1 副标题可空）, "
        "icon_bullets_es（index1 为长度3的数组，每项2-3西语单词；其他镜可[]）, "
        "key_message_es（西语 3-8 词）, creative_direction_en（80+ 词，独特画面）, diversity_lock, "
        "layout_subtype（index 5 可选 category_compare|specs_features|kit_contents|usage_steps|core_functions；"
        "index 8 用 specs_features 或 value_bundle；index 9 用 benefit_summary 或 conversion_close）。"
        "index 1 hero_hook：强视觉冲击 scroll-stopper（高对比/景深/光束/色块场景），产品约40-52%，西语标题+icon 辅佐画面；非白底、非平淡 packshot。"
        "index 2 white_bg_catalog：纯白合规 catalog，禁止任何营销文案/贴纸/icon，仅产品+包装原有印刷。"
        "creative_direction_en 必须包含明确的 product facing / camera angle（互不相同）。"
        "必须消费 product_analysis 的 before/after、same_category_comparison、key_selling_points、visual_identity。"
        "index 3 批次轮换：卖点解决对比（舒适/收纳/省空间/顺滑/耐用/显瘦/方便等，纯视觉）或产品细节特写（材质/纹理/做工/接口/标签/包装局部）；"
        "4 痛点对比（批次轮换：单图使用前/使用后 或 普通品/本品，纯视觉禁 antes/después/使用前/使用后 等字）；"
        "5 由系统按批次轮换：品类对比 / 规格属性 / 套装清单 / 使用步骤 / 核心功能（layout_subtype 五选一作参考，实际以批次为准）；"
        "6 真实生活场景信任图（墨西哥家庭/浴室/卧室/厨房/街拍/办公室等，产品自然置景或轻度使用态，真实光线，非临床白底微距）；"
        "7 目标人群场景种草（真人正在使用、自然真实、TikTok UGC 感，半身或 3/4，非纯手部步骤）；8 规格或套装；9 卖点总结或强转化收尾。"
        "人物：全组最多 2–3 帧出现人（含手）；index 2/5 无人；index 6 优先环境+产品，可无脸或仅手/背影；"
        "index 1 默认产品为主少露脸；index 7 为核心人群镜，优先露目标消费者。"
        "合规：禁止医疗夸大、绝对化承诺；西语墨西哥本地化短句；成图禁止中文（勿在 headline_es/icon 写中文，包装标签除外）。"
    )
    user = "\n".join(
        [
            f"user_prompt={user_prompt[:3000]}",
            f"product_analysis={json.dumps(product_analysis or {}, ensure_ascii=False)[:10000]}",
            f"fixed_matrix={matrix_json}",
        ]
    )
    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.75,
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        briefs = data.get("shot_briefs") or []
        if len(briefs) != 9:
            data["shot_briefs"] = base.get("shot_briefs")
        return {**base, **data}
    except Exception:
        return base


def _strategy_fallback(product_analysis: dict, user_prompt: str) -> dict:
    usps = product_analysis.get("key_selling_points") or []
    pains = product_analysis.get("pain_points") or []
    if not pains:
        pains = ["日常困扰", "效果不稳定", "使用麻烦"]
    if not usps:
        usps = ["品质可靠", "易于使用", "性价比高"]

    headlines = product_analysis.get("spanish_headlines") or []
    h = lambda i: headlines[i % len(headlines)] if headlines else "Calidad premium"

    briefs = []
    for frame in TK_MX_NINE_FRAME_MATRIX:
        idx = frame["index"]
        role = frame["role"]
        creative = _fallback_creative_en(role, user_prompt, usps, pains, product_analysis)
        layout_subtype = ""
        if idx == 8:
            layout_subtype = "specs_features"
        elif idx == 9:
            layout_subtype = "conversion_close"
        headline = h(idx - 1) if role != "white_bg_catalog" else ""
        briefs.append(
            {
                **frame,
                "image_goal_zh": frame.get("consumer_question", "")[:80],
                "composition_zh": "单图1:1，产品主体清晰",
                "scene_zh": "墨西哥电商主图场景",
                "headline_es": headline if idx == 1 else "",
                "subhead_es": (usps[0] if usps else "")[:40] if idx == 1 else "",
                "icon_bullets_es": [str(u)[:20] for u in usps[:3]] if idx == 1 and usps else [],
                "key_message_es": headline if role != "white_bg_catalog" else "",
                "creative_direction_en": creative,
                "diversity_lock": f"Unique marketing frame '{role}' — not a minor angle change of other shots.",
                "layout_subtype": layout_subtype,
            }
        )

    return {
        "product_summary_zh": product_analysis.get("primary_function") or user_prompt[:200],
        "purchase_motivations": ["解决问题", "提升形象", "省时省心"],
        "pain_points": pains[:4] if isinstance(pains, list) else [str(pains)],
        "core_usps": usps[:4] if isinstance(usps, list) else [str(usps)],
        "shot_briefs": briefs,
    }


def _fallback_before_scene(analysis: dict, pain_fallback: str) -> str:
    before = (analysis.get("before_use_state") or pain_fallback or "problem before use")[:300]
    return (
        f"BEFORE-use problem state (single photograph, no product hero yet or product small): "
        f"{before}. Relatable Mexican home context, muted tones, empathy-first, not a packshot."
    )


def _fallback_before_after(analysis: dict, usp_fallback: str) -> str:
    before = (analysis.get("before_use_state") or "before condition")[:200]
    after = (analysis.get("after_use_state") or "improved after use")[:200]
    visual = (analysis.get("before_after_visual_en") or "").strip()
    extra = visual if visual else (
        f"One cohesive studio/lifestyle photo expressing transformation from '{before}' to '{after}' "
        f"while hero product {usp_fallback} is prominent; use lighting/color/contrast or split visual weight, "
        f"NOT a multi-panel collage grid."
    )
    return (
        f"Before/after transformation in ONE frame: {extra} "
        "Do NOT render before/after or 使用前/使用后 text on the image — visual contrast only."
    )


def _fallback_category_compare(analysis: dict, usp_fallback: str) -> str:
    comp = analysis.get("same_category_comparison") or {}
    if isinstance(comp, dict):
        generic = (comp.get("generic_alternative_en") or "plain unbranded generic same-category product")[:200]
        shot = (comp.get("comparison_shot_en") or "").strip()
        adv = comp.get("our_advantages_en") or []
        adv_txt = "; ".join(str(x) for x in adv[:4]) if adv else usp_fallback
    else:
        generic = "plain unbranded generic alternative"
        shot = ""
        adv_txt = usp_fallback
    if not shot:
        shot = (
            f"Single studio photograph: our branded SKU on the right looking premium, "
            f"generic alternative ({generic}) on the left looking dull; same surface and lighting; "
            f"highlights advantages: {adv_txt}. No competitor logos or trademarked brands."
        )
    return shot


def _fallback_creative_en(role: str, user_prompt: str, usps: list, pains: list, analysis: dict) -> str:
    fn = (analysis.get("primary_function") or user_prompt)[:400]
    usp1 = usps[0] if usps else "quality"
    usp2 = usps[1] if len(usps) > 1 else "easy to use"
    pain1 = pains[0] if pains else "daily frustration"
    templates = {
        "hero_hook": (
            f"TikTok scroll-stopper hero: product as star (prefer NO model face) with bold Spanish headline space, "
            f"emotional lighting, dynamic composition, communicates {usp1}, not a plain packshot."
        ),
        "white_bg_catalog": (
            "Pure #FFFFFF seamless catalog shot, front-facing product only, even softbox, "
            "full margins for TikTok Shop compliance."
        ),
        "pain_empathy": (
            "Listing frame 3 (batch variant): EITHER benefit-solve visual — comfort, storage, space-saving, "
            "smooth, durable, slimming, convenience — OR product detail macro on material, texture, craft, "
            "label, packaging; no portrait; differs from frames 4 and 6."
        ),
        "usp_primary": _fallback_before_after(analysis, usp1),
        "usp_secondary": _fallback_category_compare(analysis, usp2),
        "trust_quality": (
            "Real-life trust scene in Mexico: product believably placed or lightly in-use in a natural "
            "daily environment — home living room, bathroom vanity, bedroom nightstand, kitchen counter, "
            "street café table, or modern office desk; warm/natural light, lived-in details, commercial "
            "clarity on SKU; communicates quality through authentic context, NOT sterile clinical macro "
            "on pure white; avoid full-face portrait (save for frame 7); must differ from frame 3 problem still."
        ),
        "ease_objection": (
            "TikTok-style crowd/social-proof scene: target consumer actively using the product in a "
            "believable Mexico daily-life setting — natural light, candid mid-action, relatable "
            "half-body or 3/4 portrait, product clearly visible in use; organic creator seeding vibe, "
            "NOT stiff catalog pose, NOT hands-only macro tutorial; gesture must differ from frames 3 and 9."
        ),
        "value_stack": (
            "Value story: kit contents from package_includes on shelf or angled layout (avoid duplicate top-down grid), "
            "value-for-money narrative, warm surface."
        ),
        "lifestyle_payoff": (
            "Conversion CLOSE frame 9: purchase atmosphere (daily essential / gift / family must-have / "
            "worth buying / benefit summary / lifestyle aspiration) — scene and props lead; product supports. "
            f"After-use mood when relevant: {(analysis.get('after_use_state') or fn)[:120]}. "
            "NOT lone packshot repeat of hero."
        ),
    }
    return templates.get(role, f"Unique e-commerce visual for {role}. {fn}")


def strategy_brief_by_index(strategy: dict) -> dict[int, dict]:
    out = {}
    for brief in strategy.get("shot_briefs") or []:
        try:
            out[int(brief["index"])] = brief
        except (KeyError, TypeError, ValueError):
            continue
    return out
