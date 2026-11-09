import json



from django.conf import settings



from generation.services.ecommerce_strategy import (
    TK_MX_NINE_FRAME_MATRIX,
    build_marketing_strategy,
    strategy_brief_by_index,
)
from generation.services.intent import detect_plan_template



QUALITY_PREFIX = (

    "Ultra-high-quality commercial e-commerce product photography, 1:1 square, "

    "sharp focus, accurate colors, professional retouching, TikTok Shop listing ready, "

    "single photograph one frame only."

)



TK_MX_NEGATIVE = (

    "collage, grid layout, split screen, multiple panels, contact sheet, photo montage, "

    "diptych, triptych, duplicate of reference photo, same background as reference, "

    "same camera angle as reference, watermark, blurry text, misspelled Spanish, "

    "English text, Chinese text, distorted logo, low resolution, amateur lighting, "
    "wrong product, different SKU, generic packaging, substitute bottle, altered label, "
    "wrong colorway, missing logo, fake brand, simplified design, different cap shape"

)





def build_plan(

    user_prompt: str,

    image_count: int,

    reference_summary: str = "",

    plan_template: str | None = None,

    product_analysis: dict | None = None,

) -> dict:

    """生成套图策划 JSON。"""

    image_count = max(1, min(image_count, settings.GEN_MAX_IMAGE_COUNT))

    if plan_template == "generic":

        template = None

    elif plan_template and plan_template != "auto":

        template = plan_template

    else:

        template = detect_plan_template(user_prompt, image_count)



    analysis = product_analysis or {}

    product_identity = _product_identity_from_analysis(analysis, reference_summary, user_prompt)



    if template == "photo_refine":
        plan = _plan_photo_refine(user_prompt, product_identity, analysis)
        return _finalize_plan(plan, product_identity, analysis, template)

    if template == "tk_mx_ecommerce_9":
        marketing_strategy = build_marketing_strategy(analysis, user_prompt)
        plan = _plan_tk_mx_ecommerce_9(user_prompt, product_identity, analysis, marketing_strategy)
        from chat.services.openai_client import is_chat_configured

        if is_chat_configured():
            enriched = _plan_with_openai(
                user_prompt,
                9,
                product_identity,
                template_hint=template,
                base_plan=plan,
                product_analysis=analysis,
                marketing_strategy=marketing_strategy,
            )
            if enriched:
                return _finalize_plan(enriched, product_identity, analysis, template, marketing_strategy)
        return _finalize_plan(plan, product_identity, analysis, template, marketing_strategy)



    from chat.services.openai_client import is_chat_configured



    if is_chat_configured():

        plan = _plan_with_openai(

            user_prompt,

            image_count,

            product_identity,

            product_analysis=analysis,

        )

        if plan:

            return _finalize_plan(plan, product_identity, analysis, template)

    return _finalize_plan(

        _plan_fallback(user_prompt, image_count, product_identity),

        product_identity,

        analysis,

        template,

    )





def _build_identity_lock(analysis: dict, product_identity: str) -> str:
    parts = []
    if analysis.get("identity_lock_en"):
        parts.append(str(analysis["identity_lock_en"]))
    if analysis.get("label_text_exact"):
        parts.append(f"Label text (exact): {analysis['label_text_exact']}")
    colors = analysis.get("primary_colors")
    if colors:
        if isinstance(colors, list):
            parts.append("Colors: " + ", ".join(str(c) for c in colors))
        else:
            parts.append(f"Colors: {colors}")
    includes = analysis.get("package_includes")
    if includes and isinstance(includes, list) and includes:
        parts.append("Includes: " + ", ".join(str(x) for x in includes))
    if analysis.get("visual_identity"):
        parts.append(str(analysis["visual_identity"]))
    if not parts and product_identity:
        parts.append(product_identity)
    return " ".join(parts)[:2800]


def _product_identity_from_analysis(analysis: dict, reference_summary: str, user_prompt: str) -> str:

    parts = []

    if analysis.get("product_name_en"):

        parts.append(str(analysis["product_name_en"]))

    if analysis.get("identity_lock_en"):

        parts.append(str(analysis["identity_lock_en"]))

    elif analysis.get("visual_identity"):

        parts.append(str(analysis["visual_identity"]))

    elif analysis.get("raw_analysis"):

        parts.append(str(analysis["raw_analysis"])[:800])

    if analysis.get("label_text_exact"):

        parts.append(f"Label: {analysis['label_text_exact']}")

    if analysis.get("primary_function"):

        parts.append(str(analysis["primary_function"]))

    if parts:

        return " ".join(parts)[:2800]

    base = (reference_summary or "").strip()

    if base:

        return (

            "Use product appearance from analysis below, but do NOT copy reference photo composition. "

            + base[:1200]

        )

    return user_prompt[:800]





def _finalize_plan(
    plan: dict,
    product_identity: str,
    analysis: dict,
    template: str | None,
    marketing_strategy: dict | None = None,
) -> dict:

    plan.setdefault("quality_prefix", QUALITY_PREFIX)

    plan.setdefault("negative_prompt", TK_MX_NEGATIVE if template == "tk_mx_ecommerce_9" else plan.get("negative_prompt"))

    plan["product_identity"] = product_identity

    plan["identity_lock"] = _build_identity_lock(analysis, product_identity)

    plan["product_analysis"] = analysis

    if template == "tk_mx_ecommerce_9":
        plan["default_reference_mode"] = "identity"
    else:
        plan.setdefault("default_reference_mode", "identity")

    plan.setdefault("locale", "es-MX")

    plan.setdefault("aspect_ratio", "1:1")

    if template:

        plan.setdefault("plan_template", template)

    shots = plan.get("shots") or []

    for shot in shots:

        shot.setdefault("reference_mode", plan.get("default_reference_mode", "identity"))

    if template == "tk_mx_ecommerce_9":
        for shot in shots:
            shot["reference_mode"] = "identity"

    if marketing_strategy:
        plan["ecommerce_strategy"] = marketing_strategy
    if not plan.get("planning_summary"):
        plan["planning_summary"] = _planning_summary_text(shots, analysis, marketing_strategy)

    return plan





def _planning_summary_text(shots: list, analysis: dict, marketing_strategy: dict | None = None) -> str:
    lines = []
    fn = analysis.get("primary_function")
    if fn:
        lines.append(f"商品作用：{fn}")
    if analysis.get("before_use_state") or analysis.get("after_use_state"):
        lines.append(
            "使用前后："
            + (analysis.get("before_use_state") or "—")
            + " → "
            + (analysis.get("after_use_state") or "—")
        )
    comp = analysis.get("same_category_comparison")
    if isinstance(comp, dict) and comp.get("generic_alternative_en"):
        lines.append(f"同类型对比基准：{comp.get('generic_alternative_en')[:120]}")
    if marketing_strategy:
        if marketing_strategy.get("product_summary_zh"):
            lines.append(f"策略摘要：{marketing_strategy['product_summary_zh']}")
        motiv = marketing_strategy.get("purchase_motivations") or []
        if motiv:
            lines.append("购买动机：" + " · ".join(str(x) for x in motiv[:4]))
        pains = marketing_strategy.get("pain_points") or []
        if pains:
            lines.append("痛点：" + " · ".join(str(x) for x in pains[:4]))
        usps = marketing_strategy.get("core_usps") or []
        if usps:
            lines.append("核心卖点：" + " · ".join(str(x) for x in usps[:4]))
    lines.append(f"已策划 {len(shots)} 张「营销职能不同」的电商主图（非简单换角度）：")
    for shot in shots:
        idx = shot.get("index")
        role = shot.get("role", "")
        pillar = shot.get("marketing_pillar") or ""
        question = (shot.get("consumer_question") or "")[:60]
        es = (shot.get("prompt_es") or "")[:60]
        lines.append(f"{idx}. [{role}] {pillar} — {question} | ES: {es}")
    return "\n".join(lines)





def _plan_photo_refine(user_prompt: str, product_identity: str, analysis: dict) -> dict:
    """单张参考图优化：去 AI 感、增强真实感，按用户指令重绘。"""
    from generation.services.intent import user_intent_snippet

    subject = user_intent_snippet(user_prompt) or user_prompt[:600]
    scene = (analysis.get("visual_identity") or analysis.get("identity_lock_en") or "")[:800]
    prompt_en = (
        "Professional photorealistic re-render and retouch of the reference advertisement photo. "
        f"User request: {subject}. "
        "Goals: replace anime/cartoon-like model with photorealistic human; reduce uncanny AI face; "
        "natural skin texture with pores and subtle asymmetry; realistic hair strands; natural hands; "
        "believable fabric folds and shoe materials; "
        "consistent outdoor natural lighting and film-like grain; preserve product, Spanish on-image text intent, "
        "overall layout and marketing message unless user asks to change them. "
        "Single full-frame photograph, e-commerce quality, no collage. "
        f"Scene/product anchors from analysis: {scene}"
    )
    shots = [
        {
            "index": 1,
            "role": "photo_refine",
            "marketing_pillar": "图生优化",
            "consumer_question": "让画面更真实、更少 AI 感",
            "visual_archetype": "photorealistic_retouch",
            "scene_family": "same_concept_realism_upgrade",
            "reference_mode": "identity",
            "prompt_es": "",
            "prompt_en": prompt_en,
            "diversity_lock": "One optimized output image, not text advice.",
        }
    ]
    return {
        "plan_template": "photo_refine",
        "style_lock": QUALITY_PREFIX,
        "subject_lock": subject,
        "negative_prompt": TK_MX_NEGATIVE
        + ", cartoon face, plastic skin, waxy skin, dead eyes, extra fingers, deformed hands, "
        "over-smoothed face, doll-like, uncanny valley, 3d render look",
        "aspect_ratio": "1:1",
        "image_count": 1,
        "locale": "es-MX",
        "default_reference_mode": "identity",
        "shots": shots,
        "planning_summary": (
            f"图生优化（1 张）：{subject[:200]}\n"
            "将基于参考图重新生成更真实、更少 AI 感的成片，而非文字分析。"
        ),
    }


def _comparison_snippet_for_shot(role: str, analysis: dict) -> str:
    """把识图 JSON 中的前后对比 / 品类对比注入对应镜头 prompt。"""
    if not analysis:
        return ""
    comp = analysis.get("same_category_comparison") or {}
    if role == "pain_empathy":
        before = (analysis.get("before_use_state") or "").strip()
        if before:
            return f"Before-use state to visualize: {before}."
        return ""
    if role == "usp_primary":
        parts = []
        if analysis.get("before_use_state"):
            parts.append(f"Before: {analysis['before_use_state']}")
        if analysis.get("after_use_state"):
            parts.append(f"After: {analysis['after_use_state']}")
        if analysis.get("before_after_visual_en"):
            parts.append(str(analysis["before_after_visual_en"]))
        return " ".join(parts)[:900]
    if role == "usp_secondary" and isinstance(comp, dict):
        chunks = []
        if comp.get("generic_alternative_en"):
            chunks.append(f"Generic alternative look: {comp['generic_alternative_en']}")
        adv = comp.get("our_advantages_en") or []
        if adv:
            chunks.append("Our advantages: " + "; ".join(str(x) for x in adv[:5]))
        if comp.get("comparison_shot_en"):
            chunks.append(str(comp["comparison_shot_en"]))
        return " ".join(chunks)[:900]
    if role == "lifestyle_payoff" and analysis.get("after_use_state"):
        return f"Reinforce after-use outcome: {analysis['after_use_state']}."
    return ""


def _plan_tk_mx_ecommerce_9(
    user_prompt: str,
    product_identity: str,
    analysis: dict,
    marketing_strategy: dict,
) -> dict:
    """TikTok 墨西哥 9 图：按营销矩阵策划，每张承担不同转化任务。"""
    subject = user_prompt[:800]
    briefs = strategy_brief_by_index(marketing_strategy or {})
    shots = []

    for frame in TK_MX_NINE_FRAME_MATRIX:
        idx = frame["index"]
        brief = briefs.get(idx, frame)
        creative = (brief.get("creative_direction_en") or "").strip()
        if not creative:
            creative = (
                f"Unique {frame['visual_archetype']} for {frame['marketing_pillar']}: "
                f"{brief.get('consumer_question', frame['consumer_question'])}"
            )
        prompt_en = (
            f"{creative} "
            f"Marketing pillar: {brief.get('marketing_pillar', frame['marketing_pillar'])}. "
            f"Visual archetype: {brief.get('visual_archetype', frame['visual_archetype'])}. "
            f"Scene family: {brief.get('scene_family', frame['scene_family'])}. "
            "Do NOT create a simple packshot with minor rotation — tell a different story beat. "
            "Explicitly rotate product to a unique camera angle vs the other 8 frames (not the same front-facing pose). "
            f"User brief: {subject}. "
            f"Diversity lock: {brief.get('diversity_lock', 'Must differ from the other 8 listing frames')}. "
            "Same product SKU as reference; new scene narrative only."
        )
        compare = _comparison_snippet_for_shot(brief.get("role", frame["role"]), analysis)
        if compare:
            prompt_en += f" Comparison context: {compare}"
        shots.append(
            {
                "index": idx,
                "role": brief.get("role", frame["role"]),
                "frame_contract": brief.get("frame_contract", frame.get("frame_contract", "")),
                "marketing_pillar": brief.get("marketing_pillar", frame["marketing_pillar"]),
                "consumer_question": brief.get("consumer_question", frame["consumer_question"]),
                "visual_archetype": brief.get("visual_archetype", frame["visual_archetype"]),
                "scene_family": brief.get("scene_family", frame["scene_family"]),
                "diversity_lock": brief.get("diversity_lock", ""),
                "reference_mode": "identity",
                "prompt_es": brief.get("key_message_es") or "",
                "prompt_en": prompt_en,
            }
        )

    return {
        "plan_template": "tk_mx_ecommerce_9",
        "style_lock": QUALITY_PREFIX,
        "subject_lock": subject,
        "negative_prompt": TK_MX_NEGATIVE
        + ", repetitive packshot, same composition as other listing images, minor angle tweak only",
        "aspect_ratio": "1:1",
        "image_count": 9,
        "locale": "es-MX",
        "default_reference_mode": "identity",
        "shots": shots,
    }





def _plan_with_openai(

    user_prompt: str,

    image_count: int,

    product_identity: str,

    template_hint: str | None = None,

    base_plan: dict | None = None,

    product_analysis: dict | None = None,
    marketing_strategy: dict | None = None,
) -> dict | None:

    from chat.services.openai_client import get_openai_client



    client = get_openai_client()

    extra = ""

    if template_hint == "tk_mx_ecommerce_9":

        extra = """
模板 tk_mx_ecommerce_9：9 张图 = 9 种「营销职能」，不是 9 次微调角度。

【固定四张 — 职能不可改，仅可丰富 prompt】
index 1 hero_hook 主图；index 2 white_bg_catalog 白底；index 4 usp_primary 单张使用前后对比；
index 5 usp_secondary 本品 vs 同品类 generic 无商标替代品并排。
【创意五张详情 — index 3,6,7,8,9】
pain_empathy / trust_quality / ease_objection / value_stack / lifestyle_payoff：
卖点、人物动作、机位、信息密度必须互斥；该多元素时可丰富（套装平铺），该简洁时微距/留白（trust）；
美妆护肤：禁止多帧重复「涂面膜/贴痘贴」同一动作；3=问题态无涂抹，6=材质/成分微距，7=唯一步骤演示，8=套装/价值故事，9=用后生活不含重复涂抹。

【人物频率 — 必须动态控制，禁止每套都 5 张出人】
全组 9 张最多 2–3 张出现人（含手部）；全脸/半身最多 1–2 张；主图 index 1 优先产品主体无模特。
index 2/5/6 必须无人物；index 4 前后对比优先光影/产品/局部皮肤，避免大正脸；index 3/9 优先环境叙事，可完全无脸。
禁止 3+ 张 bathroom mirror、3+ 张 top-down flat lay、重复 cheek 涂抹动作。

【材质与故事 — 必须可见】
index 6 必须写清膏体/泥/贴材质感、成分或工艺信任点（来自 product_analysis）；index 3/8/9 各讲不同故事 beat，少排版多叙事。

你是电商主图分析大师：先理解购买动机、痛点、卖点、顾虑、信任、性价比、愿景，再写镜头。
规则（违反则不合格）：
1) 每张必须保留 marketing_pillar, consumer_question, visual_archetype, scene_family（与 base_plan 一致或更具体）。
2) prompt_en ≥ 100 词：写「视觉叙事 + 场景家族 + 道具/信息图」；每帧必须写清 distinct camera angle / product facing，禁止 9 张都是正面同角度或同一涂抹动作。
3) index 4 用 product_analysis before/after，禁止拼贴；index 5 用 same_category_comparison；index 8 避免与旧批相同的俯拍网格；index 6 微距材质/成分。
4) prompt_es：西语墨西哥短句；white_bg 可为空。
5) reference_mode 全部为 identity；SKU 一致但构图叙事必须不同。
6) diversity_lock 必须写清与另外 8 张在动作/密度/机位上的差异。
输出 shots 字段：index, role, marketing_pillar, consumer_question, visual_archetype, scene_family,
prompt_en, prompt_es, reference_mode, diversity_lock。
不要 markdown。
"""

    system = (

        "你是 TikTok Shop 墨西哥站资深电商视觉策划。输出 JSON，无 markdown。"

        "字段: style_lock, subject_lock, negative_prompt, aspect_ratio, shots。"

        "shots 长度必须等于 image_count；每项含 index, role, marketing_pillar, prompt_en, prompt_es, reference_mode。"

        f"{extra}"

    )

    user_parts = [

        f"image_count={image_count}",

        f"product_identity={product_identity[:4000]}",

        f"product_analysis={json.dumps(product_analysis or {}, ensure_ascii=False)[:8000]}",

        f"ecommerce_strategy={json.dumps(marketing_strategy or {}, ensure_ascii=False)[:12000]}",

        f"user_prompt={user_prompt}",

    ]

    if base_plan:

        user_parts.append(f"base_plan={json.dumps(base_plan, ensure_ascii=False)[:12000]}")

    try:

        resp = client.chat.completions.create(

            model=settings.OPENAI_CHAT_MODEL,

            messages=[

                {"role": "system", "content": system},

                {"role": "user", "content": "\n".join(user_parts)},

            ],

            response_format={"type": "json_object"},

            temperature=0.7,

        )

        raw = resp.choices[0].message.content or "{}"

        data = json.loads(raw)

        shots = data.get("shots") or []

        if len(shots) != image_count:

            return base_plan

        data["image_count"] = image_count

        if template_hint:

            data["plan_template"] = template_hint

        if base_plan and template_hint == "tk_mx_ecommerce_9":
            base_by_idx = {
                int(s["index"]): s for s in (base_plan.get("shots") or []) if s.get("index") is not None
            }
            for shot in shots:
                try:
                    b = base_by_idx.get(int(shot.get("index")))
                except (TypeError, ValueError):
                    b = None
                if not b:
                    continue
                for key in (
                    "marketing_pillar",
                    "consumer_question",
                    "visual_archetype",
                    "scene_family",
                    "diversity_lock",
                    "role",
                ):
                    shot.setdefault(key, b.get(key))

        return data

    except Exception:

        return base_plan





def _plan_fallback(user_prompt: str, image_count: int, product_identity: str) -> dict:

    roles = ["hero", "white_bg", "angle", "side", "macro", "flatlay", "benefits", "howto", "lifestyle"]

    shots = []

    for i in range(image_count):

        role = roles[i % len(roles)]

        ref = "identity" if role in ("hero", "white_bg") else "none"

        shots.append(

            {

                "index": i + 1,

                "role": role,

                "reference_mode": ref,

                "prompt_es": "",

                "prompt_en": (

                    f"Single standalone commercial product photo, role={role}, new studio setup. "

                    f"{product_identity}. {user_prompt}. Variation {i + 1}/{image_count}, not a copy of reference."

                ),

            }

        )

    return {

        "style_lock": QUALITY_PREFIX,

        "subject_lock": user_prompt[:500],

        "negative_prompt": TK_MX_NEGATIVE,

        "aspect_ratio": "1:1",

        "image_count": image_count,

        "default_reference_mode": "identity",

        "shots": shots,

    }





def summarize_reference_image(attachment, vision_model: str | None = None) -> str:

    if not attachment:

        return ""

    from chat.services.vision import analyze_image_five_s



    try:

        return analyze_image_five_s(

            attachment,

            vision_model=vision_model,

        )

    except Exception as exc:

        return f"参考图分析失败: {exc}"





def analyze_product_for_plan(
    attachments,
    user_prompt: str,
    vision_model: str | None = None,
) -> dict:
    from chat.services.vision import analyze_products_for_ecommerce

    if attachments is None:
        att_list = []
    elif isinstance(attachments, list):
        att_list = attachments
    else:
        att_list = [attachments]

    try:
        return analyze_products_for_ecommerce(att_list, user_prompt, vision_model=vision_model)
    except Exception as exc:
        return {"visual_identity": str(exc), "primary_function": user_prompt[:300]}


